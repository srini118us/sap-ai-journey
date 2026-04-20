# SAP Procurement MCP Server

MCP server exposing SAP Procurement data as callable tools for Joule Agents.
Reuses HANA Cloud schema and data from Lab 52 (`sap-procurement-rag`).

Part of Lab A: Custom Joule Agent for Procurement Approval.

## Scope

This server is the **tool layer** between Joule Skills and the HANA Cloud data
backing Lab 52. It does not orchestrate decisions. It does not synthesize
responses. Its only job is to return clean, structured data when Joule asks
for it.

Session 1 scope: 3 core tools, local testing only.
Session 2+: 4 additional tools, Cloud Foundry deployment, Joule Skills, Agent.

## Architecture

```
Joule Agent (Procurement Approval Assistant)
    |
    v
Joule Skills (one per MCP tool)
    |
    v
MCP Server  [this project]
    |  Streamable HTTP transport
    v
+-------------------+        +--------------------+
| FastMCP tools     | -----> | SAP GenAI Hub       |
| (search_policies, |        | text-embedding-3    |
|  get_vendor_info, |        +--------------------+
|  get_cost_center) |
|                   | -----> +--------------------+
|                   |        | SAP HANA Cloud     |
+-------------------+        | PROC_AI schema     |
                             | (from Lab 52)      |
                             +--------------------+
```

## Systems Involved

| System | Role | Integration Pattern |
|--------|------|---------------------|
| FastMCP 3.1.1 | MCP server framework | Streamable HTTP |
| SAP HANA Cloud | Vector + relational store | hdbcli (native SQL) |
| SAP GenAI Hub | Query embedding | REST + OAuth2 Bearer |
| SAP Joule | Agent orchestration | MCP via destination |
| Cloud Foundry (us10) | Runtime host | `cf push` buildpack |

## Integration Patterns

| Hop | Pattern | Notes |
|-----|---------|-------|
| Joule -> MCP Server | Streamable HTTP | Destination URL must NOT end with `/mcp` |
| MCP Server -> HANA | hdbcli (dbapi) | Singleton connection, auto-reconnect |
| MCP Server -> GenAI Hub | REST + OAuth2 | Token cached, refresh 60s before expiry |
| HANA vector search | COSINE_SIMILARITY | REAL_VECTOR(1536), TO_REAL_VECTOR() cast |

## Lab vs Production

| Aspect | Lab (this) | Production |
|--------|------------|------------|
| Secrets | `.env` file | BTP service binding / XSUAA / secret store |
| HANA connection | Shared process-level singleton | Connection pool per worker |
| Token cache | In-memory | Redis / Hyperscaler secret manager |
| Error handling | Log + return error dict | Retry + circuit breaker + DLQ |
| Observability | stdout logs | OpenTelemetry -> SAP Cloud Logging |
| Deployment | `cf push` | CI/CD with SAP Cloud Transport Management |
| Data freshness | Static Lab 52 snapshot | CDC from S/4HANA via Datasphere |

## Tools Exposed (Session 1)

### `search_policies(query, max_results=5)`
Semantic search on `POLICY_CHUNKS` using COSINE_SIMILARITY. Embeds the query
via GenAI Hub, runs the vector search, returns chunks with similarity scores
and document/section citations.

### `get_vendor_info(vendor_id=None, vendor_name=None)`
Vendor master lookup with YTD spend aggregation. Supports exact lookup by ID
or fuzzy match by name (returns candidate list if ambiguous).

### `get_cost_center_status(cost_center_id)`
Budget utilization for a cost center. Joins COST_CENTER_MASTER to
ACDOCA_EXTRACT for actual spend, computes utilization percentage, tags
status OK / WARNING (>=85%) / CRITICAL (>=95%).

## Setup

### Prerequisites

- Python 3.10+
- Access to SAP HANA Cloud instance with Lab 52 `PROC_AI` schema loaded
- SAP GenAI Hub deployments:
  - Embedding: `text-embedding-3-small` (Lab 52 deployment `da94363cd9046ce4`)
- Windows PowerShell / Linux bash

### Installation

```bash
# Clone into your repos folder
cd C:\Users\nivas\repos
# (copy files from downloaded zip)

cd sap-procurement-mcp-server

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Configure credentials
copy .env.example .env   # Windows
# cp .env.example .env   # Linux/Mac
# Then edit .env with real values from Lab 52 .env
```

### Run local smoke test (before starting MCP server)

This tests the 3 tools as plain Python functions. Verifies HANA connectivity,
GenAI Hub embedding, and SQL correctness independently of the MCP transport.

```bash
python -m tests.test_tools_local
```

Expected: 3 PASS lines in the summary.

### Run the MCP server locally

```bash
python -m src.server
```

Server listens on `http://0.0.0.0:8080` (configurable via `MCP_PORT`).
Test with any MCP client pointed at `http://localhost:8080/mcp`.

## Project Structure

```
sap-procurement-mcp-server/
  .env.example              Template (commit this)
  .env                      Real credentials (gitignored)
  .gitignore
  requirements.txt          Pinned versions
  README.md                 This file
  src/
    server.py               FastMCP entrypoint, registers tools
    hana/
      connection.py         Singleton HANA connection, context manager
    genai/
      embedding.py          OAuth2 + embedding REST call
    tools/
      policies.py           search_policies implementation
      vendors.py            get_vendor_info implementation
      cost_centers.py       get_cost_center_status implementation
  tests/
    test_tools_local.py     Smoke test without MCP transport
```

## Challenges and Lessons Learned

Placeholder — fill in as issues surface during testing:

1. _(pending)_ Column name or schema mismatches vs Lab 52
2. _(pending)_ GenAI Hub embedding endpoint URL differences
3. _(pending)_ HANA vector literal format
4. _(pending)_ FastMCP 3.1.1 transport quirks in CF runtime

## What We Achieved (Session 1)

- Clean separation: HANA client, GenAI client, tools, server entrypoint
- Singleton HANA connection with auto-reconnect
- OAuth2 token caching with 60s pre-expiry refresh
- 3 tools returning structured dicts (machine-readable, Joule-friendly)
- Local smoke test that isolates tool logic from MCP transport
- Reuses Lab 52 `PROC_AI` schema with no new tables

## Interview Talking Points

**Elevator pitch (30s):**
"I built an MCP server that exposes SAP Procurement data as callable tools
for a Joule Agent. The tools wrap semantic search over policy documents and
structured queries over vendor and budget data in HANA Cloud. Joule can
orchestrate these tools into a procurement-approval workflow that a human
analyst would otherwise run manually across four or five screens."

**Maps to main project (RISE -> BDC -> Databricks -> Joule):**
Same Joule-as-orchestrator pattern applies to RISE migration: Joule agents
call MCP tools that reach into BDC, Databricks, or S/4HANA, synthesize
results, and return cited recommendations. Lab A is the pattern proof.

**Business value:**
Approval analysts currently join data from 4-5 sources manually (policy PDFs,
vendor master, budget reports, PO history). Agent + MCP pattern compresses
that into one natural-language query with cited sources and flags the
analyst would have missed (e.g., cost center at 91% utilization crossing an
85% escalation threshold).

**Technical challenges worth mentioning:**
- FastMCP transport selection: Joule requires Streamable HTTP, not SSE;
  FASTMCP_STATELESS_HTTP=true is mandatory.
- Destination URL quirk: must NOT end with `/mcp` — Joule appends it.
- Token lifecycle: OAuth2 tokens expire; naive re-fetch per call is slow,
  so cache with pre-expiry refresh (60s window).
- Connection reuse: HANA connection-per-call under MCP load gets expensive;
  singleton with reconnect-on-disconnect is the pragmatic pattern.

**Anticipated Q&A:**

*Q: Why MCP server instead of CAP + OData?*
A: CAP + OData is fine for deterministic CRUD. MCP is purpose-built for
LLM tool use: tool schemas are discoverable by the agent, not just by
client code. For agent use cases, MCP is the right abstraction.

*Q: Why expose three tools instead of one "answer_my_question" tool?*
A: Single-tool design hides orchestration inside tool code; the agent can't
reason about the plan. Three narrow tools let the Joule agent decide the
sequence, loop, or skip steps based on the query. That's the "tools not
agents" MCP philosophy.

*Q: How does this scale past one agent?*
A: Same MCP server. Multiple agents can call the same tools — procurement
approval, vendor onboarding, spend analytics — each with its own persona
and skill selection, all talking to the same tool surface. Single source
of truth for data access logic.

## Next Steps

- Session 1 finish: smoke test green, CF CLI installed and logged in
- Session 2: tools 4-7 (`get_po_history`, `check_approval_policy`,
  `search_contracts`, `get_spending_summary`), CF deployment
- Session 3: 7 Joule Skills in Joule Studio
- Session 4: Joule Agent assembly + 6-7 test queries with screenshots
- Session 5: GitHub repo `sap-procurement-joule-agent`, documentation

## Reference Links

- Lab 52 (`sap-procurement-rag`): https://github.com/srini118us/sap-procurement-rag
- FastMCP docs: https://github.com/jlowin/fastmcp
- SAP GenAI Hub: https://help.sap.com/docs/sap-ai-core/generative-ai-hub
- SAP HANA Vector Engine: https://help.sap.com/docs/hana-cloud-database/sap-hana-cloud-sap-hana-database-vector-engine-guide
