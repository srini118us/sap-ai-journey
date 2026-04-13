# Agentic AI

## Scope

This section contains AI agents that autonomously perform tasks by combining LLMs with tools, APIs, and human-in-the-loop controls. These agents go beyond simple chat - they observe, plan, act, and learn.

## Why "Agentic AI"

Traditional AI answers questions. Agentic AI takes actions. These use cases demonstrate the shift from chatbots to autonomous systems that integrate with SAP and enterprise APIs.

## Use Cases

| # | Use Case | What It Does | Key Technology |
|---|----------|--------------|----------------|
| 1 | [Basis Ops Copilot](./basis-ops-copilot/) | Investigates SAP job failures, proposes remediation | LangGraph + OData |
| 2 | [Customer Churn Agent](./customer-churn-agent/) | Predicts churn, explains why, recommends actions | ML + GenAI Hub |
| 3 | [LangGraph Labs](./langgraph/) | Multi-agent patterns across SAP, GCP, AWS | LangGraph framework |

## Agent Architecture Pattern

```
┌─────────────────────────────────────────────────────────────────┐
│                     AGENTIC AI PATTERN                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   User Query                                                     │
│       ↓                                                          │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │
│   │   OBSERVE   │ →  │    PLAN     │ →  │     ACT     │         │
│   │ Fetch data  │    │ LLM reasons │    │ Call APIs   │         │
│   └─────────────┘    └─────────────┘    └─────────────┘         │
│                              ↑                  │                │
│                              └──────────────────┘                │
│                              (feedback loop)                     │
│                                                                  │
│   Human-in-the-Loop: Approve risky actions before execution     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Use Case Details

### Basis Ops Copilot
- **Problem**: SAP job failures require manual investigation
- **Solution**: Agent fetches failed jobs, analyzes logs, proposes fixes
- **Safety**: Human approval required for restart/cancel actions
- **API**: `APJ_JOB_MANAGEMENT_SRV` OData service

### Customer Churn Agent
- **Problem**: Identifying at-risk customers and taking action
- **Solution**: ML predicts churn, LLM explains and recommends
- **Pattern**: Predictive (ML) + Prescriptive (LLM)
- **API**: SAP GenAI Hub orchestration

### LangGraph Labs
- **uc1-sap-procurement**: PO fulfillment agent with S/4HANA
- **uc2-sap-infra**: Infrastructure monitoring agent
- **uc3-gcp-vertex**: Cross-cloud agent with GCP
- **uc4-aws-bedrock**: Cross-cloud agent with AWS

## Key Concepts

| Concept | Description |
|---------|-------------|
| LangGraph | State machine framework for building agents |
| Tool Calling | LLM decides which functions to invoke |
| Human-in-the-Loop | Pause for approval on risky actions |
| Safety Tiers | Green (auto), Yellow (approval), Red (blocked) |
| State Machine | Graph of nodes (actions) and edges (transitions) |

## Prerequisites

- SAP AI Core instance with GenAI Hub
- Python 3.10+
- LangGraph, LangChain libraries
- SAP system access (for OData APIs)

## Structure

```
agentic-ai/
├── README.md                    # This file
├── basis-ops-copilot/
│   ├── README.md
│   ├── job_failure_agent.py
│   ├── llm_client.py
│   ├── main.py
│   └── config.json
├── customer-churn-agent/
│   ├── README.md
│   ├── churn_agent.py
│   ├── genai_client.py
│   └── requirements.txt
└── langgraph/
    ├── uc1-sap-procurement/
    ├── uc2-sap-infra/
    ├── uc3-gcp-vertex/
    └── uc4-aws-bedrock/
```

## Reference

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [SAP AI Core Agents](https://help.sap.com/docs/ai-core)
- [TechEd AI160: LangGraph + AI Core](https://github.com/SAP-samples/teched2025-AI160)
