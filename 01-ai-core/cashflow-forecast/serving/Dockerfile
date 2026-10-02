# Cashflow forecast inference container (UC2.4)
# Single-model serving — MODEL_NAME env selects which .pkl to load.
# Two AI Core deployments will share this image, differing only in MODEL_NAME.
#
# Python version note: training image base unknown. 3.11-slim is the modern default.
# If joblib pickle load fails at runtime with a Python ABI error, drop to whatever
# python: tag the training image used.

FROM python:3.11-slim

WORKDIR /app

# Install build deps for scientific libs (autots/scipy can need gcc on slim images),
# then strip them after pip install to keep the image small.
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc g++ \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN apt-get purge -y --auto-remove gcc g++

COPY app.py .

# AI Core ServingTemplate will mount the Model artifact here. The mount path is
# configured in the ServingTemplate spec next session — keep this in sync with that.
ENV MODEL_DIR=/mnt/models

# Override per deployment: model_1710.pkl or model_1010.pkl
ENV MODEL_NAME=model_1710.pkl

ENV PORT=8080
EXPOSE 8080

# Local Docker healthcheck. AI Core uses its own probes via ServingTemplate.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/v2/healthz').read()" || exit 1

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
