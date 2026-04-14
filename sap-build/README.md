# SAP Build

## Scope

SAP Build suite demonstrations including SAP Build Process Automation (SBPA) workflows and Joule Studio integrations. This section covers low-code/no-code automation patterns and AI-assisted development.

## Use Cases

| # | Use Case | What It Demonstrates | Status |
|---|----------|---------------------|--------|
| 1 | [PO-to-SO Automation](./sbpa-workflows/po-to-so-demo/) | PDF extraction → Workflow → S/4HANA | ✅ Complete |
| 2 | Joule Studio | Joule Skills and Agents | ⏳ Pending export |

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      SAP BUILD SUITE                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │              SAP BUILD PROCESS AUTOMATION                │   │
│   │                                                          │   │
│   │   ┌───────────┐    ┌───────────┐    ┌───────────┐       │   │
│   │   │  Trigger  │ →  │  Process  │ →  │  Action   │       │   │
│   │   │           │    │           │    │           │       │   │
│   │   │ API/Form  │    │ Workflow  │    │ S/4HANA   │       │   │
│   │   │ Schedule  │    │ Decisions │    │ API Call  │       │   │
│   │   │ Event     │    │ Approvals │    │ Document  │       │   │
│   │   └───────────┘    └───────────┘    └───────────┘       │   │
│   │                                                          │   │
│   │   ┌───────────────────────────────────────────────┐     │   │
│   │   │               INTEGRATIONS                     │     │   │
│   │   │                                               │     │   │
│   │   │  • Document Information Extraction (DIE)      │     │   │
│   │   │  • GenAI Hub Actions                          │     │   │
│   │   │  • S/4HANA OData APIs                         │     │   │
│   │   │  • Destinations                               │     │   │
│   │   │                                               │     │   │
│   │   └───────────────────────────────────────────────┘     │   │
│   │                                                          │   │
│   └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │                    JOULE STUDIO                          │   │
│   │                                                          │   │
│   │   ┌───────────┐    ┌───────────┐    ┌───────────┐       │   │
│   │   │  Skills   │ →  │  Agents   │ →  │  Chat     │       │   │
│   │   │           │    │           │    │           │       │   │
│   │   │ CAP/OData │    │ Multi-    │    │ Joule     │       │   │
│   │   │ OpenAPI   │    │ Skill     │    │ Interface │       │   │
│   │   │ Actions   │    │ Chains    │    │           │       │   │
│   │   └───────────┘    └───────────┘    └───────────┘       │   │
│   │                                                          │   │
│   └──────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Use Case Details

### PO-to-SO Automation

**Purpose**: Automate Purchase Order to Sales Order creation using AI-powered document extraction.

**Flow**:
1. Customer sends PO as PDF
2. Document Information Extraction extracts structured data
3. SBPA workflow receives extracted fields
4. Workflow creates Sales Order in S/4HANA

**Technologies**: Python, DIE API, SBPA Workflow REST API

---

### Joule Studio (Pending)

**Purpose**: Create custom Joule Skills and Agents for conversational AI.

**Planned Demos**:
- Intelligent Maintenance Stock Validation Agent
- Multi-skill chains with GO/NO-GO decisions

**Status**: Waiting for BTP export role assignment to export configurations.

---

## Structure

```
sap-build/
├── README.md                    # This file
├── joule-studio/                # Joule Skills & Agents (pending export)
└── sbpa-workflows/
    └── po-to-so-demo/
        ├── README.md
        ├── po_to_so_demo.py     # DIE + SBPA integration
        ├── requirements.txt
        ├── .env                 # Credentials (git-ignored)
        └── Customer_PO_*.pdf    # Sample PO document
```

## SAP Build Components

| Component | Purpose | License |
|-----------|---------|---------|
| Build Process Automation | Workflow orchestration | Standard/Advanced |
| Build Apps | Low-code app development | Standard |
| Build Work Zone | Portal and workspaces | Standard |
| Joule Studio | AI skill builder | Foundation plan |

## Key Concepts

| Concept | Description |
|---------|-------------|
| Workflow Definition | Reusable process template |
| Workflow Instance | Single execution |
| Action | Integration step (API call, document generation) |
| Decision | Business rules evaluation |
| Trigger | Initiates workflow (API, form, schedule) |
| Skill | Joule capability (CAP service, OpenAPI) |
| Agent | Multi-skill orchestrator |

## Integration Patterns

| Pattern | Use Case | Example |
|---------|----------|---------|
| Document → Workflow | PDF processing | PO-to-SO |
| API → Workflow | External triggers | Webhook events |
| Workflow → S/4HANA | Backend actions | Create Sales Order |
| GenAI → Workflow | AI decisions | Classify and route |

## Reference

- [SAP Build Process Automation](https://help.sap.com/docs/build-process-automation)
- [Document Information Extraction](https://help.sap.com/docs/document-information-extraction)
- [Joule Studio](https://help.sap.com/docs/joule)
- [SBPA Workflow API](https://api.sap.com/api/SPA_Workflow_Runtime/overview)
