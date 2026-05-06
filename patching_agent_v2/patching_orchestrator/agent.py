"""
SAP Kernel Patching Orchestrator Agent — Real Workflow

Matches actual Basis team process for SAP NetWeaver ABAP ECC kernel patching.
System: SBX (Instance 00) | Oracle DB | SUSE SLES

Architecture: Agent DECIDES + COORDINATES, existing tools EXECUTE.
- SAP stop/start:     sapcontrol / stopsap / startsap (existing)
- OS patching:         GCP VM Manager API (existing)
- Ticket management:   ServiceNow REST API (existing)
- Email notifications: Microsoft Graph API / Outlook (existing)
- Kernel files:        SAPCAR extraction (existing)

═══════════════════════════════════════════════════════════════
IMPLEMENTATION PHASES
═══════════════════════════════════════════════════════════════
Phase 1: Mock data (current - for demo and testing)
Phase 2: Real SSH to SAP VM (connect to SBX via OS Login)
Phase 3: Multi-system support (see FUTURE ENHANCEMENTS below)

═══════════════════════════════════════════════════════════════
FUTURE ENHANCEMENTS (DO NOT FORGET)
═══════════════════════════════════════════════════════════════

1. SYSTEM REGISTRY (Phase 3)
   --------------------------
   Each SAP system has different NetWeaver version, kernel release,
   support packages, and software components. The agent needs a
   registry to look up the correct target kernel and SAR file
   location per system.
   
   Implementation: Add a SYSTEM_REGISTRY dict (or JSON/YAML config)
   mapping SID → {netweaver_version, kernel_release, database_type,
   current_pl, target_pl, sar_file_location, environment, change_type}
   
   Example systems:
   - SBX (ECC, NW 7.50, Kernel 753, Oracle)
   - S4P (S/4HANA, NW 7.77, Kernel 789, HANA)
   - FIP (Fiori, NW 7.52, Kernel 753, HANA)
   - GRC (GRC, NW 7.40, Kernel 753, Oracle)
   
   Add a tool: get_system_config(sid) that reads from the registry.
   All other tools then use the config instead of hardcoded values.

2. MULTI-SYSTEM PARALLEL PATCHING (Phase 3)
   ------------------------------------------
   Use ADK ParallelAgent to patch multiple systems simultaneously.
   Each system gets its own patching agent instance with its own
   checkpoints. Parent orchestrator coordinates across systems.
   
   Implementation:
   - ParallelAgent spawns N child patching agents
   - Each child runs the same 12-tool workflow
   - Each child has its own Checkpoint 1/2/3
   - Parent tracks overall progress
   - If one system fails, others continue independently
   
   Key: systems with dependencies (e.g., ECC before GRC) should
   use SequentialAgent, independent systems use ParallelAgent.

3. SAP GUI AUTOMATION (Phase 4 — when SAP AI agents ready)
   ---------------------------------------------------------
   Currently ST22, SM21, SM37, SE06 checks are done manually by
   Basis engineer at Checkpoint 2. When SAP AI agents are available
   on BTP, these can be automated:
   
   - BTP agent calls SAP OData/RFC to query ST22 dumps
   - BTP agent checks SM21 system log entries
   - BTP agent verifies SM37 job scheduler status
   - GCP agent ↔ BTP agent communicate via A2A protocol
   
   This eliminates Checkpoint 2 manual verification.

4. AUTOMATIC TARGET VERSION SELECTION (Phase 4)
   ----------------------------------------------
   Instead of human selecting target kernel version:
   - Agent queries SAP Support Portal API (if available)
   - Cross-references current version with latest available
   - Checks OSS notes for known issues with target version
   - Recommends target version with reasoning
   
   This reduces the 3 human decisions to just 1 (approve/reject).

5. ROLLBACK TESTING (Phase 3)
   ----------------------------
   Add a "dry run" mode that simulates the full patching workflow
   including rollback, without actually touching the system.
   Useful for validating the agent before production use.

6. OUTLOOK EMAIL TEMPLATES (Phase 2)
   ------------------------------------
   Microsoft Graph API setup for Outlook:
   - Register app in Entra ID (one-time)
   - Create shared mailbox: sap-agents@company.com
   - OAuth2 client_credentials flow (not Basic Auth — retired Sept 2025)
   - Store credentials in GCP Secret Manager
   - Endpoint: POST graph.microsoft.com/v1.0/users/{mailbox}/sendMail

7. SERVICENOW INTEGRATION (Phase 2)
   ------------------------------------
   ServiceNow REST API for change requests:
   - POST /api/now/table/change_request (create)
   - PATCH /api/now/table/change_request/{sys_id} (update/close)
   - For production: change_type = "Normal" (requires CAB approval)
   - For non-prod: change_type = "Standard" (pre-approved)
   - Agent polls approval status before proceeding

═══════════════════════════════════════════════════════════════
"""

from google.adk.agents import Agent
from datetime import datetime


# ══════════════════════════════════════════════════════════════
# TOOL 1: CAPTURE CURRENT KERNEL VERSION
# ══════════════════════════════════════════════════════════════

def capture_kernel_version() -> dict:
    """
    Capture the current SAP kernel version, patch level, and
    compilation details. This establishes the BEFORE state.

    The agent should call this FIRST at the start of any kernel
    patching activity to document the source version.

    Real command: ssh to SAP VM → disp+work --version (as sidadm)
    """
    # PHASE 2: ssh_run("sudo su - sbxadm -c 'disp+work --version'")
    return {
        "timestamp": datetime.now().isoformat(),
        "system": "SBX",
        "instance_nr": "00",
        "current_kernel": {
            "kernel_release": "753",
            "patch_level": "1200",
            "source_id": "0.1200",
            "platform": "linux_x86_64",
            "compilation_mode": "UNICODE",
            "compile_time": "Jan 15 2026 14:30:00",
            "exe_directory": "/usr/sap/SBX/DVEBMGS00/exe",
            "sapcar_version": "7.53"
        },
        "host_agent": {
            "version": "7.22",
            "patch_level": "62"
        },
        "os_info": {
            "os": "SUSE Linux Enterprise Server 15 SP5",
            "kernel": "5.14.21-150500.55.52-default"
        }
    }


# ══════════════════════════════════════════════════════════════
# TOOL 2: VALIDATE TARGET KERNEL FILES
# ══════════════════════════════════════════════════════════════

def validate_target_kernel(target_patch_level: str = "1300") -> dict:
    """
    Validate that the target kernel files exist in the staging
    location (Cloud Storage bucket or NFS mount) and are the
    correct version. Also checks that SAPCAR is available.

    Args:
        target_patch_level: The target kernel patch level (e.g., "1300")

    The agent should call this to verify files are ready before
    starting the patching process.

    Real command: ssh → ls -la /staging/kernel/ && SAPCAR -tvf *.SAR
    """
    # PHASE 2: ssh_run("ls -la /sapmnt/SBX/kernel_staging/")
    return {
        "timestamp": datetime.now().isoformat(),
        "target_patch_level": target_patch_level,
        "staging_location": "/sapmnt/SBX/kernel_staging/",
        "files_found": [
            {"file": "SAPEXE_1300-80007612.SAR", "size_mb": 245, "status": "OK"},
            {"file": "SAPEXEDB_1300-80007655.SAR", "size_mb": 89, "status": "OK"},
            {"file": "igsexe_15-80003187.sar", "size_mb": 45, "status": "OK"},
            {"file": "igshelper_17-10010245.sar", "size_mb": 23, "status": "OK"},
            {"file": "SAPHOSTAGENT62_62-80004822.SAR", "size_mb": 34, "status": "OK"},
        ],
        "sapcar_available": True,
        "sapcar_path": "/usr/sap/SBX/DVEBMGS00/exe/SAPCAR",
        "checksum_valid": True,
        "validation": "PASS",
        "upgrade_path": "753 PL1200 → 753 PL1300"
    }


# ══════════════════════════════════════════════════════════════
# TOOL 3: PRE-PATCH SYSTEM CHECKS
# ══════════════════════════════════════════════════════════════

def pre_patch_checks() -> dict:
    """
    Run comprehensive pre-patch safety checks:
    - Active users logged in
    - Running batch jobs (SM37)
    - Pending IDocs (WE02)
    - Active update records
    - Oracle backup status (RMAN)
    - Disk space on exe directory filesystem
    - System load

    The agent should call this AFTER capture_kernel_version and
    validate_target_kernel. If any check fails, the agent should
    POSTPONE the patching and explain why.

    Real commands: sapcontrol, sqlplus, df, who
    """
    # PHASE 2: multiple ssh_run() calls for each check
    return {
        "timestamp": datetime.now().isoformat(),
        "system": "SBX",
        "checks": {
            "active_users": {
                "count": 2,
                "users": ["ADMIN_USER", "BATCH_USER"],
                "status": "OK",
                "detail": "Only 2 technical users logged in (downtime window active)"
            },
            "running_batch_jobs": {
                "count": 0,
                "status": "OK",
                "detail": "No active batch jobs in SM37"
            },
            "pending_idocs": {
                "count": 0,
                "status": "OK",
                "detail": "No pending IDocs in WE02"
            },
            "active_update_records": {
                "count": 0,
                "status": "OK",
                "detail": "No active update records (SM13)"
            },
            "oracle_backup": {
                "last_full_backup": "2026-05-05 22:00:00",
                "age_hours": 4,
                "status": "OK",
                "detail": "Full RMAN backup completed 4 hours ago"
            },
            "disk_space_exe": {
                "filesystem": "/usr/sap/SBX/DVEBMGS00/exe",
                "used_pct": 62,
                "free_gb": 18.5,
                "status": "OK",
                "detail": "18.5 GB free — sufficient for kernel files"
            },
            "system_load": {
                "load_avg": "0.12 0.08 0.05",
                "cpu_pct": 3,
                "memory_pct": 45,
                "status": "OK",
                "detail": "System is idle (downtime window)"
            },
            "sap_processes": {
                "all_green": True,
                "status": "OK",
                "detail": "All SAP processes GREEN before patching"
            },
            "change_request": {
                "cr_number": "CHG0012345",
                "approval_status": "APPROVED",
                "status": "OK",
                "detail": "ServiceNow CR approved by CAB"
            }
        },
        "overall_assessment": "SAFE_TO_PROCEED",
        "warnings": [],
        "blockers": []
    }


# ══════════════════════════════════════════════════════════════
# TOOL 4: STOP SAP SYSTEM
# ══════════════════════════════════════════════════════════════

def stop_sap_system() -> dict:
    """
    Stop the SAP ECC system gracefully.
    Sequence: soft shutdown (let users finish) → stop application → 
    verify all processes stopped.

    The agent should ONLY call this AFTER pre_patch_checks confirms
    SAFE_TO_PROCEED. The agent must verify the system is fully stopped
    before proceeding to backup_exe_directory.

    Real commands:
    - sapcontrol -nr 00 -function StopSystem ALL
    - sapcontrol -nr 00 -function GetProcessList (verify)
    """
    # PHASE 2: ssh_run("sudo su - sbxadm -c 'stopsap'")
    return {
        "timestamp": datetime.now().isoformat(),
        "action": "STOP_SAP",
        "system": "SBX",
        "steps": [
            {"step": "Soft shutdown initiated", "status": "OK",
             "command": "sapcontrol -nr 00 -function StopSystem ALL",
             "detail": "Sent stop signal to all processes"},
            {"step": "Wait for work processes to finish", "status": "OK",
             "duration_sec": 45, "detail": "All work processes completed"},
            {"step": "Dispatcher stopped", "status": "OK",
             "detail": "disp+work process terminated"},
            {"step": "ICM stopped", "status": "OK",
             "detail": "ICM process terminated"},
            {"step": "Gateway stopped", "status": "OK",
             "detail": "Gateway process terminated"},
            {"step": "Verify all processes down", "status": "OK",
             "command": "sapcontrol -nr 00 -function GetProcessList",
             "detail": "All processes GRAY (stopped)"}
        ],
        "result": "SUCCESS",
        "sap_status": "STOPPED",
        "downtime_started": datetime.now().isoformat()
    }


# ══════════════════════════════════════════════════════════════
# TOOL 5: BACKUP EXE DIRECTORY
# ══════════════════════════════════════════════════════════════

def backup_exe_directory() -> dict:
    """
    Create a backup of the current kernel exe directory before
    applying new kernel files. This is the rollback point.

    Creates: /usr/sap/SBX/DVEBMGS00/exe.bak_YYYYMMDD_HHMM

    The agent should ONLY call this AFTER stop_sap_system confirms
    SAP is fully stopped. If backup fails, the agent should ABORT
    the patching and restart SAP with existing kernel.

    Real command: cp -rp /usr/sap/SBX/DVEBMGS00/exe /usr/sap/SBX/DVEBMGS00/exe.bak_20260505_0200
    """
    # PHASE 2: ssh_run("cp -rp exe exe.bak_$(date +%Y%m%d_%H%M)")
    backup_name = f"exe.bak_{datetime.now().strftime('%Y%m%d_%H%M')}"
    return {
        "timestamp": datetime.now().isoformat(),
        "action": "BACKUP_EXE",
        "source": "/usr/sap/SBX/DVEBMGS00/exe",
        "backup": f"/usr/sap/SBX/DVEBMGS00/{backup_name}",
        "steps": [
            {"step": "Copy exe directory", "status": "OK",
             "command": f"cp -rp exe {backup_name}",
             "detail": "Full directory copy with permissions preserved"},
            {"step": "Verify backup size", "status": "OK",
             "source_size_mb": 1245, "backup_size_mb": 1245,
             "detail": "Backup size matches source"},
            {"step": "Verify file count", "status": "OK",
             "source_files": 847, "backup_files": 847,
             "detail": "File count matches"}
        ],
        "result": "SUCCESS",
        "rollback_path": f"/usr/sap/SBX/DVEBMGS00/{backup_name}",
        "detail": "Rollback available: restore this directory to exe if patching fails"
    }


# ══════════════════════════════════════════════════════════════
# TOOL 6: APPLY KERNEL PATCH
# ══════════════════════════════════════════════════════════════

def apply_kernel_patch() -> dict:
    """
    Extract and apply the new SAP kernel files using SAPCAR.
    Extracts SAR files from staging into the exe directory,
    overwriting existing kernel binaries.

    The agent should ONLY call this AFTER backup_exe_directory
    confirms backup is complete. If extraction fails, the agent
    should immediately call rollback_kernel.

    Real commands:
    - cd /usr/sap/SBX/DVEBMGS00/exe
    - SAPCAR -xvf /sapmnt/SBX/kernel_staging/SAPEXE_1300-*.SAR
    - SAPCAR -xvf /sapmnt/SBX/kernel_staging/SAPEXEDB_1300-*.SAR
    """
    # PHASE 2: ssh_run("SAPCAR -xvf *.SAR") for each file
    return {
        "timestamp": datetime.now().isoformat(),
        "action": "APPLY_KERNEL",
        "target_directory": "/usr/sap/SBX/DVEBMGS00/exe",
        "extractions": [
            {"file": "SAPEXE_1300-80007612.SAR",
             "status": "OK", "files_extracted": 423,
             "detail": "Kernel executables extracted"},
            {"file": "SAPEXEDB_1300-80007655.SAR",
             "status": "OK", "files_extracted": 67,
             "detail": "Database-specific libraries extracted"},
            {"file": "igsexe_15-80003187.sar",
             "status": "OK", "files_extracted": 34,
             "detail": "IGS executables extracted"},
            {"file": "igshelper_17-10010245.sar",
             "status": "OK", "files_extracted": 12,
             "detail": "IGS helper files extracted"},
        ],
        "permissions_set": True,
        "ownership_set": True,
        "result": "SUCCESS",
        "detail": "All kernel files extracted. Permissions set to sbxadm:sapsys."
    }


# ══════════════════════════════════════════════════════════════
# TOOL 7: START SAP SYSTEM
# ══════════════════════════════════════════════════════════════

def start_sap_system() -> dict:
    """
    Start the SAP system with the new kernel.
    Verifies all processes come up GREEN.

    The agent should call this AFTER apply_kernel_patch.
    The agent must verify all processes are GREEN before
    proceeding to post_patch_validation.

    Real commands:
    - sapcontrol -nr 00 -function StartSystem ALL
    - sapcontrol -nr 00 -function GetProcessList (verify GREEN)
    """
    # PHASE 2: ssh_run("sudo su - sbxadm -c 'startsap'")
    return {
        "timestamp": datetime.now().isoformat(),
        "action": "START_SAP",
        "system": "SBX",
        "steps": [
            {"step": "Start database (Oracle)", "status": "OK",
             "detail": "Oracle instance SBX started and OPEN"},
            {"step": "Start SAP instance", "status": "OK",
             "command": "sapcontrol -nr 00 -function StartSystem ALL",
             "detail": "Start signal sent"},
            {"step": "Wait for processes", "status": "OK",
             "duration_sec": 90,
             "detail": "Waited 90 seconds for all processes to initialize"},
            {"step": "Dispatcher", "status": "GREEN"},
            {"step": "ICM", "status": "GREEN"},
            {"step": "Gateway", "status": "GREEN"},
            {"step": "IGS Watchdog", "status": "GREEN"},
            {"step": "Work processes", "status": "OK",
             "detail": "6 DIA + 2 BTC + 1 UPD + 1 SPO = all running"}
        ],
        "result": "SUCCESS",
        "all_processes_green": True,
        "sap_status": "RUNNING"
    }


# ══════════════════════════════════════════════════════════════
# TOOL 8: POST-PATCH VALIDATION
# ══════════════════════════════════════════════════════════════

def post_patch_validation(target_patch_level: str = "1300") -> dict:
    """
    Comprehensive post-patching validation:
    - Verify new kernel version matches target
    - Check SM21 system log for errors since restart
    - Check ST22 for new ABAP short dumps since restart
    - Verify all processes are GREEN
    - Test RFC connections
    - Check batch job scheduler is running

    The agent should call this AFTER start_sap_system confirms
    all processes are GREEN. If any critical check fails, the
    agent should recommend rollback.

    Real commands: disp+work --version, sapcontrol alerts, snap file check
    """
    # PHASE 2: multiple ssh_run() calls
    return {
        "timestamp": datetime.now().isoformat(),
        "system": "SBX",
        "action": "POST_PATCH_VALIDATION",
        "checks": {
            "kernel_version": {
                "expected_patch_level": target_patch_level,
                "actual_patch_level": "1300",
                "kernel_release": "753",
                "status": "PASS",
                "detail": f"Kernel upgraded from PL1200 to PL{target_patch_level}"
            },
            "sm21_system_log": {
                "errors_since_restart": 0,
                "warnings_since_restart": 1,
                "status": "PASS",
                "detail": "1 warning: 'System restart detected' (expected after kernel update)"
            },
            "st22_short_dumps": {
                "dumps_since_restart": 0,
                "status": "PASS",
                "detail": "No new ABAP short dumps since restart"
            },
            "all_processes_green": {
                "status": "PASS",
                "detail": "disp+work, ICM, Gateway, IGS — all GREEN"
            },
            "rfc_connections": {
                "tested": 5,
                "passed": 5,
                "failed": 0,
                "status": "PASS",
                "detail": "All RFC destinations responding"
            },
            "batch_scheduler": {
                "status": "PASS",
                "detail": "Background job scheduler active, periodic jobs rescheduled"
            },
            "work_process_test": {
                "dialog_login": "PASS",
                "batch_job": "PASS",
                "update_process": "PASS",
                "status": "PASS",
                "detail": "All work process types tested and functional"
            },
            "icm_http_test": {
                "url": "http://localhost:8000/sap/public/ping",
                "response": "200 OK",
                "status": "PASS",
                "detail": "ICM HTTP port responding to health check"
            }
        },
        "overall_status": "ALL_CHECKS_PASSED",
        "upgrade_confirmed": f"753 PL1200 → 753 PL{target_patch_level}",
        "recommendation": "Kernel patching completed successfully. System is healthy."
    }


# ══════════════════════════════════════════════════════════════
# TOOL 9: ROLLBACK KERNEL (if something goes wrong)
# ══════════════════════════════════════════════════════════════

def rollback_kernel() -> dict:
    """
    Emergency rollback: restore the backed-up exe directory and
    restart SAP with the previous kernel version.

    The agent should ONLY call this if:
    - apply_kernel_patch fails
    - start_sap_system fails (processes don't come up GREEN)
    - post_patch_validation has critical failures

    Real commands:
    - stopsap (if running)
    - rm -rf exe && mv exe.bak_* exe
    - startsap
    - verify old version restored
    """
    # PHASE 2: ssh_run("rm -rf exe && mv exe.bak_* exe && startsap")
    return {
        "timestamp": datetime.now().isoformat(),
        "action": "ROLLBACK",
        "system": "SBX",
        "steps": [
            {"step": "Stop SAP (if running)", "status": "OK",
             "detail": "SAP stopped for rollback"},
            {"step": "Remove failed kernel", "status": "OK",
             "command": "rm -rf /usr/sap/SBX/DVEBMGS00/exe",
             "detail": "Failed kernel files removed"},
            {"step": "Restore backup", "status": "OK",
             "command": "mv exe.bak_20260505_0200 exe",
             "detail": "Previous kernel restored from backup"},
            {"step": "Start SAP with old kernel", "status": "OK",
             "detail": "SAP started successfully with PL1200"},
            {"step": "Verify old version", "status": "OK",
             "detail": "Confirmed running kernel 753 PL1200 (original)"}
        ],
        "result": "ROLLBACK_SUCCESS",
        "restored_version": "753 PL1200",
        "detail": "System restored to pre-patch state. Patching can be reattempted after root cause analysis."
    }


# ══════════════════════════════════════════════════════════════
# TOOL 10: CREATE SERVICENOW CHANGE REQUEST
# ══════════════════════════════════════════════════════════════

def create_change_request(
    description: str = "SAP Kernel Update SBX",
    change_type: str = "Standard"
) -> dict:
    """
    Create a change request in ServiceNow for the kernel patching
    activity. For production systems, this requires CAB approval.
    For non-prod, email notification is sufficient.

    Args:
        description: Description of the change
        change_type: "Standard" for non-prod, "Normal" for production

    Real API: POST https://{instance}.service-now.com/api/now/table/change_request
    """
    return {
        "timestamp": datetime.now().isoformat(),
        "action": "CREATE_CHANGE_REQUEST",
        "servicenow": {
            "cr_number": "CHG0012345",
            "state": "New",
            "type": change_type,
            "short_description": description,
            "description": f"SAP Kernel Update for system SBX. "
                          f"Upgrade from 753 PL1200 to 753 PL1300. "
                          f"Estimated downtime: 15-30 minutes.",
            "assigned_to": "SAP Basis Team",
            "approval_status": "Requested" if change_type == "Normal" else "Pre-approved",
            "url": "https://company.service-now.com/change_request.do?sysparm_query=number=CHG0012345"
        },
        "result": "CREATED",
        "detail": f"Change request CHG0012345 created. "
                  f"{'Awaiting CAB approval for production.' if change_type == 'Normal' else 'Pre-approved for non-production.'}"
    }


# ══════════════════════════════════════════════════════════════
# TOOL 11: SEND NOTIFICATION EMAIL
# ══════════════════════════════════════════════════════════════

def send_notification(
    notification_type: str = "downtime_start",
    additional_info: str = ""
) -> dict:
    """
    Send notification email via Microsoft Outlook (Graph API).
    Used for downtime announcements and completion notifications.

    Args:
        notification_type: "downtime_start", "downtime_end", "rollback", or "failure"
        additional_info: Any additional context to include in the email

    Real API: POST https://graph.microsoft.com/v1.0/users/{mailbox}/sendMail
    """
    templates = {
        "downtime_start": {
            "subject": "[DOWNTIME] SBX - SAP Kernel Patching Starting",
            "body": "SAP system SBX will be unavailable for approximately 15-30 minutes for kernel patching (753 PL1200 → PL1300). Change Request: CHG0012345.",
            "recipients": "sap-users@company.com, basis-team@company.com"
        },
        "downtime_end": {
            "subject": "[RESTORED] SBX - SAP Kernel Patching Complete",
            "body": "SAP system SBX is back online. Kernel successfully upgraded to 753 PL1300. All post-checks passed. System is healthy.",
            "recipients": "sap-users@company.com, basis-team@company.com"
        },
        "rollback": {
            "subject": "[ALERT] SBX - Kernel Patching Rolled Back",
            "body": "SAP system SBX kernel patching was rolled back to PL1200 due to issues during upgrade. System is operational on previous kernel. Investigation required.",
            "recipients": "basis-team@company.com, sap-leads@company.com"
        },
        "failure": {
            "subject": "[CRITICAL] SBX - Kernel Patching Failed",
            "body": "SAP system SBX kernel patching encountered a critical failure. Immediate attention required.",
            "recipients": "basis-team@company.com, sap-leads@company.com, oncall@company.com"
        }
    }

    template = templates.get(notification_type, templates["downtime_start"])

    return {
        "timestamp": datetime.now().isoformat(),
        "action": "SEND_EMAIL",
        "notification_type": notification_type,
        "email": {
            "from": "sap-agents@company.com",
            "to": template["recipients"],
            "subject": template["subject"],
            "body": template["body"] + (f"\n\nAdditional info: {additional_info}" if additional_info else ""),
        },
        "result": "SENT",
        "method": "Microsoft Graph API (Outlook)"
    }


# ══════════════════════════════════════════════════════════════
# TOOL 12: GENERATE PATCH REPORT
# ══════════════════════════════════════════════════════════════

def generate_patch_report() -> dict:
    """
    Generate a comprehensive patching completion report.
    Includes timeline, before/after versions, checks performed,
    and total downtime.

    The agent should call this at the very end of a successful
    patching run. The report can be attached to the ServiceNow
    change request.
    """
    return {
        "report_type": "SAP_KERNEL_PATCH_COMPLETION",
        "system": "SBX",
        "date": datetime.now().strftime("%Y-%m-%d"),
        "change_request": "CHG0012345",
        "kernel_upgrade": {
            "before": "SAP Kernel 753 Patch Level 1200",
            "after": "SAP Kernel 753 Patch Level 1300",
            "host_agent": "7.22 PL62 (unchanged)"
        },
        "files_applied": [
            "SAPEXE_1300-80007612.SAR",
            "SAPEXEDB_1300-80007655.SAR",
            "igsexe_15-80003187.sar",
            "igshelper_17-10010245.sar"
        ],
        "timeline": [
            {"time": "02:00", "event": "Pre-checks started"},
            {"time": "02:02", "event": "Pre-checks passed — safe to proceed"},
            {"time": "02:02", "event": "Downtime notification sent via Outlook"},
            {"time": "02:03", "event": "SAP system stopped (stopsap)"},
            {"time": "02:04", "event": "Exe directory backed up"},
            {"time": "02:05", "event": "Kernel files extracted (SAPCAR)"},
            {"time": "02:06", "event": "SAP system started (startsap)"},
            {"time": "02:08", "event": "All processes GREEN"},
            {"time": "02:09", "event": "Post-patch validation — ALL PASSED"},
            {"time": "02:09", "event": "Completion email sent via Outlook"},
        ],
        "downtime": {
            "start": "02:03",
            "end": "02:08",
            "total_minutes": 5
        },
        "validation_results": {
            "kernel_version": "PASS — PL1300 confirmed",
            "sm21_errors": "PASS — no errors",
            "st22_dumps": "PASS — no dumps",
            "processes_green": "PASS — all GREEN",
            "rfc_connections": "PASS — 5/5 OK",
            "batch_scheduler": "PASS — active"
        },
        "executed_by": "SAP Kernel Patching Agent (automated)",
        "reviewed_by": "Pending Basis team sign-off"
    }


# ══════════════════════════════════════════════════════════════
# AGENT DEFINITION
# ══════════════════════════════════════════════════════════════

AGENT_INSTRUCTIONS = """You are an SAP Basis operations agent that orchestrates
SAP kernel patching for SAP NetWeaver ABAP ECC systems on Oracle database
running on Google Cloud Platform (SUSE SLES).

Your system: SAP SID = SBX, Instance Number = 00, Oracle SID = SBX.

YOUR ROLE: You DECIDE when it's safe to patch, COORDINATE the sequence of
existing tools, VALIDATE each step, and REPORT the results. You do NOT
implement patching logic yourself — you call existing tools.

CRITICAL: You work WITH humans, not instead of them. There are 3 mandatory
checkpoints where you MUST STOP and wait for human confirmation before
proceeding.

AVAILABLE TOOLS (12 total):

Planning tools:
1. capture_kernel_version — Get current kernel version (BEFORE state)
2. validate_target_kernel — Verify target kernel files exist in staging
3. create_change_request — Create ServiceNow CR (Standard or Normal)
4. send_notification — Send Outlook email (downtime start/end/rollback/failure)

Execution tools:
5. pre_patch_checks — Full safety assessment (users, jobs, IDocs, backup, disk)
6. stop_sap_system — Gracefully stop SAP (sapcontrol StopSystem)
7. backup_exe_directory — Backup current exe dir (rollback point)
8. apply_kernel_patch — Extract new kernel files (SAPCAR)
9. start_sap_system — Start SAP with new kernel (sapcontrol StartSystem)
10. rollback_kernel — Emergency rollback to previous kernel

Validation tools:
11. post_patch_validation — Verify version, SM21, ST22, processes, RFC
12. generate_patch_report — Create completion report

═══════════════════════════════════════════════════════════════
PATCHING SEQUENCE WITH 3 HUMAN CHECKPOINTS
═══════════════════════════════════════════════════════════════

PHASE A — PREPARATION (automated):
1. capture_kernel_version (document BEFORE state)
2. validate_target_kernel (verify files are staged)
3. pre_patch_checks (safety assessment)

───────────────────────────────────────────────────────────────
🛑 CHECKPOINT 1 — HUMAN APPROVAL TO PROCEED
───────────────────────────────────────────────────────────────
After pre-checks, you MUST STOP and present the results to the user.
Show them:
  - Current kernel version
  - Target kernel version  
  - All pre-check results (users, jobs, IDocs, backup, disk)
  - Your assessment: GO / POSTPONE / REFUSE
  - Any warnings or concerns

Then ask: "Pre-checks complete. Ready to stop SBX and begin patching.
Do you confirm to proceed?"

DO NOT continue until the user explicitly confirms (e.g., "yes", "go ahead",
"proceed", "confirmed"). If they say "wait", "hold", "no", or raise
concerns, STOP and address their concerns first.

PHASE B — EXECUTION (automated after checkpoint 1 approval):
4. send_notification("downtime_start")
5. stop_sap_system
6. backup_exe_directory
7. apply_kernel_patch
8. start_sap_system

───────────────────────────────────────────────────────────────
🛑 CHECKPOINT 2 — HUMAN VERIFICATION AFTER RESTART
───────────────────────────────────────────────────────────────
After SAP restarts and processes show GREEN, you MUST STOP and ask
the user to verify the system via SAP GUI. Present what you've
confirmed automatically, then ask them to check what only a human
can verify:

Show them:
  - "SAP processes are GREEN (automated check passed)"
  - "New kernel version the target PL confirmed (automated check passed)"

Then ask: "SAP is up and processes are GREEN. Before I run final
validation, please verify via SAP GUI:
  1. Log in to SBX — is it responsive?
  2. Check ST22 — any new short dumps since restart?
  3. Check SM21 — any errors in system log?
  4. Check SM37 — is batch scheduler running?
  5. Quick test — run a simple transaction

Please confirm when your SAP GUI checks are done, or tell me if
you see any issues."

If the user reports issues: ASK "Do you want me to rollback to
the previous PL?" Do NOT auto-rollback without their confirmation.

If the user confirms all good: proceed to Phase C.

PHASE C — FINALIZE (automated after checkpoint 2 approval):
9. post_patch_validation (automated technical checks)
10. send_notification("downtime_end")
11. generate_patch_report

───────────────────────────────────────────────────────────────
🛑 CHECKPOINT 3 — HUMAN SIGN-OFF ON FAILURE/ROLLBACK
───────────────────────────────────────────────────────────────
If ANYTHING fails during Phase B (stop fails, patch fails, start
fails, processes not GREEN), you MUST:
  1. Clearly explain WHAT failed and WHY
  2. Present the options:
     a) "I can rollback to the previous PL (restore exe backup + restart)"
     b) "You can investigate manually first"
  3. Ask: "How would you like to proceed?"

NEVER auto-rollback without asking first. The Basis engineer may
want to investigate before deciding. A failed state with information
is better than an auto-rollback that hides the root cause.

If they choose rollback:
  - call rollback_kernel
  - call send_notification("rollback")
  - explain what happened and recommend next steps

═══════════════════════════════════════════════════════════════

DECISION RULES:
- If active users > 10 during non-maintenance window: POSTPONE
- If batch jobs are running: POSTPONE (wait for completion)
- If pending IDocs > 0: WARN but proceed (they'll process after restart)
- If last backup > 24 hours old: REFUSE to patch (backup first)
- If disk space on exe filesystem < 2 GB free: REFUSE (not enough space)
- If change request not approved (production): REFUSE
- If kernel files not found in staging: REFUSE

IMPORTANT RULES:
- NEVER skip backup_exe_directory. This is the safety net.
- NEVER skip any of the 3 checkpoints. Human verification is mandatory.
- ALWAYS capture the BEFORE kernel version first.
- ALWAYS send downtime notification before stopping SAP.
- ALWAYS send completion notification after successful patching.
- If anything fails, prioritize getting the system back online.
  A running system on old kernel is better than a broken system.
- SAP GUI checks (ST22, SM21, SM37, SE06) cannot be automated yet.
  These MUST be done by the Basis engineer at Checkpoint 2.

FUTURE SCOPE (acknowledge if user asks):
- Multi-system parallel patching (ECC, S/4HANA, Fiori, GRC) using
  ADK ParallelAgent pattern — same workflow running on multiple
  systems simultaneously with per-system checkpoints.
- SAP GUI-level checks (ST22, SM21) will be automated when SAP AI
  agents are available on BTP side.

RESPONSE STYLE:
- Show each step as you execute it with status (OK / FAILED / SKIPPED)
- At checkpoints, clearly show the 🛑 symbol and wait for human input
- For the safety assessment, clearly state: GO / POSTPONE / REFUSE
- Include before/after kernel versions in the summary
- Report total downtime in minutes
- Be specific about what commands would be executed in production
"""

root_agent = Agent(
    name="sap_kernel_patching_agent",
    model="gemini-2.5-flash",
    description="SAP Kernel Patching Orchestrator for ECC system SBX. Manages the full lifecycle: pre-checks, stop, backup, patch, start, validate, report.",
    instruction=AGENT_INSTRUCTIONS,
    tools=[
        capture_kernel_version,
        validate_target_kernel,
        pre_patch_checks,
        stop_sap_system,
        backup_exe_directory,
        apply_kernel_patch,
        start_sap_system,
        post_patch_validation,
        rollback_kernel,
        create_change_request,
        send_notification,
        generate_patch_report,
    ],
)
