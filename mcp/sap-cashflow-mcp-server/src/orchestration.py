"""SAP AI Core Orchestration client for Prompt Template invocation.

Calls the Orchestration deployment with a registered Prompt Template
(authored in UC2.6 Part B, scenario cashflow-forecast, template
cashflow-explainer-system, version 0.0.2). Returns the LLM-generated
narrative — the same content embedded inside /v2/explain, but reachable
*without* invoking the explainer container, so the template can be
swapped at runtime independently of the container image.

Reads:
    - AICORE_AUTH_URL / AICORE_CLIENT_ID / AICORE_CLIENT_SECRET (SDK auto)
    - AICORE_BASE_URL (SDK auto)
    - ORCHESTRATION_DEPLOYMENT_ID (this module reads it explicitly)
    - ORCHESTRATION_RESOURCE_GROUP (this module reads it explicitly;
      default ai-launchpad — matches where Orchestration was enabled)
    - PROMPT_TEMPLATE_REF (default
      cashflow-forecast/cashflow-explainer-system/0.0.2)
"""
import os
import logging
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SECONDS = 60
DEFAULT_TEMPLATE_REF = "cashflow-forecast/cashflow-explainer-system/0.0.2"


def render_narrative(
    company_code: str,
    forecast: float,
    forecast_date: str,
    best_model: str,
    top_features: list[dict[str, Any]],
) -> str:
    """Render the cashflow narrative using the registered Prompt Template.

    Builds an Orchestration completion request that references the
    Prompt Template by name+scenario+version and binds the five template
    variables. Returns the model's narrative text.

    Args:
        company_code: Company code (e.g., "1010").
        forecast: Predicted next-day net cashflow.
        forecast_date: ISO-8601 forecast date string.
        best_model: Name of the AutoTS model that produced the forecast
            (e.g., "UnivariateMotif").
        top_features: List of {"name": str, "shap_value": float} entries.

    Returns:
        Narrative text from the configured LLM (GPT-4o per the template).

    Raises:
        RuntimeError: if required env vars are missing.
        requests.HTTPError: on non-2xx responses from Orchestration.
    """
    deployment_id = os.getenv("ORCHESTRATION_DEPLOYMENT_ID")
    if not deployment_id:
        raise RuntimeError("ORCHESTRATION_DEPLOYMENT_ID not set in .env")

    resource_group = os.getenv("ORCHESTRATION_RESOURCE_GROUP", "ai-launchpad")
    template_ref = os.getenv("PROMPT_TEMPLATE_REF", DEFAULT_TEMPLATE_REF)

    # Lazy import so credential validation surfaces env errors first
    from gen_ai_hub.proxy.core.proxy_clients import get_proxy_client

    logger.info(
        "[ORCH] Rendering narrative via template %s on deployment %s (RG=%s)",
        template_ref, deployment_id, resource_group,
    )

    proxy = get_proxy_client()
    base_url = proxy.ai_core_client.base_url.rstrip("/")
    url = f"{base_url}/v2/inference/deployments/{deployment_id}/completion"

    session = proxy.ai_core_client.rest_client.session
    headers = {
        "Content-Type": "application/json",
        "AI-Resource-Group": resource_group,
    }

    # Format top_features as a human-readable bullet list for the {{?top_features}}
    # placeholder. The Part B template expects this as a string, not a JSON array.
    top_features_str = "\n".join(
        f"- {feat.get('name')}: SHAP value {feat.get('shap_value'):+,.2f}"
        for feat in top_features
    )

    body = {
        "orchestration_config": {
            "module_configurations": {
                "templating_module_config": {
                    "template_ref": {
                        "scenario": template_ref.split("/")[0],
                        "name": template_ref.split("/")[1],
                        "version": template_ref.split("/")[2],
                    }
                }
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

    response = session.post(
        url, json=body, headers=headers, timeout=DEFAULT_TIMEOUT_SECONDS
    )
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
