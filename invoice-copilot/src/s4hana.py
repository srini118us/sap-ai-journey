"""SAP S/4HANA purchase-order lookup over OData.

The only module in this project that talks to S/4HANA, so there is one place
to change when the service or the credential pattern moves -- the same role
`genai.py` plays for GenAI Hub, `rpt.py` for RPT-1.5, and
`vertex_secondopinion.py` for the cross-cloud call.

Two GETs against API_PURCHASEORDER_PROCESS_SRV, because the purchase order
header carries no total:

    GET .../A_PurchaseOrder('<po>')?$format=json
        -> d.Supplier, d.AddressName, d.DocumentCurrency
    GET .../A_PurchaseOrder('<po>')/to_PurchaseOrderItem?$format=json
        -> d.results[], each with NetPriceAmount and OrderQuantity

The PO total is the sum of NetPriceAmount * OrderQuantity across the items.

Transport and auth only. No comparison logic and no trace entries live here --
those belong to the caller, the same way `genai.py` leaves parsing to the node.

Credentials come from .env: S4_BASE_URL, S4_USER, S4_PASSWORD. S4_PASSWORD is
a secret. It is handed to `requests` as basic auth and goes nowhere else --
not into a URL, not into a log line, and not into the errors raised here,
which report HTTP status codes and exception type names only, the same
discipline `rpt.py` applies to its token requests.
"""

import os
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import quote

import requests
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

SERVICE_PATH = "/sap/opu/odata/sap/API_PURCHASEORDER_PROCESS_SRV"
ENTITY_SET = "A_PurchaseOrder"
ITEMS_NAVIGATION = "to_PurchaseOrderItem"

REQUEST_TIMEOUT_SECONDS = 60

# A purchase order with more item pages than this is not something this flow
# is prepared to sum. The cap exists so a paging bug cannot spin forever, and
# hitting it raises rather than returning a partial total -- a PO total that
# silently omits lines would surface as a false amount_mismatch on a perfectly
# good invoice, which is worse than reporting that the lookup failed.
MAX_ITEM_PAGES = 20

# The PO reference is read off a supplier's document by a language model, so
# it is untrusted input, and it goes into an OData key predicate. Anything
# that is not plausibly a purchase order number never reaches the service:
# see fetch_purchase_order, which reports it as "no such PO" rather than
# building a request around it.
_PO_REFERENCE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_\-/]{0,39}$")


class S4HANAError(RuntimeError):
    """The purchase order could not be looked up.

    Raised for missing configuration, auth failures, network errors, non-2xx
    responses other than 404, and unparseable bodies alike -- callers treat
    them the same way: trace it, record the PO check as one that could not
    run, and never report an invoice as clean on the strength of a check that
    never happened.

    A purchase order that genuinely does not exist is NOT this: that comes
    back as {"found": False}. See fetch_purchase_order().
    """


_session = None


def _http() -> requests.Session:
    """One session for the whole run, so repeated lookups reuse the TLS
    connection instead of shaking hands once per invoice."""
    global _session
    if _session is None:
        _session = requests.Session()
    return _session


def _require(name: str) -> str:
    """Read a required setting, naming the missing key rather than its value."""
    value = os.getenv(name)
    if not value:
        raise S4HANAError(f"{name} is not set; add it to .env (see .env.example).")
    return value


def base_url() -> str:
    """The S/4HANA host. Environment-specific, and a production system
    identifier, so it is read from .env rather than hardcoded."""
    return _require("S4_BASE_URL").rstrip("/")


def _credentials() -> tuple[str, str]:
    """Basic-auth pair. The password is returned for `requests` to put in an
    Authorization header and is never rendered anywhere else."""
    return _require("S4_USER"), _require("S4_PASSWORD")


def _get(url: str, *, allow_missing: bool = False):
    """GET one OData URL and return the parsed contents of its `d` envelope.

    Returns None on 404 when `allow_missing` is set: "there is no such
    purchase order" is an answer from S/4HANA, not a failure to reach it, and
    the caller turns it into a validation issue rather than a skipped check.
    Every other non-200 raises.
    """
    try:
        response = _http().get(
            url,
            auth=_credentials(),
            headers={"Accept": "application/json"},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except requests.RequestException as e:
        raise S4HANAError(f"Could not reach S/4HANA: {type(e).__name__}.") from e

    if allow_missing and response.status_code == 404:
        return None

    if response.status_code in (401, 403):
        # Status only, and no echo of the request: the Authorization header on
        # it is derived from S4_PASSWORD.
        raise S4HANAError(
            f"S/4HANA refused the credentials with HTTP {response.status_code}; "
            "check S4_USER and S4_PASSWORD, and that the user is authorized for "
            "API_PURCHASEORDER_PROCESS_SRV."
        )

    if response.status_code != 200:
        raise S4HANAError(f"S/4HANA returned HTTP {response.status_code}: {response.text[:200]}")

    try:
        body = response.json()
    except ValueError as e:
        raise S4HANAError(f"S/4HANA response was not JSON: {type(e).__name__}.") from e

    if not isinstance(body, dict) or "d" not in body:
        raise S4HANAError(
            f"S/4HANA returned {type(body).__name__} with no `d` envelope; "
            "expected an OData JSON document."
        )

    return body["d"]


def _decimal(value, field: str, where: str) -> Decimal:
    """Coerce one OData number.

    OData v2 renders Edm.Decimal as a JSON *string* -- NetPriceAmount arrives
    as "40.86", not 40.86. Decimal parses those exactly; float would turn
    83 * 40.86 into 3391.3799999999997 and make a cent-level comparison a
    coin toss.
    """
    if value is None or value == "":
        raise S4HANAError(f"{where} carries no {field}.")
    try:
        return Decimal(str(value).strip())
    except (InvalidOperation, ValueError) as e:
        raise S4HANAError(
            f"{where} has a {field} that is not a number ({type(e).__name__})."
        ) from e


def _order_total(po_reference: str, encoded: str):
    """Sum NetPriceAmount * OrderQuantity across every item of one PO.

    Returns (total, item_count). `total` is None when the PO carries no items
    at all -- a PO with no lines has no total, which is a different fact from
    a total of zero, and the caller skips the amount comparison rather than
    comparing an invoice against 0.00.

    NOTE: this multiplies the net price by the ordered quantity directly. SAP
    also carries NetPriceQuantity, the price unit -- a net price quoted "per
    100 pieces" would need dividing by it. Every item in play here is priced
    per single unit; a PO that is not would need this formula revisited.
    """
    url = f"{base_url()}{SERVICE_PATH}/{ENTITY_SET}('{encoded}')/{ITEMS_NAVIGATION}?$format=json"

    total = Decimal("0")
    count = 0

    for _page in range(MAX_ITEM_PAGES):
        payload = _get(url)
        results = payload.get("results") if isinstance(payload, dict) else payload
        if not isinstance(results, list):
            raise S4HANAError(
                f"PO {po_reference} item response carried no results list "
                f"(got {type(results).__name__})."
            )

        for item in results:
            if not isinstance(item, dict):
                raise S4HANAError(
                    f"PO {po_reference} returned an item of type {type(item).__name__}, "
                    "expected an object."
                )
            where = f"PO {po_reference} item {item.get('PurchaseOrderItem', count + 1)}"
            price = _decimal(item.get("NetPriceAmount"), "NetPriceAmount", where)
            quantity = _decimal(item.get("OrderQuantity"), "OrderQuantity", where)
            total += price * quantity
            count += 1

        next_url = payload.get("__next") if isinstance(payload, dict) else None
        if not next_url:
            # Money, rounded once at the end rather than once per item.
            return (float(round(total, 2)) if count else None), count
        url = next_url

    raise S4HANAError(
        f"PO {po_reference} has more than {MAX_ITEM_PAGES} pages of items; refusing to "
        "report a total that may be missing lines."
    )


def fetch_purchase_order(po_reference) -> dict:
    """Look one purchase order up in S/4HANA.

    Returns, without raising, for a PO that simply is not there:

        {"found": bool, "po": dict | None, "reason": str | None}

    `found: False` is a *return value*, not an error. It means S/4HANA
    answered, and the answer is that no such purchase order exists -- which
    makes the invoice citing it suspicious, and is the caller's `po_not_found`
    issue. That is a different fact from "S/4HANA could not be reached", which
    says nothing about the invoice at all and raises S4HANAError instead.
    Collapsing the two would either fail good invoices during an outage or
    quietly clear invoices citing POs nobody ever checked.

    `po` carries the keys the validate node compares on:

        {"po_reference", "vendor", "supplier", "amount", "currency", "item_count"}

    `amount` is None when the PO carries no items, and `vendor` is empty when
    the PO carries no address name. The caller skips those comparisons rather
    than inventing a verdict for them.
    """
    if not isinstance(po_reference, str) or not _PO_REFERENCE_RE.match(po_reference.strip()):
        # Not a request S/4HANA could answer, so it is not sent. An invoice
        # citing something that cannot be a PO number is in exactly the same
        # position as one citing a PO number that does not exist.
        shown = po_reference if isinstance(po_reference, str) else type(po_reference).__name__
        return {
            "found": False,
            "po": None,
            "reason": f"{shown!r} is not a usable purchase order reference; it was not looked up.",
        }

    po_reference = po_reference.strip()
    # Doubling is how OData escapes a quote inside a key predicate; quoting
    # then keeps the whole predicate a single safe path segment.
    encoded = quote(po_reference.replace("'", "''"), safe="")

    header = _get(
        f"{base_url()}{SERVICE_PATH}/{ENTITY_SET}('{encoded}')?$format=json",
        allow_missing=True,
    )

    if header is None:
        return {
            "found": False,
            "po": None,
            "reason": f"No purchase order {po_reference} exists in S/4HANA.",
        }

    if not isinstance(header, dict):
        raise S4HANAError(
            f"PO {po_reference} came back as {type(header).__name__}, expected an object."
        )

    total, item_count = _order_total(po_reference, encoded)

    return {
        "found": True,
        "reason": None,
        "po": {
            "po_reference": header.get("PurchaseOrder") or po_reference,
            "vendor": (header.get("AddressName") or "").strip(),
            "supplier": (header.get("Supplier") or "").strip(),
            "amount": total,
            "currency": (header.get("DocumentCurrency") or "").strip(),
            "item_count": item_count,
        },
    }
