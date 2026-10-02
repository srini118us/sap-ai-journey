"""Node bodies for the invoice flow.

`extract` is real: it calls SAP GenAI Hub. `score` is real: it calls SAP
RPT-1.5, on synthetic context rows. `intake` is real apart from OCR. Every
other node is still a STUB, marked with what replaces it.

Each node returns a partial state update plus exactly one trace entry --
including when it has nothing to flag, and including when it fails. Nothing
here raises: intake, extraction and scoring failures are caught, traced, and
routed to a human.

Split this module into a nodes/ package when `score` grows a real body; that
is the next natural seam.
"""

import json
import re

from . import genai, rpt, s4hana, vertex_secondopinion
from .samples import STUB_RISK_CONTEXT
from .state import InvoiceState, trace

# The column RPT-1.5 fills in, and the bands it chooses between. The list is
# the context table's vocabulary -- it sets how many candidates to ask for, and
# names the band whose probability becomes the risk score. The model is free to
# return something else; score traces it when it does.
RISK_COLUMN = "risk_band"
RISK_BANDS = ["HIGH", "MEDIUM", "LOW"]
SCORE_BAND = "HIGH"

# Tolerance for comparing two money amounts: the invoice against the PO, and
# the line items against the stated total. Rounding noise is not a discrepancy.
AMOUNT_TOLERANCE = 0.01

# Fields the extract node asks the model for, in the shape the rest of the
# flow expects.
EXTRACTED_FIELDS = ["vendor", "invoice_number", "amount", "currency", "po_reference", "line_items"]

# The fields the two independent extractions are compared on -- not all of
# them. These three decide the money, the counterparty and the commitment
# being drawn down, which is to say they are the ones where a misread changes
# the outcome. A disagreement on, say, invoice_number is a data-quality note,
# not a reason to stop a payment, and cross-checking everything would bury the
# three that matter under noise.
CROSS_CHECK_FIELDS = ["amount", "vendor", "po_reference"]

# Checks whose result is a precondition for posting without a person looking.
# A check that merely could not run is not an issue -- nothing is known about
# the invoice either way -- but straight-through posting one whose purchase
# order was never verified is precisely the silent pass this flow exists to
# prevent, so `route` treats an unrun control check as a trigger.
#
# `amount_matches_po` is in here for the same reason `po_exists` is, and it is
# the subtler of the two: the PO can be found, the vendor can match, and the
# amount comparison can still not run -- a PO carrying no items has no total,
# and a PO in another currency has no comparable one. Posting on that is
# posting an invoice whose money was checked against nothing.
#
# The cross-model check is deliberately NOT in here: a second opinion is
# supplementary, and losing it must not change where an invoice goes.
CONTROL_CHECKS = {"po_exists", "amount_matches_po"}

EXTRACTION_SYSTEM_PROMPT = """\
You extract structured data from invoice documents.

Return ONLY a single valid JSON object. No prose, no explanation, no markdown
code fences, no text before or after the JSON.

If a field is not present in the document, use null for it. Do not guess and
do not invent values that are not in the document."""

EXTRACTION_USER_TEMPLATE = """\
Extract the invoice fields from the document below.

Return a JSON object with exactly these keys:

{{
  "vendor": string,            // the supplier issuing the invoice
  "invoice_number": string,
  "amount": number,            // total amount due, taken from the invoice total line
  "currency": string,          // ISO 4217 code, e.g. EUR
  "po_reference": string,      // purchase order reference, or null if absent
  "line_items": [
    {{"description": string, "quantity": number, "unit_price": number, "amount": number}}
  ]
}}

Rules for numbers:
- Copy every digit exactly as printed, including all decimal places. 4,820.50
  is 4820.50 -- not 4820, not 4820.5 rounded from something else.
- Strip currency symbols and thousands separators. Keep the decimal point.
- Never round, re-derive, or recalculate a total. Read it off the document.

Document:
---
{document_text}
---"""

# Models sometimes wrap JSON in a code fence despite being told not to. That is
# a known formatting quirk, not a parse failure -- strip it, and trace that we
# had to.
_FENCE_RE = re.compile(r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", re.DOTALL)


def _strip_fences(text: str) -> tuple[str, bool]:
    """Return (payload, cleanup_applied)."""
    match = _FENCE_RE.match(text)
    return (match.group(1), True) if match else (text, False)


def _norm_name(value):
    """Fold a name for comparison: case and whitespace differences are not
    mismatches. Invoice letterheads are routinely all-caps while master data
    is title case. The real validate node matches on vendor ID from the vendor
    master and will not need this."""
    if not isinstance(value, str):
        return None
    return " ".join(value.split()).casefold()


def _as_float(value):
    """Coerce a model-supplied number to float, or None if it cannot be."""
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.replace(",", "").replace(" ", "").strip())
        except ValueError:
            return None
    return None


def _line_items_total(line_items):
    """Sum the line-item amounts.

    Returns (total, unreadable), where `unreadable` counts entries whose amount
    could not be read as a number. A non-zero count makes the sum untrustworthy,
    so the caller skips the comparison rather than reporting a discrepancy that
    is really an extraction gap.

    Amounts are never re-derived from quantity * unit_price. Extraction copies
    what the document printed, and so does this -- re-deriving would paper over
    the very inconsistency the check exists to find.
    """
    total = 0.0
    unreadable = 0
    for item in line_items:
        amount = _as_float(item.get("amount")) if isinstance(item, dict) else None
        if amount is None:
            unreadable += 1
        else:
            total += amount
    return total, unreadable


def _rejected(decision: str, reason: str, **data) -> dict:
    """Build the partial update for an intake that produced no usable document.

    `document` stays None so nothing downstream can mistake a rejection for an
    empty-but-valid invoice, and `intake_error` is what the conditional edge
    below reads.
    """
    return {
        "document": None,
        "intake_error": reason,
        "trace": trace("intake", decision=decision, reason=reason, **data),
    }


def intake(state: InvoiceState) -> dict:
    """Normalize the raw input into a document the rest of the flow can read.

    Three outcomes, all traced, none raising -- the same shape `extract` uses:

      accepted       -> document populated, flow continues to extract
      no_document    -> nothing readable was handed in at all
      empty_document -> text was handed in, and it is blank

    The two failures are kept apart on purpose. "No text arrived" points at
    the upstream handoff; "text arrived and it is blank" points at the
    document itself, and they send an operator to different places.

    Every rejection is an explicit check on the input, never a caught
    exception: a blanket try/except here would swallow a bug in this node and
    report it as a bad invoice.

    STUB: only the OCR is missing. The real node accepts a PDF/image/IDoc,
    runs OCR over it, and stores the original. The normalization and the
    rejections below are real and survive that change -- an unreadable scan
    fails here exactly as blank text does now.
    """
    source = state.get("source")

    if not isinstance(source, dict):
        return _rejected(
            "no_document",
            f"No document was handed in: source is {type(source).__name__}, expected a dict.",
            invoice_id=state["invoice_id"],
        )

    raw_text = source.get("text")
    if not isinstance(raw_text, str):
        found = "absent" if raw_text is None else f"of type {type(raw_text).__name__}"
        return _rejected(
            "no_document",
            f"Source carries no document text: `text` is {found}, expected a string.",
            invoice_id=state["invoice_id"],
            source_keys=sorted(source),
        )

    # Line endings are normalized so that the same document handed in from
    # Windows and from Unix produces the same text and the same char count.
    text = raw_text.replace("\r\n", "\n").replace("\r", "\n").strip()

    filename = source.get("filename")
    filename = filename.strip() or None if isinstance(filename, str) else None

    if not text:
        handed_in = (
            "no characters were handed in"
            if not raw_text
            else f"{len(raw_text)} characters were handed in and all of them are whitespace"
        )
        return _rejected(
            "empty_document",
            f"Document text is empty: {handed_in}.",
            invoice_id=state["invoice_id"],
            filename=filename,
        )

    document = {
        "invoice_id": state["invoice_id"],
        "filename": filename,
        "received_at": source.get("received_at"),
        "text": text,
    }
    return {
        "document": document,
        "intake_error": None,
        "trace": trace(
            "intake",
            decision="accepted",
            reason=(
                f"Document normalized into state ({len(text)} characters); no OCR in the stub."
                if filename
                else (
                    f"Document normalized into state ({len(text)} characters); no filename was "
                    "supplied. No OCR in the stub."
                )
            ),
            filename=filename,
            received_at=document["received_at"],
            text_chars=len(text),
        ),
    }


def select_after_intake(state: InvoiceState) -> str:
    """Conditional edge: skip the whole flow when there is no document to read."""
    return "human_review" if state["intake_error"] else "extract"


def _second_opinion(document_text: str) -> dict:
    """Fetch the cross-model reading of the same document, or say why there is
    none.

    This is the project's one deliberate non-AI-Core call, and it stays a
    comparison: the SAP GenAI Hub extraction above is and remains the primary.
    See CLAUDE.md.

    Never raises, and -- more importantly -- never fails the invoice. The three
    statuses mirror `extract_fields`'s own contract:

      extracted     -> the endpoint returned fields; a comparison can run
      not_extracted -> the endpoint ran and found nothing. Its own verdict, not
                       a failure: the second-opinion analogue of `parse_failed`
      call_failed   -> the endpoint could not be reached, or refused

    Only `extracted` can produce a disagreement. The other two are a *missing
    comparison*, which `validate` records as a skipped check -- collapsing them
    into a disagreement would let an unreachable endpoint stop payments, which
    is the opposite of what a second opinion is for.
    """
    try:
        result = vertex_secondopinion.extract_fields(document_text)
    except vertex_secondopinion.VertexSecondOpinionError as e:
        return {
            "status": "call_failed",
            "fields": {},
            "model": vertex_secondopinion.MODEL_NAME,
            "detail": str(e),
        }

    if not result["extracted"]:
        return {
            "status": "not_extracted",
            "fields": {},
            "model": result["model"],
            "detail": "The endpoint ran and returned no fields.",
        }

    return {
        "status": "extracted",
        "fields": result["fields"],
        "model": result["model"],
        "detail": f"{len(result['fields'])} field(s) returned.",
    }


def extract(state: InvoiceState) -> dict:
    """Pull structured fields out of the document with an LLM via SAP GenAI Hub,
    then fetch a second, independently-built reading of the same document.

    Extraction is an LLM job -- never RPT-1.5, which is for scoring.

    Three outcomes, all traced, none raising:
      extracted    -> fields populated, flow continues to validate
      parse_failed -> model returned something that is not JSON
      call_failed  -> GenAI Hub could not be reached or refused the call

    The second opinion is fetched here, on the success path only, because this
    is where a document text becomes fields and both readings are peers. It
    never touches the decision above: whatever the cross-cloud call does, the
    outcome of this node is decided by the SAP extraction alone, and the
    comparison is `validate`'s to make. On the two failure paths it is not
    called at all -- with no SAP fields there is nothing to compare it against,
    and spending the call would buy nothing, the same reasoning that makes a
    rejected intake skip this node entirely.
    """
    document_text = state["document"]["text"]
    messages = [
        {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
        {"role": "user", "content": EXTRACTION_USER_TEMPLATE.format(document_text=document_text)},
    ]

    # 1. Call the model.
    try:
        raw = genai.complete(messages)
    except genai.GenAIHubError as e:
        error = str(e)
        return {
            "fields": None,
            "extraction_error": error,
            "second_opinion": None,
            "trace": trace(
                "extract",
                decision="call_failed",
                reason=f"GenAI Hub call failed: {error}",
                model=genai.model_name(),
            ),
        }

    # 2. Parse the response as JSON.
    payload, cleanup_applied = _strip_fences(raw or "")
    try:
        parsed = json.loads(payload)
    except (json.JSONDecodeError, TypeError) as e:
        error = f"Model response was not valid JSON: {e}"
        return {
            "fields": None,
            "extraction_error": error,
            "second_opinion": None,
            "trace": trace(
                "extract",
                decision="parse_failed",
                reason=error,
                model=genai.model_name(),
                cleanup_applied=cleanup_applied,
                raw_preview=(raw or "")[:200],
            ),
        }

    if not isinstance(parsed, dict):
        error = f"Model returned JSON of type {type(parsed).__name__}, expected an object."
        return {
            "fields": None,
            "extraction_error": error,
            "second_opinion": None,
            "trace": trace(
                "extract",
                decision="parse_failed",
                reason=error,
                model=genai.model_name(),
                raw_preview=(raw or "")[:200],
            ),
        }

    # 3. Normalize onto the keys the rest of the flow expects.
    fields = {key: parsed.get(key) for key in EXTRACTED_FIELDS}
    fields["amount"] = _as_float(fields["amount"])
    if not isinstance(fields["line_items"], list):
        fields["line_items"] = []

    absent = [k for k in EXTRACTED_FIELDS if fields[k] in (None, [])]

    # 4. A second, independently-built reading of the same document. Its
    #    outcome is recorded, never acted on here.
    opinion = _second_opinion(document_text)
    other = opinion["fields"]

    reason = (
        f"Extracted {len(EXTRACTED_FIELDS)} fields via GenAI Hub."
        if not absent
        else f"Extracted via GenAI Hub; absent from the document: {', '.join(absent)}."
    )
    reason += f" Second opinion ({opinion['model']}): {opinion['status']} -- {opinion['detail']}"

    return {
        "fields": fields,
        "extraction_error": None,
        "second_opinion": opinion,
        "trace": trace(
            "extract",
            decision="extracted" if not absent else "extracted_with_gaps",
            reason=reason,
            model=genai.model_name(),
            cleanup_applied=cleanup_applied,
            vendor=fields["vendor"],
            invoice_number=fields["invoice_number"],
            amount=fields["amount"],
            currency=fields["currency"],
            po_reference=fields["po_reference"],
            line_item_count=len(fields["line_items"]),
            # Both readings of the key fields land in one trace entry, at the
            # moment both were obtained. `validate` records the verdict; this
            # records what each model actually said.
            second_opinion=opinion["status"],
            second_opinion_model=opinion["model"],
            second_opinion_amount=_as_float(other.get("amount")),
            second_opinion_vendor=other.get("vendor"),
            second_opinion_po_reference=other.get("po_reference"),
        ),
    }


def select_after_extract(state: InvoiceState) -> str:
    """Conditional edge: skip validate/score when there are no fields to work on."""
    return "human_review" if state["extraction_error"] else "validate"


def _cross_check_second_opinion(fields: dict, opinion: dict, sap_model: str):
    """Compare the two independent extractions on the key fields.

    Returns (checked, issues, skipped) for `validate` to fold into its own
    lists -- the same three-way shape its other checks report in.

    Only a field *both* models read can disagree. A field one of them left
    absent is recorded as a skipped comparison naming which model was silent:
    one extractor missing what the other found is a coverage gap, not a
    contradiction, and reporting it as a disagreement would make "we compared
    them and they differ" indistinguishable from "we could not compare them".
    Same rule as validation["skipped"] and the score row's `not_checked`.

    Amounts are compared as numbers on the existing tolerance -- two models
    printing 4820.5 and 4820.50 have not disagreed about anything. Names and
    references are compared case-folded and whitespace-folded, because a
    letterhead in caps and master data in title case are the same vendor.
    """
    checked, issues, skipped = [], [], []
    other_model = opinion["model"]

    for field in CROSS_CHECK_FIELDS:
        check = f"second_opinion_{field}"
        ours, theirs = fields.get(field), opinion["fields"].get(field)

        if field == "amount":
            ours_read, theirs_read = _as_float(ours), _as_float(theirs)
            # `is not None`, not truthiness: an invoice for 0.00 was still read.
            readable = (ours_read is not None, theirs_read is not None)
        else:
            ours_read, theirs_read = _norm_name(ours), _norm_name(theirs)
            # A field folded down to "" carries nothing to compare.
            readable = (bool(ours_read), bool(theirs_read))

        if not all(readable):
            silent = [m for m, ok in zip((sap_model, other_model), readable) if not ok]
            skipped.append(
                {
                    "check": check,
                    "reason": (
                        f"No usable {field} from {' or '.join(silent)}; there is nothing "
                        "to compare, which is not a disagreement."
                    ),
                }
            )
            continue

        checked.append(check)

        if field == "amount":
            delta = abs(ours_read - theirs_read)
            if delta > AMOUNT_TOLERANCE:
                issues.append(
                    {
                        "code": "extraction_disagreement",
                        "detail": (
                            f"amount: {sap_model} read {ours_read:.2f}, {other_model} read "
                            f"{theirs_read:.2f} (off by {delta:.2f})."
                        ),
                    }
                )
        elif ours_read != theirs_read:
            issues.append(
                {
                    "code": "extraction_disagreement",
                    "detail": (
                        f"{field}: {sap_model} read {ours!r}, {other_model} read {theirs!r}."
                    ),
                }
            )

    return checked, issues, skipped


def validate(state: InvoiceState) -> dict:
    """Check the extracted fields for internal consistency, against the PO, and
    against a second model's reading of the same document.

    Three independent checks, all traced:

      1. Line items vs the stated total. Catches a number misread during
         extraction -- a dropped cent, a transposed digit -- with no PO
         involved. It runs even when the PO cannot be found, because a bad PO
         reference is exactly where a misread amount also hides.
      2. The extracted fields vs the purchase order, read live from S/4HANA.
         Three outcomes, and they are not interchangeable: the PO is found and
         compared; S/4HANA answers that no such PO exists, which is a
         `po_not_found` issue because an invoice citing a nonexistent PO is
         suspicious; or S/4HANA cannot be reached, which says nothing about
         the invoice and is recorded as a check that did not run.
      3. The extracted fields vs the cross-model second opinion, on the key
         fields. Catches the misread that check 1 cannot see -- one where the
         invoice is internally consistent and agrees with the PO, and the
         document itself is simply ambiguous about what it says.

    Checks 1 and 3 are both extraction-quality checks and both read only
    state; check 3 is placed last so the PO comparison keeps its position.
    This node makes the comparison but does not fetch the second reading --
    `extract` does that, which keeps every check here pure logic over state.

    A check that cannot run is recorded in `skipped`, never passed over: "no
    line items were extracted" and "the line items reconciled" are different
    facts and the trace has to tell them apart. That rule carries the whole
    weight of check 3's failure mode: an unreachable second-opinion endpoint
    is a *missing comparison*, recorded and moved past, never an issue and
    never a reason to hold an invoice.

    Check 2 reads the PO header and its items from API_PURCHASEORDER_PROCESS_SRV
    (`s4hana.py`). The header carries no total, so the PO total is summed from
    the items. Comparisons that the PO itself cannot support -- no address
    name, no items, a currency the invoice does not share -- are skipped with
    the reason, never guessed at.

    Still stubbed here: nothing else about the PO is checked. The real node
    also reads the vendor master and the goods receipt, which is what turns
    "the PO says this vendor" into "this vendor is who we think they are" and
    "the amount matches" into "the goods actually arrived".
    """
    fields = state["fields"]
    po_reference = fields.get("po_reference")

    checked = []
    issues = []
    skipped = []

    # 1. Internal consistency: do the line items add up to the stated total?
    amount = fields.get("amount")
    line_items = fields.get("line_items") or []
    items_sum, unreadable = _line_items_total(line_items)

    if amount is None:
        skipped.append(
            {
                "check": "line_items_sum_matches_total",
                "reason": "No usable total was extracted from the invoice.",
            }
        )
    elif not line_items:
        skipped.append(
            {
                "check": "line_items_sum_matches_total",
                "reason": "No line items were extracted from the invoice.",
            }
        )
    elif unreadable:
        skipped.append(
            {
                "check": "line_items_sum_matches_total",
                "reason": (
                    f"{unreadable} of {len(line_items)} line item amounts were unreadable; "
                    "any sum would be misleading."
                ),
            }
        )
    else:
        checked.append("line_items_sum_matches_total")
        delta = abs(items_sum - amount)
        if delta > AMOUNT_TOLERANCE:
            issues.append(
                {
                    "code": "amount_inconsistent",
                    "detail": (
                        f"Line items sum to {items_sum:.2f} but the stated total is "
                        f"{amount:.2f} (off by {delta:.2f})."
                    ),
                }
            )

    # 2. Against the purchase order in S/4HANA.
    po = None
    try:
        lookup = s4hana.fetch_purchase_order(po_reference)
    except s4hana.S4HANAError as e:
        # Infrastructure, not the invoice. The check does not run, and saying
        # so is the whole point: a PO that was never looked up must not read
        # as a PO that checked out. `route` picks this up as a control that
        # could not be verified, so nothing posts on the strength of it.
        skipped.append(
            {
                "check": "po_exists",
                "reason": (
                    f"S/4HANA could not be reached, so PO {po_reference} was never looked "
                    f"up: {e} Nothing about this invoice is implied either way."
                ),
            }
        )
    else:
        checked.append("po_exists")
        if lookup["found"]:
            po = lookup["po"]
        else:
            # S/4HANA answered, and the answer is that this PO does not exist.
            # An invoice citing one that does not is suspicious on its face.
            issues.append({"code": "po_not_found", "detail": lookup["reason"]})

    if po is not None:
        if not po["vendor"]:
            skipped.append(
                {
                    "check": "vendor_matches_po",
                    "reason": (
                        f"PO {po['po_reference']} carries no address name in S/4HANA; there "
                        "is no vendor to compare the invoice against."
                    ),
                }
            )
        else:
            checked.append("vendor_matches_po")
            if _norm_name(po["vendor"]) != _norm_name(fields.get("vendor")):
                issues.append(
                    {
                        "code": "vendor_mismatch",
                        "detail": (
                            f"Invoice vendor {fields.get('vendor')!r} != PO vendor "
                            f"{po['vendor']!r} (supplier {po['supplier']})."
                        ),
                    }
                )

        # Currency is settled before the amount, because whether two figures
        # can be compared at all depends on it.
        same_currency = False
        if not po["currency"]:
            skipped.append(
                {
                    "check": "currency_matches_po",
                    "reason": f"PO {po['po_reference']} carries no document currency in S/4HANA.",
                }
            )
        else:
            checked.append("currency_matches_po")
            if po["currency"] != fields.get("currency"):
                issues.append(
                    {
                        "code": "currency_mismatch",
                        "detail": (
                            f"Invoice currency {fields.get('currency')!r} != PO currency "
                            f"{po['currency']!r}."
                        ),
                    }
                )
            else:
                same_currency = True

        if po["amount"] is None:
            skipped.append(
                {
                    "check": "amount_matches_po",
                    "reason": (
                        f"PO {po['po_reference']} carries no items in S/4HANA, so it has no "
                        "total to compare against."
                    ),
                }
            )
        elif amount is None:
            issues.append(
                {"code": "amount_unreadable", "detail": "No usable amount was extracted from the invoice."}
            )
        elif not same_currency:
            # 3391.38 USD and 3391.38 EUR are not the same amount of money.
            # Comparing them without a rate would report a match that is not
            # one; the currency difference is already an issue above.
            skipped.append(
                {
                    "check": "amount_matches_po",
                    "reason": (
                        f"Invoice is in {fields.get('currency')!r} and PO "
                        f"{po['po_reference']} is in {po['currency']!r}; the two totals are "
                        "not comparable without an exchange rate."
                    ),
                }
            )
        else:
            checked.append("amount_matches_po")
            if abs(po["amount"] - amount) > AMOUNT_TOLERANCE:
                issues.append(
                    {
                        "code": "amount_mismatch",
                        "detail": (
                            f"Invoice amount {amount:.2f} != PO total {po['amount']:.2f} "
                            f"({po['item_count']} item(s) in S/4HANA)."
                        ),
                    }
                )

    # 3. Against the second, independently-built extraction.
    opinion = state.get("second_opinion")
    opinion_status = opinion["status"] if opinion else "not_run"

    if opinion_status == "extracted":
        cross_checked, cross_issues, cross_skipped = _cross_check_second_opinion(
            fields, opinion, genai.model_name()
        )
        checked += cross_checked
        issues += cross_issues
        skipped += cross_skipped
    else:
        # The endpoint was unreachable, or ran and found nothing, or extraction
        # never got here. None of those is a disagreement, and none of them
        # changes where this invoice is routed -- it is recorded as a
        # comparison that did not happen and the flow carries on.
        detail = opinion["detail"] if opinion else "Extraction did not reach the second opinion."
        skipped.append(
            {
                "check": "second_opinion",
                "reason": (
                    f"No second opinion to compare against ({opinion_status}): {detail} "
                    "A comparison that could not be made is not a disagreement."
                ),
            }
        )

    reconciled = "line_items_sum_matches_total" in checked

    if issues:
        reason = "; ".join(i["detail"] for i in issues)
    else:
        reason = f"All {len(checked)} checks passed (PO {po_reference})"
        reason += "; line items reconciled to the stated total." if reconciled else "."
    if skipped:
        reason += " Skipped: " + "; ".join(f"{s['check']} -- {s['reason']}" for s in skipped)

    validation = {"issues": issues, "checked": checked, "skipped": skipped}
    return {
        "validation": validation,
        "trace": trace(
            "validate",
            decision="issues_found" if issues else "passed",
            reason=reason,
            checks_run=len(checked),
            issue_codes=[i["code"] for i in issues],
            checks_skipped=[s["check"] for s in skipped],
            line_items_sum=round(items_sum, 2) if reconciled else None,
            stated_total=amount if reconciled else None,
            second_opinion=opinion_status,
        ),
    }


def _risk_features(state: InvoiceState) -> dict:
    """Build the feature row RPT-1.5 scores, from extracted fields and what
    validate found.

    `po_status` carries `not_checked` when S/4HANA could not be reached.
    STUB_RISK_CONTEXT holds no row with that value, deliberately: there is no
    observed history of how invoices scored during an outage, and inventing
    some would be the fabricated signal that file warns against. RPT-1.5 sees
    an unfamiliar category and leans on the other columns, which is the honest
    outcome -- and `route` has already flagged the invoice by then anyway.

    `score` runs after `validate`, so the validation outcome is the strongest
    signal available -- and the live model agrees: on a probe of this exact
    row shape it put most of its weight on amount, vendor_known and po_status.

    Every column that can be unknown says so rather than defaulting to a
    verdict. A PO that was never found leaves the vendor comparison unrun, and
    "we checked and the vendor matched" must not look like "we never checked"
    -- the same rule validate follows with its skipped list.
    """
    fields = state["fields"]
    validation = state["validation"]

    codes = {issue["code"] for issue in validation["issues"]}
    checked = set(validation["checked"])

    if "po_exists" not in checked:
        # S/4HANA was unreachable. Without this branch the row would fall
        # through to "matched" and tell RPT-1.5 -- and the trace, and whoever
        # reads it later -- that a PO checked out when it was never fetched.
        po_status = "not_checked"
    elif "po_not_found" in codes:
        po_status = "not_found"
    elif codes & {"amount_mismatch", "currency_mismatch", "vendor_mismatch", "amount_unreadable"}:
        po_status = "mismatched"
    else:
        po_status = "matched"

    if "vendor_mismatch" in codes:
        vendor_known = "no"
    elif "vendor_matches_po" in checked:
        vendor_known = "yes"
    else:
        vendor_known = "not_checked"

    if "line_items_sum_matches_total" not in checked:
        line_items_reconcile = "not_checked"
    elif "amount_inconsistent" in codes:
        line_items_reconcile = "no"
    else:
        line_items_reconcile = "yes"

    return {
        "amount": fields.get("amount"),
        "currency": fields.get("currency"),
        "po_status": po_status,
        "vendor_known": vendor_known,
        "line_items_reconcile": line_items_reconcile,
    }


def score(state: InvoiceState) -> dict:
    """Risk score the invoice with SAP RPT-1.5.

    Scoring is an RPT-1.5 job -- never the extraction LLM. RPT-1.5 is a
    tabular model: it is handed a feature row, not a prompt.

    It predicts in context, so the call carries STUB_RISK_CONTEXT (rows with
    known outcomes) followed by this invoice with its band marked for
    prediction. Asking for top_k candidates rather than one is what makes a
    real score possible: the band is the top candidate, and the probability
    mass on HIGH is the score.

    Three outcomes, all traced, none raising:
      scored        -> band and distribution from RPT-1.5, flow continues
      call_failed   -> the deployment could not be reached or refused the call
      no_prediction -> a well-formed response that carries no band for this row

    STUB: the context rows, and only those. The call, the feature row and the
    returned distribution are real. Real context is settled invoices from
    S/4HANA; two dozen invented rows make the predictions directionally sane,
    not calibrated.
    """
    features = _risk_features(state)
    query_row = {
        "invoice_id": state["invoice_id"],
        **features,
        RISK_COLUMN: rpt.PREDICT_PLACEHOLDER,
    }
    rows = STUB_RISK_CONTEXT + [query_row]

    try:
        body = rpt.predict(
            rows,
            target_column=RISK_COLUMN,
            index_column="invoice_id",
            top_k=len(RISK_BANDS),
        )
    except rpt.RPTError as e:
        error = str(e)
        return {
            "risk": None,
            "score_error": error,
            "trace": trace(
                "score",
                decision="call_failed",
                reason=f"RPT-1.5 call failed: {error}",
                model=rpt.MODEL_NAME,
                context_rows=len(STUB_RISK_CONTEXT),
                **features,
            ),
        }

    # Find this invoice's row. One query row goes out, but matching on the
    # index column rather than trusting position keeps that assumption from
    # becoming a silent mis-scoring if a future call batches invoices.
    entry = next(
        (r for r in body["predictions"] if str(r.get("invoice_id")) == str(state["invoice_id"])),
        None,
    )
    candidates = [c for c in ((entry or {}).get(RISK_COLUMN) or []) if isinstance(c, dict)]

    if not candidates:
        error = (
            f"RPT-1.5 returned {len(body['predictions'])} prediction row(s) but none carried a "
            f"{RISK_COLUMN} for invoice {state['invoice_id']}."
        )
        return {
            "risk": None,
            "score_error": error,
            "trace": trace(
                "score",
                decision="no_prediction",
                reason=error,
                model=rpt.MODEL_NAME,
                context_rows=len(STUB_RISK_CONTEXT),
            ),
        }

    # Candidates come back most-confident first.
    distribution = {
        str(c.get("prediction")): round(float(c.get("confidence") or 0.0), 4) for c in candidates
    }
    band = str(candidates[0].get("prediction"))
    confidence = round(float(candidates[0].get("confidence") or 0.0), 4)

    # The score is the probability mass on HIGH, not the winner's confidence.
    # They are different questions: a confident LOW is a safe invoice, and
    # collapsing both into one float would report it as a risky one.
    risk_score = distribution.get(SCORE_BAND, 0.0)

    explanations = body.get("explanations") or {}
    column_scores = (explanations.get("top_column_scores") or [{}])[0]

    unexpected = band not in RISK_BANDS
    reason = (
        f"RPT-1.5 scored this {band} at {confidence:.2f} confidence "
        f"(P({SCORE_BAND})={risk_score:.2f}) from {len(STUB_RISK_CONTEXT)} context rows."
    )
    if unexpected:
        reason += f" Band is not one of {', '.join(RISK_BANDS)}; routing treats it as non-HIGH."
    if column_scores:
        drivers = ", ".join(
            f"{k}={v}" for k, v in sorted(column_scores.items(), key=lambda kv: -kv[1])
        )
        reason += f" Top drivers: {drivers}."

    risk = {
        "score": risk_score,
        "band": band,
        "confidence": confidence,
        "distribution": distribution,
        "model": rpt.MODEL_NAME,
        "explanations": {
            "top_column_scores": column_scores,
            "top_relevant_context_rows": (explanations.get("top_relevant_context_rows") or [[]])[0],
        },
    }
    return {
        "risk": risk,
        "score_error": None,
        "trace": trace(
            "score",
            decision=band,
            reason=reason,
            model=rpt.MODEL_NAME,
            score=risk_score,
            confidence=confidence,
            distribution=distribution,
            context_rows=len(STUB_RISK_CONTEXT),
            top_column_scores=column_scores,
            **features,
        ),
    }


def select_after_score(state: InvoiceState) -> str:
    """Conditional edge: never route on a risk band that was never computed."""
    return "human_review" if state["score_error"] else "route"


def route(state: InvoiceState) -> dict:
    """Decide straight-through vs human review.

    Three things send an invoice to a person: a validation issue, a control
    check that could not be run at all, and a HIGH risk band. The middle one
    is why an S/4HANA outage does not quietly start auto-posting invoices with
    unverified POs, and why a PO with no comparable total does not clear on
    the strength of the checks that did run -- see CONTROL_CHECKS.

    The rule stays when the stubs are replaced; only the thresholds feeding it
    become real. This node classifies -- the conditional edge below only reads
    the outcome, so the logic lives in one place.
    """
    issues = state["validation"]["issues"]
    skipped = state["validation"]["skipped"]
    band = state["risk"]["band"]

    triggers = []
    if issues:
        triggers.append(f"{len(issues)} validation issue(s): {', '.join(i['code'] for i in issues)}")

    # A control that could not be run is not an issue -- nothing is known
    # either way -- but it is also not clearance. Posting an invoice whose PO
    # was never verified because S/4HANA happened to be down is the silent
    # pass this flow exists to prevent, so it goes to a person instead.
    unverified = [s["check"] for s in skipped if s["check"] in CONTROL_CHECKS]
    if unverified:
        triggers.append(f"could not verify: {', '.join(unverified)}")

    if band == "HIGH":
        triggers.append(f"risk band {band}")

    outcome = "exception" if triggers else "clean"
    reason = "; ".join(triggers) if triggers else f"No validation issues and risk band {band}."

    decision = {"outcome": outcome, "reason": reason, "triggers": triggers}
    return {
        "decision": decision,
        "trace": trace("route", decision=outcome, reason=reason, trigger_count=len(triggers)),
    }


def select_outcome(state: InvoiceState) -> str:
    """Conditional edge: map the routing decision onto the next node."""
    return "human_review" if state["decision"]["outcome"] == "exception" else "straight_through"


def straight_through(state: InvoiceState) -> dict:
    """Terminal: post the invoice without human involvement.

    STUB: records the decision. The real node posts to S/4HANA and returns the
    resulting document number.
    """
    return {
        "trace": trace(
            "straight_through",
            decision="posted",
            reason="Clean invoice; would post to S/4HANA. No posting in the stub.",
            invoice_id=state["invoice_id"],
        )
    }


def human_review(state: InvoiceState) -> dict:
    """Terminal: hand the invoice to a person.

    Reached four ways: routed as an exception after scoring, or short-circuited
    from intake (no document), extract (no fields) or score (no risk band).
    Everything it reads is therefore optional, and the four are reported apart
    -- a queue entry that cannot say which stage gave up is not an audit trail.

    STUB: records the decision. The real node opens a review task carrying the
    issues and the risk band, and waits for a verdict.
    """
    decision = state.get("decision")
    validation = state.get("validation") or {"issues": []}
    risk = state.get("risk") or {}
    intake_error = state.get("intake_error")
    extraction_error = state.get("extraction_error")
    score_error = state.get("score_error")

    if decision:
        reason = f"Exception routed for review: {decision['reason']}"
    elif intake_error:
        reason = f"No usable document, nothing to extract from: {intake_error}"
    elif extraction_error:
        reason = f"Extraction failed, nothing to validate or score: {extraction_error}"
    else:
        reason = f"Risk scoring failed, not safe to route automatically: {score_error}"

    return {
        "trace": trace(
            "human_review",
            decision="queued",
            reason=reason,
            invoice_id=state["invoice_id"],
            issue_codes=[i["code"] for i in validation["issues"]],
            risk_band=risk.get("band"),
            intake_error=intake_error,
            extraction_error=extraction_error,
            score_error=score_error,
        )
    }
