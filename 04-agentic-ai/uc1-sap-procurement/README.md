# UC1: SAP Procurement Agent

## Scope

Production-ready LangGraph agent that handles purchase order queries and policy lookups with S/4HANA integration, RAG-based policy search, and human-in-the-loop approval workflow via SAP Build Process Automation.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                   PROCUREMENT AGENT GRAPH                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   User Query                                                     │
│       │                                                          │
│       ▼                                                          │
│   ┌─────────────┐                                                │
│   │ GUARDRAILS  │  PII masking, input validation,               │
│   │             │  prompt injection detection                    │
│   └──────┬──────┘                                                │
│          │                                                       │
│          ▼                                                       │
│   ┌─────────────┐                                                │
│   │   ROUTER    │  LLM-based intent classification              │
│   │  (GPT-4o)   │  → po_query / policy_lookup / general         │
│   └──────┬──────┘                                                │
│          │                                                       │
│    ┌─────┴─────┬─────────────┐                                   │
│    │           │             │                                   │
│    ▼           ▼             ▼                                   │
│ ┌──────┐  ┌─────────┐  ┌──────────┐                              │
│ │ RAG  │  │  TOOLS  │  │ RESPOND  │                              │
│ │      │  │         │  │ (general)│                              │
│ └──┬───┘  └────┬────┘  └────┬─────┘                              │
│    │           │            │                                    │
│    │           ▼            │                                    │
│    │      ┌─────────┐       │                                    │
│    │      │  HITL   │       │                                    │
│    │      │ (>$50k) │       │                                    │
│    │      └────┬────┘       │                                    │
│    │           │            │                                    │
│    └───────────┼────────────┘                                    │
│                ▼                                                  │
│          ┌──────────┐                                            │
│          │ RESPOND  │                                            │
│          └────┬─────┘                                            │
│               │                                                   │
│               ▼                                                   │
│              END                                                  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Components

### 1. Guardrails Node
- **PII Masking**: SSN, credit cards, emails
- **Input Validation**: Length limits, sanitization
- **Injection Detection**: Blocks prompt injection attempts

### 2. Router Node (LLM-based)
- Uses GPT-4o-mini for intent classification
- Intents: `po_query`, `policy_lookup`, `general`
- Fallback to keyword matching if LLM fails

### 3. RAG Node
- **Vector Store**: ChromaDB with OpenAI embeddings
- **Content**: Procurement policies (approval thresholds, vendor requirements, payment terms)
- **Retrieval**: Top 3 similar chunks

### 4. Tools Node (S/4HANA)
| Tool | OData API | Purpose |
|------|-----------|---------|
| `get_purchase_order` | API_PURCHASEORDER_PROCESS_SRV | Fetch PO details |
| `list_purchase_orders` | API_PURCHASEORDER_PROCESS_SRV | List recent POs |
| `calculate_po_value` | API_PURCHASEORDER_PROCESS_SRV | Get PO amount for approval |

### 5. HITL Node (Human-in-the-Loop)
- **Threshold**: $50,000 (configurable via `HITL_APPROVAL_THRESHOLD`)
- **Action**: Triggers SAP BPA workflow for high-value POs
- **Approval Levels**: Auto → Manager → Director → VP → CFO

### 6. SAP BPA Integration
- Triggers workflow instance via REST API
- Passes PO context (amount, vendor, release code)
- Returns workflow instance ID for tracking

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Create `.env` file:

```bash
# S/4HANA Connection
S4_BASE_URL=https://your-s4hana-host:port
S4_USER=your_user
S4_PASSWORD=your_password

# OpenAI (for RAG embeddings and router)
OPENAI_API_KEY=your_openai_key

# SAP BPA (optional - for HITL workflow)
BPA_API_URL=https://spa-api-gateway.cfapps.us10.hana.ondemand.com
BPA_AUTH_URL=https://your-tenant.authentication.us10.hana.ondemand.com
BPA_CLIENT_ID=your_client_id
BPA_CLIENT_SECRET=your_client_secret
BPA_DEFINITION_ID=your_workflow_definition_id

# HITL Threshold
HITL_APPROVAL_THRESHOLD=50000
```

### 3. Run the Agent

```bash
# Full interactive mode
python lab11_uc1_agent.py

# Test specific PO
python test_s4hana.py

# Test BPA integration
python test_bpa.py
```

## Sample Queries

| Query | Intent | Action |
|-------|--------|--------|
| "What are the approval thresholds?" | policy_lookup | RAG search |
| "Show PO 4500000001" | po_query | S/4HANA API call |
| "List purchase orders over $50,000" | po_query | S/4HANA + filter |
| "Hello, what can you help with?" | general | Direct response |

## Files

| File | Purpose |
|------|---------|
| `lab11_uc1_agent.py` | Main LangGraph agent (all components) |
| `Lab11_UC1_LangGraph_Walkthrough.ipynb` | Step-by-step tutorial |
| `Lab11_UC1_PO_Fulfillment_Agent.ipynb` | Full demo notebook |
| `Lab11_UC1_Hands_On_Guide.docx` | Documentation |
| `test_s4hana.py` | Test S/4HANA connection |
| `test_bpa.py` | Test BPA workflow trigger |
| `test_bpa_trigger.py` | BPA trigger test |
| `test_release.py` | Release strategy test |
| `procurement_agent_graph.png` | Generated graph diagram |

## Procurement Policies (RAG Content)

The agent has knowledge of:
- **Approval Thresholds**: $10k (manager) → $50k (director) → $100k (VP) → $500k (CFO)
- **Vendor Requirements**: Registration, tax ID, compliance certification
- **Payment Terms**: Net 15/30/45/60 by vendor category
- **Three-Way Match**: PO + Goods Receipt + Invoice (tolerances: qty ±5%, price ±2%)
- **Emergency Purchases**: Max $25k, CFO notification within 24h

## Key Concepts

| Concept | Implementation |
|---------|----------------|
| StateGraph | LangGraph state machine with typed state |
| Conditional Edges | Dynamic routing based on intent |
| Tool Calling | @tool decorator for S/4HANA functions |
| RAG | ChromaDB + OpenAI embeddings |
| HITL | Approval workflow via SAP BPA |
| Checkpointing | MemorySaver for conversation history |

## Reference

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [SAP Purchase Order API](https://api.sap.com/api/API_PURCHASEORDER_PROCESS_SRV)
- [SAP Build Process Automation](https://help.sap.com/docs/build-process-automation)
- [TechEd AI160](https://github.com/SAP-samples/teched2025-AI160)
