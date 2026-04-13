# MEGA LAB: Intelligent AI System

## Overview

This lab combines ML + GenAI to build enterprise AI solutions:

| Part | Topic | Status |
|------|-------|--------|
| **Part 1** | GenAI Hub API Calls | ✅ Created |
| **Part 2** | Churn Prevention Agent (ML + LLM) | ✅ Created |
| **Part 3** | Document Q&A with RAG | 📋 Tomorrow |
| **Part 4** | Email Classifier | 📋 Tomorrow |

---

## Quick Start

### 1. Setup Environment

```bash
# Navigate to mega_lab folder
cd C:\sap-ai-journey\mega_lab

# Create virtual environment
python -m venv venv
.\venv\Scripts\Activate  # Windows
# source venv/bin/activate  # Mac/Linux

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Credentials

```bash
# Copy template
copy .env.template .env

# Edit .env with your SAP AI Core credentials
# Get these from BTP Cockpit → AI Core → Service Keys
```

### 3. Run Part 1: Test GenAI Hub Connection

```bash
cd part1_genai_api
python genai_client.py
```

Expected output:
```
✓ Token obtained (expires in 12 hours)
--- Available Deployments ---
  • gpt-4o-mini: ... [RUNNING]
--- Test Chat ---
  Response: Hello from SAP GenAI Hub!
✅ GenAI Hub connection successful!
```

### 4. Run Part 2: Churn Prevention Agent

```bash
cd part2_churn_agent

# Quick test (ML only, no LLM needed)
python churn_agent.py --quick

# Full demo (requires GenAI Hub credentials)
python churn_agent.py

# Mock mode (no credentials needed)
python churn_agent.py --mock
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                CHURN PREVENTION AGENT                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  "Analyze customer CUST-1001 for churn risk"                │
│                         │                                    │
│                         ▼                                    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  STEP 1: Get Customer Data                           │   │
│  │  Source: SAP S/4HANA / CRM (simulated)              │   │
│  │  Output: tenure, spend, tickets, contract, etc.     │   │
│  └──────────────────────────────────────────────────────┘   │
│                         │                                    │
│                         ▼                                    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  STEP 2: ML Prediction (PREDICTIVE)                  │   │
│  │  Model: Random Forest / RPT-1                        │   │
│  │  Output: 78% churn probability, HIGH risk           │   │
│  └──────────────────────────────────────────────────────┘   │
│                         │                                    │
│                         ▼                                    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  STEP 3: LLM Explanation (DIAGNOSTIC)                │   │
│  │  Model: GPT-4 via GenAI Hub                         │   │
│  │  Output: "High risk because low tenure + high       │   │
│  │          tickets indicates onboarding issues..."    │   │
│  └──────────────────────────────────────────────────────┘   │
│                         │                                    │
│                         ▼                                    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  STEP 4: LLM Recommendations (PRESCRIPTIVE)          │   │
│  │  Output:                                             │   │
│  │  1. Immediate: Schedule success call                │   │
│  │  2. This week: Review all open tickets              │   │
│  │  3. This month: Offer training session              │   │
│  └──────────────────────────────────────────────────────┘   │
│                         │                                    │
│                         ▼                                    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  STEP 5: Generate Communication                      │   │
│  │  Output: Personalized retention email draft         │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Files Structure

```
mega_lab/
├── .env.template              # Credentials template
├── .env                       # Your credentials (create this)
├── requirements.txt           # Python dependencies
├── README.md                  # This file
│
├── part1_genai_api/
│   └── genai_client.py        # GenAI Hub API client
│
├── part2_churn_agent/
│   └── churn_agent.py         # ML + LLM churn prevention
│
├── part3_rag/                 # Coming tomorrow
│   └── (document_qa.py)
│
└── part4_email_classifier/    # Coming tomorrow
    └── (email_classifier.py)
```

---

## Key Concepts

### AI Spectrum (Interview Gold!)

| Type | Question | Technology | Example |
|------|----------|------------|---------|
| **Descriptive** | What happened? | Reports, SAC | "Sales were $2M" |
| **Diagnostic** | Why did it happen? | Analytics | "Due to supply issues" |
| **Predictive** | What will happen? | ML Models | "Customer X will churn" |
| **Prescriptive** | What should we do? | ML + LLM | "Offer 20% discount" |
| **Autonomous** | Do it for me | Agents | "Auto-send retention offer" |

### This Lab Demonstrates

- **Predictive**: ML model predicts churn probability
- **Prescriptive**: LLM explains why + recommends actions
- **Moving toward Autonomous**: Draft communications ready to send

---

## Troubleshooting

### "Token request failed"
- Check AUTH_URL format: `https://xxx.authentication.us10.hana.ondemand.com`
- Verify CLIENT_ID and CLIENT_SECRET from service key

### "Deployment not found"
- List available models first: `client.list_deployments()`
- Update `default_model` in genai_client.py

### "Connection refused"
- Check AI_API_URL format
- Ensure AI Core service is running

---

## Next Steps (Tomorrow)

1. **Part 3: RAG** - Upload docs → HANA Vector → Semantic search
2. **Part 4: Email Classifier** - Classify + auto-draft responses
3. **Integration** - Connect to your MCP server on Kyma

---

*Created: March 2026*
*Author: Srinivasa Dasari (Deloitte US)*
*Goal: Solution Architect → AI Architect*
