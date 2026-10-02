"""Vendor information lookup tool.

Returns vendor master data plus year-to-date spend from PO_HISTORY.
Column names match Lab 52's actual schema.
"""
import os
import logging
from typing import Any, Optional

from src.hana import get_cursor

logger = logging.getLogger(__name__)


def get_vendor_info(
    vendor_id: Optional[str] = None,
    vendor_name: Optional[str] = None,
) -> dict[str, Any]:
    """Retrieve vendor master data and YTD spending.

    Args:
        vendor_id: Exact vendor ID (e.g., "V-10042"). Preferred when known.
        vendor_name: Partial vendor name (e.g., "ACME"). Used when vendor_id is missing.

    Returns:
        Dict with vendor details, or error if not found/ambiguous.
    """
    if not vendor_id and not vendor_name:
        return {"error": "Provide either vendor_id or vendor_name"}

    schema = os.getenv("HANA_SCHEMA", "PROC_AI")

    # Step 1: Find the vendor row
    if vendor_id:
        where_clause = "VENDOR_ID = ?"
        param = vendor_id.strip()
        logger.info("[get_vendor_info] Lookup by vendor_id=%s", param)
    else:
        where_clause = "UPPER(VENDOR_NAME) LIKE UPPER(?)"
        param = f"%{vendor_name.strip()}%"
        logger.info("[get_vendor_info] Lookup by vendor_name=%s", param)

    vendor_sql = f"""
        SELECT
            VENDOR_ID,
            VENDOR_NAME,
            CATEGORY,
            TIER,
            STATUS,
            COUNTRY,
            PAYMENT_TERMS,
            RISK_SCORE,
            ONBOARDED_AT
        FROM {schema}.VENDOR_MASTER
        WHERE {where_clause}
        ORDER BY LENGTH(VENDOR_NAME) ASC
    """

    try:
        with get_cursor() as cursor:
            cursor.execute(vendor_sql, (param,))
            rows = cursor.fetchall()
    except Exception as exc:
        logger.exception("[get_vendor_info] Vendor lookup failed")
        return {"error": f"HANA query failed: {exc}"}

    if not rows:
        return {"error": f"No vendor found matching {param!r}"}
    if len(rows) > 1 and vendor_name:
        # Ambiguous name match — return candidates for caller to disambiguate
        return {
            "error": "Multiple vendors match; refine vendor_name or use vendor_id",
            "candidates": [
                {"vendor_id": r[0], "vendor_name": r[1], "status": r[4]}
                for r in rows[:10]
            ],
        }

    row = rows[0]
    resolved_vendor_id = row[0]

    vendor = {
        "vendor_id": row[0],
        "vendor_name": row[1],
        "category": row[2],
        "tier": row[3],
        "status": row[4],
        "country": row[5],
        "payment_terms": row[6],
        "risk_score": float(row[7]) if row[7] is not None else None,
        "onboarded_at": str(row[8]) if row[8] else None,
    }

    # Step 2: Compute YTD spend from PO_HISTORY
    # Use APPROVED/CLOSED POs only (same filter as Lab 52's spend summary)
    spend_sql = f"""
        SELECT
            COUNT(*) AS PO_COUNT,
            COALESCE(SUM(AMOUNT), 0) AS TOTAL_SPEND
        FROM {schema}.PO_HISTORY
        WHERE VENDOR_ID = ?
          AND YEAR(PO_DATE) = YEAR(CURRENT_DATE)
          AND STATUS IN ('Approved', 'Closed')
    """

    try:
        with get_cursor() as cursor:
            cursor.execute(spend_sql, (resolved_vendor_id,))
            spend_row = cursor.fetchone()
            vendor["ytd_po_count"] = int(spend_row[0])
            vendor["ytd_spend"] = float(spend_row[1])
    except Exception as exc:
        logger.warning("[get_vendor_info] YTD spend query failed: %s", exc)
        vendor["ytd_po_count"] = None
        vendor["ytd_spend"] = None

    logger.info("[get_vendor_info] Resolved vendor %s", resolved_vendor_id)
    return vendor
