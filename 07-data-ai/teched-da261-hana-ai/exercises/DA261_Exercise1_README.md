# TechEd 2025 DA261 - Exercise 1: Outlier Analysis on Financial Transaction Data

**Workshop:** Unlocking AI-driven insights from your business data in SAP HANA Cloud  
**Author:** Srinivasa Dasari (Srini)  
**Date:** April 15, 2026  
**Repository:** [github.com/SAP-samples/teched2025-DA261](https://github.com/SAP-samples/teched2025-DA261)

---

## Scope

This lab demonstrates SAP HANA Cloud's in-database machine learning using the Predictive Analysis Library (PAL). The exercise focuses on **outlier detection** in financial transaction data using **Isolation Forest**, an unsupervised anomaly detection algorithm that runs entirely inside the HANA database.

### Learning Objectives
- Understand HANA DataFrames and how compute stays inside the database
- Use PAL Isolation Forest for anomaly detection on financial data
- Interpret outlier scores and labels to identify suspicious transactions
- Handle PAL permission requirements in HANA Cloud
- Navigate HANA Cloud trial tier limitations

---

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Python Client  │────▶│   HANA Cloud     │────▶│  PAL Isolation  │
│  (hana-ml SDK)  │     │   Free Tier      │     │     Forest      │
└─────────────────┘     └──────────────────┘     └─────────────────┘
        │                       │                       │
        │  SQL Queries          │  Data Storage         │  ML Execution
        │  (no data leaves      │  + Processing         │  Inside HANA
        │   until collect())    │                       │
        ▼                       ▼                       ▼
   Orchestration           Data Layer              ML Engine
```

**Key Insight:** Data never leaves HANA until `collect()` is called. The HANA DataFrame holds SQL queries, not data.

---

## Systems Involved

| System | Details | Connection |
|--------|---------|------------|
| HANA Cloud | Free Tier, US10 region | `04aefaf5-...hanacloud.ondemand.com:443` |
| WSL Ubuntu | Python 3.12.3, hana-ml 2.28 | SSL encrypted via hdbcli |
| User | PAL_USER (created for PAL execution) | `AFL__SYS_AFL_AFLPAL_EXECUTE` role |

---

## Environment Setup

### Starting the Environment

```bash
# In PowerShell - start Ubuntu WSL
wsl -d Ubuntu

# Navigate to exercises and activate venv
cd /mnt/c/Users/nivas/repos/teched2025-DA261/exercises
source .venv/bin/activate

# Verify packages
pip list | grep -E 'hdbcli|hana-ml'
# hdbcli 2.28.19
# hana-ml 2.28.26031701
```

### Why WSL?
Windows `hdbcli` fails SSL handshake with HANA Cloud due to certificate chain issues. Linux handles SSL differently and bypasses this problem.

---

## Challenges and Resolutions

### 1. Missing DA261_SHARE Schema

**Problem:** TechEd workshop schema with pre-populated ACDOCA data doesn't exist in personal trial.

**Resolution:** Generated synthetic ACDOCA data (500 rows) using Python and uploaded via `create_dataframe_from_pandas()`.

### 2. PAL Role Not Granted to DBADMIN

**Error:** `PALUnusableError: Missing needed role - AFL__SYS_AFL_AFLPAL_EXECUTE`

**Root Cause:** HANA Cloud requires explicit PAL role grant. DBADMIN cannot grant to itself.

**Resolution:** Created PAL_USER via SQL Console:

```sql
CREATE USER PAL_USER PASSWORD Initial123 NO FORCE_FIRST_PASSWORD_CHANGE;
GRANT AFL__SYS_AFL_AFLPAL_EXECUTE TO PAL_USER;
GRANT SELECT, INSERT, UPDATE, DELETE ON SCHEMA DBADMIN TO PAL_USER;
GRANT CREATE ANY ON SCHEMA DBADMIN TO PAL_USER;
```

### 3. PAL Data Type Mismatch

**Error:** `Data types of input table do not match PAL specification`

**Root Cause:** PAL Isolation Forest requires numeric features. Categorical columns are NVARCHAR.

**Resolution:** Encoded categorical features using SQL CASE statements:

```python
hdf_encoded = hdf_acdoca_slice.select('*',
  ('CASE WHEN "Debit/Credit" = \'S\' THEN 1 ELSE 0 END', 'DC_CODE'),
  ('CASE WHEN "Financial Account Type" = \'P+L Statement\' THEN 1 
    WHEN ... = \'Balance Sheet Asset\' THEN 2 
    WHEN ... = \'Balance Sheet Liability\' THEN 3 ELSE 4 END', 'FAT_CODE'))
```

### 4. Trial Tier Limitations

| Feature | Status | Error |
|---------|--------|-------|
| SHAP Explainability (`show_explainer=True`) | NOT AVAILABLE | `ISOLATION_FOREST_EXPLAIN_ANY` not supported |
| Massive Parallel (`massive=True`) | NOT AVAILABLE | `MASSIVE_ISOLATION_FOREST` not supported |

---

## Lab Execution Results

### Data Summary

| Metric | Value |
|--------|-------|
| Total Transactions | 500 |
| Filtered Slice (CC01/PC002) | 166 |
| Outliers Detected | 9 (5.4%) |
| Normal Transactions | 157 |
| Contamination Parameter | 0.05 (5%) |

### Outliers Detected

```
ID    SCORE    LABEL   Details
──────────────────────────────────────────────────
77    0.6138    -1     Equity, $19,792, Debit but negative amount
12    0.5998    -1     P+L Statement, $19,053
49    0.5888    -1     Balance Sheet Asset, $18,248
90    0.5832    -1     P+L Statement, $19,475
30    0.5831    -1     Equity, $17,046
82    0.5822    -1     Balance Sheet Asset, $18,213
108   0.5726    -1     Balance Sheet Asset, $18,969
29    0.5697    -1     Balance Sheet Asset, $93 (unusual combo)
107   0.5683    -1     Balance Sheet Liability, $16,833
```

### Outlier Patterns Identified

1. **High Amount Transactions:** Most outliers have amounts between $16,000-$19,000
2. **Rare Account Types:** Equity appears in outliers (IDs 77, 30) - least common type
3. **Sign Mismatches:** ID 77 shows Debit indicator (S) but negative amount
4. **Unusual Combinations:** ID 29 flagged despite low amount ($93.31)

---

## Key Concepts

| Concept | Description |
|---------|-------------|
| **HANA DataFrame** | Holds SQL query, not data. Data stays in HANA until `collect()` |
| **PAL** | Predictive Analysis Library - SAP's in-database ML engine |
| **Isolation Forest** | Unsupervised anomaly detection. Outliers need fewer splits to isolate |
| **Contamination** | Expected % of outliers. 0.05 = algorithm expects ~5% anomalous |
| **LABEL** | Output: 1 = normal, -1 = outlier |
| **SCORE** | 0-1 anomaly score. Higher = more anomalous |

---

## Lab vs Production

| Aspect | Lab Environment | Production Environment |
|--------|-----------------|------------------------|
| Data | 500 synthetic ACDOCA rows | Millions of real S/4HANA entries |
| HANA Tier | Free Tier (limited PAL) | Standard/Enterprise (full PAL) |
| SHAP | Not available | Full explainability with REASON_CODE |
| Parallel | Not available | Massive parallel per G/L Account |
| Integration | Manual connection | BTP Destination, SAC, Joule |

---

## Code Reference

### Connect to HANA Cloud

```python
from hana_ml import dataframe

pal_conn = dataframe.ConnectionContext(
    address="04aefaf5-8823-4aef-b849-6e2bdfb3bd7b.hna1.prod-us10.hanacloud.ondemand.com",
    port=443,
    user="PAL_USER",
    password="Initial123",
    encrypt=True,
    sslValidateCertificate=False
)
print(f"Connected: {pal_conn.connection.isconnected()}")
```

### Create HANA DataFrame and Filter

```python
acdoca_hdf = pal_conn.table("ACDOCA", schema="DBADMIN")
hdf_acdoca_slice = acdoca_hdf.filter('"Company Code" = \'CC01\' AND "Profit Center"=\'PC002\'')
print(f"Slice has {hdf_acdoca_slice.count()} rows")
```

### Train Isolation Forest

```python
from hana_ml.algorithms.pal.preprocessing import IsolationForest

encoded_features = ['DC_CODE', 'FAT_CODE', 'Amount (USD)', 'Amount (Transaction)']
isof = IsolationForest(random_state=251104, n_estimators=100, max_samples=166, bootstrap=False)
isof.fit(data=hdf_encoded, features=encoded_features)
```

### Predict Outliers

```python
hdf_encoded_id = hdf_encoded.add_id()
outlier_results = isof.predict(
    data=hdf_encoded_id, 
    key='ID', 
    features=encoded_features, 
    contamination=0.05
)
print(outlier_results.filter('LABEL = -1').sort('SCORE', desc=True).collect())
```

---

## What We Achieved

- [x] Connected Python to HANA Cloud via WSL Ubuntu (bypassing Windows SSL issues)
- [x] Created synthetic ACDOCA financial transaction data (500 rows, 13 columns)
- [x] Configured PAL access by creating PAL_USER with AFL execution role
- [x] Encoded categorical features to numeric for PAL compatibility
- [x] Trained Isolation Forest model inside HANA using PAL
- [x] Identified 9 outliers (5.4%) with business-interpretable patterns
- [x] Documented trial tier limitations (no SHAP, no massive parallel)

---

## Next Steps

1. **Exercise 2 - Vector Search:** Use HANA Cloud vector engine with text embeddings for semantic search
2. **Exercise 3 - Knowledge Graph:** Create RDF triples and query with SPARQL for entity relationships
3. **Production Planning:** Test full PAL with SHAP explainability on real S/4HANA data

---

## Reference Links

| Resource | URL |
|----------|-----|
| TechEd DA261 GitHub | [github.com/SAP-samples/teched2025-DA261](https://github.com/SAP-samples/teched2025-DA261) |
| hana-ml Documentation | [help.sap.com/docs/HANA_CLOUD/hana-ml](https://help.sap.com/docs/HANA_CLOUD/hana-ml) |
| PAL Isolation Forest | [help.sap.com/docs/HANA_CLOUD/PAL](https://help.sap.com/docs/HANA_CLOUD/PAL) |
| HANA Cloud Free Tier | [developers.sap.com/tutorials/hana-cloud-deploying.html](https://developers.sap.com/tutorials/hana-cloud-deploying.html) |
