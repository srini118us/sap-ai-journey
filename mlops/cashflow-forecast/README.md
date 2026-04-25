# Cashflow Forecast ML Pipeline

## Overview
Machine learning pipeline for cashflow forecasting using SAP data.

## Structure
- `src/` - Training scripts and dependencies
- `data/` - Sample cashflow data
- `workflows/` - Argo WorkflowTemplates

## Usage
```bash
# Training
python src/train.py

# Build Docker image
docker build -t cashflow-forecast src/
```

## Requirements
- Python 3.9+
- SAP HANA connection
- ML dependencies (see requirements.txt)

## TODO
- [ ] Implement training script
- [ ] Add data preprocessing
- [ ] Configure Argo workflows
- [ ] Add model evaluation
