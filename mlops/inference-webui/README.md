# Lab 5: Web UI for Churn Predictions

A simple web interface to interact with your SAP AI Core churn prediction model.

## Architecture

```
┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐
│   Browser       │  HTTP   │   Node.js       │  HTTPS  │   SAP AI Core   │
│   (index.html)  │ ──────► │   Proxy Server  │ ──────► │   (your model)  │
│                 │         │   (server.js)   │         │                 │
└─────────────────┘         └─────────────────┘         └─────────────────┘
        │                           │                           │
        │                           │                           │
   User enters              Handles OAuth              Returns prediction
   customer data            authentication             (churn/stay)
```

## Why a Proxy Server?

Browser JavaScript cannot directly call SAP AI Core because:
1. **OAuth requires client_secret** - Can't expose secrets in browser code
2. **CORS restrictions** - Cross-origin requests are blocked

The proxy server solves both issues by handling authentication server-side.

## Quick Start

### 1. Install Node.js
Download from: https://nodejs.org/

### 2. Setup Project
```bash
cd C:\sap-ai-journey\labs\lab5-web-ui
npm install
```

### 3. Start Server
```bash
npm start
```

### 4. Open Browser
Navigate to: http://localhost:3000

## Files

| File | Description |
|------|-------------|
| `index.html` | Frontend UI (HTML/CSS/JavaScript) |
| `server.js` | Proxy server (Node.js/Express) |
| `package.json` | Node.js dependencies |

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Serves the web UI |
| `/predict` | POST | Makes prediction request |
| `/health` | GET | Checks model health |
| `/info` | GET | Server information |

## Configuration

Edit `server.js` to update credentials:

```javascript
const CONFIG = {
    CLIENT_ID: 'your-client-id',
    CLIENT_SECRET: 'your-client-secret',
    AUTH_URL: 'https://your-auth-url.authentication.region.hana.ondemand.com',
    AI_API_URL: 'https://api.ai.prod.region.aws.ml.hana.ondemand.com',
    DEPLOYMENT_ID: 'your-deployment-id',
    RESOURCE_GROUP: 'default'
};
```

## Sample Request

```json
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

## Sample Response

```json
{
    "predictions": [
        {
            "churn_prediction": 0,
            "churn_probability": 0.31,
            "risk_level": "Medium"
        }
    ],
    "model_version": "1.0.0",
    "features_used": [
        "monthly_spend",
        "tenure_months",
        "support_tickets",
        "contract_type"
    ]
}
```

## Screenshots

(Add screenshots after running the app)

## Troubleshooting

| Error | Solution |
|-------|----------|
| `ECONNREFUSED` | Check if server is running |
| `401 Unauthorized` | Verify OAuth credentials |
| `404 Not Found` | Check deployment ID |
| `CORS error` | Make sure to use proxy server |

## Next Steps

- Deploy to SAP BTP (HTML5 Repository)
- Add batch prediction support
- Add prediction history
- Add export to CSV

---

*Lab 5 | SAP AI Core MLOps Series*
