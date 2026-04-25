# Cashflow forecasting training image
# Built for SAP AI Core (rootless execution required)
# Tag convention: srini117us/cashflow-train:<semver>

FROM python:3.11-slim

# === The rootless trap ===
# AI Core executes containers as a non-root user.
# Pre-create the directories the script needs and make them
# world-writable, so user 1000 (or whatever AI Core picks) can write.
RUN mkdir -p /app /app/output && chmod -R 777 /app

WORKDIR /app

# Copy and install dependencies first (better Docker layer caching:
# requirements rarely change, code changes often)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy training script
COPY train.py /app/train.py

# Run as non-root user (1000 is conventional)
USER 1000

ENTRYPOINT ["python", "/app/train.py"]
