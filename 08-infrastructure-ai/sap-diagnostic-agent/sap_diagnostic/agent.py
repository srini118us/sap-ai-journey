"""
SAP ECC Diagnostic Agent — ADK Version (with mock data for prototyping)

Run locally: adk web
Run in browser: opens at http://localhost:8000

Replace mock functions with real SSH calls in Phase 2.
"""
from google.adk.agents import Agent
import json
from datetime import datetime


# ══════════════════════════════════════════════════════════════
# TOOL FUNCTIONS (mock data for Phase 1 — replace with SSH in Phase 2)
# ══════════════════════════════════════════════════════════════

def check_os() -> dict:
    """
    Check OS-level health: CPU load, memory usage, disk space,
    swap utilization, top processes, and recent system errors.
    All checks are read-only and safe for production.
    Returns structured health data from the SAP ECC server.
    """
    # PHASE 1: Mock data (replace with SSH in Phase 2)
    return {
        "system": "SBX",
        "timestamp": datetime.now().isoformat(),
        "load_average": "2.34 1.89 1.56 (4 CPUs)",
        "memory": {
            "total_mb": 65536,
            "used_mb": 52428,
            "free_mb": 4096,
            "buffers_cache_mb": 9012,
            "usage_percent": 80.0
        },
        "swap": {
            "total_mb": 32768,
            "used_mb": 1024,
            "usage_percent": 3.1
        },
        "disk_usage": [
            {"filesystem": "/dev/sda1", "mount": "/", "size": "50G", "used": "32G", "pct": "64%"},
            {"filesystem": "/dev/sdb1", "mount": "/usr/sap", "size": "100G", "used": "67G", "pct": "67%"},
            {"filesystem": "/dev/sdc1", "mount": "/oracle/SBX", "size": "500G", "used": "423G", "pct": "85%"},
            {"filesystem": "/dev/sdd1", "mount": "/oracle/SBX/oraarch", "size": "200G", "used": "178G", "pct": "89%"},
            {"filesystem": "/dev/sde1", "mount": "/sapmnt", "size": "50G", "used": "12G", "pct": "24%"},
        ],
        "top_cpu_processes": [
            {"user": "orasbx", "pid": 12345, "cpu_pct": 45.2, "command": "ora_dbw0_SBX"},
            {"user": "orasbx", "pid": 12346, "cpu_pct": 23.1, "command": "ora_lg00_SBX"},
            {"user": "sbxadm", "pid": 23456, "cpu_pct": 12.8, "command": "dw.sapSBX_D00"},
            {"user": "sbxadm", "pid": 23457, "cpu_pct": 8.3, "command": "dw.sapSBX_D00"},
        ],
        "zombie_processes": 0,
        "recent_errors": [
            "Feb 27 03:45:12 sapsbx kernel: [warning] possible memory pressure detected",
            "Feb 27 02:12:08 sapsbx systemd: ntp.service restart triggered",
        ]
    }


def check_oracle() -> dict:
    """
    Check Oracle database health: instance status, tablespace usage,
    long-running queries, wait events, active sessions, archive log
    status, and recent RMAN backup status.
    All queries are read-only SELECT statements. Safe for production.
    Returns structured Oracle health data.
    """
    # PHASE 1: Mock data (replace with SSH + sqlplus in Phase 2)
    return {
        "system": "SBX",
        "oracle_sid": "SBX",
        "timestamp": datetime.now().isoformat(),
        "instance_status": "OPEN",
        "database_status": "ACTIVE",
        "tablespace_usage": [
            {"name": "PSAPSR3", "used_gb": 234.5, "total_gb": 280.0, "pct_used": 83.8},
            {"name": "PSAPSR3700", "used_gb": 45.2, "total_gb": 60.0, "pct_used": 75.3},
            {"name": "PSAPUNDO", "used_gb": 12.3, "total_gb": 30.0, "pct_used": 41.0},
            {"name": "SYSTEM", "used_gb": 2.1, "total_gb": 5.0, "pct_used": 42.0},
            {"name": "PSAPTEMP", "used_gb": 8.7, "total_gb": 50.0, "pct_used": 17.4},
        ],
        "long_running_queries": [
            {
                "sid": 234, "serial": 45678, "username": "SAPSR3",
                "minutes_running": 45.2,
                "sql_text": "SELECT * FROM BSEG WHERE BUKRS = '1000' AND GJAHR = '2025'..."
            },
            {
                "sid": 567, "serial": 89012, "username": "SAPSR3",
                "minutes_running": 12.8,
                "sql_text": "SELECT * FROM VBAK INNER JOIN VBAP ON..."
            },
        ],
        "top_wait_events": [
            {"event": "db file sequential read", "total_waits": 1234567, "time_waited_sec": 456.7},
            {"event": "log file sync", "total_waits": 234567, "time_waited_sec": 89.3},
            {"event": "buffer busy waits", "total_waits": 12345, "time_waited_sec": 23.4},
        ],
        "active_sessions": {"ACTIVE": 12, "INACTIVE": 45, "KILLED": 0},
        "archive_log_mode": "ARCHIVELOG",
        "archive_log_space_used": "178G of 200G (89%)",
        "alert_log_recent": [
            "ORA-00060: deadlock detected while waiting for resource (resolved automatically)",
            "Checkpoint not complete - increase log file size",
        ],
        "last_rman_backup": {
            "type": "DB FULL", "status": "COMPLETED",
            "start_time": "2025-02-26 22:00", "end_time": "2025-02-27 01:30"
        }
    }


def check_sap() -> dict:
    """
    Check SAP application health: process list, work process table
    showing what each process is doing, system alerts, ICM thread
    status, enqueue locks, and recent ABAP dump count.
    Uses sapcontrol read-only functions. Safe for production.
    Returns structured SAP health data.
    """
    # PHASE 1: Mock data (replace with SSH + sapcontrol in Phase 2)
    return {
        "system": "SBX",
        "instance_nr": "00",
        "timestamp": datetime.now().isoformat(),
        "process_list": [
            {"name": "disp+work.EXE", "pid": 23450, "status": "GREEN", "description": "Dispatcher"},
            {"name": "igswd.EXE", "pid": 23451, "status": "GREEN", "description": "IGS Watchdog"},
            {"name": "gwrd", "pid": 23452, "status": "GREEN", "description": "Gateway Reader"},
            {"name": "icman", "pid": 23453, "status": "GREEN", "description": "ICM"},
        ],
        "work_processes": [
            {"wp_no": 0, "type": "DIA", "pid": 23460, "status": "Run", "user": "JSMITH", "action": "SEQUENTIAL_READ", "table": "BSEG", "time_sec": 234},
            {"wp_no": 1, "type": "DIA", "pid": 23461, "status": "Wait", "user": "", "action": "", "table": "", "time_sec": 0},
            {"wp_no": 2, "type": "DIA", "pid": 23462, "status": "Wait", "user": "", "action": "", "table": "", "time_sec": 0},
            {"wp_no": 3, "type": "DIA", "pid": 23463, "status": "Run", "user": "AJONES", "action": "INSERT", "table": "VBAK", "time_sec": 12},
            {"wp_no": 4, "type": "DIA", "pid": 23464, "status": "Wait", "user": "", "action": "", "table": "", "time_sec": 0},
            {"wp_no": 5, "type": "DIA", "pid": 23465, "status": "Wait", "user": "", "action": "", "table": "", "time_sec": 0},
            {"wp_no": 6, "type": "BTC", "pid": 23470, "status": "Run", "user": "BATCH", "action": "SEQUENTIAL_READ", "table": "BKPF", "time_sec": 2700},
            {"wp_no": 7, "type": "BTC", "pid": 23471, "status": "Wait", "user": "", "action": "", "table": "", "time_sec": 0},
            {"wp_no": 8, "type": "UPD", "pid": 23480, "status": "Wait", "user": "", "action": "", "table": "", "time_sec": 0},
            {"wp_no": 9, "type": "SPO", "pid": 23490, "status": "Wait", "user": "", "action": "", "table": "", "time_sec": 0},
        ],
        "total_dia_wp": 6, "busy_dia_wp": 2,
        "total_btc_wp": 2, "busy_btc_wp": 1,
        "system_alerts": [
            {"severity": "YELLOW", "alert": "Shortdumps occurred: 3 in last hour"},
            {"severity": "GREEN", "alert": "All services running normally"},
        ],
        "icm_threads": {"total": 20, "active": 3, "idle": 17},
        "enqueue_locks": 23,
        "recent_dumps_24h": 7,
        "key_parameters": {
            "PHYS_MEMSIZE": "65536 MB",
            "em/initial_size_MB": "32768",
            "rdisp/wp_no_dia": "6",
            "rdisp/wp_no_btc": "2"
        }
    }


def full_diagnostic() -> dict:
    """
    Run a comprehensive health check across all three layers:
    OS (CPU, memory, disk), Oracle DB (tablespace, queries, waits),
    and SAP application (processes, work processes, alerts).
    Use this for general health checks or when correlating issues
    across layers. Returns combined results from all checks.
    """
    return {
        "system": "SBX",
        "timestamp": datetime.now().isoformat(),
        "check_type": "full_diagnostic",
        "os": check_os(),
        "oracle": check_oracle(),
        "sap": check_sap(),
    }


# ══════════════════════════════════════════════════════════════
# AGENT DEFINITION
# ══════════════════════════════════════════════════════════════

AGENT_INSTRUCTIONS = """You are an expert SAP Basis engineer and Oracle DBA
specializing in SAP ECC systems running on Oracle databases on Google Cloud
Platform (SUSE SLES).

Your system: SAP SID = SBX, Instance Number = 00, Oracle SID = SBX.

You have 4 diagnostic tools. All are READ-ONLY and safe to run anytime.

AVAILABLE TOOLS:
1. check_os — OS health: CPU, memory, disk, swap, processes, errors
2. check_oracle — Oracle DB: instance, tablespace, queries, waits, backups
3. check_sap — SAP app: processes, work processes, alerts, ICM, locks, dumps
4. full_diagnostic — Combined check across all three layers

HOW TO DIAGNOSE:
1. Start with the most relevant tool for the question
2. Look for anomalies in the results
3. Correlate across layers (e.g., high CPU → check Oracle for long queries
   → check SAP for stuck work processes)
4. Explain WHY, not just WHAT
5. Give specific, actionable recommendations

RESPONSE FORMAT:
- Status summary: healthy / warning / critical
- Key findings with severity
- Cross-layer correlations
- Specific recommendations
- Always mention which tool you used

IMPORTANT:
- All checks are read-only. You CANNOT make changes.
- If action is needed, recommend it for the Basis team to execute.
- For Oracle waits: explain in SAP context (e.g., "db file sequential read"
  = index reads, likely from SAP reports accessing BSEG/BKPF tables).
- For work processes: flag any running > 600 seconds as potentially stuck.
"""

# Create the agent
root_agent = Agent(
    name="sap_diagnostic_agent",
    model="gemini-2.5-flash",
    description="SAP ECC diagnostic agent for system SBX. Checks OS, Oracle DB, and SAP application health.",
    instruction=AGENT_INSTRUCTIONS,
    tools=[
        check_os,
        check_oracle,
        check_sap,
        full_diagnostic,
    ],
)
