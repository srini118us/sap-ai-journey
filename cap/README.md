# SAP CAP Labs

CAP (Cloud Application Programming Model) labs on HANA Cloud, part of the sap-ai-journey repo. Each is a CAP application. Several are also MCP enabled. See the MCP index for the MCP view.

## Labs

| Lab | What it is | MCP |
|---|---|---|
| [lab1-mcp-tools](lab1-mcp-tools) | Procurement service: Suppliers and PurchaseOrders, a checkPOStatus lookup, and a guarded setPOStatus write behind an approval gate | Yes, exposed as MCP tools |
| [lab2a-vector-sqlite](lab2a-vector-sqlite) | RAG vector search over policy chunks, cosine similarity in the Node handler on SQLite | Yes, search exposed as an MCP tool |
| [lab2b-vector-hana](lab2b-vector-hana) | The same retrieval using native HANA REAL_VECTOR and COSINE_SIMILARITY | Not MCP enabled |

## MCP

Labs 1 and 2a expose their operations over the Model Context Protocol through the @cap-js/mcp plugin. See [../MCP](../MCP) for the MCP index and the platform BTP admin lab.

## How to run a lab

cd into the lab folder, then:
- npm install
- cds watch
- connect an MCP client (MCP Inspector or Claude Code) to the service path endpoint, for example http://localhost:4004/odata/v4/procurement
