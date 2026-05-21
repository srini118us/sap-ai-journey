# SAP AI Core training image for supplier on-time delivery prediction
# XGBoost binary classifier with feature importance reporting

FROM python:3.11-slim

# Install dependencies first (cached layer)
COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt

# Create directories
# /app/src   = training script
# /app/data  = S3-mounted dataset (mounted by AI Core at runtime)
# /app/model = S3-mounted model output (mounted by AI Core at runtime)
# /tmp       = scratch space and library cache home
RUN mkdir -p /app/src /app/data /app/model /tmp/sklearn_data && \
    chmod -R 777 /tmp/sklearn_data

COPY train.py /app/src/train.py

# AI Core runs as non-root user from group nogroup
# Grant group access to all app directories
RUN chgrp -R nogroup /app /tmp/sklearn_data && \
    chmod -R 770 /app && \
    chmod -R 777 /tmp/sklearn_data

# Library cache vars (avoid /nonexistent issue we saw in house price)
ENV SCIKIT_LEARN_DATA=/tmp/sklearn_data
ENV HOME=/tmp
ENV PYTHONUNBUFFERED=1
