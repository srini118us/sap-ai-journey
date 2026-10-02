"""SAP MCP Server
Exposes live S/4HANA purchase order data as MCP tools over the standard
API_PURCHASEORDER_PROCESS_SRV OData service.

Tools:
  get_purchase_orders(top, supplier)   - list POs, optionally filtered by supplier
  get_purchase_order(po_number)        - one PO with its line items
  get_vendor_summary(supplier)         - PO count and profile for one supplier
  classify_purchase_order(po_number)   - direct vs indirect classification via PO type

Configuration comes from environment variables only (never hardcode credentials):
  SAP_BASE_URL   e.g. https://mtsapserver6g.themdlabs.com:44300
  SAP_USER       communication user
  SAP_PASSWORD   its password
  VERIFY_SSL     "true" or "false" (lab systems usually need false)
  DIRECT_PO_TYPES  comma separated document types treated as direct (default "NB")

Run modes:
  python sap_mcp_server.py --test    quick connectivity test, no MCP involved
  python sap_mcp_server.py           starts the MCP server on stdio (for ADK / clients)
"""

import json
import os
import re
import sys

import httpx
from mcp.server.fastmcp import FastMCP

SAP_BASE_URL = os.environ.get("SAP_BASE_URL", "").rstrip("/")
SAP_USER = os.environ.get("SAP_USER", "")
SAP_PASSWORD = os.environ.get("SAP_PASSWORD", "")
VERIFY_SSL = os.environ.get("VERIFY_SSL", "false").lower() == "true"
DIRECT_PO_TYPES = {
    t.strip() for t in os.environ.get("DIRECT_PO_TYPES", "NB").split(",") if t.strip()
}

SERVICE = "/sap/opu/odata/sap/API_PURCHASEORDER_PROCESS_SRV"

HEADER_FIELDS = [
    "PurchaseOrder", "PurchaseOrderType", "Supplier", "AddressName",
    "CompanyCode", "PurchasingOrganization", "PurchasingGroup",
    "DocumentCurrency", "PaymentTerms", "CreationDate",
]
ITEM_FIELDS = [
    "PurchaseOrderItem", "Material", "PurchaseOrderItemText",
    "OrderQuantity", "PurchaseOrderQuantityUnit", "NetPriceAmount",
    "DocumentCurrency", "Plant",
]

mcp = FastMCP("sap-purchase-orders")


def _client(timeout: float = 30.0) -> httpx.Client:
    if not (SAP_BASE_URL and SAP_USER and SAP_PASSWORD):
        raise RuntimeError(
            "Missing configuration: set SAP_BASE_URL, SAP_USER and SAP_PASSWORD "
            "environment variables before starting the server."
        )
    return httpx.Client(
        base_url=SAP_BASE_URL,
        auth=(SAP_USER, SAP_PASSWORD),
        verify=VERIFY_SSL,
        timeout=timeout,
    )


def _odata(path: str, params: dict) -> dict:
    """GET an OData v2 path and return the payload under d."""
    params = {**params, "$format": "json"}
    with _client() as client:
        resp = client.get(f"{SERVICE}{path}", params=params)
        resp.raise_for_status()
        return resp.json()["d"]


def _odata_count(path: str, params: dict) -> int:
    """GET an OData v2 $count endpoint, which returns plain text."""
    with _client() as client:
        resp = client.get(f"{SERVICE}{path}/$count", params=params)
        resp.raise_for_status()
        return int(resp.text.strip())


def _iso_date(value):
    """Convert OData v2 /Date(ms)/ strings to YYYY-MM-DD."""
    if isinstance(value, str):
        match = re.match(r"/Date\((\d+)", value)
        if match:
            from datetime import datetime, timezone
            ms = int(match.group(1))
            return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).date().isoformat()
    return value


def _slim(record: dict, fields: list) -> dict:
    out = {}
    for key in fields:
        val = record.get(key)
        if key.endswith("Date"):
            val = _iso_date(val)
        out[key] = val
    return out


@mcp.tool()
def get_purchase_orders(top: int = 10, supplier: str = "") -> str:
    """List purchase orders from the live SAP S/4HANA system.

    Args:
        top: maximum number of orders to return (1 to 50).
        supplier: optional SAP supplier ID to filter by, e.g. "17300001" or "USSU-VSF01".
    """
    params = {"$top": max(1, min(int(top), 50)), "$select": ",".join(HEADER_FIELDS)}
    if supplier:
        params["$filter"] = f"Supplier eq '{supplier}'"
    data = _odata("/A_PurchaseOrder", params)
    rows = [_slim(r, HEADER_FIELDS) for r in data.get("results", [])]
    return json.dumps({"count_returned": len(rows), "purchase_orders": rows})


@mcp.tool()
def get_purchase_order(po_number: str) -> str:
    """Get one purchase order with its line items from the live SAP S/4HANA system.

    Args:
        po_number: the purchase order number, e.g. "4500000001".
    """
    data = _odata(
        f"/A_PurchaseOrder('{po_number}')",
        {"$expand": "to_PurchaseOrderItem"},
    )
    header = _slim(data, HEADER_FIELDS)
    items_raw = data.get("to_PurchaseOrderItem", {}).get("results", [])
    header["items"] = [_slim(i, ITEM_FIELDS) for i in items_raw]
    header["item_count"] = len(header["items"])
    return json.dumps(header)


@mcp.tool()
def get_vendor_summary(supplier: str) -> str:
    """Summarize one supplier: total PO count in SAP, document types used, and recent orders.

    Args:
        supplier: the SAP supplier ID, e.g. "17300001" or "USSU-VSF01".
    """
    total = _odata_count(
        "/A_PurchaseOrder", {"$filter": f"Supplier eq '{supplier}'"}
    )
    data = _odata(
        "/A_PurchaseOrder",
        {
            "$filter": f"Supplier eq '{supplier}'",
            "$select": "PurchaseOrder,PurchaseOrderType,AddressName,CreationDate",
            "$top": 50,
        },
    )
    rows = data.get("results", [])
    types = {}
    for r in rows:
        types[r.get("PurchaseOrderType", "?")] = types.get(r.get("PurchaseOrderType", "?"), 0) + 1
    summary = {
        "supplier": supplier,
        "supplier_name": rows[0].get("AddressName") if rows else None,
        "total_purchase_orders": total,
        "document_types_in_sample": types,
        "sample_size": len(rows),
        "recent_orders": [r.get("PurchaseOrder") for r in rows[:5]],
        "note": "Counts come live from S/4HANA via OData; sample limited to 50 orders.",
    }
    return json.dumps(summary)


@mcp.tool()
def classify_purchase_order(po_number: str) -> str:
    """Classify a purchase order as direct or indirect procurement, the same
    lookup an invoice routing workflow performs before deciding the target system.

    Args:
        po_number: the purchase order number, e.g. "4500000001".
    """
    data = _odata(
        f"/A_PurchaseOrder('{po_number}')",
        {"$select": "PurchaseOrder,PurchaseOrderType,Supplier,AddressName"},
    )
    po_type = data.get("PurchaseOrderType", "")
    classification = "direct" if po_type in DIRECT_PO_TYPES else "indirect"
    result = {
        "purchase_order": data.get("PurchaseOrder"),
        "document_type": po_type,
        "supplier": data.get("Supplier"),
        "supplier_name": data.get("AddressName"),
        "classification": classification,
        "rule": (
            f"document types {sorted(DIRECT_PO_TYPES)} are treated as direct; "
            "the mapping is configurable per landscape (env DIRECT_PO_TYPES)"
        ),
    }
    return json.dumps(result)


SO_SERVICE = "/sap/opu/odata/sap/API_SALES_ORDER_SRV"
SALES_ORG = os.environ.get("SALES_ORG", "1710")
DIST_CHANNEL = os.environ.get("DIST_CHANNEL", "10")
DIVISION = os.environ.get("DIVISION", "00")
SO_TYPE = os.environ.get("SO_TYPE", "OR")


def _odata_at(service: str, path: str, params: dict) -> dict:
    params = {**params, "$format": "json"}
    with _client() as client:
        resp = client.get(f"{service}{path}", params=params)
        resp.raise_for_status()
        return resp.json()["d"]


def _post_odata(service: str, path: str, payload: dict) -> dict:
    """OData v2 write: fetch CSRF token on a GET, then POST with token and cookies.
    Uses a long timeout because the first write on a cold system can be slow."""
    with _client(timeout=120.0) as client:
        head = client.get(f"{service}/$metadata", headers={"X-CSRF-Token": "Fetch"})
        token = head.headers.get("x-csrf-token")
        if not token:
            raise RuntimeError("Could not fetch a CSRF token from the SAP gateway.")
        resp = client.post(
            f"{service}{path}",
            json=payload,
            headers={"X-CSRF-Token": token, "Accept": "application/json"},
        )
        if resp.status_code >= 400:
            raise RuntimeError(
                f"SAP rejected the posting ({resp.status_code}): {resp.text[:800]}"
            )
        return resp.json()["d"]


@mcp.tool()
def create_sales_order(customer_po_number: str, sold_to_party: str,
                       material: str, quantity: int) -> str:
    """WRITE OPERATION: creates a REAL Sales Order in the live S/4HANA system.
    Call this ONLY after the user has explicitly approved the proposed order in
    this conversation. Never call it speculatively. Safe against retries: if an
    order for this customer PO and customer already exists, it is returned
    instead of creating a duplicate.

    Args:
        customer_po_number: the customer's own PO number from their document.
        sold_to_party: SAP customer number, e.g. "17100009".
        material: SAP material number, e.g. "TG11".
        quantity: order quantity in base unit.
    """
    existing = _odata_at(
        SO_SERVICE, "/A_SalesOrder",
        {"$filter": (f"PurchaseOrderByCustomer eq '{customer_po_number}' "
                     f"and SoldToParty eq '{sold_to_party}'"),
         "$select": "SalesOrder,SoldToParty,PurchaseOrderByCustomer,"
                    "TotalNetAmount,TransactionCurrency",
         "$top": 2},
    ).get("results", [])
    if existing:
        row = existing[0]
        return json.dumps({
            "already_exists": True,
            "sales_order": row.get("SalesOrder"),
            "sold_to_party": row.get("SoldToParty"),
            "customer_po": row.get("PurchaseOrderByCustomer"),
            "total_net_amount": str(row.get("TotalNetAmount")),
            "currency": row.get("TransactionCurrency"),
            "note": ("Idempotency guard: an order for this customer PO already "
                     "exists in S/4HANA. No new order was created."),
        })
    payload = {
        "SalesOrderType": SO_TYPE,
        "SalesOrganization": SALES_ORG,
        "DistributionChannel": DIST_CHANNEL,
        "OrganizationDivision": DIVISION,
        "SoldToParty": sold_to_party,
        "PurchaseOrderByCustomer": customer_po_number,
        "to_Item": [
            {"Material": material, "RequestedQuantity": str(int(quantity))}
        ],
    }
    data = _post_odata(SO_SERVICE, "/A_SalesOrder", payload)
    return json.dumps({
        "created_sales_order": data.get("SalesOrder"),
        "sold_to_party": data.get("SoldToParty"),
        "customer_po": data.get("PurchaseOrderByCustomer"),
        "total_net_amount": str(data.get("TotalNetAmount")),
        "currency": data.get("TransactionCurrency"),
        "note": "A real Sales Order was created in S/4HANA.",
    })


@mcp.tool()
def get_sales_order(so_number: str) -> str:
    """Read one Sales Order with its items from the live S/4HANA system,
    typically to verify a just created order.

    Args:
        so_number: the Sales Order number, e.g. "1234".
    """
    data = _odata_at(
        SO_SERVICE,
        f"/A_SalesOrder('{so_number}')",
        {"$expand": "to_Item",
         "$select": "SalesOrder,SalesOrderType,SoldToParty,PurchaseOrderByCustomer,"
                    "TotalNetAmount,TransactionCurrency,SalesOrganization,"
                    "to_Item/Material,to_Item/RequestedQuantity,to_Item/NetAmount"},
    )
    items = [
        {"Material": i.get("Material"),
         "RequestedQuantity": i.get("RequestedQuantity"),
         "NetAmount": str(i.get("NetAmount"))}
        for i in data.get("to_Item", {}).get("results", [])
    ]
    return json.dumps({
        "sales_order": data.get("SalesOrder"),
        "type": data.get("SalesOrderType"),
        "sold_to_party": data.get("SoldToParty"),
        "customer_po": data.get("PurchaseOrderByCustomer"),
        "total_net_amount": str(data.get("TotalNetAmount")),
        "currency": data.get("TransactionCurrency"),
        "items": items,
    })


def _selftest() -> None:
    print(f"Base URL : {SAP_BASE_URL}")
    print(f"User     : {SAP_USER}")
    print(f"VerifySSL: {VERIFY_SSL}")
    print("-" * 60)
    print("1) get_purchase_orders(top=3)")
    print(get_purchase_orders(3), "\n")
    print("2) get_purchase_order('4500000001')")
    print(get_purchase_order("4500000001"), "\n")
    print("3) get_vendor_summary('17300001')")
    print(get_vendor_summary("17300001"), "\n")
    print("4) classify_purchase_order('4500000029')  # the ENB one")
    print(classify_purchase_order("4500000029"), "\n")
    print("All four tools returned. The server is ready for MCP clients.")


if __name__ == "__main__":
    if "--test" in sys.argv:
        _selftest()
    else:
        mcp.run()
