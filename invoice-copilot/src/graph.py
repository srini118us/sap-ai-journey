"""Graph assembly.

intake -+-> extract -+-> validate -> score -+-> route -+-> straight_through -> END
        |            |                          |          +-> human_review  -> END
        |            |                          +-> human_review (scoring failed)
        |            +-> human_review (extraction failed) ------------------> END
        +-> human_review (no usable document) ---------------------------> END

The two terminals are real nodes, not a collapsed edge into END: they are
where genuinely different downstream work lands (posting vs. queueing for a
person), and as nodes they keep the branch visible in the topology.

Three branches short-circuit to the human, for the same reason. After
`extract`, a failed extraction skips validate and score: there is nothing to
validate or score without fields. After `intake`, a rejected document skips
extraction too: there is nothing to extract from, and sending an empty
document to the model would spend a call to learn what intake already knows.
After `score`, a failed RPT-1.5 call skips routing: routing on a risk band
that was never computed would be a guess wearing a decision's clothes.

The scoring branch is the one short-circuit that discards work -- the invoice
does have fields and validation results, and `route` could have reached a
verdict from the validation issues alone. It is still the right call: a
straight-through posting decided without a risk score is exactly the silent
pass this flow exists to prevent. Nothing is lost from the audit trail, since
`human_review` traces the validation issues either way.

Having the skipped nodes no-op defensively would be worse than not visiting
them -- a node that runs on nothing and reports nothing is exactly the silent
pass the trace exists to prevent.
"""

from langgraph.graph import END, START, StateGraph

from . import nodes
from .state import InvoiceState


def build_graph():
    """Wire the nodes and compile the flow."""
    builder = StateGraph(InvoiceState)

    builder.add_node("intake", nodes.intake)
    builder.add_node("extract", nodes.extract)
    builder.add_node("validate", nodes.validate)
    builder.add_node("score", nodes.score)
    builder.add_node("route", nodes.route)
    builder.add_node("straight_through", nodes.straight_through)
    builder.add_node("human_review", nodes.human_review)

    builder.add_edge(START, "intake")

    builder.add_conditional_edges(
        "intake",
        nodes.select_after_intake,
        {"extract": "extract", "human_review": "human_review"},
    )

    builder.add_conditional_edges(
        "extract",
        nodes.select_after_extract,
        {"validate": "validate", "human_review": "human_review"},
    )

    builder.add_edge("validate", "score")

    builder.add_conditional_edges(
        "score",
        nodes.select_after_score,
        {"route": "route", "human_review": "human_review"},
    )

    builder.add_conditional_edges(
        "route",
        nodes.select_outcome,
        {"straight_through": "straight_through", "human_review": "human_review"},
    )

    builder.add_edge("straight_through", END)
    builder.add_edge("human_review", END)

    return builder.compile()
