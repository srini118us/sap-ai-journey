# SAP AI Core tutorial: House Price Predictor
# Builds a Docker image containing the sklearn training script.
# AI Core pulls this image, runs the training script,
# and captures output (model artifact, logs, metrics).

FROM python:3.11-slim

# Install dependencies first (cached layer)
COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt

# Create the working directory expected by AI Core
RUN mkdir -p /app/src
COPY main.py /app/src/main.py

# Permissions for AI Core to read and execute
RUN chgrp -R nogroup /app && \
    chmod -R 770 /app
