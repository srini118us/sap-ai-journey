"""
Patching Orchestrator Agent — ADK Version

Architecture: Agent DECIDES, existing tools EXECUTE.
- Pre/post checks:  Agent runs checks via SSH
- OS patching:      Agent calls GCP VM Manager API (existing tool)
- App stop/start:   Agent calls systemctl via SSH (existing tool)
- Decision making:  Gemini reasons about safety

Phase 1: Mock data (current)
Phase 2: Real SSH to Tomcat test VM
Phase 3: Swap Tomcat commands for SAP sapcontrol commands
"""

from google.adk.agents import Agent
from datetime import datetime
import json


# ══════════════════════════════════════════════════════════════
# TOOL 1: PRE-CHECK — Is it safe to patch right now?
# ══════════════════════════════════════════════════════════════

def pre_check_system() -> dict:
    """
    Run pre-checks before patching: check if the application is serving
    traffic, active connections, running background jobs, last backup
    status, and disk space. Returns a safety assessment.

    The agent should call this FIRST before any patching activity.
    If pre-checks show the system is not safe, the agent should
    POSTPONE and explain why.
    """
    # MOCK DATA — replace with real SSH commands in Phase 2
    # Phase 2: ssh_run("curl -s -o /dev/null -w '%{http_code}' http://localhost:8080")
    # Phase 3 (SAP): ssh_run("sapcontrol -nr 00 -function ABAPGetSystemWPTable")
    return {
        "timestamp": datetime.now().isoformat(),
        "system": "agent-test-vm",
        "application": "Tomcat 9",
        "checks": {
            "app_status": {
                "status": "RUNNING",
                "http_response": 200,
                "detail": "Tomcat responding on port 8080"
            },
            "active_connections": {
                "count": 3,
                "detail": "3 active HTTP sessions"
            },
            "background_jobs": {
                "running": 1,
                "detail": "1 scheduled task running (log rotation)"
            },
            "last_backup": {
                "status": "SUCCESS",
                "timestamp": "2026-05-04 22:00:00",
                "age_hours": 8,
                "detail": "Full disk snapshot completed 8 hours ago"
            },
            "disk_space": {
                "root_pct": 45,
                "app_pct": 62,
                "detail": "/ at 45%, /opt at 62% — sufficient space for patches"
            },
            "pending_patches": {
                "security": 12,
                "regular": 34,
                "detail": "12 security patches, 34 regular updates available"
            },
            "system_load": {
                "load_avg": "0.45 0.32 0.28",
                "cpu_pct": 12,
                "memory_pct": 58,
                "detail": "System load is low"
            }
        },
        "overall_safety": "SAFE_TO_PATCH",
        "warnings": ["3 active connections will be dropped during restart"]
    }


# ══════════════════════════════════════════════════════════════
# TOOL 2: STOP APPLICATION — Gracefully stop the app
# ══════════════════════════════════════════════════════════════

def stop_application() -> dict:
    """
    Gracefully stop the application (Tomcat/SAP) before patching.
    Waits for active connections to drain, then stops the service.
    Returns the stop status.

    The agent should ONLY call this AFTER pre_check_system confirms
    it is safe to proceed. The agent should verify the app is fully
    stopped before calling apply_os_patches.
    """
    # MOCK DATA — replace with real commands in Phase 2
    # Phase 2: ssh_run("sudo systemctl stop tomcat9")
    # Phase 3 (SAP): ssh_run("sapcontrol -nr 00 -function StopSystem ALL")
    return {
        "timestamp": datetime.now().isoformat(),
        "action": "STOP_APPLICATION",
        "application": "Tomcat 9",
        "steps_executed": [
            {"step": "Drain connections", "status": "OK", "detail": "Waited 30s, 3 connections drained"},
            {"step": "Stop Tomcat service", "status": "OK", "detail": "systemctl stop tomcat9 completed"},
            {"step": "Verify stopped", "status": "OK", "detail": "Port 8080 no longer responding"},
            {"step": "Verify processes", "status": "OK", "detail": "No java processes running"}
        ],
        "result": "SUCCESS",
        "app_status": "STOPPED"
    }


# ══════════════════════════════════════════════════════════════
# TOOL 3: APPLY OS PATCHES — Use GCP VM Manager (existing tool)
# ══════════════════════════════════════════════════════════════

def apply_os_patches() -> dict:
    """
    Apply OS patches using GCP VM Manager patch job API.
    This does NOT code patching logic — it calls the existing
    GCP VM Manager service which handles the actual patching.
    Returns the patch job status and list of patches applied.

    The agent should ONLY call this AFTER stop_application confirms
    the app is fully stopped. The agent should check the result
    and decide whether a reboot is needed.
    """
    # MOCK DATA — replace with real VM Manager API call in Phase 2
    # Phase 2: gcloud compute os-config patch-jobs execute
    #          --instance-filter-names="zones/us-central1-a/instances/agent-test-vm"
    # This calls GCP's EXISTING patch management — we don't code patching ourselves
    return {
        "timestamp": datetime.now().isoformat(),
        "action": "APPLY_OS_PATCHES",
        "method": "GCP VM Manager Patch Job",
        "patch_job_id": "patch-job-20260505-001",
        "patches_applied": [
            {"name": "linux-base-5.15.0-92", "type": "security", "status": "INSTALLED"},
            {"name": "openssl-3.0.13-1", "type": "security", "status": "INSTALLED"},
            {"name": "libcurl4-7.88.1-3", "type": "security", "status": "INSTALLED"},
            {"name": "systemd-252-14", "type": "regular", "status": "INSTALLED"},
            {"name": "ca-certificates-20240203", "type": "regular", "status": "INSTALLED"},
        ],
        "summary": {
            "total_applied": 5,
            "security_patches": 3,
            "regular_patches": 2,
            "failed": 0
        },
        "reboot_required": True,
        "result": "SUCCESS"
    }


# ══════════════════════════════════════════════════════════════
# TOOL 4: REBOOT SYSTEM — If patches require it
# ══════════════════════════════════════════════════════════════

def reboot_system() -> dict:
    """
    Reboot the system if patches require a restart.
    Waits for the system to come back online and verifies SSH access.
    Returns the reboot status.

    The agent should ONLY call this if apply_os_patches indicates
    reboot_required=True. After reboot, the agent MUST call
    start_application to bring the app back online.
    """
    # MOCK DATA — replace with real commands in Phase 2
    # Phase 2: ssh_run("sudo reboot") then poll until SSH responds
    return {
        "timestamp": datetime.now().isoformat(),
        "action": "REBOOT_SYSTEM",
        "steps_executed": [
            {"step": "Initiate reboot", "status": "OK", "detail": "sudo reboot issued"},
            {"step": "Wait for shutdown", "status": "OK", "detail": "System went offline after 15s"},
            {"step": "Wait for boot", "status": "OK", "detail": "System back online after 45s"},
            {"step": "Verify SSH access", "status": "OK", "detail": "SSH connection re-established"}
        ],
        "result": "SUCCESS",
        "downtime_seconds": 60
    }


# ══════════════════════════════════════════════════════════════
# TOOL 5: START APPLICATION — Bring app back online
# ══════════════════════════════════════════════════════════════

def start_application() -> dict:
    """
    Start the application (Tomcat/SAP) after patching and reboot.
    Verifies the application is fully operational.
    Returns the startup status.

    The agent should call this after apply_os_patches (and reboot
    if needed). The agent should then call post_check_system to
    validate everything is healthy.
    """
    # MOCK DATA — replace with real commands in Phase 2
    # Phase 2: ssh_run("sudo systemctl start tomcat9")
    # Phase 3 (SAP): ssh_run("sapcontrol -nr 00 -function StartSystem ALL")
    return {
        "timestamp": datetime.now().isoformat(),
        "action": "START_APPLICATION",
        "application": "Tomcat 9",
        "steps_executed": [
            {"step": "Start Tomcat service", "status": "OK", "detail": "systemctl start tomcat9"},
            {"step": "Wait for startup", "status": "OK", "detail": "Waited 20s for initialization"},
            {"step": "Verify port 8080", "status": "OK", "detail": "Port 8080 responding"},
            {"step": "Verify HTTP 200", "status": "OK", "detail": "GET / returned HTTP 200"}
        ],
        "result": "SUCCESS",
        "app_status": "RUNNING"
    }


# ══════════════════════════════════════════════════════════════
# TOOL 6: POST-CHECK — Validate everything is healthy
# ══════════════════════════════════════════════════════════════

def post_check_system() -> dict:
    """
    Run post-patching validation: verify application health,
    check for errors, confirm patches were applied, measure
    response times. Returns overall health status.

    The agent should call this LAST after start_application.
    If post-checks fail, the agent should recommend rollback
    and alert the team.
    """
    # MOCK DATA — replace with real commands in Phase 2
    # Phase 2: ssh_run("curl -w '%{time_total}' http://localhost:8080")
    # Phase 3 (SAP): ssh_run("sapcontrol -nr 00 -function GetProcessList")
    return {
        "timestamp": datetime.now().isoformat(),
        "action": "POST_CHECK",
        "checks": {
            "app_responding": {
                "status": "PASS",
                "http_code": 200,
                "response_time_ms": 45,
                "detail": "Tomcat responding in 45ms"
            },
            "all_processes_running": {
                "status": "PASS",
                "detail": "Tomcat main process + worker threads active"
            },
            "no_error_logs": {
                "status": "PASS",
                "detail": "No errors in /var/log/tomcat9/catalina.out since restart"
            },
            "patches_verified": {
                "status": "PASS",
                "kernel_version": "5.15.0-92-generic",
                "detail": "Running patched kernel"
            },
            "disk_space_ok": {
                "status": "PASS",
                "detail": "/ at 47% (was 45% pre-patch, slight increase expected)"
            }
        },
        "overall_status": "HEALTHY",
        "total_downtime_minutes": 2.5,
        "recommendation": "System is healthy. Patching completed successfully."
    }


# ══════════════════════════════════════════════════════════════
# TOOL 7: GENERATE REPORT — Create patching completion report
# ══════════════════════════════════════════════════════════════

def generate_patch_report() -> dict:
    """
    Generate a summary report of the patching activity for
    stakeholders. Includes timeline, patches applied, downtime,
    and post-check results.

    The agent should call this after all patching steps are complete
    to create a record of the maintenance activity.
    """
    return {
        "report_type": "PATCHING_COMPLETION",
        "system": "agent-test-vm",
        "date": datetime.now().strftime("%Y-%m-%d"),
        "timeline": [
            {"time": "02:00", "event": "Pre-checks started"},
            {"time": "02:01", "event": "Pre-checks passed — safe to proceed"},
            {"time": "02:01", "event": "Application stopped (Tomcat 9)"},
            {"time": "02:02", "event": "OS patches applied via VM Manager (5 patches)"},
            {"time": "02:03", "event": "System rebooted (60s downtime)"},
            {"time": "02:04", "event": "Application started (Tomcat 9)"},
            {"time": "02:05", "event": "Post-checks passed — system healthy"},
        ],
        "patches_applied": 5,
        "security_patches": 3,
        "total_downtime_minutes": 2.5,
        "post_check_status": "ALL PASSED",
        "next_patch_window": "2026-06-01"
    }


# ══════════════════════════════════════════════════════════════
# AGENT DEFINITION
# ══════════════════════════════════════════════════════════════

AGENT_INSTRUCTIONS = """You are an infrastructure operations agent that
orchestrates OS patching for application servers. You coordinate existing
tools — you do NOT code patching logic yourself.

YOUR ROLE: Decide, coordinate, validate. Let existing tools do the work.

AVAILABLE TOOLS (call in this order for a full patching run):
1. pre_check_system — Safety assessment: is it safe to patch now?
2. stop_application — Gracefully stop the app before patching
3. apply_os_patches — Trigger GCP VM Manager to apply patches
4. reboot_system — Reboot if patches require it
5. start_application — Bring the app back online
6. post_check_system — Validate everything is healthy after patching
7. generate_patch_report — Create a completion report

DECISION RULES:
- NEVER skip pre_check_system. Always check safety first.
- If pre-checks show active users > 50 or critical jobs running: POSTPONE.
  Explain why and suggest a better time.
- If last backup is older than 24 hours: REFUSE to patch. Backup first.
- If disk space < 20% free: WARN but proceed with caution.
- If apply_os_patches fails: DO NOT start the app. Alert immediately.
- If post_check_system fails: Recommend rollback and alert the team.
- If reboot_required is False: Skip reboot_system, go directly to
  start_application.

WHEN USER ASKS TO PATCH:
1. Run pre_check_system
2. Analyze results and DECIDE: go / postpone / refuse
3. If go: execute the full sequence (stop → patch → reboot → start → check)
4. After each step, verify before proceeding to the next
5. Generate a report at the end

WHEN USER ASKS ABOUT PATCH STATUS:
- Run pre_check_system to show current state
- Report pending patches and last patch date

RESPONSE STYLE:
- Be concise and action-oriented
- Show each step as you execute it
- Clearly state GO / POSTPONE / REFUSE decisions with reasoning
- At the end, summarize: patches applied, downtime, status

IMPORTANT:
- You orchestrate existing tools, you don't implement patching yourself
- In production, apply_os_patches calls GCP VM Manager API
- In production, stop/start calls sapcontrol for SAP systems
- Always prioritize safety over speed
"""

root_agent = Agent(
    name="patching_orchestrator",
    model="gemini-2.5-flash",
    description="Infrastructure patching orchestrator that decides when to patch, coordinates stop/start of applications, triggers GCP VM Manager for actual patching, and validates results.",
    instruction=AGENT_INSTRUCTIONS,
    tools=[
        pre_check_system,
        stop_application,
        apply_os_patches,
        reboot_system,
        start_application,
        post_check_system,
        generate_patch_report,
    ],
)
