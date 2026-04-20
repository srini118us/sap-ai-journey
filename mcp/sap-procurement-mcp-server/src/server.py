"""FastMCP server for SAP Procurement tools.

Exposes 3 core MCP tools for Joule Agent consumption:
    - search_policies: Semantic search on procurement policies
    - get_vendor_info: Vendor master + YTD spend lookup
    - get_cost_center_status: Budget utilization check

Transport: Streamable HTTP (required by Joule; FASTMCP_STATELESS_HTTP=true)
"""
import os
import logging

from dotenv import load_dotenv
from fastmcp import FastMCP

# Load .env from current working directory
load_dotenv()

# Configure logging before importing tools
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Import tools after env is loaded
from src.tools import search_policies as _search_policies
from src.tools import get_vendor_info as _get_vendor_info
from src.tools import get_cost_center_status as _get_cost_center_status

# Create MCP server
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
                     May return multiple candidates if ambiguous.

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


if __name__ == "__main__":
    host = os.getenv("MCP_HOST", "0.0.0.0")
    port = int(os.getenv("MCP_PORT", "8080"))
    logger.info("[SERVER] Starting FastMCP on %s:%s (Streamable HTTP)", host, port)
    mcp.run(transport="streamable-http", host=host, port=port)
