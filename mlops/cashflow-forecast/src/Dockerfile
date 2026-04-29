# UC2.5 training image — adds insert_synthetic.py to UC2.3's training image.
# Two scripts in one image; the workflow YAML uses different `command:` entries
# per step (insert in step 1, train in step 2).
#
# Versioning: bumped from 0.3 to 0.4 to signal the new contract.
# Tag: srini117us/cashflow-train:0.4

FROM python:3.11-slim

WORKDIR /app

# Build deps for hdbcli native bits + scientific stack; stripped after install.
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc g++ \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN apt-get purge -y --auto-remove gcc g++

# Both scripts live in the same image. Workflow YAML picks which to invoke
# via the `command:` field per step.
COPY train.py .
COPY insert_synthetic.py .

# Pre-create output directory with permissive perms so non-root Argo pods
# can write into it. UC2.3 didn't need this because its single-step pod ran
# as root; UC2.5's DAG steps run as a non-root user (Argo executor 3.7.4
# default), and /app is owned by root from WORKDIR.
RUN mkdir -p /app/output && chmod 777 /app/output
# Default command (manual `docker run` will train); the AI Core workflow
# overrides this per step.
CMD ["python", "/app/train.py"]
