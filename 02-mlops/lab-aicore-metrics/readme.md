# Lab: SAP AI Core Metrics API

## Overview

This lab demonstrates how to use the SAP AI Core Metrics API for logging training metrics, monitoring drift, and comparing models.

## Key Concepts

### SAP AI Core Metrics Components

| Component | Purpose | Example |
|-----------|---------|---------|
| `Metric` | Log numeric values | accuracy, loss, F1 |
| `MetricTag` | Metadata labels | model_type, stage |
| `MetricCustomInfo` | Store JSON/text | confusion matrix |
| `Tracking` | Client for logging | `Tracking()` |

### Methods

| Method | Description |
|--------|-------------|
| `log_metrics()` | Log one or more metrics |
| `set_tags()` | Set metadata tags |
| `modify()` | Batch update all |

## Important Notes

| Environment | Metrics Persistence |
|-------------|---------------------|
| Local | No (runs but doesn't save) |
| AI Core Execution | Yes (saves to AI Launchpad) |

## Quick Start

```bash
python sap_aicore_metrics_demo.py
```

## Comparison: SAP AI Core vs Vertex AI

| Feature | SAP AI Core | Vertex AI |
|---------|-------------|-----------|
| Metrics Logging | Manual (SDK) | Automatic |
| Drift Detection | Manual | Built-in |
| Visualization | AI Launchpad | Console |
| Model Comparison | Up to 5 models | Unlimited |

## Files

| File | Purpose |
|------|---------|
| `sap_aicore_metrics_demo.py` | Demo with mock SDK |
| `README.md` | This file |

## Author

Srinivasa Dasari - Solution Architect