"""
PAL runtime test for SAP HANA Cloud.

Registration in SYS.AFL_PACKAGES proves the PAL library is INSTALLED.
It does NOT prove PAL can EXECUTE: execution needs the Script Server
process, which requires at least 3 vCPUs and is therefore unavailable
on HANA Cloud Free Tier (fixed at 1 vCPU / 16 GB / 80 GB).

This script settles the question by attempting a real PAL fit and
reading the error, rather than inferring from catalog tables.

Prerequisites
-------------
    pip install hana-ml hdbcli

A database user with the AFL roles. DBADMIN cannot grant these to
itself ("grantor and grantee are identical"), so create a dedicated
user:

    CREATE USER PAL_USER PASSWORD "<password>" NO FORCE_FIRST_PASSWORD_CHANGE;
    GRANT AFL__SYS_AFL_AFLPAL_EXECUTE TO PAL_USER;
    GRANT AFL__SYS_AFL_AFLPAL_EXECUTE_WITH_GRANT_OPTION TO PAL_USER;
    GRANT SELECT ON SCHEMA <schema> TO PAL_USER;

Environment variables
---------------------
    HANA_HOST       SQL endpoint hostname, copied verbatim from
                    HANA Cloud Central. Note the subdomain is hna0,
                    not hana. Never construct this from a pattern.
    HANA_PORT       defaults to 443
    HANA_USER       defaults to PAL_USER
    HANA_PASSWORD
    HANA_SCHEMA     schema holding the test table
    HANA_TABLE      table to read

PowerShell note: single quote any password containing $ or @, or the
shell expands it.

    $env:HANA_HOST='<guid>.hna0.prod-<region>.hanacloud.ondemand.com'
    $env:HANA_PASSWORD='<password>'

Run
---
    python test_pal.py
"""
import os
import sys
import traceback

HOST = os.environ.get("HANA_HOST")
PORT = int(os.environ.get("HANA_PORT", "443"))
USER = os.environ.get("HANA_USER", "PAL_USER")
PASSWORD = os.environ.get("HANA_PASSWORD")
SCHEMA = os.environ.get("HANA_SCHEMA")
TABLE = os.environ.get("HANA_TABLE")

if not all([HOST, PASSWORD, SCHEMA, TABLE]):
    print("Missing environment variables. "
          "Need HANA_HOST, HANA_PASSWORD, HANA_SCHEMA, HANA_TABLE.")
    sys.exit(1)

print("=" * 62)
print("PAL runtime test")
print("=" * 62)

# ---------------------------------------------------------------- connect
try:
    from hana_ml import ConnectionContext
    conn = ConnectionContext(
        address=HOST, port=PORT, user=USER, password=PASSWORD, encrypt=True
    )
    print(f"[1] connected      : {conn.hana_version()}")
except Exception as e:
    print(f"[1] FAILED to connect: {e}")
    print()
    print("    Error 414 'user is forced to change password' means the")
    print("    account is in forced-change state. Only hdbsql prompts for")
    print("    the change; hdbcli cannot clear it, even with newPassword=.")
    sys.exit(1)

# --------------------------------------------------- catalog checks first
try:
    cur = conn.connection.cursor()

    cur.execute("SELECT AREA_NAME, PACKAGE_NAME FROM SYS.AFL_PACKAGES")
    packages = cur.fetchall()
    print(f"[2] AFL packages   : {[p[1] for p in packages] or 'none'}")

    cur.execute("SELECT COUNT(*) FROM SYS.AFL_FUNCTIONS "
                "WHERE AREA_NAME = 'AFLPAL'")
    print(f"[3] PAL functions  : {cur.fetchone()[0]}")

    cur.execute("SELECT SERVICE_NAME FROM SYS.M_SERVICES "
                "WHERE ACTIVE_STATUS = 'YES'")
    services = [s[0] for s in cur.fetchall()]
    print(f"[4] services       : {services}")
    print(f"    scriptserver   : "
          f"{'present' if 'scriptserver' in services else 'ABSENT'}")
    cur.close()
except Exception as e:
    print(f"[2] catalog check failed: {e}")

# ------------------------------------------------------------- read table
try:
    df = conn.table(TABLE, schema=SCHEMA)
    print(f"[5] rows visible   : {df.count()}")
except Exception as e:
    print(f"[5] FAILED to read {SCHEMA}.{TABLE}: {e}")
    conn.close()
    sys.exit(1)

# -------------------------------------------------- the decisive PAL call
print("[6] attempting a real PAL fit (IsolationForest) ...")
try:
    from hana_ml.algorithms.pal.preprocessing import IsolationForest

    numeric = df.select(*[c for c in df.columns][:5])
    model = IsolationForest(random_state=42)
    model.fit(data=numeric, key=df.columns[0])

    print()
    print("    RESULT: PAL EXECUTES. Script Server is running.")
    print("    hana-ml in-database training is viable on this instance.")
except Exception as e:
    msg = str(e)
    print()
    print("    RESULT: PAL call failed.")
    print(f"    error: {msg[:300]}")
    print()
    lowered = msg.lower()
    if "scriptserver" in lowered or "34091" in msg:
        print("    Confirmed: Script Server is not running (error 34091).")
        print("    PAL and APL cannot execute on this instance.")
        print("    Needs 3+ vCPUs; Free Tier is fixed at 1.")
        print("    Alternatives: SAP RPT tabular models, the HANA vector")
        print("    engine, AI Core containers, or local Python.")
    else:
        print("    Different failure (grants, column types, or syntax).")
        traceback.print_exc()

conn.close()
print("=" * 62)
