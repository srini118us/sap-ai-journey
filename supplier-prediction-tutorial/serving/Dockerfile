# SAP AI Core serving image for supplier prediction inference
# FastAPI server that loads XGBoost model from mounted volume

FROM python:3.11-slim

COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt

# Create directories
# /app/src     = serving code
# /mnt/models  = AI Core mounts the model artifact here at runtime
# /tmp         = cache home for sklearn/xgboost
RUN mkdir -p /app/src /mnt/models /tmp/sklearn_data && \
    chmod -R 777 /tmp/sklearn_data

COPY serve.py /app/src/serve.py

# AI Core runs as non-root user from group nogroup
RUN chgrp -R nogroup /app /mnt/models /tmp/sklearn_data && \
    chmod -R 770 /app /mnt/models && \
    chmod -R 777 /tmp/sklearn_data

# Environment for libraries that need HOME or cache paths
ENV SCIKIT_LEARN_DATA=/tmp/sklearn_data
ENV HOME=/tmp
ENV PYTHONUNBUFFERED=1

# AI Core convention: serve on port 9001
EXPOSE 9001

# Start FastAPI server with uvicorn
CMD ["uvicorn", "src.serve:app", "--host", "0.0.0.0", "--port", "9001", "--app-dir", "/app"]
