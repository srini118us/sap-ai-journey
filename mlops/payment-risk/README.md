# Payment Risk Predictor (SAP-RPT-1)

## Scope

Demonstrates SAP's Relational Foundation Model (RPT-1) integrated with a CAP application for payment risk prediction. Unlike traditional ML pipelines that require training, RPT-1 uses in-context learning — historical FI-AR records with known outcomes teach the model patterns at inference time.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                   RPT-1 PAYMENT RISK FLOW                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │                   CAP APPLICATION                        │   │
│   │                                                          │   │
│   │   ┌───────────────┐       ┌───────────────┐             │   │
│   │   │ PaymentHistory│       │  NewCustomers │             │   │
│   │   │               │       │               │             │   │
│   │   │ 20 records    │       │ 8 records     │             │   │
│   │   │ KNOWN labels  │       │ [PREDICT]     │             │   │
│   │   └───────┬───────┘       └───────┬───────┘             │   │
│   │           │                       │                      │   │
│   │           └───────────┬───────────┘                      │   │
│   │                       │                                  │   │
│   │                       ▼                                  │   │
│   │           ┌───────────────────────┐                      │   │
│   │           │   runPrediction()     │                      │   │
│   │           │   (cat-service.js)    │                      │   │
│   │           └───────────┬───────────┘                      │   │
│   │                       │                                  │   │
│   └───────────────────────┼──────────────────────────────────┘   │
│                           │                                      │
│                           ▼                                      │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │                   RPT-1 API                              │   │
│   │           https://rpt.cloud.sap/api/predict              │   │
│   │                                                          │   │
│   │   INPUT:                                                 │   │
│   │   {                                                      │   │
│   │     "rows": [                                            │   │
│   │       // Context rows (known labels)                     │   │
│   │       {"customer_id": "C1001", "days_overdue_avg": "2",  │   │
│   │        "payment_risk": "LOW"},                           │   │
│   │       {"customer_id": "C1002", "days_overdue_avg": "45", │   │
│   │        "payment_risk": "HIGH"},                          │   │
│   │       ...                                                │   │
│   │       // Target rows (to predict)                        │   │
│   │       {"customer_id": "C2001", "days_overdue_avg": "35", │   │
│   │        "payment_risk": "[PREDICT]"}                      │   │
│   │     ]                                                    │   │
│   │   }                                                      │   │
│   │                                                          │   │
│   │   OUTPUT:                                                │   │
│   │   { "prediction": { "predictions": [                     │   │
│   │       { "payment_risk": [                                │   │
│   │           { "prediction": "HIGH", "confidence": 0.7 }    │   │
│   │       ]}                                                 │   │
│   │   ]}}                                                    │   │
│   │                                                          │   │
│   └─────────────────────────────────────────────────────────┘   │
│                           │                                      │
│                           ▼                                      │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │                 PredictionResults                        │   │
│   │                                                          │   │
│   │   customer_id │ predicted_risk │ confidence │ timestamp  │   │
│   │   ────────────┼────────────────┼────────────┼────────────│   │
│   │   C2001       │ HIGH           │ 70%        │ 2024-...   │   │
│   │   C2002       │ LOW            │ 85%        │ 2024-...   │   │
│   │                                                          │   │
│   └─────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## How RPT-1 Works

RPT-1 (Relational Pre-trained Transformer) is SAP's foundation model for tabular data. It uses **in-context learning**:

1. **Context Rows** — Historical records with known labels serve as few-shot examples
2. **Target Rows** — New records with `[PREDICT]` placeholder in the target column
3. **Pattern Learning** — Model learns relationships from context and predicts targets
4. **No Training Required** — Works like few-shot prompting for structured data

```
Traditional ML Pipeline        vs        RPT-1
─────────────────────                    ─────
Data Collection                          Data Collection
Feature Engineering                      ───────────────
Model Selection                          API Call with
Hyperparameter Tuning                    labeled examples
Training                                 ───────────────
Evaluation                               Predictions
Deployment
```

## Components

### CDS Entities

| Entity | Purpose | Records |
|--------|---------|---------|
| `PaymentHistory` | Historical FI-AR data with known risk | 20 |
| `NewCustomers` | Customers to predict | 8 |
| `PredictionResults` | Stored predictions | - |

### Service Actions

| Action/Function | Description |
|-----------------|-------------|
| `runPrediction(rpt1Token)` | Call RPT-1 API and store results |
| `getRiskSummary()` | Return HIGH/MEDIUM/LOW counts |

## Features (FI-AR Data)

| Feature | Type | Description |
|---------|------|-------------|
| `customer_id` | String | Unique identifier |
| `region` | String | Geographic region |
| `industry` | String | Business sector |
| `invoice_amount` | Number | Invoice value |
| `payment_terms` | String | Net 30, Net 60, etc. |
| `days_overdue_avg` | Number | Average days past due |
| `num_late_payments` | Number | Historical late count |
| `credit_limit` | Number | Customer credit limit |
| `outstanding_balance` | Number | Current AR balance |
| `payment_risk` | String | HIGH / MEDIUM / LOW |

## API Details

| Item | Value |
|------|-------|
| Endpoint | https://rpt.cloud.sap/api/predict |
| Method | POST |
| Auth | Bearer token (from rpt.cloud.sap) |
| Predict Flag | `[PREDICT]` in target column |
| Rate Limit | Yes (429 errors) |
| Timeout | 30 seconds |

## Response Handling

```javascript
// RPT-1 response structure
{
  "prediction": {
    "predictions": [
      {
        "payment_risk": [
          { "prediction": "HIGH", "confidence": 0.7 }
        ]
      }
    ]
  }
}

// Extract prediction
const riskEntry = predRow?.payment_risk?.[0] || {};
const predictedRisk = riskEntry.prediction || 'UNKNOWN';
const confidence = Math.round(riskEntry.confidence * 100) + '%';
```

## Quick Start

### Prerequisites

- Node.js 18+
- CDS CLI (`npm install -g @sap/cds-dk`)
- RPT-1 token from https://rpt.cloud.sap

### Installation

```bash
cd mlops/payment-risk
npm install
```

### Get RPT-1 Token

1. Go to https://rpt.cloud.sap
2. Click Documentation
3. Login with SAP S-user
4. Copy API token

### Run

```bash
cds watch
```

### Access

Open browser: http://localhost:4004/app/index.html

### Run Prediction

1. Paste RPT-1 token
2. Click "Run Prediction"
3. View results in dashboard

## Files

```
payment-risk/
├── README.md                # This file
├── package.json
├── app/
│   ├── index.html           # Dashboard UI
│   └── services.cds
├── db/
│   ├── schema.cds           # Entity definitions
│   └── data/
│       ├── ...PaymentHistory.csv
│       └── ...NewCustomers.csv
└── srv/
    ├── cat-service.cds      # Service definition
    └── cat-service.js       # RPT-1 integration logic
```

| File | Purpose |
|------|---------|
| `cat-service.js` | runPrediction action with RPT-1 API call |
| `schema.cds` | PaymentHistory, NewCustomers, PredictionResults |
| `index.html` | Dashboard with token input and results |

## Error Handling

| Error | Cause | Solution |
|-------|-------|----------|
| 400 | Missing token | Provide RPT-1 token |
| 401 | Invalid token | Get fresh token from rpt.cloud.sap |
| 429 | Rate limit | Wait and retry |
| 500 | Unexpected response | Check RPT-1 API status |

## Key Concepts

| Concept | Description |
|---------|-------------|
| In-Context Learning | Model learns from labeled examples at inference time |
| Foundation Model | Pre-trained on tabular data, generalizes to new domains |
| [PREDICT] Marker | Placeholder in target column for values to predict |
| Confidence Score | RPT-1's certainty (0.0 - 1.0) |
| Few-Shot Prompting | Technique applied to structured data |

## RPT-1 vs Traditional ML

| Aspect | Traditional ML | RPT-1 |
|--------|----------------|-------|
| Training | Required (hours/days) | None |
| Infrastructure | Docker, Argo, AI Core | API call |
| Feature Engineering | Critical | Minimal |
| Model Selection | Manual | Built-in |
| Deployment | Complex | None |
| Cost | Compute + storage | API calls only |

## SAP Data Fit

RPT-1 was trained on SAP business data patterns. Ideal use cases include:

- FI-AR payment prediction
- Vendor performance scoring
- Customer credit risk
- Inventory demand forecasting
- Any structured SAP data

## Integration Points

| Integrates With | Purpose |
|-----------------|---------|
| CAP Framework | Service layer |
| SQLite/HANA | Data persistence |
| GenAI Hub | Combine RPT-1 + LLM for explanations |
| SAC | Visualize predictions |

## Reference

- [SAP RPT-1](https://help.sap.com/docs/sap-ai-core/generative-ai/sap-rpt-1)
- [RPT-1 Playground](https://rpt.cloud.sap)
- [CAP Documentation](https://cap.cloud.sap/docs)
