# SAP AI Journey

End-to-end SAP AI learning repository covering AI Core workflows, MLOps patterns, agentic AI, foundation models, and BTP integrations.

## Repository Structure

```
sap-ai-journey/
├── foundations/          # AI Core basics: Hello World, Metrics, Model Serving
├── mlops/                # MLOps: Experiment tracking, Training, Inference, RPT-1
├── agentic-ai/           # LangGraph agents, Joule copilots, multi-agent systems
├── databricks/           # BDC labs: XGBoost, SHAP, Cashflow forecasting
├── applications/         # Production apps: BTP Ops Intelligence dashboard
├── sap-build/            # SBPA workflows, Joule Studio
├── mcp/                  # Model Context Protocol servers
├── genai-hub/            # GenAI Hub orchestration (pending)
└── a2a/                  # Agent-to-Agent protocol (planned)
```

## Sections

### [Foundations](./foundations/)
AI Core fundamentals with progressive complexity.

| Lab | Description |
|-----|-------------|
| hello-world | Basic Argo workflow on AI Core |
| hello-metrics | Metrics API integration |
| model-serving | Deploy and serve ML models |
| multi-step-pipeline | Multi-step orchestration |

---

### [MLOps](./mlops/)
Complete ML lifecycle on SAP AI Core.

| Lab | Description |
|-----|-------------|
| aicore-metrics | Experiment tracking, drift monitoring |
| ml-training | Argo workflow for model training |
| inference-webui | Web UI with OAuth proxy |
| payment-risk | SAP-RPT-1 foundation model |

---

### [Agentic AI](./agentic-ai/)
Intelligent agents for SAP enterprise scenarios.

| Use Case | Description |
|----------|-------------|
| langgraph/uc1-sap-procurement | Invoice processing with HITL |
| basis-ops-copilot | Dual-agent SAP Basis troubleshooting |
| customer-churn-agent | AutoGen multi-agent churn analysis |

---

### [Databricks](./databricks/)
SAP BDC + Databricks ML labs.

| Lab | Description |
|-----|-------------|
| Lab A | Vendor delivery risk with XGBoost + SHAP |
| Lab C | Journal entry anomaly detection |
| Lab E | Multi-company working capital dashboard |
| Lab F | Data freshness monitor |
| Lab G | Unity Catalog lineage explorer |
| Lab UC2/UC3 | Cashflow forecasting with AutoTS |

---

### [Applications](./applications/)
Production BTP applications.

| App | Description |
|-----|-------------|
| btp-ops-intelligence | Operations dashboard with 9 OData endpoints |

---

### [SAP Build](./sap-build/)
Low-code automation and AI skills.

| Project | Description |
|---------|-------------|
| sbpa-workflows/po-to-so-demo | PDF → DIE → SBPA → S/4HANA |
| joule-studio | Joule Skills and Agents (pending) |

---

### [MCP](./mcp/)
Model Context Protocol servers for AI assistant integration.

| Server | Description |
|--------|-------------|
| kyma-mcp-server | S/4HANA Purchase Orders via MCP |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                      SAP AI ECOSYSTEM                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│   │  AI Core    │  │  GenAI Hub  │  │  Joule      │             │
│   │  (MLOps)    │  │  (LLMs)     │  │  (Skills)   │             │
│   └──────┬──────┘  └──────┬──────┘  └──────┬──────┘             │
│          │                │                │                     │
│          └────────────────┼────────────────┘                     │
│                           │                                      │
│                           ▼                                      │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │                    SAP BTP                               │   │
│   │                                                          │   │
│   │   ┌───────────┐  ┌───────────┐  ┌───────────┐           │   │
│   │   │   HANA    │  │   Cloud   │  │   Work    │           │   │
│   │   │   Cloud   │  │  Foundry  │  │   Zone    │           │   │
│   │   └───────────┘  └───────────┘  └───────────┘           │   │
│   │                                                          │   │
│   └─────────────────────────────────────────────────────────┘   │
│                           │                                      │
│                           ▼                                      │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │                  SAP BACKENDS                            │   │
│   │                                                          │   │
│   │   ┌───────────┐  ┌───────────┐  ┌───────────┐           │   │
│   │   │  S/4HANA  │  │    BDC    │  │ Datasphere│           │   │
│   │   │  (OData)  │  │  (Delta)  │  │   (SAC)   │           │   │
│   │   └───────────┘  └───────────┘  └───────────┘           │   │
│   │                                                          │   │
│   └─────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- SAP BTP account with AI Core entitlement
- Python 3.9+
- Node.js 18+ (for CAP apps)
- Docker (for AI Core workflows)

### Clone and Explore

```bash
git clone https://github.com/srini118us/sap-ai-journey.git
cd sap-ai-journey
```

### Run a CAP Application

```bash
cd applications/btp-ops-intelligence
npm install
cds watch
# Open http://localhost:4004
```

### Run a Python Lab

```bash
cd mlops/aicore-metrics
pip install -r requirements.txt
python sap_aicore_metrics_demo.py
```

### Deploy to AI Core

1. Push workflows to GitHub
2. Connect repo via AI Launchpad → Applications
3. Create configurations and executions

## Key Technologies

| Technology | Used For |
|------------|----------|
| SAP AI Core | ML training, serving, MLOps |
| SAP GenAI Hub | LLM orchestration, RAG |
| SAP Joule | Conversational AI skills |
| SAP CAP | Application development |
| SAP HANA Cloud | Persistence |
| SAP BDC | Delta Share data access |
| Databricks | ML on SAP data |
| LangGraph | Agentic AI workflows |
| FastMCP | MCP server framework |

## Reference

- [SAP AI Core](https://help.sap.com/docs/sap-ai-core)
- [SAP AI Launchpad](https://help.sap.com/docs/ai-launchpad)
- [SAP GenAI Hub](https://help.sap.com/docs/sap-ai-core/generative-ai-hub)
- [SAP Joule](https://help.sap.com/docs/joule)
- [SAP CAP](https://cap.cloud.sap/docs)
- [MCP Protocol](https://modelcontextprotocol.io/)
- [LangGraph](https://langchain-ai.github.io/langgraph/)
