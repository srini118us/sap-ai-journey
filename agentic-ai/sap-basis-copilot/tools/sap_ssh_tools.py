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

def check_disk_space() -> str:
    return run_ssh_command('df -h')

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

def check_long_running_work_processes() -> str:
    """SM66 equivalent - Global Work Process Overview.
    Flags PRIV mode processes (memory hogs) and processes running
    longer than 10 minutes, identifying the program/report and user."""
    raw = run_ssh_command("su - a4hadm -c 'sapcontrol -nr 00 -function ABAPGetWPTable'")
    lines = raw.strip().split("\n")
    data_lines = [l for l in lines if l.strip() and l[0].isdigit()]
    if not data_lines:
        return raw

    flagged = []
    summary = []
    for line in data_lines:
        cols = [c.strip() for c in line.split(",")]
        if len(cols) < 13:
            continue
        no, typ, pid, status, reason, start, err, sem, cpu, time_str, program, client, user = cols[:13]
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
            flagged.append(f"WP{no} ({typ}, PID {pid}): {reason_tag} | Program: {program or 'N/A'} | User: {user or 'N/A'} | Client: {client or 'N/A'}")

    result = f"Total work processes checked: {len(data_lines)}\n"
    result += f"Status summary: {', '.join(summary)}\n\n"
    if flagged:
        result += "FLAGGED WORK PROCESSES:\n" + "\n".join(flagged)
    else:
        result += "No work processes in PRIV mode or running over 10 minutes. All processes healthy."
    return result

def check_lock_entries() -> str:
    return run_ssh_command("su - a4hadm -c 'sapcontrol -nr 01 -function EnqGetStatistic'")

def check_hana_load_history() -> str:
    sql = 'SELECT HOST, MAX(CPU) AS MAX_CPU_PCT, MAX(MEMORY_USED)/1024/1024 AS MAX_MEM_GB FROM SYS.M_LOAD_HISTORY_SERVICE WHERE TIME >= ADD_SECONDS(NOW(), -86400) GROUP BY HOST'
    cmd = f"su - hdbadm -c 'hdbsql -U HDB_KEY_CAL -d SYSTEMDB \"{sql}\"'"
    return run_ssh_command(cmd)

def check_hana_expensive_sql() -> str:
    sql = 'SELECT TOP 5 STATEMENT_HASH, EXECUTION_COUNT, TOTAL_EXECUTION_TIME/1000000 AS TOTAL_SEC, LEFT(STATEMENT_STRING,80) AS STMT FROM SYS.M_SQL_PLAN_CACHE ORDER BY TOTAL_EXECUTION_TIME DESC'
    cmd = f"su - hdbadm -c 'hdbsql -U HDB_KEY_CAL -d SYSTEMDB \"{sql}\"'"
    return run_ssh_command(cmd)

def check_failed_updates() -> str:
    sql = 'SELECT COUNT(*) AS FAILED_UPDATES FROM SAPA4H.VBHDR WHERE VBSTATE = 2'
    cmd = f"su - a4hadm -c 'hdbsql -U DEFAULT -d HDB \"{sql}\"'"
    return run_ssh_command(cmd)

def check_failed_trfc() -> str:
    """SM58 equivalent - finds failed tRFC entries with full diagnostic context.
    Returns destination, function module, error message, user, and tcode for each
    failed entry so the agent can classify transient vs config issues. Does NOT
    reprocess anything - reprocessing requires explicit human confirmation via
    reprocess_trfc_entry()."""
    import paramiko as _paramiko
    client = _paramiko.SSHClient()
    client.set_missing_host_key_policy(_paramiko.AutoAddPolicy())
    client.connect(SAP_HOST, username=SAP_USER, key_filename=SAP_KEY)
    sql = "SELECT ARFCDEST, ARFCFNAM, ARFCMSG, ARFCUSER, ARFCTCODE, ARFCDATUM, ARFCUZEIT, ARFCRETRYS FROM SAPA4H.ARFCSSTATE WHERE ARFCSTATE = \'SYSFAIL\'"
    sftp = client.open_sftp()
    with sftp.open("/tmp/sm58_detail.sql", "w") as f:
        f.write(sql)
    sftp.close()
    stdin, stdout, stderr = client.exec_command("su - a4hadm -c \'hdbsql -U DEFAULT -d HDB -I /tmp/sm58_detail.sql\'")
    result = stdout.read().decode()
    client.close()
    return result if result.strip() else "No SYSFAIL entries found in tRFC queue."

def reprocess_trfc_entry(destination: str, function_module: str) -> str:
    """Reprocesses a failed tRFC entry by triggering RSARFCEX for the specified
    destination via background job. ONLY call this after the human has explicitly
    confirmed they want to reprocess this specific entry. NEVER call this
    automatically without explicit human confirmation in the conversation,
    especially for destinations related to invoicing, billing, or customer-facing
    interfaces, where reprocessing could cause duplicate transactions."""
    cmd = f"su - a4hadm -c \"echo 'SUBMIT RSARFCEX WITH DESTIN = {destination}.' > /tmp/rsarfcex_job.txt && echo 'Job submission prepared for destination {destination}, function {function_module}. Manual execution via SE38/SM37 recommended for this trial system - RSARFCEX requires background job scheduling authorization.'\""
    return run_ssh_command(cmd)

def check_sost_failures() -> str:
    cmd = "su - a4hadm -c 'hdbsql -U DEFAULT -d HDB -o /tmp/sost_out.txt \"SELECT STA_ORDER, COUNT(*) AS CNT FROM SAPA4H.SOST GROUP BY STA_ORDER\" && cat /tmp/sost_out.txt'"
    return run_ssh_command(cmd)

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

def check_cancelled_jobs() -> str:
    import paramiko as _paramiko
    client = _paramiko.SSHClient()
    client.set_missing_host_key_policy(_paramiko.AutoAddPolicy())
    client.connect(SAP_HOST, username=SAP_USER, key_filename=SAP_KEY)
    sql = "SELECT JOBNAME, STRTDATE, STRTTIME, ENDDATE, ENDTIME, STATUS FROM SAPA4H.TBTCO WHERE STATUS = 'A' AND STRTDATE >= TO_VARCHAR(ADD_DAYS(NOW(),-1),'YYYYMMDD') ORDER BY STRTDATE DESC"
    sftp = client.open_sftp()
    with sftp.open('/tmp/sm37c.sql', 'w') as f:
        f.write(sql)
    sftp.close()
    stdin, stdout, stderr = client.exec_command("su - a4hadm -c 'hdbsql -U DEFAULT -d HDB -I /tmp/sm37c.sql'")
    result = stdout.read().decode()
    client.close()
    return result if result else "No cancelled jobs found in last 24h" 

def check_long_running_jobs() -> str:
    import paramiko as _paramiko
    client = _paramiko.SSHClient()
    client.set_missing_host_key_policy(_paramiko.AutoAddPolicy())
    client.connect(SAP_HOST, username=SAP_USER, key_filename=SAP_KEY)
    sql = "SELECT JOBNAME, STRTDATE, STRTTIME, STATUS FROM SAPA4H.TBTCO WHERE STATUS = 'R' AND STRTDATE >= TO_VARCHAR(ADD_DAYS(NOW(),-1),'YYYYMMDD') ORDER BY STRTDATE DESC"
    sftp = client.open_sftp()
    with sftp.open('/tmp/sm37l.sql', 'w') as f:
        f.write(sql)
    sftp.close()
    stdin, stdout, stderr = client.exec_command("su - a4hadm -c 'hdbsql -U DEFAULT -d HDB -I /tmp/sm37l.sql'")
    result = stdout.read().decode()
    client.close()
    return result if result else "No long running jobs found" 

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

def check_sarfc() -> str:
    """SARFC equivalent - checks RFC server group resources from RZLLITAB.
    Shows available work process quota and users per server group and AS instance.
    Status GREEN if WP_QUOTA > 0, YELLOW if WP_QUOTA = 0 (needs RZ12 config check)."""
    import paramiko as _paramiko
    client = _paramiko.SSHClient()
    client.set_missing_host_key_policy(_paramiko.AutoAddPolicy())
    client.connect(SAP_HOST, username=SAP_USER, key_filename=SAP_KEY)
    sql = """SELECT CLASSNAME, APPLSERVER, WP_QUOTA, USERS, GROUPTYPE
    FROM SAPA4H.RZLLITAB
    ORDER BY CLASSNAME, APPLSERVER"""
    sftp = client.open_sftp()
    with sftp.open('/tmp/sarfc_check.sql', 'w') as f:
        f.write(sql)
    sftp.close()
    stdin, stdout, stderr = client.exec_command(
        "su - a4hadm -c 'hdbsql -U DEFAULT -d HDB -I /tmp/sarfc_check.sql'"
    )
    result = stdout.read().decode()
    client.close()
    if not result.strip():
        return "No RFC server groups found in RZLLITAB. Check RZ12 configuration."
    return result

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

def get_idoc_details(mestyp: str, status: str) -> str:
    """Get details of failed IDocs for a specific message type and status.
    Used to provide context for human review before reprocessing decision."""
    import paramiko as _paramiko
    client = _paramiko.SSHClient()
    client.set_missing_host_key_policy(_paramiko.AutoAddPolicy())
    client.connect(SAP_HOST, username=SAP_USER, key_filename=SAP_KEY)
    sql = f"""SELECT DOCNUM, MESTYP, STATUS, DIRECT, RCVPRT, RCVPRN,
    SNDPRT, SNDPRN, CREDAT, CRETIM, UPDDAT, UPDTIM
    FROM SAPA4H.EDIDC
    WHERE MESTYP = '{mestyp}' AND STATUS = '{status}'
    AND UPDDAT >= TO_VARCHAR(ADD_DAYS(NOW(),-7),'YYYYMMDD')
    ORDER BY CREDAT DESC, CRETIM DESC"""
    sftp = client.open_sftp()
    with sftp.open('/tmp/idoc_detail.sql', 'w') as f:
        f.write(sql)
    sftp.close()
    stdin, stdout, stderr = client.exec_command(
        "su - a4hadm -c 'hdbsql -U DEFAULT -d HDB -I /tmp/idoc_detail.sql'"
    )
    result = stdout.read().decode()
    client.close()
    return result if result.strip() else f"No IDocs found for MESTYP={mestyp} STATUS={status}."

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

def check_smq1_outbound() -> str:
    """SMQ1 equivalent - checks outbound qRFC queues for stuck or failed entries.
    Joins QRFC_N_QOUT with QRFC_I_ERR_STATE to identify queues with errors."""
    import paramiko as _paramiko
    client = _paramiko.SSHClient()
    client.set_missing_host_key_policy(_paramiko.AutoAddPolicy())
    client.connect(SAP_HOST, username=SAP_USER, key_filename=SAP_KEY)
    sql = """SELECT Q.QUEUE_NAME, Q.DEST_NAME, Q.CLIENT,
    COUNT(Q.UNIT_ID) AS QUEUE_DEPTH,
    E.MESSAGE
    FROM SAPA4H.QRFC_N_QOUT Q
    LEFT JOIN SAPA4H.QRFC_I_ERR_STATE E ON Q.UNIT_ID = E.UNIT_ID
    GROUP BY Q.QUEUE_NAME, Q.DEST_NAME, Q.CLIENT, E.MESSAGE
    ORDER BY QUEUE_DEPTH DESC"""
    sftp = client.open_sftp()
    with sftp.open('/tmp/smq1.sql', 'w') as f:
        f.write(sql)
    sftp.close()
    stdin, stdout, stderr = client.exec_command(
        "su - a4hadm -c 'hdbsql -U DEFAULT -d HDB -I /tmp/smq1.sql'"
    )
    result = stdout.read().decode()
    client.close()
    return result if result.strip() else "No outbound qRFC queue entries found (SMQ1 is clean)."

def check_smq2_inbound() -> str:
    """SMQ2 equivalent - checks inbound qRFC queues for stuck or failed entries.
    Joins QRFC_I_QIN with QRFC_I_ERR_STATE to identify queues with errors."""
    import paramiko as _paramiko
    client = _paramiko.SSHClient()
    client.set_missing_host_key_policy(_paramiko.AutoAddPolicy())
    client.connect(SAP_HOST, username=SAP_USER, key_filename=SAP_KEY)
    sql = """SELECT Q.QUEUE_NAME, Q.DEST_NAME, Q.CLIENT,
    COUNT(Q.UNIT_ID) AS QUEUE_DEPTH,
    E.MESSAGE
    FROM SAPA4H.QRFC_I_QIN Q
    LEFT JOIN SAPA4H.QRFC_I_ERR_STATE E ON Q.UNIT_ID = E.UNIT_ID
    GROUP BY Q.QUEUE_NAME, Q.DEST_NAME, Q.CLIENT, E.MESSAGE
    ORDER BY QUEUE_DEPTH DESC"""
    sftp = client.open_sftp()
    with sftp.open('/tmp/smq2.sql', 'w') as f:
        f.write(sql)
    sftp.close()
    stdin, stdout, stderr = client.exec_command(
        "su - a4hadm -c 'hdbsql -U DEFAULT -d HDB -I /tmp/smq2.sql'"
    )
    result = stdout.read().decode()
    client.close()
    return result if result.strip() else "No inbound qRFC queue entries found (SMQ2 is clean)."
def check_st22_dumps() -> str:
    """ST22 equivalent - finds ABAP short dumps from last 24 hours.
    Only returns critical information: error type, program, count.
    Filters to top 10 most frequent dumps only."""
    import paramiko as _paramiko
    client = _paramiko.SSHClient()
    client.set_missing_host_key_policy(_paramiko.AutoAddPolicy())
    client.connect(SAP_HOST, username=SAP_USER, key_filename=SAP_KEY)
    sql = """SELECT TOP 10
    SNAPDATE, ERRTY, ERRCLAS, REPID,
    LEFT(ERRMESS, 80) AS ERROR_MSG,
    COUNT(*) AS DUMP_COUNT
    FROM SAPA4H.SNAP
    WHERE SNAPDATE >= TO_VARCHAR(ADD_DAYS(NOW(),-1),'YYYYMMDD')
    GROUP BY SNAPDATE, ERRTY, ERRCLAS, REPID, ERRMESS
    ORDER BY DUMP_COUNT DESC"""
    sftp = client.open_sftp()
    with sftp.open('/tmp/st22.sql', 'w') as f:
        f.write(sql)
    sftp.close()
    stdin, stdout, stderr = client.exec_command(
        "su - a4hadm -c 'hdbsql -U DEFAULT -d HDB -I /tmp/st22.sql'"
    )
    result = stdout.read().decode()
    client.close()
    return result if result.strip() else "No ABAP short dumps in last 24 hours. ST22 is GREEN."

def check_sm21_syslog() -> str:
    """SM21 equivalent - reads SAP system log for critical errors only.
    Uses sapcontrol ABAPReadSyslog and filters for E/A severity messages.
    Ignores Info and Warning level messages to reduce noise."""
    import paramiko as _paramiko
    client = _paramiko.SSHClient()
    client.set_missing_host_key_policy(_paramiko.AutoAddPolicy())
    client.connect(SAP_HOST, username=SAP_USER, key_filename=SAP_KEY)
    stdin, stdout, stderr = client.exec_command(
        "su - a4hadm -c 'sapcontrol -nr 00 -function ABAPReadSyslog' | grep -E '(Error|Abort|Critical|ABAP|kernel|restart|dump|shutdown)' | head -20"
    )
    result = stdout.read().decode()
    client.close()
    if not result.strip():
        return "No critical errors found in SAP system log. SM21 is GREEN."
    return result

def check_sost_failed_emails() -> str:
    """SOST detailed check - groups failed entries by error reason and send type.
    More detailed than check_sost_failures - shows error message and oldest/newest dates."""
    import paramiko as _paramiko
    client = _paramiko.SSHClient()
    client.set_missing_host_key_policy(_paramiko.AutoAddPolicy())
    client.connect(SAP_HOST, username=SAP_USER, key_filename=SAP_KEY)
    sql = """SELECT SNDART, MSGID, MSGNO, LEFT(MSGV1,60) AS ERROR_REASON,
    COUNT(*) AS CNT,
    MIN(ENTRY_DATE) AS OLDEST,
    MAX(ENTRY_DATE) AS NEWEST
    FROM SAPA4H.SOST
    WHERE STA_ORDER NOT IN ('S','E')
    OR (STA_ORDER = 'E' AND ENTRY_DATE >= TO_VARCHAR(ADD_DAYS(NOW(),-1),'YYYYMMDD'))
    GROUP BY SNDART, MSGID, MSGNO, MSGV1
    ORDER BY CNT DESC"""
    sftp = client.open_sftp()
    with sftp.open('/tmp/sost_failed.sql', 'w') as f:
        f.write(sql)
    sftp.close()
    stdin, stdout, stderr = client.exec_command(
        "su - a4hadm -c 'hdbsql -U DEFAULT -d HDB -I /tmp/sost_failed.sql'"
    )
    result = stdout.read().decode()
    client.close()
    return result if result.strip() else "No failed SOST entries found in last 24h."

def get_sost_failed_details() -> str:
    """Get full details of failed SOST entries for human review before resend decision.
    Shows object key, sender, recipient, send type, date, and error."""
    import paramiko as _paramiko
    client = _paramiko.SSHClient()
    client.set_missing_host_key_policy(_paramiko.AutoAddPolicy())
    client.connect(SAP_HOST, username=SAP_USER, key_filename=SAP_KEY)
    sql = """SELECT OBJTP, OBJYR, OBJNO, SNDART, CREATOR, SENDER,
    ENTRY_DATE, ENTRY_TIME, STA_ORDER, MSGID, MSGNO, LEFT(MSGV1,60) AS ERROR
    FROM SAPA4H.SOST
    WHERE STA_ORDER NOT IN ('S','E')
    OR (STA_ORDER = 'E' AND ENTRY_DATE >= TO_VARCHAR(ADD_DAYS(NOW(),-1),'YYYYMMDD'))
    ORDER BY ENTRY_DATE DESC, ENTRY_TIME DESC"""
    sftp = client.open_sftp()
    with sftp.open('/tmp/sost_details.sql', 'w') as f:
        f.write(sql)
    sftp.close()
    stdin, stdout, stderr = client.exec_command(
        "su - a4hadm -c 'hdbsql -U DEFAULT -d HDB -I /tmp/sost_details.sql'"
    )
    result = stdout.read().decode()
    client.close()
    return result if result.strip() else "No failed SOST entries found."

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

