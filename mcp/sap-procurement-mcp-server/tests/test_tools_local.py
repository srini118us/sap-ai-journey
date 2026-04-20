"""Local smoke test for the 3 core tools.

Runs each tool as a plain Python function (no MCP transport) to verify
HANA connectivity, GenAI Hub embedding, and SQL correctness before
starting the FastMCP server.

Usage:
    cd sap-procurement-mcp-server
    python -m tests.test_tools_local
"""
import json
import logging
import sys

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

from src.tools import search_policies, get_vendor_info, get_cost_center_status


def _print_section(title):
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def _print_result(result, max_chars=800):
    text = json.dumps(result, indent=2, default=str)
    if len(text) > max_chars:
        text = text[:max_chars] + "\n  ...(truncated)"
    print(text)


def _has_error(result):
    """Return True if the result dict contains an error key."""
    return isinstance(result, dict) and "error" in result


def test_search_policies():
    _print_section("TEST 1: search_policies")
    queries = [
        "approval limit for consulting services",
        "vendor onboarding requirements",
    ]
    all_ok = True
    for q in queries:
        print(f"\n[Query] {q}")
        result = search_policies(query=q, max_results=3)
        _print_result(result)
        if _has_error(result):
            all_ok = False
        elif result.get("count", 0) == 0:
            print("  WARNING: No results returned (POLICY_CHUNKS may be empty).")
    return all_ok


def test_get_vendor_info():
    _print_section("TEST 2: get_vendor_info")
    print("\n[By name] ACME")
    result = get_vendor_info(vendor_name="ACME")
    _print_result(result)

    # An ambiguous-name error is acceptable; it means lookup itself worked
    if _has_error(result) and "Multiple" not in result.get("error", ""):
        if "candidates" not in result:
            return False

    # If a vendor_id resolved, try exact lookup too
    if "vendor_id" in result:
        vid = result["vendor_id"]
        print(f"\n[By id] {vid}")
        result2 = get_vendor_info(vendor_id=vid)
        _print_result(result2)
        return not _has_error(result2)

    # Multi-match with candidates is still a working lookup
    return "candidates" in result or "vendor_id" in result


def test_get_cost_center_status():
    _print_section("TEST 3: get_cost_center_status")
    all_ok = True
    for cc_id in ["CC-4400", "CC-1000"]:
        print(f"\n[Cost center] {cc_id}")
        result = get_cost_center_status(cost_center_id=cc_id)
        _print_result(result)
        # "not found" is data-specific, not a connectivity failure.
        # Only fail on real HANA/SQL errors.
        if _has_error(result) and "not found" not in result.get("error", ""):
            all_ok = False
    return all_ok


def main():
    tests = [
        ("search_policies", test_search_policies),
        ("get_vendor_info", test_get_vendor_info),
        ("get_cost_center_status", test_get_cost_center_status),
    ]
    results = {}
    for name, fn in tests:
        try:
            results[name] = fn()
        except Exception as exc:
            logging.exception("Test %s crashed", name)
            results[name] = False

    _print_section("SUMMARY")
    for name, ok in results.items():
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {name}")

    sys.exit(0 if all(results.values()) else 1)


if __name__ == "__main__":
    main()
