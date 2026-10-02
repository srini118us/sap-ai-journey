import json
import os
import tempfile
import paramiko

DEFAULT_REGISTRY = {
    "systems": {
        "A4H": {
            "description": "SAP ABAP Platform 2023 Trial (SAP CAL on GCP)",
            "host": "YOUR_SAP_HOST_IP",
            "sid": "A4H",
            "instance_nr": "00",
            "hana_schema": "SAPA4H",
            "hana_userstore": "DEFAULT",
            "hana_userstore_sys": "HDB_KEY_CAL",
            "ssh_user": "root",
            "ssh_key_secret": "sap-basis-agent-key",
            "environment": "DEV",
            "system_type": "ABAP_PLATFORM",
            "pillars": ["infrastructure", "operations", "application"]
        },
        "BDD": {
            "description": "SAP S4HANA Development System",
            "host": "YOUR_SAP_HOST_IP",
            "sid": "BDD",
            "instance_nr": "00",
            "hana_schema": "SAPBDD",
            "hana_userstore": "DEFAULT",
            "hana_userstore_sys": "HDB_KEY_BDD",
            "ssh_user": "root",
            "ssh_key_secret": "sap-basis-agent-key",
            "environment": "DEV",
            "system_type": "S4HANA",
            "pillars": ["infrastructure", "operations", "application"]
        },
        "BDQ": {
            "description": "SAP S4HANA Quality System",
            "host": "bdq-app-01.internal",
            "sid": "BDQ",
            "instance_nr": "00",
            "hana_schema": "SAPBDQ",
            "hana_userstore": "DEFAULT",
            "hana_userstore_sys": "HDB_KEY_BDQ",
            "ssh_user": "root",
            "ssh_key_secret": "sap-bdq-ssh-key",
            "environment": "QAS",
            "system_type": "S4HANA",
            "pillars": ["infrastructure", "operations"]
        },
        "BDP": {
            "description": "SAP S4HANA Production System",
            "host": "bdp-app-01.internal",
            "sid": "BDP",
            "instance_nr": "00",
            "hana_schema": "SAPBDP",
            "hana_userstore": "DEFAULT",
            "hana_userstore_sys": "HDB_KEY_BDP",
            "ssh_user": "root",
            "ssh_key_secret": "sap-bdp-ssh-key",
            "environment": "PRD",
            "system_type": "S4HANA",
            "pillars": ["infrastructure", "operations"]
        },
        "BFP": {
            "description": "SAP Fiori Production System",
            "host": "bfp-app-01.internal",
            "sid": "BFP",
            "instance_nr": "00",
            "hana_schema": "SAPBFP",
            "hana_userstore": "DEFAULT",
            "hana_userstore_sys": "HDB_KEY_BFP",
            "ssh_user": "root",
            "ssh_key_secret": "sap-bfp-ssh-key",
            "environment": "PRD",
            "system_type": "FIORI",
            "pillars": ["infrastructure", "operations"]
        },
        "BGP": {
            "description": "SAP GRC Production System",
            "host": "bgp-app-01.internal",
            "sid": "BGP",
            "instance_nr": "00",
            "hana_schema": "SAPBGP",
            "hana_userstore": "DEFAULT",
            "hana_userstore_sys": "HDB_KEY_BGP",
            "ssh_user": "root",
            "ssh_key_secret": "sap-bgp-ssh-key",
            "environment": "PRD",
            "system_type": "GRC",
            "pillars": ["infrastructure", "operations"]
        },
        "BHP": {
            "description": "SAP HANA Platform Production",
            "host": "bhp-db-01.internal",
            "sid": "BHP",
            "instance_nr": "02",
            "hana_schema": "SAPBHP",
            "hana_userstore": "DEFAULT",
            "hana_userstore_sys": "HDB_KEY_BHP",
            "ssh_user": "root",
            "ssh_key_secret": "sap-bhp-ssh-key",
            "environment": "PRD",
            "system_type": "HANA",
            "pillars": ["infrastructure", "operations"]
        }
    }
}

PILLAR_TOOLS = {
    "infrastructure": [
        "check_disk_space", "check_system_instances", "check_kernel_version",
        "check_lock_entries", "kernel_patch_scan_sar", "kernel_patch_prechecks",
        "kernel_patch_backup", "kernel_patch_extract", "kernel_patch_stop_sap",
        "kernel_patch_apply", "kernel_patch_start_sap", "kernel_patch_postchecks",
        "kernel_patch_rollback"
    ],
    "operations": [
        "check_sap_process_health", "check_hana_health", "check_long_running_work_processes",
        "check_hana_load_history", "check_sarfc", "check_smq1_outbound",
        "check_smq2_inbound", "check_sm21_syslog",
        "check_sm20_security_audit_monitor",
        "check_critical_auth_changes",
        "check_st22_dump_triage",
        "check_hana_parameters",
        "os_patch_check",
        "os_patch_detect_app",
        "os_patch_apply",
        "os_patch_verify",
        "find_function_module",
        "get_function_module_signature",
        "check_cancelled_jobs", "check_long_running_jobs",
        "analyze_dbacockpit_cpu_screenshot", "analyze_dbacockpit_memory_screenshot"
    ],
    "application": [
        "check_failed_trfc", "reprocess_trfc_entry", "check_failed_idocs",
        "get_idoc_details", "reprocess_idoc", "check_sost_failures",
        "check_sost_failed_emails", "get_sost_failed_details", "resend_sost_email",
        "check_failed_updates", "check_hana_expensive_sql",
        "check_application_log", "list_application_log_objects",
        "check_workflow_errors", "list_workflow_summary",
        "check_stuck_workflows"
    ]
}


class SAPConnection:
    """Central connection manager for all SAP systems.
    Reads from Secret Manager (production) or DEFAULT_REGISTRY (dev/trial).
    
    Usage:
        conn = SAPConnection("BDD")
        blocked = conn.is_allowed("application")
        if blocked: return blocked
        client = conn.get_ssh_client()
    """
    GCP_PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT", "sap-basis-copilot")
    REGISTRY_SECRET = "sap-basis-system-registry"

    def __init__(self, system_id: str):
        self.system_id = system_id.upper()
        self._registry = self._load_registry()
        if self.system_id not in self._registry["systems"]:
            available = list(self._registry["systems"].keys())
            raise ValueError(
                f"System '{self.system_id}' not found in registry.\n"
                f"Available systems: {', '.join(available)}"
            )
        s = self._registry["systems"][self.system_id]
        self.description = s["description"]
        self.host = s["host"]
        self.sid = s["sid"]
        self.instance_nr = s["instance_nr"]
        self.hana_schema = s["hana_schema"]
        self.hana_userstore = s["hana_userstore"]
        self.hana_userstore_sys = s["hana_userstore_sys"]
        self.ssh_user = s["ssh_user"]
        self.ssh_key_secret = s["ssh_key_secret"]
        self.environment = s["environment"]
        self.system_type = s["system_type"]
        self.pillars = s["pillars"]
        self._ssh_key_path = None

    def _load_registry(self) -> dict:
        try:
            from google.cloud import secretmanager
            client = secretmanager.SecretManagerServiceClient()
            name = f"projects/{self.GCP_PROJECT}/secrets/{self.REGISTRY_SECRET}/versions/latest"
            response = client.access_secret_version(request={"name": name})
            return json.loads(response.payload.data.decode("UTF-8"))
        except Exception:
            return DEFAULT_REGISTRY

    def _load_ssh_key(self) -> str:
        if self._ssh_key_path and os.path.exists(self._ssh_key_path):
            return self._ssh_key_path
        local_key = os.path.expanduser(f"~/.ssh/{self.ssh_key_secret}")
        if os.path.exists(local_key):
            self._ssh_key_path = local_key
            return local_key
        try:
            from google.cloud import secretmanager
            client = secretmanager.SecretManagerServiceClient()
            name = f"projects/{self.GCP_PROJECT}/secrets/{self.ssh_key_secret}/versions/latest"
            response = client.access_secret_version(request={"name": name})
            tmp = tempfile.NamedTemporaryFile(delete=False, mode="wb", suffix=".pem")
            tmp.write(response.payload.data)
            tmp.close()
            os.chmod(tmp.name, 0o600)
            self._ssh_key_path = tmp.name
            return tmp.name
        except Exception as e:
            raise Exception(f"SSH key not found locally or in Secret Manager: {str(e)}")

    def is_allowed(self, pillar: str):
        """Returns None if allowed, or error message string if not allowed."""
        if pillar not in self.pillars:
            return (
                f"NOT ALLOWED: '{pillar}' checks are disabled for {self.system_id} "
                f"({self.environment} environment).\n"
                f"Enabled pillars: {', '.join(self.pillars)}\n"
                f"Application-layer checks on {self.environment} systems may contain "
                f"business data requiring data governance approval."
            )
        return None

    def get_ssh_client(self):
        """Returns connected paramiko SSH client for this system."""
        key_path = self._load_ssh_key()
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            client.connect(self.host, username=self.ssh_user, key_filename=key_path)
        except Exception as e:
            raise Exception(
                f"Cannot connect to {self.system_id} ({self.host}).\n"
                f"Check: Is the system running? Is the network accessible?\n"
                f"Error: {str(e)}"
            )
        return client

    def confirm_destructive(self, operation: str):
        """Returns confirmation prompt for destructive operations. None for DEV."""
        if self.environment == "PRD":
            return (
                f"PRODUCTION SYSTEM WARNING\n"
                f"System : {self.system_id} — {self.description}\n"
                f"Action : {operation}\n"
                f"Impact : This affects LIVE users on a PRODUCTION system.\n"
                f"To confirm type exactly: YES CONFIRM {self.system_id} {operation}"
            )
        elif self.environment == "QAS":
            return (
                f"Quality system {self.system_id}: Confirm {operation}? "
                f"Type 'yes proceed' to continue."
            )
        return None

    def __str__(self):
        return (
            f"SAPConnection({self.system_id}) | {self.description} | "
            f"{self.environment} | Pillars: {', '.join(self.pillars)}"
        )


def get_available_systems() -> str:
    """ADK Tool: List all SAP systems in the registry with environment and pillars."""
    lines = ["Available SAP Systems in Registry:", "=" * 50]
    for sid, cfg in DEFAULT_REGISTRY["systems"].items():
        lines.append(
            f"{sid:5} | {cfg['environment']:5} | {cfg['system_type']:15} | "
            f"{cfg['description']}"
        )
        lines.append(f"      | Pillars: {', '.join(cfg['pillars'])}")
        lines.append("")
    return "\n".join(lines)
