# Cashflow Forecasting Pipeline

End-to-end ML training pipeline on SAP AI Core for financial cashflow forecasting. Demonstrates Argo workflow orchestration, custom Docker images, and HANA Cloud integration.

## Status

- [x] UC2.3: HANA + AutoTS training (live data)
- [x] UC2.4: Inference serving container
- [x] UC2.5: Recurring training pipeline
- [x] UC2.5: Model promotion workflow
- [ ] AI Core Application registered
- [ ] Full end-to-end execution

## Project Structure

```
sap-ai-journey/mlops/cashflow-forecast/
├── src/                                # UC2.3 + UC2.5 training
│   ├── train.py                        # AutoTS training script
│   ├── insert_synthetic.py             # Synthetic data insertion
│   ├── Dockerfile                      # Training container
│   └── requirements.txt                # Training dependencies
├── serving/                            # UC2.4 inference
│   ├── app.py                          # FastAPI inference server
│   ├── Dockerfile                      # Serving container
│   ├── requirements.txt                # Serving dependencies
│   ├── test_local.sh                   # Local testing
│   └── test_deployed.py                # Deployment testing
├── promote/                            # UC2.5 model promotion
│   ├── promote.py                      # Model promotion script
│   ├── Dockerfile                      # Promotion container
│   └── requirements.txt                # Promotion dependencies
├── workflows/
│   ├── train-template.yaml             # UC2.3 single training
│   ├── train-recurring-template.yaml   # UC2.5 recurring training
│   ├── serving-template.yaml           # UC2.4 inference
│   └── promote-template.yaml           # UC2.5 model promotion
└── data/
    └── cashflow_sample.csv             # Sample data (legacy)
```

## UC2.3 - Training (HANA + AutoTS)
- Live SAP HANA Cloud data from `PROC_AI.CASHFLOW_DAILY`
- AutoTS time series forecasting per company
- Multi-company support (1710, 1010)
- Model artifacts uploaded to S3

## UC2.4 - Inference (FastAPI)
- RESTful API endpoints for cashflow predictions
- Model loading from S3 artifacts
- Health check and metadata endpoints
- Docker containerized for AI Core

## UC2.5 - Recurring & Promotion
- **Recurring Training**: Synthetic data insertion + AutoTS retraining
- **Model Promotion**: Staging → Production deployment workflow
- Argo DAG orchestration with dependency management
- Automated model lifecycle management

## Architecture

Sits alongside `aicore-metrics/`, `ml-training/`, `inference-webui/`, and `payment-risk/` as Lab 5 in the MLOps series. See `../README.md` for the full lifecycle context.