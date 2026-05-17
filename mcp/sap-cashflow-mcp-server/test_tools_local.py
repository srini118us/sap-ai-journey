"""Local smoke test of the two MCP tool functions (no FastMCP server).

Exercises tools as plain Python — proves tool code is correct independent
of MCP transport, FastMCP version, etc.
"""
import os
import json
import sys
from dotenv import load_dotenv

load_dotenv()

# Import tool implementations directly
from src.tools.explain_cashflow_full import explain_cashflow_full
from src.tools.explain_cashflow_template import explain_cashflow_template


def banner(msg):
    print()
    print("=" * 70)
    print(f" {msg}")
    print("=" * 70)


def assert_keys(d, required, label):
    missing = [k for k in required if k not in d]
    if missing:
        print(f"[FAIL] {label}: missing keys {missing}")
        print(f"       Got keys: {list(d.keys())}")
        return False
    print(f"[PASS] {label}: all required keys present")
    return True


def short(value, limit=200):
    s = str(value)
    return s if len(s) <= limit else s[:limit] + "..."


# -------- Test 1: Tool 8 standalone --------
banner("TEST 1: Tool 8 — explain_cashflow_full(company_code='1010')")
try:
    result_t8 = explain_cashflow_full("1010")
    print(f"Got dict with {len(result_t8)} keys.")
    print(f"  company_code: {result_t8.get('company_code')}")
    print(f"  forecast:     {result_t8.get('forecast')}")
    print(f"  best_model:   {result_t8.get('best_model')}")
    print(f"  top_features count: {len(result_t8.get('top_features', []))}")
    print(f"  has narrative? {'narrative' in result_t8}  (should be False)")
    print(f"  surrogate_caveat: {short(result_t8.get('surrogate_caveat'))}")

    t1_ok = (
        assert_keys(result_t8, ["company_code", "forecast", "top_features", "best_model", "surrogate_caveat"], "Tool 8 schema")
        and "narrative" not in result_t8  # narrative deliberately stripped
        and abs(result_t8["forecast"] - 8494.45) < 1.0  # matches UC2.6 baseline
    )
    print(f"[{'PASS' if t1_ok else 'FAIL'}] Test 1 overall")
except Exception as e:
    print(f"[FAIL] Test 1 raised exception: {type(e).__name__}: {e}")
    t1_ok = False
    result_t8 = None


# -------- Test 2: Tool 9 standalone --------
banner("TEST 2: Tool 9 — explain_cashflow_template(standalone)")
sample_features = [
    {"name": "dom", "shap_value": 4972.12},
    {"name": "lag_14", "shap_value": 1021.10},
    {"name": "dow", "shap_value": 1012.08},
]
try:
    result_t9 = explain_cashflow_template(
        company_code="1010",
        forecast=8494.45,
        forecast_date="2026-04-30T00:00:00",
        best_model="UnivariateMotif",
        top_features=sample_features,
    )
    print(f"Got dict with {len(result_t9)} keys: {list(result_t9.keys())}")
    print(f"  narrative (first 300 chars): {short(result_t9.get('narrative'), 300)}")
    t2_ok = (
        "narrative" in result_t9
        and isinstance(result_t9["narrative"], str)
        and len(result_t9["narrative"]) > 50  # actual content, not empty
    )
    print(f"[{'PASS' if t2_ok else 'FAIL'}] Test 2 overall")
except Exception as e:
    print(f"[FAIL] Test 2 raised exception: {type(e).__name__}: {e}")
    t2_ok = False


# -------- Test 3: Chained Tool 8 -> Tool 9 --------
banner("TEST 3: Chained — Tool 8 output piped into Tool 9")
if not t1_ok or result_t8 is None:
    print("[SKIP] Test 1 didn't pass, can't chain.")
    t3_ok = False
else:
    try:
        result_t9_chained = explain_cashflow_template(
            company_code=result_t8["company_code"],
            forecast=result_t8["forecast"],
            forecast_date=result_t8["forecast_date"],
            best_model=result_t8["best_model"],
            top_features=result_t8["top_features"],
        )
        print(f"  narrative (first 300 chars): {short(result_t9_chained.get('narrative'), 300)}")
        t3_ok = (
            "narrative" in result_t9_chained
            and isinstance(result_t9_chained["narrative"], str)
            and len(result_t9_chained["narrative"]) > 50
        )
        print(f"[{'PASS' if t3_ok else 'FAIL'}] Test 3 overall")
    except Exception as e:
        print(f"[FAIL] Test 3 raised exception: {type(e).__name__}: {e}")
        t3_ok = False


# -------- Summary --------
banner("SUMMARY")
print(f"  Test 1 (Tool 8 standalone):           {'PASS' if t1_ok else 'FAIL'}")
print(f"  Test 2 (Tool 9 standalone):           {'PASS' if t2_ok else 'FAIL'}")
print(f"  Test 3 (Chained Tool 8 -> Tool 9):    {'PASS' if t3_ok else 'FAIL'}")
print()
sys.exit(0 if (t1_ok and t2_ok and t3_ok) else 1)
