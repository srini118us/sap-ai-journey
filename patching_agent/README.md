# Patching Orchestrator Agent

A **Google ADK** (Agent Development Kit) agent, powered by Gemini, that
orchestrates OS patching for application servers. The design principle is
**"the agent DECIDES, existing tools EXECUTE"** — the agent reasons about
safety and sequencing, while the actual patching is delegated to platform
services (GCP VM Manager, `systemctl`/`sapcontrol` over SSH).

> Status: **Phase 1 (prototype)** — the tools return realistic **mock data**.
> Phase 2 swaps in real SSH commands against a Tomcat test VM; Phase 3 replaces
> Tomcat commands with SAP `sapcontrol` equivalents.

## Folder Structure

```
patching_agent/
├── patching_orchestrator/
│   ├── agent.py          # Agent definition + 7 tool functions
│   └── __init__.py       # Exposes root_agent
├── setup_test_vm.sh      # Provisions a free-tier GCP e2-micro VM with Tomcat
└── .env                  # Google/Vertex credentials (not committed values)
```

## The Agent

- **Model:** `gemini-2.5-flash`
- **Name:** `patching_orchestrator`
- **Tools (intended call order):**
  1. `pre_check_system` — safety assessment (app status, connections, backups, disk, load)
  2. `stop_application` — gracefully stop the app (drain connections, stop service)
  3. `apply_os_patches` — trigger GCP VM Manager patch job
  4. `reboot_system` — reboot only if patches require it
  5. `start_application` — bring the app back online
  6. `post_check_system` — validate health after patching
  7. `generate_patch_report` — produce a completion report

The agent's instructions encode decision rules — e.g. never skip the pre-check,
refuse to patch if the last backup is older than 24h, postpone if too many
active users or critical jobs are running, and skip reboot when not required.

## Prerequisites

- Python with `google-adk` installed
- A Google API key or Vertex AI access

`.env` provides (values redacted here):

```
GOOGLE_GENAI_USE_VERTEXAI=...
GOOGLE_API_KEY=...
GOOGLE_CLOUD_PROJECT=...
GOOGLE_CLOUD_LOCATION=...
```

## Run Locally

```bash
# from patching_agent/
adk web          # opens the ADK dev UI (default http://localhost:8000)
```

Then ask the agent to check patch status or run a patching cycle.

## Test VM (optional, for Phase 2)

`setup_test_vm.sh` creates a free-tier `e2-micro` Ubuntu 22.04 VM named
`agent-test-vm` in `us-central1-a`, installs Tomcat 9, and opens port 8080.
Edit `PROJECT_ID` at the top of the script first, then:

```bash
./setup_test_vm.sh
```

It prints the VM details and the `VM_NAME` / `VM_ZONE` / `VM_PROJECT` values to
add to your `.env` for the real-SSH phase.
