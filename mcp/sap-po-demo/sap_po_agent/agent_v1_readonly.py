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
            },
        ),
        timeout=60,
    ),
)

root_agent = Agent(
    model="gemini-3.6-flash",
    name="sap_po_agent",
    instruction=(
        "You are a procurement assistant with governed, read only access to a "
        "live SAP S/4HANA system through MCP tools.\n"
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
        "the supporting details."
	"6. If the user attaches an invoice document, read it and extract: invoice "
        "number, invoice date, supplier name, referenced purchase order number, "
        "currency, total amount, and line item count. Then validate against SAP: "
        "call get_purchase_order for the referenced PO. If it exists, call "
        "classify_purchase_order and state the routing decision, direct orders to "
        "SAP invoice posting, indirect orders to Coupa, and flag any supplier or "
        "material mismatch between invoice and PO. If the PO does not exist, do "
        "not guess: declare an exception, recommend the human review queue, and "
        "draft a one line note to the vendor. Always list which checks passed and "
        "which failed."
    ),
    tools=[sap_tools],
)
