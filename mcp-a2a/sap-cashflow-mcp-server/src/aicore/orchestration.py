"""SAP AI Core Orchestration client for Prompt Template invocation.

Implements UC2.7 Tool 9 with the **Option C (embedded inline template)**
pattern.

The v0.0.2 template content authored in UC2.6 Part B (Prompt Editor →
scenario cashflow-forecast → name cashflow-explainer-system → version
0.0.2 → UUID 1ad15091-ad26-43a6-810e-77011234a04c) is embedded directly
in this module. This bypasses the rental BTP constraint where prompt
templates created via Prompt Editor UI are owned by the human user
principal, not the client-credentials service principal — making them
unreachable to service-key authenticated callers via the Prompt Registry
API regardless of scope.

The architectural intent of Part B — prompt-as-config separated from
code-as-implementation — is preserved at the *authoring* layer (templates
remain registered in Prompt Management for human iteration). What this
module sacrifices is *runtime-fetch swappability*. Tool 9 must be
redeployed to pick up new template versions.

Migration path to runtime fetch: re-author the template via Prompt
Registry API (POST /v2/lm/promptTemplates) using service-key
credentials. That makes the template owned by the same principal that
queries it, and Tool 9 can switch from inline-embedded to runtime fetch
via /v2/lm/promptTemplates/{uuid}/substitute. Code change is isolated
to this file (~30 lines).

Reads:
    - AICORE_AUTH_URL / AICORE_CLIENT_ID / AICORE_CLIENT_SECRET (SDK auto)
    - AICORE_BASE_URL (SDK auto)
    - ORCHESTRATION_DEPLOYMENT_ID (this module reads it explicitly)
    - ORCHESTRATION_RESOURCE_GROUP (this module reads it; default ml-training)
    - ORCHESTRATION_MODEL_NAME (default gpt-4o)
    - ORCHESTRATION_MODEL_VERSION (default latest)
    - ORCHESTRATION_MAX_TOKENS (default 600)
    - ORCHESTRATION_TEMPERATURE (default 0.1)
"""
import os
import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SECONDS = 60

# v0.0.2 template content — verbatim from UC2.6 Part B Section 4.3 + 7.2.
# Authored in Prompt Editor, registered as
# cashflow-forecast/cashflow-explainer-system/0.0.2.
# UUID for cross-reference / audit: 1ad15091-ad26-43a6-810e-77011234a04c.
SYSTEM_MESSAGE = """You are a financial cashflow explainer for SAP customer companies.
Your job is to translate machine learning forecasts into CFO-ready narratives.

CAVEAT REQUIREMENTS:

The narrative MUST include explicit acknowledgment that:
- SHAP values explain a RandomForest surrogate model, NOT the production AutoTS forecaster
- Feature contributions are correlational, NOT causal
- Treat as approximation guidance, NOT direct decomposition of the production model

INSTRUCTIONS:

Generate an 80-120 word narrative that:

1. States the forecast clearly with the company code.

2. Explains which features the prediction is most consistent with.
   Use "consistent with" language, NOT "because of" (correlation vs causation).

3. Notes the surrogate caveat (see CAVEAT REQUIREMENTS above).

4. Closes with one concrete CFO action recommendation.

Tone: professional, financial-advisor voice. No marketing language."""

USER_MESSAGE = """Generate the cashflow narrative for:

- Company code: {{?company_code}}
- Forecast date: {{?forecast_date}}
- Predicted next-day net cashflow: {{?forecast}}
- Best forecasting model: {{?best_model}}
- Top SHAP feature attributions (from RandomForest surrogate):

{{?top_features}}"""

# Audit metadata so Tool 9 responses can declare provenance.
EMBEDDED_TEMPLATE_REF = (
    "cashflow-forecast/cashflow-explainer-system/0.0.2 "
    "[embedded — UUID 1ad15091-ad26-43a6-810e-77011234a04c]"
)


def _proxy():
    """Return the gen-ai-hub-sdk proxy client.

    Lazy-imported so credential validation surfaces env errors at first
    real call, not at module import.
    """
    from gen_ai_hub.proxy.core.proxy_clients import get_proxy_client
    return get_proxy_client()


def render_narrative(
    company_code: str,
    forecast: float,
    forecast_date: str,
    best_model: str,
    top_features: list[dict[str, Any]],
) -> str:
    """Render the cashflow narrative via Orchestration with the embedded template.

    Builds an Orchestration completion request with the v0.0.2 template
    messages inline, plus input_params for {{?variable}} substitution.
    Orchestration's templating engine substitutes server-side, calls the
    LLM, returns narrative.

    Args:
        company_code: Company code (e.g., "1010").
        forecast: Predicted next-day net cashflow.
        forecast_date: ISO-8601 forecast date string.
        best_model: AutoTS model identifier.
        top_features: List of {"name": str, "shap_value": float}.

    Returns:
        Narrative text (LLM-generated).
    """
    deployment_id = os.getenv("ORCHESTRATION_DEPLOYMENT_ID")
    if not deployment_id:
        raise RuntimeError("ORCHESTRATION_DEPLOYMENT_ID not set in .env")

    resource_group = os.getenv("ORCHESTRATION_RESOURCE_GROUP", "ml-training")
    llm_model_name = os.getenv("ORCHESTRATION_MODEL_NAME", "gpt-4o")
    llm_model_version = os.getenv("ORCHESTRATION_MODEL_VERSION", "latest")
    llm_max_tokens = int(os.getenv("ORCHESTRATION_MAX_TOKENS", "600"))
    llm_temperature = float(os.getenv("ORCHESTRATION_TEMPERATURE", "0.1"))

    logger.info(
        "[ORCH] Rendering narrative via embedded template (ref=%s) on deployment %s (RG=%s)",
        EMBEDDED_TEMPLATE_REF, deployment_id, resource_group,
    )

    proxy = _proxy()
    base_url = proxy.ai_core_client.base_url.rstrip("/")
    url = f"{base_url}/inference/deployments/{deployment_id}/completion"

    headers = dict(proxy.request_header)
    headers["AI-Resource-Group"] = resource_group
    headers["Content-Type"] = "application/json"

    # Format top_features as a human-readable bullet list for the
    # {{?top_features}} placeholder. The Part B template expects a string.
    top_features_str = "\n".join(
        f"- {feat.get('name')}: SHAP value {feat.get('shap_value'):+,.2f}"
        for feat in top_features
    )

    body = {
        "orchestration_config": {
            "module_configurations": {
                "llm_module_config": {
                    "model_name": llm_model_name,
                    "model_version": llm_model_version,
                    "model_params": {
                        "max_tokens": llm_max_tokens,
                        "temperature": llm_temperature,
                    },
                },
                "templating_module_config": {
                    "template": [
                        {"role": "system", "content": SYSTEM_MESSAGE},
                        {"role": "user", "content": USER_MESSAGE},
                    ],
                },
            }
        },
        "input_params": {
            "company_code": str(company_code),
            "forecast_date": str(forecast_date),
            "forecast": f"{forecast:,.2f}",
            "best_model": str(best_model),
            "top_features": top_features_str,
        },
    }

    logger.info("[ORCH] POSTing to URL: %s", url)
    response = requests.post(
        url, json=body, headers=headers, timeout=DEFAULT_TIMEOUT_SECONDS
    )
    if response.status_code >= 400:
        logger.error("[ORCH] HTTP %s response body: %s",
                     response.status_code, response.text)
        response.raise_for_status()
    payload = response.json()

    # Orchestration response shape: orchestration_result.choices[0].message.content
    try:
        narrative = (
            payload["orchestration_result"]["choices"][0]["message"]["content"]
        )
    except (KeyError, IndexError, TypeError) as e:
        raise ValueError(
            f"Unexpected Orchestration response shape — could not extract "
            f"narrative. Top-level keys: {list(payload.keys())}. Error: {e}"
        ) from e

    if not narrative or not narrative.strip():
        raise ValueError("Orchestration returned empty narrative")

    logger.info("[ORCH] Narrative rendered (%d chars)", len(narrative))
    return narrative.strip()
