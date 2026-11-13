# SAP MCP Labs

Index for the Model Context Protocol labs in this repository. The CAP labs live under the cap folder as CAP applications. The BTP Administration lab lives here, since it is not CAP code. Click a link to open a lab.

## Labs

| Lab | What it shows | Where |
|---|---|---|
| CAP service as MCP, plus guarded write | A CAP operation (checkPOStatus) exposed as an MCP tool, and a validated write (setPOStatus) behind an approval gate | [cap/lab1-mcp-tools](../cap/lab1-mcp-tools) |
| Retrieval over MCP (RAG) and composition | A vector search exposed as an MCP tool, two MCP servers composed in one answer | [cap/lab2a-vector-sqlite](../cap/lab2a-vector-sqlite) |
| BTP Administration MCP (platform as MCP) | The SAP hosted BTP admin server driven in plain language across accounts, services, security, and connectivity, ending in an access review | this folder |

Related: [cap/lab2b-vector-hana](../cap/lab2b-vector-hana) is the native HANA vector version of the retrieval lab (not MCP enabled).

## The capabilities covered

1. Tools, an operation called as a tool (lab1 checkPOStatus).
2. Guarded write, a validated change behind a rule, marked destructive (lab1 setPOStatus).
3. Retrieval, grounded passages returned as a tool (lab2a search), and composition across servers.
4. Platform administration, the live BTP account exposed as read tools (BTP admin).

## How to run

- CAP labs: open the lab folder, npm install, cds watch, connect an MCP client (MCP Inspector or Claude Code). Each lab carries the @mcp annotation.
- BTP admin: register the SAP hosted server once with claude mcp add, then /mcp and sign in. No local server.

## Notes

- A CAP lab serves its MCP endpoint at the service path, for example http://localhost:4004/odata/v4/procurement, not under /mcp.
- Detailed write-ups with screenshots are kept as Word documents.
