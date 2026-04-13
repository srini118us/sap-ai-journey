# Customer Churn Agent

## Scope

ML + GenAI agent that predicts customer churn, explains the risk factors, and recommends retention actions. Demonstrates the shift from predictive to prescriptive AI.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                  CUSTOMER CHURN AGENT                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  "Analyze customer CUST-1001 for churn risk"                    │
│                         │                                        │
│                         ▼                                        │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  STEP 1: Get Customer Data                               │   │
│  │  Source: SAP S/4HANA / CRM (simulated)                   │   │
│  │  Output: tenure, spend, tickets, contract, etc.          │   │
│  └──────────────────────────────────────────────────────────┘   │
│                         │                                        │
│                         ▼                                        │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  STEP 2: ML Prediction (PREDICTIVE)                      │   │
│  │  Model: Random Forest / SAP RPT-1                        │   │
│  │  Output: 78% churn probability, HIGH risk                │   │
│  └──────────────────────────────────────────────────────────┘   │
│                         │                                        │
│                         ▼                                        │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  STEP 3: LLM Explanation (DIAGNOSTIC)                    │   │
│  │  Model: GPT-4o via GenAI Hub                             │   │
│  │  Output: "High risk due to low tenure + high tickets"    │   │
│  └──────────────────────────────────────────────────────────┘   │
│                         │                                        │
│                         ▼                                        │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  STEP 4: LLM Recommendations (PRESCRIPTIVE)              │   │
│  │  Output: Personalized retention actions                  │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Credentials

```bash
# Create .env file with SAP AI Core credentials
# Get these from BTP Cockpit → AI Core → Service Keys

AUTH_URL=https://xxx.authentication.us10.hana.ondemand.com
CLIENT_ID=your_client_id
CLIENT_SECRET=your_client_secret
AI_API_URL=https://api.ai.prod.us-east-1.aws.ml.hana.ondemand.com/v2
```

### 3. Run the Agent

```bash
# Full demo (requires GenAI Hub credentials)
python churn_agent.py

# Quick test (ML only, no LLM needed)
python churn_agent.py --quick

# Mock mode (no credentials needed)
python churn_agent.py --mock
```

## Files

| File | Purpose |
|------|---------|
| `churn_agent.py` | Main agent orchestrating ML + LLM |
| `churn_agent_s4.py` | S/4HANA integrated version |
| `genai_client.py` | SAP GenAI Hub API client |
| `rag_client.py` | RAG/grounding client |
| `email_classifier.py` | Email classification module |
| `s4hana_client.py` | S/4HANA OData client |
| `requirements.txt` | Python dependencies |

## AI Spectrum Demonstrated

| Type | Question | This Agent |
|------|----------|------------|
| **Descriptive** | What happened? | - |
| **Diagnostic** | Why? | LLM explains risk factors |
| **Predictive** | What will happen? | ML predicts churn probability |
| **Prescriptive** | What to do? | LLM recommends retention actions |

## Key Concepts

| Concept | Description |
|---------|-------------|
| GenAI Hub | SAP's managed LLM gateway |
| Orchestration | Combining ML predictions with LLM reasoning |
| Grounding | RAG with enterprise documents |
| Tool Calling | LLM invoking Python functions |

## Prerequisites

- SAP AI Core instance with GenAI Hub
- Python 3.10+
- GenAI Hub deployment (gpt-4o or similar)

## Reference

- [SAP GenAI Hub Documentation](https://help.sap.com/docs/ai-core)
- [Orchestration Service](https://help.sap.com/docs/sap-ai-core/sap-ai-core-service-guide/orchestration)
