"""Entrypoint: exercise the second-opinion extraction on its own.

    python -m src.try_secondopinion            # the first synthetic sample
    python -m src.try_secondopinion INV-1003   # a specific one

The graph does not call this path yet. This script is how the cross-cloud
call gets proven -- auth, endpoint, response shape -- before any node depends
on it.

Like `run_flow`, it runs to completion without credentials: the call fails,
the failure is printed with the reason, and the exit code says so. It never
stack-traces on a configuration problem.

Nothing here prints a credential. The failures reported by
`vertex_secondopinion` are already type- and status-only.
"""

import json
import sys

from . import vertex_secondopinion as second
from .samples import SAMPLES


def pick_sample(invoice_id: str | None) -> dict:
    """The named sample, or the first one that actually carries text.

    SAMPLE_EMPTY is in SAMPLES on purpose -- it is the intake rejection case --
    and sending it would test nothing but the guard in extract_fields().
    """
    if invoice_id:
        for sample in SAMPLES:
            if sample["invoice_id"] == invoice_id:
                return sample
        known = ", ".join(s["invoice_id"] for s in SAMPLES)
        raise SystemExit(f"No sample {invoice_id}. Known samples: {known}")

    for sample in SAMPLES:
        if (sample["source"].get("text") or "").strip():
            return sample
    raise SystemExit("No sample carries any invoice text.")


def main() -> int:
    sample = pick_sample(sys.argv[1] if len(sys.argv) > 1 else None)
    text = sample["source"]["text"]

    print(f"Invoice {sample['invoice_id']} -- {len(text)} characters of text")

    # Resolved before the call so a missing URL is reported as configuration
    # rather than as a failed request.
    try:
        print(f"Endpoint: {second.endpoint_url()}")
    except second.VertexSecondOpinionError as e:
        print(f"\nNOT CONFIGURED: {e}")
        return 2

    try:
        result = second.extract_fields(text)
    except second.VertexSecondOpinionError as e:
        print(f"\nCALL FAILED: {e}")
        return 1

    if not result["extracted"]:
        print("\nEXTRACTED: no -- the endpoint ran and returned no fields.")
        return 0

    print(f"\nEXTRACTED: yes -- {len(result['fields'])} field(s) from {result['model']}")
    print(json.dumps(result["fields"], indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
