FROM python:3.11-slim

# Non-root UID matches AI Core / Kyma runtime expectations
RUN groupadd -r mcp -g 1000 && useradd -r -u 1000 -g mcp mcp

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/

# Joule requires Streamable HTTP transport with stateless HTTP mode
ENV FASTMCP_STATELESS_HTTP=true \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    MCP_HOST=0.0.0.0 \
    PORT=8080

USER 1000:1000

EXPOSE 8080

CMD ["python", "-m", "src.server"]
