"""Cost center budget status tool.

Reads pre-computed SPEND_YTD from COST_CENTER_MASTER (matches Lab 52's pattern).
No ACDOCA join needed — Lab 52 stores the rollup directly on the master row.
"""
import os
import logging
from typing import Any

from src.hana import get_cursor

logger = logging.getLogger(__name__)

# Utilization warning thresholds (informational only; policy rules live in POLICY_CHUNKS)
WARN_THRESHOLD = 0.85
CRITICAL_THRESHOLD = 0.95


def get_cost_center_status(cost_center_id: str) -> dict[str, Any]:
    """Retrieve budget utilization for a cost center.

    Args:
        cost_center_id: Cost center identifier (e.g., "CC-4400").

    Returns:
        Dict with budget details and utilization status flags.
    """
    if not cost_center_id or not cost_center_id.strip():
        return {"error": "cost_center_id is required"}

    cost_center_id = cost_center_id.strip().upper()
    schema = os.getenv("HANA_SCHEMA", "PROC_AI")

    logger.info("[get_cost_center_status] cost_center_id=%s", cost_center_id)

    # Note: column is COST_CENTER (no _ID suffix) per Lab 52 schema
    sql = f"""
        SELECT
            COST_CENTER,
            CC_NAME,
            MANAGER,
            DEPARTMENT,
            BUDGET_ANNUAL,
            BUDGET_YTD,
            SPEND_YTD,
            STATUS
        FROM {schema}.COST_CENTER_MASTER
        WHERE COST_CENTER = ?
    """

    try:
        with get_cursor() as cursor:
            cursor.execute(sql, (cost_center_id,))
            row = cursor.fetchone()
    except Exception as exc:
        logger.exception("[get_cost_center_status] Query failed")
        return {"error": f"HANA query failed: {exc}"}

    if not row:
        return {"error": f"Cost center {cost_center_id!r} not found"}

    budget_annual = float(row[4]) if row[4] is not None else 0.0
    budget_ytd = float(row[5]) if row[5] is not None else 0.0
    spend_ytd = float(row[6]) if row[6] is not None else 0.0
    remaining = budget_annual - spend_ytd
    utilization = (spend_ytd / budget_annual) if budget_annual > 0 else 0.0

    # Status flag based on utilization
    if utilization >= CRITICAL_THRESHOLD:
        utilization_flag = "CRITICAL"
    elif utilization >= WARN_THRESHOLD:
        utilization_flag = "WARNING"
    else:
        utilization_flag = "OK"

    result = {
        "cost_center": row[0],
        "cc_name": row[1],
        "manager": row[2],
        "department": row[3],
        "budget_annual": budget_annual,
        "budget_ytd": budget_ytd,
        "spend_ytd": spend_ytd,
        "remaining_budget": remaining,
        "utilization_pct": round(utilization * 100, 2),
        "utilization_flag": utilization_flag,
        "status": row[7],
    }

    logger.info(
        "[get_cost_center_status] %s: %.1f%% utilized (%s)",
        cost_center_id,
        result["utilization_pct"],
        utilization_flag,
    )
    return result
