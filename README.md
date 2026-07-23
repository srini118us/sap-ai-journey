# Enterprise AI Engineering on SAP — GCP, Databricks, and Modern LLM Tooling

A working portfolio of applied AI, machine learning, and agentic systems for enterprise SAP landscapes. Projects span SAP AI Core, SAP Business Data Cloud, HANA Cloud, SAP Joule Studio, Google Cloud (Vertex AI, ADK), Databricks, and modern LLM frameworks. The focus is applied engineering: agents and models built end to end against real running SAP systems in personal lab and trial environments, using synthetic business data.

> Maturity is noted honestly per project, from working proofs of concept to prototypes and tutorials. Everything runs on personal lab, trial, and sandbox environments (SAP CAL, BTP trial, SAP Databricks trial) with synthetic or sample data: real systems rather than mocks, so the mechanics are genuine, but nothing here is a production or client landscape. All system identifiers shown are examples only.
---

## Featured Work

### Enterprise RAG on SAP HANA Cloud Vector Engine
A retrieval-augmented generation system for procurement approval decisions, built natively on the SAP HANA Cloud Vector Engine with SAP GenAI Hub. It answers compound business questions by combining unstructured policy documents with structured SAP business data in a single retrieval cycle — a "data gravity" pattern for SAP-centric AI. Hybrid retrieval (vector search plus SQL lookups) with grounded, cited answers.
`sap-procurement-rag/`

### Joule Studio 2.0 — Intelligent Collections Orchestrator
A multi-agent Accounts Receivable collections system built on SAP Joule Studio 2.0, validating the Sapphire 2026 agent templates against an on-premise S/4HANA backend. Demonstrates SAP-native multi-agent orchestration on current Joule tooling.
`sap-joulestudio/`

### Agentic AI for SAP Operations
Autonomous agents combining LLMs with tools and human-in-the-loop controls: a Basis help assistant (LangGraph + OData) for natural-language SAP Q&A, a Customer Churn agent (ML prediction plus GenAI Hub reasoning), and multi-agent LangGraph labs spanning SAP, GCP, and AWS.
`agentic-ai/`

### SAP Machine Learning on Databricks (BDC)
ML and analytics on SAP data accessed via BDC Delta Share. Complete: vendor late-delivery prediction (XGBoost + SHAP) and cashflow forecasting (AutoTS). In progress: journal-entry anomaly detection, multi-company working-capital analytics, data-freshness monitoring, and Unity Catalog lineage.
`databricks/`

### MLOps on SAP AI Core
The ML lifecycle operationalized on SAP BTP: experiment tracking and drift monitoring, Argo training pipelines, an inference web UI, and a payment-risk use case built on SAP's RPT-1 foundation model.
`mlops/`

### Model Context Protocol Servers for SAP
MCP servers exposing SAP systems to AI assistants (Claude, Joule): S/4HANA purchase orders (Kyma), cashflow data, and a procurement tool-layer for Joule Agents that shares the HANA Cloud schema behind the procurement RAG system.
`mcp/`

---

## Repository Structure

| Folder | Description |
|---|---|
| `sap-procurement-rag/` | Enterprise RAG on SAP HANA Cloud Vector Engine + GenAI Hub (hybrid retrieval, cited answers) |
| `sap-joulestudio/` | Joule Studio 2.0 multi-agent AR collections orchestrator (Sapphire 2026 templates, on-prem S/4HANA) |
| `agentic-ai/` | Autonomous agents — LangGraph + OData Basis help assistant, churn agent, multi-cloud LangGraph labs |
| `databricks/` | SAP ML on Databricks via BDC Delta Share (vendor risk, cashflow forecasting, anomaly, analytics) |
| `mlops/` | ML lifecycle on SAP AI Core (metrics, training, inference, RPT-1 payment risk) |
| `mcp/` | Model Context Protocol servers exposing SAP to AI assistants (Kyma / cashflow / procurement) |
| `applications/` | BTP Ops Intelligence — CAP + HANA Cloud dashboard with natural-language querying |
| `patching_agent_v2/` | SAP kernel patching orchestrator agent (ADK, tool coordination, human checkpoints) |
| `payment-delay/` | Vendor invoice late-payment prediction (XGBoost) packaged as an AI Core scenario (HANA training, KServe serving) |
| `foundations/` | SAP AI Core fundamentals — a progressive learning track (workflows, metrics, KServe serving, pipelines) |
| `aicore-utilities/` | Reusable SAP AI Core scripts — REST API client, connectivity tests, resource inventory, cost control |
| `sap-build/` | SAP Build Process Automation + Joule Studio — low-code automation (PO-to-SO workflow) |
| `supplier-prediction-tutorial/` | AI Core tutorial — purchase-order on-time delivery prediction (XGBoost + FastAPI) |
| `sap-diagnostic-agent/` | ADK agent for SAP ECC/Oracle health checks (prototype, mock data; real SSH/sqlplus planned) |
| `n8n-ticket-triage/` | Automation lab — AI support-ticket triage pipeline (n8n + Claude + Data Tables) |
| `house-price-tutorial/` | Minimal AI Core training example (scikit-learn regression) |

> An archive folder (`sap-btp-exports/`) holds re-importable exports of low-code BTP artifacts. Some folders contain earlier prototypes or in-progress work not listed above.

---

## Technology

| Layer | Tools |
|---|---|
| Agents / Orchestration | Google ADK, LangGraph, MCP, SAP Joule Studio, SAP Build Process Automation |
| LLMs / GenAI | Gemini (Vertex AI), OpenAI GPT, SAP GenAI Hub, SAP RPT-1 |
| RAG / Vector | SAP HANA Cloud Vector Engine, FAISS |
| Cloud / Data | SAP BTP, SAP AI Core, SAP Business Data Cloud, Google Cloud, Databricks |
| ML | scikit-learn, XGBoost, SHAP, Argo Workflows, KServe |
| SAP | S/4HANA, HANA Cloud, ABAP SDK for Google Cloud, OData |
| Languages | Python, CAP (Node.js) |

---

## Related Repositories

- **GCP Vertex AI Labs** — ADK, Vertex Pipelines, Agent Engine, SAP RAG assistant, A2A FinOps, MCP incident manager, Gemini Enterprise Agent Platform: https://github.com/srini118us/gcp-vertex-ai
- **AWS Bedrock Labs** — SAP-style procurement agents and enterprise guardrails on the Bedrock Converse API
- **SAP EarlyWatch Alert Analyzer** — AI analysis of EWA PDF reports (OpenAI Vision + semantic search): https://github.com/srini118us/SAP-EWA-Analyzer

---

## Notes on Scope and Confidentiality

- Projects use non-production, synthetic identifiers and sample data. No real enterprise system names, credentials, or business data are included.
- Maturity is stated honestly per project — some proven against live systems, others prototypes or tutorials.
- Each subfolder contains its own README with implementation detail.

## Author

[Srinivas](https://github.com/srini118us)
