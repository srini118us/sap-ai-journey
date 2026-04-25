"""
Cashflow forecasting training script — sklearn placeholder.

Reads a CSV with columns: date, company_code, cashflow_amount, currency.
Trains a LinearRegression model to predict cashflow_amount from a
day-of-year feature. Saves model + metrics as artifacts.

This is the Friday placeholder. Sunday will swap LinearRegression
for AutoTS without changing the surrounding pipeline.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

import joblib
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, r2_score


# Paths follow AI Core Argo conventions.
# Inputs land at /app/data/ (mounted by Argo from the bound dataset).
# Outputs go to /app/output/ (uploaded by Argo to S3 as model artifacts).
DATA_DIR = Path(os.environ.get("DATA_DIR", "/app/data"))
OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", "/app/output"))
INPUT_FILE = DATA_DIR / "cashflow_sample.csv"
MODEL_FILE = OUTPUT_DIR / "model.pkl"
METRICS_FILE = OUTPUT_DIR / "metrics.json"


def load_data(path: Path) -> pd.DataFrame:
    print(f"[load] reading {path}")
    df = pd.read_csv(path)
    df["date"] = pd.to_datetime(df["date"])
    df["day_of_year"] = df["date"].dt.dayofyear
    print(f"[load] rows={len(df)} columns={list(df.columns)}")
    return df


def train(df: pd.DataFrame) -> tuple[LinearRegression, dict]:
    print("[train] fitting LinearRegression on day_of_year -> cashflow_amount")
    X = df[["day_of_year"]].values
    y = df["cashflow_amount"].values

    model = LinearRegression()
    model.fit(X, y)

    y_pred = model.predict(X)
    metrics = {
        "model_type": "LinearRegression",
        "training_rows": len(df),
        "features": ["day_of_year"],
        "target": "cashflow_amount",
        "mae": float(mean_absolute_error(y, y_pred)),
        "r2": float(r2_score(y, y_pred)),
        "trained_at": datetime.utcnow().isoformat() + "Z",
        "version": "0.1.0",
    }
    print(f"[train] metrics={metrics}")
    return model, metrics


def save(model: LinearRegression, metrics: dict) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[save] writing model -> {MODEL_FILE}")
    joblib.dump(model, MODEL_FILE)
    print(f"[save] writing metrics -> {METRICS_FILE}")
    METRICS_FILE.write_text(json.dumps(metrics, indent=2))


def main() -> int:
    print("=" * 60)
    print("cashflow-forecast training (sklearn placeholder)")
    print("=" * 60)
    if not INPUT_FILE.exists():
        print(f"[error] input not found: {INPUT_FILE}", file=sys.stderr)
        print(f"[error] DATA_DIR contents: {list(DATA_DIR.glob('*'))}", file=sys.stderr)
        return 1

    df = load_data(INPUT_FILE)
    model, metrics = train(df)
    save(model, metrics)
    print("[done] training complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
