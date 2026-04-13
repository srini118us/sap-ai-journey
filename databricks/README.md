# Databricks Labs

## Scope

ML and analytics labs using SAP Business Data Cloud (BDC) with Databricks. These labs demonstrate how to access SAP data via Delta Share and build ML models, dashboards, and monitoring solutions.

## Data Source

All labs connect to SAP data via **BDC Delta Share**:

```
bdc_share_vendorperformance.`s4_zvendorperformance_dp_srv:v1`.s4custom_vendorperformance
bdc_share_cash_flow.cashflow.cashflow
```

## Labs Overview

| Lab | Description | ML/Analytics | Status |
|-----|-------------|--------------|--------|
| [Lab A](#lab-a-vendor-delivery-risk) | Vendor Late Delivery Prediction | XGBoost + SHAP | ✅ Complete |
| [Lab C](#lab-c-journal-anomaly-detection) | Journal Entry Anomaly Detection | Anomaly Detection | 📋 In Progress |
| [Lab E](#lab-e-working-capital-dashboard) | Multi-Company Working Capital Dashboard | Analytics | 📋 In Progress |
| [Lab F](#lab-f-data-freshness-monitor) | Data Freshness Monitor | Monitoring | 📋 In Progress |
| [Lab G](#lab-g-unity-catalog-lineage) | Unity Catalog Lineage Explorer | Governance | 📋 In Progress |
| [Lab UC2/UC3](#lab-uc2uc3-cashflow-forecast) | Cashflow Forecasting | AutoTS Time Series | ✅ Complete |

---

## Lab A: Vendor Delivery Risk

### What It Does
Predicts which purchase orders are at risk of late delivery using vendor performance data from S/4HANA.

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                 VENDOR DELIVERY RISK MODEL                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   BDC Delta Share                                                │
│   (s4custom_vendorperformance)                                   │
│          │                                                       │
│          ▼                                                       │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │
│   │   EDA &     │ →  │  Feature    │ →  │  XGBoost    │         │
│   │ Viz (Seaborn│    │ Engineering │    │ Classifier  │         │
│   └─────────────┘    └─────────────┘    └─────────────┘         │
│                                                │                 │
│                                                ▼                 │
│                                         ┌─────────────┐          │
│                                         │    SHAP     │          │
│                                         │ Explainability│        │
│                                         └─────────────┘          │
│                                                │                 │
│                                                ▼                 │
│                                         JSON Export              │
│                                         (for AI Core/LLM)        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Features Used
- **Numerical**: Net Order Value, PO Quantity, Invoice/GR Quantities, Cycle Time
- **Categorical**: Vendor, Material Type/Group, Purchasing Org, Company, Plant, Country
- **Engineered**: Vendor historical late rate, average order value

### Model Metrics
| Metric | Value |
|--------|-------|
| Accuracy | ~0.95+ |
| Precision | High |
| Recall | High |
| ROC-AUC | ~1.0 |

### Key Output
- SHAP feature importance (what drives late delivery risk)
- JSON export for LLM verbalization (Option D integration)

---

## Lab UC2/UC3: Cashflow Forecast

### What It Does
Time series forecasting of monthly cashflow by company code using AutoTS.

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                 CASHFLOW FORECASTING                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   BDC Delta Share                                                │
│   (cashflow table)                                               │
│          │                                                       │
│          ▼                                                       │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │
│   │  Monthly    │ →  │   AutoTS    │ →  │  6-Month    │         │
│   │ Aggregation │    │  Training   │    │  Forecast   │         │
│   └─────────────┘    └─────────────┘    └─────────────┘         │
│                                                │                 │
│                                                ▼                 │
│                                         Delta Table              │
│                                   (workspace.srini_forecasts)    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Output
- 6-month cashflow forecast per company code
- Actuals + Forecast combined table
- Published to Delta Lake for SAC/Joule consumption

---

## Lab C: Journal Entry Anomaly Detection

Detects unusual journal entries that may indicate errors or fraud.
- Statistical anomaly detection
- Rule-based flagging

---

## Lab E: Multi-Company Working Capital Dashboard

Cross-company working capital analysis:
- DSO (Days Sales Outstanding)
- DPO (Days Payables Outstanding)
- DIO (Days Inventory Outstanding)

---

## Lab F: Data Freshness Monitor

Monitors BDC data pipeline health:
- Last refresh timestamps
- Row count deltas
- Alerting for stale data

---

## Lab G: Unity Catalog Lineage Explorer

Data governance and lineage:
- Table dependencies
- Column-level lineage
- Impact analysis

---

## Prerequisites

- Databricks workspace with BDC Delta Share configured
- Access to SAP BDC shares:
  - `bdc_share_vendorperformance`
  - `bdc_share_cash_flow`
- Python libraries: `xgboost`, `shap`, `autots`, `scikit-learn`

## How to Run

1. Open Databricks workspace
2. Import notebook (`.py` file)
3. Attach to cluster with required libraries
4. Run cells sequentially

## Structure

```
databricks/
├── README.md                              # This file
├── Lab_A_Vendor_Delivery_Risk_SHAP.py     # XGBoost + SHAP
├── Lab_C_Journal_Entry_Anomaly_Detection.py
├── Lab_E_Multi_Company_WC_Dashboard.py
├── Lab_F_Data_Freshness_Monitor.py
├── Lab_G_Unity_Catalog_Lineage.py
└── Lab_UC2_UC3_Cashflow_Forecast.py       # AutoTS forecasting
```

## Integration Points

| Lab | Integrates With |
|-----|-----------------|
| Lab A | Option D (SHAP → LLM verbalization via AI Core) |
| Lab UC2/UC3 | SAC, Joule NLQ (forecast table) |
| Lab E | SAC Working Capital Story |

## Reference

- [SAP Business Data Cloud](https://help.sap.com/docs/business-data-cloud)
- [Databricks Delta Sharing](https://docs.databricks.com/delta-sharing/)
- [SHAP Documentation](https://shap.readthedocs.io/)
- [AutoTS Documentation](https://github.com/winedarksea/AutoTS)
