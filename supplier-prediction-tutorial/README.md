# Supplier On-Time Delivery Prediction (SAP AI Core)

An end-to-end **SAP AI Core** tutorial that predicts whether a purchase order
will be delivered **on time** or **late**, using an XGBoost binary classifier
trained on synthetic procurement data. It covers the full lifecycle: data
generation, training (with metrics + feature importance), and a FastAPI serving
endpoint with explanations.

## Folder Structure

```
supplier-prediction-tutorial/
|-- data/
|   |-- generate_data.py         # Synthetic data generator (vendors + PO records)
|   `-- training_data.csv        # 10,000 generated PO records
|-- training/
|   |-- train.py                 # XGBoost training + evaluation + artifact save
|   |-- Dockerfile
|   `-- requirements.txt
|-- serving/
|   |-- serve.py                 # FastAPI inference server (/v2/predict, /healthz)
|   |-- Dockerfile
|   `-- requirements.txt
`-- supplier-prediction-train.yaml  # Argo WorkflowTemplate for AI Core
```

## 1. Data

`data/generate_data.py` creates realistic synthetic procurement data with
deliberate, learnable patterns (historical on-time rate is the strongest
signal; long lead times, Friday deliveries, high concurrent POs, quarter-end
and peak season all increase lateness), plus random noise.

- 100 vendors, 10,000 PO records -> `training_data.csv`
- Label: `on_time` (1 = on time, 0 = late)
- Features include vendor category/country, historical on-time rate, lead time
  and variance, PO amount, concurrent POs, material complexity, and calendar
  flags (day of week, quarter-end, peak season)

Regenerate:

```bash
cd data && python generate_data.py
```

## 2. Training

`training/train.py` label-encodes categorical columns, trains an XGBoost
classifier, and reports accuracy, AUC, confusion matrix, classification report,
and feature importance. It saves the following artifacts to `MODEL_OUTPUT_DIR`
(default `/app/model`):

- `model.json` and `model.pkl` — the trained model (native + pickle)
- `encoders.json` — label-encoder classes (needed at inference)
- `feature_names.json` — feature order (needed at inference)
- `metrics.json` — training metrics

Hyperparameters are configurable via env vars (`N_ESTIMATORS`, `MAX_DEPTH`,
`LEARNING_RATE`, `TEST_SIZE`); input path via `DATA_PATH`. In AI Core the
Object Store Secret mounts the S3 data at `/app/data/training_data.csv` and
collects outputs from `/app/model/`.

## 3. Serving

`serving/serve.py` is a FastAPI app that loads the model artifacts from
`/mnt/models` (AI Core convention) at startup and exposes:

- `POST /v2/predict` — custom endpoint; returns on-time/late probability,
  prediction label, confidence (HIGH/MEDIUM/LOW), and top contributing factors
- `POST /v1/models/{model_name}:predict` — KServe-compatible endpoint
- `GET /healthz` — liveness probe (used by AI Core)
- `GET /v2/metrics` — returns the saved training metrics
- `GET /` — service info

Request body is validated by a Pydantic schema (`vendor_category`,
`vendor_country`, `historical_ontime_rate`, `avg_lead_time_days`, etc.). The
server listens on port **9001**.

## Build & Push Images

```bash
docker build -t docker.io/<your-repo>/supplier-prediction-train:01 ./training
docker push docker.io/<your-repo>/supplier-prediction-train:01

docker build -t docker.io/<your-repo>/supplier-prediction-serve:01 ./serving
docker push docker.io/<your-repo>/supplier-prediction-serve:01
```

The training workflow references `docker.io/srini117us/supplier-prediction-train:01`
with image-pull secret `docker-hub-srini117us` — update to your registry.

## Run on SAP AI Core

1. Upload `training_data.csv` to your S3 bucket registered via an Object Store Secret.
2. Sync `supplier-prediction-train.yaml` into your AI Core Git repo (scenario id
   `supplier-prediction-tutorial`, executable `supplier-prediction-train`).
3. Run the training executable to produce the model artifact.
4. Deploy the serving image, mounting the trained artifact at `/mnt/models`.

## Example Prediction

```bash
curl -X POST http://localhost:9001/v2/predict \
  -H "Content-Type: application/json" \
  -d '{
    "vendor_category": "PACK", "vendor_country": "US",
    "historical_ontime_rate": 0.86, "avg_lead_time_days": 6.9,
    "lead_time_variance": 3.57, "po_count_last_quarter": 14,
    "po_amount": 26062.92, "concurrent_pos": 5, "material_complexity": 4,
    "expected_lead_time_days": 8.8, "delivery_day_of_week": 5,
    "is_quarter_end": 1, "is_peak_season": 1
  }'
```

## Note

The `top_factors` returned by `/v2/predict` use XGBoost **global** feature
importance, not per-prediction SHAP values (a deliberate trade-off to keep
inference fast). Swap in SHAP if per-request explanations are required.

A `_temp_disabled/` folder may be present with work-in-progress files that are
not part of the active pipeline.
