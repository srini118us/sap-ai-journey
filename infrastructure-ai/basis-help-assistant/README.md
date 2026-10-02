# SAP Job Failure Agent

LangGraph-based AI agent for investigating and remediating SAP background job failures via `APJ_JOB_MANAGEMENT_SRV` OData service.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    LangGraph State Machine                   │
├─────────────────────────────────────────────────────────────┤
│  fetch_failed_jobs → analyze_job → fetch_job_log            │
│         ↓                                                    │
│  diagnose_root_cause → propose_remediation                   │
│         ↓                                                    │
│  await_approval (human-in-the-loop)                          │
│         ↓                                                    │
│  execute_remediation → report_findings                       │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              APJ_JOB_MANAGEMENT_SRV (OData)                  │
├─────────────────────────────────────────────────────────────┤
│  JobRunOverviewSet    - List jobs with status                │
│  JobRunDetailsSet     - Full job details                     │
│  JobRunLogSet         - Job execution logs                   │
│  RestartJob           - Restart failed job (POST)            │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Connection

Edit `config.json`:

```json
{
    "sap_odata": {
        "base_url": "https://your-sap-host:port/sap/opu/odata/sap/APJ_JOB_MANAGEMENT_SRV",
        "username": "your_username",
        "password": "your_password"
    },
    "ai_core": {
        "mode": "aicore",
        "model_name": "gpt-4o"
    }
}
```

### 3. Run Agent

**Interactive Mode (with human approval):**
```bash
python main.py --mode interactive
```

**Batch Mode (report only):**
```bash
python main.py --mode batch --output report.json
```

**Test with Mock Data:**
```bash
python main.py --mock
```

## Safety Tiers

| Action | Tier | Auto-Execute |
|--------|------|--------------|
| Read job status | 🟢 Green | ✅ Yes |
| Read job logs | 🟢 Green | ✅ Yes |
| Restart job | 🟡 Yellow | ❌ Human approval |
| Cancel job | 🟡 Yellow | ❌ Human approval |

## Files

| File | Purpose |
|------|---------|
| `job_failure_agent.py` | Core LangGraph agent + OData client |
| `llm_client.py` | SAP AI Core / OpenAI / Mock LLM wrappers |
| `main.py` | CLI entry point |
| `config.json` | Connection settings |

## OData Entity Sets Used

- `JobRunOverviewSet` - Failed jobs list (filter: `JobRunStatus eq 'A'`)
- `JobRunDetailsSet` - Job details by key
- `JobRunLogSet` - Job log entries
- `ApplicationLogMessageSet` - Application log messages
- `RestartJob` - Function import for job restart

## Deployment to SAP AI Core

1. Create AI Core deployment configuration
2. Push Docker image with agent code
3. Create inference deployment
4. Call via AI Core inference endpoint

See: https://github.com/SAP-samples/teched2025-AI160 for deployment templates.

## Next Steps

- [ ] Add tRFC Auto-Healer (SM58)
- [ ] Add Queue Health Agent (SMQ1/SMQ2)
- [ ] Add SAP Notes RAG grounding
- [ ] Integrate with GCP Vertex AI (A2A)
