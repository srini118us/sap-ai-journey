"""
Cashflow forecasting — UC2.3.

Reads from PROC_AI.CASHFLOW_DAILY in SAP HANA Cloud (live data).
Computes net cashflow per (date, company): INFLOW - OUTFLOW.
Trains an AutoTS model PER COMPANY (one model per legal entity).
Saves models + metrics as artifacts.

Connection details come from environment variables, populated by the
AI Core Generic Secret 'hana-cashflow-creds' at runtime.
"""
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import joblib
import pandas as pd
from autots import AutoTS
from hdbcli import dbapi

OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", "/app/output"))
METRICS_FILE = OUTPUT_DIR / "metrics.json"

HANA_HOST = os.environ.get("HANA_HOST")
HANA_PORT = int(os.environ.get("HANA_PORT", "443"))
HANA_USER = os.environ.get("HANA_USER")
HANA_PASSWORD = os.environ.get("HANA_PASSWORD")
HANA_SCHEMA = os.environ.get("HANA_SCHEMA", "PROC_AI")

FORECAST_HORIZON = int(os.environ.get("FORECAST_HORIZON", "14"))
COMPANIES = ["1710", "1010"]


def fetch_cashflow_data() -> pd.DataFrame:
    print(f"[load] connecting to HANA at {HANA_HOST}:{HANA_PORT} as {HANA_USER}")
    if not all([HANA_HOST, HANA_USER, HANA_PASSWORD]):
        print("[error] missing HANA env vars - check Generic Secret binding", file=sys.stderr)
        sys.exit(1)

    conn = dbapi.connect(
        address=HANA_HOST,
        port=HANA_PORT,
        user=HANA_USER,
        password=HANA_PASSWORD,
        encrypt=True,
        sslValidateCertificate=True,
    )
    cur = conn.cursor()

    query = f"""
        SELECT
            TXN_DATE,
            COMPANY_CODE,
            SUM(CASE WHEN TXN_TYPE = 'INFLOW'  THEN CASHFLOW_AMOUNT ELSE 0 END) -
            SUM(CASE WHEN TXN_TYPE = 'OUTFLOW' THEN CASHFLOW_AMOUNT ELSE 0 END) AS NET_CASHFLOW
        FROM {HANA_SCHEMA}.CASHFLOW_DAILY
        WHERE COMPANY_CODE IN ('1710', '1010')
        GROUP BY TXN_DATE, COMPANY_CODE
        ORDER BY TXN_DATE, COMPANY_CODE
    """
    print(f"[load] executing aggregation query")
    cur.execute(query)
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description]
    df = pd.DataFrame(rows, columns=cols)
    conn.close()

    df["TXN_DATE"] = pd.to_datetime(df["TXN_DATE"])
    df["NET_CASHFLOW"] = df["NET_CASHFLOW"].astype(float)
    print(f"[load] fetched rows={len(df)} companies={df['COMPANY_CODE'].nunique()} "
          f"range={df['TXN_DATE'].min().date()}..{df['TXN_DATE'].max().date()}")
    return df


def train_one_company(df_company: pd.DataFrame, company_code: str):
    print(f"\n[train:{company_code}] starting AutoTS, rows={len(df_company)}")

    ts = df_company.set_index("TXN_DATE")[["NET_CASHFLOW"]].copy()
    ts.columns = [f"net_cashflow_{company_code}"]

    model = AutoTS(
        forecast_length=FORECAST_HORIZON,
        frequency="D",
        prediction_interval=0.95,
        ensemble=None,
        max_generations=2,
        num_validations=1,
        validation_method="backwards",
        models_to_validate=0.2,
        no_negatives=False,
        verbose=0,
    )
    model = model.fit(ts)

    forecast_df = model.predict().forecast
    print(f"[train:{company_code}] best model: {model.best_model_name}")
    print(f"[train:{company_code}] forecast next {FORECAST_HORIZON} days: "
          f"min={forecast_df.values.min():.0f} max={forecast_df.values.max():.0f}")

    metrics = {
        "company_code": company_code,
        "best_model": str(model.best_model_name),
        "training_rows": len(df_company),
        "forecast_horizon_days": FORECAST_HORIZON,
        "forecast_start": forecast_df.index.min().isoformat(),
        "forecast_end": forecast_df.index.max().isoformat(),
        "forecast_min": float(forecast_df.values.min()),
        "forecast_max": float(forecast_df.values.max()),
        "forecast_mean": float(forecast_df.values.mean()),
    }
    return model, metrics


def main() -> int:
    print("=" * 60)
    print("UC2.3 - Cashflow forecasting (HANA + AutoTS)")
    print("=" * 60)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    df = fetch_cashflow_data()
    if df.empty:
        print("[error] no rows returned from HANA", file=sys.stderr)
        return 1

    all_metrics = {
        "trained_at": datetime.utcnow().isoformat() + "Z",
        "version": "0.3.0",
        "data_source": f"{HANA_SCHEMA}.CASHFLOW_DAILY",
        "models": [],
    }

    for company_code in COMPANIES:
        df_company = df[df["COMPANY_CODE"] == company_code].copy()
        if df_company.empty:
            print(f"[warn] no rows for company {company_code}, skipping")
            continue

        model, metrics = train_one_company(df_company, company_code)

        model_path = OUTPUT_DIR / f"model_{company_code}.pkl"
        print(f"[save] writing model -> {model_path}")
        joblib.dump(model, model_path)

        all_metrics["models"].append(metrics)

    print(f"[save] writing metrics -> {METRICS_FILE}")
    METRICS_FILE.write_text(json.dumps(all_metrics, indent=2))

    print("\n[done] training complete for all companies")
    return 0


if __name__ == "__main__":
    sys.exit(main())
