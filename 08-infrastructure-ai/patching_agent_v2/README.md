# SAP Kernel Patching Orchestrator Agent

## What This Is
An AI agent that orchestrates SAP kernel patching by **deciding** when it's
safe, **coordinating** existing tools (sapcontrol, SAPCAR, VM Manager,
ServiceNow, Outlook), and **validating** results — with human checkpoints
at critical moments.

## Architecture Decision
**The agent does NOT code patching logic.** It calls existing tools:
- `sapcontrol / stopsap / startsap` → SAP stop/start (existing)
- `SAPCAR` → kernel file extraction (existing)
- GCP VM Manager API → OS patching (existing)
- ServiceNow REST API → change request management (existing)
- Microsoft Graph API → Outlook email notifications (existing)

## Current State (Phase 1)
- ✅ 12 tools covering full patching lifecycle
- ✅ 3 human checkpoints (pre-approval, post-restart GUI check, failure handling)
- ✅ Mock data for demo and testing
- ✅ Runs locally via `adk web .`
- ⬜ Real SSH to SAP VM (Phase 2)
- ⬜ Multi-system support (Phase 3)

## How to Run
```bash
cd patching_agent_v2/
# Edit .env with your Gemini API key
adk web .
# Select patching_orchestrator → ask "Patch SBX kernel to PL1300"
```

## 3 Human Checkpoints

### 🛑 Checkpoint 1: Before stopping SAP
Agent shows pre-check results, asks "Confirm to proceed?"
- You say "go ahead" → agent continues
- You say "wait" → agent pauses

### 🛑 Checkpoint 2: After SAP restarts
Agent says processes are GREEN, asks you to verify via SAP GUI:
- Check ST22 (short dumps)
- Check SM21 (system log)
- Check SM37 (batch scheduler)
- You say "looks good" → agent finalizes
- You say "I see errors" → agent asks about rollback

### 🛑 Checkpoint 3: On failure
Agent explains what failed, presents options:
- "Rollback to previous kernel"
- "Investigate manually first"
- NEVER auto-rollbacks without asking

## Tools Reference (12 total)

| # | Tool | Phase | What it does |
|---|------|-------|-------------|
| 1 | capture_kernel_version | Planning | disp+work --version (BEFORE state) |
| 2 | validate_target_kernel | Planning | Check SAR files exist in staging |
| 3 | create_change_request | Planning | ServiceNow API: create CR |
| 4 | send_notification | Planning | Outlook API: downtime email |
| 5 | pre_patch_checks | Pre-exec | Users, jobs, IDocs, backup, disk |
| 6 | stop_sap_system | Execution | sapcontrol StopSystem ALL |
| 7 | backup_exe_directory | Execution | cp -rp exe exe.bak |
| 8 | apply_kernel_patch | Execution | SAPCAR -xvf *.SAR |
| 9 | start_sap_system | Execution | sapcontrol StartSystem ALL |
| 10 | rollback_kernel | Emergency | Restore exe.bak → restart |
| 11 | post_patch_validation | Validation | Version, SM21, ST22, RFC |
| 12 | generate_patch_report | Reporting | Full timeline + results |

## Phase 2: Real SSH Connection
Replace mock `return {}` in each tool with real SSH commands:
```python
# Mock (current):
return {"sap_status": "STOPPED"}

# Real (Phase 2):
output = ssh_run("sudo su - sbxadm -c 'stopsap'")
return {"sap_status": "STOPPED", "output": output}
```
SSH options:
- Option A: `gcloud compute ssh` from laptop (needs VPN)
- Option B: Cloud Function with OS Login (production path)
- Option C: Agent on GCE VM in same VPC (easiest network)

## Phase 3: Multi-System Support

### System Registry
Each SAP system needs different kernel files based on NetWeaver version:
```
SBX → ECC,     NW 7.50, Kernel 753, Oracle → SAPEXE_1300-*.SAR
S4P → S/4HANA, NW 7.77, Kernel 789, HANA   → SAPEXE_300-*.SAR
FIP → Fiori,   NW 7.52, Kernel 753, HANA   → SAPEXE_1300-*.SAR
GRC → GRC,     NW 7.40, Kernel 753, Oracle → SAPEXE_1300-*.SAR
```
Implementation: Add SYSTEM_REGISTRY config dict + get_system_config(sid) tool.
Agent looks up correct files/paths per system instead of hardcoded values.

### Parallel Patching
Use ADK ParallelAgent to patch multiple systems simultaneously:
```
ParentOrchestrator
  ├── ParallelAgent
  │   ├── PatchingAgent(SBX) ← own checkpoints
  │   ├── PatchingAgent(FIP) ← own checkpoints
  │   └── PatchingAgent(GRC) ← own checkpoints
  └── SequentialAgent
      └── PatchingAgent(S4P) ← production, patched separately
```
Independent systems run in parallel. Dependent systems run sequentially.

## Phase 4: SAP AI Agent Integration

### SAP GUI Checks Automation
Currently Checkpoint 2 requires manual SAP GUI verification (ST22, SM21, SM37).
When SAP AI agents are available on BTP:
- BTP agent queries ST22 via OData/RFC
- BTP agent checks SM21 system log
- BTP agent verifies SM37 job scheduler
- GCP agent ↔ BTP agent communicate via A2A protocol
- Eliminates manual Checkpoint 2

### Automatic Target Version Selection
Instead of human choosing target kernel:
- Agent queries SAP Support Portal API
- Cross-references with current version
- Checks OSS notes for known issues
- Recommends target version with reasoning
- Reduces human decisions from 3 to 1

## Integration Notes

### Microsoft Outlook (Email)
- Microsoft Graph API with OAuth2 client_credentials flow
- Basic Auth retired September 2025 — Graph API is the ONLY path
- Register app in Entra ID, create shared mailbox (sap-agents@company.com)
- Store credentials in GCP Secret Manager
- Endpoint: POST graph.microsoft.com/v1.0/users/{mailbox}/sendMail
- Shared mailbox limit: ~2,000 emails/24hrs (sufficient)

### ServiceNow (Change Requests)
- POST /api/now/table/change_request (create)
- PATCH /api/now/table/change_request/{sys_id} (update/close)
- Production: change_type = "Normal" (requires CAB approval)
- Non-prod: change_type = "Standard" (pre-approved)
- Agent polls approval status before proceeding

## File Structure
```
patching_agent_v2/
  .env                        ← API key (not committed to git)
  patching_orchestrator/
    __init__.py               ← from .agent import root_agent
    agent.py                  ← 12 tools + instructions + future notes
```
