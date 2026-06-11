# Joule Studio 2.0 Evaluation Lab — Intelligent Collections Orchestrator

Multi-agent AR collections management built on SAP BTP Joule Studio 2.0 using SAP-provided agent templates.

## Overview

This lab evaluates SAP Joule Studio 2.0 capabilities by building a fully operational multi-agent orchestration system for Accounts Receivable collections. The primary objective was to validate the new SAP-provided agent templates introduced in the Joule Studio 2.0 wave (Sapphire 2026) on a real on-premise S/4HANA backend.

## Architecture

```
User query
    │
    ▼
Collections Orchestrator (Supervisor Agent — SAP template)
    │
    ├── Overdue Assessment Agent (SAP template)
    │       └── Get Customer Overdue skill → FAR_CUSTOMER_LINE_ITEMS (S/4HANA)
    │
    ├── Delivery Block Agent (SAP template)
    │       ├── Read Open Sales Orders skill → API_SALES_ORDER_SRV GET
    │       └── Set Delivery Block skill    → API_SALES_ORDER_SRV PATCH
    │
    ├── Dispute Case Agent (SAP template)
    │       └── Create Dispute Case skill → API_BUSINESS_PARTNER
    │
    └── Promise to Pay Agent (SAP template)
            └── Create Promise to Pay skill → API_BUSINESS_PARTNER/to_Customer
```

## What Was Validated (Joule Studio 2.0)

- SAP-provided agent templates available in the Create dialog — 2.0 wave confirmed
- Templates produce agentic multi-step reasoning (Decompose → Plan → Route)
- Model-agnostic operation: Claude Sonnet 4 (anthropic--claude-4-sonnet) confirmed as active model
- Human-in-loop confirmation gate fires before any write action
- Real S/4HANA data flowing through the agent pipeline (47s execution, not hallucination)

## Stack

| Layer | Component |
|---|---|
| Agent builder | SAP Build Joule Studio 2.0 |
| AI model | Claude Sonnet 4 (Anthropic via SAP GenAI Hub) |
| Actions | SAP Build Actions (3 projects) |
| Connectivity | BTP Connectivity Service + SAP Cloud Connector |
| Backend | SAP S/4HANA On-Premise, Client 100 |
| Deployment | PG Shared Environment |

## Project Contents

| File | Description |
|---|---|
| `Intelligent Collections Orchestrator.mtar` | Exported Joule Studio project (deploy-ready) |
| `Intelligent Collections Orchestrator_translation*.zip` | Translation bundle |

## Key Findings

1. SAP-provided templates accelerate agent description and expertise authoring significantly
2. Joule Studio formula editor has a type-inference bug for OData filter construction — use the SAP Build Actions Condition Editor instead
3. `API_OPLACCTGDOCITEMCUBE_SRV` is an analytical cube unsuitable for open item queries — use `FAR_CUSTOMER_LINE_ITEMS` (FBL5N equivalent)
4. BTP destination hostname must match Cloud Connector virtual host exactly including domain suffix
5. Timeline logs are the only reliable way to confirm real tool execution vs hallucination

## Status

Deployed and Active — PG Shared Environment — June 2026

---

*SAP BTP AI Portfolio · Srinivasa Dasari*
