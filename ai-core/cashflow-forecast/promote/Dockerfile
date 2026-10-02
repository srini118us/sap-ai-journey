# UC2.5 promote container.
#
# Purpose: scheduled job that calls AI Core REST API to promote newest
# trained Model to live deployments. No scientific stack needed.
#
# Tag: srini117us/cashflow-promote:0.1

FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY promote.py .

# Default command. AI Core workflow YAML can override but doesn't need to —
# this container has one job.
CMD ["python", "/app/promote.py"]
