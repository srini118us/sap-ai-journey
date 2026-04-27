#!/bin/bash
# Local smoke test for cashflow forecast inference container.
# Pulls a model from S3, builds the image, runs the container, exercises all
# three endpoints, and tears down. Run BEFORE pushing the image to Docker Hub.
#
# Usage:
#   ./test_local.sh           # tests with company 1710
#   ./test_local.sh 1010      # tests with company 1010
#
# Pre-reqs:
#   - aws cli configured (AWS profile that can read s3://amzn-aicore-2026)
#   - docker daemon running
#   - run from the serving/ directory

set -euo pipefail

S3_PREFIX="s3://amzn-aicore-2026/cashflow/ec23c62af0900c0f/trained_model"
COMPANY="${1:-1710}"
PORT=8080
IMAGE_TAG="cashflow-serve:0.1-local"

# tmp dir cleaned up on exit (success or failure)
LOCAL_MODELS=$(mktemp -d)
CONTAINER_ID=""

cleanup() {
    if [ -n "$CONTAINER_ID" ]; then
        echo "[cleanup] stopping container $CONTAINER_ID"
        docker stop "$CONTAINER_ID" >/dev/null 2>&1 || true
        docker rm "$CONTAINER_ID" >/dev/null 2>&1 || true
    fi
    rm -rf "$LOCAL_MODELS"
}
trap cleanup EXIT

echo "[1/6] downloading model + metrics for company $COMPANY"
aws s3 cp "$S3_PREFIX/model_${COMPANY}.pkl" "$LOCAL_MODELS/"
aws s3 cp "$S3_PREFIX/metrics.json" "$LOCAL_MODELS/"
ls -la "$LOCAL_MODELS"

echo "[2/6] building image $IMAGE_TAG"
docker build -t "$IMAGE_TAG" .

echo "[3/6] starting container"
CONTAINER_ID=$(docker run -d \
    -p "$PORT:8080" \
    -v "$LOCAL_MODELS:/mnt/models:ro" \
    -e "MODEL_NAME=model_${COMPANY}.pkl" \
    "$IMAGE_TAG")
echo "       container id: $CONTAINER_ID"

echo "[4/6] waiting for /v2/healthz to return 200"
for i in $(seq 1 60); do
    if curl -sf "http://localhost:$PORT/v2/healthz" >/dev/null 2>&1; then
        echo "       ready after ${i}s"
        break
    fi
    sleep 1
    if [ "$i" -eq 60 ]; then
        echo "[fail] container did not become healthy in 60s"
        docker logs "$CONTAINER_ID"
        exit 1
    fi
done

echo "[5/6] hitting endpoints"
echo "--- /v2/healthz ---"
curl -sf "http://localhost:$PORT/v2/healthz" | python -m json.tool

echo "--- /v2/info ---"
curl -sf "http://localhost:$PORT/v2/info" | python -m json.tool

echo "--- /v2/predict (default horizon) ---"
curl -sf -X POST "http://localhost:$PORT/v2/predict" \
    -H "Content-Type: application/json" \
    -d '{}' | python -m json.tool

echo "--- /v2/predict (forecast_length=30) ---"
curl -sf -X POST "http://localhost:$PORT/v2/predict" \
    -H "Content-Type: application/json" \
    -d '{"forecast_length": 30}' | python -m json.tool

echo "--- /v2/predict (out-of-range, expect 422) ---"
curl -s -o /dev/null -w "HTTP %{http_code}\n" -X POST "http://localhost:$PORT/v2/predict" \
    -H "Content-Type: application/json" \
    -d '{"forecast_length": 999}'

echo "[6/6] container logs (last 20 lines)"
docker logs --tail 20 "$CONTAINER_ID"

echo "[done] smoke test passed for company $COMPANY"
