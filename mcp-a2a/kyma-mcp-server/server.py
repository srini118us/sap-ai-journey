"""
SAP MCP Server
Exposes SAP-style tools via Model Context Protocol (MCP)

This server can be connected to:
- Claude Desktop (local development)
- SAP Joule (production on Kyma)
- Any MCP-compatible client

Transport modes:
- stdio: For local development with Claude Desktop
- streamable-http: For HTTP-based deployment (Kyma, Joule Studio)
- sse: DEPRECATED - Use streamable-http instead
"""

from fastmcp import FastMCP
from typing import Optional
import json

# Import our SAP tools
from tools import (
    get_purchase_orders,
    get_purchase_order_by_id,
    get_vendor_summary
)

# Initialize the MCP Server
mcp = FastMCP(name="sap-procurement-server")


# ============================================================
# TOOL 1: Get Purchase Orders (with filters)
# ============================================================
@mcp.tool()
def sap_get_purchase_orders(
    status: Optional[str] = None,
    vendor: Optional[str] = None,
    plant: Optional[str] = None,
    limit: int = 10
) -> str:
    """
    Retrieve Purchase Orders from SAP S/4HANA.
    
    Use this tool to search and list purchase orders with optional filters.
    
    Args:
        status: Filter by PO status - "Approved", "Pending Approval", or "Delivered"
        vendor: Filter by vendor name (partial match supported)
        plant: Filter by plant code (e.g., "Plant-US-01")
        limit: Maximum number of results (default: 10)
    
    Returns:
        JSON string containing matching purchase orders with summary
    
    Example queries:
        - "Show me all pending purchase orders"
        - "List POs from ACME Supplies"
        - "Get approved orders from Plant-US-01"
    """
    result = get_purchase_orders(
        status=status,
        vendor=vendor,
        plant=plant,
        limit=limit
    )
    return json.dumps(result, indent=2)


# ============================================================
# TOOL 2: Get Single Purchase Order by ID
# ============================================================
@mcp.tool()
def sap_get_purchase_order(po_number: str) -> str:
    """
    Retrieve a specific Purchase Order by its PO Number.
    
    Use this tool when you need details about a specific purchase order.
    
    Args:
        po_number: The Purchase Order number (e.g., "4500000001")
    
    Returns:
        JSON string containing the purchase order details
    
    Example queries:
        - "Get details for PO 4500000001"
        - "Show me purchase order 4500000003"
    """
    result = get_purchase_order_by_id(po_number)
    return json.dumps(result, indent=2)


# ============================================================
# TOOL 3: Get Vendor Summary
# ============================================================
@mcp.tool()
def sap_get_vendor_summary() -> str:
    """
    Get a summary of Purchase Orders grouped by vendor.
    
    Use this tool for vendor analysis and spend overview.
    
    Returns:
        JSON string containing vendor-wise PO summary including:
        - Number of POs per vendor
        - Total spend per vendor
        - PO statuses per vendor
    
    Example queries:
        - "Show me vendor-wise PO summary"
        - "Which vendors have the most orders?"
        - "Give me a spend analysis by vendor"
    """
    result = get_vendor_summary()
    return json.dumps(result, indent=2)


# ============================================================
# RESOURCE: Procurement Help Documentation
# ============================================================
@mcp.resource("sap://procurement/help")
def get_procurement_help() -> str:
    """
    Returns help documentation for the SAP Procurement MCP Server.
    """
    help_text = """
    # SAP Procurement MCP Server - Help
    
    ## Available Tools
    
    ### 1. sap_get_purchase_orders
    Search and filter purchase orders.
    - Filter by status: Approved, Pending Approval, Delivered
    - Filter by vendor name
    - Filter by plant code
    
    ### 2. sap_get_purchase_order
    Get details for a specific PO by number.
    - PO numbers are in format: 45XXXXXXXX
    
    ### 3. sap_get_vendor_summary
    Get spend analysis grouped by vendor.
    
    ## Example Questions
    - "What purchase orders are pending approval?"
    - "Show me all POs from ACME Supplies"
    - "Get details for PO 4500000001"
    - "Which vendor has the highest spend?"
    
    ## Source System
    This server connects to SAP S/4HANA (simulated for demo).
    """
    return help_text


# ============================================================
# Main Entry Point
# ============================================================
if __name__ == "__main__":
    import sys
    
    # Check for transport mode argument
    if len(sys.argv) > 1 and sys.argv[1] == "--http":
        # Streamable HTTP mode for Kyma/Joule (NEW - Joule compatible!)
        print("Starting MCP Server in Streamable HTTP mode...")
        print("Endpoint: http://0.0.0.0:8080/mcp")
        mcp.run(
            transport="streamable-http",
            host="0.0.0.0",
            port=8080,
            path="/mcp"
        )
    elif len(sys.argv) > 1 and sys.argv[1] == "--sse":
        # SSE mode - DEPRECATED (kept for backward compatibility)
        print("WARNING: SSE transport is deprecated. Use --http for Joule.")
        print("Starting MCP Server in SSE mode (HTTP)...")
        mcp.run(transport="sse", host="0.0.0.0", port=8080)
    else:
        # Default: stdio mode for Claude Desktop
        print("Starting MCP Server in stdio mode...")
        mcp.run(transport="stdio")
