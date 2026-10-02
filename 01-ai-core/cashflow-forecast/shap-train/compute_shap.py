"""
UC2.6 — SHAP summary computation for cashflow forecasting.

Fits a RandomForestRegressor surrogate per company on sliding-window features
derived from PROC_AI.CASHFLOW_DAILY, then computes SHAP TreeExplainer values
on the surrogate. Writes shap_summary_<company>.json per company to OUTPUT_DIR.

IMPORTANT: SHAP values explain the surrogate model, NOT the production
UnivariateMotif forecaster. The surrogate is fit to mimic the forecaster's
behavior on training windows. Downstream verbalization must phrase outputs as
"the prediction is consistent with..." rather than "the model predicted X
because...". See UC2_6_README.md for the full architectural caveat.
"""
import json
import os
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import shap
from hdbcli import dbapi
from sklearn.ensemble import RandomForestRegressor

# ---- env / config ----
HANA_HOST = os.environ.get("HANA_HOST")
HANA_PORT = int(os.environ.get("HANA_PORT", "443"))
HANA_USER = os.environ.get("HANA_USER")
HANA_PASSWORD = os.environ.get("HANA_PASSWORD")
HANA_SCHEMA = os.environ.get("HANA_SCHEMA", "PROC_AI")
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "/app/output")
COMPANIES = os.environ.get("COMPANY_CODES", "1010,1710").split(",")

FEATURES = [
    "lag_1", "lag_7", "lag_14", "lag_30",
    "rolling_mean_7", "rolling_mean_30", "rolling_std_7",
    "dow", "dom", "month",
]


def log(msg: str) -> None:
    print(f"[shap-train] {msg}", flush=True)


def connect_hana():
    if not all([HANA_HOST, HANA_USER, HANA_PASSWORD]):
        log("ERROR: HANA_HOST / HANA_USER / HANA_PASSWORD not all set")
        sys.exit(1)
    log(f"connecting to HANA at {HANA_HOST}:{HANA_PORT} as {HANA_USER}")
    return dbapi.connect(
        address=HANA_HOST,
        port=HANA_PORT,
        user=HANA_USER,
        password=HANA_PASSWORD,
        encrypt=True,
        sslValidateCertificate=True,
    )


def load_company_series(conn, company_code: str) -> pd.DataFrame:
    cur = conn.cursor()
    query = f"""
        SELECT TXN_DATE,
               SUM(CASE WHEN TXN_TYPE = 'INFLOW'  THEN CASHFLOW_AMOUNT ELSE 0 END)
             - SUM(CASE WHEN TXN_TYPE = 'OUTFLOW' THEN CASHFLOW_AMOUNT ELSE 0 END) AS NET_CASHFLOW
        FROM {HANA_SCHEMA}.CASHFLOW_DAILY
        WHERE COMPANY_CODE = '{company_code}'
        GROUP BY TXN_DATE
        ORDER BY TXN_DATE
        
    """
    cur.execute(query)
    rows = cur.fetchall()
    cur.close()
    if not rows:
        raise RuntimeError(f"No rows returned for company {company_code}")
    df = pd.DataFrame(rows, columns=["txn_date", "net_amount"])
    df["txn_date"] = pd.to_datetime(df["txn_date"])
    df["net_amount"] = df["net_amount"].astype(float)
    df = df.sort_values("txn_date").reset_index(drop=True)
    log(f"company {company_code}: loaded {len(df)} rows, "
        f"range {df['txn_date'].min().date()}..{df['txn_date'].max().date()}")
    return df


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Sliding-window features. Drops rows with NaN from initial lags."""
    f = df.copy()
    for lag in (1, 7, 14, 30):
        f[f"lag_{lag}"] = f["net_amount"].shift(lag)
    f["rolling_mean_7"] = f["net_amount"].shift(1).rolling(7).mean()
    f["rolling_mean_30"] = f["net_amount"].shift(1).rolling(30).mean()
    f["rolling_std_7"] = f["net_amount"].shift(1).rolling(7).std()
    f["dow"] = f["txn_date"].dt.dayofweek
    f["dom"] = f["txn_date"].dt.day
    f["month"] = f["txn_date"].dt.month
    f["target"] = f["net_amount"]
    f = f.dropna().reset_index(drop=True)
    return f


def fit_surrogate(features_df: pd.DataFrame) -> RandomForestRegressor:
    X = features_df[FEATURES].values
    y = features_df["target"].values
    model = RandomForestRegressor(
        n_estimators=200,
        max_depth=10,
        min_samples_leaf=3,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X, y)
    train_r2 = model.score(X, y)
    log(f"surrogate trained, in-sample R²={train_r2:.3f} on {len(X)} windows")
    return model


def compute_shap_summary(
    model: RandomForestRegressor,
    features_df: pd.DataFrame,
    company_code: str,
) -> dict:
    X = features_df[FEATURES].values
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X)  # shape: (n_windows, n_features)
    log(f"company {company_code}: computed SHAP, shape={shap_values.shape}")

    # Global feature importance: mean absolute SHAP per feature
    mean_abs_shap = np.abs(shap_values).mean(axis=0)
    global_importance = sorted(
        zip(FEATURES, mean_abs_shap.tolist()),
        key=lambda kv: kv[1],
        reverse=True,
    )

    # Per-window top-3 features (for nearest-window lookup at inference)
    windows = []
    for i in range(len(features_df)):
        sv = shap_values[i]
        ranked = sorted(
            zip(FEATURES, sv.tolist()),
            key=lambda kv: abs(kv[1]),
            reverse=True,
        )[:3]
        windows.append({
            "txn_date": features_df.iloc[i]["txn_date"].strftime("%Y-%m-%d"),
            "feature_vector": features_df.iloc[i][FEATURES].astype(float).tolist(),
            "actual": float(features_df.iloc[i]["target"]),
            "predicted": float(model.predict(X[i:i+1])[0]),
            "top_features": [
                {"name": name, "shap_value": val} for name, val in ranked
            ],
        })

    return {
        "company_code": company_code,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "feature_names": FEATURES,
        "n_training_windows": len(windows),
        "in_sample_r2": float(model.score(X, features_df["target"].values)),
        "global_feature_importance": [
            {"name": n, "mean_abs_shap": v} for n, v in global_importance
        ],
        "windows": windows,
        "_caveat": (
            "SHAP values explain a RandomForest surrogate fit to mimic the "
            "production AutoTS UnivariateMotif forecaster. They are an "
            "approximation of the real model's behavior, not a direct "
            "decomposition of it."
        ),
    }


def main() -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    log(f"OUTPUT_DIR={OUTPUT_DIR}, companies={COMPANIES}")
    conn = connect_hana()
    try:
        for company_code in COMPANIES:
            company_code = company_code.strip()
            log(f"=== processing company {company_code} ===")
            raw = load_company_series(conn, company_code)
            features = build_features(raw)
            log(f"company {company_code}: {len(features)} usable windows after lag dropping")
            model = fit_surrogate(features)
            summary = compute_shap_summary(model, features, company_code)
            out_path = os.path.join(OUTPUT_DIR, f"shap_summary_{company_code}.json")
            with open(out_path, "w") as f:
                json.dump(summary, f, indent=2)
            log(f"company {company_code}: wrote {out_path} "
                f"({len(summary['windows'])} windows, "
                f"top global feature: {summary['global_feature_importance'][0]['name']})")
    finally:
        conn.close()
    log("done")


if __name__ == "__main__":
    main()
