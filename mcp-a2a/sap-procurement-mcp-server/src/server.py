"""FastMCP server for SAP Procurement tools.

Exposes 7 MCP tools for Joule Agent consumption:
    - search_policies: Semantic search on procurement policies
    - get_vendor_info: Vendor master + YTD spend lookup
    - get_cost_center_status: Budget utilization check
    - get_po_history: Recent purchase orders with flexible filters
    - search_contracts: Semantic search on vendor contracts
    - get_spending_summary: Aggregate spend analysis
    - check_approval_policy: RAG-based policy lookup for PO approval decisions

Transport: Streamable HTTP (required by Joule).
"""
import os
import logging

from dotenv import load_dotenv
from fastmcp import FastMCP

load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

from src.tools import search_policies as _search_policies
from src.tools import get_vendor_info as _get_vendor_info
from src.tools import get_cost_center_status as _get_cost_center_status
from src.tools import get_po_history as _get_po_history
from src.tools import search_contracts as _search_contracts
from src.tools import get_spending_summary as _get_spending_summary
from src.tools import check_approval_policy as _check_approval_policy

mcp = FastMCP(os.getenv("MCP_SERVER_NAME", "procurement-server"))


@mcp.tool()
def search_policies(query: str, max_results: int = 5) -> dict:
    """Search procurement policies using semantic similarity.

    Use this tool when the user asks about approval limits, spending rules,
    vendor requirements, contract policies, or any procurement governance topic.

    Args:
        query: Natural language description of what policy information is needed.
               Example: "What is the approval limit for consulting services?"
        max_results: Maximum number of relevant policy chunks to return (1-10, default 5).

    Returns:
        A dictionary containing matched policy chunks with similarity scores,
        document titles, and section references for citation.
    """
    return _search_policies(query=query, max_results=max_results)


@mcp.tool()
def get_vendor_info(
    vendor_id: str | None = None,
    vendor_name: str | None = None,
) -> dict:
    """Look up vendor master details and year-to-date spending.

    Use this tool when the user mentions a specific vendor by name or ID and
    needs vendor status, tier, risk score, or spending history.

    Args:
        vendor_id: Exact vendor identifier (e.g., "V-10042"). Use this when known.
        vendor_name: Partial vendor name (e.g., "ACME"). Used when vendor_id is missing.

    Returns:
        Vendor details including status, tier, risk score, category,
        and year-to-date PO count and total spend.
    """
    return _get_vendor_info(vendor_id=vendor_id, vendor_name=vendor_name)


@mcp.tool()
def get_cost_center_status(cost_center_id: str) -> dict:
    """Retrieve current budget utilization for a cost center.

    Use this tool when evaluating whether a cost center has remaining budget
    for a new purchase order, or when the user asks about budget status.

    Args:
        cost_center_id: Cost center identifier (e.g., "CC-4400").

    Returns:
        Allocated budget, actual spend, remaining budget, utilization percentage,
        and status flag (OK / WARNING >=85% / CRITICAL >=95%).
    """
    return _get_cost_center_status(cost_center_id=cost_center_id)


@mcp.tool()
def get_po_history(
    vendor_id: str | None = None,
    cost_center: str | None = None,
    days_back: int | None = None,
    max_results: int = 20,
) -> dict:
    """Retrieve recent purchase orders with flexible filters.

    Use this tool when the user asks about past POs for a specific vendor,
    cost center, or time window. At least one filter must be provided.

    Args:
        vendor_id: Filter by vendor ID (e.g., "V-10001").
        cost_center: Filter by cost center (e.g., "CC-4400").
        days_back: Only include POs from the last N days (e.g., 90 = last quarter).
        max_results: Max rows returned (default 20, capped at 100).

    Returns:
        List of PO records ordered by date descending, plus count and echoed filters.
    """
    return _get_po_history(
        vendor_id=vendor_id,
        cost_center=cost_center,
        days_back=days_back,
        max_results=max_results,
    )


@mcp.tool()
def search_contracts(
    query: str,
    max_results: int = 5,
    active_only: bool = True,
) -> dict:
    """Semantic search on vendor contracts.

    Use this tool when the user asks about contract terms, pricing, discounts,
    renewal dates, or wants to find contracts related to a topic.

    Args:
        query: Natural language description of contract info needed.
               Example: "annual SaaS maintenance contracts with volume discounts"
        max_results: Max contracts to return (default 5, capped at 10).
        active_only: Only include active contracts (default True).

    Returns:
        Contract records with vendor info, key terms, and similarity scores.
    """
    return _search_contracts(
        query=query, max_results=max_results, active_only=active_only
    )


@mcp.tool()
def get_spending_summary(
    vendor_id: str | None = None,
    cost_center: str | None = None,
    days_back: int = 365,
) -> dict:
    """Aggregate spending summary over a trailing time window.

    Counts only APPROVED and CLOSED POs (excludes DRAFT/PENDING/CANCELLED)
    to reflect committed spend. Use this for rollups like "how much have
    we spent with vendor X this year" or "CC-4400 spend last quarter".

    Args:
        vendor_id: Filter by vendor (optional).
        cost_center: Filter by cost center (optional).
        days_back: Trailing window in days (default 365).

    Returns:
        po_count, total_spend, avg/min/max PO amount, and echoed filters.
    """
    return _get_spending_summary(
        vendor_id=vendor_id, cost_center=cost_center, days_back=days_back
    )


@mcp.tool()
def check_approval_policy(
    amount: float,
    vendor_id: str | None = None,
    cost_center: str | None = None,
    category: str | None = None,
) -> dict:
    """Check approval policy for a proposed purchase order (RAG-based).

    Retrieves relevant policy passages for the PO's characteristics plus
    structured context signals (vendor tier, CC utilization). The agent
    then reasons about whether to approve, escalate, or reject.

    Use this tool BEFORE making any approval recommendation.

    Args:
        amount: PO amount (in currency).
        vendor_id: Vendor ID for tier/risk lookup (optional).
        cost_center: Cost center for budget check (optional).
        category: Hint for policy search (e.g., "IT Services", "Consulting").

    Returns:
        Policy context (retrieved chunks), vendor/CC context, and signals
        (amount tier, vendor risk, CC utilization, budget overage flag).
    """
    return _check_approval_policy(
        amount=amount,
        vendor_id=vendor_id,
        cost_center=cost_center,
        category=category,
    )


if __name__ == "__main__":
    host = os.getenv("MCP_HOST", "0.0.0.0")
    port = int(os.getenv("PORT", os.getenv("MCP_PORT", "8080")))
    logger.info(
        "[SERVER] Starting FastMCP '%s' on %s:%s (Streamable HTTP) — 7 tools registered",
        os.getenv("MCP_SERVER_NAME", "procurement-server"), host, port,
    )
    mcp.run(transport="streamable-http", host=host, port=port)
