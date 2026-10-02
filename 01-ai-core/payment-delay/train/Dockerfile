FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --timeout 300 --retries 10 -r requirements.txt
COPY train.py .
RUN mkdir -p /app/model && chmod -R 777 /app/model
ENTRYPOINT ["python", "train.py"]