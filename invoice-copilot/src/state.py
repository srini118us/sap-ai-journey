"""State schema for the invoice-copilot flow.

One InvoiceState object carries a single invoice through the whole graph.
Nodes return *partial* updates (just the keys they own); LangGraph merges
them into the running state.

`second_opinion` is the cross-model reading of the same document, fetched by
`extract` alongside the SAP one. It is never an error field: it always says
what happened (`extracted`, `not_extracted`, `call_failed`), and no
conditional edge reads it, because a second opinion that could not be obtained
must never change where an invoice is routed. `validate` turns a disagreement
into an issue; an absent second opinion becomes a skipped check.

The `trace` field is the audit record. Every node appends exactly one entry
saying what it decided and why -- including on the boring "passed, nothing
to flag" path. It is annotated with operator.add so that partial updates
concatenate: without that reducer, each node returning {"trace": [...]}
would overwrite the previous entries and the trace would keep only the last
line.
"""

import operator
from datetime import datetime, timezone
from typing import Annotated, TypedDict


class TraceEntry(TypedDict):
    """One node's decision. `data` holds small, non-secret supporting detail."""

    node: str
    decision: str
    reason: str
    ts: str
    data: dict


class InvoiceState(TypedDict):
    """Full state. Node-produced keys start as None and are filled in order.

    Nodes return a subset of these keys, which is the normal LangGraph
    pattern even though the TypedDict itself is total.
    """

    invoice_id: str
    source: dict  # raw input, exactly as handed in
    document: dict | None  # intake   -> normalized document
    intake_error: str | None  # intake   -> set when there was no usable document
    fields: dict | None  # extract  -> structured invoice fields
    extraction_error: str | None  # extract  -> set when extraction failed
    second_opinion: dict | None  # extract  -> {"status", "fields", "model", "detail"}
    validation: dict | None  # validate -> {"issues": [], "checked": [], "skipped": []}
    risk: dict | None  # score    -> {"score": float, "band": str, ...}
    score_error: str | None  # score    -> set when the RPT-1.5 call failed
    decision: dict | None  # route    -> {"outcome": str, "reason": str}
    trace: Annotated[list[TraceEntry], operator.add]


def trace(node: str, decision: str, reason: str, **data) -> list[TraceEntry]:
    """Build a one-entry trace update.

    Returns a list because the reducer concatenates lists -- a node writes
    `{"trace": trace(...)}` and LangGraph appends it to what came before.

    Never pass credentials or raw secrets in **data. The trace is printed,
    logged, and audited.
    """
    return [
        TraceEntry(
            node=node,
            decision=decision,
            reason=reason,
            ts=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            data=data,
        )
    ]


def new_state(invoice_id: str, source: dict) -> InvoiceState:
    """Build a complete initial state for one invoice."""
    return InvoiceState(
        invoice_id=invoice_id,
        source=source,
        document=None,
        intake_error=None,
        fields=None,
        extraction_error=None,
        second_opinion=None,
        validation=None,
        risk=None,
        score_error=None,
        decision=None,
        trace=[],
    )
