# SAP ECC Diagnostic Agent

A **Google ADK** agent, powered by Gemini, that acts as an expert SAP Basis
engineer and Oracle DBA. It runs **read-only** health checks across three
layers of an SAP ECC system on Oracle (GCP / SUSE SLES) and explains findings
with cross-layer correlation and actionable recommendations.

> Status: **Phase 1 (prototype)** — the tools return realistic **mock data**.
> Phase 2 replaces the mocks with real SSH + `sqlplus` + `sapcontrol` calls.

Target system in the sample: SAP SID `SBX`, instance `00`, Oracle SID `SBX`.

## Folder Structure

```
sap-diagnostic-agent/
├── sap_diagnostic/
│   ├── agent.py        # Agent definition + 4 diagnostic tools
│   └── __init__.py     # Exposes root_agent
└── .env                # Google/Vertex credentials (not committed values)
```

## The Agent

- **Model:** `gemini-2.5-flash`
- **Name:** `sap_diagnostic_agent`
- **Tools (all read-only, safe to run anytime):**
  1. `check_os` — CPU load, memory, swap, disk usage, top processes, recent errors
  2. `check_oracle` — instance status, tablespace usage, long-running queries,
     wait events, sessions, archive log, last RMAN backup
  3. `check_sap` — process list, work-process table, alerts, ICM threads,
     enqueue locks, recent ABAP dumps
  4. `full_diagnostic` — runs all three and returns a combined view

The agent correlates across layers (e.g. high CPU -> long Oracle query ->
stuck SAP work process), explains *why* not just *what*, and flags work
processes running longer than 600 seconds as potentially stuck. It only
recommends changes for the Basis team — it never executes them.

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
# from sap-diagnostic-agent/
adk web          # opens the ADK dev UI (default http://localhost:8000)
```

Then ask questions like "is the system healthy?", "why is CPU high?", or
"check Oracle tablespaces."
