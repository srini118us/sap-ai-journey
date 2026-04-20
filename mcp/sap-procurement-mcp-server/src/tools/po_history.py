"""PO history lookup tool.

Returns recent purchase orders filtered by vendor, cost center, and/or time window.
At least one filter is required to prevent accidental full-table scans.
Column names match Lab 52's PO_HISTORY schema.
"""
import os
import logging
from typing import Any, Optional

from src.hana import get_cursor

logger = logging.getLogger(__name__)


def get_po_history(
    vendor_id: Optional[str] = None,
    cost_center: Optional[str] = None,
    days_back: Optional[int] = None,
    max_results: int = 20,
) -> dict[str, Any]:
    """Retrieve recent purchase orders.

    At least one of vendor_id, cost_center, or days_back must be provided
    to scope the query. Results are ordered by PO_DATE descending.

    Args:
        vendor_id: Exact vendor ID (e.g., "V-10001") to filter by.
        cost_center: Cost center ID (e.g., "CC-4400") to filter by.
        days_back: Only include POs from the last N days (e.g., 90 for last quarter).
        max_results: Maximum rows to return (default 20, cap 100).

    Returns:
        Dict with:
            - filters: Echo of applied filters for trace
            - results: List of PO records
            - count: Number of results returned
            - error: Present if the query failed or no filter provided
    """
    # Enforce at least one filter — prevents full-table scans
    if not any([vendor_id, cost_center, days_back]):
        return {
            "error": "Provide at least one of: vendor_id, cost_center, or days_back"
        }

    max_results = min(max(max_results, 1), 100)
    schema = os.getenv("HANA_SCHEMA", "PROC_AI")

    # Build WHERE clause dynamically based on which filters are set
    where_parts = []
    params = []

    if vendor_id:
        where_parts.append("VENDOR_ID = ?")
        params.append(vendor_id.strip())

    if cost_center:
        where_parts.append("COST_CENTER = ?")
        params.append(cost_center.strip().upper())

    if days_back is not None and days_back > 0:
        where_parts.append("PO_DATE >= ADD_DAYS(CURRENT_DATE, ?)")
        params.append(-days_back)

    where_sql = " AND ".join(where_parts)

    sql = f"""
        SELECT
            PO_ID,
            VENDOR_ID,
            CATEGORY,
            DESCRIPTION,
            AMOUNT,
            CURRENCY,
            COST_CENTER,
            PO_DATE,
            STATUS,
            APPROVED_BY
        FROM {schema}.PO_HISTORY
        WHERE {where_sql}
        ORDER BY PO_DATE DESC
        LIMIT ?
    """
    params.append(max_results)

    logger.info(
        "[get_po_history] vendor_id=%s cost_center=%s days_back=%s max=%d",
        vendor_id, cost_center, days_back, max_results,
    )

    try:
        with get_cursor() as cursor:
            cursor.execute(sql, tuple(params))
            rows = cursor.fetchall()
    except Exception as exc:
        logger.exception("[get_po_history] Query failed")
        return {"error": f"HANA query failed: {exc}"}

    results = [
        {
            "po_id": row[0],
            "vendor_id": row[1],
            "category": row[2],
            "description": row[3],
            "amount": float(row[4]) if row[4] is not None else 0.0,
            "currency": row[5],
            "cost_center": row[6],
            "po_date": str(row[7]) if row[7] else None,
            "status": row[8],
            "approved_by": row[9],
        }
        for row in rows
    ]

    logger.info("[get_po_history] Returned %d POs", len(results))
    return {
        "filters": {
            "vendor_id": vendor_id,
            "cost_center": cost_center,
            "days_back": days_back,
        },
        "results": results,
        "count": len(results),
    }
