"""Spending summary tool.

Aggregates PO spending by vendor and/or cost center over a trailing time window.
Returns count, total, average, min, max for approved/closed POs.
"""
import os
import logging
from typing import Any, Optional

from src.hana import get_cursor

logger = logging.getLogger(__name__)


def get_spending_summary(
    vendor_id: Optional[str] = None,
    cost_center: Optional[str] = None,
    days_back: int = 365,
) -> dict[str, Any]:
    """Aggregate spending summary for a vendor, cost center, or both.

    Counts only APPROVED and CLOSED POs (excludes DRAFT, PENDING, CANCELLED)
    to reflect actual committed spend, matching Lab 52's pattern.

    Args:
        vendor_id: Filter by specific vendor (optional).
        cost_center: Filter by specific cost center (optional).
        days_back: Trailing window in days (default 365 = 1 year).

    Returns:
        Dict with po_count, total_spend, avg_po_amount, min_po_amount, max_po_amount.
        Returns zero-valued summary if no POs match (not an error).
    """
    if days_back <= 0:
        return {"error": "days_back must be positive"}

    schema = os.getenv("HANA_SCHEMA", "PROC_AI")

    # Build WHERE dynamically; always include the time window + status filter
    where_parts = [
        "PO_DATE >= ADD_DAYS(CURRENT_DATE, ?)",
        "STATUS IN ('Approved', 'Closed')",
    ]
    params = [-days_back]

    if vendor_id:
        where_parts.append("VENDOR_ID = ?")
        params.append(vendor_id.strip())

    if cost_center:
        where_parts.append("COST_CENTER = ?")
        params.append(cost_center.strip().upper())

    where_sql = " AND ".join(where_parts)

    sql = f"""
        SELECT
            COUNT(*)                       AS PO_COUNT,
            COALESCE(SUM(AMOUNT), 0)       AS TOTAL_SPEND,
            COALESCE(AVG(AMOUNT), 0)       AS AVG_PO,
            COALESCE(MIN(AMOUNT), 0)       AS MIN_PO,
            COALESCE(MAX(AMOUNT), 0)       AS MAX_PO
        FROM {schema}.PO_HISTORY
        WHERE {where_sql}
    """

    logger.info(
        "[get_spending_summary] vendor_id=%s cost_center=%s days_back=%d",
        vendor_id, cost_center, days_back,
    )

    try:
        with get_cursor() as cursor:
            cursor.execute(sql, tuple(params))
            row = cursor.fetchone()
    except Exception as exc:
        logger.exception("[get_spending_summary] Query failed")
        return {"error": f"HANA query failed: {exc}"}

    po_count = int(row[0]) if row[0] else 0
    total = float(row[1])
    avg = float(row[2])
    min_po = float(row[3])
    max_po = float(row[4])

    result = {
        "filters": {
            "vendor_id": vendor_id,
            "cost_center": cost_center,
            "days_back": days_back,
        },
        "po_count": po_count,
        "total_spend": total,
        "avg_po_amount": round(avg, 2),
        "min_po_amount": min_po,
        "max_po_amount": max_po,
        "status_filter": "Approved or Closed only",
    }

    logger.info(
        "[get_spending_summary] %d POs, total=%.2f, avg=%.2f",
        po_count, total, avg,
    )
    return result
