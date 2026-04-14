# PO-to-SO Automation Demo

## Scope

End-to-end automation that extracts Purchase Order data from PDF using SAP Document Information Extraction (DIE), then triggers an SAP Build Process Automation (SBPA) workflow to create a Sales Order in S/4HANA.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                   PO-TO-SO AUTOMATION FLOW                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌─────────────┐                                               │
│   │  Customer   │                                               │
│   │  PO (PDF)   │                                               │
│   └──────┬──────┘                                               │
│          │                                                       │
│          ▼                                                       │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │        SAP DOCUMENT INFORMATION EXTRACTION (DIE)         │   │
│   │                                                          │   │
│   │   Upload PDF → Extract Fields → Return Structured Data   │   │
│   │                                                          │   │
│   │   Header Fields:                                         │   │
│   │   • documentNumber, documentDate, deliveryDate           │   │
│   │   • senderName, grossAmount, currencyCode                │   │
│   │                                                          │   │
│   │   Line Item Fields:                                      │   │
│   │   • description, quantity, unitPrice                     │   │
│   │   • customerMaterialNumber                               │   │
│   │                                                          │   │
│   └────────────────────────┬────────────────────────────────┘   │
│                            │                                     │
│                            ▼                                     │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │         SAP BUILD PROCESS AUTOMATION (SBPA)              │   │
│   │                                                          │   │
│   │   Workflow: pOtoSOProcess                                │   │
│   │   Definition: us10.sap-btp-joule.socreationfrompo        │   │
│   │                                                          │   │
│   │   Context Payload:                                       │   │
│   │   {                                                      │   │
│   │     "purchaseordernumber": "PO2026001",                  │   │
│   │     "customername": "GlobalTech",                        │   │
│   │     "deliverydate": "2026-04-20",                        │   │
│   │     "materialnumber": "TG11",                            │   │
│   │     "quantity": 100,                                     │   │
│   │     "pocontent": "PO PO2026001 from GlobalTech"          │   │
│   │   }                                                      │   │
│   │                                                          │   │
│   └────────────────────────┬────────────────────────────────┘   │
│                            │                                     │
│                            ▼                                     │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │                     S/4HANA                              │   │
│   │                                                          │   │
│   │   Sales Order Created (VA01 equivalent)                  │   │
│   │                                                          │   │
│   └─────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Components

### DIE (Document Information Extraction)

| Component | Value |
|-----------|-------|
| API URL | `https://aiservices-dox.cfapps.us10.hana.ondemand.com` |
| Document Type | `purchaseOrder` |
| Auth | OAuth 2.0 client credentials |

### SBPA (Build Process Automation)

| Component | Value |
|-----------|-------|
| Workflow Definition | `us10.sap-btp-joule.socreationfrompo.pOtoSOProcess` |
| API Endpoint | `/workflow/rest/v1/workflow-instances` |
| Auth | OAuth 2.0 client credentials |

## Flow

| Step | Service | Action |
|------|---------|--------|
| 1 | DIE | Upload PDF, create extraction job |
| 2 | DIE | Poll job status until DONE |
| 3 | Python | Parse extraction result → context payload |
| 4 | SBPA | Trigger workflow with PO context |
| 5 | SBPA/S4 | Workflow creates Sales Order |

## Extracted Fields

### Header Fields

| Field | Description | Example |
|-------|-------------|---------|
| `documentNumber` | PO number | PO2026001 |
| `documentDate` | Issue date | 2026-04-13 |
| `deliveryDate` | Requested delivery | 2026-04-20 |
| `senderName` | Customer name | GlobalTech |
| `grossAmount` | Total value | 15000.00 |
| `currencyCode` | Currency | USD |

### Line Item Fields

| Field | Description | Example |
|-------|-------------|---------|
| `description` | Material description | Widget Pro |
| `quantity` | Order quantity | 100 |
| `unitPrice` | Price per unit | 150.00 |
| `customerMaterialNumber` | Material ID | TG11 |

## Configuration

### Environment Variables (.env)

```env
BPA_API_URL=https://spa-api-gateway-bpi-us-prod.cfapps.us10.hana.ondemand.com
BPA_AUTH_URL=https://sap-btp-joule.authentication.us10.hana.ondemand.com
BPA_CLIENT_ID=sb-xxx
BPA_CLIENT_SECRET=xxx
```

### DIE Credentials

Configured directly in script (from BTP service key for Document Information Extraction service).

## Quick Start

### Prerequisites

- Python 3.9+
- SAP BTP with DIE and SBPA services
- SBPA workflow deployed (`pOtoSOProcess`)
- S/4HANA system connected to SBPA

### Installation

```bash
cd sap-build/sbpa-workflows/po-to-so-demo
pip install -r requirements.txt
```

### Configuration

1. Create `.env` file with BPA credentials
2. Update DIE credentials in `po_to_so_demo.py`
3. Place customer PO PDF in the folder

### Run

```bash
python po_to_so_demo.py
```

### Expected Output

```
============================================================
PO-to-SO AUTOMATION: PDF → DIE → SBPA → S/4HANA
============================================================

[1] Uploading PDF to DIE: Customer_PO_GlobalTech_PO2026001.pdf
    Job ID: abc123...

[2] Waiting for extraction...
    Attempt 1: PENDING
    Attempt 2: RUNNING
    Attempt 3: DONE

[2b] Extracted Fields:
     purchaseordernumber: PO2026001
     customername: GlobalTech
     deliverydate: 2026-04-20
     materialnumber: TG11
     quantity: 100
     pocontent: PO PO2026001 from GlobalTech

[3] Triggering SBPA workflow...
    Payload: { ... }
    Status: 201
    Instance ID: xyz789...
    Workflow Status: RUNNING

============================================================
SUCCESS! Check SBPA Monitoring for workflow status.
============================================================
```

## Files

```
po-to-so-demo/
├── README.md                              # This file
├── po_to_so_demo.py                       # Main script
├── requirements.txt                       # Python dependencies
├── .env                                   # BPA credentials (git-ignored)
└── Customer_PO_GlobalTech_PO2026001.pdf   # Sample PO
```

| File | Purpose |
|------|---------|
| `po_to_so_demo.py` | DIE extraction + SBPA trigger logic |
| `requirements.txt` | httpx, python-dotenv |
| `.env` | BPA API credentials |

## Dependencies

```
httpx
python-dotenv
```

## Error Handling

| Error | Cause | Solution |
|-------|-------|----------|
| DIE extraction timeout | Large PDF / slow processing | Increase poll attempts |
| DIE extraction FAILED | Invalid document format | Check PDF is valid PO |
| BPA 401 | Invalid credentials | Verify .env credentials |
| BPA 404 | Wrong workflow definition | Check definitionId |

## Integration Points

| Integrates With | Purpose |
|-----------------|---------|
| Document Information Extraction | PDF field extraction |
| SAP Build Process Automation | Workflow orchestration |
| S/4HANA | Sales Order creation (via SBPA action) |

## Key Concepts

| Concept | Description |
|---------|-------------|
| DIE Job | Async extraction - upload returns job ID, poll for result |
| Document Type | `purchaseOrder` enables PO-specific field extraction |
| Workflow Instance | Single execution of SBPA workflow |
| Context Payload | Data passed to workflow at trigger time |

## Reference

- [Document Information Extraction](https://help.sap.com/docs/document-information-extraction)
- [SAP Build Process Automation API](https://help.sap.com/docs/build-process-automation)
- [SBPA Workflow REST API](https://api.sap.com/api/SPA_Workflow_Runtime/overview)
