# SAP-RPT-1 Payment Risk Predictor
## CAP + SAP Relational Foundation Model Demo

**Author:** Srinivasa | SAP AI Architect Learning Journey
**Purpose:** Demonstrates SAP-RPT-1 in-context learning integrated into a CAP application
**Use Case:** Predict payment risk (HIGH/MEDIUM/LOW) for new customers using historical FI-AR data

---

## What This Does

This CAP app shows how SAP-RPT-1 replaces traditional ML pipelines for tabular prediction:

```
Historical FI-AR Data (20 records with known risk)
         +
New Customer Records (8 records, risk unknown)
         ↓
    SAP-RPT-1 API (rpt.cloud.sap/api/predict)
         ↓
Payment Risk Predictions: HIGH / MEDIUM / LOW
```

No model training. No Docker. No Argo workflows. Just data + API call.

---

## Prerequisites

- Node.js 18+ installed
- `@sap/cds-dk` installed globally (`npm install -g @sap/cds-dk`)
- RPT-1 API token from https://rpt.cloud.sap (free, S-user login)

---

## Step 1: Setup

```bash
# Clone or copy project
cd rpt1-payment-risk

# Install dependencies
npm install

# Verify CDS is working
cds version
```

---

## Step 2: Get Your RPT-1 Token

1. Go to https://rpt.cloud.sap
2. Click **Documentation** (top right)
3. Log in with your **SAP S-user** credentials
4. Copy the **API Token** displayed on the docs page
5. Keep this handy — you'll paste it in the app UI

---

## Step 3: Run the App

```bash
# Start with sample data (SQLite in-memory)
cds watch
```

Open browser: **http://localhost:4004/app/index.html**

---

## Step 4: Run a Prediction

1. Paste your RPT-1 token into the **API Token** field
2. Click **▶ Run Prediction**
3. Watch RPT-1 classify 8 new customers as HIGH / MEDIUM / LOW risk
4. KPI cards update with the summary

---

## How RPT-1 In-Context Learning Works

The `runPrediction` action in `cat-service.js` builds this payload:

```json
{
  "rows": [
    // 20 context rows with known payment_risk labels
    { "customer_id": "C1001", "days_overdue_avg": "2", "payment_risk": "LOW" },
    { "customer_id": "C1002", "days_overdue_avg": "45", "payment_risk": "HIGH" },
    ...

    // 8 target rows with [PREDICT] placeholder
    { "customer_id": "C2001", "days_overdue_avg": "35", "payment_risk": "[PREDICT]" },
    { "customer_id": "C2002", "days_overdue_avg": "6",  "payment_risk": "[PREDICT]" },
    ...
  ]
}
```

RPT-1 learns from the labeled rows and fills in `[PREDICT]` for the target rows.

---

## API Details

| Item         | Value                                |
|--------------|--------------------------------------|
| Endpoint     | https://rpt.cloud.sap/api/predict    |
| Method       | POST                                 |
| Auth         | Bearer <token>                       |
| Content-Type | application/json                     |
| Payload Key  | `rows` (array of flat objects)       |
| Predict Flag | `[PREDICT]` in target column value   |

---

## Project Structure

```
rpt1-payment-risk/
├── db/
│   └── schema.cds              # PaymentHistory, NewCustomers, PredictionResults
├── srv/
│   ├── cat-service.cds         # Service + action + function definitions
│   └── cat-service.js          # RPT-1 API call logic
├── data/
│   ├── sap.rpt1.paymentrisk-PaymentHistory.csv   # 20 historical FI-AR records
│   └── sap.rpt1.paymentrisk-NewCustomers.csv     # 8 new customers to predict
├── app/
│   └── index.html              # Dashboard UI
├── package.json
└── README.md
```

---

## Extending This Demo

### Add Real S/4HANA Data
Replace the CSV files with data exported from:
- **FI-AR Aging Report** (transaction FBL5N)
- **Customer Credit Master** (transaction FD32)

### Deploy to BTP Cloud Foundry
```bash
cds add cf-manifest
cf push
```

### Integrate with GenAI Hub
Add a second action that calls GenAI Hub orchestration to generate
a natural language explanation of WHY a customer is high risk —
combining RPT-1's structured prediction with an LLM's explanation capability.

---

## Key Learning Points

1. **RPT-1 vs Traditional ML**: No training pipeline, no Docker, no Argo — just an API call
2. **In-Context Learning**: Labeled rows teach the model; `[PREDICT]` rows get predictions
3. **CAP Integration**: Standard `axios.post()` call from a CDS action handler
4. **SAP Data Fit**: FI-AR data (customer, amounts, overdue days) is exactly what RPT-1 was trained on

---

## Related Resources

- RPT-1 Playground: https://rpt.cloud.sap
- SAP RPT-1 Docs: https://help.sap.com/docs/sap-ai-core/generative-ai/sap-rpt-1
- CAP Documentation: https://cap.cloud.sap/docs
- SAP AI Core Tutorial: https://developers.sap.com/mission.ai-core.html
