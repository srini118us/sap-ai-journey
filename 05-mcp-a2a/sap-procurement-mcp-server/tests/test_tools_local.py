"""Local smoke test for all 7 MCP tools.

Calls each tool directly (no MCP protocol) against live HANA + GenAI Hub.
Run with: python -m tests.test_tools_local

Requires HANA Cloud instance to be RUNNING (not hibernated).
"""
import json
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

project_root = Path(__file__).resolve().parent.parent
load_dotenv(project_root / ".env")

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

from src.tools import (
    search_policies,
    get_vendor_info,
    get_cost_center_status,
    get_po_history,
    search_contracts,
    get_spending_summary,
    check_approval_policy,
)


def _header(n: int, name: str) -> None:
    print("\n" + "=" * 70)
    print(f"TEST {n}: {name}")
    print("=" * 70)


def _pretty(data: dict, truncate_at: int = 800) -> str:
    text = json.dumps(data, indent=2, default=str)
    if len(text) > truncate_at:
        return text[:truncate_at] + "\n  ...(truncated)"
    return text


def _is_pass(result: dict, allow_empty: bool = False) -> bool:
    err = result.get("error", "")
    if not err:
        return True
    if "not found" in err.lower() or "no vendor" in err.lower():
        return allow_empty
    return False


def main() -> None:
    results_log: list[tuple[str, bool]] = []

    # ---- TEST 1: search_policies ----
    _header(1, "search_policies")
    for q in ["approval limit for consulting services", "vendor onboarding requirements"]:
        print(f"\n[Query] {q}")
        r = search_policies(query=q, max_results=3)
        print(_pretty(r))
    results_log.append(("search_policies", _is_pass(r)))

    # ---- TEST 2: get_vendor_info ----
    _header(2, "get_vendor_info")
    for kwargs in [{"vendor_name": "ACME"}, {"vendor_id": "V-10001"}]:
        label = kwargs.get("vendor_name") or kwargs.get("vendor_id")
        tag = "By name" if "vendor_name" in kwargs else "By id"
        print(f"\n[{tag}] {label}")
        r = get_vendor_info(**kwargs)
        print(_pretty(r))
    results_log.append(("get_vendor_info", _is_pass(r)))

    # ---- TEST 3: get_cost_center_status ----
    _header(3, "get_cost_center_status")
    for cc in ["CC-4400", "CC-1000"]:
        print(f"\n[Cost center] {cc}")
        r = get_cost_center_status(cost_center_id=cc)
        print(_pretty(r))
    results_log.append(("get_cost_center_status", _is_pass(r, allow_empty=True)))

    # ---- TEST 4: get_po_history ----
    _header(4, "get_po_history")
    print("\n[Filter: vendor_id=V-10001]")
    r = get_po_history(vendor_id="V-10001", max_results=5)
    print(_pretty(r))
    pass_4a = _is_pass(r)

    print("\n[Filter: cost_center=CC-4400, days_back=365]")
    r = get_po_history(cost_center="CC-4400", days_back=365, max_results=5)
    print(_pretty(r))
    pass_4b = _is_pass(r)

    print("\n[No filters - should return error]")
    r = get_po_history()
    print(_pretty(r))
    pass_4c = "error" in r
    results_log.append(("get_po_history", pass_4a and pass_4b and pass_4c))

    # ---- TEST 5: search_contracts ----
    _header(5, "search_contracts")
    for q in ["cloud services SaaS", "consulting services annual"]:
        print(f"\n[Query] {q}")
        r = search_contracts(query=q, max_results=3)
        print(_pretty(r))
    results_log.append(("search_contracts", _is_pass(r)))

    # ---- TEST 6: get_spending_summary ----
    _header(6, "get_spending_summary")
    print("\n[By vendor V-10001, 365 days]")
    r = get_spending_summary(vendor_id="V-10001", days_back=365)
    print(_pretty(r))
    pass_6a = _is_pass(r)

    print("\n[By CC-4400, 90 days]")
    r = get_spending_summary(cost_center="CC-4400", days_back=90)
    print(_pretty(r))
    pass_6b = _is_pass(r)
    results_log.append(("get_spending_summary", pass_6a and pass_6b))

    # ---- TEST 7: check_approval_policy ----
    _header(7, "check_approval_policy")
    print("\n[Scenario: $87,500 PO for ACME on CC-4400, IT Services]")
    r = check_approval_policy(
        amount=87500,
        vendor_id="V-10001",
        cost_center="CC-4400",
        category="IT Services",
    )
    print(_pretty(r, truncate_at=1500))
    pass_7a = _is_pass(r)

    print("\n[Scenario: $5,000 small purchase, no vendor context]")
    r = check_approval_policy(amount=5000, category="Office Supplies")
    print(_pretty(r, truncate_at=1200))
    pass_7b = _is_pass(r)
    results_log.append(("check_approval_policy", pass_7a and pass_7b))

    # ---- SUMMARY ----
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    all_pass = True
    for name, passed in results_log:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"  {status} {name}")
        all_pass = all_pass and passed

    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
