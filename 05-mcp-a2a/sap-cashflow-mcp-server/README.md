# MCP (Model Context Protocol)

## Scope

MCP server implementations that expose SAP systems to AI assistants. These servers enable natural language interaction with SAP data through Claude Desktop, SAP Joule, and other MCP-compatible clients.

## Use Cases

| # | Use Case | What It Demonstrates | Status |
|---|----------|---------------------|--------|
| 1 | [Kyma MCP Server](./kyma-mcp-server/) | S/4HANA Purchase Orders via MCP | ✅ Complete |

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    MCP INTEGRATION PATTERN                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │                    AI ASSISTANTS                         │   │
│   │                                                          │   │
│   │   ┌───────────┐    ┌───────────┐    ┌───────────┐       │   │
│   │   │  Claude   │    │   SAP     │    │   Custom  │       │   │
│   │   │  Desktop  │    │   Joule   │    │   Client  │       │   │
│   │   └─────┬─────┘    └─────┬─────┘    └─────┬─────┘       │   │
│   │         │                │                │              │   │
│   │         └────────────────┼────────────────┘              │   │
│   │                          │                               │   │
│   │                          ▼                               │   │
│   │                    MCP Protocol                          │   │
│   │                  (JSON-RPC based)                        │   │
│   │                                                          │   │
│   └──────────────────────────┼───────────────────────────────┘   │
│                              │                                   │
│   ┌──────────────────────────┼───────────────────────────────┐   │
│   │                          ▼                                │   │
│   │                    MCP SERVERS                            │   │
│   │                                                          │   │
│   │   ┌─────────────────────────────────────────────────┐   │   │
│   │   │            kyma-mcp-server                       │   │   │
│   │   │                                                  │   │   │
│   │   │  Tools:                                          │   │   │
│   │   │  • sap_get_purchase_orders                       │   │   │
│   │   │  • sap_get_purchase_order                        │   │   │
│   │   │  • sap_get_vendor_summary                        │   │   │
│   │   │                                                  │   │   │
│   │   │  Transports: stdio | streamable-http             │   │   │
│   │   │                                                  │   │   │
│   │   └─────────────────────────────────────────────────┘   │   │
│   │                                                          │   │
│   └──────────────────────────┬───────────────────────────────┘   │
│                              │                                   │
│   ┌──────────────────────────┼───────────────────────────────┐   │
│   │                          ▼                                │   │
│   │                    SAP SYSTEMS                            │   │
│   │                                                          │   │
│   │   ┌───────────┐    ┌───────────┐    ┌───────────┐       │   │
│   │   │  S/4HANA  │    │  BTP      │    │   Other   │       │   │
│   │   │  (OData)  │    │  APIs     │    │  Services │       │   │
│   │   └───────────┘    └───────────┘    └───────────┘       │   │
│   │                                                          │   │
│   └──────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## What is MCP?

Model Context Protocol (MCP) is an open standard for connecting AI assistants to external tools and data sources. Key concepts:

| Concept | Description |
|---------|-------------|
| **Tool** | Function the AI can call (e.g., query database, call API) |
| **Resource** | Static data accessible to AI (e.g., documentation, schemas) |
| **Transport** | Communication method between client and server |
| **Server** | Backend that exposes tools and resources |
| **Client** | AI assistant that consumes tools (Claude, Joule) |

## Transport Modes

| Mode | Use Case | Example |
|------|----------|---------|
| `stdio` | Local development | Claude Desktop |
| `streamable-http` | Cloud deployment | Kyma, Joule Studio |
| `sse` | DEPRECATED | Legacy HTTP streaming |

## Structure

```
mcp/
├── README.md                # This file
└── kyma-mcp-server/
    ├── README.md            # Detailed documentation
    ├── server.py            # FastMCP server
    ├── tools.py             # S/4HANA integration
    ├── requirements.txt
    ├── Dockerfile
    └── k8s/                  # Kyma deployment manifests
```

## Key Technologies

| Technology | Purpose |
|------------|---------|
| FastMCP | Python MCP server framework |
| Kyma Runtime | Kubernetes-based container hosting |
| OData | SAP API standard |
| JSON-RPC | MCP wire protocol |

## Reference

- [MCP Specification](https://modelcontextprotocol.io/)
- [FastMCP](https://github.com/jlowin/fastmcp)
- [Claude MCP Documentation](https://docs.anthropic.com/en/docs/build-with-claude/mcp)
- [Kyma Runtime](https://help.sap.com/docs/btp/sap-business-technology-platform/kyma-environment)
