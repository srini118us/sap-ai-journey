"""Entrypoint: run the stubbed invoice flow end to end.

    python -m src.run_flow

Runs every synthetic sample so one command exercises both branches, and
prints each invoice's full trace.

The extract node calls SAP GenAI Hub and the score node calls SAP RPT-1.5, so
a populated .env is needed for a real run. Without one the flow still runs end
to end: the calls fail, the nodes trace `call_failed`, and every invoice is
routed to human review with the reason recorded.
"""

from .graph import build_graph
from .samples import SAMPLES
from .state import new_state


def print_trace(entries):
    """Print the audit trail, one line per node decision."""
    for e in entries:
        print(f"  {e['ts']}  {e['node']:<17} {e['decision']:<20} {e['reason']}")
        if e["data"]:
            detail = ", ".join(f"{k}={v}" for k, v in e["data"].items() if v not in (None, [], {}))
            if detail:
                print(f"  {'':<26} {'':<17} -> {detail}")


def outcome_of(result) -> str:
    """An invoice rejected at intake, or one that failed extraction or scoring,
    never reaches `route`, so it has no decision -- it is an exception by
    virtue of where it ended up."""
    decision = result.get("decision")
    return decision["outcome"] if decision else "exception"


def reason_of(result) -> str:
    """Report which stage gave up, not just that one did."""
    decision = result.get("decision")
    if decision:
        return decision["reason"]
    if result.get("intake_error"):
        return f"No usable document: {result['intake_error']}"
    if result.get("extraction_error"):
        return f"Extraction failed: {result['extraction_error']}"
    return f"Risk scoring failed: {result.get('score_error')}"


def run_one(graph, sample):
    """Run a single invoice through the graph and report its trace."""
    invoice_id = sample["invoice_id"]
    print(f"\n{'=' * 100}\nInvoice {invoice_id}\n{'=' * 100}")

    result = graph.invoke(new_state(invoice_id, sample["source"]))

    print_trace(result["trace"])
    print(f"\n  OUTCOME: {outcome_of(result).upper()} -- {reason_of(result)}")
    return result


def main():
    graph = build_graph()

    print("--- Graph topology (mermaid) ---")
    print(graph.get_graph().draw_mermaid())

    results = [run_one(graph, sample) for sample in SAMPLES]

    print(f"\n{'=' * 100}\nSummary\n{'=' * 100}")
    for r in results:
        risk = r.get("risk") or {}
        validation = r.get("validation") or {"issues": []}
        print(
            f"  {r['invoice_id']}  {outcome_of(r):<10} "
            f"risk={risk.get('band') or 'n/a':<7} issues={len(validation['issues'])}  "
            f"trace_entries={len(r['trace'])}"
        )


if __name__ == "__main__":
    main()
