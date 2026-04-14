# Kyma MCP Server

## Scope

Model Context Protocol (MCP) server exposing SAP S/4HANA Purchase Order APIs to AI assistants. This server enables Claude Desktop, SAP Joule, and other MCP-compatible clients to query and analyze procurement data using natural language.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     MCP SERVER ARCHITECTURE                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │                    MCP CLIENTS                           │   │
│   │                                                          │   │
│   │   ┌───────────┐    ┌───────────┐    ┌───────────┐       │   │
│   │   │  Claude   │    │   SAP     │    │   Other   │       │   │
│   │   │  Desktop  │    │   Joule   │    │   Client  │       │   │
│   │   │  (stdio)  │    │  (http)   │    │           │       │   │
│   │   └─────┬─────┘    └─────┬─────┘    └─────┬─────┘       │   │
│   │         │                │                │              │   │
│   └─────────┼────────────────┼────────────────┼──────────────┘   │
│             │                │                │                  │
│             ▼                ▼                ▼                  │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │                  FASTMCP SERVER                          │   │
│   │              (sap-procurement-server)                    │   │
│   │                                                          │   │
│   │   Transport Modes:                                       │   │
│   │   • stdio           → Claude Desktop (local)             │   │
│   │   • streamable-http → Kyma / Joule Studio                │   │
│   │   • sse             → DEPRECATED                         │   │
│   │                                                          │   │
│   │   ┌─────────────────────────────────────────────────┐   │   │
│   │   │                   TOOLS                          │   │   │
│   │   │                                                  │   │   │
│   │   │  ┌─────────────────────────────────────────┐    │   │   │
│   │   │  │ sap_get_purchase_orders                 │    │   │   │
│   │   │  │ Filter by status, vendor, plant         │    │   │   │
│   │   │  └─────────────────────────────────────────┘    │   │   │
│   │   │                                                  │   │   │
│   │   │  ┌─────────────────────────────────────────┐    │   │   │
│   │   │  │ sap_get_purchase_order                  │    │   │   │
│   │   │  │ Get single PO by number                 │    │   │   │
│   │   │  └─────────────────────────────────────────┘    │   │   │
│   │   │                                                  │   │   │
│   │   │  ┌─────────────────────────────────────────┐    │   │   │
│   │   │  │ sap_get_vendor_summary                  │    │   │   │
│   │   │  │ Vendor-wise PO analysis                 │    │   │   │
│   │   │  └─────────────────────────────────────────┘    │   │   │
│   │   │                                                  │   │   │
│   │   └──────────────────────────────────────────────────┘   │   │
│   │                                                          │   │
│   └────────────────────────┬────────────────────────────────┘   │
│                            │                                     │
│                            ▼                                     │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │                    SAP S/4HANA                           │   │
│   │                                                          │   │
│   │   OData API: API_PURCHASEORDER_PROCESS_SRV               │   │
│   │   Auth: HTTP Basic                                       │   │
│   │                                                          │   │
│   │   Endpoints:                                             │   │
│   │   • /A_PurchaseOrder         (list/filter)               │   │
│   │   • /A_PurchaseOrder('{id}') (single PO)                 │   │
│   │                                                          │   │
│   └─────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Tools

### sap_get_purchase_orders

Search and filter purchase orders.

| Parameter | Type | Description |
|-----------|------|-------------|
| `status` | string | Filter: Approved, Pending Approval, Delivered |
| `vendor` | string | Filter by vendor name (partial match) |
| `plant` | string | Filter by plant code |
| `limit` | int | Max results (default: 10) |

**Example queries:**
- "Show me all pending purchase orders"
- "List POs from ACME Supplies"
- "Get approved orders from Plant-US-01"

---

### sap_get_purchase_order

Get details for a specific PO.

| Parameter | Type | Description |
|-----------|------|-------------|
| `po_number` | string | PO number (e.g., "4500000001") |

**Example queries:**
- "Get details for PO 4500000001"
- "Show me purchase order 4500000003"

---

### sap_get_vendor_summary

Vendor-wise spend analysis.

**Returns:**
- PO count per vendor
- Company codes per vendor
- Purchasing orgs per vendor

**Example queries:**
- "Which vendors have the most orders?"
- "Give me a spend analysis by vendor"

## Transport Modes

| Mode | Use Case | Command |
|------|----------|---------|
| `stdio` | Claude Desktop (local) | `python server.py` |
| `streamable-http` | Kyma / Joule Studio | `python server.py --http` |
| `sse` | DEPRECATED | `python server.py --sse` |

## Configuration

### Environment Variables

```bash
S4_BASE_URL=http://your-s4hana-server:8003
S4_USER=username
S4_PASSWORD=password
```

### Claude Desktop Config

```json
{
  "mcpServers": {
    "sap-procurement": {
      "command": "python",
      "args": ["C:/path/to/server.py"]
    }
  }
}
```

## Quick Start

### Local Development (Claude Desktop)

```bash
cd mcp/kyma-mcp-server
pip install -r requirements.txt

# Set S/4HANA credentials
export S4_BASE_URL=http://your-server:8003
export S4_USER=your-user
export S4_PASSWORD=your-password

# Run in stdio mode
python server.py
```

### Kyma Deployment

```bash
# Build Docker image
docker build -t kyma-mcp-server .

# Deploy to Kyma
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/apirule.yaml
```

## Files

```
kyma-mcp-server/
├── README.md                    # This file
├── server.py                    # FastMCP server with tool definitions
├── tools.py                     # S/4HANA OData API integration
├── requirements.txt             # Python dependencies
├── Dockerfile                   # Container image
├── claude_desktop_config.json   # Claude Desktop configuration
├── kubeconfig.yaml              # Kubernetes config
└── k8s/
    ├── deployment.yaml          # Kyma deployment
    ├── service.yaml             # Kubernetes service
    └── apirule.yaml             # Kyma API rule (ingress)
```

| File | Purpose |
|------|---------|
| `server.py` | FastMCP server, tool decorators, transport handling |
| `tools.py` | OData requests, response parsing, vendor summary |
| `Dockerfile` | Container build for Kyma deployment |

## Dependencies

```
fastmcp
requests
python-dotenv
```

## S/4HANA API Details

| Field | Value |
|-------|-------|
| OData Service | `API_PURCHASEORDER_PROCESS_SRV` |
| Entity | `A_PurchaseOrder` |
| Auth | HTTP Basic |
| Format | JSON (`$format=json`) |

### Response Fields

| Field | Description |
|-------|-------------|
| `PurchaseOrder` | PO number |
| `Supplier` | Vendor ID |
| `SupplierName` | Vendor name |
| `CompanyCode` | Company code |
| `PurchasingOrganization` | Purchasing org |
| `PurchasingGroup` | Purchasing group |
| `CreationDate` | Created date |
| `DocumentCurrency` | Currency |

## Key Concepts

| Concept | Description |
|---------|-------------|
| MCP | Model Context Protocol - standard for AI tool integration |
| FastMCP | Python framework for building MCP servers |
| Tool | Function exposed to AI assistants |
| Resource | Static data/documentation accessible to AI |
| Transport | Communication method (stdio, http, sse) |

## Integration Points

| Integrates With | Purpose |
|-----------------|---------|
| Claude Desktop | Local development and testing |
| SAP Joule | Production AI assistant |
| S/4HANA | Purchase order data source |
| Kyma Runtime | Container deployment |

## Reference

- [MCP Specification](https://modelcontextprotocol.io/)
- [FastMCP](https://github.com/jlowin/fastmcp)
- [SAP Purchase Order API](https://api.sap.com/api/API_PURCHASEORDER_PROCESS_SRV)
- [Kyma Runtime](https://help.sap.com/docs/btp/sap-business-technology-platform/kyma-environment)
