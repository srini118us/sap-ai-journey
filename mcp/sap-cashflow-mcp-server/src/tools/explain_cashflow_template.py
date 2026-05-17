"""Tool 9: explain_cashflow_template

Renders a CFO-ready cashflow narrative via SAP AI Core Orchestration
with the cashflow-explainer-system template content authored in UC2.6
Part B (scenario cashflow-forecast, name cashflow-explainer-system,
version 0.0.2). Returns the narrative string only.

This is the prompt-as-config arm of UC2.7. Per Option C (embedded
inline template), the v0.0.2 template content is embedded in
src/aicore/orchestration.py rather than fetched from Prompt Registry
at runtime, due to rental BTP principal-ownership constraint on
templates created via Prompt Editor UI.

Two calling patterns are supported:

1. Standalone — caller supplies all five template variables directly.
2. Chained from Tool 8 — agent calls explain_cashflow_full first, then
   passes those structured fields into this tool. The agent prompt
   should explain this chaining; the tool itself is unaware of context.

Permissive top_features handling:
   Joule Studio's MCP chaining occasionally serializes nested arrays
   inconsistently when the agent passes Tool 8's output to Tool 9. To
   make the chain-call robust, this tool accepts:
     - None or empty list — falls back to a placeholder string so the
       template can still render (with reduced specificity)
     - A JSON-encoded string of the list — automatically parsed
     - A list of dicts with name + shap_value (the canonical shape)
     - A list of strings (degraded but usable)
"""
import json
import logging
from typing import Any

from src.aicore.orchestration import render_narrative

logger = logging.getLogger(__name__)


def _normalize_top_features(
    top_features: Any,
) -> list[dict[str, Any]]:
    """Coerce whatever Joule sends us into the canonical shape.

    Returns a list of {"name": str, "shap_value": float} dicts. Returns
    a single placeholder entry if the input is missing or unusable, so
    the template still has *something* to render.
    """
    # None or empty
    if top_features is None or top_features == "" or top_features == []:
        logger.warning(
            "[TOOL9] top_features missing or empty — using placeholder. "
            "Joule chain-call may have dropped the field."
        )
        return [{"name": "(features unavailable)", "shap_value": 0.0}]

    # JSON-encoded string
    if isinstance(top_features, str):
        try:
            parsed = json.loads(top_features)
            logger.info("[TOOL9] Parsed top_features from JSON string")
            return _normalize_top_features(parsed)
        except (json.JSONDecodeError, ValueError):
            logger.warning(
                "[TOOL9] top_features arrived as non-JSON string '%s' — "
                "treating as single feature name",
                top_features[:80],
            )
            return [{"name": top_features[:80], "shap_value": 0.0}]

    # List
    if isinstance(top_features, list):
        if len(top_features) == 0:
            logger.warning("[TOOL9] top_features is empty list — using placeholder")
            return [{"name": "(features unavailable)", "shap_value": 0.0}]

        normalized = []
        for entry in top_features[:5]:
            if isinstance(entry, dict):
                name = entry.get("name") or entry.get("feature") or "(unnamed)"
                shap_raw = entry.get("shap_value", entry.get("value", 0.0))
                try:
                    shap_value = float(shap_raw)
                except (TypeError, ValueError):
                    shap_value = 0.0
                normalized.append({"name": str(name), "shap_value": shap_value})
            elif isinstance(entry, str):
                # Agent passed a list of feature name strings only
                normalized.append({"name": entry, "shap_value": 0.0})
            else:
                # Skip silently — unknown shape
                logger.warning("[TOOL9] Skipping unrecognized feature entry: %r", entry)

        if not normalized:
            return [{"name": "(features unavailable)", "shap_value": 0.0}]
        return normalized

    # Dict (single feature passed instead of list)
    if isinstance(top_features, dict):
        return _normalize_top_features([top_features])

    # Anything else — last resort
    logger.warning(
        "[TOOL9] top_features arrived as unexpected type %s — using placeholder",
        type(top_features).__name__,
    )
    return [{"name": "(features unavailable)", "shap_value": 0.0}]


def explain_cashflow_template(
    company_code: str,
    forecast: float,
    forecast_date: str,
    best_model: str,
    top_features: Any = None,
) -> dict:
    """Implementation backing the explain_cashflow_template MCP tool.

    Args:
        company_code: Company code (e.g., "1010").
        forecast: Predicted next-day net cashflow (number).
        forecast_date: ISO-8601 forecast date string.
        best_model: AutoTS model identifier (e.g., "UnivariateMotif").
        top_features: List of {"name": str, "shap_value": number}.
            Pass through directly from Tool 8 when chaining. Permissive:
            see _normalize_top_features above for accepted shapes.

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

    # Permissive handling — Joule's MCP chaining sometimes drops or
    # mangles the top_features field. Normalize rather than fail.
    capped_features = _normalize_top_features(top_features)

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
