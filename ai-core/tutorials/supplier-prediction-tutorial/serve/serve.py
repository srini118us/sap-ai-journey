"""
FastAPI inference server for supplier on-time delivery prediction.

Loads the trained XGBoost model from the AI Core mounted volume at startup.
Exposes /predict endpoint that accepts vendor + PO features as JSON,
returns probability of on-time delivery plus contributing factors.

Standard SAP AI Core serving pattern:
- Model artifact mounted at /mnt/models/ (AI Core convention)
- HTTP server listens on port 9001 (AI Core convention)
- /v1/models/<model-name>:predict for KServe compatibility
- /v2/predict for custom predict endpoint
- /healthz for liveness check
"""

import json
import os
import pickle
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import xgboost as xgb
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


# AI Core convention paths
MODEL_DIR = os.environ.get("MODEL_DIR", "/mnt/models")
MODEL_NAME = os.environ.get("MODEL_NAME", "supplier-prediction")

# Global model artifacts (loaded at startup)
model = None
encoders = None
feature_names = None
metrics = None


def load_model_artifacts():
    """Load model and metadata from mounted volume."""
    global model, encoders, feature_names, metrics
    
    model_dir = Path(MODEL_DIR)
    print(f"Loading model artifacts from: {model_dir}")
    print(f"Contents: {list(model_dir.iterdir()) if model_dir.exists() else 'directory missing'}")
    
    # Load XGBoost model
    model_path = model_dir / "model.json"
    if model_path.exists():
        model = xgb.XGBClassifier()
        model.load_model(str(model_path))
        print(f"  Loaded model from {model_path}")
    else:
        # Fallback to pickle
        pickle_path = model_dir / "model.pkl"
        if pickle_path.exists():
            with open(pickle_path, "rb") as f:
                model = pickle.load(f)
            print(f"  Loaded model from {pickle_path}")
        else:
            raise FileNotFoundError(
                f"Model file not found at {model_path} or {pickle_path}"
            )
    
    # Load encoders
    encoders_path = model_dir / "encoders.json"
    if encoders_path.exists():
        with open(encoders_path, "r") as f:
            encoders = json.load(f)
        print(f"  Loaded encoders: {list(encoders.keys())}")
    else:
        encoders = {}
    
    # Load feature names
    features_path = model_dir / "feature_names.json"
    if features_path.exists():
        with open(features_path, "r") as f:
            feature_names = json.load(f)
        print(f"  Loaded {len(feature_names)} feature names")
    else:
        raise FileNotFoundError(f"Feature names not found at {features_path}")
    
    # Load metrics (for reporting via /metrics endpoint)
    metrics_path = model_dir / "metrics.json"
    if metrics_path.exists():
        with open(metrics_path, "r") as f:
            metrics = json.load(f)
        print(f"  Loaded metrics: accuracy={metrics.get('accuracy')}")
    
    print("Model loading complete")


# Pydantic models for request/response

class PredictionRequest(BaseModel):
    """Single PO prediction request."""
    vendor_category: str = Field(..., description="RAW, PACK, FINISH, or SERVICE")
    vendor_country: str = Field(..., description="US, DE, CN, IN, or MX")
    historical_ontime_rate: float = Field(..., ge=0.0, le=1.0)
    avg_lead_time_days: float = Field(..., gt=0)
    lead_time_variance: float = Field(..., ge=0)
    po_count_last_quarter: int = Field(..., ge=0)
    po_amount: float = Field(..., gt=0)
    concurrent_pos: int = Field(..., ge=0)
    material_complexity: int = Field(..., ge=1, le=5)
    expected_lead_time_days: float = Field(..., gt=0)
    delivery_day_of_week: int = Field(..., ge=0, le=6, description="0=Mon, 6=Sun")
    is_quarter_end: int = Field(..., ge=0, le=1)
    is_peak_season: int = Field(..., ge=0, le=1)


class PredictionResponse(BaseModel):
    """Prediction response with probability and explanation."""
    on_time_probability: float
    late_probability: float
    prediction: str  # "ON_TIME" or "LATE"
    confidence: str  # "HIGH", "MEDIUM", "LOW"
    top_factors: list[dict]


# FastAPI app

app = FastAPI(
    title="Supplier On-time Delivery Prediction",
    description="XGBoost-based prediction of supplier delivery on-time probability",
    version="1.0.0",
)


@app.on_event("startup")
async def startup():
    """Load model when the server starts."""
    try:
        load_model_artifacts()
        print("Server ready to accept requests")
    except Exception as e:
        print(f"FAILED to load model: {e}")
        raise


@app.get("/healthz")
def healthcheck():
    """AI Core uses this for liveness probe."""
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    return {"status": "ok", "model_loaded": True}


@app.get("/")
def root():
    """Basic info endpoint."""
    return {
        "service": "supplier-prediction",
        "version": "1.0",
        "model_name": MODEL_NAME,
        "endpoints": ["/healthz", "/v2/predict", "/v2/metrics"],
    }


@app.get("/v2/metrics")
def get_metrics():
    """Return model training metrics."""
    if metrics is None:
        return {"message": "Metrics not available"}
    return metrics


def encode_categorical(value: str, encoder_classes: list) -> int:
    """Convert categorical string to integer using saved encoder classes."""
    try:
        return encoder_classes.index(value)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown category: {value}. Valid: {encoder_classes}",
        )


def predict_with_explanation(features_dict: dict) -> PredictionResponse:
    """Run prediction and return result with top factor explanations."""
    
    # Encode categorical features using saved encoders
    encoded = features_dict.copy()
    encoded["vendor_category"] = encode_categorical(
        features_dict["vendor_category"],
        encoders["vendor_category"]["classes"],
    )
    encoded["vendor_country"] = encode_categorical(
        features_dict["vendor_country"],
        encoders["vendor_country"]["classes"],
    )
    
    # Build feature vector in the correct order
    X = np.array([[encoded[name] for name in feature_names]])
    
    # Predict probabilities
    proba = model.predict_proba(X)[0]
    late_prob = float(proba[0])
    ontime_prob = float(proba[1])
    
    # Determine prediction and confidence
    if ontime_prob > 0.7:
        prediction = "ON_TIME"
        confidence = "HIGH" if ontime_prob > 0.85 else "MEDIUM"
    elif ontime_prob < 0.3:
        prediction = "LATE"
        confidence = "HIGH" if ontime_prob < 0.15 else "MEDIUM"
    else:
        prediction = "ON_TIME" if ontime_prob > 0.5 else "LATE"
        confidence = "LOW"
    
    # Get top contributing features from XGBoost feature importance
    # (Note: this is global importance, not per-prediction.
    # True SHAP would be per-prediction but adds significant compute)
    importance = model.feature_importances_
    top_indices = np.argsort(importance)[::-1][:5]
    top_factors = [
        {
            "feature": feature_names[i],
            "importance": float(importance[i]),
            "value": float(X[0][i]),
        }
        for i in top_indices
    ]
    
    return PredictionResponse(
        on_time_probability=round(ontime_prob, 4),
        late_probability=round(late_prob, 4),
        prediction=prediction,
        confidence=confidence,
        top_factors=top_factors,
    )


@app.post("/v2/predict", response_model=PredictionResponse)
def predict(request: PredictionRequest):
    """
    Predict on-time delivery probability for a single PO.
    
    Returns probability score, prediction label, confidence level,
    and top contributing factors with their importance scores.
    """
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    features_dict = request.dict()
    return predict_with_explanation(features_dict)


@app.post("/v1/models/{model_name}:predict")
def predict_kserve(model_name: str, request: PredictionRequest):
    """KServe-compatible predict endpoint."""
    if model_name != MODEL_NAME:
        raise HTTPException(status_code=404, detail=f"Model {model_name} not found")
    return predict(request)
