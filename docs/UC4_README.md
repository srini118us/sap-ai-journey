# UC4 — Intelligent Procurement Agent (SAP AI Journey)

**End-to-end use case combining live S/4HANA data with a custom XGBoost model, delivered through a Joule Studio agent.**

## Architecture at a glance

```
User (chat)
     │
     ▼
┌─────────────────────────────────────────┐
│ Joule Agent: Risk Analyzer Agent        │
│  (Gemini 3.5 Flash)                     │
└──┬──────────────┬──────────────┬───────┘
   ▼              ▼              ▼
getDelayed    getPurchase    getSupplier
Purchase      Order          RiskScore
Orders        Suppliers      (calls AI Core)
   │              │              │
   ▼              ▼              ▼
S/4HANA (v2 OData)              AI Core deployment
Private Cloud                   XGBoost model (KServe / FastAPI)
                                    ▲
                        ┌───────────┴─────────┐
                        │ S3 (dataset, model) │
                        │ Docker (images)     │
                        │ GitHub (this repo)  │
                        └─────────────────────┘
```

## Status (Aug 21 2026)

| Step | Component | Status |
|---|---|---|
| 1 | Baseline Joule agent + 2 S/4 skills (supplier leaderboard from live data) | ✅ COMPLETE |
| 2 | XGBoost model trained + served on AI Core, callable via HTTPS | ✅ COMPLETE |
| 3 | Joule skill `getSupplierRiskScore` wrapping AI Core inference | ⚠️ Runtime 0ms short-circuit — investigating |
| 4 | Datasphere semantic view | ⏳ Planned |
| 5 | SAC scorecard | ⏳ Planned |
| 6 | SBPA >1M approval workflow | ⏳ Planned |
| 7 | BDC / Databricks comparative deployment (stretch) | ⏳ Optional |

## Repo layout (relevant to this use case)

```
supplier-prediction-tutorial/
├── data/                            # Synthetic training data + generator
│   ├── generate_data.py
│   └── training_data.csv            # 10k rows, 13 features + label
├── training/
│   ├── train.py                     # XGBoost trainer
│   ├── requirements.txt
│   └── Dockerfile
├── serving/
│   ├── serve.py                     # FastAPI on port 9001 (/v2/predict + /healthz)
│   ├── requirements.txt
│   └── Dockerfile
├── supplier-prediction-train.yaml   # AI Core WorkflowTemplate (v1.1 — has artifact bindings)
├── supplier-prediction-serve.yaml   # AI Core ServingTemplate
└── README.md                        # Detailed step-by-step for this component

scripts/
└── test-predict.ps1                 # PowerShell smoke test against deployed endpoint

docs/
└── UC4_Handoff_Aug21.docx           # Full architecture + build log + screenshots
```

## Key lessons (article-worthy)

1. **AI Core is a three-contracts orchestrator.** It hosts none of your code, data, or model. Every failure is one of three named-thing mismatches (registry secret, object store secret, git/YAML).

2. **A workflow template without `inputs.artifacts` / `outputs.artifacts` trains a model into the void.** The pod runs, exits, and nothing survives — no S3 upload, no model artifact registration. This was the fix in commit `c0034cc`.

3. **Build-from-Scratch actions require output lists named after HTTP status codes** (e.g., `200`). Lists named `default` or `success` compile to no consumable schema; the editor error is "invalid code".

4. **Joule Studio uses destination environment variables as the runtime binding mechanism** — defined in Project Properties → Environment Variables, mapped to real BTP destinations at deploy time. The shipped Procurement Risk Analyzer template hides this step by pre-creating the S4H_Dest variable.

5. **Every OData v2 `Edm.Time` field arrives as an ISO 8601 duration** (`PT00H00M00S`) — set API Format to None on the action's output schema, otherwise validation fails.

6. **In PowerShell, single-quote credentials containing `$`, `|`, or `!`** — double quotes silently mangle them.

## Deployed endpoint (Aug 21 2026)

- **Deployment ID:** `dd779af933dbd298`
- **URL:** `https://api.ai.prod.us-east-1.aws.ml.hana.ondemand.com/v2/inference/deployments/dd779af933dbd298/v2/predict`
- **Auth:** OAuth2 client_credentials against XSUAA `/oauth/token`
- **Required header:** `AI-Resource-Group: myresourcegroup`
- **Model:** XGBoost binary classifier, accuracy 0.661 on synthetic data
- **Note:** the double `/v2` is correct — AI Core gateway path (`/v2/inference/...`) + FastAPI route (`/v2/predict`).

See `scripts/test-predict.ps1` for a working smoke test.

## References

- SAP Community — Custom Agentic Chatbot with SAP AI Core and Joule Studio Part 3(1)
- SAP-samples/teched2025-AI163 exercise 4 (destination environment variable pattern)
- SAP RIG — Building a Procurement Agent for S/4HANA Cloud Private Edition (baseline)

Full bibliography and build log in `docs/UC4_Handoff_Aug21.docx`.
