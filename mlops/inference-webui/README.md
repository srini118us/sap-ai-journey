# Inference Web UI

## Scope

Browser-based interface for interacting with SAP AI Core model deployments. This lab includes a Node.js proxy server that handles OAuth authentication and CORS, enabling frontend applications to call AI Core inference endpoints securely.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     INFERENCE WEB UI                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌─────────────┐         ┌─────────────┐         ┌───────────┐ │
│   │   Browser   │  HTTP   │   Node.js   │  HTTPS  │  SAP AI   │ │
│   │             │ ──────► │   Proxy     │ ──────► │   Core    │ │
│   │ index.html  │         │  server.js  │         │           │ │
│   └─────────────┘         └─────────────┘         └───────────┘ │
│         │                       │                       │       │
│         │                       │                       │       │
│   Customer data           OAuth token             Prediction    │
│   (JSON payload)          caching                 response      │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   WHY PROXY IS NEEDED:                                          │
│                                                                  │
│   1. OAuth requires client_secret                               │
│      └─► Cannot expose secrets in browser JavaScript            │
│                                                                  │
│   2. CORS restrictions                                          │
│      └─► Browser blocks cross-origin requests to AI Core        │
│                                                                  │
│   3. Token management                                           │
│      └─► Server caches token, handles refresh                   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Components

### Server Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Serves index.html (Web UI) |
| `/predict` | POST | Forwards prediction to AI Core |
| `/health` | GET | Checks model deployment health |
| `/info` | GET | Returns server configuration |

### OAuth Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                     TOKEN MANAGEMENT                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   1. Check Cache                                                 │
│      │                                                           │
│      ├─► Token valid? ────► Use cached token                    │
│      │                                                           │
│      └─► Token expired/missing                                  │
│              │                                                   │
│              ▼                                                   │
│   2. Request New Token                                          │
│      POST {AUTH_URL}/oauth/token                                │
│      │                                                           │
│      │  grant_type: client_credentials                          │
│      │  client_id: {CLIENT_ID}                                  │
│      │  client_secret: {CLIENT_SECRET}                          │
│      │                                                           │
│      ▼                                                           │
│   3. Cache Token                                                │
│      │                                                           │
│      │  cachedToken = access_token                              │
│      │  tokenExpiry = now + expires_in - 5min buffer            │
│      │                                                           │
│      ▼                                                           │
│   4. Use Token                                                  │
│      Authorization: Bearer {token}                              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Configuration

The server requires SAP BTP service key credentials:

```javascript
const CONFIG = {
    // OAuth credentials
    CLIENT_ID: 'sb-xxx|aicore!b164',
    CLIENT_SECRET: 'xxx$xxx',
    
    // URLs
    AUTH_URL: 'https://{subdomain}.authentication.{region}.hana.ondemand.com',
    AI_API_URL: 'https://api.ai.prod.{region}.aws.ml.hana.ondemand.com',
    
    // Deployment
    DEPLOYMENT_ID: 'dxxxxxxxxx',
    RESOURCE_GROUP: 'default'
};
```

### Getting Credentials

1. Open SAP BTP Cockpit
2. Navigate to AI Core service instance
3. Create or view service key
4. Extract: `clientid`, `clientsecret`, `url`, `serviceurls.AI_API_URL`

## API Reference

### POST /predict

**Request:**
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

**Response:**
```json
{
    "predictions": [
        {
            "churn_prediction": 0,
            "churn_probability": 0.31,
            "risk_level": "Medium"
        }
    ],
    "model_version": "1.0.0"
}
```

### GET /health

**Response:**
```json
{
    "proxy": "healthy",
    "model": {
        "status": "RUNNING"
    }
}
```

### GET /info

**Response:**
```json
{
    "name": "SAP AI Core Proxy Server",
    "version": "1.0.0",
    "deployment_id": "dxxxxxxxxx",
    "endpoints": {
        "predict": "POST /predict",
        "health": "GET /health",
        "info": "GET /info"
    }
}
```

## Quick Start

### Prerequisites

- Node.js 18+
- SAP AI Core service key
- Deployed model in AI Core

### Installation

```bash
cd mlops/inference-webui
npm install
```

### Configuration

Edit `server.js` and update the CONFIG object with service key values.

### Run

```bash
npm start
# or
node server.js
```

### Access

Open browser: http://localhost:3000

## Files

```
inference-webui/
├── README.md           # This file
├── index.html          # Web UI (HTML/CSS/JavaScript)
├── server.js           # Node.js proxy server
└── package.json        # Dependencies
```

| File | Purpose |
|------|---------|
| `server.js` | Express server with OAuth, prediction proxy |
| `index.html` | Frontend form for entering customer data |
| `package.json` | Dependencies: express, cors, node-fetch |

## Dependencies

```json
{
    "express": "^4.x",
    "cors": "^2.x",
    "node-fetch": "^2.x"
}
```

## Error Handling

| Error | Cause | Solution |
|-------|-------|----------|
| `ECONNREFUSED` | Server not running | Start with `npm start` |
| `401 Unauthorized` | Invalid credentials | Check CLIENT_ID/SECRET |
| `404 Not Found` | Wrong deployment ID | Verify DEPLOYMENT_ID |
| `CORS error` | Direct browser call | Use proxy server |
| `Token expired` | Cache issue | Server auto-refreshes |

## Security Considerations

| Item | Implementation |
|------|----------------|
| Credentials | Server-side only, never in browser |
| Token Caching | 5-minute buffer before expiry |
| CORS | Proxy handles cross-origin |
| HTTPS | AI Core API uses TLS |

## Key Concepts

| Concept | Description |
|---------|-------------|
| OAuth 2.0 Client Credentials | Machine-to-machine authentication |
| Resource Group | AI Core tenant isolation |
| Deployment ID | Unique identifier for model deployment |
| Inference Endpoint | `/v2/inference/deployments/{id}/v2/predict` |

## Integration Points

| Integrates With | Purpose |
|-----------------|---------|
| AI Core Deployment | Model inference |
| XSUAA | OAuth token service |
| AI Launchpad | Deployment management |

## Reference

- [AI Core Inference](https://help.sap.com/docs/sap-ai-core/sap-ai-core-service-guide/consume-model)
- [Service Keys](https://help.sap.com/docs/btp/sap-business-technology-platform/creating-service-keys)
- [Express.js](https://expressjs.com/)
