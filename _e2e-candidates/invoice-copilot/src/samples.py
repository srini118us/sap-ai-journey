"""Synthetic invoice documents and a stand-in PO ledger.

Clean-room, with exactly one documented exception. Every vendor, PO number and
amount here is invented, except SAMPLE_CLEAN, which is keyed to a purchase
order that really exists in the connected S/4HANA sandbox -- see its comment.
That is what makes the live PO lookup testable end to end; nothing else here
comes from a real system, and nothing else should.

Invoices carry plain text -- that is what the extract node sends to the model,
the way a real document would arrive after OCR. Nothing here is pre-structured,
so extraction is a genuine task rather than a passthrough.

SAMPLE_CLEAN routes straight through, and is the one sample whose PO is real:
it exercises the live S/4HANA match path. SAMPLE_EXCEPTION cites a PO that does not
exist in S/4HANA and is large enough to score HIGH, so one run exercises both
exception triggers. SAMPLE_LINE_ITEM_DRIFT's own line items do not add up to its
stated total -- the one discrepancy no PO comparison can see, and it is raised
whether or not the PO is found.
SAMPLE_SECOND_OPINION_SPLIT prints two defensible totals, so the two
independent extractions may well read different amounts off it -- the
cross-model check is the only one with anything to say about it.
SAMPLE_CURRENCY_SPLIT cites the same real PO as SAMPLE_CLEAN but bills in EUR
against a USD order, so the amounts cannot be compared at all.
SAMPLE_EMPTY never gets as far as extraction: it carries no readable text, so
intake rejects it and it exercises the short-circuit straight to the human.
"""

SAMPLE_CLEAN = {
    "invoice_id": "INV-1001",
    "source": {
        "filename": "INV-1001.pdf",
        "received_at": "2026-09-01T09:14:00Z",
        # THE ONE NON-CLEAN-ROOM SAMPLE, on purpose and documented here.
        # PO 4500000672 really exists in the connected S/4HANA sandbox, where
        # it carries vendor "EV Parts Inc." and a single item of 83 @ 40.86 USD
        # -- a total of 3,391.38 that `validate` now sums from the live item
        # rows rather than reading out of a stub. Without one sample keyed to
        # real master data there is no way to prove the match path works; every
        # other sample stays invented. Sandbox demo data, not client data.
        #
        # Deliberately denominated in USD, not EUR like the rest. The PO is in
        # USD, and an EUR invoice against it would trip currency_mismatch and
        # skip the amount comparison -- so the one thing this sample exists to
        # prove, that a real PO total reconciles to the cent, would never run.
        "text": """EV PARTS INC.
2100 Harbor Boulevard, Detroit, MI 48226, United States
EIN 00-0000000

INVOICE

Invoice number:   INV-1001
Invoice date:     28 August 2026
Purchase order:   4500000672
Payment terms:    Net 30

Bill to:
  Contoso Manufacturing NV
  Havenlaan 12, 1000 Brussels, Belgium

--------------------------------------------------------------------
Description                        Qty     Unit price       Amount
--------------------------------------------------------------------
Battery module housing              83          40.86      3,391.38
--------------------------------------------------------------------
                                            Total USD      3,391.38
--------------------------------------------------------------------

Remit to account 0000000000 / routing 000000000
Questions: ar@evparts.example
""",
    },
}


SAMPLE_EXCEPTION = {
    "invoice_id": "INV-1002",
    "source": {
        "filename": "INV-1002.pdf",
        "received_at": "2026-09-02T16:41:00Z",
        # PO-77004 does not exist in S/4HANA, so validate raises po_not_found,
        # and the size pushes the risk band to HIGH -- both exception triggers.
        "text": """\
CALDERON INDUSTRIAL SA
Poligono Industrial Norte 8, 28850 Madrid, Spain
NIF A12345678

INVOICE

Invoice number:   INV-1002
Invoice date:     30 August 2026
Purchase order:   PO-77004
Payment terms:    Net 45

Bill to:
  Contoso Manufacturing NV
  Havenlaan 12, 1000 Brussels, Belgium

--------------------------------------------------------------------
Description                        Qty     Unit price       Amount
--------------------------------------------------------------------
Pump housing, cast                  50       1,825.00     91,250.00
--------------------------------------------------------------------
                                            Total EUR     91,250.00
--------------------------------------------------------------------

Remit to IBAN ES00 0000 0000 0000 0000 0000
Questions: cobros@calderon-industrial.example
""",
    },
}


SAMPLE_LINE_ITEM_DRIFT = {
    "invoice_id": "INV-1003",
    "source": {
        "filename": "INV-1003.pdf",
        "received_at": "2026-09-03T11:02:00Z",
        # The document contradicts itself: the two line amounts sum to 7,318.25
        # but the printed total says 7,318.75. Each line is internally consistent
        # (qty * unit price checks out), so a faithful extraction reproduces the
        # discrepancy rather than inventing it. PO-90455 does not exist in
        # S/4HANA, which is the point of running this one anyway: the
        # line-items check needs no PO and fires regardless.
        "text": """HALVORSEN TOOLING AS
Nedre Storgate 19, 3015 Drammen, Norway
Org. nr. NO 999 888 777 MVA

INVOICE

Invoice number:   INV-1003
Invoice date:     01 September 2026
Purchase order:   PO-90455
Payment terms:    Net 30

Bill to:
  Contoso Manufacturing NV
  Havenlaan 12, 1000 Brussels, Belgium

--------------------------------------------------------------------
Description                        Qty     Unit price       Amount
--------------------------------------------------------------------
Carbide insert, CNMG 120408        125          38.50      4,812.50
Tool holder, MTJNR 2020K16          15         167.05      2,505.75
--------------------------------------------------------------------
                                            Total EUR      7,318.75
--------------------------------------------------------------------

Remit to IBAN NO00 0000 0000 000
Questions: faktura@halvorsen-tooling.example
""",
    },
}


SAMPLE_SECOND_OPINION_SPLIT = {
    "invoice_id": "INV-1005",
    "source": {
        "filename": "INV-1005.pdf",
        "received_at": "2026-09-05T08:37:00Z",
        # Two defensible answers to "what is the total?". The goods lines sum
        # to 9,900.00, printed as `Subtotal EUR`; a credit note line then takes
        # 450.00 back off and the document closes on `Amount due EUR 9,450.00`.
        # Neither line is labelled plainly "Total", so a faithful extractor can
        # land on either, and two independently-built ones plausibly land on
        # different ones -- which is the whole point of asking twice.
        #
        # Everything else is built so the cross-model check is the ONLY check
        # with anything to say, the way INV-1003 isolates amount_inconsistent:
        # the credit note is itself a line item, so the three line amounts sum
        # to 9,450.00 and reconcile against the amount-due reading. PO-61870
        # does not exist in S/4HANA, so po_not_found is raised alongside the
        # disagreement; the trace keeps the two apart.
        #
        # Being honest about what this sample does and does not guarantee: it
        # makes disagreement *plausible*, not certain. Both models may read the
        # same total, in which case the check passes and records that they
        # agreed -- which is a real outcome, not a failed test. The path that
        # IS deterministic here is the degradation one: with no GCP settings in
        # .env the second opinion comes back `call_failed` for every invoice,
        # the comparison is recorded as skipped, and routing is unchanged.
        "text": """MERIDIAN WERKZEUGBAU GMBH
Am Alten Hafen 7, 28217 Bremen, Germany
VAT DE822345678

INVOICE

Invoice number:   INV-1005
Invoice date:     03 September 2026
Purchase order:   PO-61870
Payment terms:    Net 30

Bill to:
  Contoso Manufacturing NV
  Havenlaan 12, 1000 Brussels, Belgium

--------------------------------------------------------------------
Description                        Qty     Unit price       Amount
--------------------------------------------------------------------
Machining centre retrofit kit        1       6,200.00      6,200.00
Installation labour, 74 hrs         74          50.00      3,700.00
--------------------------------------------------------------------
                                         Subtotal EUR      9,900.00

Credit note CN-2214, returned spindle                       -450.00
--------------------------------------------------------------------
                                       Amount due EUR      9,450.00
--------------------------------------------------------------------

Remit to IBAN DE00 1111 1111 1111 1111 11
Questions: rechnung@meridian-werkzeugbau.example
""",
    },
}


SAMPLE_CURRENCY_SPLIT = {
    "invoice_id": "INV-1006",
    "source": {
        "filename": "INV-1006.pdf",
        "received_at": "2026-09-06T13:20:00Z",
        # Cites the same real PO as SAMPLE_CLEAN (4500000672, USD) but bills in
        # EUR. Everything else lines up: the vendor is the one on the PO, and
        # the single line reconciles to the stated total.
        #
        # So the only thing wrong is the currency -- and the consequence is the
        # point of the sample. `validate` raises currency_mismatch AND skips
        # the amount comparison, because 3,120.80 EUR and 3,391.38 USD are not
        # two readings of one number and no exchange rate is applied anywhere
        # in this flow. A skipped amount comparison is a control check that did
        # not run, so `route` sends this to a person even though nothing has
        # been shown to be wrong with the money itself.
        #
        # Non-clean-room in the same, documented way SAMPLE_CLEAN is: it has to
        # name a PO that really exists to reach the comparison at all.
        "text": """EV PARTS INC.
2100 Harbor Boulevard, Detroit, MI 48226, United States
EIN 00-0000000

INVOICE

Invoice number:   INV-1006
Invoice date:     04 September 2026
Purchase order:   4500000672
Payment terms:    Net 30

Bill to:
  Contoso Manufacturing NV
  Havenlaan 12, 1000 Brussels, Belgium

--------------------------------------------------------------------
Description                        Qty     Unit price       Amount
--------------------------------------------------------------------
Battery module housing              83          37.60      3,120.80
--------------------------------------------------------------------
                                            Total EUR      3,120.80
--------------------------------------------------------------------

Remit to IBAN DE00 2222 2222 2222 2222 22
Questions: ar@evparts.example
""",
    },
}


# A document that arrived carrying nothing readable. Intake rejects it before
# extraction spends a model call to discover the same thing, so the run
# exercises the short-circuit out of intake.
SAMPLE_EMPTY = {
    "invoice_id": "INV-1004",
    "source": {
        "filename": "INV-1004.pdf",
        "received_at": "2026-09-04T16:02:00Z",
        "text": "   \n\n\t  \n",
    },
}


SAMPLES = [
    SAMPLE_CLEAN,
    SAMPLE_EXCEPTION,
    SAMPLE_LINE_ITEM_DRIFT,
    SAMPLE_SECOND_OPINION_SPLIT,
    SAMPLE_CURRENCY_SPLIT,
    SAMPLE_EMPTY,
]


# Labeled history for the RPT-1.5 risk model. RPT-1.5 predicts in context --
# there is no training run -- so every scoring call carries rows like these
# with known outcomes, and the model infers the pattern from them.
#
# STUB: these are invented. The real context is settled invoices with known
# outcomes read from S/4HANA, and SAP recommends 500-2000 rows for a useful
# trade-off between quality, latency and cost. Two dozen synthetic rows make
# the call real and the predictions directionally sane; they do not make the
# scores calibrated, and nothing here should be read as a tuned model.
#
# Clean-room like the rest of this file: no real vendor, amount, or outcome.
#
# The columns mirror exactly what the score node can derive from extracted
# fields plus validation output, and the values stay internally consistent
# with what `validate` can actually produce -- a PO that was never found
# leaves the vendor unchecked, so those rows carry vendor_known="not_checked"
# rather than a verdict validate could not have reached.
#
# Vendor history is the one signal deliberately absent: with no real history
# there is nothing honest to put in such a column. It arrives with the real
# context rows, not before.
#
# The currency mix is deliberate and load-bearing, not decoration. An earlier
# version carried three USD rows, one per band -- balanced across bands, but
# each sitting near the top of its band's amount range, so currency tracked
# amount and RPT-1.5 read it as the second-strongest risk driver. It is not
# one. USD now sits on three rows per band at the same amount ranks in every
# band (1st, 4th and 7th of eight, sorted by amount), which is what makes the
# column uninformative rather than merely even. Keep that shape if you edit
# these rows: a column that carries no signal has to be built to carry none.
STUB_RISK_CONTEXT = [
    # Small, clean, everything reconciles.
    {"invoice_id": "H-01", "amount": 320.00, "currency": "USD", "po_status": "matched", "vendor_known": "yes", "line_items_reconcile": "yes", "risk_band": "LOW"},
    {"invoice_id": "H-02", "amount": 480.50, "currency": "EUR", "po_status": "matched", "vendor_known": "yes", "line_items_reconcile": "yes", "risk_band": "LOW"},
    {"invoice_id": "H-03", "amount": 1250.00, "currency": "USD", "po_status": "matched", "vendor_known": "yes", "line_items_reconcile": "yes", "risk_band": "LOW"},
    {"invoice_id": "H-04", "amount": 2100.75, "currency": "EUR", "po_status": "matched", "vendor_known": "yes", "line_items_reconcile": "yes", "risk_band": "LOW"},
    {"invoice_id": "H-05", "amount": 3400.00, "currency": "EUR", "po_status": "matched", "vendor_known": "yes", "line_items_reconcile": "yes", "risk_band": "LOW"},
    {"invoice_id": "H-06", "amount": 890.25, "currency": "EUR", "po_status": "matched", "vendor_known": "yes", "line_items_reconcile": "yes", "risk_band": "LOW"},
    {"invoice_id": "H-07", "amount": 4100.00, "currency": "USD", "po_status": "matched", "vendor_known": "yes", "line_items_reconcile": "yes", "risk_band": "LOW"},
    {"invoice_id": "H-08", "amount": 6800.00, "currency": "EUR", "po_status": "matched", "vendor_known": "yes", "line_items_reconcile": "yes", "risk_band": "LOW"},
    # Mid-range, or clean but larger, or one check unhappy.
    {"invoice_id": "H-09", "amount": 9800.00, "currency": "USD", "po_status": "matched", "vendor_known": "yes", "line_items_reconcile": "no", "risk_band": "MEDIUM"},
    {"invoice_id": "H-10", "amount": 12400.00, "currency": "EUR", "po_status": "mismatched", "vendor_known": "yes", "line_items_reconcile": "yes", "risk_band": "MEDIUM"},
    {"invoice_id": "H-11", "amount": 15200.00, "currency": "USD", "po_status": "mismatched", "vendor_known": "yes", "line_items_reconcile": "yes", "risk_band": "MEDIUM"},
    {"invoice_id": "H-12", "amount": 11000.00, "currency": "EUR", "po_status": "matched", "vendor_known": "yes", "line_items_reconcile": "not_checked", "risk_band": "MEDIUM"},
    {"invoice_id": "H-13", "amount": 18500.00, "currency": "EUR", "po_status": "matched", "vendor_known": "no", "line_items_reconcile": "yes", "risk_band": "MEDIUM"},
    {"invoice_id": "H-14", "amount": 22000.00, "currency": "EUR", "po_status": "matched", "vendor_known": "yes", "line_items_reconcile": "no", "risk_band": "MEDIUM"},
    {"invoice_id": "H-15", "amount": 26000.00, "currency": "USD", "po_status": "matched", "vendor_known": "yes", "line_items_reconcile": "yes", "risk_band": "MEDIUM"},
    {"invoice_id": "H-16", "amount": 31000.00, "currency": "EUR", "po_status": "matched", "vendor_known": "yes", "line_items_reconcile": "yes", "risk_band": "MEDIUM"},
    # Large, and something is wrong with most of them.
    {"invoice_id": "H-17", "amount": 48000.00, "currency": "USD", "po_status": "not_found", "vendor_known": "not_checked", "line_items_reconcile": "no", "risk_band": "HIGH"},
    {"invoice_id": "H-18", "amount": 51000.00, "currency": "EUR", "po_status": "mismatched", "vendor_known": "yes", "line_items_reconcile": "no", "risk_band": "HIGH"},
    {"invoice_id": "H-19", "amount": 56000.00, "currency": "EUR", "po_status": "matched", "vendor_known": "no", "line_items_reconcile": "no", "risk_band": "HIGH"},
    {"invoice_id": "H-20", "amount": 64000.00, "currency": "USD", "po_status": "not_found", "vendor_known": "not_checked", "line_items_reconcile": "no", "risk_band": "HIGH"},
    {"invoice_id": "H-21", "amount": 72500.00, "currency": "EUR", "po_status": "mismatched", "vendor_known": "no", "line_items_reconcile": "no", "risk_band": "HIGH"},
    {"invoice_id": "H-22", "amount": 88000.00, "currency": "EUR", "po_status": "not_found", "vendor_known": "not_checked", "line_items_reconcile": "yes", "risk_band": "HIGH"},
    {"invoice_id": "H-23", "amount": 95000.00, "currency": "USD", "po_status": "mismatched", "vendor_known": "yes", "line_items_reconcile": "no", "risk_band": "HIGH"},
    {"invoice_id": "H-24", "amount": 120000.00, "currency": "EUR", "po_status": "not_found", "vendor_known": "not_checked", "line_items_reconcile": "no", "risk_band": "HIGH"},
]
