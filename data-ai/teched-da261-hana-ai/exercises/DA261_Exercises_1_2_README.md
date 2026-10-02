# TechEd 2025 DA261 - Exercises 1 & 2: Complete Lab Guide

**Workshop:** Unlocking AI-driven Insights from Business Data in SAP HANA Cloud  
**Author:** Srinivasa Dasari (Srini)  
**Date:** April 15, 2026  
**Repository:** [github.com/SAP-samples/teched2025-DA261](https://github.com/SAP-samples/teched2025-DA261)

---

## Overview

This lab covers SAP HANA Cloud's AI capabilities through hands-on exercises:

| Exercise | Topic | Key Technology |
|----------|-------|----------------|
| **Ex 1** | Outlier Analysis on ACDOCA | PAL Isolation Forest |
| **Ex 2.1** | Exploring Consumer Complaints | HANA DataFrames |
| **Ex 2.3** | Vector Similarity Search | REAL_VECTOR, COSINE_SIMILARITY |
| **Ex 2.4** | Classification with AutoML | PAL Random Forest |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│  SAP HANA Cloud                                                     │
│  ┌──────────────┐    ┌─────────────┐    ┌──────────────────────┐   │
│  │  Data Tables │───▶│  PAL Engine │───▶│  ML Models           │   │
│  │  ACDOCA      │    │  - Isolation│    │  - Anomaly Detection │   │
│  │  Complaints  │    │  - Random   │    │  - Classification    │   │
│  │  Vectors     │    │    Forest   │    │  - Predictions       │   │
│  └──────────────┘    └─────────────┘    └──────────────────────┘   │
│         ▲                                         │                 │
│         │            REAL_VECTOR                  │                 │
│         │         ┌─────────────┐                 │                 │
│         └─────────│ Vector      │◀────────────────┘                 │
│                   │ Engine      │                                   │
│                   │ COSINE_SIM  │                                   │
│                   └─────────────┘                                   │
└─────────────────────────────────────────────────────────────────────┘
                           ▲
                           │ hana-ml SDK
                           │
                    ┌──────┴──────┐
                    │ Python      │
                    │ WSL Ubuntu  │
                    └─────────────┘
```

**Key Insight:** Data never leaves HANA. ML algorithms execute inside the database.

---

## Environment Setup

### Prerequisites
- HANA Cloud Free Tier instance
- WSL Ubuntu with Python 3.12
- hana-ml, scikit-learn packages

### Starting the Environment

```bash
# Start Ubuntu WSL
wsl -d Ubuntu

# Navigate and activate
cd /mnt/c/Users/nivas/repos/teched2025-DA261/exercises
source .venv/bin/activate
```

### PAL User Setup (Required)

DBADMIN cannot grant PAL role to itself. Create a dedicated user:

```sql
CREATE USER PAL_USER PASSWORD Initial123 NO FORCE_FIRST_PASSWORD_CHANGE;
GRANT AFL__SYS_AFL_AFLPAL_EXECUTE TO PAL_USER;
GRANT SELECT, INSERT, UPDATE, DELETE ON SCHEMA DBADMIN TO PAL_USER;
GRANT CREATE ANY ON SCHEMA DBADMIN TO PAL_USER;
```

---

## Exercise 1: Outlier Analysis

### Objective
Detect anomalous financial transactions using PAL Isolation Forest.

### Code

```python
from hana_ml import dataframe
from hana_ml.algorithms.pal.preprocessing import IsolationForest

# Connect
conn = dataframe.ConnectionContext(
    address="hana-host.hanacloud.ondemand.com",
    port=443, user="PAL_USER", password="xxx",
    encrypt=True, sslValidateCertificate=False
)

# Train Isolation Forest
isof = IsolationForest(n_estimators=100, max_samples=166, bootstrap=False)
isof.fit(data=hdf_encoded, features=['DC_CODE', 'FAT_CODE', 'Amount (USD)'])

# Predict outliers
results = isof.predict(data=hdf_encoded_id, key='ID', contamination=0.05)
outliers = results.filter('LABEL = -1').collect()
```

### Results

| Metric | Value |
|--------|-------|
| Total Transactions | 500 |
| Filtered Slice | 166 |
| Outliers Detected | 9 (5.4%) |

**Patterns Found:**
1. High amounts ($16K-$19K)
2. Rare account types (Equity)
3. Sign mismatches (Debit with negative amount)

---

## Exercise 2.3: Vector Similarity Search

### Concept: Semantic vs Keyword Search

| Type | How It Works | Example |
|------|--------------|---------|
| **Keyword** | Match exact words | `LIKE '%fraud%'` finds only "fraud" |
| **Semantic** | Match meaning | "fraud" finds "theft", "scam", "unauthorized" |

### Implementation

```python
from sklearn.feature_extraction.text import TfidfVectorizer

# Create TF-IDF vectors (100 dimensions)
vectorizer = TfidfVectorizer(max_features=100, stop_words='english')
vectors = vectorizer.fit_transform(narratives).toarray()

# Store in HANA with REAL_VECTOR
CREATE TABLE COMPLAINT_VECTORS (
    COMPLAINT_ID NVARCHAR(20) PRIMARY KEY,
    NARRATIVE NCLOB,
    EMBEDDING REAL_VECTOR(100)
);

# Search using COSINE_SIMILARITY
SELECT COMPLAINT_ID, NARRATIVE,
    COSINE_SIMILARITY(EMBEDDING, TO_REAL_VECTOR(?)) AS SIMILARITY
FROM COMPLAINT_VECTORS
ORDER BY SIMILARITY DESC LIMIT 5;
```

### Search Results

| Query | Top Match | Similarity |
|-------|-----------|------------|
| "Someone stole my identity" | Identity theft complaint | 0.533 |
| "Calling me at work about debt" | Debt collector harassment | 0.613 |
| "Charged fees without telling" | Overdraft fees issue | 0.444 |

---

## Exercise 2.4: Classification

### Objective
Predict if complaint results in monetary relief (27% of cases).

### Model Comparison

| Model | Accuracy | True Positives | Recall |
|-------|----------|----------------|--------|
| Decision Tree | 73.7% | 1/81 | 1.5% |
| **Random Forest** | **93.7%** | **66/81** | **81%** |

### Feature Importance

```
PRODUCT_CODE:  23.5% ████████████
ISSUE_CODE:    23.2% ████████████
STATE_CODE:    22.3% ███████████
COMPANY_CODE:  18.3% █████████
DISPUTED:       6.8% ███
TIMELY:         5.8% ███
```

### Code

```python
from hana_ml.algorithms.pal.trees import RandomForestClassifier

rf_clf = RandomForestClassifier(n_estimators=50, max_depth=10)
rf_clf.fit(data=train_hdf, key='ID', features=features, label='TARGET')

# Predict
predictions = rf_clf.predict(data=train_hdf, key='ID', features=features)

# Feature importance
print(rf_clf.feature_importances_.collect())
```

---

## Key Concepts

### PAL (Predictive Analysis Library)
SAP's in-database ML engine. Algorithms run inside HANA - no data extraction needed.

### HANA DataFrame
Holds SQL query, not data. Data stays in HANA until `collect()` is called.

### Embedding Dimensions

| Model | Dimensions | Use Case |
|-------|------------|----------|
| TF-IDF (this lab) | 100 | Simple, fast |
| SAP NEB | 768 | HANA native |
| OpenAI ada-002 | 1536 | Deep semantic |

### Model Evaluation

- **Accuracy:** Can be misleading with imbalanced data
- **Recall:** Of all positives, how many did we find?
- **Precision:** When we predict positive, how often are we correct?

---

## Challenges Resolved

| Issue | Resolution |
|-------|------------|
| Windows SSL failure | Use WSL Ubuntu |
| PAL role not granted | Create PAL_USER, grant AFL role |
| Data type mismatch | Encode categorical to numeric |
| AutoML workload class | Use Random Forest directly |
| SAP NEB not available | Use TF-IDF vectors |

---

## Lab vs Production

| Aspect | Lab | Production |
|--------|-----|------------|
| Data | 300-500 synthetic rows | Millions of real records |
| Embeddings | TF-IDF (100 dims) | AI Core ada-002 (1536 dims) |
| Model Deploy | In-memory | AI Core serving endpoint |
| Integration | Manual Python | SAC, Joule, Work Zone |

---

## What We Achieved

- [x] Connected Python to HANA Cloud via WSL
- [x] Created PAL_USER with AFL execution role
- [x] Trained PAL Isolation Forest (detected 9 anomalies)
- [x] Stored TF-IDF vectors as REAL_VECTOR in HANA
- [x] Implemented semantic search with COSINE_SIMILARITY
- [x] Trained Random Forest classifier (93.7% accuracy, 81% recall)
- [x] Analyzed feature importance for business insights

---

## Next Steps

1. **Exercise 3:** Knowledge Graph with RDF/SPARQL
2. **AI Core Embeddings:** Deploy text-embedding-ada-002
3. **Joule Integration:** Natural language queries on vector data

---

## Reference Links

| Resource | URL |
|----------|-----|
| TechEd DA261 GitHub | [github.com/SAP-samples/teched2025-DA261](https://github.com/SAP-samples/teched2025-DA261) |
| hana-ml Docs | [help.sap.com/docs/HANA_CLOUD/hana-ml](https://help.sap.com/docs/HANA_CLOUD/hana-ml) |
| PAL Reference | [help.sap.com/docs/HANA_CLOUD/PAL](https://help.sap.com/docs/HANA_CLOUD/PAL) |
| HANA Vector Engine | [help.sap.com/docs/HANA_CLOUD/vector-engine](https://help.sap.com/docs/HANA_CLOUD/vector-engine) |
