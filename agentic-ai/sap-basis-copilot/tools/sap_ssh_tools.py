import paramiko

def _get_ssh_key_path():
    """Get SSH key — local file in Cloud Shell, Secret Manager in Cloud Run."""
    import os, tempfile
    local = os.path.expanduser("~/.ssh/sap-basis-agent-key")
    if os.path.exists(local):
        return local
    try:
        from google.cloud import secretmanager
        client = secretmanager.SecretManagerServiceClient()
        name = "projects/sap-basis-copilot/secrets/sap-basis-agent-key/versions/latest"
        response = client.access_secret_version(request={"name": name})
        tmp = tempfile.NamedTemporaryFile(delete=False, mode="wb", suffix=".pem")
        tmp.write(response.payload.data)
        tmp.close()
        os.chmod(tmp.name, 0o600)
        return tmp.name
    except Exception as e:
        raise Exception("SSH key not found locally or in Secret Manager: " + str(e))
from sap_basis_copilot.tools.sap_connection import SAPConnection, get_available_systems, PILLAR_TOOLS
import os
import tempfile

SAP_HOST = "35.236.203.34"
SAP_USER = "root"

def get_ssh_key_path():
    key_path = _get_ssh_key_path()
    if os.path.exists(key_path):
        return key_path
    try:
        from google.cloud import secretmanager
        client = secretmanager.SecretManagerServiceClient()
        name = "projects/sap-basis-copilot/secrets/sap-basis-agent-key/versions/latest"
        response = client.access_secret_version(request={"name": name})
        key_data = response.payload.data
        tmp = tempfile.NamedTemporaryFile(delete=False, mode='wb', suffix='.pem')
        tmp.write(key_data)
        tmp.close()
        os.chmod(tmp.name, 0o600)
        return tmp.name
    except Exception as e:
        raise Exception(f"SSH key not found locally or in Secret Manager: {e}")

SAP_KEY = get_ssh_key_path()

def run_ssh_command(command: str) -> str:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(SAP_HOST, username=SAP_USER, key_filename=SAP_KEY)
        stdin, stdout, stderr = client.exec_command(command)
        output = stdout.read().decode()
        error = stderr.read().decode()
        return output if output else error
    finally:
        client.close()

def check_sap_process_health(system_id: str = "A4H") -> str:
    """Check SAP process health (SM50 equivalent) on specified system.
    system_id: SAP System ID (e.g. A4H, BDD, BDP). Default: A4H"""
    try:
        conn = SAPConnection(system_id)
        blocked = conn.is_allowed("operations")
        if blocked: return blocked
        client = conn.get_ssh_client()
        sid_lower = conn.sid.lower()
        stdin, stdout, stderr = client.exec_command(
            f"su - {sid_lower}adm -c 'sapcontrol -nr {conn.instance_nr} -function GetProcessList'"
        )
        result = stdout.read().decode()
        client.close()
        return f"[{system_id}] Process Health:\n{result}"
    except Exception as e:
        return f"[{system_id}] ERROR: {str(e)}"

def check_hana_health(system_id: str = "A4H") -> str:
    """Check HANA database health on specified system.
    system_id: SAP System ID (e.g. A4H, BDD, BDP). Default: A4H"""
    try:
        conn = SAPConnection(system_id)
        blocked = conn.is_allowed("operations")
        if blocked: return blocked
        client = conn.get_ssh_client()
        stdin, stdout, stderr = client.exec_command(
            "su - hdbadm -c 'sapcontrol -nr 02 -function GetProcessList'"
        )
        result = stdout.read().decode()
        client.close()
        return f"[{system_id}] HANA Health:\n{result}"
    except Exception as e:
        return f"[{system_id}] ERROR: {str(e)}"

def check_disk_space(system_id: str = "A4H") -> str:
    """Disk space (df -h) on the SAP host.
    system_id: SAP System ID. Default: A4H"""
    try:
        conn = SAPConnection(system_id)
        blocked = conn.is_allowed("operations")
        if blocked: return blocked
        client = conn.get_ssh_client()
        stdin, stdout, stderr = client.exec_command("df -h")
        result = stdout.read().decode()
        client.close()
        return f"[{system_id}]\n" + result
    except Exception as e:
        return f"[{system_id}] ERROR: {str(e)}"

def check_system_instances(system_id: str = "A4H") -> str:
    """Check SAP system instances (SM51 equivalent) on specified system.
    system_id: SAP System ID (e.g. A4H, BDD, BDP). Default: A4H"""
    try:
        conn = SAPConnection(system_id)
        blocked = conn.is_allowed("infrastructure")
        if blocked: return blocked
        client = conn.get_ssh_client()
        sid_lower = conn.sid.lower()
        stdin, stdout, stderr = client.exec_command(
            f"su - {sid_lower}adm -c 'sapcontrol -nr {conn.instance_nr} -function GetSystemInstanceList'"
        )
        result = stdout.read().decode()
        client.close()
        return f"[{system_id}] System Instances:\n{result}"
    except Exception as e:
        return f"[{system_id}] ERROR: {str(e)}"

def check_long_running_work_processes(system_id: str = "A4H") -> str:
    """SM66 equivalent - Global Work Process Overview.
    Flags PRIV mode processes and processes running > 10 minutes.
    system_id: SAP System ID. Default: A4H"""
    try:
        conn = SAPConnection(system_id)
        blocked = conn.is_allowed("operations")
        if blocked: return blocked
        client = conn.get_ssh_client()
        sid_lower = conn.sid.lower()
        instance = getattr(conn, "instance_nr", "00")
        stdin, stdout, stderr = client.exec_command(
            f"su - {sid_lower}adm -c 'sapcontrol -nr {instance} -function ABAPGetWPTable'"
        )
        raw = stdout.read().decode()
        client.close()
    except Exception as e:
        return f"[{system_id}] ERROR: {str(e)}"
    lines = raw.strip().split("\n")
    data_lines = [l for l in lines if l.strip() and l[0].isdigit()]
    if not data_lines:
        return f"[{system_id}] " + raw
    flagged = []
    summary = []
    for line in data_lines:
        cols = [c.strip() for c in line.split(",")]
        if len(cols) < 13:
            continue
        no, typ, pid, status, reason, start, err, sem, cpu, time_str, program, client_c, user = cols[:13]
        summary.append(f"WP{no} {typ} {status}")
        is_priv = status.upper() == "PRIV"
        is_long_run = False
        if status.lower() in ("run", "running"):
            try:
                parts = time_str.split(":")
                seconds = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2]) if len(parts) == 3 else int(parts[0]) * 60 + int(parts[1])
                if seconds > 600:
                    is_long_run = True
            except Exception:
                pass
        if is_priv or is_long_run:
            reason_tag = "PRIV (memory hog)" if is_priv else f"Running > 10 min ({time_str})"
            flagged.append(f"WP{no} ({typ}, PID {pid}): {reason_tag} | Program: {program or 'N/A'} | User: {user or 'N/A'} | Client: {client_c or 'N/A'}")
    result = f"[{system_id}] Total work processes checked: {len(data_lines)}\n"
    result += f"Status summary: {', '.join(summary)}\n\n"
    if flagged:
        result += "FLAGGED WORK PROCESSES:\n" + "\n".join(flagged)
    else:
        result += "No work processes in PRIV mode or running over 10 minutes. All healthy."
    return result

def check_lock_entries(system_id: str = "A4H") -> str:
    """SM12 equivalent - enqueue statistics.
    system_id: SAP System ID. Default: A4H"""
    try:
        conn = SAPConnection(system_id)
        blocked = conn.is_allowed("operations")
        if blocked: return blocked
        client = conn.get_ssh_client()
        sid_lower = conn.sid.lower()
        instance = getattr(conn, "instance_nr", "00")
        stdin, stdout, stderr = client.exec_command(
            f"su - {sid_lower}adm -c 'sapcontrol -nr {instance} -function EnqGetStatistic'"
        )
        result = stdout.read().decode()
        client.close()
        return f"[{system_id}] " + (result if result.strip() else "No lock statistics.")
    except Exception as e:
        return f"[{system_id}] ERROR: {str(e)}"

def check_hana_load_history(system_id: str = "A4H") -> str:
    """HANA load history (last 24h CPU/mem) from SYSTEMDB monitoring views.
    Uses the SYSTEMDB userstore key (conn.hana_systemdb_userstore) and the
    HANA OS admin user (conn.hana_os_user). These must exist in the registry
    per system; for A4H they are HDB_KEY_CAL / hdbadm.
    system_id: SAP System ID. Default: A4H"""
    try:
        conn = SAPConnection(system_id)
        blocked = conn.is_allowed("operations")
        if blocked: return blocked
        client = conn.get_ssh_client()
        sysdb_key = getattr(conn, "hana_systemdb_userstore", "HDB_KEY_CAL")
        os_user = getattr(conn, "hana_os_user", "hdbadm")
        sql = ("SELECT HOST, MAX(CPU) AS MAX_CPU_PCT, "
               "MAX(MEMORY_USED)/1024/1024 AS MAX_MEM_GB "
               "FROM SYS.M_LOAD_HISTORY_SERVICE "
               "WHERE TIME >= ADD_SECONDS(NOW(), -86400) GROUP BY HOST")
        sftp = client.open_sftp()
        with sftp.open("/tmp/hana_load.sql", "w") as f:
            f.write(sql)
        sftp.close()
        stdin, stdout, stderr = client.exec_command(
            f"su - {os_user} -c 'hdbsql -U {sysdb_key} -d SYSTEMDB -I /tmp/hana_load.sql'"
        )
        result = stdout.read().decode()
        client.close()
        return f"[{system_id}] " + (result if result.strip() else "No load history rows.")
    except Exception as e:
        return f"[{system_id}] ERROR: {str(e)}"

def check_hana_expensive_sql(system_id: str = "A4H") -> str:
    """Top 5 expensive SQL by total execution time from SYSTEMDB plan cache.
    Uses the SYSTEMDB userstore key (conn.hana_systemdb_userstore) and the
    HANA OS admin user (conn.hana_os_user). For A4H: HDB_KEY_CAL / hdbadm.
    system_id: SAP System ID. Default: A4H"""
    try:
        conn = SAPConnection(system_id)
        blocked = conn.is_allowed("operations")
        if blocked: return blocked
        client = conn.get_ssh_client()
        sysdb_key = getattr(conn, "hana_systemdb_userstore", "HDB_KEY_CAL")
        os_user = getattr(conn, "hana_os_user", "hdbadm")
        sql = ("SELECT TOP 5 STATEMENT_HASH, EXECUTION_COUNT, "
               "TOTAL_EXECUTION_TIME/1000000 AS TOTAL_SEC, "
               "LEFT(STATEMENT_STRING,80) AS STMT "
               "FROM SYS.M_SQL_PLAN_CACHE ORDER BY TOTAL_EXECUTION_TIME DESC")
        sftp = client.open_sftp()
        with sftp.open("/tmp/hana_exp.sql", "w") as f:
            f.write(sql)
        sftp.close()
        stdin, stdout, stderr = client.exec_command(
            f"su - {os_user} -c 'hdbsql -U {sysdb_key} -d SYSTEMDB -I /tmp/hana_exp.sql'"
        )
        result = stdout.read().decode()
        client.close()
        return f"[{system_id}] " + (result if result.strip() else "No expensive SQL rows.")
    except Exception as e:
        return f"[{system_id}] ERROR: {str(e)}"

def check_failed_updates(system_id: str = "A4H") -> str:
    """SM13 equivalent - count of failed update requests (VBSTATE=2).
    system_id: SAP System ID. Default: A4H"""
    try:
        conn = SAPConnection(system_id)
        blocked = conn.is_allowed("operations")
        if blocked: return blocked
        client = conn.get_ssh_client()
        sid_lower = conn.sid.lower()
        sql = f"SELECT COUNT(*) AS FAILED_UPDATES FROM {conn.hana_schema}.VBHDR WHERE VBSTATE = 2"
        sftp = client.open_sftp()
        with sftp.open("/tmp/sm13.sql", "w") as f:
            f.write(sql)
        sftp.close()
        stdin, stdout, stderr = client.exec_command(
            f"su - {sid_lower}adm -c 'hdbsql -U {conn.hana_userstore} -d HDB -I /tmp/sm13.sql'"
        )
        result = stdout.read().decode()
        client.close()
        return f"[{system_id}] " + (result if result.strip() else "No failed updates.")
    except Exception as e:
        return f"[{system_id}] ERROR: {str(e)}"

def check_failed_trfc(system_id: str = "A4H") -> str:
    """SM58 equivalent - finds failed tRFC entries (SYSFAIL state).
    system_id: SAP System ID (e.g. A4H, BDD). Default: A4H"""
    try:
        conn = SAPConnection(system_id)
        blocked = conn.is_allowed("operations")
        if blocked: return blocked
        client = conn.get_ssh_client()
        sid_lower = conn.sid.lower()
        sql = ("SELECT ARFCDEST, ARFCFNAM, ARFCMSG, ARFCUSER, ARFCTCODE, "
               "ARFCDATUM, ARFCUZEIT, ARFCRETRYS "
               f"FROM {conn.hana_schema}.ARFCSSTATE WHERE ARFCSTATE = 'SYSFAIL'")
        sftp = client.open_sftp()
        with sftp.open("/tmp/sm58_detail.sql", "w") as f:
            f.write(sql)
        sftp.close()
        stdin, stdout, stderr = client.exec_command(
            f"su - {sid_lower}adm -c 'hdbsql -U {conn.hana_userstore} -d HDB -I /tmp/sm58_detail.sql'"
        )
        result = stdout.read().decode()
        client.close()
        return f"[{system_id}] " + (result if result.strip() else "No failed tRFC entries (SM58 clean).")
    except Exception as e:
        return f"[{system_id}] ERROR: {str(e)}"

def reprocess_trfc_entry(destination: str, function_module: str) -> str:
    """Reprocesses a failed tRFC entry by triggering RSARFCEX for the specified
    destination via background job. ONLY call this after the human has explicitly
    confirmed they want to reprocess this specific entry. NEVER call this
    automatically without explicit human confirmation in the conversation,
    especially for destinations related to invoicing, billing, or customer-facing
    interfaces, where reprocessing could cause duplicate transactions."""
    cmd = f"su - a4hadm -c \"echo 'SUBMIT RSARFCEX WITH DESTIN = {destination}.' > /tmp/rsarfcex_job.txt && echo 'Job submission prepared for destination {destination}, function {function_module}. Manual execution via SE38/SM37 recommended for this trial system - RSARFCEX requires background job scheduling authorization.'\""
    return run_ssh_command(cmd)

def check_sost_failures(system_id: str = "A4H") -> str:
    """SOST equivalent - send-order status counts.
    system_id: SAP System ID. Default: A4H"""
    try:
        conn = SAPConnection(system_id)
        blocked = conn.is_allowed("operations")
        if blocked: return blocked
        client = conn.get_ssh_client()
        sid_lower = conn.sid.lower()
        sql = f"SELECT STA_ORDER, COUNT(*) AS CNT FROM {conn.hana_schema}.SOST GROUP BY STA_ORDER"
        sftp = client.open_sftp()
        with sftp.open("/tmp/sost_status.sql", "w") as f:
            f.write(sql)
        sftp.close()
        stdin, stdout, stderr = client.exec_command(
            f"su - {sid_lower}adm -c 'hdbsql -U {conn.hana_userstore} -d HDB -I /tmp/sost_status.sql'"
        )
        result = stdout.read().decode()
        client.close()
        return f"[{system_id}] " + (result if result.strip() else "No SOST entries.")
    except Exception as e:
        return f"[{system_id}] ERROR: {str(e)}"

def check_kernel_version(system_id: str = "A4H") -> str:
    """Check SAP kernel version and patch level on specified system.
    system_id: SAP System ID (e.g. A4H, BDD, BDP). Default: A4H"""
    try:
        conn = SAPConnection(system_id)
        blocked = conn.is_allowed("infrastructure")
        if blocked: return blocked
        client = conn.get_ssh_client()
        sid_lower = conn.sid.lower()
        stdin, stdout, stderr = client.exec_command(
            f"su - {sid_lower}adm -c 'disp+work -version'"
        )
        result = stdout.read().decode()
        client.close()
        return f"[{system_id}] Kernel Version:\n{result}"
    except Exception as e:
        return f"[{system_id}] ERROR: {str(e)}"

def check_cancelled_jobs(system_id: str = "A4H") -> str:
    """SM37 equivalent - cancelled jobs (status A) in last 24h.
    system_id: SAP System ID. Default: A4H"""
    try:
        conn = SAPConnection(system_id)
        blocked = conn.is_allowed("operations")
        if blocked: return blocked
        client = conn.get_ssh_client()
        sid_lower = conn.sid.lower()
        sql = ("SELECT JOBNAME, STRTDATE, STRTTIME, ENDDATE, ENDTIME, STATUS "
               f"FROM {conn.hana_schema}.TBTCO WHERE STATUS = 'A' "
               "AND STRTDATE >= TO_VARCHAR(ADD_DAYS(NOW(),-1),'YYYYMMDD') "
               "ORDER BY STRTDATE DESC")
        sftp = client.open_sftp()
        with sftp.open("/tmp/sm37c.sql", "w") as f:
            f.write(sql)
        sftp.close()
        stdin, stdout, stderr = client.exec_command(
            f"su - {sid_lower}adm -c 'hdbsql -U {conn.hana_userstore} -d HDB -I /tmp/sm37c.sql'"
        )
        result = stdout.read().decode()
        client.close()
        return f"[{system_id}] " + (result if result.strip() else "No cancelled jobs in last 24h.")
    except Exception as e:
        return f"[{system_id}] ERROR: {str(e)}"

def check_long_running_jobs(system_id: str = "A4H") -> str:
    """SM37 equivalent - running jobs (status R) started in last 24h.
    system_id: SAP System ID. Default: A4H"""
    try:
        conn = SAPConnection(system_id)
        blocked = conn.is_allowed("operations")
        if blocked: return blocked
        client = conn.get_ssh_client()
        sid_lower = conn.sid.lower()
        sql = ("SELECT JOBNAME, STRTDATE, STRTTIME, STATUS "
               f"FROM {conn.hana_schema}.TBTCO WHERE STATUS = 'R' "
               "AND STRTDATE >= TO_VARCHAR(ADD_DAYS(NOW(),-1),'YYYYMMDD') "
               "ORDER BY STRTDATE DESC")
        sftp = client.open_sftp()
        with sftp.open("/tmp/sm37l.sql", "w") as f:
            f.write(sql)
        sftp.close()
        stdin, stdout, stderr = client.exec_command(
            f"su - {sid_lower}adm -c 'hdbsql -U {conn.hana_userstore} -d HDB -I /tmp/sm37l.sql'"
        )
        result = stdout.read().decode()
        client.close()
        return f"[{system_id}] " + (result if result.strip() else "No long running jobs.")
    except Exception as e:
        return f"[{system_id}] ERROR: {str(e)}"

def analyze_dbacockpit_cpu_screenshot() -> str:
    try:
        import subprocess
        result = subprocess.run(['python3', '-c', '''
import os, base64
from google import genai
from google.cloud import storage
os.environ['GOOGLE_CLOUD_PROJECT'] = 'sap-basis-copilot'
os.environ['GOOGLE_GENAI_USE_VERTEXAI'] = 'TRUE'
client_gcs = storage.Client(project='sap-basis-copilot')
image_bytes = client_gcs.bucket('sap-basis-copilot-screenshots').blob('CHART_CPU.JPG').download_as_bytes()
image_b64 = base64.b64encode(image_bytes).decode('utf-8')
client_ai = genai.Client(vertexai=True, project='sap-basis-copilot', location='global')
response = client_ai.models.generate_content(model='gemini-3.5-flash', contents=[{'role':'user','parts':[{'inline_data':{'mime_type':'image/jpeg','data':image_b64}},{'text':'SAP DBACOCKPIT CPU chart. Extract Max CPU%, Avg CPU%, Current CPU%. Status GREEN<70% YELLOW 70-90% RED>90%.'}]}])
print('CHART_URL: https://storage.googleapis.com/sap-basis-copilot-screenshots/CHART_CPU.JPG')
print(response.text)
'''], capture_output=True, text=True, timeout=60)
        if result.stdout and result.stdout.strip():
            return result.stdout
        return 'CPU chart analysis unavailable - upload fresh screenshot to GCS bucket'
    except Exception as e:
        return f'CPU chart analysis skipped - error: {str(e)[:100]}'

def analyze_dbacockpit_memory_screenshot() -> str:
    try:
        import subprocess
        result = subprocess.run(['python3', '-c', '''
import os, base64
from google import genai
from google.cloud import storage
os.environ['GOOGLE_CLOUD_PROJECT'] = 'sap-basis-copilot'
os.environ['GOOGLE_GENAI_USE_VERTEXAI'] = 'TRUE'
client_gcs = storage.Client(project='sap-basis-copilot')
image_bytes = client_gcs.bucket('sap-basis-copilot-screenshots').blob('CHART_usedmemory.JPG').download_as_bytes()
image_b64 = base64.b64encode(image_bytes).decode('utf-8')
client_ai = genai.Client(vertexai=True, project='sap-basis-copilot', location='global')
response = client_ai.models.generate_content(model='gemini-3.5-flash', contents=[{'role':'user','parts':[{'inline_data':{'mime_type':'image/jpeg','data':image_b64}},{'text':'SAP DBACOCKPIT Memory chart. Extract Max Memory MB, Avg Memory MB, Current Memory MB. Calculate utilization %. Status GREEN<70% YELLOW 70-85% RED>85%.'}]}])
print(response.text)
'''], capture_output=True, text=True, timeout=60)
        if result.stdout and result.stdout.strip():
            return result.stdout
        return 'Memory chart analysis unavailable - upload fresh screenshot to GCS bucket'
    except Exception as e:
        return f'Memory chart analysis skipped - error: {str(e)[:100]}'

def check_sarfc(system_id: str = "A4H") -> str:
    """SARFC equivalent - RFC server group resources from RZLLITAB.
    system_id: SAP System ID. Default: A4H"""
    try:
        conn = SAPConnection(system_id)
        blocked = conn.is_allowed("operations")
        if blocked: return blocked
        client = conn.get_ssh_client()
        sid_lower = conn.sid.lower()
        sql = ("SELECT CLASSNAME, APPLSERVER, WP_QUOTA, USERS, GROUPTYPE "
               f"FROM {conn.hana_schema}.RZLLITAB ORDER BY CLASSNAME, APPLSERVER")
        sftp = client.open_sftp()
        with sftp.open("/tmp/sarfc_check.sql", "w") as f:
            f.write(sql)
        sftp.close()
        stdin, stdout, stderr = client.exec_command(
            f"su - {sid_lower}adm -c 'hdbsql -U {conn.hana_userstore} -d HDB -I /tmp/sarfc_check.sql'"
        )
        result = stdout.read().decode()
        client.close()
        if not result.strip():
            return f"[{system_id}] No RFC server groups in RZLLITAB. Check RZ12."
        return f"[{system_id}] {result}"
    except Exception as e:
        return f"[{system_id}] ERROR: {str(e)}"

def check_failed_idocs(system_id: str = "A4H") -> str:
    """BD87 equivalent - finds failed IDocs grouped by message type and status.
    APPLICATION pillar required - blocked on PRD systems by default.
    system_id: SAP System ID (e.g. A4H, BDD). Default: A4H"""
    try:
        conn = SAPConnection(system_id)
        blocked = conn.is_allowed("application")
        if blocked: return f"[{system_id}] {blocked}"
        import paramiko as _p
        client = conn.get_ssh_client()
        sid_lower = conn.sid.lower()
        sql = ("SELECT MESTYP, STATUS, DIRECT, COUNT(*) AS CNT, "
               "MIN(CREDAT) AS OLDEST, MAX(CREDAT) AS NEWEST "
               f"FROM {conn.hana_schema}.EDIDC "
               "WHERE STATUS NOT IN ('03','06','12','16','18','30','53') "
               "AND UPDDAT >= TO_VARCHAR(ADD_DAYS(NOW(),-7),'YYYYMMDD') "
               "GROUP BY MESTYP, STATUS, DIRECT ORDER BY CNT DESC")
        sftp = client.open_sftp()
        with sftp.open("/tmp/idoc_check.sql", "w") as f:
            f.write(sql)
        sftp.close()
        stdin, stdout, stderr = client.exec_command(
            f"su - {sid_lower}adm -c 'hdbsql -U {conn.hana_userstore} -d HDB -I /tmp/idoc_check.sql'"
        )
        result = stdout.read().decode()
        client.close()
        return f"[{system_id}] " + (result if result.strip() else "No failed IDocs found in last 7 days.")
    except Exception as e:
        return f"[{system_id}] ERROR: {str(e)}"

def get_idoc_details(mestyp: str, status: str, system_id: str = "A4H") -> str:
    """Get details of failed IDocs for a specific message type and status.
    system_id: SAP System ID. Default: A4H"""
    try:
        conn = SAPConnection(system_id)
        blocked = conn.is_allowed("application")
        if blocked: return f"[{system_id}] {blocked}"
        client = conn.get_ssh_client()
        sid_lower = conn.sid.lower()
        sql = ("SELECT DOCNUM, MESTYP, STATUS, DIRECT, RCVPRT, RCVPRN, "
               "SNDPRT, SNDPRN, CREDAT, CRETIM, UPDDAT, UPDTIM "
               f"FROM {conn.hana_schema}.EDIDC "
               f"WHERE MESTYP = '{mestyp}' AND STATUS = '{status}' "
               "AND UPDDAT >= TO_VARCHAR(ADD_DAYS(NOW(),-7),'YYYYMMDD') "
               "ORDER BY CREDAT DESC, CRETIM DESC")
        sftp = client.open_sftp()
        with sftp.open("/tmp/idoc_detail.sql", "w") as f:
            f.write(sql)
        sftp.close()
        stdin, stdout, stderr = client.exec_command(
            f"su - {sid_lower}adm -c 'hdbsql -U {conn.hana_userstore} -d HDB -I /tmp/idoc_detail.sql'"
        )
        result = stdout.read().decode()
        client.close()
        return f"[{system_id}] " + (result if result.strip() else f"No IDocs for MESTYP={mestyp} STATUS={status}.")
    except Exception as e:
        return f"[{system_id}] ERROR: {str(e)}"

def reprocess_idoc(docnum: str) -> str:
    """Reprocess a specific failed IDoc by document number.
    ONLY call this after explicit human confirmation that:
    1. The IDoc is a TECHNICAL error (not a business data error)
    2. The application team has confirmed reprocessing is safe
    3. Root cause has been investigated
    NEVER call automatically - duplicate postings are a serious business risk."""
    audit_entry = f"IDoc reprocess requested: DOCNUM={docnum}"
    cmd = f"echo '{audit_entry}' >> /tmp/idoc_audit.log && echo 'IDoc {docnum} reprocess prepared. To execute: in SAP GUI go to BD87, enter IDoc number {docnum}, select and click Reprocess. Or run report RBDMANI2 via SE38 with IDoc number. Audit log entry created.'"
    return run_ssh_command(cmd)

def check_smq1_outbound(system_id: str = "A4H") -> str:
    """SMQ1 equivalent - outbound qRFC queues, stuck/failed entries.
    system_id: SAP System ID. Default: A4H"""
    try:
        conn = SAPConnection(system_id)
        blocked = conn.is_allowed("operations")
        if blocked: return blocked
        client = conn.get_ssh_client()
        sid_lower = conn.sid.lower()
        sch = conn.hana_schema
        sql = ("SELECT Q.QUEUE_NAME, Q.DEST_NAME, Q.CLIENT, "
               "COUNT(Q.UNIT_ID) AS QUEUE_DEPTH, E.MESSAGE "
               f"FROM {sch}.QRFC_N_QOUT Q "
               f"LEFT JOIN {sch}.QRFC_I_ERR_STATE E ON Q.UNIT_ID = E.UNIT_ID "
               "GROUP BY Q.QUEUE_NAME, Q.DEST_NAME, Q.CLIENT, E.MESSAGE "
               "ORDER BY QUEUE_DEPTH DESC")
        sftp = client.open_sftp()
        with sftp.open("/tmp/smq1.sql", "w") as f:
            f.write(sql)
        sftp.close()
        stdin, stdout, stderr = client.exec_command(
            f"su - {sid_lower}adm -c 'hdbsql -U {conn.hana_userstore} -d HDB -I /tmp/smq1.sql'"
        )
        result = stdout.read().decode()
        client.close()
        return f"[{system_id}] " + (result if result.strip() else "No outbound qRFC entries (SMQ1 clean).")
    except Exception as e:
        return f"[{system_id}] ERROR: {str(e)}"

def check_smq2_inbound(system_id: str = "A4H") -> str:
    """SMQ2 equivalent - inbound qRFC queues, stuck/failed entries.
    system_id: SAP System ID. Default: A4H"""
    try:
        conn = SAPConnection(system_id)
        blocked = conn.is_allowed("operations")
        if blocked: return blocked
        client = conn.get_ssh_client()
        sid_lower = conn.sid.lower()
        sch = conn.hana_schema
        sql = ("SELECT Q.QUEUE_NAME, Q.DEST_NAME, Q.CLIENT, "
               "COUNT(Q.UNIT_ID) AS QUEUE_DEPTH, E.MESSAGE "
               f"FROM {sch}.QRFC_I_QIN Q "
               f"LEFT JOIN {sch}.QRFC_I_ERR_STATE E ON Q.UNIT_ID = E.UNIT_ID "
               "GROUP BY Q.QUEUE_NAME, Q.DEST_NAME, Q.CLIENT, E.MESSAGE "
               "ORDER BY QUEUE_DEPTH DESC")
        sftp = client.open_sftp()
        with sftp.open("/tmp/smq2.sql", "w") as f:
            f.write(sql)
        sftp.close()
        stdin, stdout, stderr = client.exec_command(
            f"su - {sid_lower}adm -c 'hdbsql -U {conn.hana_userstore} -d HDB -I /tmp/smq2.sql'"
        )
        result = stdout.read().decode()
        client.close()
        return f"[{system_id}] " + (result if result.strip() else "No inbound qRFC entries (SMQ2 clean).")
    except Exception as e:
        return f"[{system_id}] ERROR: {str(e)}"

def check_st22_dumps(system_id: str = "A4H") -> str:
    """ST22 equivalent (legacy simple) - ABAP short dumps last 24h, top 10.
    NOTE: check_st22_dump_triage (UC-D1) is the richer replacement.
    system_id: SAP System ID. Default: A4H"""
    try:
        conn = SAPConnection(system_id)
        blocked = conn.is_allowed("operations")
        if blocked: return blocked
        client = conn.get_ssh_client()
        sid_lower = conn.sid.lower()
        sql = ("SELECT TOP 10 SNAPDATE, ERRTY, ERRCLAS, REPID, "
               "LEFT(ERRMESS, 80) AS ERROR_MSG, COUNT(*) AS DUMP_COUNT "
               f"FROM {conn.hana_schema}.SNAP "
               "WHERE SNAPDATE >= TO_VARCHAR(ADD_DAYS(NOW(),-1),'YYYYMMDD') "
               "GROUP BY SNAPDATE, ERRTY, ERRCLAS, REPID, ERRMESS "
               "ORDER BY DUMP_COUNT DESC")
        sftp = client.open_sftp()
        with sftp.open("/tmp/st22.sql", "w") as f:
            f.write(sql)
        sftp.close()
        stdin, stdout, stderr = client.exec_command(
            f"su - {sid_lower}adm -c 'hdbsql -U {conn.hana_userstore} -d HDB -I /tmp/st22.sql'"
        )
        result = stdout.read().decode()
        client.close()
        return f"[{system_id}] " + (result if result.strip() else "No ABAP short dumps in last 24h.")
    except Exception as e:
        return f"[{system_id}] ERROR: {str(e)}"

def check_sm21_syslog(system_id: str = "A4H") -> str:
    """SM21 equivalent - SAP system log, critical errors only.
    system_id: SAP System ID. Default: A4H"""
    try:
        conn = SAPConnection(system_id)
        blocked = conn.is_allowed("operations")
        if blocked: return blocked
        client = conn.get_ssh_client()
        sid_lower = conn.sid.lower()
        instance = getattr(conn, "instance_nr", "00")
        stdin, stdout, stderr = client.exec_command(
            f"su - {sid_lower}adm -c 'sapcontrol -nr {instance} -function ABAPReadSyslog' "
            "| grep -E '(Error|Abort|Critical|ABAP|kernel|restart|dump|shutdown)' | head -20"
        )
        result = stdout.read().decode()
        client.close()
        if not result.strip():
            return f"[{system_id}] No critical errors in SAP system log (SM21 GREEN)."
        return f"[{system_id}] {result}"
    except Exception as e:
        return f"[{system_id}] ERROR: {str(e)}"

def check_sm20_security_audit_monitor(system_id: str = "A4H", hours: int = 24) -> str:
    """SM20 equivalent - Security Audit Log Monitor (UC-S1).
    Queries the Security Audit Log runtime buffer table (RSAU_BUF_DATA) for
    audit events. Schema confirmed on A4H: AREA, SUBID, SLGDATTIM, SLGUSER,
    SLGTC, SLGREPNA, TERM_IPV6, SLGLTRM2, SAL_DATA. Returns the last 200 events
    ordered by timestamp so the calling agent can classify severity
    (INFO/WARNING/CRITICAL) - failed logon attempts, authorization failures on
    sensitive transactions, and user master record changes.
    READ-ONLY - OPERATIONS pillar. Does not modify anything.
    system_id: SAP System ID (e.g. A4H, BDD, BDP). Default: A4H
    hours: lookback window in hours, human-readable label only."""
    try:
        conn = SAPConnection(system_id)
        blocked = conn.is_allowed("operations")
        if blocked: return blocked
        client = conn.get_ssh_client()
        sid_lower = conn.sid.lower()
        userstore = conn.hana_userstore
        schema = conn.hana_schema

        count_sql = f"SELECT COUNT(*) AS ROW_COUNT FROM {schema}.RSAU_BUF_DATA"
        sftp = client.open_sftp()
        with sftp.open("/tmp/sm20_count.sql", "w") as f:
            f.write(count_sql)
        sftp.close()
        stdin, stdout, stderr = client.exec_command(
            f"su - {sid_lower}adm -c 'hdbsql -U {userstore} -d HDB -I /tmp/sm20_count.sql'"
        )
        count_result = stdout.read().decode()
        count_err = stderr.read().decode()
        if "invalid table name" in (count_result + count_err).lower() or \
           "not found" in (count_result + count_err).lower():
            client.close()
            return (
                f"[{system_id}] RSAU_BUF_DATA not found in schema {schema}.\n"
                f"This SAP release may store the security audit log under a different "
                f"table name (e.g. RSAU_BUF_DATA_DB on some releases). Raw error:\n"
                f"{count_result}{count_err}"
            )

        data_sql = (
            f"SELECT TOP 200 AREA, SUBID, SLGDATTIM, SLGUSER, SLGTC, SLGREPNA, "
            f"TERM_IPV6, SLGLTRM2, SAL_DATA FROM {schema}.RSAU_BUF_DATA "
            f"ORDER BY SLGDATTIM DESC"
        )
        sftp = client.open_sftp()
        with sftp.open("/tmp/sm20_check.sql", "w") as f:
            f.write(data_sql)
        sftp.close()
        stdin, stdout, stderr = client.exec_command(
            f"su - {sid_lower}adm -c 'hdbsql -U {userstore} -d HDB -I /tmp/sm20_check.sql'"
        )
        result = stdout.read().decode()
        err = stderr.read().decode()
        client.close()

        if not result.strip():
            return (
                f"[{system_id}] SM20 Security Audit Log: 0 rows in RSAU_BUF_DATA "
                f"(table exists but is empty).\n"
                f"Row count check returned: {count_result.strip()}\n"
                f"Likely cause: SM19/RSAU_CONFIG audit logging is not active, or no "
                f"qualifying events have occurred yet since it was activated.\n"
                f"Action: activate audit logging via RSAU_CONFIG (SAP GUI), generate a "
                f"test event (e.g. a deliberate failed logon), then re-run this check."
            )
        return (
            f"[{system_id}] SM20 Security Audit Log - raw buffer contents "
            f"(requested window label: last {hours}h):\n{result}\n"
            f"stderr (if any): {err.strip()[:300]}"
        )
    except Exception as e:
        return f"[{system_id}] ERROR: {str(e)}"

def check_sost_failed_emails(system_id: str = "A4H") -> str:
    """SOST detailed - failed entries grouped by error reason and send type.
    system_id: SAP System ID. Default: A4H"""
    try:
        conn = SAPConnection(system_id)
        blocked = conn.is_allowed("application")
        if blocked: return f"[{system_id}] {blocked}"
        client = conn.get_ssh_client()
        sid_lower = conn.sid.lower()
        sql = ("SELECT SNDART, MSGID, MSGNO, LEFT(MSGV1,60) AS ERROR_REASON, "
               "COUNT(*) AS CNT, MIN(ENTRY_DATE) AS OLDEST, MAX(ENTRY_DATE) AS NEWEST "
               f"FROM {conn.hana_schema}.SOST "
               "WHERE STA_ORDER NOT IN ('S','E') "
               "OR (STA_ORDER = 'E' AND ENTRY_DATE >= TO_VARCHAR(ADD_DAYS(NOW(),-1),'YYYYMMDD')) "
               "GROUP BY SNDART, MSGID, MSGNO, MSGV1 ORDER BY CNT DESC")
        sftp = client.open_sftp()
        with sftp.open("/tmp/sost_failed.sql", "w") as f:
            f.write(sql)
        sftp.close()
        stdin, stdout, stderr = client.exec_command(
            f"su - {sid_lower}adm -c 'hdbsql -U {conn.hana_userstore} -d HDB -I /tmp/sost_failed.sql'"
        )
        result = stdout.read().decode()
        client.close()
        return f"[{system_id}] " + (result if result.strip() else "No failed SOST entries in last 24h.")
    except Exception as e:
        return f"[{system_id}] ERROR: {str(e)}"

def get_sost_failed_details(system_id: str = "A4H") -> str:
    """Full details of failed SOST entries for human review before resend.
    system_id: SAP System ID. Default: A4H"""
    try:
        conn = SAPConnection(system_id)
        blocked = conn.is_allowed("application")
        if blocked: return f"[{system_id}] {blocked}"
        client = conn.get_ssh_client()
        sid_lower = conn.sid.lower()
        sql = ("SELECT OBJTP, OBJYR, OBJNO, SNDART, CREATOR, SENDER, "
               "ENTRY_DATE, ENTRY_TIME, STA_ORDER, MSGID, MSGNO, LEFT(MSGV1,60) AS ERROR "
               f"FROM {conn.hana_schema}.SOST "
               "WHERE STA_ORDER NOT IN ('S','E') "
               "OR (STA_ORDER = 'E' AND ENTRY_DATE >= TO_VARCHAR(ADD_DAYS(NOW(),-1),'YYYYMMDD')) "
               "ORDER BY ENTRY_DATE DESC, ENTRY_TIME DESC")
        sftp = client.open_sftp()
        with sftp.open("/tmp/sost_details.sql", "w") as f:
            f.write(sql)
        sftp.close()
        stdin, stdout, stderr = client.exec_command(
            f"su - {sid_lower}adm -c 'hdbsql -U {conn.hana_userstore} -d HDB -I /tmp/sost_details.sql'"
        )
        result = stdout.read().decode()
        client.close()
        return f"[{system_id}] " + (result if result.strip() else "No failed SOST entries.")
    except Exception as e:
        return f"[{system_id}] ERROR: {str(e)}"

def resend_sost_email(object_type: str, object_year: str, object_number: str) -> str:
    """Resend a specific failed SOST entry by object key.
    ONLY call after explicit human confirmation that:
    1. The recipient address is valid
    2. The content is correct
    3. Resending will not cause duplicates
    NEVER call automatically - duplicate emails to customers/vendors are a serious risk."""
    audit_entry = f"SOST resend requested: OBJTP={object_type} OBJYR={object_year} OBJNO={object_number}"
    cmd = f"echo '{audit_entry}' >> /tmp/sost_audit.log && echo 'SOST resend prepared for object {object_type}/{object_year}/{object_number}. To execute: in SAP GUI go to SOST, find this entry and click Resend. Or run report RSOSTSND via SE38. Audit log entry created at /tmp/sost_audit.log'"
    return run_ssh_command(cmd)


def kernel_patch_scan_sar(staging_dir='/usr/sap/basis/kernel') -> str:
    """Scan staging directory for SAR files and validate integrity."""
    cmd = f'''
STAGING="{staging_dir}"
echo "=== SAR FILE SCAN ==="
if [ ! -d "$STAGING" ]; then
    echo "ERROR: Staging directory $STAGING does not exist."
    echo "Please create it and upload SAR files:"
    echo "  mkdir -p $STAGING"
    exit 1
fi
SAR_FILES=$(find $STAGING -name "*.SAR" -o -name "*.sar" 2>/dev/null)
if [ -z "$SAR_FILES" ]; then
    echo "ERROR: No SAR files found in $STAGING"
    echo "Please upload kernel patch SAR files and try again."
    exit 1
fi
echo "Found SAR files:"
echo "$SAR_FILES" | while read f; do
    size=$(ls -lh "$f" | awk "{{print $5}}")
    echo "  $(basename $f) [$size]"
done
echo ""
echo "Validating integrity..."
ALL_OK=true
echo "$SAR_FILES" | while read f; do
    echo -n "  $(basename $f): "
    /usr/sap/A4H/D00/exe/SAPCAR -t -f "$f" > /dev/null 2>&1
    if [ $? -eq 0 ]; then echo "OK"
    else echo "FAILED - corrupted!"; ALL_OK=false; fi
done
echo ""
if [ "$ALL_OK" = "true" ]; then
    echo "All $(echo "$SAR_FILES" | wc -l) SAR files valid and ready."
else
    echo "WARNING: Some files failed validation. Re-download before patching."
fi
'''
    return run_ssh_command(cmd)

def kernel_patch_prechecks(staging_dir='/usr/sap/basis/kernel') -> str:
    """Run all pre-checks: kernel version, exe locations, health, jobs, disk space."""
    import paramiko as _p
    client = _p.SSHClient()
    client.set_missing_host_key_policy(_p.AutoAddPolicy())
    client.connect(SAP_HOST, username=SAP_USER, key_filename=SAP_KEY)
    results = []

    stdin, stdout, stderr = client.exec_command(
        "su - a4hadm -c 'disp+work -version' | grep -E 'kernel release|patch number|compile time'"
    )
    results.append("=== CURRENT KERNEL VERSION ===")
    results.append(stdout.read().decode().strip())

    stdin, stdout, stderr = client.exec_command(
        "find /usr/sap /sapmnt -name 'disp+work' 2>/dev/null | grep -v backup | grep -v extract | grep -v kernel_patch"
    )
    exe_locations = stdout.read().decode().strip()
    results.append("\n=== EXE DIRECTORIES (will be backed up and patched) ===")
    for loc in exe_locations.split('\n'):
        if loc:
            stdin2, stdout2, _ = client.exec_command(f"strings {loc} 2>/dev/null | grep SAPProductVersion")
            ver = stdout2.read().decode().strip()
            results.append(f"  {loc} -> {ver}")

    stdin, stdout, stderr = client.exec_command(
        "su - a4hadm -c 'sapcontrol -nr 00 -function GetProcessList' | grep -E 'GREEN|YELLOW|RED|GRAY'"
    )
    health = stdout.read().decode().strip()
    results.append("\n=== SYSTEM HEALTH ===")
    if 'RED' in health:
        results.append("WARNING: RED processes found! Resolve before patching.")
    results.append(health)

    sftp = client.open_sftp()
    with sftp.open('/tmp/kpre_jobs.sql', 'w') as f:
        f.write("SELECT COUNT(*) AS RUNNING_JOBS FROM SAPA4H.TBTCO WHERE STATUS = 'R'")
    with sftp.open('/tmp/kpre_upd.sql', 'w') as f:
        f.write("SELECT COUNT(*) AS OPEN_UPDATES FROM SAPA4H.VBHDR WHERE VBSTATE = 2")
    sftp.close()

    stdin, stdout, stderr = client.exec_command(
        "su - a4hadm -c 'hdbsql -U DEFAULT -d HDB -I /tmp/kpre_jobs.sql'"
    )
    results.append("\n=== RUNNING JOBS (ideally 0 before patching) ===")
    results.append(stdout.read().decode().strip())

    stdin, stdout, stderr = client.exec_command(
        "su - a4hadm -c 'hdbsql -U DEFAULT -d HDB -I /tmp/kpre_upd.sql'"
    )
    results.append("\n=== OPEN UPDATE REQUESTS SM13 (ideally 0) ===")
    results.append(stdout.read().decode().strip())

    stdin, stdout, stderr = client.exec_command("df -h /usr/sap | tail -1")
    results.append("\n=== DISK SPACE (/usr/sap) ===")
    results.append(stdout.read().decode().strip())

    stdin, stdout, stderr = client.exec_command(
        f"find {staging_dir} -name '*.SAR' -o -name '*.sar' 2>/dev/null | wc -l"
    )
    sar_count = stdout.read().decode().strip()
    results.append(f"\n=== SAR FILES IN {staging_dir} ===")
    results.append(f"  {sar_count} SAR file(s) ready for patching")

    client.close()
    return "\n".join(results)

def kernel_patch_backup() -> str:
    """Backup ALL exe directories dynamically found on the system."""
    cmd = '''
echo "=== KERNEL BACKUP ==="
timestamp=$(date +%Y%m%d_%H%M%S)
backup_root="/usr/sap/kernel_backup_${timestamp}"
mkdir -p ${backup_root}
EXE_DIRS=$(find /usr/sap /sapmnt -name "disp+work" 2>/dev/null | grep -v backup | grep -v extract | grep -v kernel_patch | xargs -I{} dirname {})
if [ -z "$EXE_DIRS" ]; then
    echo "ERROR: No exe directories found to backup!"; exit 1
fi
echo "Backing up exe directories:"
echo "$EXE_DIRS" | while read dir; do
    safe_name=$(echo "$dir" | tr '/' '_' | sed 's/^_//')
    backup_dir="${backup_root}/${safe_name}"
    mkdir -p "${backup_dir}"
    cp -rp "${dir}/"* "${backup_dir}/" 2>/dev/null || true
    echo "  $dir -> backed up $(ls ${backup_dir} | wc -l) files"
done
echo "BACKUP_ROOT=${backup_root}" > /tmp/kernel_backup_info.txt
echo "BACKUP_TIMESTAMP=${timestamp}" >> /tmp/kernel_backup_info.txt
echo ""
echo "=== BACKUP COMPLETE ==="
echo "Location: ${backup_root}"
echo "Size: $(du -sh ${backup_root} | cut -f1)"
'''
    return run_ssh_command(cmd)

def kernel_patch_extract(staging_dir='/usr/sap/basis/kernel') -> str:
    """Extract all SAR files from staging directory to /tmp/kernel_extract/."""
    cmd = f'''
echo "=== EXTRACTING SAR FILES ==="
EXTRACT_DIR="/usr/sap/basis/kernel/extract"
mkdir -p ${{EXTRACT_DIR}}
SAR_FILES=$(find {staging_dir} -name "*.SAR" -o -name "*.sar" 2>/dev/null)
if [ -z "$SAR_FILES" ]; then
    echo "ERROR: No SAR files in {staging_dir}"; exit 1
fi
echo "$SAR_FILES" | while read f; do
    echo "Extracting: $(basename $f)"
    /usr/sap/A4H/D00/exe/SAPCAR -xf "$f" -R "${{EXTRACT_DIR}}/" 2>&1 | tail -2
done
echo ""
echo "=== EXTRACTION COMPLETE ==="
echo "Files extracted: $(ls ${{EXTRACT_DIR}} | wc -l)"
echo "Key files:"
ls ${{EXTRACT_DIR}} | grep -E "disp|sapstart|R3trans|SAPCAR|icmbnd" | head -10
if [ -f "${{EXTRACT_DIR}}/disp+work" ]; then
    echo "Patch level in extract:"
    strings "${{EXTRACT_DIR}}/disp+work" | grep SAPProductVersion
fi
'''
    return run_ssh_command(cmd)

def kernel_patch_start_sap() -> str:
    """Step 7: Start SAP and WAIT until ALL key processes are GREEN.
    Keeps waiting in intervals - does NOT timeout and exit.
    If RED process detected: reports for human decision."""
    cmd = '''
echo "=== STARTING SAP WITH NEW KERNEL ==="
su - a4hadm -c 'sapcontrol -nr 00 -function Start'
echo "Waiting for all processes to reach GREEN status..."
elapsed=0
interval=20
while true; do
    sleep $interval
    elapsed=$((elapsed + interval))
    status=$(su - a4hadm -c 'sapcontrol -nr 00 -function GetProcessList' 2>/dev/null)
    green=$(echo "$status" | grep -c "GREEN" || true)
    red=$(echo "$status" | grep -c "RED" || true)
    gray=$(echo "$status" | grep -c "GRAY" || true)
    yellow=$(echo "$status" | grep -c "YELLOW" || true)
    echo "[${elapsed}s] GREEN: $green | RED: $red | YELLOW: $yellow | GRAY: $gray"
    if [ "$red" -gt 0 ]; then
        echo ""
        echo "=== WARNING: RED PROCESS DETECTED ==="
        echo "$status"
        echo "Check: /usr/sap/A4H/D00/work/dev_disp"
        echo "Check: /usr/sap/A4H/D00/work/dev_w0"
        echo "Run kernel_patch_rollback() if needed."
        break
    fi
    if [ "$green" -ge 4 ] && [ "$gray" -eq 0 ] && [ "$red" -eq 0 ]; then
        echo ""
        echo "=== SAP STARTED SUCCESSFULLY after ${elapsed}s ==="
        echo "$status"
        break
    fi
    if [ "$elapsed" -ge 600 ]; then
        echo "Taking longer than expected (${elapsed}s) - continuing to wait..."
        echo "$status"
    fi
done
'''
    return run_ssh_command(cmd)

def kernel_patch_stop_sap() -> str:
    """Stop SAP and wait until ALL processes are GRAY. Never returns early."""
    cmd = '''
echo "=== STOPPING SAP ==="
su - a4hadm -c 'sapcontrol -nr 00 -function Stop'
echo "Waiting for all processes to reach GRAY..."
elapsed=0
interval=15
while true; do
    sleep $interval
    elapsed=$((elapsed + interval))
    status=$(su - a4hadm -c 'sapcontrol -nr 00 -function GetProcessList' 2>/dev/null)
    green=$(echo "$status" | grep -c "GREEN" || true)
    yellow=$(echo "$status" | grep -c "YELLOW" || true)
    gray=$(echo "$status" | grep -c "GRAY" || true)
    running=$((green + yellow))
    echo "[${elapsed}s] Running: $running | Stopped(GRAY): $gray"
    if [ "$running" -eq 0 ] && [ "$gray" -gt 0 ]; then
        echo ""
        echo "=== SAP FULLY STOPPED after ${elapsed}s ==="
        echo "Safe to proceed with kernel patching."
        break
    fi
    if [ "$elapsed" -ge 300 ]; then
        echo ""
        echo "=== TAKING LONGER THAN 5 MINUTES ==="
        echo "Current status:"
        echo "$status"
        echo ""
        echo "Possible causes: long-running jobs, active sessions"
        echo "Check SM66 for stuck work processes"
        echo "Continuing to wait..."
        echo ""
    fi
done
'''
    return run_ssh_command(cmd)

def kernel_patch_apply() -> str:
    """Apply extracted kernel to ALL exe directories found dynamically."""
    cmd = '''
echo "=== APPLYING KERNEL PATCH ==="
EXTRACT_DIR="/usr/sap/basis/kernel/extract"
if [ ! -d "$EXTRACT_DIR" ] || [ -z "$(ls $EXTRACT_DIR 2>/dev/null)" ]; then
    echo "ERROR: /tmp/kernel_extract is empty. Run kernel_patch_extract() first."
    exit 1
fi
green=$(su - a4hadm -c 'sapcontrol -nr 00 -function GetProcessList' 2>/dev/null | grep -c "GREEN" || true)
if [ "$green" -gt 0 ]; then
    echo "ERROR: SAP still running ($green GREEN processes)! Stop SAP first."
    exit 1
fi
EXE_DIRS=$(find /usr/sap /sapmnt -name "disp+work" 2>/dev/null | grep -v backup | grep -v extract | grep -v kernel_patch | xargs -I{} dirname {})
echo "Updating exe directories:"
echo "$EXE_DIRS" | while read dir; do
    echo "  Updating: $dir"
    if [ -f "$EXTRACT_DIR/disp+work" ]; then
        cp -fp "$EXTRACT_DIR/disp+work" "$dir/disp+work"
    fi
    cp -fp $EXTRACT_DIR/* "$dir/" 2>/dev/null || true
    chown -R a4hadm:sapsys "$dir/" 2>/dev/null || true
    ver=$(strings "$dir/disp+work" 2>/dev/null | grep SAPProductVersion || echo "unknown")
    echo "    $ver"
done
echo ""
echo "=== PATCH APPLIED ==="
echo "Final verification:"
find /usr/sap /sapmnt -name "disp+work" 2>/dev/null | grep -v backup | grep -v extract | grep -v kernel_patch | while read f; do
    ver=$(strings "$f" 2>/dev/null | grep SAPProductVersion)
    echo "  $f: $ver"
done
'''
    return run_ssh_command(cmd)

def kernel_patch_postchecks() -> str:
    """Post-patch verification: kernel version, process health, work processes, system log, audit log."""
    import paramiko as _p
    client = _p.SSHClient()
    client.set_missing_host_key_policy(_p.AutoAddPolicy())
    client.connect(SAP_HOST, username=SAP_USER, key_filename=SAP_KEY)
    results = []

    stdin, stdout, stderr = client.exec_command(
        "su - a4hadm -c 'disp+work -version' | grep -E 'kernel release|patch number|compile time'"
    )
    results.append("=== NEW KERNEL VERSION ===")
    results.append(stdout.read().decode().strip())

    stdin, stdout, stderr = client.exec_command(
        "find /usr/sap /sapmnt -name 'disp+work' 2>/dev/null | grep -v backup | grep -v extract | grep -v kernel_patch"
    )
    exe_files = stdout.read().decode().strip().split('\n')
    results.append("\n=== ALL EXE LOCATIONS VERIFIED ===")
    for exe in exe_files:
        if exe:
            stdin2, stdout2, _ = client.exec_command(f"strings {exe} 2>/dev/null | grep SAPProductVersion")
            ver = stdout2.read().decode().strip()
            ok = "OK" if "200" in ver else "CHECK NEEDED"
            results.append(f"  {exe}: {ver} [{ok}]")

    stdin, stdout, stderr = client.exec_command(
        "su - a4hadm -c 'sapcontrol -nr 00 -function GetProcessList'"
    )
    proc = stdout.read().decode().strip()
    results.append("\n=== PROCESS HEALTH ===")
    results.append(proc)
    if 'RED' in proc:
        results.append("CRITICAL: RED processes! Consider rollback.")
    elif 'GREEN' in proc:
        results.append("All processes GREEN - patch successful!")

    stdin, stdout, stderr = client.exec_command(
        "su - a4hadm -c 'sapcontrol -nr 00 -function ABAPReadSyslog' | grep -iE 'error|abort|dump' | grep -v 'profile' | head -5"
    )
    syslog = stdout.read().decode().strip()
    results.append("\n=== SYSTEM LOG (errors only) ===")
    results.append(syslog if syslog else "No critical errors - GOOD")

    stdin, stdout, stderr = client.exec_command(
        "echo '--- Kernel Patch Audit ---' >> /tmp/kernel_patch_audit.log && "
        "echo 'Date/Time: '$(date) >> /tmp/kernel_patch_audit.log && "
        "echo 'System: A4H on GCP (sap-basis-copilot)' >> /tmp/kernel_patch_audit.log && "
        "su - a4hadm -c 'disp+work -version' | grep -E 'kernel release|patch number' >> /tmp/kernel_patch_audit.log && "
        "echo 'Patched by: SAP Basis Copilot ADK Agent' >> /tmp/kernel_patch_audit.log && "
        "echo '--------------------------' >> /tmp/kernel_patch_audit.log && "
        "cat /tmp/kernel_patch_audit.log"
    )
    results.append("\n=== AUDIT LOG ===")
    results.append(stdout.read().decode().strip())

    client.close()
    return "\n".join(results)

def kernel_patch_rollback() -> str:
    """Emergency rollback to previous kernel. SAP must be stopped first."""
    cmd = '''
echo "=== KERNEL ROLLBACK ==="
if [ ! -f /tmp/kernel_backup_info.txt ]; then
    echo "ERROR: No backup info at /tmp/kernel_backup_info.txt"
    echo "Check /usr/sap/ for kernel_backup_* directories manually."
    exit 1
fi
BACKUP_ROOT=$(grep BACKUP_ROOT /tmp/kernel_backup_info.txt | cut -d= -f2)
echo "Restoring from: $BACKUP_ROOT"
green=$(su - a4hadm -c 'sapcontrol -nr 00 -function GetProcessList' 2>/dev/null | grep -c "GREEN" || true)
if [ "$green" -gt 0 ]; then
    echo "ERROR: SAP still running! Stop SAP before rollback."
    exit 1
fi
ls ${BACKUP_ROOT} | while read backup_dir; do
    orig_path=$(echo "/${backup_dir}" | tr '_' '/')
    if [ -d "$orig_path" ] && [ -d "${BACKUP_ROOT}/${backup_dir}" ]; then
        echo "Restoring: $orig_path"
        cp -fp "${BACKUP_ROOT}/${backup_dir}/"* "$orig_path/" 2>/dev/null || true
        chown -R a4hadm:sapsys "$orig_path/" 2>/dev/null || true
        ver=$(strings "$orig_path/disp+work" 2>/dev/null | grep SAPProductVersion || echo "unknown")
        echo "  Restored: $ver"
    fi
done
echo ""
echo "=== ROLLBACK COMPLETE ==="
echo "Start SAP to verify: sapcontrol -nr 00 -function Start"
'''
    return run_ssh_command(cmd)

def deploy_hana_vm(sid: str = "HXE", hostname: str = "hxehost",
                   machine_type: str = "e2-highmem-8", zone: str = "us-east4-b") -> str:
    """Deploy a new GCP VM for HANA Express installation.
    Infrastructure pillar tool — creates VM, validates zone capacity first.
    ONLY call after explicit human confirmation with cost estimate."""
    import subprocess
    sid_lower = sid.lower()
    vm_name = f"{sid_lower}-hana-demo"
    project = "sap-basis-copilot"
    script = f"""
set -e
PROJECT={project}
ZONE={zone}
VM_NAME={vm_name}
SSH_KEY=$(cat ~/.ssh/sap-basis-agent-key.pub)

echo "=== Pre-checks ==="
EXISTING=$(gcloud compute instances list --project=$PROJECT --filter="name=$VM_NAME" --format="get(name)" 2>/dev/null)
if [ -n "$EXISTING" ]; then
    echo "ERROR: VM $VM_NAME already exists in project $PROJECT"
    exit 1
fi

echo "=== Creating VM: $VM_NAME ==="
gcloud compute instances create $VM_NAME \
  --project=$PROJECT \
  --zone=$ZONE \
  --machine-type={machine_type} \
  --image-family=sles-15-sp5 \
  --image-project=suse-cloud \
  --boot-disk-size=200GB \
  --boot-disk-type=pd-ssd \
  --metadata="enable-osconfig=TRUE,ssh-keys=saps101226:$SSH_KEY" \
  --tags=hana-express,sap-demo \
  --scopes=cloud-platform \
  --labels="sid={sid_lower},type=hana-express,env=dev"

VM_IP=$(gcloud compute instances describe $VM_NAME \
  --zone=$ZONE --project=$PROJECT \
  --format="get(networkInterfaces[0].accessConfigs[0].natIP)" 2>/dev/null)

echo "VM_NAME=$VM_NAME"
echo "VM_IP=$VM_IP"
echo "SID={sid}"
echo "VM created successfully!"
"""
    result = subprocess.run(['bash', '-c', script], capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        return f"VM deployment failed:\n{result.stderr[:500]}"
    return result.stdout

def setup_hana_express(sid: str = "HXE", hostname: str = "hxehost", vm_ip: str = "") -> str:
    """Setup Docker and HANA prerequisites on the deployed VM.
    Run after deploy_hana_vm() — installs Docker, sets kernel params, creates data directories."""
    import subprocess
    sid_lower = sid.lower()
    vm_name = f"{sid_lower}-hana-demo"
    project = "sap-basis-copilot"
    zone = "us-east4-b"
    data_dir = f"/data/{sid_lower}"
    script = f"""
gcloud compute ssh {vm_name} \
  --zone={zone} --project={project} \
  --command="
sudo zypper install -y docker 2>/dev/null || true
sudo systemctl enable docker && sudo systemctl start docker
echo 'fs.file-max=20000000' | sudo tee -a /etc/sysctl.conf
echo 'vm.max_map_count=135217728' | sudo tee -a /etc/sysctl.conf
echo 'kernel.shmmax=1073741824' | sudo tee -a /etc/sysctl.conf
echo 'kernel.shmall=8388608' | sudo tee -a /etc/sysctl.conf
sudo sysctl -p 2>/dev/null || true
sudo mkdir -p {data_dir} && sudo chmod 777 {data_dir}
echo '{{"master_password": "HanaExpr2026#"}}' | sudo tee {data_dir}/{sid_lower}passwd.json
sudo chmod 600 {data_dir}/{sid_lower}passwd.json
sudo chown 12000:79 {data_dir}/{sid_lower}passwd.json
echo 'Setup complete!'
"
"""
    result = subprocess.run(['bash', '-c', script], capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        return f"Setup failed:\n{result.stderr[:500]}"
    return result.stdout

def run_hana_express(sid: str = "HXE", hostname: str = "hxehost") -> str:
    """Pull and start HANA Express Docker container on the VM.
    Run after setup_hana_express() — pulls image and starts HANA DB.
    HANA initialization takes 5-10 minutes."""
    import subprocess
    sid_lower = sid.lower()
    vm_name = f"{sid_lower}-hana-demo"
    project = "sap-basis-copilot"
    zone = "us-east4-b"
    data_dir = f"/data/{sid_lower}"
    script = f"""
gcloud compute ssh {vm_name} \
  --zone={zone} --project={project} \
  --command="
sudo docker rm {sid_lower} 2>/dev/null || true
sudo docker pull saplabs/hanaexpress:latest
sudo docker run \
  --stop-timeout 3600 -d \
  --name {sid_lower} -h {hostname} \
  -p 39013:39013 -p 39017:39017 \
  -p 39041-39045:39041-39045 \
  -p 1128-1129:1128-1129 \
  -p 59013-59014:59013-59014 \
  -v {data_dir}:/hana/mounts \
  --ulimit nofile=1048576:1048576 \
  --sysctl kernel.shmmax=1073741824 \
  --sysctl 'net.ipv4.ip_local_port_range=40000 60999' \
  --sysctl kernel.shmall=8388608 \
  saplabs/hanaexpress:latest \
  --passwords-url file:///hana/mounts/{sid_lower}passwd.json \
  --agree-to-sap-license --dont-check-system
echo 'HANA container started in background!'
echo 'Wait 5-8 minutes then verify with verify_hana_running()'
"
"""
    result = subprocess.run(['bash', '-c', script], capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        return f"HANA start failed:\n{result.stderr[:500]}"
    return result.stdout

def verify_hana_running(sid: str = "HXE") -> str:
    """Verify HANA Express running via direct SSH to 34.48.207.206"""
    import paramiko, os
    try:
        sid_lower = sid.lower()
        key_path = _get_ssh_key_path()
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect("34.48.207.206", username="saps101226", key_filename=key_path)
        cmd = (
            "echo === Container Status === && "
            "sudo docker ps --filter name=hxe && "
            "HDBSQL=$(sudo docker exec hxe find /hana/shared -name hdbsql 2>/dev/null | head -1) && "
            "echo === Version === && "
            "sudo docker exec hxe $HDBSQL -i 90 -d HXE -u SYSTEM -p HanaExpr2026# "
            "'SELECT VERSION FROM SYS.M_DATABASE' && "
            "echo === SQL Test === && "
            "sudo docker exec hxe $HDBSQL -i 90 -d HXE -u SYSTEM -p HanaExpr2026# "
            "'SELECT * FROM DUMMY'"
        )
        stdin, stdout, stderr = client.exec_command(cmd)
        result = stdout.read().decode()
        client.close()
        return "[HXE] HANA Express Verification:\n" + result
    except Exception as e:
        return "[HXE] ERROR: " + str(e)

def upgrade_hana_express(current_version="2.00.082", target_tag="latest", vm_name="hana-express-demo", zone="us-east4-b"):
    """Upgrade HANA Express via direct SSH + polling."""
    import paramiko, os, time, datetime
    try:
        key = _get_ssh_key_path()
        c = paramiko.SSHClient()
        c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        c.connect("34.48.207.206", username="saps101226", key_filename=key)
        out = []
        def run(cmd):
            _, o, e = c.exec_command(cmd)
            return o.read().decode() + e.read().decode()
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        out.append("=== STEP 1: BACKUP ===")
        out.append(run("sudo cp -rp /data/hxe /data/hxe_backup_" + ts + " && echo Backup done!"))
        out.append("=== STEP 2: STOP HANA ===")
        out.append(run("sudo docker stop hxe && sudo docker rm hxe && echo Stopped!"))
        out.append("=== STEP 3: PULL ===")
        out.append(run("sudo docker pull saplabs/hanaexpress:" + target_tag + " && echo Pulled!"))
        out.append("=== STEP 4: START ===")
        rcmd = ("sudo docker run --stop-timeout 3600 -d --name hxe -h hxehost "
                "-p 39013:39013 -p 39017:39017 -p 39041-39045:39041-39045 "
                "-p 1128-1129:1128-1129 -p 59013-59014:59013-59014 "
                "-v /data/hxe:/hana/mounts --ulimit nofile=1048576:1048576 "
                "--sysctl kernel.shmmax=1073741824 "
                "--sysctl 'net.ipv4.ip_local_port_range=40000 60999' "
                "--sysctl kernel.shmall=8388608 "
                "saplabs/hanaexpress:" + target_tag + " "
                "--passwords-url file:///hana/mounts/hxepasswd.json "
                "--agree-to-sap-license --dont-check-system")
        out.append(run(rcmd))
        out.append("=== STEP 5: POLLING ===")
        for i in range(20):
            time.sleep(30)
            logs = run("sudo docker logs hxe 2>&1 | tail -3")
            out.append("[" + str((i+1)*30) + "s] " + logs.strip())
            if "Startup finished" in logs:
                out.append("HANA ready!")
                break
        out.append("=== STEP 6: POST-CHECKS ===")
        h = run("sudo docker exec hxe find /hana/shared -name hdbsql 2>/dev/null | head -1").strip()
        out.append(run("sudo docker exec hxe " + h + " -i 90 -d HXE -u SYSTEM -p HanaExpr2026# 'SELECT VERSION FROM SYS.M_DATABASE'"))
        out.append(run("sudo docker exec hxe " + h + " -i 90 -d HXE -u SYSTEM -p HanaExpr2026# 'SELECT * FROM DUMMY'"))
        out.append("=== UPGRADE COMPLETE: " + current_version + " to " + target_tag + " ===")
        c.close()
        return "\n".join(out)
    except Exception as e:
        return "Upgrade failed: " + str(e)



def check_critical_auth_changes(
    system_id: str = "A4H",
    days: int = 7
) -> str:
    """Critical Authorization Change Monitor (UC-S2).

    Detects privilege escalation and suspicious authorization
    changes across four views:
    1. SAP_ALL / SAP_NEW profile holders (UST04)
    2. Recent role assignments (AGR_USERS)
    3. Auth-related change documents with exact date+time+actor
       for after-hours detection (CDHDR: IDENTITY/PFCG/SUSR_PROF)
    4. Account anomalies: new users, lock flags (USR02)

    READ-ONLY - OPERATIONS pillar. Does not modify anything.

    system_id: SAP System ID (e.g. A4H, BDD, BDP). Default: A4H
    days: lookback window for changes. Default: 7
    """
    conn = SAPConnection(system_id)
    blocked = conn.is_allowed("operations")
    if blocked:
        return blocked

    client = conn.get_ssh_client()
    userstore = conn.hana_userstore   # "DEFAULT" on A4H
    schema = conn.hana_schema         # "SAPA4H" on A4H

    # Date columns are NVARCHAR(8) YYYYMMDD on this release
    cutoff = (
        f"TO_VARCHAR(ADD_DAYS(CURRENT_DATE, -{days}), 'YYYYMMDD')"
    )

    queries = [
        (
            "CRITICAL PROFILE HOLDERS (UST04)",
            f"SELECT MANDT, BNAME, PROFILE FROM {schema}.UST04 "
            f"WHERE PROFILE IN ('SAP_ALL','SAP_NEW') "
            f"ORDER BY BNAME"
        ),
        (
            f"ROLE ASSIGNMENTS LAST {days} DAYS (AGR_USERS)",
            f"SELECT TOP 100 UNAME, AGR_NAME, FROM_DAT, TO_DAT "
            f"FROM {schema}.AGR_USERS "
            f"WHERE FROM_DAT >= {cutoff} "
            f"ORDER BY FROM_DAT DESC"
        ),
        (
            f"AUTH CHANGE DOCUMENTS LAST {days} DAYS (CDHDR)",
            f"SELECT TOP 200 OBJECTCLAS, OBJECTID, USERNAME, "
            f"UDATE, UTIME, TCODE "
            f"FROM {schema}.CDHDR "
            f"WHERE OBJECTCLAS IN ('IDENTITY','PFCG','SUSR_PROF') "
            f"AND UDATE >= {cutoff} "
            f"ORDER BY UDATE DESC, UTIME DESC"
        ),
        (
            "ACCOUNT ANOMALIES (USR02)",
            f"SELECT BNAME, USTYP, UFLAG, ERDAT, ANAME, TRDAT "
            f"FROM {schema}.USR02 "
            f"WHERE ERDAT >= {cutoff} OR UFLAG <> 0 "
            f"ORDER BY ERDAT DESC"
        ),
    ]

    sections = []
    for label, sql in queries:
        # Same wrapper as SM20: SSH as root, su to a4hadm,
        # run hdbsql with the DEFAULT userstore key
        cmd = (
            'su - a4hadm -c '
            '"hdbsql -U ' + userstore + ' -A -j \\"' + sql + '\\""'
        )
        stdin, stdout, stderr = client.exec_command(cmd, timeout=60)
        result = stdout.read().decode()
        err = stderr.read().decode()

        low = (result + err).lower()
        if "invalid table name" in low or "invalid schema name" in low:
            sections.append(
                f"=== {label} ===\n"
                f"Table/schema not found on this release: "
                f"{err.strip()[:200]}"
            )
        elif "0 rows selected" in result:
            sections.append(f"=== {label} ===\n0 rows.")
        elif not result.strip():
            sections.append(
                f"=== {label} ===\nNo output. "
                f"Error: {err.strip()[:200]}"
            )
        else:
            sections.append(f"=== {label} ===\n{result.strip()}")

    client.close()
    return (
        f"[{system_id}] UC-S2 Critical Auth Change Monitor "
        f"(lookback {days} days)\n\n" + "\n\n".join(sections)
    )


import re


def check_st22_dump_triage(
    system_id: str = "A4H",
    days: int = 1
) -> str:
    """ST22 ABAP Dump Triage (UC-D1).

    Reads dump headers from SNAP, decodes error type + program,
    groups and counts them for triage. READ-ONLY, OPERATIONS pillar.

    system_id: SAP System ID. Default A4H
    days: lookback window. Default 1 (24 hours)
    """
    conn = SAPConnection(system_id)
    blocked = conn.is_allowed("operations")
    if blocked:
        return blocked

    client = conn.get_ssh_client()
    userstore = conn.hana_userstore
    schema = conn.hana_schema
    cutoff = f"TO_VARCHAR(ADD_DAYS(CURRENT_DATE, -{days}), 'YYYYMMDD')"

    sql = (
        f"SELECT TOP 200 DATUM, UZEIT, AHOST, UNAME, "
        f"FLIST || FLIST02 AS HDR "
        f"FROM {schema}.SNAP "
        f"WHERE FLIST LIKE 'FC%' AND DATUM >= {cutoff} "
        f"ORDER BY DATUM DESC, UZEIT DESC"
    )
    # Write SQL to a temp file on the VM, run hdbsql -I, avoids
    # all nested-quote issues through paramiko + su
    remote_sql = "/tmp/uc_d1_dump.sql"
    sftp = client.open_sftp()
    with sftp.open(remote_sql, "w") as f:
        f.write(sql + ";\n")
    sftp.close()
    cmd = ("su - a4hadm -c 'hdbsql -U " + userstore
           + " -A -j -I " + remote_sql + "'")
    stdin, stdout, stderr = client.exec_command(cmd, timeout=90)
    result = stdout.read().decode()
    err = stderr.read().decode()
    client.close()

    if result.strip().startswith("*"):
        return (f"[{system_id}] ST22 query failed: "
                + result.strip()[:300])
    if "0 rows selected" in result:
        return (f"[{system_id}] ST22 Dump Triage: 0 dumps in the "
                f"last {days} day(s). System clean.")
    if not result.strip():
        return f"[{system_id}] ST22 query error: {err.strip()[:300]}"

    def field(hdr, tag):
        m = re.search(tag + r"(\d{3})", hdr)
        if not m:
            return ""
        ln = int(m.group(1))
        start = m.end()
        return hdr[start:start + ln].strip()

    groups = {}
    for line in result.splitlines():
        if not line.startswith("|") or line.startswith("| ---"):
            continue
        parts = [c.strip() for c in line.strip("|").split("|")]
        if len(parts) < 5 or parts[0] == "DATUM":
            continue
        datum, uzeit, ahost, uname, hdr = parts[:5]
        errid = field(hdr, "FC")
        prog = field(hdr, "AP")
        key = (errid, prog)
        g = groups.setdefault(key, {"cnt": 0, "users": set(),
                                    "first": datum + " " + uzeit,
                                    "last": datum + " " + uzeit})
        g["cnt"] += 1
        g["users"].add(uname or "?")
        g["last"] = max(g["last"], datum + " " + uzeit)
        g["first"] = min(g["first"], datum + " " + uzeit)

    lines = [f"[{system_id}] ST22 Dump Triage (last {days} day(s)) "
             f"- {sum(g['cnt'] for g in groups.values())} dumps, "
             f"{len(groups)} distinct groups:\n"]
    for (errid, prog), g in sorted(groups.items(),
                                   key=lambda x: -x[1]["cnt"]):
        lines.append(
            f"ERROR: {errid} | PROGRAM: {prog or 'n/a'} | "
            f"COUNT: {g['cnt']} | USERS: {','.join(sorted(g['users']))} | "
            f"FIRST: {g['first']} | LAST: {g['last']}")
    return "\n".join(lines)
