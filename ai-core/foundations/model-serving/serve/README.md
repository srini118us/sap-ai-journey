# Lab 4: Model Serving with KServe

Deploy the trained churn prediction model as a REST API using SAP AI Core.

## 📁 Structure

```
model-serving/
├── serve/
│   ├── inference.py      # FastAPI inference server
│   ├── requirements.txt  # Python dependencies
│   └── Dockerfile        # Container definition
├── workflows/
│   └── serving-template.yaml  # SAP AI Core serving template
└── README.md
```

## 🚀 Deployment Steps

### 1. Build Docker Image
```bash
cd model-serving/serve
docker build -t srini117us/churn-serving:v1 .
```

### 2. Push to Docker Hub
```bash
docker push srini117us/churn-serving:v1
```

### 3. Push Template to GitHub
```bash
git add .
git commit -m "Add model serving template"
git push
```

### 4. Sync in AI Core
- Go to AI Core Launchpad → Applications
- Sync the GitHub repository

### 5. Create Configuration
Create a configuration linking:
- Scenario: `churn-serving`
- Executable: `churn-server`
- Input Artifact: `churnmodel` (from training)

### 6. Create Deployment
Deploy using the configuration.

## 🔌 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v2/health` | GET | Health check |
| `/v2/predict` | POST | Batch predictions |
| `/v2/predict/single` | POST | Single prediction |

### Example Request
```json
POST /v2/predict
{
  "customers": [
    {
      "monthly_spend": 85.50,
      "tenure_months": 24,
      "support_tickets": 2,
      "contract_type": "annual"
    }
  ]
}
```

### Example Response
```json
{
  "predictions": [
    {
      "churn_prediction": 0,
      "churn_probability": 0.15,
      "risk_level": "Low"
    }
  ],
  "model_version": "1.0.0",
  "features_used": ["monthly_spend", "tenure_months", "support_tickets", "contract_type"]
}
```

## ✅ Prerequisites
- Trained model artifact (`churnmodel`) in S3
- Docker Hub account (srini117us)
- GitHub repo synced with AI Core
