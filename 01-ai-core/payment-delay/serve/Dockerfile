FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --timeout 300 --retries 10 -r requirements.txt
COPY serve.py .
EXPOSE 9001
ENTRYPOINT ["gunicorn", "--bind", "0.0.0.0:9001", "--timeout", "120", "serve:app"]
