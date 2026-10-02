FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY server.py .
COPY tools.py .

# Expose port
EXPOSE 8080

# Enable stateless mode for Kubernetes (multiple replicas)
ENV FASTMCP_STATELESS_HTTP=true

# S/4HANA Connection (override with Kubernetes secrets/configmap)
ENV S4_BASE_URL=http://mtsapserver3.themdlabs.com:8003
ENV S4_USER=sdasari
ENV S4_PASSWORD=Welcome#234

# Run with Streamable HTTP transport (Joule compatible)
CMD ["python", "server.py", "--http"]
