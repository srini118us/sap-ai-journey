"""
Batch supplier delivery risk scoring.
Reads V_SUPPLIER_FEATURES (Datasphere space schema), calls the AI Core XGBoost
deployment for each supplier, appends results to a decision log table in the
Open SQL schema. One RUN_ID per execution keeps full history (auditable).
"""
import json
import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import requests
from dotenv import load_dotenv
from hdbcli import dbapi

load_dotenv()

SPACE_SCHEMA = "UC4_PROC"
OPEN_SCHEMA = "UC4_PROC#SCORING"
VIEW = "V_SUPPLIER_FEATURES"
LOG_TABLE = "SUPPLIER_RISK_DECISION_LOG"
HIGH_RISK = 0.50      # late probability threshold for HIGH band
MEDIUM_RISK = 0.30    # late probability threshold for MEDIUM band

FEATURES = [
    "vendor_category", "vendor_country", "historical_ontime_rate",
    "avg_lead_time_days", "lead_time_variance", "po_count_last_quarter",
    "po_amount", "concurrent_pos", "material_complexity",
    "expected_lead_time_days", "delivery_day_of_week",
    "is_quarter_end", "is_peak_season",
]

DDL = f'''
CREATE COLUMN TABLE "{OPEN_SCHEMA}"."{LOG_TABLE}" (
  RUN_ID              NVARCHAR(36)  NOT NULL,
  SUPPLIER            NVARCHAR(10)  NOT NULL,
  STATUS              NVARCHAR(10),
  PREDICTION          NVARCHAR(10),
  LATE_PROBABILITY    DECIMAL(6,4),
  ONTIME_PROBABILITY  DECIMAL(6,4),
  CONFIDENCE          NVARCHAR(10),
  RISK_BAND           NVARCHAR(10),
  TOP_FACTOR          NVARCHAR(60),
  MODEL_ID            NVARCHAR(40),
  DEPLOYMENT_ID       NVARCHAR(40),
  FEATURES_JSON       NVARCHAR(2000),
  ERROR_MESSAGE       NVARCHAR(1000),
  SCORED_AT           TIMESTAMP,
  PRIMARY KEY (RUN_ID, SUPPLIER)
)'''


def to_native(v):
    """Datasphere returns Decimal; the model expects plain JSON numbers."""
    if isinstance(v, Decimal):
        return float(v)
    return v


def get_token():
    r = requests.post(
        os.environ["AICORE_AUTH_URL"],
        data={
            "grant_type": "client_credentials",
            "client_id": os.environ["AICORE_CLIENT_ID"],
            "client_secret": os.environ["AICORE_CLIENT_SECRET"],
        },
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def risk_band(late_p):
    if late_p is None:
        return None
    if late_p >= HIGH_RISK:
        return "HIGH"
    if late_p >= MEDIUM_RISK:
        return "MEDIUM"
    return "LOW"


def main():
    conn = dbapi.connect(
        address=os.environ["DSP_HOST"], port=443,
        user=os.environ["DSP_USER"], password=os.environ["DSP_PASSWORD"],
        encrypt=True, sslValidateCertificate=True,
    )
    cur = conn.cursor()

    cur.execute(
        "SELECT COUNT(*) FROM SYS.TABLES WHERE SCHEMA_NAME = ? AND TABLE_NAME = ?",
        (OPEN_SCHEMA, LOG_TABLE),
    )
    if cur.fetchone()[0] == 0:
        cur.execute(DDL)
        print(f"Created {OPEN_SCHEMA}.{LOG_TABLE}")

    cur.execute(f'SELECT "Supplier", {", ".join(f"{chr(34)}{c}{chr(34)}" for c in FEATURES)} '
                f'FROM "{SPACE_SCHEMA}"."{VIEW}"')
    rows = cur.fetchall()
    print(f"Read {len(rows)} suppliers from {VIEW}")

    token = get_token()
    dep_url = os.environ["AICORE_DEPLOYMENT_URL"].rstrip("/")
    headers = {"Authorization": f"Bearer {token}", "AI-Resource-Group": "default"}
    run_id = str(uuid.uuid4())
    scored_at = datetime.now(timezone.utc).replace(tzinfo=None)
    model_id = os.environ.get("AICORE_MODEL_ID", "")
    deployment_id = dep_url.split("/")[-1]

    out = []
    for row in rows:
        supplier = row[0]
        payload = {f: to_native(v) for f, v in zip(FEATURES, row[1:])}
        rec = dict(status="ERROR", pred=None, late=None, ontime=None,
                   conf=None, top=None, err=None)
        try:
            r = requests.post(f"{dep_url}/v2/predict", headers=headers,
                              json=payload, timeout=30)
            if r.ok:
                d = r.json()
                factors = d.get("top_factors") or []
                rec.update(status="OK", pred=d.get("prediction"),
                           late=d.get("late_probability"),
                           ontime=d.get("on_time_probability"),
                           conf=d.get("confidence"),
                           top=factors[0]["feature"] if factors else None)
            else:
                rec["err"] = f"{r.status_code}: {r.text[:900]}"
        except requests.RequestException as e:
            rec["err"] = str(e)[:900]

        out.append((run_id, supplier, rec["status"], rec["pred"], rec["late"],
                    rec["ontime"], rec["conf"], risk_band(rec["late"]), rec["top"],
                    model_id, deployment_id, json.dumps(payload), rec["err"],
                    scored_at))
        print(f'{supplier:<12} {rec["status"]:<6} {rec["pred"] or "":<8} '
              f'late={rec["late"]} band={risk_band(rec["late"])}')

    cur.executemany(
        f'INSERT INTO "{OPEN_SCHEMA}"."{LOG_TABLE}" VALUES '
        f'(?,?,?,?,?,?,?,?,?,?,?,?,?,?)', out)
    conn.commit()
    ok = sum(1 for o in out if o[2] == "OK")
    print(f"Run {run_id}: {ok}/{len(out)} scored, written to {LOG_TABLE}")
    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
