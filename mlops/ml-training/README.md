# ML Training Pipeline

## Scope

End-to-end ML training pipeline deployed on SAP AI Core using Argo Workflows. This lab trains a customer churn prediction model using RandomForest, demonstrating the complete workflow from data ingestion to model artifact output.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                 SAP AI CORE TRAINING PIPELINE                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │                    OBJECT STORE (S3)                     │   │
│   │                                                          │   │
│   │   /data/customer_churn.csv                               │   │
│   │                                                          │   │
│   └────────────────────────┬────────────────────────────────┘   │
│                            │                                     │
│                            ▼ Input Artifact                      │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │                  ARGO WORKFLOW TEMPLATE                  │   │
│   │                  (churn-model-training)                  │   │
│   │                                                          │   │
│   │   ┌─────────────────────────────────────────────────┐   │   │
│   │   │              training-template                   │   │   │
│   │   │                                                  │   │   │
│   │   │  1. Install Dependencies                         │   │   │
│   │   │     pip install pandas scikit-learn joblib       │   │   │
│   │   │                                                  │   │   │
│   │   │  2. Load Training Data                           │   │   │
│   │   │     df = pd.read_csv('/app/data/...')            │   │   │
│   │   │                                                  │   │   │
│   │   │  3. Feature Engineering                          │   │   │
│   │   │     contract_type → contract_numeric             │   │   │
│   │   │                                                  │   │   │
│   │   │  4. Train RandomForest                           │   │   │
│   │   │     n_estimators=100, max_depth=5                │   │   │
│   │   │                                                  │   │   │
│   │   │  5. Evaluate Model                               │   │   │
│   │   │     accuracy, classification_report              │   │   │
│   │   │                                                  │   │   │
│   │   │  6. Save Artifacts                               │   │   │
│   │   │     churn_model.pkl, metrics.json                │   │   │
│   │   │                                                  │   │   │
│   │   └─────────────────────────────────────────────────┘   │   │
│   │                                                          │   │
│   └────────────────────────┬────────────────────────────────┘   │
│                            │                                     │
│                            ▼ Output Artifact                     │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │                    OBJECT STORE (S3)                     │   │
│   │                                                          │   │
│   │   /models/churn_model.pkl                                │   │
│   │   /models/metrics.json                                   │   │
│   │                                                          │   │
│   └─────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Workflow Specification

### Metadata

| Field | Value |
|-------|-------|
| Name | `churn-model-training` |
| Scenario | `ml-training` |
| Executable | `churn-trainer` |
| Version | `1.0.2` |
| Container | `python:3.9-slim` |

### Artifacts

| Artifact | Type | Path | Description |
|----------|------|------|-------------|
| `trainingdata` | Input | `/app/data/` | CSV dataset |
| `trainedmodel` | Output | `/tmp/model/` | Model + metrics |

## Pipeline Steps

| Step | Input | Output | Details |
|------|-------|--------|---------|
| Install | - | Dependencies | pandas, scikit-learn, joblib |
| Load | `/app/data/customer_churn.csv` | DataFrame | Validate shape, check distribution |
| Preprocess | Raw columns | Features | Map `contract_type` to numeric |
| Split | Features, Target | Train/Test | 70/30 split, random_state=42 |
| Train | X_train, y_train | Model | RandomForest (100 trees, depth 5) |
| Evaluate | X_test, y_test | Metrics | Accuracy, classification report |
| Save | Model, Metrics | Files | `.pkl` and `.json` |

## Features

| Feature | Type | Description |
|---------|------|-------------|
| `monthly_spend` | Numeric | Customer spending per month |
| `tenure_months` | Numeric | How long customer has been active |
| `support_tickets` | Numeric | Number of support requests |
| `contract_numeric` | Encoded | 0=monthly, 1=annual |

**Target**: `churned` (0=stayed, 1=left)

## Model Configuration

```python
RandomForestClassifier(
    n_estimators=100,    # Number of trees
    max_depth=5,         # Limit tree depth
    random_state=42      # Reproducibility
)
```

## Output Artifacts

### churn_model.pkl
Serialized scikit-learn model using joblib.

### metrics.json
```json
{
  "accuracy": 0.85,
  "features": ["monthly_spend", "tenure_months", "support_tickets", "contract_numeric"],
  "model_type": "RandomForestClassifier"
}
```

## Quick Start

### Deploy to AI Core

1. Sync workflow to AI Core via GitHub repository
2. Create configuration with input artifact binding
3. Create execution to trigger training
4. Monitor in AI Launchpad

### Local Testing

```bash
# Simulate the training logic locally
cd mlops/ml-training

# The workflow runs inside AI Core, but the Python logic can be extracted
# and tested with local data
```

## Files

```
ml-training/
├── README.md                    # This file
└── workflows/
    └── train-model.yaml         # Argo WorkflowTemplate
```

| File | Purpose |
|------|---------|
| `train-model.yaml` | Argo workflow with embedded Python training script |

## Workflow YAML Structure

```yaml
apiVersion: argoproj.io/v1alpha1
kind: WorkflowTemplate
metadata:
  name: churn-model-training
  annotations:
    scenarios.ai.sap.com/name: "ml-training"
    executables.ai.sap.com/name: "churn-trainer"
spec:
  entrypoint: main
  templates:
    - name: main
      steps:
        - - name: train-model
            template: training-template
    - name: training-template
      inputs:
        artifacts:
          - name: trainingdata
            path: /app/data/
      outputs:
        artifacts:
          - name: trainedmodel
            path: /tmp/model/
      container:
        image: python:3.9-slim
        command: ["/bin/sh", "-c"]
        args:
          - |
            # Install, train, save
```

## Key Concepts

| Concept | Description |
|---------|-------------|
| WorkflowTemplate | Reusable Argo template registered with AI Core |
| Input Artifact | Data pulled from Object Store before execution |
| Output Artifact | Files pushed to Object Store after execution |
| Scenario | Logical grouping of related workflows |
| Executable | Specific runnable workflow within a scenario |
| Configuration | Runtime binding of artifacts and parameters |

## Integration Points

| Integrates With | Purpose |
|-----------------|---------|
| Object Store (S3/GCS) | Training data input, model output |
| AI Launchpad | Execution monitoring |
| Inference Deployment | Deploy trained model |
| Metrics API | Log training metrics |

## Reference

- [AI Core Training](https://help.sap.com/docs/sap-ai-core/sap-ai-core-service-guide/train-model)
- [Argo Workflows](https://argoproj.github.io/argo-workflows/)
- [Object Store Setup](https://help.sap.com/docs/sap-ai-core/sap-ai-core-service-guide/register-object-store-secret)
