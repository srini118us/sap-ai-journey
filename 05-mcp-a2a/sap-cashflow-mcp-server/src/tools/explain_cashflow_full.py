"""Tool 8: explain_cashflow_full

Calls the UC2.6 Step 4 cashflow-explain deployment and returns the
*structured* explainability fields only — forecast, top SHAP features,
nearest-window context, and the surrogate caveat. The narrative field
embedded by the explainer service is *deliberately stripped* so the
agent decides whether to render a narrative via Tool 9 (Prompt Template
path) instead. This separates SHAP-data retrieval from narrative
generation per the 9a-revised UC2.7 design.

Joule 10KB tool-response limit: enforced by truncating to top-5 features.
The full explainer typically returns 3 features (152-window summary
collapses to dom/lag_14/dow tier), so 5 is a safe ceiling.
"""
import logging

from src.aicore.inference import call_explain

logger = logging.getLogger(__name__)

DEFAULT_TOP_N = 5


def explain_cashflow_full(
    company_code: str,
    top_n: int = DEFAULT_TOP_N,
) -> dict:
    """Implementation backing the explain_cashflow_full MCP tool.

    Args:
        company_code: Company code recognised by the explain service
            (currently "1010" or "1710" per UC2.6 Step 4 smoke tests).
        top_n: Cap on number of SHAP features returned (default 5,
            min 1, max 10). Enforces Joule 10KB response limit.

    Returns:
        dict with keys:
            company_code, forecast, forecast_date, best_model,
            nearest_window {date, actual, predicted},
            top_features (list of {name, shap_value}, length <= top_n),
            surrogate_caveat
        The narrative field is intentionally NOT returned.
    """
    if not company_code or not str(company_code).strip():
        raise ValueError("company_code is required")

    top_n = max(1, min(int(top_n), 10))

    raw = call_explain(company_code=str(company_code))

    top_features = raw.get("top_features") or []
    if len(top_features) > top_n:
        logger.info(
            "[TOOL8] Truncating top_features from %d to %d for 10KB compliance",
            len(top_features), top_n,
        )
        top_features = top_features[:top_n]

    # Round SHAP values to 2 decimals for response size and readability;
    # the agent-facing payload does not need 15-digit precision.
    top_features = [
        {
            "name": feat.get("name"),
            "shap_value": round(float(feat.get("shap_value", 0.0)), 2),
        }
        for feat in top_features
    ]

    nearest = raw.get("nearest_window") or {}
    if nearest:
        nearest = {
            "date": nearest.get("date"),
            "actual": round(float(nearest.get("actual", 0.0)), 2),
            "predicted": round(float(nearest.get("predicted", 0.0)), 2),
        }

    return {
        "company_code": raw.get("company_code"),
        "forecast": round(float(raw.get("forecast", 0.0)), 2),
        "forecast_date": raw.get("forecast_date"),
        "best_model": raw.get("best_model"),
        "nearest_window": nearest,
        "top_features": top_features,
        "surrogate_caveat": raw.get("surrogate_caveat"),
    }
