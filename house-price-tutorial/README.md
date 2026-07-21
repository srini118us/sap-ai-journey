# House Price Tutorial (SAP AI Core)

A minimal, end-to-end **SAP AI Core** training example — the "hello world" of
running a model on AI Core. It trains a scikit-learn `DecisionTreeRegressor`
on the built-in California housing dataset and prints the test R² score to the
AI Core execution logs.

Adapted from the official SAP tutorial:
https://developers.sap.com/tutorials/ai-core-code.html

## Folder Structure

```
house-price-tutorial/
├── main.py                  # Training script (load data -> split -> train -> score)
├── Dockerfile               # python:3.11-slim image that runs main.py
├── house-price-train.yaml   # Argo WorkflowTemplate for AI Core
└── requirements.txt         # scikit-learn, numpy, pandas
```

## What It Does

`main.py`:
1. Loads the California housing dataset via `sklearn.datasets.fetch_california_housing()`
2. Splits it 70/30 into train/test
3. Trains a `DecisionTreeRegressor`
4. Prints the test R² score (`Test Data Score <value>`) to stdout

Note: as the tutorial states, printing the score to logs is not the recommended
way to report metrics in AI Core — it's kept simple on purpose.

## Build & Push Image

```bash
docker build -t docker.io/<your-repo>/house-price:01 .
docker push docker.io/<your-repo>/house-price:01
```

The workflow references `docker.io/srini117us/house-price:01` with image-pull
secret `docker-hub-srini117us` — update to your own registry as needed.

## Run on SAP AI Core

1. Sync `house-price-train.yaml` into your AI Core Git repo (scenario id
   `house-price-tutorial`, executable `house-price-train`).
2. Create a configuration for the executable.
3. Start an execution and view the R² score in the execution logs.

## Environment

The Dockerfile sets `SCIKIT_LEARN_DATA=/tmp/sklearn_data` and `HOME=/tmp` so the
dataset can be downloaded/cached at runtime inside the container.
