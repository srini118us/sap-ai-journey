# Payment Delay Prediction

Predicts whether a vendor invoice will be **paid late** using an XGBoost
classifier trained on SAP S/4HANA payment data. Packaged as an end-to-end
**SAP AI Core** scenario: a training workflow that produces a model artifact
and a KServe serving endpoint that exposes real-time predictions.

## What It Does

- **Training** pulls vendor payment history from HANA, engineers features,
  trains an XGBoost model, and saves it as an AI Core model artifact.
- **Serving** loads that artifact behind a Flask/Gunicorn REST API and returns
  a delay probability for each invoice sent to it.

## Folder Structure

```
payment-delay/
|-- train/                     # Training component
|   |-- train.py               # HANA read -> feature prep -> XGBoost -> save artifact
|   |-- Dockerfile             # python:3.11-slim, runs train.py
|   `-- requirements.txt
|-- serve/                     # Serving component
|   |-- serve.py               # Flask app: /v1/predict, /v1/healthz
|   |-- Dockerfile             # gunicorn on port 9001
|   `-- requirements.txt
`-- workflows/                 # SAP AI Core templates
    |-- training-template.yaml # Argo WorkflowTemplate (pd-train-tmpl)
    `-- serving-template.yaml  # ServingTemplate (pd-serve-tmpl)
```

## Data

Source table: `ML_PAYMENT.VENDOR_PAYMENTS` (SAP HANA).

- **Target:** `IS_DELAYED` (1 = paid late, 0 = on time)
- **Dropped (leakage / identifiers):** `DELAY_DAYS`, `INVOICE_ID`, `VENDOR_ID`,
  `NET_DUE_DATE`, `CLEARING_DATE`
- **Categorical encoding:** `COMPANY_CODE` is one-hot encoded (`drop_first=True`)
- Class imbalance is handled via XGBoost `scale_pos_weight`.

## Training

`train.py` connects to HANA using environment variables, trains the model,
prints evaluation metrics (accuracy, F1, ROC-AUC), and writes two artifacts to
`/app/model`:

- `model.joblib` — the trained XGBoost classifier
- `columns.joblib` — the feature column order (so serving can align inputs)

Required environment variables (provided on AI Core via the
`hana-payment-creds` secret):

| Variable        | Description                    |
|-----------------|--------------------------------|
| `HANA_HOST`     | HANA host address              |
| `HANA_PORT`     | HANA port (default `443`)      |
| `HANA_USER`     | HANA user                      |
| `HANA_PASSWORD` | HANA password                  |

Model hyperparameters: `n_estimators=200`, `max_depth=6`,
`learning_rate=0.1`, `eval_metric=logloss`, `random_state=42`.

## Serving

`serve.py` loads the model artifact from `/mnt/models` (mounted by KServe from
the training artifact) and exposes:

- `POST /v1/predict` — accepts a single JSON object or a list of objects.
  Input columns are aligned to the training columns via `reindex`, so any
  missing feature is filled with 0.
- `GET /v1/healthz` — returns `{"status": "ok"}`.

Response format:

```json
[
  { "delay_probability": 0.83, "predicted_delayed": 1 }
]
```

`predicted_delayed` is `1` when `delay_probability >= 0.5`.

Container listens on port **9001** (Gunicorn, 120s timeout).

## Build & Push Images

```bash
# from payment-delay/
docker build -t docker.io/<your-repo>/payment-delay-train:1.1 ./train
docker push docker.io/<your-repo>/payment-delay-train:1.1

docker build -t docker.io/<your-repo>/payment-delay-serve:1.0 ./serve
docker push docker.io/<your-repo>/payment-delay-serve:1.0
```

The provided templates reference the images `srini117us/payment-delay-train:1.1`
and `srini117us/payment-delay-serve:1.0` with image-pull secret
`docker-hub-srini117us` — update these to your registry as needed.

## Deploy on SAP AI Core

1. Sync the `workflows/` templates into your AI Core Git repository (both live
   under the scenario id `payment-delay-prediction`).
2. Create the required secrets: `hana-payment-creds` (HANA credentials) and the
   Docker image-pull secret.
3. Run the **training** executable `pd-train` — it produces the `paymentmodel`
   artifact.
4. Create a **deployment** from the serving executable `pd-serve`, passing the
   trained `paymentmodel` artifact as input.

## Example Prediction

```bash
curl -X POST https://<deployment-url>/v1/predict \
  -H "Authorization: Bearer <token>" \
  -H "AI-Resource-Group: <resource-group>" \
  -H "Content-Type: application/json" \
  -d '[{"COMPANY_CODE": "1000", "NET_ORDER_VALUE": 12500, "...": "..."}]'
```

## Notes

- The serving template declares an input parameter `greetmessage` that is not
  used by `serve.py`; it is boilerplate and can be removed.
- `sslValidateCertificate=False` is set on the HANA connection for convenience;
  enable certificate validation for production.
