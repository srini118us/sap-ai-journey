# MLOps

## Scope

MLOps patterns for SAP AI Core covering the complete ML lifecycle: experiment tracking, model training, inference deployment, and foundation models. This section includes 4 labs demonstrating different aspects of operationalizing ML on SAP BTP.

## Use Cases

| # | Use Case | What It Demonstrates | Key Technology |
|---|----------|---------------------|----------------|
| 1 | [AI Core Metrics](./aicore-metrics/) | Experiment tracking, drift monitoring | AI Core Metrics API |
| 2 | [ML Training](./ml-training/) | End-to-end training pipeline | Argo Workflows |
| 3 | [Inference Web UI](./inference-webui/) | Web interface for model predictions | Node.js proxy + OAuth |
| 4 | [Payment Risk](./payment-risk/) | SAP-RPT-1 foundation model | CAP + RPT-1 API |

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      MLOps LIFECYCLE                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │                    EXPERIMENT PHASE                      │   │
│   │                                                          │   │
│   │   ┌───────────┐    ┌───────────┐    ┌───────────┐       │   │
│   │   │  Develop  │ →  │   Train   │ →  │  Evaluate │       │   │
│   │   │           │    │           │    │           │       │   │
│   │   │ Features  │    │ Workflows │    │  Metrics  │       │   │
│   │   └───────────┘    └───────────┘    └───────────┘       │   │
│   │                          │                               │   │
│   │                          ▼                               │   │
│   │                  ┌───────────────┐                       │   │
│   │                  │  AI Core      │                       │   │
│   │                  │  Metrics API  │ ← Lab 1: aicore-metrics│  │
│   │                  └───────────────┘                       │   │
│   │                                                          │   │
│   └──────────────────────────────────────────────────────────┘   │
│                          │                                       │
│   ┌──────────────────────┼──────────────────────────────────┐   │
│   │                      ▼                                   │   │
│   │              TRAINING PHASE                              │   │
│   │                                                          │   │
│   │   ┌───────────┐    ┌───────────┐    ┌───────────┐       │   │
│   │   │  Object   │ →  │   Argo    │ →  │   Model   │       │   │
│   │   │  Store    │    │ Workflow  │    │  Artifact │       │   │
│   │   │  (S3)     │    │           │    │  (.pkl)   │       │   │
│   │   └───────────┘    └───────────┘    └───────────┘       │   │
│   │                          │                               │   │
│   │                          └── Lab 2: ml-training          │   │
│   │                                                          │   │
│   └──────────────────────────────────────────────────────────┘   │
│                          │                                       │
│   ┌──────────────────────┼──────────────────────────────────┐   │
│   │                      ▼                                   │   │
│   │             DEPLOYMENT PHASE                             │   │
│   │                                                          │   │
│   │   ┌───────────┐    ┌───────────┐    ┌───────────┐       │   │
│   │   │  Model    │ →  │   AI Core │ →  │   Web UI  │       │   │
│   │   │ Registry  │    │  Deploy   │    │  (proxy)  │       │   │
│   │   └───────────┘    └───────────┘    └───────────┘       │   │
│   │                          │                               │   │
│   │                          └── Lab 3: inference-webui      │   │
│   │                                                          │   │
│   └──────────────────────────────────────────────────────────┘   │
│                          │                                       │
│   ┌──────────────────────┼──────────────────────────────────┐   │
│   │                      ▼                                   │   │
│   │            FOUNDATION MODELS                             │   │
│   │                                                          │   │
│   │   ┌───────────┐    ┌───────────┐    ┌───────────┐       │   │
│   │   │  Context  │ →  │  RPT-1    │ →  │ Prediction│       │   │
│   │   │  Rows     │    │  API      │    │  Results  │       │   │
│   │   │ (labeled) │    │           │    │           │       │   │
│   │   └───────────┘    └───────────┘    └───────────┘       │   │
│   │                          │                               │   │
│   │                          └── Lab 4: payment-risk         │   │
│   │                                                          │   │
│   └──────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Use Case Details

### Lab 1: AI Core Metrics

**Purpose**: Log training metrics, monitor drift, compare model executions.

**Key Classes**:
- `Metric` — Single measurement (name, value, step)
- `MetricTag` — Metadata label for filtering
- `MetricCustomInfo` — JSON reports (confusion matrix, feature importance)
- `Tracking` — Client for logging to AI Launchpad

**Important**: Metrics only persist when running inside AI Core execution environment. The demo includes a mock SDK for local development.

```python
from ai_core_sdk.tracking import Tracking
tracking = Tracking()
tracking.log_metrics([Metric(name="accuracy", value=0.94, step=5)])
```

---

### Lab 2: ML Training

**Purpose**: End-to-end training pipeline with Argo Workflows.

**Pipeline Steps**:
1. Load training data from Object Store
2. Feature engineering (encode categoricals)
3. Train RandomForest classifier
4. Evaluate (accuracy, classification report)
5. Save model artifact (.pkl) and metrics (.json)

**Model**: RandomForest (100 trees, max_depth=5) for customer churn prediction.

---

### Lab 3: Inference Web UI

**Purpose**: Browser interface for calling AI Core model deployments.

**Why Proxy Needed**:
- OAuth requires server-side client_secret
- Browser CORS blocks direct AI Core calls
- Token caching and refresh handling

**Endpoints**:
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/predict` | POST | Forward to AI Core |
| `/health` | GET | Check deployment status |
| `/info` | GET | Server configuration |

---

### Lab 4: Payment Risk (RPT-1)

**Purpose**: Demonstrate SAP's foundation model for tabular data.

**How It Works**:
1. Send historical FI-AR records with known `payment_risk` labels
2. Append new customer records with `payment_risk = "[PREDICT]"`
3. RPT-1 learns patterns and fills in predictions
4. No training required — in-context learning

**Comparison**:
| Traditional ML | RPT-1 |
|----------------|-------|
| Training required | None |
| Docker + Argo | API call |
| Hours/days setup | Minutes |

---

## Structure

```
mlops/
├── README.md                          # This file
├── aicore-metrics/
│   ├── readme.md
│   └── sap_aicore_metrics_demo.py     # Mock SDK + demo
├── ml-training/
│   ├── README.md
│   └── workflows/
│       └── train-model.yaml           # Argo WorkflowTemplate
├── inference-webui/
│   ├── README.md
│   ├── index.html                     # Web UI
│   ├── server.js                      # Node.js proxy
│   └── package.json
└── payment-risk/
    ├── README.md
    ├── app/                           # Dashboard UI
    ├── db/                            # Schema + sample data
    └── srv/
        └── cat-service.js             # RPT-1 integration
```

## Key Concepts

| Concept | Lab | Description |
|---------|-----|-------------|
| Metrics API | 1 | Log training metrics to AI Launchpad |
| Drift Detection | 1 | Monitor feature distribution changes |
| Argo Workflows | 2 | Kubernetes-native workflow engine |
| Input/Output Artifacts | 2 | Object Store integration |
| OAuth Proxy | 3 | Server-side token management |
| In-Context Learning | 4 | Few-shot prompting for tabular data |
| Foundation Model | 4 | Pre-trained model, no training needed |

## Technology Stack

| Technology | Used In | Purpose |
|------------|---------|---------|
| Python | Labs 1, 2 | Training, metrics |
| Argo Workflows | Lab 2 | Pipeline orchestration |
| Node.js / Express | Lab 3 | Proxy server |
| CAP (Node.js) | Lab 4 | Service layer |
| scikit-learn | Lab 2 | RandomForest classifier |
| RPT-1 API | Lab 4 | Foundation model inference |

## Comparison: SAP AI Core vs Alternatives

| Feature | SAP AI Core | Vertex AI | SageMaker |
|---------|-------------|-----------|-----------|
| Metrics | Manual SDK | Auto + Manual | Auto |
| Drift Detection | Manual | Built-in | Built-in |
| Workflows | Argo | Pipelines | Pipelines |
| Foundation Models | RPT-1 | Gemini | Bedrock |
| Visualization | AI Launchpad | Console | Studio |

## Prerequisites

| Lab | Requirements |
|-----|--------------|
| 1 | Python 3.9+ |
| 2 | AI Core with Object Store |
| 3 | Node.js 18+, AI Core deployment |
| 4 | Node.js 18+, CDS CLI, RPT-1 token |

## Reference

- [AI Core MLOps](https://help.sap.com/docs/sap-ai-core/sap-ai-core-service-guide/mlops)
- [AI Core Metrics](https://help.sap.com/docs/sap-ai-core/sap-ai-core-service-guide/metrics)
- [AI Core SDK](https://pypi.org/project/ai-core-sdk/)
- [SAP RPT-1](https://help.sap.com/docs/sap-ai-core/generative-ai/sap-rpt-1)
- [RPT-1 Playground](https://rpt.cloud.sap)
- [Argo Workflows](https://argoproj.github.io/argo-workflows/)
