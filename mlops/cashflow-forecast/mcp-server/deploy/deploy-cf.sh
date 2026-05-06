#!/bin/bash
# UC2.7 Cloud Foundry deployment for sap-cashflow-mcp-server.
#
# Run from the mcp-server directory after .env has the four AICORE_*
# values populated. Script:
#   1. Reads AICORE_* values from .env.
#   2. Pushes the app via manifest.yml (non-secret env vars baked in).
#   3. Sets AICORE_* secrets via `cf set-env` (kept out of manifest.yml
#      so the manifest is safe to commit to git).
#   4. Restages so the new env vars take effect.
#
# Pre-requisites:
#   - cf CLI installed
#   - cf logged in: `cf login -a https://api.cf.us10-001.hana.ondemand.com`
#     against rental org-build-sap-btp-joule, space build (Space Developer role)
#   - Image srini117us/sap-cashflow-mcp-server:v1 already pushed to Docker Hub
#   - .env populated in mcp-server/ directory

set -euo pipefail

ENV_FILE="${1:-.env}"
APP_NAME="sap-cashflow-mcp-server"

if [[ ! -f "$ENV_FILE" ]]; then
    echo "ERROR: $ENV_FILE not found. Run from mcp-server/ directory."
    exit 1
fi

# Load AICORE_* from .env without exporting other variables.
get_env() {
    grep -E "^${1}=" "$ENV_FILE" | head -1 | sed -E "s/^${1}=//; s/\r$//"
}

AICORE_AUTH_URL=$(get_env AICORE_AUTH_URL)
AICORE_CLIENT_ID=$(get_env AICORE_CLIENT_ID)
AICORE_CLIENT_SECRET=$(get_env AICORE_CLIENT_SECRET)
AICORE_BASE_URL=$(get_env AICORE_BASE_URL)

for var in AICORE_AUTH_URL AICORE_CLIENT_ID AICORE_CLIENT_SECRET AICORE_BASE_URL; do
    if [[ -z "${!var:-}" ]]; then
        echo "ERROR: $var is empty in $ENV_FILE"
        exit 1
    fi
done

echo "[deploy] Pushing app via manifest.yml (no-start so we can set secrets first)..."
cf push -f manifest.yml --no-start

echo "[deploy] Setting AICORE_* secrets via cf set-env..."
cf set-env "$APP_NAME" AICORE_AUTH_URL "$AICORE_AUTH_URL"
cf set-env "$APP_NAME" AICORE_CLIENT_ID "$AICORE_CLIENT_ID"
cf set-env "$APP_NAME" AICORE_CLIENT_SECRET "$AICORE_CLIENT_SECRET"
cf set-env "$APP_NAME" AICORE_BASE_URL "$AICORE_BASE_URL"

echo "[deploy] Starting the app (env vars now in place)..."
cf start "$APP_NAME"

echo "[deploy] Done. Routes:"
cf app "$APP_NAME" | grep -E "^routes:" | head -1
