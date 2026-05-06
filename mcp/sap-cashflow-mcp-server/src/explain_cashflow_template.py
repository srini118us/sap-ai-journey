"""Tool 9: explain_cashflow_template

Renders a CFO-ready cashflow narrative via SAP AI Core Orchestration
with the registered Prompt Template authored in UC2.6 Part B
(scenario cashflow-forecast, name cashflow-explainer-system, version
0.0.2). Returns the narrative string only.

This is the prompt-as-config arm of UC2.7. The narrative content can be
changed by editing the Prompt Template in Prompt Management without
touching this tool, the MCP server image, or the explainer container.

Two calling patterns are supported:

1. Standalone — caller supplies all five template variables directly.
   Use when SHAP data was sourced from somewhere other than Tool 8 or
   when running templated prompts against hypothetical inputs.

2. Chained from Tool 8 — agent calls explain_cashflow_full first, then
   passes those structured fields into this tool. The agent prompt
   should explain this chaining; the tool itself is unaware of context.
"""
import logging
from typing import Any

from src.aicore.orchestration import render_narrative

logger = logging.getLogger(__name__)


def explain_cashflow_template(
    company_code: str,
    forecast: float,
    forecast_date: str,
    best_model: str,
    top_features: list[dict[str, Any]],
) -> dict:
    """Implementation backing the explain_cashflow_template MCP tool.

    Args:
        company_code: Company code (e.g., "1010").
        forecast: Predicted next-day net cashflow (number).
        forecast_date: ISO-8601 forecast date string.
        best_model: AutoTS model identifier (e.g., "UnivariateMotif").
        top_features: List of {"name": str, "shap_value": number}.
            Pass through directly from Tool 8 when chaining.

    Returns:
        dict with keys:
            narrative: str — LLM-generated narrative
            template_ref: str — which template version produced it
                (useful for audit / A-B comparison)
    """
    if not company_code or not str(company_code).strip():
        raise ValueError("company_code is required")
    if forecast is None:
        raise ValueError("forecast is required")
    if not forecast_date:
        raise ValueError("forecast_date is required")
    if not best_model:
        raise ValueError("best_model is required")
    if not top_features:
        raise ValueError("top_features is required (non-empty list)")

    # Defensive: cap features passed into the prompt to avoid wasting
    # template tokens on features the LLM would ignore anyway.
    capped_features = top_features[:5]

    narrative = render_narrative(
        company_code=str(company_code),
        forecast=float(forecast),
        forecast_date=str(forecast_date),
        best_model=str(best_model),
        top_features=capped_features,
    )

    import os
    template_ref = os.getenv(
        "PROMPT_TEMPLATE_REF",
        "cashflow-forecast/cashflow-explainer-system/0.0.2",
    )

    return {
        "narrative": narrative,
        "template_ref": template_ref,
    }
