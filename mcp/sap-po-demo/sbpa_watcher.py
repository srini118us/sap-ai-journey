"""Email to Order watcher, session 2: trigger the SBPA approval process and
watch its outcome.

Modes:
  python sbpa_watcher.py --handshake       auth + list deployed definitions
  python sbpa_watcher.py --test-trigger    start one approval with sample data
  python sbpa_watcher.py --watch <id>      poll an instance until it completes
"""

import json
import os
import sys
import time

import httpx

_envfile = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
if os.path.exists(_envfile):
    for _line in open(_envfile, encoding="utf-8"):
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _, _v = _line.partition("=")
            os.environ.setdefault(_k.strip(), _v.strip().strip('"').strip("'"))

SBPA_CLIENT_ID = os.environ.get("SBPA_CLIENT_ID", "")
SBPA_CLIENT_SECRET = os.environ.get("SBPA_CLIENT_SECRET", "")
SBPA_TOKEN_URL = os.environ.get("SBPA_TOKEN_URL", "")
SBPA_API_URL = os.environ.get("SBPA_API_URL", "").rstrip("/")
SBPA_DEFINITION_ID = os.environ.get(
    "SBPA_DEFINITION_ID",
    "eu10.sap-joule-dev-s0gu7itl.orderapprovalemailtoordergcp.order_Approval",
)


def get_token() -> str:
    resp = httpx.post(
        SBPA_TOKEN_URL,
        data={"grant_type": "client_credentials"},
        auth=(SBPA_CLIENT_ID, SBPA_CLIENT_SECRET),
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def _api(method: str, path: str, token: str, payload: dict = None):
    resp = httpx.request(
        method,
        f"{SBPA_API_URL}{path}",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
        timeout=30,
    )
    if resp.status_code >= 400:
        raise RuntimeError(f"SBPA API {resp.status_code}: {resp.text[:600]}")
    return resp.json() if resp.text else {}


def list_process_definitions(token: str) -> list:
    return _api("GET", "/workflow/rest/v1/workflow-definitions", token)


def start_approval_process(proposal: dict, token: str) -> str:
    """Start the deployed approval process with the proposal as context.
    Keys go in both given casing and lowercase so either identifier style binds."""
    context = {}
    for k, v in proposal.items():
        lk = k.lower()
        context[lk] = v
        context["_" + lk] = v
    data = _api(
        "POST", "/workflow/rest/v1/workflow-instances", token,
        {"definitionId": SBPA_DEFINITION_ID, "context": context},
    )
    return data.get("id", "")


def get_instance(instance_id: str, token: str) -> dict:
    return _api("GET", f"/workflow/rest/v1/workflow-instances/{instance_id}", token)


def get_execution_logs(instance_id: str, token: str) -> list:
    return _api(
        "GET",
        f"/workflow/rest/v1/workflow-instances/{instance_id}/execution-logs",
        token,
    )


def _decision_from_logs(logs: list) -> str:
    for entry in logs:
        if str(entry.get("type", "")).upper().startswith("USERTASK") and (
            "COMPLETED" in str(entry.get("type", "")).upper()
        ):
            blob = json.dumps(entry).lower()
            for marker, verdict in (
                ('"decision": "approve', "APPROVED"),
                ('"outcome": "approve', "APPROVED"),
                ("'approve'", "APPROVED"),
                ('"decision": "reject', "REJECTED"),
                ('"outcome": "reject', "REJECTED"),
                ("'reject'", "REJECTED"),
            ):
                if marker in blob:
                    return verdict
            print("  usertask entry detail:", json.dumps(entry)[:500])
    return "UNKNOWN (see the printed entry detail)"


def handshake() -> None:
    print("1) Requesting OAuth token ...")
    token = get_token()
    print(f"   token received ({len(token)} chars)")
    print("2) Calling the Process Automation API ...")
    defs = list_process_definitions(token)
    print(f"   OK. Deployed process definitions visible: {len(defs)}")
    for d in defs:
        print(f"   - {d.get('id')}  (version {d.get('version')})")
    print("\nHANDSHAKE COMPLETE: the watcher can authenticate and talk to SBPA.")


def test_trigger() -> None:
    proposal = {
        "customerName": "Riverbend Retail Group",
        "sapCustomerNumber": "17100009",
        "customerPoNumber": "CPO-2026-0900",
        "material": "TG11",
        "quantity": 5,
        "requestedDate": "09/15/2026",
        "checkResults": (
            "PO duplicate check: PASSED (no order exists for CPO-2026-0900). "
            "Customer check: PASSED (17100009 known, prior orders exist). "
            "Material check: PASSED (TG11 valid). All checks passed."
        ),
        "recommendation": "CREATE the sales order",
        "sourceFile": "test_trigger_sample.pdf",
    }
    print("Starting approval process ...")
    token = get_token()
    instance_id = start_approval_process(proposal, token)
    print(f"Instance started: {instance_id}")
    print("Now open My Inbox in SAP Build: the task should appear there.")
    print(f"To watch the outcome:  python sbpa_watcher.py --watch {instance_id}")


def watch(instance_id: str) -> None:
    token = get_token()
    print(f"Watching instance {instance_id} (poll every 10s, Ctrl+C to stop)")
    while True:
        inst = get_instance(instance_id, token)
        status = inst.get("status", "?")
        print(f"  status: {status}")
        if status not in ("RUNNING", "SUSPENDED"):
            break
        time.sleep(10)
        token = get_token()
    ctx = _api(
        "GET",
        f"/workflow/rest/v1/workflow-instances/{instance_id}/context",
        token,
    )
    print(f"Decision: {ctx.get('custom', {}).get('decision', 'not set')}")


def show_context(instance_id: str) -> None:
    token = get_token()
    ctx = _api(
        "GET",
        f"/workflow/rest/v1/workflow-instances/{instance_id}/context",
        token,
    )
    print(json.dumps(ctx, indent=2))


def mail_test() -> None:
    import imaplib
    m = imaplib.IMAP4_SSL(os.environ.get("IMAP_HOST", "imap.gmail.com"))
    m.login(os.environ["MAIL_USER"], os.environ["MAIL_APP_PASSWORD"])
    m.select("INBOX")
    typ, data = m.search(None, "UNSEEN")
    ids = data[0].split() if data and data[0] else []
    print(f"Connected as {os.environ['MAIL_USER']}. Unread messages: {len(ids)}")
    m.logout()


if __name__ == "__main__":
    if "--handshake" in sys.argv:
        handshake()
    elif "--test-trigger" in sys.argv:
        test_trigger()
    elif "--watch" in sys.argv:
        idx = sys.argv.index("--watch")
        watch(sys.argv[idx + 1])
    elif "--context" in sys.argv:
        idx = sys.argv.index("--context")
        show_context(sys.argv[idx + 1])
    elif "--mail-test" in sys.argv:
        mail_test()
    else:
        print(__doc__)