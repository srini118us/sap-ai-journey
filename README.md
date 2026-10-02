# SAP AI Journey

A collection of hands on SAP AI labs covering SAP AI Core, Generative AI Hub, Joule and Joule Studio, RAG, Agentic AI, MCP and A2A, SAP Build, data and AI integration, and AI assisted SAP infrastructure and operations.

This repository focuses on individual SAP AI capabilities, reusable patterns, and focused technology labs. Larger business solutions that combine application, data, AI, integration, and decision layers are maintained separately under End to End Labs.

All work runs on personal lab, trial, and sandbox environments. Maturity is noted per lab in each section README.

## Structure

```mermaid
flowchart TD
    R[sap-ai-journey]
    R --> A[ai-core]
    R --> B[joule-joule-studio]
    R --> C[rag]
    R --> D[agentic-ai]
    R --> E[mcp-a2a]
    R --> F[build-apps-bpa]
    R --> G[data-ai]
    R --> H[infrastructure-ai]
    R --> I[architecture]
    R --> J[docs]
```

| Folder | What belongs here |
|---|---|
| [ai-core](ai-core/) | SAP AI Core runtime, training, serving, metrics, utilities, and RPT 1 |
| [joule-joule-studio](joule-joule-studio/) | Joule Studio agents and skills |
| [rag](rag/) | Retrieval augmented generation on SAP data (HANA vector engine, GenAI Hub) |
| [agentic-ai](agentic-ai/) | Agent orchestration and agent architecture labs |
| [mcp-a2a](mcp-a2a/) | MCP servers and agent interoperability |
| [build-apps-bpa](build-apps-bpa/) | SAP Build apps and process automation, CAP apps |
| [data-ai](data-ai/) | SAP data plus AI experiments (BDC Delta Share on Databricks, HANA Cloud ML) |
| [infrastructure-ai](infrastructure-ai/) | AI assisted SAP Basis and operations (Basis Copilot, patching, diagnostics, BTP ops) |
| [architecture](architecture/) | Cross lab architecture notes |
| [docs](docs/) | Supporting documentation and the old to new path mapping |

Two staging folders hold items waiting for a decision:

* `_e2e-candidates/`: complete business solutions (Email to Order, Invoice copilot) that fit the planned End to End Labs repository.
* `_pending-learning/`: generic framework exercises (Claude API sessions, n8n triage) that fit the planned learning repository.

## Featured labs

* Basis Copilot: Google ADK and Gemini agent for SAP Basis operations ([infrastructure-ai](infrastructure-ai/basis-copilot/))
* Joule Studio 2 Intelligent Collections Orchestrator ([joule-joule-studio](joule-joule-studio/collections-orchestrator/))
* Cashflow forecasting pipeline on SAP AI Core ([ai-core](ai-core/cashflow-forecast/))
* MCP servers for S/4HANA, cashflow, and procurement ([mcp-a2a](mcp-a2a/))
* Vendor master data quality RAG ([rag](rag/vendor-mdq-copilot/))
* BDC Delta Share ML labs on Databricks ([data-ai](data-ai/databricks-labs/))

## Related repositories

Databricks, SAP Datasphere and BDC, Google Vertex AI, and AWS Bedrock work are maintained in separate repositories under github.com/srini118us.
