"""Approval policy check tool.

RAG-based: given PO details (amount, vendor, cost center), constructs a targeted
policy query and returns the most relevant approval policy chunks, plus structured
context signals the agent can reason over.

This is deliberately NOT rule-based. Approval tiers live in the policy documents
themselves — hardcoding them in Python would create drift when policies change.
Instead, we retrieve the relevant policy passages and let the Joule agent interpret them.
"""
import os
import logging
from typing import Any, Optional

from src.tools.policies import search_policies
from src.tools.vendors import get_vendor_info
from src.tools.cost_centers import get_cost_center_status

logger = logging.getLogger(__name__)


def check_approval_policy(
    amount: float,
    vendor_id: Optional[str] = None,
    cost_center: Optional[str] = None,
    category: Optional[str] = None,
) -> dict[str, Any]:
    """Check approval policy for a proposed purchase order.

    Retrieves (a) the most relevant approval policy passages for the PO's
    characteristics, (b) structured context signals (vendor tier, CC utilization)
    that affect approval decisions. The agent uses this to reason about whether
    the PO should be approved, escalated, or rejected.

    Args:
        amount: PO amount in USD (or contract currency).
        vendor_id: Vendor ID (e.g., "V-10001"). If provided, vendor risk/tier is included.
        cost_center: Cost center (e.g., "CC-4400"). If provided, budget utilization is included.
        category: Optional category hint ("IT Services", "Consulting", "Capital", etc.)
                  to refine the policy search.

    Returns:
        Dict with:
            - amount: Echo
            - policy_context: Relevant policy chunks (RAG retrieval)
            - vendor_context: Vendor info if vendor_id provided
            - cost_center_context: CC status if cost_center provided
            - signals: Structured flags the agent can quickly reference
            - error: Present if retrieval failed
    """
    if amount is None or amount < 0:
        return {"error": "amount must be a non-negative number"}

    logger.info(
        "[check_approval_policy] amount=%.2f vendor=%s cc=%s category=%s",
        amount, vendor_id, cost_center, category,
    )

    # Build a policy query from the PO characteristics
    # Use amount magnitude + category to target the most relevant policy chunks
    query_parts = []
    if category:
        query_parts.append(category)
    query_parts.append(f"approval limit {_amount_tier(amount)}")
    query_parts.append("procurement approval authority")
    policy_query = " ".join(query_parts)

    # Fan out to retrieve policy + contextual data
    policy_result = search_policies(query=policy_query, max_results=4)

    vendor_context = None
    if vendor_id:
        vendor_context = get_vendor_info(vendor_id=vendor_id)

    cost_center_context = None
    if cost_center:
        cost_center_context = get_cost_center_status(cost_center_id=cost_center)

    # Build structured signals the agent can use without re-reading policy text
    signals = _build_signals(
        amount=amount,
        vendor_context=vendor_context,
        cost_center_context=cost_center_context,
    )

    return {
        "amount": amount,
        "category": category,
        "policy_query_used": policy_query,
        "policy_context": policy_result.get("results", []),
        "policy_count": policy_result.get("count", 0),
        "vendor_context": vendor_context,
        "cost_center_context": cost_center_context,
        "signals": signals,
    }


def _amount_tier(amount: float) -> str:
    """Map amount to a textual tier for more relevant policy retrieval."""
    if amount < 10_000:
        return "under 10000 department head"
    if amount < 50_000:
        return "10000 to 50000 department director finance"
    if amount < 250_000:
        return "50000 to 250000 VP approval"
    if amount < 1_000_000:
        return "250000 to 1 million executive approval"
    return "over 1 million CFO board approval"


def _build_signals(
    amount: float,
    vendor_context: Optional[dict],
    cost_center_context: Optional[dict],
) -> dict[str, Any]:
    """Extract quick-reference flags from the retrieved context."""
    signals = {
        "amount": amount,
        "amount_tier": _amount_tier(amount),
    }

    if vendor_context and "error" not in vendor_context:
        signals["vendor_tier"] = vendor_context.get("tier")
        signals["vendor_status"] = vendor_context.get("status")
        risk = vendor_context.get("risk_score")
        signals["vendor_risk_score"] = risk
        if risk is not None:
            signals["vendor_risk_flag"] = (
                "HIGH" if risk >= 0.7 else "MEDIUM" if risk >= 0.4 else "LOW"
            )
        signals["vendor_ytd_spend"] = vendor_context.get("ytd_spend")

    if cost_center_context and "error" not in cost_center_context:
        signals["cc_utilization_pct"] = cost_center_context.get("utilization_pct")
        signals["cc_utilization_flag"] = cost_center_context.get("utilization_flag")
        signals["cc_remaining_budget"] = cost_center_context.get("remaining_budget")
        # Flag if PO would exceed remaining budget
        remaining = cost_center_context.get("remaining_budget")
        if remaining is not None and amount > remaining:
            signals["would_exceed_cc_budget"] = True
            signals["overage_amount"] = round(amount - remaining, 2)
        else:
            signals["would_exceed_cc_budget"] = False

    return signals
