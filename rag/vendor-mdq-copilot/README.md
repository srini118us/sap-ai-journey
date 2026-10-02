# Vendor Master Data Quality Copilot

RAG solution for detecting and explaining vendor master data quality issues in SAP environments. Grounded on HANA Cloud native vector engine plus SAP Gen AI Hub Orchestration.

Companion to [sap-procurement-rag](https://github.com/srini118us/sap-procurement-rag) in this repo.

## Business context

Every SAP client has vendor master data problems: duplicate vendors, missing tax IDs, blocked vendors still transacting, weekend round number postings that signal fraud. Traditional detection uses static SQL rules. This copilot combines:

1. Structured detection (SQL rules in QUALITY_RULES table)
2. Historical context (past issues and resolutions in QUALITY_ISSUES)
3. Policy grounding (4 corporate policies chunked and embedded)
4. LLM reasoning (Claude Sonnet via SAP Gen AI Hub Orchestration)

Result: natural language answers to questions like "why was vendor V0000147 flagged?" or "what is the unblock procedure for a sanctions related block?" backed by policy citations and data evidence.

## Architecture

```
User question
    v
SAP Gen AI Hub Orchestration
    +-- Grounding module -> HANA Cloud vector engine
    |                       (VENDORS, QUALITY_ISSUES, POLICY_CHUNKS)
    +-- LLM module -> Claude 4.5 Sonnet
    v
Grounded answer with citations
    v
SAP Optimizations evaluation
    (Groundedness, Answer Relevance, Correctness)
```

## Tech stack

| Layer | Technology |
|-------|------------|
| Vector store | SAP HANA Cloud native REAL_VECTOR (build 4.00.000.00) |
| Embedding models | NVIDIA Llama 3.2 NV EmbedQA 1b (2048 dim) + Text Embedding 3 Small (1536 dim) |
| LLM | Claude 4.5 Sonnet via SAP Gen AI Hub |
| Orchestration | SAP Gen AI Hub Orchestration Configuration |
| Evaluation | SAP Optimizations (native 25 evaluators) |
| Data gen | Python (deterministic, seed 42) |
| Data load | hdbcli (SAP HANA driver) |

## Repository structure

```
vendor-mdq-copilot/
├── README.md                          this file
├── LOAD_RUNBOOK.md                    step by step load instructions
├── 01_ddl.sql                         5 table definitions with vector columns
├── 02_generate_data.py                synthetic data generator (seed 42)
├── 03_load_data.sql                   880 INSERT statements
├── 04_generate_policies.py            4 policy PDF generator (reportlab)
├── 05_chunk_and_load_policies.py      PDF chunking to POLICY_CHUNKS
├── 06_embed_all.py                    dual embedding population
├── build_load_sql.py                  helper that regenerates 03_load_data.sql
├── data/
│   ├── vendors.csv                    150 vendors with intentional defects
│   ├── transactions.csv               500 invoice postings
│   ├── quality_rules.csv              30 MDG business rules (QR001 to QR030)
│   └── quality_issues.csv             200 historical issues (mix OPEN, RESOLVED)
└── policies/
    ├── 01_vendor_mdg_policy.pdf                  Vendor MDG Policy v4.2
    ├── 02_duplicate_detection_standard.pdf       Duplicate Detection Standard v3.1
    ├── 03_vendor_onboarding_compliance.pdf       Onboarding Compliance v5.0
    └── 04_blocked_vendor_management.pdf          Blocked Vendor Management v2.3
```

## Intentional data quality defects

The synthetic data ships with realistic MDQ defects for RAG to detect and explain:

| Defect | Count | Detection rule |
|--------|-------|----------------|
| Missing tax IDs on active vendors | 5 | QR002 |
| Duplicate address clusters (3 vendors each) | 5 groups | QR004 |
| Blocked vendors with recent transactions | 10 txns | QR005 |
| Round number weekend postings | 10 txns | QR010, QR011 |
| High risk score vendors | ~15 | QR008 |

## Setup

### Prerequisites

- SAP BTP subaccount with HANA Cloud instance (native vector engine, HANA Cloud QRC 2024.2 or later)
- SAP AI Core with Gen AI Hub subscription
- Two embedding model deployments running:
  - NVIDIA Llama 3.2 NV EmbedQA 1b (aicore-nvidia executable)
  - Text Embedding 3 Small (azure-openai executable)
- Python 3.9 or later

### Install

```bash
pip install hdbcli pypdf reportlab requests
```

### Environment variables

Create a `.env` file (do NOT commit):

```bash
HANA_HOST=<uuid>.hana.prod-us10.hanacloud.ondemand.com
HANA_PORT=443
HANA_USER=DBADMIN
HANA_PASSWORD=<from BTP Cockpit password reset>

AI_CORE_URL=https://api.ai.prod.us-east-1.aws.ml.hana.ondemand.com
AI_CORE_AUTH_URL=https://<subdomain>.authentication.us10.hana.ondemand.com/oauth/token
AI_CORE_CLIENT_ID=<from AI Core service key>
AI_CORE_CLIENT_SECRET=<from AI Core service key>
AI_CORE_RG=default

DEPLOY_ID_NVIDIA=<nvidia deployment id>
DEPLOY_ID_OPENAI=<text embedding 3 small deployment id>
```

## Load sequence

Run in order:

```bash
# 1. Schema (SAP HANA Database Explorer)
# Paste 01_ddl.sql, run in Database Explorer

# 2. Data generation (local)
python 02_generate_data.py
# Produces 4 CSVs in data/

# 3. Data load (SAP HANA Database Explorer)
# Paste 03_load_data.sql, run in Database Explorer
# Or use Import Data wizard per table

# 4. Policy PDF generation (local)
python 04_generate_policies.py
# Produces 4 PDFs in policies/

# 5. Chunk PDFs and load POLICY_CHUNKS (local)
python 05_chunk_and_load_policies.py

# 6. Populate all vector columns (local)
python 06_embed_all.py
```

## Verification queries

After all loads complete:

```sql
-- Row counts
SELECT 'VENDORS' AS TBL, COUNT(*) FROM VENDORS
UNION ALL SELECT 'TRANSACTIONS', COUNT(*) FROM TRANSACTIONS
UNION ALL SELECT 'QUALITY_RULES', COUNT(*) FROM QUALITY_RULES
UNION ALL SELECT 'QUALITY_ISSUES', COUNT(*) FROM QUALITY_ISSUES
UNION ALL SELECT 'POLICY_CHUNKS', COUNT(*) FROM POLICY_CHUNKS;

-- Expected: 150, 500, 30, 200, ~70

-- Vector population check
SELECT COUNT(*) AS EMBEDDED_VENDORS
FROM VENDORS
WHERE DESC_VEC_NVIDIA IS NOT NULL AND DESC_VEC_OPENAI IS NOT NULL;
-- Expected: 150
```

## Next phases (not yet in this repo)

- Phase 4: Orchestration Configuration with Grounding module pointing at HANA
- Phase 5: Deploy Orchestration to default resource group
- Phase 6: Evaluate with SAP Optimizations (Groundedness, Answer Relevance, Correctness)
- Phase 7: A/B compare (with grounding vs without, NVIDIA vs Text Embedding 3 Small)

## Key architectural decisions

**Dual embedding columns**: NVIDIA and Text Embedding 3 Small vectors stored side by side, allowing empirical comparison of data sovereignty (SAP Managed NVIDIA) versus quality (Azure hosted OpenAI) tradeoffs.

**Native REAL_VECTOR over external stores**: eliminates a network hop, simplifies operations, keeps data collocated with structured queries for hybrid retrieval.

**Policy grounding over prompt stuffing**: 4 policies chunked into ~70 sections instead of concatenated into system prompt. Scales to hundreds of policies.

**Chunk metadata preservation**: SECTION_NAME retained per chunk to enable precise citations in answers.

## Data sovereignty note

Data is fully synthetic (generator seed 42, reproducible). No client, employee, vendor, or transaction data from any real environment. Safe for public repository.
