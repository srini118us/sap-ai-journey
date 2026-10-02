"""Local smoke tests for the cashflow MCP tools.

Run BEFORE Docker build / Kyma deploy. Validates that AI Core auth works,
the explain deployment is reachable, and the Prompt Template is invokable.

Usage:
    cd sap-cashflow-mcp-server
    python -m venv venv && source venv/bin/activate
    pip install -r requirements.txt
    cp .env.example .env  # populate values
    python -m tests.test_tools_local
"""
import json
import sys
import logging

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level="INFO",
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("smoke")


def smoke_tool_8():
    """Tool 8: explain_cashflow_full — should hit /v2/explain on d00c85f445274f70."""
    from src.tools import explain_cashflow_full

    logger.info("Running Tool 8 smoke (company_code=1010)...")
    result = explain_cashflow_full(company_code="1010", top_n=5)

    assert result["company_code"] == "1010", "company_code mismatch"
    assert isinstance(result["forecast"], (int, float)), "forecast missing or wrong type"
    assert "narrative" not in result, "narrative should be stripped per 9a-revised design"
    assert isinstance(result["top_features"], list), "top_features missing"
    assert len(result["top_features"]) <= 5, "top_n cap not enforced"

    payload_size = len(json.dumps(result))
    assert payload_size < 10_000, f"Tool 8 response {payload_size} bytes exceeds Joule 10KB"

    logger.info("Tool 8 OK — forecast=%s, features=%d, size=%d bytes",
                result["forecast"], len(result["top_features"]), payload_size)
    return result


def smoke_tool_9(tool_8_output: dict):
    """Tool 9: explain_cashflow_template — should render via Prompt Template v0.0.2."""
    from src.tools import explain_cashflow_template

    logger.info("Running Tool 9 smoke (chained from Tool 8 output)...")
    result = explain_cashflow_template(
        company_code=tool_8_output["company_code"],
        forecast=tool_8_output["forecast"],
        forecast_date=tool_8_output["forecast_date"],
        best_model=tool_8_output["best_model"],
        top_features=tool_8_output["top_features"],
    )

    assert "narrative" in result, "narrative missing"
    assert isinstance(result["narrative"], str) and result["narrative"].strip(), \
        "narrative empty"
    assert "template_ref" in result, "template_ref missing"

    # Surrogate honesty check — v0.0.2 must include the caveat content
    narrative_lower = result["narrative"].lower()
    assert "surrogate" in narrative_lower or "randomforest" in narrative_lower, \
        "v0.0.2 narrative missing surrogate caveat — verify template version"

    payload_size = len(json.dumps(result))
    assert payload_size < 10_000, f"Tool 9 response {payload_size} bytes exceeds Joule 10KB"

    logger.info("Tool 9 OK — narrative=%d chars, template=%s, size=%d bytes",
                len(result["narrative"]), result["template_ref"], payload_size)
    return result


if __name__ == "__main__":
    try:
        t8 = smoke_tool_8()
        t9 = smoke_tool_9(t8)
        print("\n=== TOOL 8 OUTPUT ===")
        print(json.dumps(t8, indent=2))
        print("\n=== TOOL 9 OUTPUT ===")
        print(json.dumps(t9, indent=2))
        print("\nAll smoke tests PASSED.")
    except Exception as e:
        logger.exception("Smoke FAILED")
        sys.exit(1)
