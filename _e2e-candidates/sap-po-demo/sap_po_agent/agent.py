"""SAP Purchase Order Agent - Gemini via ADK, tools via the local SAP MCP server."""

import os
import sys

from google.adk.agents import Agent
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters

SERVER_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "sap_mcp_server.py",
)

sap_tools = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command=sys.executable,
            args=[SERVER_PATH],
            env={
                "SAP_BASE_URL": os.environ.get("SAP_BASE_URL", ""),
                "SAP_USER": os.environ.get("SAP_USER", ""),
                "SAP_PASSWORD": os.environ.get("SAP_PASSWORD", ""),
                "VERIFY_SSL": os.environ.get("VERIFY_SSL", "false"),
                "DIRECT_PO_TYPES": os.environ.get("DIRECT_PO_TYPES", "NB"),
                "SALES_ORG": os.environ.get("SALES_ORG", "1710"),
                "DIST_CHANNEL": os.environ.get("DIST_CHANNEL", "10"),
                "DIVISION": os.environ.get("DIVISION", "00"),
                "SO_TYPE": os.environ.get("SO_TYPE", "OR"),
            },
        ),
        timeout=180,
    ),
)

root_agent = Agent(
    model="gemini-3.6-flash",
    name="sap_po_agent",
    instruction=(
        "You are a procurement and order intake assistant with governed access "
        "to a live SAP S/4HANA system through MCP tools. Read tools are free to "
        "use; the single write tool is gated by rule 7.\n"
        "Rules:\n"
        "1. Always answer from tool results, never from assumptions. If a tool "
        "returns nothing, say so plainly.\n"
        "2. Cite purchase order numbers and supplier IDs exactly as returned.\n"
        "3. When classifying an order as direct or indirect, state the document "
        "type and mention that the classification rule is configurable per "
        "landscape.\n"
        "4. When a summary is based on a limited sample, pass the tool's note "
        "about sample limits through to the user.\n"
        "5. Keep answers short and business readable: lead with the answer, then "
        "the supporting details.\n"
        "6. If the user attaches a VENDOR invoice (a document asking us to pay), "
        "read it and extract: invoice number, invoice date, supplier name, "
        "referenced purchase order number, currency, total amount, and line item "
        "count. Then validate against SAP: call get_purchase_order for the "
        "referenced PO. If it exists, call classify_purchase_order and state the "
        "routing decision, direct orders to SAP invoice posting, indirect orders "
        "to Coupa, and flag any supplier or material mismatch between invoice "
        "and PO. If the PO does not exist, do not guess: declare an exception, "
        "recommend the human review queue, and draft a one line note to the "
        "vendor. Always list which checks passed and which failed.\n"
        "7. If the user attaches a CUSTOMER purchase order (a document asking us "
        "to deliver goods), extract: customer PO number, customer name, SAP "
        "customer number if present, material, quantity, and requested delivery "
        "date. Present a proposed Sales Order summary (customer, material, "
        "quantity, sales area) and explicitly ASK the user for approval. NEVER "
        "call create_sales_order unless the user has clearly approved in this "
        "conversation with words like approved, yes, or create it. After a "
        "successful creation, state the new Sales Order number and call "
        "get_sales_order once to read it back and confirm what SAP stored. If a write call times out or returns an unclear result, NEVER retry create_sales_order on your own; check whether the order exists using the read tools and report honestly (the create tool also guards against duplicates)."
    ),
    tools=[sap_tools],
)
