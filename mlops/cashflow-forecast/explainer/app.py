"""
UC2.6 — SHAP-based cashflow forecast explainer.

Composes: existing UC2.4 /v2/predict deployments + pre-computed SHAP
summaries (from UC2.6 shap-train artifact) + GPT-4o via SAP GenAI Hub.

IMPORTANT — Surrogate honesty: SHAP values explain a RandomForest
surrogate trained to mimic the production AutoTS UnivariateMotif
forecaster, NOT the forecaster itself. Verbalization phrases drivers
as "consistent with" rather than "because of".

Endpoints:
  GET  /v2/healthz   -> liveness probe
  GET  /v2/info      -> service metadata
  POST /v2/explain   -> {company_code} -> forecast + SHAP narrative
"""
import json
import logging
import os
from pathlib import Path
from typing import Any

import numpy as np
import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO, format="[explainer] %(message)s")
log = logging.getLogger(__name__)

# ---- env / config ----
SHAP_SUMMARY_DIR = os.getenv("SHAP_SUMMARY_DIR", "/app/shap-summaries")
PREDICT_URL_1010 = os.getenv("PREDICT_URL_1010", "")
PREDICT_URL_1710 = os.getenv("PREDICT_URL_1710", "")
GPT4O_DEPLOYMENT_ID = os.getenv("GPT4O_DEPLOYMENT_ID", "")
AICORE_RESOURCE_GROUP = os.getenv("AICORE_RESOURCE_GROUP", "ai-launchpad")
PREDICT_RESOURCE_GROUP = os.getenv("PREDICT_RESOURCE_GROUP", AICORE_RESOURCE_GROUP)

# AICORE_AUTH_URL, AICORE_CLIENT_ID, AICORE_CLIENT_SECRET, AICORE_BASE_URL
# auto-picked up by gen-ai-hub-sdk

PREDICT_URLS: dict[str, str] = {}
if PREDICT_URL_1010:
    PREDICT_URLS["1010"] = PREDICT_URL_1010
if PREDICT_URL_1710:
    PREDICT_URLS["1710"] = PREDICT_URL_1710

SUMMARIES: dict[str, dict[str, Any]] = {}


def load_summaries() -> None:
    """Load shap_summary_<company>.json files at startup."""
    summary_dir = Path(SHAP_SUMMARY_DIR)
    if not summary_dir.exists():
        log.error("SHAP_SUMMARY_DIR=%s does not exist", summary_dir)
        return
    for path in sorted(summary_dir.glob("shap_summary_*.json")):
        try:
            with open(path) as f:
                data = json.load(f)
            company = data.get("company_code")
            if not company:
                log.warning("%s has no company_code, skipping", path)
                continue
            SUMMARIES[company] = data
            log.info(
                "loaded %s: %d windows, top feature %s",
                path.name,
                data.get("n_training_windows", 0),
                data.get("global_feature_importance", [{}])[0].get("name"),
            )
        except Exception as e:
            log.error("failed to load %s: %s", path, e)


def get_aicore_token() -> str:
    """Fetch OAuth token for calling AI Core inference deployments.
    
    The gen-ai-hub-sdk handles its own auth, but for direct /v2/predict calls
    to the UC2.4 serving deployments, we need raw OAuth.
    """
    resp = requests.post(
        os.environ["AICORE_AUTH_URL"] + "/oauth/token",
        data={"grant_type": "client_credentials"},
        auth=(os.environ["AICORE_CLIENT_ID"], os.environ["AICORE_CLIENT_SECRET"]),
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def call_predict(company_code: str) -> dict[str, Any]:
    """Call UC2.4 /v2/predict deployment for the given company."""
    if company_code not in PREDICT_URLS:
        raise ValueError(f"No predict URL configured for company {company_code}")
    url = PREDICT_URLS[company_code] + "/v2/predict"
    token = get_aicore_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "AI-Resource-Group": PREDICT_RESOURCE_GROUP,
        "Content-Type": "application/json",
    }
    body = {"forecast_length": 14}
    resp = requests.post(url, json=body, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json()


def find_nearest_window(summary: dict[str, Any], target_features: list[float]) -> dict[str, Any]:
    """Cosine-similarity nearest window match among training windows."""
    target = np.array(target_features, dtype=float)
    target_norm = np.linalg.norm(target)
    if target_norm == 0:
        return summary["windows"][0]
    best_score, best_window = -1.0, summary["windows"][0]
    for w in summary["windows"]:
        v = np.array(w["feature_vector"], dtype=float)
        v_norm = np.linalg.norm(v)
        if v_norm == 0:
            continue
        score = float(np.dot(target, v) / (target_norm * v_norm))
        if score > best_score:
            best_score, best_window = score, w
    return best_window


def build_prompt(company_code: str, forecast: float, nearest_window: dict[str, Any]) -> list[dict[str, str]]:
    """Construct chat messages for GPT-4o."""
    top_features = nearest_window.get("top_features", [])
    feat_lines = []
    for f in top_features:
        sign = "toward higher inflow" if f["shap_value"] > 0 else "toward lower inflow"
        feat_lines.append(f"  - {f['name']}: SHAP value {f['shap_value']:+.1f} ({sign})")
    features_block = "\n".join(feat_lines) if feat_lines else "  - (no feature attributions available)"
    
    system = (
        "You are an explainability assistant for an enterprise cashflow forecasting model. "
        "The forecast comes from an AutoTS UnivariateMotif model. SHAP values come from a "
        "RandomForest surrogate trained to mimic the forecaster on training-window data. "
        "Always phrase drivers as 'consistent with...' not 'because of...'. "
        "Output: 4-5 sentences. Cover (1) the forecast value in plain English, "
        "(2) which features the prediction is most consistent with, "
        "(3) confidence/risk caveat acknowledging the surrogate, "
        "(4) one suggested action a CFO might take."
    )
    user = (
        f"Company {company_code}: predicted next-day net cashflow = {forecast:,.0f}.\n"
        f"Nearest matching historical window: {nearest_window.get('txn_date', 'unknown')}, "
        f"actual that day = {nearest_window.get('actual', 0):,.0f}.\n"
        f"Top SHAP feature attributions (from surrogate):\n{features_block}\n\n"
        f"Write the explanation."
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def call_gpt4o(messages: list[dict[str, str]]) -> str:
    """Call GPT-4o via SAP GenAI Hub SDK."""
    if not GPT4O_DEPLOYMENT_ID:
        raise RuntimeError("GPT4O_DEPLOYMENT_ID not set")
    from gen_ai_hub.proxy.native.openai import chat
    log.info("calling GPT-4o deployment %s", GPT4O_DEPLOYMENT_ID)
    response = chat.completions.create(
        deployment_id=GPT4O_DEPLOYMENT_ID,
        messages=messages,
        max_tokens=400,
        temperature=0.3,
    )
    return response.choices[0].message.content


# ---- FastAPI ----
app = FastAPI(title="Cashflow Forecast Explainer", version="0.1.0")


@app.on_event("startup")
def on_startup() -> None:
    load_summaries()
    log.info("ready: companies=%s, predict_urls=%s, gpt4o=%s",
             list(SUMMARIES.keys()),
             list(PREDICT_URLS.keys()),
             "set" if GPT4O_DEPLOYMENT_ID else "MISSING")


class ExplainRequest(BaseModel):
    company_code: str


@app.get("/v2/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/v2/info")
def info() -> dict[str, Any]:
    return {
        "service": "cashflow-explainer",
        "version": "0.1.0",
        "companies_served": list(SUMMARIES.keys()),
        "predict_urls_configured": list(PREDICT_URLS.keys()),
        "gpt4o_deployment_set": bool(GPT4O_DEPLOYMENT_ID),
        "feature_names": SUMMARIES.get(next(iter(SUMMARIES), ""), {}).get("feature_names", []),
        "surrogate_caveat": (
            "SHAP values explain a RandomForest surrogate that mimics the production "
            "AutoTS UnivariateMotif forecaster. Phrasings are 'consistent with', not 'because of'."
        ),
    }


@app.post("/v2/explain")
def explain(req: ExplainRequest) -> dict[str, Any]:
    company = req.company_code
    if company not in SUMMARIES:
        raise HTTPException(status_code=404, detail=f"No SHAP summary for company {company}")
    if company not in PREDICT_URLS:
        raise HTTPException(status_code=404, detail=f"No predict URL for company {company}")

    try:
        prediction = call_predict(company)
    except Exception as e:
        log.exception("predict call failed")
        raise HTTPException(status_code=502, detail=f"Predict call failed: {e}")

    forecast_list = prediction.get("forecast", [])
    if not forecast_list:
        raise HTTPException(status_code=502, detail="No forecast points returned from /v2/predict")
    forecast_value = float(forecast_list[0].get("forecast", 0))
    forecast_date = forecast_list[0].get("date", "unknown")

    summary = SUMMARIES[company]
    last_window = summary["windows"][-1]
    nearest = find_nearest_window(summary, last_window["feature_vector"])

    messages = build_prompt(company, forecast_value, nearest)
    try:
        narrative = call_gpt4o(messages)
    except Exception as e:
        log.exception("GPT-4o call failed")
        raise HTTPException(status_code=502, detail=f"LLM call failed: {e}")

    return {
        "company_code": company,
        "forecast": forecast_value,
        "forecast_date": forecast_date,
        "best_model": prediction.get("best_model"),
        "nearest_window": {
            "date": nearest.get("txn_date"),
            "actual": nearest.get("actual"),
            "predicted": nearest.get("predicted"),
        },
        "top_features": nearest.get("top_features", []),
        "narrative": narrative,
        "surrogate_caveat": (
            "Explanation derived from a RandomForest surrogate trained to mimic the "
            "AutoTS UnivariateMotif forecaster. Treat as approximation, not direct decomposition."
        ),
    }
