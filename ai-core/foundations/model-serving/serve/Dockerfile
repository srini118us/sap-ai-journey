# SAP AI Core Model Serving Container
# Customer Churn Prediction API

FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MODEL_PATH=/mnt/models

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy inference server code
COPY inference.py .

# Create model mount directory
RUN mkdir -p /mnt/models

# Expose port (AI Core standard)
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/v2/health')" || exit 1

# Run the inference server
CMD ["uvicorn", "inference:app", "--host", "0.0.0.0", "--port", "8080"]
