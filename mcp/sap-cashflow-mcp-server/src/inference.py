"""SAP AI Core deployment inference client.

Thin wrapper over the gen-ai-hub-sdk proxy client to call any AI Core
deployment by ID — including custom KServe deployments that are NOT
OpenAI-compatible (e.g., the UC2.6 Step 4 cashflow-explain endpoint).

Mirrors the env-driven pattern used by src/genai/embedding.py: the SDK
auto-discovers AICORE_* env vars; this module surfaces the deployment-
specific env vars and adds an explicit AI-Resource-Group header for
cross-RG calls.

Reads:
    - AICORE_AUTH_URL (auto-picked up by SDK)
    - AICORE_CLIENT_ID (auto-picked up by SDK)
    - AICORE_CLIENT_SECRET (auto-picked up by SDK)
    - AICORE_BASE_URL (auto-picked up by SDK)
    - EXPLAIN_DEPLOYMENT_ID (this module reads it explicitly)
    - EXPLAIN_RESOURCE_GROUP (this module reads it explicitly; default ml-training)
"""
import os
import logging

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SECONDS = 60


def call_explain(company_code: str) -> dict:
    """Call the UC2.6 Step 4 cashflow-explain deployment.

    Posts {"company_code": ...} to /v2/explain and returns the parsed
    JSON response. The deployment lives in the ml-training resource group
    and is reached via the AI Core inference proxy, with auth handled by
    gen-ai-hub-sdk.

    Args:
        company_code: Company code string (e.g., "1010", "1710"). Must
            match a company served by the explain deployment, which loads
            its set from /v2/info.

    Returns:
        Full JSON payload as returned by /v2/explain. Schema (UC2.6):
            company_code: str
            forecast: float
            forecast_date: ISO-8601 string
            best_model: str
            nearest_window: {date, actual, predicted}
            top_features: list of {name, shap_value}
            narrative: str (GPT-4o output, embedded in the explain service)
            surrogate_caveat: str

    Raises:
        RuntimeError: if required env vars are missing.
        requests.HTTPError: on non-2xx responses from AI Core.
    """
    if not company_code or not str(company_code).strip():
        raise ValueError("company_code is required")

    deployment_id = os.getenv("EXPLAIN_DEPLOYMENT_ID")
    if not deployment_id:
        raise RuntimeError("EXPLAIN_DEPLOYMENT_ID not set in .env")

    resource_group = os.getenv("EXPLAIN_RESOURCE_GROUP", "ml-training")

    # Lazy import so credential validation surfaces env errors first
    from gen_ai_hub.proxy.core.proxy_clients import get_proxy_client

    logger.info(
        "[AICORE] Calling /v2/explain on deployment %s (RG=%s) for company %s",
        deployment_id, resource_group, company_code,
    )

    proxy = get_proxy_client()
    base_url = proxy.ai_core_client.base_url.rstrip("/")
    url = f"{base_url}/v2/inference/deployments/{deployment_id}/v2/explain"

    # Reuse the SDK's authenticated session (handles OAuth2 + token refresh).
    session = proxy.ai_core_client.rest_client.session
    headers = {
        "Content-Type": "application/json",
        "AI-Resource-Group": resource_group,
    }

    response = session.post(
        url,
        json={"company_code": str(company_code)},
        headers=headers,
        timeout=DEFAULT_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    payload = response.json()

    if "company_code" not in payload or "forecast" not in payload:
        raise ValueError(
            f"Unexpected /v2/explain response shape — missing company_code "
            f"or forecast field. Keys present: {list(payload.keys())}"
        )

    logger.info(
        "[AICORE] /v2/explain returned forecast=%s for company %s",
        payload.get("forecast"), payload.get("company_code"),
    )
    return payload
