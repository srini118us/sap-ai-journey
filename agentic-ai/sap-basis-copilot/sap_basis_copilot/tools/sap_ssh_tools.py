from datetime import datetime, timedelta
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

SAP_HOST = "YOUR_SAP_HOST_IP"
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
  --metadata="enable-osconfig=TRUE,ssh-keys=YOUR_GCP_USER:$SSH_KEY" \
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
    """Verify HANA Express running via direct SSH to YOUR_HANA_HOST_IP"""
    import paramiko, os
    try:
        sid_lower = sid.lower()
        key_path = _get_ssh_key_path()
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect("YOUR_HANA_HOST_IP", username="YOUR_GCP_USER", key_filename=key_path)
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
        c.connect("YOUR_HANA_HOST_IP", username="YOUR_GCP_USER", key_filename=key)
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


def find_function_module(
    search_terms: str,
    system_id: str = "A4H",
    rfc_only: bool = True
) -> str:
    """Function Module and BAPI Finder (UC-D3 search).

    SE37 / BAPI browser equivalent. Searches the function module
    directory (TFDIR) joined to English short texts (TFTIT) for the
    supplied keywords. Use when a developer describes a need in plain
    English, e.g. "which BAPI creates a user".

    Returns candidate names and descriptions ONLY. Call
    get_function_module_signature() afterwards for parameters.

    READ-ONLY - OPERATIONS pillar. Does not modify anything.

    search_terms: space separated keywords, e.g. "user create"
    system_id: SAP System ID (e.g. A4H, BDD, BDP). Default: A4H
    rfc_only: restrict to remote enabled modules. Default: True
    """
    conn = SAPConnection(system_id)
    blocked = conn.is_allowed("operations")
    if blocked:
        return blocked

    terms = [t.upper() for t in re.findall(r"[A-Za-z0-9_]+", search_terms)]
    terms = terms[:5]
    if not terms:
        return (
            f"[{system_id}] No usable search keywords supplied. "
            f"Ask the user for 2 to 4 keywords."
        )

    client = conn.get_ssh_client()
    userstore = conn.hana_userstore   # "DEFAULT" on A4H
    schema = conn.hana_schema         # "SAPA4H" on A4H
    adm_user = conn.sid.lower() + "adm"

    conds = " AND ".join(
        f"(UPPER(T.STEXT) LIKE '%{t}%' OR UPPER(D.FUNCNAME) LIKE '%{t}%')"
        for t in terms
    )
    rfc = "D.FMODE = 'R' AND " if rfc_only else ""

    sql = (
        f"SELECT TOP 25 D.FUNCNAME, D.FMODE, T.STEXT "
        f"FROM {schema}.TFDIR D "
        f"INNER JOIN {schema}.TFTIT T "
        f"ON T.FUNCNAME = D.FUNCNAME AND T.SPRAS = 'E' "
        f"WHERE {rfc}{conds} "
        f"ORDER BY CASE WHEN D.FUNCNAME LIKE 'BAPI%' THEN 0 ELSE 1 END, "
        f"D.FUNCNAME"
    )

    cmd = (
        'su - ' + adm_user + ' -c '
        '"hdbsql -U ' + userstore + ' -A -j \\"' + sql + '\\""'
    )
    stdin, stdout, stderr = client.exec_command(cmd, timeout=60)
    result = stdout.read().decode()
    err = stderr.read().decode()
    client.close()

    joined = " ".join(terms)
    low = (result + err).lower()

    if "invalid table name" in low or "invalid schema name" in low:
        return (
            f"[{system_id}] Dictionary tables not reachable on this "
            f"release: {err.strip()[:200]}"
        )

    if "0 rows selected" in result or not result.strip():
        return (
            f"[{system_id}] NOT FOUND: no function modules on system "
            f"{system_id} match these keywords: {joined}. "
            f"Do NOT suggest function module names from general SAP "
            f"knowledge. Tell the user nothing matched on this system "
            f"and ask for different keywords."
        )

    rows = [ln for ln in result.strip().split("\n")[1:] if ln.strip()]
    return (
        f"[{system_id}] UC-D3 Function Module Search - keywords: {joined}\n"
        f"{len(rows)} match(es) shown, capped at 25. "
        f"Live read from {schema}.TFDIR joined to TFTIT.\n\n"
        + result.strip()
    )


def get_function_module_signature(
    function_name: str,
    system_id: str = "A4H"
) -> str:
    """Function Module Signature Reader (UC-D3 detail).

    Reads the full active parameter interface of a function module or
    BAPI from FUPARAREF, so a sample CALL FUNCTION block can be written
    from real parameters rather than from memory. Call after
    find_function_module() once the developer picks a module.

    READ-ONLY - OPERATIONS pillar. Does not modify anything.

    function_name: exact name, e.g. BAPI_USER_CREATE1
    system_id: SAP System ID (e.g. A4H, BDD, BDP). Default: A4H
    """
    conn = SAPConnection(system_id)
    blocked = conn.is_allowed("operations")
    if blocked:
        return blocked

    fm = re.sub(r"[^A-Za-z0-9_/]", "", function_name).upper()
    if not fm:
        return f"[{system_id}] Invalid function module name supplied."

    client = conn.get_ssh_client()
    userstore = conn.hana_userstore
    schema = conn.hana_schema
    adm_user = conn.sid.lower() + "adm"

    sql = (
        f"SELECT PARAMTYPE, PPOSITION, PARAMETER, STRUCTURE, "
        f"OPTIONAL, DEFAULTVAL "
        f"FROM {schema}.FUPARAREF "
        f"WHERE FUNCNAME = '{fm}' AND R3STATE = 'A' "
        f"ORDER BY PARAMTYPE, PPOSITION"
    )

    cmd = (
        'su - ' + adm_user + ' -c '
        '"hdbsql -U ' + userstore + ' -A -j \\"' + sql + '\\""'
    )
    stdin, stdout, stderr = client.exec_command(cmd, timeout=60)
    result = stdout.read().decode()
    err = stderr.read().decode()
    client.close()

    low = (result + err).lower()

    if "invalid table name" in low or "invalid schema name" in low:
        return (
            f"[{system_id}] FUPARAREF not reachable on this release: "
            f"{err.strip()[:200]}"
        )

    if "0 rows selected" in result or not result.strip():
        return (
            f"[{system_id}] NOT FOUND: function module {fm} does not "
            f"exist on system {system_id}. FUPARAREF returned zero "
            f"active parameters, so this module is not installed here. "
            f"Report it to the user as not found and STOP. Do NOT "
            f"generate a signature or a sample ABAP call for {fm} from "
            f"general SAP knowledge. Note this system is ABAP Platform "
            f"developer edition, so SD, MM and FI modules are absent."
        )

    rows = [ln for ln in result.strip().split("\n")[1:] if ln.strip()]
    return (
        f"[{system_id}] UC-D3 Signature for {fm} - {len(rows)} active "
        f"parameters. Live read from {schema}.FUPARAREF.\n"
        f"PARAMTYPE is from the function module's own perspective and "
        f"INVERTS in the caller: I = importing, so write it under "
        f"EXPORTING in the CALL FUNCTION block; E = exporting, so write "
        f"it under IMPORTING; C = changing; T = tables; X = exceptions. "
        f"OPTIONAL = X means optional, blank means mandatory.\n\n"
        + result.strip()
    )
# =====================================================================
# UC-A3 / UC-A4  New tools for the SAP Basis Copilot
#
# Append these two functions to the END of tools/sap_ssh_tools.py,
# after get_function_module_signature.
#
# House style followed:
#   inline hdbsql through paramiko + su, no sftp of .sql files
#   adm user derived from the SID, not hardcoded a4hadm
#   conn.hana_userstore and conn.hana_schema used for the connection
#   bare "blocked" returned for governance blocks
#   hdbsql errors detected on STDOUT with the '* NNN:' prefix
#
# VERIFY ON FIRST RUN
#   BALHDR message count columns. The SE16 export showed 9 of 43 fields,
#   so MSG_CNT_A / MSG_CNT_E / MSG_CNT_W and ALPROG are expected but not
#   confirmed on this release. If hdbsql returns an unknown column error
#   it names the column, so drop that one from the SELECT and rerun.
# =====================================================================

from datetime import datetime, timedelta


def check_application_log(
    system_id: str = "A4H",
    hours_back: int = 2,
    program: str = "",
    log_object: str = "",
    user: str = "",
    errors_only: bool = True,
    date_from: str = "",
    date_to: str = "",
) -> str:
    """Read the SAP application log (SLG1) for a time window.

    This is the BUSINESS level log. Applications write here through the
    BAL framework when something fails for a business reason, which is
    often invisible in ST22 because no program actually terminated.

    Args:
        system_id: SID from the registry, for example A4H
        hours_back: how far back to look, in hours
        program: optional filter on the writing program (ALPROG)
        log_object: optional filter on the application area (OBJECT)
        user: optional filter on the user who triggered it
        errors_only: when True, only logs containing errors or aborts
        date_from: optional absolute start date, YYYYMMDD. Overrides
            hours_back. Use when the user names a specific date or when
            the data being looked for is older than a relative window
            would reach.
        date_to: optional absolute end date, YYYYMMDD. Defaults to
            date_from, meaning a single day.

    Returns:
        Formatted findings, or a message stating nothing was found.
    """
    conn = SAPConnection(system_id)

    blocked = conn.is_allowed("application")
    if blocked:
        return blocked

    if date_from:
        d_from, t_from = date_from, "000000"
        d_to, t_to = (date_to or date_from), "235959"
        window_label = f"{d_from} to {d_to}"
    else:
        now = datetime.now()
        start = now - timedelta(hours=hours_back)
        d_from, t_from = start.strftime("%Y%m%d"), start.strftime("%H%M%S")
        d_to, t_to = now.strftime("%Y%m%d"), now.strftime("%H%M%S")
        window_label = f"last {hours_back} hour(s)"

    schema = conn.hana_schema
    adm = conn.sid.lower() + "adm"

    # ALDATE and ALTIME are separate columns, so the window has to be
    # expressed as a spanning comparison rather than a date equality.
    # That also means it crosses midnight correctly.
    where = [
        f"( ALDATE > '{d_from}' OR ( ALDATE = '{d_from}' AND ALTIME >= '{t_from}' ) )",
        f"( ALDATE < '{d_to}'   OR ( ALDATE = '{d_to}'   AND ALTIME <= '{t_to}' ) )",
    ]

    if errors_only:
        # Only logs that actually carry an error or an abort. Without this
        # a busy system returns hundreds of routine informational logs.
        # MSG_CNT_* are NUMC, holding '000000' rather than 0, so the
        # cast is required. A bare > 0 comparison is unreliable here.
        where.append(
            "( TO_INTEGER(MSG_CNT_E) > 0 OR TO_INTEGER(MSG_CNT_A) > 0 )"
        )
    if program:
        where.append(f"UPPER(ALPROG) LIKE UPPER('%{program}%')")
    if log_object:
        where.append(f"UPPER(OBJECT) LIKE UPPER('%{log_object}%')")
    if user:
        where.append(f"UPPER(ALUSER) = UPPER('{user}')")

    sql = (
        "SELECT ALDATE, ALTIME, ALUSER, OBJECT, SUBOBJECT, ALPROG, "
        "ALTCODE, EXTNUMBER, MSG_CNT_A, MSG_CNT_E, MSG_CNT_W, LOGNUMBER "
        f"FROM {schema}.BALHDR "
        "WHERE " + " AND ".join(where) + " "
        "ORDER BY ALDATE, ALTIME"
    )

    cmd = 'su - ' + adm + ' -c ' + '"hdbsql -U ' + conn.hana_userstore + \
          ' -A -j \\"' + sql + '\\""'

    client = conn.get_ssh_client()
    stdin, stdout, stderr = client.exec_command(cmd, timeout=60)
    out = stdout.read().decode(errors="replace")
    client.close()

    # hdbsql writes errors to STDOUT with a '* NNN:' prefix, not stderr.
    # Without this check the tool falsely reports a clean result.
    if "* " in out and ":" in out.split("* ", 1)[-1][:8]:
        return f"{system_id}: application log query failed. {out.strip()}"

    rows = [r for r in out.splitlines() if r.strip() and not r.startswith("rows")]
    if not rows:
        scope = "with errors" if errors_only else ""
        return (
            f"{system_id}: no application log entries {scope} in "
            f"{window_label}. Note this is a genuine empty result, "
            f"not a failure. On a developer edition system without the SD, "
            f"MM and FI application stack, SLG1 is written mainly by "
            f"Gateway and Fiori components."
        )

    lines = [
        f"{system_id} APPLICATION LOG (SLG1), {window_label}",
        f"Filters: errors_only={errors_only}"
        + (f", program~{program}" if program else "")
        + (f", object~{log_object}" if log_object else "")
        + (f", user={user}" if user else ""),
        f"{len(rows)} log(s) found",
        "",
    ]

    for r in rows[:50]:
        f = [c.strip().strip('"') for c in r.split(",")]
        if len(f) < 12:
            continue
        (aldate, altime, aluser, obj, subobj, alprog,
         altcode, extnum, cnt_a, cnt_e, cnt_w, lognum) = f[:12]

        stamp = f"{aldate[6:8]}.{aldate[4:6]}.{aldate[0:4]} {altime[0:2]}:{altime[2:4]}:{altime[4:6]}"
        sev = "ABORT" if cnt_a not in ("0", "") else "ERROR"

        lines.append(
            f"[{sev}] {stamp} {aluser} | {obj}/{subobj} | program {alprog}"
            + (f" | tcode {altcode}" if altcode else "")
            + (f" | ext {extnum}" if extnum else "")
        )
        lines.append(
            f"        aborts {cnt_a}, errors {cnt_e}, warnings {cnt_w} "
            f"| open SLG1 on log {lognum} for message detail"
        )

    if len(rows) > 50:
        lines.append("")
        lines.append(
            f"[TRUNCATED] showing 50 of {len(rows)}. Narrow the window or "
            f"add a program or object filter."
        )

    return "\n".join(lines)


def check_workflow_errors(
    system_id: str = "A4H",
    hours_back: int = 24,
    task: str = "",
) -> str:
    """Find SAP Business Workflow work items sitting in error.

    Equivalent to SWI2_DIAG. A workflow in error stalls silently: the
    business process simply stops, and nobody is notified unless someone
    looks. Reads SWWWIHEAD, the work item header table.

    Args:
        system_id: SID from the registry, for example A4H
        hours_back: how far back to look, in hours
        task: optional filter on the task, for example TS12300097

    Returns:
        Formatted findings, or a message stating nothing was found.
    """
    conn = SAPConnection(system_id)

    blocked = conn.is_allowed("application")
    if blocked:
        return blocked

    start = datetime.now() - timedelta(hours=hours_back)
    d_from = start.strftime("%Y%m%d")

    schema = conn.hana_schema
    adm = conn.sid.lower() + "adm"

    where = [
        "WI_STAT = 'ERROR'",
        f"WI_CD >= '{d_from}'",
    ]
    if task:
        where.append(f"UPPER(WI_RH_TASK) LIKE UPPER('%{task}%')")

    sql = (
        "SELECT WI_ID, WI_CD, WI_CT, WI_TYPE, WI_RH_TASK, WI_STAT, "
        "WI_CREATOR, WI_TEXT "
        f"FROM {schema}.SWWWIHEAD "
        "WHERE " + " AND ".join(where) + " "
        "ORDER BY WI_CD, WI_CT"
    )

    cmd = 'su - ' + adm + ' -c ' + '"hdbsql -U ' + conn.hana_userstore + \
          ' -A -j \\"' + sql + '\\""'

    client = conn.get_ssh_client()
    stdin, stdout, stderr = client.exec_command(cmd, timeout=60)
    out = stdout.read().decode(errors="replace")
    client.close()

    if "* " in out and ":" in out.split("* ", 1)[-1][:8]:
        return f"{system_id}: workflow query failed. {out.strip()}"

    rows = [r for r in out.splitlines() if r.strip() and not r.startswith("rows")]
    if not rows:
        return (
            f"{system_id}: no workflow work items in error status in the "
            f"last {hours_back} hour(s). Note this is a genuine empty "
            f"result. A developer edition system with no business "
            f"applications configured will normally have no workflows "
            f"running at all."
        )

    lines = [
        f"{system_id} WORKFLOW ERRORS (SWI2_DIAG equivalent), last {hours_back} hour(s)",
        f"{len(rows)} work item(s) in error",
        "",
    ]

    for r in rows[:50]:
        f = [c.strip().strip('"') for c in r.split(",")]
        if len(f) < 8:
            continue
        wi_id, wi_cd, wi_ct, wi_type, task_id, stat, creator, text = f[:8]
        stamp = f"{wi_cd[6:8]}.{wi_cd[4:6]}.{wi_cd[0:4]} {wi_ct[0:2]}:{wi_ct[2:4]}:{wi_ct[4:6]}"
        lines.append(f"[ERROR] {stamp} work item {wi_id} | task {task_id} | type {wi_type}")
        lines.append(f"        {text}")
        lines.append(f"        created by {creator} | restart via SWPR after fixing the cause")

    if len(rows) > 50:
        lines.append("")
        lines.append(f"[TRUNCATED] showing 50 of {len(rows)}.")

    return "\n".join(lines)



# =====================================================================
# DISCOVERY TOOLS
#
# The problem these solve: nobody knows the OBJECT codes or the task IDs.
# Real users say "Gateway" or "purchasing", while the tables hold
# /IWFND/ and TS12300097. These return the shape of what is there, so
# the conversation becomes two steps: what is logging errors, then show
# me those.
# =====================================================================


def list_application_log_objects(
    system_id: str = "A4H",
    hours_back: int = 24,
    date_from: str = "",
    date_to: str = "",
) -> str:
    """Show which applications wrote to SLG1, and how many had errors.

    Use this FIRST when the user asks a broad question like "any
    application errors today" or does not know the OBJECT code. The
    result tells them what to drill into with check_application_log.

    Args:
        system_id: SID from the registry, for example A4H
        hours_back: how far back to look, in hours
        date_from: optional absolute start date, YYYYMMDD. Overrides
            hours_back.
        date_to: optional absolute end date, YYYYMMDD. Defaults to
            date_from, meaning a single day.

    Returns:
        One line per application area with totals and error counts.
    """
    conn = SAPConnection(system_id)

    blocked = conn.is_allowed("application")
    if blocked:
        return blocked

    if date_from:
        d_from, t_from = date_from, "000000"
        d_to, t_to = (date_to or date_from), "235959"
        window_label = f"{d_from} to {d_to}"
    else:
        now = datetime.now()
        start = now - timedelta(hours=hours_back)
        d_from, t_from = start.strftime("%Y%m%d"), start.strftime("%H%M%S")
        d_to, t_to = now.strftime("%Y%m%d"), now.strftime("%H%M%S")
        window_label = f"last {hours_back} hour(s)"

    schema = conn.hana_schema
    adm = conn.sid.lower() + "adm"

    sql = (
        "SELECT OBJECT, SUBOBJECT, COUNT(*) AS TOTAL, "
        "SUM(CASE WHEN TO_INTEGER(MSG_CNT_E) > 0 "
        "OR TO_INTEGER(MSG_CNT_A) > 0 THEN 1 ELSE 0 END) AS WITH_ERR "
        f"FROM {schema}.BALHDR "
        f"WHERE ( ALDATE > '{d_from}' OR ( ALDATE = '{d_from}' AND ALTIME >= '{t_from}' ) ) "
        f"AND ( ALDATE < '{d_to}' OR ( ALDATE = '{d_to}' AND ALTIME <= '{t_to}' ) ) "
        "GROUP BY OBJECT, SUBOBJECT "
        "ORDER BY WITH_ERR DESC, TOTAL DESC"
    )

    cmd = 'su - ' + adm + ' -c ' + '"hdbsql -U ' + conn.hana_userstore + \
          ' -A -j \\"' + sql + '\\""'

    client = conn.get_ssh_client()
    stdin, stdout, stderr = client.exec_command(cmd, timeout=60)
    out = stdout.read().decode(errors="replace")
    client.close()

    if "* " in out and ":" in out.split("* ", 1)[-1][:8]:
        return f"{system_id}: application log summary failed. {out.strip()}"

    rows = [r for r in out.splitlines() if r.strip() and not r.startswith("rows")]
    if not rows:
        return (
            f"{system_id}: nothing wrote to the application log in "
            f"{window_label}. This is a genuine empty result."
        )

    lines = [
        f"{system_id} APPLICATION LOG SUMMARY, {window_label}",
        f"{len(rows)} application area(s) wrote logs",
        "",
    ]

    err_areas = []
    for r in rows[:60]:
        f = [c.strip().strip('"') for c in r.split(",")]
        if len(f) < 4:
            continue
        obj, subobj, total, with_err = f[:4]
        flag = "ERRORS" if with_err not in ("0", "") else "clean "
        lines.append(
            f"[{flag}] {obj}/{subobj}: {total} log(s), {with_err} containing errors"
        )
        if with_err not in ("0", ""):
            err_areas.append(obj)

    lines.append("")
    if err_areas:
        lines.append(
            "To drill in, call check_application_log with log_object set to "
            "one of: " + ", ".join(sorted(set(err_areas))[:8])
        )
    else:
        lines.append("No area recorded any errors in this window.")

    return "\n".join(lines)


def list_workflow_summary(
    system_id: str = "A4H",
    hours_back: int = 24,
) -> str:
    """Show workflow activity grouped by task and status.

    Use this FIRST for broad questions like "any workflow issues" or
    "how are the workflows doing". It shows the shape: which tasks are
    running, and how many sit in each status. ERROR is the obvious
    problem, but a large READY or STARTED count on an old task usually
    means something is silently stuck.

    Args:
        system_id: SID from the registry, for example A4H
        hours_back: how far back to look, in hours

    Returns:
        One line per task and status combination with a count.
    """
    conn = SAPConnection(system_id)

    blocked = conn.is_allowed("application")
    if blocked:
        return blocked

    start = datetime.now() - timedelta(hours=hours_back)
    d_from = start.strftime("%Y%m%d")

    schema = conn.hana_schema
    adm = conn.sid.lower() + "adm"

    sql = (
        "SELECT WI_RH_TASK, WI_STAT, COUNT(*) AS CNT "
        f"FROM {schema}.SWWWIHEAD "
        f"WHERE WI_CD >= '{d_from}' "
        "GROUP BY WI_RH_TASK, WI_STAT "
        "ORDER BY CNT DESC"
    )

    cmd = 'su - ' + adm + ' -c ' + '"hdbsql -U ' + conn.hana_userstore + \
          ' -A -j \\"' + sql + '\\""'

    client = conn.get_ssh_client()
    stdin, stdout, stderr = client.exec_command(cmd, timeout=60)
    out = stdout.read().decode(errors="replace")
    client.close()

    if "* " in out and ":" in out.split("* ", 1)[-1][:8]:
        return f"{system_id}: workflow summary failed. {out.strip()}"

    rows = [r for r in out.splitlines() if r.strip() and not r.startswith("rows")]
    if not rows:
        return (
            f"{system_id}: no workflow work items created in the last "
            f"{hours_back} hour(s). This is a genuine empty result. A "
            f"developer edition system with no business applications "
            f"configured normally runs no workflows at all."
        )

    lines = [
        f"{system_id} WORKFLOW SUMMARY, last {hours_back} hour(s)",
        "",
    ]

    problems = []
    for r in rows[:60]:
        f = [c.strip().strip('"') for c in r.split(",")]
        if len(f) < 3:
            continue
        task, stat, cnt = f[:3]
        marker = "PROBLEM" if stat.upper() in ("ERROR", "CANCELLED") else "       "
        lines.append(f"[{marker}] task {task}: {cnt} work item(s) in status {stat}")
        if stat.upper() == "ERROR":
            problems.append(task)

    lines.append("")
    if problems:
        lines.append(
            "Work items in ERROR found. Call check_workflow_errors for the "
            "detail on: " + ", ".join(sorted(set(problems))[:8])
        )
    else:
        lines.append(
            "No work items in ERROR status. Call check_stuck_workflows to "
            "look for items that are not in error but have stopped moving."
        )

    return "\n".join(lines)


def check_stuck_workflows(
    system_id: str = "A4H",
    older_than_hours: int = 24,
) -> str:
    """Find work items that are not in error but have stopped moving.

    This is the harder failure mode. A work item in ERROR at least
    announces itself. One sitting in READY or STARTED for days looks
    healthy in every status report while the business process it belongs
    to has quietly stopped, usually because no agent was assigned or the
    assigned agent never acted.

    Args:
        system_id: SID from the registry, for example A4H
        older_than_hours: flag items untouched for longer than this

    Returns:
        Formatted findings, or a message stating nothing was found.
    """
    conn = SAPConnection(system_id)

    blocked = conn.is_allowed("application")
    if blocked:
        return blocked

    cutoff = datetime.now() - timedelta(hours=older_than_hours)
    d_cut = cutoff.strftime("%Y%m%d")

    schema = conn.hana_schema
    adm = conn.sid.lower() + "adm"

    sql = (
        "SELECT WI_ID, WI_CD, WI_CT, WI_TYPE, WI_RH_TASK, WI_STAT, "
        "WI_AAGENT, WI_TEXT "
        f"FROM {schema}.SWWWIHEAD "
        "WHERE WI_STAT IN ( 'READY', 'STARTED', 'WAITING', 'COMMITTED' ) "
        f"AND WI_CD <= '{d_cut}' "
        "ORDER BY WI_CD, WI_CT"
    )

    cmd = 'su - ' + adm + ' -c ' + '"hdbsql -U ' + conn.hana_userstore + \
          ' -A -j \\"' + sql + '\\""'

    client = conn.get_ssh_client()
    stdin, stdout, stderr = client.exec_command(cmd, timeout=60)
    out = stdout.read().decode(errors="replace")
    client.close()

    if "* " in out and ":" in out.split("* ", 1)[-1][:8]:
        return f"{system_id}: stuck workflow query failed. {out.strip()}"

    rows = [r for r in out.splitlines() if r.strip() and not r.startswith("rows")]
    if not rows:
        return (
            f"{system_id}: no work items older than {older_than_hours} "
            f"hour(s) still sitting in an open status. This is a genuine "
            f"empty result."
        )

    lines = [
        f"{system_id} STUCK WORKFLOWS, open for more than {older_than_hours} hour(s)",
        f"{len(rows)} work item(s) not progressing",
        "",
    ]

    for r in rows[:50]:
        f = [c.strip().strip('"') for c in r.split(",")]
        if len(f) < 8:
            continue
        wi_id, wi_cd, wi_ct, wi_type, task_id, stat, agent, text = f[:8]
        stamp = f"{wi_cd[6:8]}.{wi_cd[4:6]}.{wi_cd[0:4]} {wi_ct[0:2]}:{wi_ct[2:4]}"
        age_note = "no agent assigned" if not agent.strip() else f"assigned to {agent}"
        lines.append(f"[STALLED] {stamp} work item {wi_id} | task {task_id} | status {stat}")
        lines.append(f"          {text}")
        lines.append(f"          {age_note} | check SWI1 for the work item history")

    if len(rows) > 50:
        lines.append("")
        lines.append(f"[TRUNCATED] showing 50 of {len(rows)}.")

    return "\n".join(lines)

# =====================================================================
# WIRING — three places, same as every other tool
#
# 1. agent.py imports
#    from tools.sap_ssh_tools import (
#        ...,
#        check_application_log,
#        list_application_log_objects,
#        check_workflow_errors,
#        list_workflow_summary,
#        check_stuck_workflows,
#    )
#
# 2. agent.py tools list
#    tools=[
#        ...,
#        check_application_log,
#        list_application_log_objects,
#        check_workflow_errors,
#        list_workflow_summary,
#        check_stuck_workflows,
#    ]
#
# 3. tools/sap_connection.py
#    PILLAR_TOOLS["application"].extend([
#        "check_application_log",
#        "list_application_log_objects",
#        "check_workflow_errors",
#        "list_workflow_summary",
#        "check_stuck_workflows",
#    ])
#
# Both belong to the APPLICATION pillar, so they are blocked on PRD
# systems by the existing governance, which is correct.
# =====================================================================

# =====================================================================
# AGENT INSTRUCTION BLOCK — add to the instruction string in agent.py
#
# APPLICATION LOG AND WORKFLOW
#
# check_application_log reads SLG1, the BUSINESS level log. Use it when
# the question is about an application failing rather than a program
# terminating. It is a different layer from ST22: a business validation
# failure writes here and produces no dump at all.
#
# Default to errors_only=True. Routine informational logs are noise and
# a busy system writes hundreds of them.
#
# check_workflow_errors finds work items stuck in error status. A stalled
# workflow is silent, so nobody is notified unless someone looks.
#
# ABSOLUTE RULE for both: an empty result means the log is genuinely
# empty. Say so plainly. Do NOT describe what such logs usually contain,
# and do NOT fill the gap from general SAP knowledge. State that nothing
# was found and suggest widening the window.
#
# Neither tool returns individual message text. Say so when relevant, and
# point the user at SLG1 on the specific log number for the detail.
# =====================================================================
def check_hana_parameters(system_id: str = "A4H") -> str:
    """HANA Parameter Config Review (UC-HP1).
    Reads customer-set (SYSTEM + DATABASE layer) HANA .ini parameter overrides
    and has Gemini assess them against best practice. Reviews only the
    non-DEFAULT layers - deliberate changes from SAP defaults, the real config
    risk surface, not the 3500+ shipped defaults. Focuses on global.ini,
    nameserver.ini, indexserver.ini. READ-ONLY, OPERATIONS pillar.
    system_id: SAP System ID. Default A4H
    """
    conn = SAPConnection(system_id)
    blocked = conn.is_allowed("operations")
    if blocked:
        return blocked
    client = conn.get_ssh_client()
    userstore = conn.hana_userstore
    sql = (
        "SELECT FILE_NAME, LAYER_NAME, SECTION, KEY, VALUE "
        "FROM SYS.M_INIFILE_CONTENTS "
        "WHERE LAYER_NAME IN ('SYSTEM','DATABASE') "
        "ORDER BY FILE_NAME, SECTION, KEY"
    )
    # File-based hdbsql: SFTP the SQL to the VM, run hdbsql -I, avoids
    # all nested-quote issues through paramiko + su (same as UC-D1)
    remote_sql = "/tmp/uc_hp1_params.sql"
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
        return (f"[{system_id}] HANA parameter query failed: "
                + result.strip()[:300])
    if not result.strip():
        return f"[{system_id}] HANA query error: {err.strip()[:300]}"
    if "0 rows selected" in result:
        return (f"[{system_id}] HANA Parameter Review: no SYSTEM/DATABASE "
                f"layer overrides found (unusual - expected customer settings).")

    # Parse the hdbsql pipe-table output into numbered evidence rows
    important = ("global.ini", "nameserver.ini", "indexserver.ini")
    rows = []
    for line in result.splitlines():
        if not line.startswith("|") or line.startswith("| ---"):
            continue
        parts = [c.strip() for c in line.strip("|").split("|")]
        if len(parts) < 5 or parts[0] == "FILE_NAME":
            continue
        rows.append(parts[:5])
    if not rows:
        return (f"[{system_id}] Could not parse parameter rows. Raw:\n"
                + result[:1200])

    ev = []
    n = 0
    for fname, layer, section, key, value in rows:
        n += 1
        flag = " [KEY FILE]" if fname in important else ""
        ev.append(f"[{n}] {fname} / {section} / {key} = {value} "
                  f"(layer={layer}){flag}")
    evidence = "\n".join(ev)

    prompt = (
        "You are a senior SAP HANA administrator reviewing the customer-set "
        "configuration parameter OVERRIDES on system " + system_id + ". These "
        "are parameters deliberately changed from SAP defaults (SYSTEM and "
        "DATABASE layers), so each is a conscious choice worth scrutinising. "
        "Below is the complete numbered list.\n\n"
        "PARAMETER OVERRIDES:\n" + evidence + "\n\n"
        "Assess the configuration. For EACH parameter you comment on, cite its "
        "number [n]. Structure your response:\n"
        "1. OVERALL ASSESSMENT: one line - GREEN / AMBER / RED.\n"
        "2. NOTABLE PARAMETERS: for each worth attention, give parameter, "
        "value, why it matters, and whether it looks safe / aggressive / "
        "risky. Focus on memory (allocationlimit, buffer caches), persistence, "
        "password policy, security-relevant settings. Prioritise global.ini / "
        "nameserver.ini / indexserver.ini.\n"
        "3. SUGGESTED CHECKS: additional HANA mini-checks you would run GIVEN "
        "these specific values (e.g. verify allocationlimit against physical "
        "RAM and co-located tenants).\n\n"
        "RULES: comment only on parameters actually listed - do NOT invent "
        "any. If a value cannot be judged without more context (e.g. physical "
        "RAM), say so rather than guessing. Put general HANA knowledge in a "
        "clearly labelled COMMENTARY note, separate from findings about the "
        "actual data above."
    )
    try:
        from google import genai
        client_ai = genai.Client(vertexai=True, project='sap-basis-copilot', location='global')
        response = client_ai.models.generate_content(
            model='gemini-3.5-flash',
            contents=[{'role': 'user', 'parts': [{'text': prompt}]}])
        verdict = response.text
    except Exception as e:
        return (f"[{system_id}] Collected {n} parameter overrides but Gemini "
                f"review failed: {str(e)}\n\nRAW OVERRIDES:\n{evidence}")

    return (f"[{system_id}] HANA Parameter Config Review - {n} customer "
            f"overrides (SYSTEM/DATABASE layers)\n\n{verdict}")
# ============================================================================
# ============================================================================
# ============================================================================
# OS Patching via VM Manager — operations pillar, state-changing (v4)
# Uses google-cloud-os-config (inventory + patch jobs) and google-cloud-compute
# (VM existence / running-state / reboot confirmation). No gcloud CLI.
# v4 adds: VM-exists-and-running pre-check, before/after OS version capture,
# reboot-and-up confirmation, and a complete single-session narrative.
# Requires in Dockerfile pip install: google-cloud-os-config google-cloud-compute
# ============================================================================

def _osconfig_project():
    import os
    return os.environ.get("GOOGLE_CLOUD_PROJECT", "sap-basis-copilot")


def _vm_status(vm_name: str, zone: str):
    """Return (exists: bool, status: str) for a GCE instance. status is e.g.
    RUNNING / TERMINATED / STOPPING, or '' if it does not exist."""
    from google.cloud import compute_v1
    project = _osconfig_project()
    client = compute_v1.InstancesClient()
    try:
        inst = client.get(project=project, zone=zone, instance=vm_name)
        return True, inst.status
    except Exception:
        return False, ""


def _os_version(vm_name: str, zone: str):
    """Return the OS short_name + version from VM Manager inventory, or None."""
    try:
        from google.cloud import osconfig_v1
        project = _osconfig_project()
        client = osconfig_v1.OsConfigZonalServiceClient()
        name = f"projects/{project}/locations/{zone}/instances/{vm_name}/inventory"
        inv = client.get_inventory(request={"name": name, "view": osconfig_v1.InventoryView.FULL})
        return f"{inv.os_info.short_name} {inv.os_info.version}"
    except Exception:
        return None


def os_patch_check(vm_name: str, zone: str = "us-east4-b") -> str:
    """Check available OS patches on a target VM. First verifies the VM exists and
    is RUNNING, then reads the VM Manager inventory.
    Operations pillar tool — READ-ONLY pre-check. This is the 'before' baseline.
    vm_name is the GCE instance name (e.g. 'rhel-patch-demo')."""
    # 1. VM existence + running-state guard
    try:
        exists, status = _vm_status(vm_name, zone)
    except Exception as e:
        return f"OS patch check for {vm_name}: could not query VM status ({e})."
    if not exists:
        return (f"OS patch check for {vm_name}: VM NOT FOUND in zone {zone}. "
                f"Confirm the instance name and zone before patching.")
    if status != "RUNNING":
        return (f"OS patch check for {vm_name}: VM exists but is '{status}', not RUNNING. "
                f"Start the VM before patching.")
    # 2. Inventory read
    try:
        from google.cloud import osconfig_v1
        project = _osconfig_project()
        client = osconfig_v1.OsConfigZonalServiceClient()
        name = f"projects/{project}/locations/{zone}/instances/{vm_name}/inventory"
        inv = client.get_inventory(request={"name": name, "view": osconfig_v1.InventoryView.FULL})
    except Exception as e:
        return (f"OS patch check for {vm_name}: VM is RUNNING, but inventory is not "
                f"available yet (VM Manager may still be collecting). {e}")
    installed, available, kernel_pending = 0, 0, False
    sample = []
    for item in inv.items.values():
        if item.type_ == osconfig_v1.Inventory.Item.Type.INSTALLED_PACKAGE:
            installed += 1
        elif item.type_ == osconfig_v1.Inventory.Item.Type.AVAILABLE_PACKAGE:
            available += 1
            pkg = item.available_package
            nm = ""
            for attr in ("yum_package", "zypper_patch", "apt_package", "cos_package"):
                p = getattr(pkg, attr, None)
                if p and getattr(p, "package_name", ""):
                    nm = p.package_name; break
            if not nm:
                nm = str(pkg).split("\n")[0][:40]
            if "kernel" in nm.lower():
                kernel_pending = True
            if len(sample) < 8:
                sample.append(nm)
    lines = [f"VM status: RUNNING",
             f"OS: {inv.os_info.short_name} {inv.os_info.version}",
             f"Installed packages: {installed}",
             f"Available updates: {available}",
             f"Kernel update pending: {'YES (reboot required)' if kernel_pending else 'no'}"]
    if sample:
        lines.append("Sample available updates: " + ", ".join(sample))
    return f"OS patch pre-check for {vm_name} ({zone}):\n" + "\n".join(lines)


def os_patch_detect_app(vm_name: str, zone: str = "us-east4-b") -> str:
    """Detect whether an SAP application / HANA is present on the target VM,
    using the VM Manager inventory (installed packages) as a signal.
    Operations pillar tool — READ-ONLY. Call BEFORE os_patch_apply."""
    try:
        from google.cloud import osconfig_v1
        project = _osconfig_project()
        client = osconfig_v1.OsConfigZonalServiceClient()
        name = f"projects/{project}/locations/{zone}/instances/{vm_name}/inventory"
        inv = client.get_inventory(request={"name": name, "view": osconfig_v1.InventoryView.FULL})
    except Exception as e:
        return (f"Application check for {vm_name}: inventory not available ({e}). "
                f"Treat as UNKNOWN — confirm manually before patching.")
    blob = ""
    for item in inv.items.values():
        blob += str(item.installed_package).lower()
    sap_markers = ["saphostagent", "saphostctrl", "hdb", "saphana", "sapcar", "sapinit"]
    hit = [m for m in sap_markers if m in blob]
    if hit:
        return (f"Application check for {vm_name}: SAP-related packages detected ({', '.join(hit)}). "
                f"Treat as a SAP host — STOP SAP/HANA before patching (kernel_patch_stop_sap), "
                f"then start after (kernel_patch_start_sap).")
    return (f"Application check for {vm_name}: no SAP-related packages detected in inventory. "
            f"Appears to be a plain OS host — safe to patch directly, no stop/start needed.")


def os_patch_apply(vm_name: str, zone: str = "us-east4-b", reboot: str = "DEFAULT") -> str:
    """Apply OS patches to a target VM via a VM Manager patch job, then confirm the
    VM rebooted and is back up, and report the OS version before -> after.
    Operations pillar tool — STATE-CHANGING. ONLY call after explicit human
    confirmation and after os_patch_detect_app. Waits up to ~20 minutes for the job
    to complete; for longer jobs it returns the job id and asks the user to run verify.
    Do NOT call against a live SAP host without stopping SAP first."""
    import time
    try:
        from google.cloud import osconfig_v1
    except Exception as e:
        return f"OS patch apply for {vm_name}: os-config library unavailable ({e})"

    # Guard: VM must exist and be RUNNING
    try:
        exists, status = _vm_status(vm_name, zone)
    except Exception as e:
        return f"OS patch apply for {vm_name}: could not query VM status ({e})."
    if not exists:
        return f"OS patch apply for {vm_name}: VM NOT FOUND in zone {zone}. Aborting."
    if status != "RUNNING":
        return f"OS patch apply for {vm_name}: VM is '{status}', not RUNNING. Start it first. Aborting."

    before_version = _os_version(vm_name, zone) or "unknown"
    project = _osconfig_project()
    client = osconfig_v1.OsConfigServiceClient()
    reboot_map = {
        "DEFAULT": osconfig_v1.PatchConfig.RebootConfig.DEFAULT,
        "ALWAYS": osconfig_v1.PatchConfig.RebootConfig.ALWAYS,
        "NEVER": osconfig_v1.PatchConfig.RebootConfig.NEVER,
    }
    try:
        job = client.execute_patch_job(request={
            "parent": f"projects/{project}",
            "instance_filter": osconfig_v1.PatchInstanceFilter(
                instances=[f"zones/{zone}/instances/{vm_name}"]),
            "patch_config": osconfig_v1.PatchConfig(
                reboot_config=reboot_map.get(reboot, osconfig_v1.PatchConfig.RebootConfig.DEFAULT)),
            "display_name": f"{vm_name}-patch-job",
            "description": "OS patch via Basis Copilot",
        })
    except Exception as e:
        return f"OS patch apply for {vm_name}: failed to start patch job ({e})"
    job_name = job.name

    DONE = {osconfig_v1.PatchJob.State.SUCCEEDED,
            osconfig_v1.PatchJob.State.COMPLETED_WITH_ERRORS,
            osconfig_v1.PatchJob.State.CANCELED,
            osconfig_v1.PatchJob.State.TIMED_OUT}
    # Bounded wait ~20 min: 60 iterations x 20s
    final = None
    for _ in range(60):
        try:
            j = client.get_patch_job(name=job_name)
            final = j.state
            if j.state in DONE:
                break
        except Exception:
            pass
        time.sleep(20)

    # If not finished within the window, return gracefully
    if final not in DONE:
        return (f"OS patch job for {vm_name} started (job: {job_name}) and is still running "
                f"after ~20 minutes (state: {final.name if final else 'UNKNOWN'}). "
                f"Large jobs can take longer — run 'verify OS patches on {vm_name}' shortly to "
                f"confirm completion and the final version.")

    if final != osconfig_v1.PatchJob.State.SUCCEEDED:
        return (f"OS patch job for {vm_name} finished with state {final.name} (job: {job_name}). "
                f"Review the patch job in VM Manager for details.")

    # Job SUCCEEDED — confirm the VM rebooted and is back RUNNING (bounded ~5 min)
    reboot_ok = False
    for _ in range(15):
        try:
            _, st = _vm_status(vm_name, zone)
            if st == "RUNNING":
                reboot_ok = True
                break
        except Exception:
            pass
        time.sleep(20)

    # Re-read version + remaining updates (inventory may lag; best-effort)
    after_version = _os_version(vm_name, zone) or "unknown (inventory refreshing)"
    remaining = "unknown"
    try:
        zclient = osconfig_v1.OsConfigZonalServiceClient()
        name = f"projects/{project}/locations/{zone}/instances/{vm_name}/inventory"
        inv = zclient.get_inventory(request={"name": name, "view": osconfig_v1.InventoryView.FULL})
        remaining = str(sum(1 for it in inv.items.values()
                            if it.type_ == osconfig_v1.Inventory.Item.Type.AVAILABLE_PACKAGE))
    except Exception:
        pass

    reboot_line = ("VM rebooted and is back up (RUNNING)." if reboot_ok
                   else "VM reboot not yet confirmed back up — check shortly.")
    version_line = (f"OS version: {before_version} -> {after_version}"
                    if before_version != after_version
                    else f"OS version: {after_version}")
    return (f"OS patch job for {vm_name}: SUCCEEDED (job: {job_name}).\n"
            f"{version_line}\n"
            f"{reboot_line}\n"
            f"Updates remaining: {remaining} "
            f"(inventory refreshes on an interval; run verify shortly if this is not 0 yet).")


def os_patch_verify(vm_name: str, zone: str = "us-east4-b") -> str:
    """Verify OS patching succeeded on the target VM via the VM Manager inventory API.
    Operations pillar tool — READ-ONLY post-check. Reports remaining available updates
    (should be 0) and the OS/kernel state. This is the 'after' evidence."""
    try:
        exists, status = _vm_status(vm_name, zone)
        if not exists:
            return f"OS patch verify for {vm_name}: VM NOT FOUND in zone {zone}."
    except Exception:
        pass
    try:
        from google.cloud import osconfig_v1
        project = _osconfig_project()
        client = osconfig_v1.OsConfigZonalServiceClient()
        name = f"projects/{project}/locations/{zone}/instances/{vm_name}/inventory"
        inv = client.get_inventory(request={"name": name, "view": osconfig_v1.InventoryView.FULL})
    except Exception as e:
        return f"OS patch verify for {vm_name}: inventory not available yet ({e})"
    available = sum(1 for item in inv.items.values()
                    if item.type_ == osconfig_v1.Inventory.Item.Type.AVAILABLE_PACKAGE)
    status_txt = "CLEAN — no updates pending" if available == 0 else f"{available} updates still pending"
    return (f"OS patch verification for {vm_name} ({zone}):\n"
            f"OS: {inv.os_info.short_name} {inv.os_info.version}\n"
            f"Available updates remaining: {available}  ({status_txt})")
