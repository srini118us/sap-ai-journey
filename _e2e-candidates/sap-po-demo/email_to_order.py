"""Email to Order pipeline: the glue.

Flow per unread mail with a PDF in the lab inbox:
  1. pull the attachment and sender
  2. Gemini (via the existing ADK agent + MCP tools) reads the PDF and
     validates against live S/4HANA -> structured proposal JSON
  3. proposal starts the SBPA approval process
  4. poll the decision (custom.decision: PENDING -> APPROVED/REJECTED)
  5. APPROVED -> create_sales_order (idempotency guard included)
  6. confirmation or decline email back to the sender

Modes:
  python email_to_order.py --once    process current unread mail, then exit
  python email_to_order.py --run     poll forever (every 60s)
"""

import asyncio
import email
import imaplib
import json
import os
import re
import smtplib
import sys
import time
from email.header import decode_header
from email.mime.text import MIMEText
from email.utils import parseaddr

# ---- load .env files BEFORE importing modules that read os.environ ----------
_here = os.path.dirname(os.path.abspath(__file__))
for _envfile in (os.path.join(_here, ".env"),
                 os.path.join(_here, "sap_po_agent", ".env")):
    if os.path.exists(_envfile):
        for _line in open(_envfile, encoding="utf-8"):
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _, _v = _line.partition("=")
                os.environ.setdefault(_k.strip(), _v.strip().strip('"').strip("'"))

import sap_mcp_server as sap                      # noqa: E402
from sbpa_watcher import (get_token, start_approval_process,  # noqa: E402
                          get_instance, _api)

MAIL_USER = os.environ["MAIL_USER"]
MAIL_APP_PASSWORD = os.environ["MAIL_APP_PASSWORD"]
IMAP_HOST = os.environ.get("IMAP_HOST", "imap.gmail.com")
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
DECISION_POLL_SECONDS = 20
DECISION_TIMEOUT_SECONDS = 45 * 60

AGENT_TASK = """Process the attached document as a potential CUSTOMER purchase order.

1. First decide: is this document actually a customer purchase order? 
2. If yes: extract the fields, validate against SAP using your tools
   (does the customer exist, is the material real, does an order for this
   customer PO number already exist), but do NOT create anything and do NOT
   ask for approval - a human will approve through a workflow.
3. End your reply with ONLY one fenced JSON block in exactly this shape:

```json
{
  "is_order": true,
  "customerName": "...",
  "sapCustomerNumber": "...",
  "customerPoNumber": "...",
  "material": "...",
  "quantity": 0,
  "requestedDate": "...",
  "checkResults": "one paragraph: each check with PASSED/FAILED and reason",
  "recommendation": "CREATE the sales order  OR  HOLD for human review"
}
```

If the document is NOT a customer purchase order, return "is_order": false and
put what the document appears to be into "checkResults".
"""


# ---------------------------------------------------------------- mailbox ---
def fetch_unread_pdfs():
    """Yield (sender, subject, filename, pdf_bytes) for unread mails with PDFs."""
    m = imaplib.IMAP4_SSL(IMAP_HOST)
    m.login(MAIL_USER, MAIL_APP_PASSWORD)
    m.select("INBOX")
    typ, data = m.search(None, "UNSEEN")
    ids = data[0].split() if data and data[0] else []
    results = []
    for num in ids:
        typ, msgdata = m.fetch(num, "(RFC822)")      # fetching marks it read
        msg = email.message_from_bytes(msgdata[0][1])
        sender = parseaddr(msg.get("From", ""))[1]
        raw_subj = msg.get("Subject", "")
        subject = ""
        for part, enc in decode_header(raw_subj):
            subject += part.decode(enc or "utf-8", "replace") if isinstance(part, bytes) else part
        for part in msg.walk():
            fname = part.get_filename() or ""
            if part.get_content_type() == "application/pdf" or fname.lower().endswith(".pdf"):
                payload = part.get_payload(decode=True)
                if payload:
                    results.append((sender, subject, fname or "attachment.pdf", payload))
    m.logout()
    return results


def send_mail(to_addr: str, subject: str, body: str) -> None:
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = MAIL_USER
    msg["To"] = to_addr
    with smtplib.SMTP_SSL(SMTP_HOST, 465) as s:
        s.login(MAIL_USER, MAIL_APP_PASSWORD)
        s.send_message(msg)


# ------------------------------------------------------------------ agent ---
def run_agent_on_pdf(pdf_bytes: bytes, filename: str) -> dict:
    """Headless run of the existing ADK agent on the PDF; returns the JSON proposal."""
    from google.adk.runners import InMemoryRunner
    from google.genai import types
    from sap_po_agent.agent import root_agent

    runner = InMemoryRunner(agent=root_agent, app_name="email_to_order")
    session = asyncio.run(runner.session_service.create_session(
        app_name="email_to_order", user_id="pipeline"))
    message = types.Content(role="user", parts=[
        types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
        types.Part(text=AGENT_TASK),
    ])
    final_text = ""
    for ev in runner.run(user_id="pipeline", session_id=session.id, new_message=message):
        if ev.content and ev.content.parts:
            for p in ev.content.parts:
                if getattr(p, "text", None):
                    final_text = p.text
    match = re.search(r"```json\s*(\{.*?\})\s*```", final_text, re.DOTALL)
    blob = match.group(1) if match else final_text[final_text.find("{"): final_text.rfind("}") + 1]
    proposal = json.loads(blob)
    proposal["sourceFile"] = filename
    return proposal


# --------------------------------------------------------------- decision ---
def wait_for_decision(instance_id: str) -> str:
    deadline = time.time() + DECISION_TIMEOUT_SECONDS
    while time.time() < deadline:
        token = get_token()
        ctx = _api("GET", f"/workflow/rest/v1/workflow-instances/{instance_id}/context", token)
        decision = ctx.get("custom", {}).get("decision", "PENDING")
        status = get_instance(instance_id, token).get("status", "?")
        print(f"    approval status={status} decision={decision}")
        if decision in ("APPROVED", "REJECTED"):
            return decision
        if status not in ("RUNNING", "SUSPENDED"):
            return decision
        time.sleep(DECISION_POLL_SECONDS)
    return "TIMEOUT"


# ---------------------------------------------------------------- pipeline --
def process_one(sender: str, subject: str, filename: str, pdf: bytes) -> None:
    print(f"\n=== {filename} from {sender} ({subject!r}) ===")
    print("  1) Gemini reads the document and checks SAP ...")
    try:
        proposal = run_agent_on_pdf(pdf, filename)
    except Exception as exc:
        print("  agent failed:", exc)
        send_mail(sender, "Order document could not be processed",
                  "Your document could not be processed automatically and was "
                  "routed to a human. Reference: " + filename)
        return

    if not proposal.get("is_order", False):
        print("  triage: not an order ->", proposal.get("checkResults", ""))
        send_mail(sender, "Document received - not recognized as an order",
                  "The attached document was not recognized as a customer "
                  "purchase order and was routed to a human for review.\n\n"
                  "Assessment: " + str(proposal.get("checkResults", "")))
        return

    print("  2) proposal:", proposal.get("customerPoNumber"),
          proposal.get("material"), proposal.get("quantity"))
    token = get_token()
    payload = {k: proposal.get(k, "") for k in (
        "customerName", "sapCustomerNumber", "customerPoNumber", "material",
        "quantity", "requestedDate", "checkResults", "recommendation", "sourceFile")}
    instance_id = start_approval_process(payload, token)
    print(f"  3) approval task created (instance {instance_id}) - go to My Inbox")

    decision = wait_for_decision(instance_id)
    print("  4) decision:", decision)

    if decision == "APPROVED":
        print("  5) posting to S/4HANA ...")
        try:
            result = json.loads(sap.create_sales_order(
                proposal["customerPoNumber"], proposal["sapCustomerNumber"],
                proposal["material"], int(proposal["quantity"])))
        except Exception as exc:
            print("  posting failed:", exc)
            send_mail(sender, "Order approved - posting issue",
                      "Your order was approved but posting hit a technical "
                      "issue; our team will follow up. Ref: " + filename)
            return
        so = result.get("created_sales_order") or result.get("sales_order")
        note = " (existing order - duplicate submission detected)" if result.get("already_exists") else ""
        print(f"  6) SALES ORDER {so}{note}")
        send_mail(sender, f"Order confirmed - SAP Sales Order {so}",
                  f"Thank you. Your purchase order {proposal['customerPoNumber']} "
                  f"was approved and recorded as SAP Sales Order {so}{note}.\n"
                  f"Total net amount: {result.get('total_net_amount')} "
                  f"{result.get('currency')}.")
    elif decision == "REJECTED":
        send_mail(sender, f"Order {proposal['customerPoNumber']} - not approved",
                  "Your purchase order was reviewed and not approved. "
                  "Please contact our sales team for details.")
    else:
        print("  no decision within the window; task remains in My Inbox")


def main() -> None:
    loop = "--run" in sys.argv
    while True:
        batch = fetch_unread_pdfs()
        if batch:
            for sender, subject, fname, pdf in batch:
                process_one(sender, subject, fname, pdf)
        else:
            print("no unread mail with PDF attachments")
        if not loop:
            break
        time.sleep(60)


if __name__ == "__main__":
    if "--once" in sys.argv or "--run" in sys.argv:
        main()
    else:
        print(__doc__)