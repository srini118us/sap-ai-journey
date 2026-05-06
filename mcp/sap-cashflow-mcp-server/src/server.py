"""FastMCP server for SAP Cashflow Forecast Explainability tools.

Exposes 2 MCP tools for Joule Agent consumption:
    - explain_cashflow_full: Structured SHAP explainability data
      (calls UC2.6 Step 4 /v2/explain, strips embedded narrative)
    - explain_cashflow_template: LLM narrative via registered Prompt
      Template (calls Orchestration; UC2.6 Part B template v0.0.2)

Transport: Streamable HTTP (required by Joule).
"""
import os
import logging

from dotenv import load_dotenv
from fastmcp import FastMCP

load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

from src.tools import explain_cashflow_full as _explain_cashflow_full
from src.tools import explain_cashflow_template as _explain_cashflow_template

mcp = FastMCP(os.getenv("MCP_SERVER_NAME", "cashflow-server"))


@mcp.tool()
def explain_cashflow_full(
    company_code: str,
    top_n: int = 5,
) -> dict:
    """Retrieve SHAP-based explainability data for a cashflow forecast.

    Calls the SAP AI Core cashflow-forecast-explain deployment and returns
    the *structured fields only* — forecast value, forecast date, model
    identifier, top SHAP features, and the surrogate caveat. The embedded
    LLM narrative is intentionally excluded; use explain_cashflow_template
    for narrative rendering. This tool fetches data; the agent reasons over
    it.

    Use this tool when the user asks for the cashflow forecast, the SHAP
    feature attributions, the top drivers of the forecast, or the
    explainability data for a specific company. Use this BEFORE calling
    explain_cashflow_template, because the template tool needs these
    structured fields as input.

    Args:
        company_code: Company code recognised by the explain service.
            Currently supported: "1010", "1710". Sending another code
            will return a service error.
        top_n: Cap on the number of SHAP features returned (default 5,
            range 1-10). Enforces the Joule 10KB tool-response limit.

    Returns:
        Dictionary with: company_code, forecast, forecast_date, best_model,
        nearest_window {date, actual, predicted}, top_features (list of
        {name, shap_value}, length <= top_n), and surrogate_caveat.
        Narrative field is intentionally omitted.
    """
    return _explain_cashflow_full(company_code=company_code, top_n=top_n)


@mcp.tool()
def explain_cashflow_template(
    company_code: str,
    forecast: float,
    forecast_date: str,
    best_model: str,
    top_features: list[dict] | None = None,
) -> dict:
    """Render a CFO-ready cashflow narrative via the registered SAP Prompt Template.

    Invokes SAP AI Core Orchestration with the cashflow-explainer-system
    template (scenario cashflow-forecast, version 0.0.2) authored in
    UC2.6 Part B. Returns the natural-language narrative only. The
    template encodes the surrogate-honesty framing ("consistent with"
    not "because of"), the surrogate-vs-production-model caveat, and
    the CFO-action-recommendation requirement.

    Use this tool when the user asks for an explanation, a narrative,
    a CFO-friendly summary, or a "plain English" version of the
    forecast. Always call explain_cashflow_full FIRST to get the
    structured fields this tool needs as input — top_features in
    particular cannot be invented and must come from /v2/explain.

    Args:
        company_code: Company code (e.g., "1010"). Pass through from
            explain_cashflow_full output.
        forecast: Predicted next-day net cashflow value. Pass through
            from explain_cashflow_full.
        forecast_date: ISO-8601 forecast date string. Pass through from
            explain_cashflow_full.
        best_model: AutoTS model identifier (e.g., "UnivariateMotif").
            Pass through from explain_cashflow_full.
        top_features: List of {"name": str, "shap_value": number}.
            Pass through from explain_cashflow_full.top_features.

    Returns:
        Dictionary with: narrative (LLM-generated narrative string) and
        template_ref (e.g., "cashflow-forecast/cashflow-explainer-system/0.0.2"
        — useful for audit and A/B comparison across template versions).
    """
    return _explain_cashflow_template(
        company_code=company_code,
        forecast=forecast,
        forecast_date=forecast_date,
        best_model=best_model,
        top_features=top_features or [],
    )


if __name__ == "__main__":
    host = os.getenv("MCP_HOST", "0.0.0.0")
    port = int(os.getenv("PORT", os.getenv("MCP_PORT", "8080")))
    logger.info(
        "[SERVER] Starting FastMCP '%s' on %s:%s (Streamable HTTP) — 2 tools registered",
        os.getenv("MCP_SERVER_NAME", "cashflow-server"), host, port,
    )
    mcp.run(transport="streamable-http", host=host, port=port)
