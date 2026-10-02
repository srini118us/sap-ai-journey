"""
Cashflow forecast inference service (UC2.4).

Single-model container. Each deployment runs one instance with MODEL_NAME
pointing to one of the .pkl files registered as a Model artifact in AI Core.
Two deployments (one per company) share this same image.

Endpoints:
  POST /v2/predict  - forecast next N days (N defaults to model's training horizon)
  GET  /v2/healthz  - 200 only if model loaded successfully at startup
  GET  /v2/info     - model metadata + metrics from training run
"""
import json
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

import joblib
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


MODEL_DIR = Path(os.environ.get("MODEL_DIR", "/mnt/models"))
MODEL_NAME = os.environ.get("MODEL_NAME", "model_1710.pkl")
MAX_FORECAST_LENGTH = int(os.environ.get("MAX_FORECAST_LENGTH", "60"))


# In-process state populated at startup. Single-process container, so a plain dict
# is fine; if we ever go multi-worker, switch to a load-once pattern via lifespan.
state = {
    "model": None,
    "metrics": None,
    "company_code": None,
    "loaded_at": None,
    "model_path": None,
    "default_horizon": 14,
}


def _load_model():
    """Eager-load model + metrics at startup. Fail loud if missing — /healthz
    must return 200 only when the container is actually serveable."""
    model_path = MODEL_DIR / MODEL_NAME
    if not model_path.exists():
        raise RuntimeError(
            f"Model file not found at {model_path}. "
            f"Check MODEL_NAME env var and AI Core Model artifact mount."
        )

    print(f"[startup] loading model from {model_path}")
    state["model"] = joblib.load(model_path)
    state["model_path"] = str(model_path)
    state["loaded_at"] = time.time()

    # Convention: filename is model_<company_code>.pkl
    company_code = MODEL_NAME.replace("model_", "").replace(".pkl", "")
    state["company_code"] = company_code

    # metrics.json is a sibling of the .pkl files (archive: none in workflow)
    metrics_path = MODEL_DIR / "metrics.json"
    if metrics_path.exists():
        all_metrics = json.loads(metrics_path.read_text())
        per_company = next(
            (m for m in all_metrics.get("models", []) if m.get("company_code") == company_code),
            None,
        )
        state["metrics"] = per_company
        if per_company and "forecast_horizon_days" in per_company:
            state["default_horizon"] = int(per_company["forecast_horizon_days"])
    else:
        print(f"[startup] warning: metrics.json not found at {metrics_path}")

    print(
        f"[startup] model loaded: company={state['company_code']} "
        f"default_horizon={state['default_horizon']}"
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    _load_model()
    yield


app = FastAPI(
    title="Cashflow Forecast Service",
    version="0.1.0",
    lifespan=lifespan,
)


class PredictRequest(BaseModel):
    forecast_length: Optional[int] = Field(
        default=None,
        ge=1,
        le=MAX_FORECAST_LENGTH,
        description="Days to forecast. Defaults to the training-time horizon (14).",
    )


class ForecastPoint(BaseModel):
    date: str
    forecast: float
    lower_95: Optional[float] = None
    upper_95: Optional[float] = None


class PredictResponse(BaseModel):
    company_code: str
    best_model: str
    horizon: int
    forecast: list[ForecastPoint]


@app.get("/v2/healthz")
def healthz():
    if state["model"] is None:
        raise HTTPException(status_code=503, detail="model not loaded")
    return {"status": "ok"}


@app.get("/v2/info")
def info():
    return {
        "company_code": state["company_code"],
        "model_path": state["model_path"],
        "loaded_at_epoch": state["loaded_at"],
        "default_horizon": state["default_horizon"],
        "max_forecast_length": MAX_FORECAST_LENGTH,
        "training_metrics": state["metrics"],
    }


@app.post("/v2/predict", response_model=PredictResponse)
def predict(req: PredictRequest):
    if state["model"] is None:
        raise HTTPException(status_code=503, detail="model not loaded")

    horizon = req.forecast_length or state["default_horizon"]

    # AutoTS 0.6.x supports forecast_length override on predict(); fall back if not.
    try:
        prediction = state["model"].predict(forecast_length=horizon)
    except TypeError:
        # Older AutoTS API — returns canned fit-time horizon
        prediction = state["model"].predict()

    forecast_df = prediction.forecast
    upper_df = getattr(prediction, "upper_forecast", None)
    lower_df = getattr(prediction, "lower_forecast", None)

    col = forecast_df.columns[0]
    points = []
    for idx in forecast_df.index:
        date_str = idx.isoformat() if hasattr(idx, "isoformat") else str(idx)
        points.append(
            ForecastPoint(
                date=date_str,
                forecast=float(forecast_df.loc[idx, col]),
                upper_95=float(upper_df.loc[idx, col]) if upper_df is not None else None,
                lower_95=float(lower_df.loc[idx, col]) if lower_df is not None else None,
            )
        )

    best_model = state["metrics"]["best_model"] if state["metrics"] else "unknown"
    return PredictResponse(
        company_code=state["company_code"],
        best_model=str(best_model),
        horizon=len(points),
        forecast=points,
    )
