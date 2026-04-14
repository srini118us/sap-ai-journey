# AI Core Metrics

## Scope

Demonstrates the SAP AI Core Metrics API for experiment tracking, model monitoring, and drift detection. This lab includes a mock SDK implementation that mirrors the production `ai_core_sdk` patterns, enabling local development and testing before deploying to AI Core.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                 SAP AI CORE METRICS FLOW                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │                  TRAINING EXECUTION                      │   │
│   │                                                          │   │
│   │   ┌───────────┐    ┌───────────┐    ┌───────────┐       │   │
│   │   │  Epoch 1  │ →  │  Epoch 2  │ →  │  Epoch N  │       │   │
│   │   │           │    │           │    │           │       │   │
│   │   │ loss: 0.85│    │ loss: 0.62│    │ loss: 0.22│       │   │
│   │   │ acc: 0.72 │    │ acc: 0.81 │    │ acc: 0.94 │       │   │
│   │   └─────┬─────┘    └─────┬─────┘    └─────┬─────┘       │   │
│   │         │                │                │              │   │
│   │         ▼                ▼                ▼              │   │
│   │   ┌─────────────────────────────────────────────┐       │   │
│   │   │           Tracking.log_metrics()            │       │   │
│   │   │                                             │       │   │
│   │   │  • Metric(name, value, timestamp, step)     │       │   │
│   │   │  • MetricTag(name, value)                   │       │   │
│   │   │  • MetricCustomInfo(name, json_value)       │       │   │
│   │   └─────────────────────┬───────────────────────┘       │   │
│   │                         │                                │   │
│   └─────────────────────────┼────────────────────────────────┘   │
│                             │                                    │
│                             ▼                                    │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │                 SAP AI LAUNCHPAD                         │   │
│   │                                                          │   │
│   │   ┌───────────┐  ┌───────────┐  ┌───────────┐           │   │
│   │   │  Metrics  │  │   Tags    │  │  Custom   │           │   │
│   │   │  Charts   │  │  Filters  │  │  Reports  │           │   │
│   │   └───────────┘  └───────────┘  └───────────┘           │   │
│   │                                                          │   │
│   │   Compare up to 5 model executions side-by-side          │   │
│   │                                                          │   │
│   └─────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Components

### SDK Classes

| Class | Purpose | Example |
|-------|---------|---------|
| `Metric` | Single measurement | `Metric(name="accuracy", value=0.94, step=5)` |
| `MetricTag` | Metadata label | `MetricTag(name="Model Type", value="XGBoost")` |
| `MetricCustomInfo` | JSON reports | Classification report, feature importance |
| `Tracking` | Client for logging | `Tracking().log_metrics([...])` |

### Tracking Methods

| Method | Description |
|--------|-------------|
| `log_metrics(metrics)` | Log one or more Metric objects |
| `set_tags(tags)` | Set metadata tags for filtering |
| `modify(tags, metrics, custom_info)` | Batch update all types |
| `get_summary()` | Local only - returns logged data |

## Flow

1. **Initialize Tracking** - Create `Tracking()` client (connects to AI Core in production)
2. **Set Tags** - Add metadata (model type, dataset, stage, version)
3. **Training Loop** - Log metrics per epoch with step number
4. **Final Metrics** - Log final accuracy, loss, duration
5. **Custom Info** - Store JSON reports (confusion matrix, feature importance)
6. **Drift Monitoring** - Log JS divergence scores per feature

## Drift Detection Pattern

SAP AI Core does not have built-in drift detection like Vertex AI. This lab demonstrates a manual approach:

```python
# Calculate Jensen-Shannon divergence per feature
drift_metrics = {
    "invoice_amount_js_divergence": 0.15,  # > 0.1 = DRIFT
    "vendor_risk_score_js_divergence": 0.08,  # OK
}

# Log to AI Launchpad for monitoring
tracking.log_metrics([
    Metric(name="max_drift_score", value=0.15),
    Metric(name="drift_detected", value=1.0)  # Boolean as float
])
```

## Quick Start

```bash
cd mlops/aicore-metrics
python sap_aicore_metrics_demo.py
```

Expected output:
- Training metrics logged per epoch
- Drift monitoring metrics
- Summary of all logged data
- Production code template

## Environment Behavior

| Environment | Metrics Persistence |
|-------------|---------------------|
| Local (this demo) | In-memory only, not saved |
| AI Core Execution | Persisted to AI Launchpad |

The mock SDK allows development and testing locally. When the same code runs inside an AI Core execution, metrics automatically persist.

## Production Code Pattern

```python
from datetime import datetime
from ai_core_sdk.tracking import Tracking
from ai_core_sdk.models import Metric, MetricTag, MetricCustomInfo

tracking = Tracking()

# Set metadata
tracking.set_tags(tags=[
    MetricTag(name="Model", value="ChurnPredictor"),
    MetricTag(name="Version", value="1.0.0"),
])

# Training loop
for epoch in range(num_epochs):
    # ... training code ...
    tracking.log_metrics(metrics=[
        Metric(name="loss", value=float(loss), step=epoch),
        Metric(name="accuracy", value=float(acc), step=epoch),
    ])

# Final metrics
tracking.log_metrics(metrics=[
    Metric(name="final_accuracy", value=0.94),
    Metric(name="training_duration_seconds", value=3600.0),
])

# Custom reports
tracking.modify(custom_info=[
    MetricCustomInfo(name="confusion_matrix", value=json.dumps(cm)),
    MetricCustomInfo(name="feature_importance", value=json.dumps(importance)),
])
```

## Files

```
aicore-metrics/
├── readme.md                      # This file
└── sap_aicore_metrics_demo.py     # Mock SDK + demonstration
```

| File | Lines | Purpose |
|------|-------|---------|
| `sap_aicore_metrics_demo.py` | ~280 | Mock SDK classes, training simulation, drift monitoring |

## Key Concepts

| Concept | Description |
|---------|-------------|
| Step-based Logging | Track metrics per epoch for training curves |
| Tags | Filter and group executions in AI Launchpad |
| Custom Info | Store arbitrary JSON (reports, matrices) |
| Drift Detection | Manual JS divergence calculation + alerting |
| Model Comparison | Compare up to 5 executions in AI Launchpad |

## Comparison: SAP AI Core vs Vertex AI

| Feature | SAP AI Core | Vertex AI |
|---------|-------------|-----------|
| Metrics Logging | Manual (SDK) | Automatic + Manual |
| Drift Detection | Manual implementation | Built-in |
| Visualization | AI Launchpad | Vertex Console |
| Model Comparison | Up to 5 models | Unlimited |
| Custom Reports | MetricCustomInfo | Metadata |

## Reference

- [AI Core Metrics API](https://help.sap.com/docs/sap-ai-core/sap-ai-core-service-guide/metrics)
- [AI Core SDK on PyPI](https://pypi.org/project/ai-core-sdk/)
- [AI Launchpad](https://help.sap.com/docs/ai-launchpad)
