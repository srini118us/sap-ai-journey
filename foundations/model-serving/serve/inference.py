"""
Customer Churn Prediction - Inference Server
SAP AI Core Model Serving with FastAPI
"""

import os
import json
import logging
from typing import List, Optional
from contextlib import asynccontextmanager

import joblib
import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Model storage
model = None
model_info = None


class CustomerFeatures(BaseModel):
    """Input features for churn prediction"""
    monthly_spend: float = Field(..., description="Monthly spending amount", ge=0)
    tenure_months: int = Field(..., description="Customer tenure in months", ge=0)
    support_tickets: int = Field(..., description="Number of support tickets", ge=0)
    contract_type: str = Field(..., description="Contract type: 'monthly' or 'annual'")

    class Config:
        json_schema_extra = {
            "example": {
                "monthly_spend": 85.50,
                "tenure_months": 24,
                "support_tickets": 2,
                "contract_type": "annual"
            }
        }


class PredictionRequest(BaseModel):
    """Batch prediction request"""
    customers: List[CustomerFeatures]


class PredictionResult(BaseModel):
    """Single prediction result"""
    churn_prediction: int = Field(..., description="0=Stay, 1=Churn")
    churn_probability: float = Field(..., description="Probability of churn")
    risk_level: str = Field(..., description="Low/Medium/High risk")


class PredictionResponse(BaseModel):
    """Prediction response"""
    predictions: List[PredictionResult]
    model_version: str
    features_used: List[str]


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    model_loaded: bool
    model_type: Optional[str] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load model on startup"""
    global model, model_info
    
    # Model path - SAP AI Core mounts artifacts here
    model_path = os.environ.get("MODEL_PATH", "/mnt/models")
    model_file = os.path.join(model_path, "churn_model.pkl")
    metrics_file = os.path.join(model_path, "metrics.json")
    
    logger.info(f"Loading model from: {model_file}")
    
    try:
        # List directory contents for debugging
        if os.path.exists(model_path):
            logger.info(f"Model directory contents: {os.listdir(model_path)}")
        
        # Load the trained model
        model = joblib.load(model_file)
        logger.info("Model loaded successfully!")
        
        # Load metrics if available
        if os.path.exists(metrics_file):
            with open(metrics_file, 'r') as f:
                model_info = json.load(f)
            logger.info(f"Model info: {model_info}")
        else:
            model_info = {"model_type": "RandomForestClassifier", "features": []}
            
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        raise RuntimeError(f"Model loading failed: {e}")
    
    yield
    
    logger.info("Shutting down inference server")


# Create FastAPI app
app = FastAPI(
    title="Customer Churn Prediction API",
    description="SAP AI Core Model Serving - Predict customer churn probability",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/health", response_model=HealthResponse)
@app.get("/v2/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint for AI Core"""
    return HealthResponse(
        status="healthy" if model is not None else "unhealthy",
        model_loaded=model is not None,
        model_type=model_info.get("model_type") if model_info else None
    )


@app.get("/v2/ready")
async def readiness_check():
    """Readiness probe for Kubernetes"""
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    return {"status": "ready"}


@app.get("/v2/live")
async def liveness_check():
    """Liveness probe for Kubernetes"""
    return {"status": "alive"}


def prepare_features(customer: CustomerFeatures) -> np.ndarray:
    """Convert customer features to model input format"""
    contract_numeric = 0 if customer.contract_type.lower() == "monthly" else 1
    
    return np.array([[
        customer.monthly_spend,
        customer.tenure_months,
        customer.support_tickets,
        contract_numeric
    ]])


def get_risk_level(probability: float) -> str:
    """Categorize churn risk"""
    if probability < 0.3:
        return "Low"
    elif probability < 0.7:
        return "Medium"
    else:
        return "High"


@app.post("/v2/predict", response_model=PredictionResponse)
async def predict(request: PredictionRequest):
    """
    Predict churn for one or more customers
    
    Returns prediction (0/1), probability, and risk level for each customer
    """
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    predictions = []
    
    for customer in request.customers:
        try:
            # Prepare features
            features = prepare_features(customer)
            
            # Get prediction and probability
            prediction = int(model.predict(features)[0])
            probabilities = model.predict_proba(features)[0]
            churn_prob = float(probabilities[1])  # Probability of class 1 (churn)
            
            predictions.append(PredictionResult(
                churn_prediction=prediction,
                churn_probability=round(churn_prob, 4),
                risk_level=get_risk_level(churn_prob)
            ))
            
        except Exception as e:
            logger.error(f"Prediction error: {e}")
            raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")
    
    return PredictionResponse(
        predictions=predictions,
        model_version="1.0.0",
        features_used=["monthly_spend", "tenure_months", "support_tickets", "contract_type"]
    )


@app.post("/v2/predict/single", response_model=PredictionResult)
async def predict_single(customer: CustomerFeatures):
    """
    Predict churn for a single customer (convenience endpoint)
    """
    request = PredictionRequest(customers=[customer])
    response = await predict(request)
    return response.predictions[0]


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
