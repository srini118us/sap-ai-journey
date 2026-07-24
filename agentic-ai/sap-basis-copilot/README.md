# SAP Basis Copilot

An agentic AI assistant built with Google ADK and Gemini 3.5 Flash that automates daily SAP Basis health checks against a live S/4HANA system (A4H Developer Edition, GCP CAL trial), plus a human-in-the-loop SAP queue reprocessing agent for failed tRFC entries (SM58).

## Architecture

Browser (Cloud Run web UI) to Google ADK Agent (Gemini 3.5 Flash, Vertex AI) to SSH (paramiko) plus hdbsql plus sapcontrol to SAP A4H on GCP (HANA plus ABAP stack).

Deployed on Cloud Run: containerized, secrets pulled from Secret Manager at runtime (SSH key never baked into the image).

## What it does

### Daily Basis Health Check (16 automated checks)

Equivalent to a Basis engineer's morning routine across SM51, SM50, HANA process health, disk space, SM66 (enhanced to flag PRIV-mode and over-10-minute running work processes with program/user identification), DBACOCKPIT load history and expensive SQL, SM13, SM12 (via sapcontrol EnqGetStatistic), SM58, SOST, kernel version, SM37 (cancelled and long-running jobs), plus Gemini Vision analysis of DBACOCKPIT CPU and Memory charts captured from SAP GUI.

### SAP Queue Reprocessing Agent (SM58, human-in-the-loop)

Finds failed tRFC entries, classifies each as transient (safe to retry) or a configuration issue (destination missing, auth failure, not safe to blindly retry), and explicitly refuses to auto-reprocess. Only executes reprocessing when the user gives explicit confirmation in the conversation, with an extra warning for destinations that could touch invoicing, billing, or customer-facing interfaces.

## Known limitations and deferred work

- SARFC (RFC resource monitoring): deferred. No sapcontrol web-service method exists for this; the real ABAP-layer equivalent (RSARFCCHK) requires either a custom RFC-enabled function module or the Vertex AI SDK for ABAP, which would also unlock a genuinely bidirectional SAP-side and GCP-side agent architecture. Scoped as a future session.
- DBACOCKPIT chart capture: currently manual (RDP into SAP GUI, screenshot, upload to GCS). SAP GUI Scripting automation was attempted but blocked by an RDP and COM window-station isolation issue even after confirming sapgui/user_scripting was enabled server-side via RZ11. Deferred.
- RSARFCEX execution: reprocess_trfc_entry() currently prepares the job submission but does not fully execute scheduled background job submission (needs SM36 authorization setup on this trial system).

## Stack

Google ADK 2.3.0, Gemini 3.5 Flash via Vertex AI (enterprise mode, global location), Cloud Run (containerized deployment), Secret Manager (SSH key storage), Cloud Storage (DBACOCKPIT screenshot hosting), paramiko (SSH), hdbsql (HANA queries), sapcontrol (SAP process control).
