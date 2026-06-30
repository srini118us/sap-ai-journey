import paramiko
import os
import tempfile

SAP_HOST = "35.236.203.34"
SAP_USER = "root"

def get_ssh_key_path():
    key_path = os.path.expanduser("~/.ssh/sap-basis-agent-key")
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

def check_sap_process_health() -> str:
    return run_ssh_command("su - a4hadm -c 'sapcontrol -nr 00 -function GetProcessList'")

def check_hana_health() -> str:
    return run_ssh_command("su - hdbadm -c 'sapcontrol -nr 02 -function GetProcessList'")

def check_disk_space() -> str:
    return run_ssh_command('df -h')

def check_system_instances() -> str:
    return run_ssh_command("su - a4hadm -c 'sapcontrol -nr 00 -function GetSystemInstanceList'")

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

def check_kernel_version() -> str:
    return run_ssh_command("su - a4hadm -c 'disp+work -version'")

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
'''], capture_output=True, text=True)
    return result.stdout if result.stdout else result.stderr

def analyze_dbacockpit_memory_screenshot() -> str:
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
response = client_ai.models.generate_content(model='gemini-3.5-flash', contents=[{'role':'user','parts':[{'inline_data':{'mime_type':'image/jpeg','data':image_b64}},{'text':'SAP DBACOCKPIT Memory chart. Extract Max Memory MB, Avg Memory MB, Current Memory MB, Total Physical MB. Calculate utilization %. Status GREEN<70% YELLOW 70-85% RED>85%.'}]}])
print(response.text)
'''], capture_output=True, text=True)
