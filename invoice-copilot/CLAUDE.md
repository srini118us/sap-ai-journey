# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

`invoice-copilot` is a SAP invoice-processing agent built with LangGraph, running on SAP AI Core / BTP. It reads invoice documents, extracts fields, validates them against S/4HANA, scores risk, and routes clean cases straight through while sending exceptions to a human.

This is a new standalone project. It sits inside the `sap-ai-journey` git repository but does not depend on the sibling folders — treat it as its own codebase.

## Architecture

A LangGraph `StateGraph` is the core of the system. Everything else is a detail hanging off it.

```
intake → extract → validate → score → route
```

| Node | Responsibility |
|---|---|
| `intake` | Accept the invoice document, normalize it into state |
| `extract` | Pull structured fields out of the document (LLM via GenAI Hub) |
| `validate` | Check extracted fields against S/4HANA master/transactional data |
| `score` | Risk score the invoice (SAP RPT-1.5, tabular prediction) |
| `route` | Clean → straight-through; exception → human-in-the-loop |

Two rules that shape the code:

- **Every model call in the graph goes through SAP AI Core.** Never call a model provider's API directly. There are two call shapes, and they are not interchangeable:
  - **LLM calls go through SAP GenAI Hub** (`gen_ai_hub` SDK against the AI Core deployment) — `genai.py`.
  - **RPT-1.5 is called as a plain AI Core inference deployment** (`POST .../v2/inference/deployments/{id}/predict`) — `rpt.py`. Not by choice: the `gen_ai_hub` SDK ships chat and embedding clients only and has no tabular client, so there is nothing to route this through.

  There is exactly one path outside AI Core, and it is deliberately narrow: **`vertex_secondopinion.py`**, a second-opinion extraction served by a private Google Cloud Run endpoint with Gemini behind it. It exists so an independently-built extractor can be compared against the SAP one — two disagreeing readings of the same invoice are a signal worth having. It is a comparison only and never the primary extraction; `extract` stays on GenAI Hub, and it is wired in as cross-model verification: `extract` fetches the second reading, `validate` compares it. Note that even here this project does not reach a model provider: it calls a Cloud Run service that holds the Gemini credentials and makes that call server-side. Adding a *second* such path needs the same justification this one had, not this bullet as precedent.
- **RPT-1.5 is for scoring, not extraction.** It is a tabular prediction model — handed a feature row, not a prompt. Field extraction is an LLM job; risk scoring is an RPT-1.5 job. Don't cross the wires.

### State object

A single state object carries the invoice through the whole graph. Each node returns a partial update rather than mutating shared state.

`second_opinion` is the one field that is deliberately *not* an error field.
It always says what happened (`extracted`, `not_extracted`, `call_failed`),
and no conditional edge reads it, because a second opinion that could not be
obtained must never change where an invoice is routed.

It includes a **`trace`** field: every node appends its decision and the reason for it. The trace is not optional and not a debug nicety — it is how the flow is audited, and it is the reason "nothing fails silently" holds in practice. A node that cannot explain its decision in the trace is not finished.

## Conventions

- **Python with a venv.** Activate before running anything.
  ```powershell
  python -m venv venv
  venv\Scripts\activate          # PowerShell
  pip install -r requirements.txt
  ```
- **Secrets come from `.env`, loaded with `python-dotenv`.** Never hardcode a credential, and never print one — not in a log line, not in a debug dump, not in a trace entry. `.env` is gitignored by the repo root `.gitignore`; `.env.example` is explicitly tracked, so keep it current with key names and placeholder values.

  The expected variables are exactly:
  ```
  AICORE_AUTH_URL, AICORE_BASE_URL, AICORE_CLIENT_ID,
  AICORE_CLIENT_SECRET, AICORE_RESOURCE_GROUP, MODEL_NAME,
  RPT_DEPLOYMENT_ID, S4_BASE_URL, S4_USER, S4_PASSWORD,
  VERTEX_EXTRACT_URL, GCP_SA_KEY_B64
  ```

  `S4_BASE_URL`, `S4_USER` and `S4_PASSWORD` belong to `s4hana.py` and nothing
  else reads them. `S4_PASSWORD` **is** a secret: it is handed to `requests`
  as basic auth and goes nowhere else — not into a URL, not into a log line,
  and not into an error message. That module reports HTTP status codes and
  exception type names only, the same discipline `rpt.py` applies to its token
  requests. `S4_BASE_URL` is a production system identifier and is read from
  `.env` for the same reason `VERTEX_EXTRACT_URL` is.
  `RPT_DEPLOYMENT_ID` is the AI Core deployment whose configuration binds
  `modelName=sap-rpt-1.5`. It is environment-specific but not a secret.

  The last two belong to `vertex_secondopinion.py` and nothing else reads them.
  `VERTEX_EXTRACT_URL` is the Cloud Run endpoint and *also* the audience the
  identity token is signed for, so it lives in one place and the two cannot
  drift apart — a mismatch surfaces as a bare 403. Like `RPT_DEPLOYMENT_ID` it
  is environment-specific rather than secret, and it is read from `.env` rather
  than hardcoded because it carries a GCP project number, which the clean-room
  rule below keeps out of source. `GCP_SA_KEY_B64` **is** a secret: it decodes
  to a service account key JSON containing a private key. No error path may
  echo it, the decoded JSON, or the minted token — that module reports
  exception type names and HTTP status codes only, the same discipline
  `rpt.py` applies to its token requests.
- **Synthetic data only.** Clean-room: no client names, no real vendor or invoice data, no production system identifiers. Sample invoices are generated, not sourced.

## Principles

1. **Nothing fails silently.** Every node logs its decision — including the boring "passed, nothing to flag" case. Swallowed exceptions and silent fallbacks are bugs, not resilience.
2. **Nodes must earn their place.** The graph stays small and legible. Before adding a node, be able to say what decision it makes that no existing node can. Prefer extending a node over adding one.

## Layout

```
src/state.py    InvoiceState, TraceEntry, trace(), new_state()
src/genai.py    the ONLY module that imports the GenAI Hub SDK
src/rpt.py      the ONLY module that calls the RPT-1.5 deployment
src/s4hana.py   the ONLY module that talks to S/4HANA
src/nodes.py    node bodies + the four conditional-edge functions
src/graph.py    build_graph() — wiring
src/samples.py  synthetic invoice text + STUB_RISK_CONTEXT
src/run_flow.py entrypoint: python -m src.run_flow

src/vertex_secondopinion.py  the ONLY module that touches Google Cloud auth
src/try_secondopinion.py     entrypoint: python -m src.try_secondopinion [invoice_id]
```

`nodes.py` imports `vertex_secondopinion.py`, and that import is
**one-directional**: `vertex_secondopinion.py` must never import `nodes.py`,
which would go circular. `try_secondopinion.py` stays off to one side — the
graph does not import it — and remains how the cross-cloud call is proven in
isolation when auth or the endpoint is in question.

Keep `vertex_secondopinion.py` transport-and-auth only: no comparison logic
and no trace entries. The comparison lives in `nodes.py`, where the two
readings are peers and the verdict is a validation issue like any other.

### The SDK import gotcha

`gen_ai_hub.proxy.native.openai.chat` constructs the AI Core proxy client on **attribute access**, reading credentials immediately. A module-level `from ... import chat` therefore raises at import time when `.env` is missing — before any node can catch it. `genai.py` imports it inside `complete()` for exactly this reason. Don't hoist it to the top of the module.

## Status

- **Real:** `extract` — calls GenAI Hub, parses JSON into `fields`, then fetches the cross-model second opinion into `second_opinion`. Verified end to end against a live deployment.
- **Real apart from OCR:** `intake` — normalizes the raw input into `document` (filename, text, line endings folded) and rejects anything unreadable. Only the OCR is missing; the normalization and the rejections survive that change, since an unreadable scan fails there exactly as blank text does now.
- **Real apart from its context rows:** `score` — calls the deployed RPT-1.5 and returns its band, distribution and explanations. Verified end to end against a live deployment. The stubbed half is `STUB_RISK_CONTEXT`; see below.
- **Real:** `validate`'s PO check — reads the PO header and items live from S/4HANA (`API_PURCHASEORDER_PROCESS_SRV`) and sums the PO total from the item rows, because the header carries none. Verified end to end against a live system.
- **Stubs:** both terminals (record only, no posting or task creation). `validate` still checks *only* the PO — the vendor master and goods receipt are not read, so "the PO names this vendor" is not yet "this vendor is who we think they are".
- **Real, and wired:** the Gemini second opinion, as cross-model verification. See below.

`validate` runs three independent checks, and all three are now real. The
line-items-sum-vs-total cross-check reads only extracted fields and catches a
number misread during extraction (a dropped cent, a transposed digit) that the
PO comparison cannot see. The cross-model check reads only extracted fields and
the second opinion. The PO check reads S/4HANA. A check that cannot run is
recorded in `validation["skipped"]` and in the trace -- "no line items
extracted" and "line items reconciled" must never look the same.

### The PO check against S/4HANA

`s4hana.py` is the only module that talks to S/4HANA. Two GETs against
`API_PURCHASEORDER_PROCESS_SRV`, because **the PO header carries no total**:
the header gives `Supplier`, `AddressName` and `DocumentCurrency`, and the
`to_PurchaseOrderItem` collection gives the rows whose
`NetPriceAmount * OrderQuantity` sum to the PO total.

Three outcomes, and conflating any two of them is the bug this design exists
to prevent:

| S/4HANA says | `validate` does | Why |
|---|---|---|
| PO found | Compares vendor, currency, amount | The check ran |
| **404 / unusable reference** | **`po_not_found` issue** | S/4HANA answered. An invoice citing a PO that does not exist is suspicious |
| **Unreachable, or refused the credentials** | **`skipped`, no issue** | Says nothing about the invoice. Failing it would punish invoices for an outage |

`fetch_purchase_order()` encodes that distinction in its contract: `found:
False` is a *return value*, `S4HANAError` is raised. Same shape as
`extract_fields()`'s `extracted: False`.

**A skipped control check is not clearance.** `route` triggers on
`CONTROL_CHECKS` — `po_exists` and `amount_matches_po` — appearing in
`skipped`, so an S/4HANA outage sends invoices to a person rather than quietly
straight-through-posting them with their PO unverified, and a PO whose total
could not be compared (no items, or another currency) does not clear on the
strength of the checks that did run. Either would be the silent pass this
whole flow exists to prevent. The cross-model check is deliberately *not* a control
check: a second opinion is supplementary and losing it must not move an
invoice. `_risk_features` reports `po_status="not_checked"` for the same
reason, rather than letting an unfetched PO fall through to `"matched"`.

Four things the PO check will not guess at, each skipped with its reason
rather than resolved by assumption:

- **Currencies that differ.** `currency_mismatch` is raised *and* the amount
  comparison is skipped: 3391.38 USD and 3391.38 EUR are not the same amount
  of money, and reporting a match would be a false clear. No FX conversion —
  that is a decision, not a default. `SAMPLE_CURRENCY_SPLIT` exercises it.
- **A PO with no items**, which has no total. Different from a total of zero.

  Both of those leave `amount_matches_po` skipped, which is a control check,
  so the invoice routes to a person rather than clearing on the checks that
  did run.
- **A PO with no address name**, which has no vendor to compare.
- **Numbers.** OData v2 renders `Edm.Decimal` as a JSON *string* (`"40.86"`),
  parsed with `Decimal` and rounded once at the end. Float would make
  `83 * 40.86` into `3391.3799999999997` and a cent-level comparison a coin
  toss.

The PO reference reaches this module from a language model reading a
supplier's document, and goes into an OData key predicate. It is pattern-
checked before any request is built, and a reference that cannot be a PO
number is reported as "not found" rather than sent. Item paging is followed to
the end: a partial sum would surface as a *false* `amount_mismatch` on a good
invoice, so hitting `MAX_ITEM_PAGES` raises instead of returning a short
total.

### Cross-model verification (the Gemini second opinion)

The work is split across two existing nodes, and **no node was added** — per
"nodes must earn their place", a `second_opinion` node would make no decision
that `extract` and `validate` do not already make between them, and would need
its own conditional edge purely to be skipped when extraction failed.

- **`extract` fetches it.** That node is where document text becomes fields, so
  it is where both readings exist as peers. It is called on the success path
  only: with no SAP fields there is nothing to compare against, the same
  reasoning that makes a rejected intake skip `extract` entirely. It never
  touches `extract`'s own decision — that stays decided by the SAP extraction
  alone — and both models' readings of the key fields land in the one trace
  entry, at the moment both were obtained.
- **`validate` compares it**, because the output is a validation issue, which
  is already that node's output shape. Keeping the call out of `validate`
  leaves every check there pure logic over state.

Compared on `CROSS_CHECK_FIELDS` — `amount`, `vendor`, `po_reference` — and not
on everything: those three decide the money, the counterparty and the
commitment. `amount` is compared as a number on `AMOUNT_TOLERANCE` (4820.5 and
4820.50 have not disagreed about anything); names and references are compared
case- and whitespace-folded. A mismatch raises one
`extraction_disagreement` issue per field, naming both models and both
readings, and `route` treats it as any other issue.

Two rules hold this together, and neither is negotiable:

1. **An unobtainable second opinion is a missing comparison, never a
   disagreement.** `call_failed` (endpoint unreachable or refusing) and
   `not_extracted` (the endpoint ran and found nothing — its own verdict, the
   analogue of `parse_failed`) both record a `second_opinion` entry in
   `validation["skipped"]` and change nothing else. An invoice must never be
   held because a cross-cloud call failed.
2. **A field only one model read is a coverage gap, not a contradiction.** It
   is skipped per-field, naming which model was silent — the same rule that
   keeps `not_checked` distinct from `no` in the score row.

Deliberately **not** a `score` feature column. There is no real disagreement
history, so every one of the 24 `STUB_RISK_CONTEXT` rows would need an invented
value for it — fabricated signal in a table whose own comments warn against
exactly that. It arrives with the real context rows, like vendor history.

`SAMPLE_SECOND_OPINION_SPLIT` (INV-1005) exercises the path: it prints both a
`Subtotal EUR 9,900.00` and an `Amount due EUR 9,450.00`, neither labelled
plainly "Total", so the two extractions can land on different ones. Everything
else about it passes, so a disagreement is the only issue it can raise. That
makes disagreement *plausible*, not certain — both models may read the same
total, which is a real outcome and not a failed test.

### Scoring with RPT-1.5

RPT-1.5 predicts **in context**: there is no training run and no fitted model.
Every call carries rows with known outcomes, which teach it the pattern, plus
the query row whose `risk_band` cell holds `[PREDICT]`. `top_k` is requested
for every band, not just the winner -- that is what turns a bare label into a
distribution, and `risk["score"]` is the probability mass on `HIGH`, *not* the
winning band's confidence. The two are different questions: a confident `LOW`
is a safe invoice, and collapsing both into one float would report it as a
risky one.

The feature row is derived from extracted fields plus what `validate` found,
which is why `score` runs after it. Columns that can be unknown say so --
`not_checked` is a distinct value from `yes` and `no`, the same rule
`validation["skipped"]` follows. A PO that was never found leaves the vendor
comparison unrun, and the context rows are kept internally consistent with
that: no synthetic row claims a verdict `validate` could not have reached.

**`STUB_RISK_CONTEXT` is the stubbed half.** Real context is settled invoices
with known outcomes from S/4HANA, and SAP recommends 500-2000 rows. Two dozen
invented rows make the call and the distribution real and the predictions
directionally sane; they do not make the scores calibrated. Vendor history is
deliberately absent as a column — with no real history there is nothing honest
to put there, and it arrives with the real context rows.

The response also carries `explanations.top_column_scores`, which the trace
records. That is the first point in this flow where a score can say *why* it
came out the way it did, so it is not optional decoration.

`extract` has three outcomes, all traced, none raising: `extracted`, `parse_failed`, `call_failed`. The latter two short-circuit past validate/score straight to `human_review` — there is nothing to validate or score without fields.

`score` follows it too: `scored`, `call_failed`, `no_prediction` (a well-formed response carrying no band for this invoice). Both failures short-circuit past `route`, because routing on a band that was never computed would be a guess wearing a decision's clothes. It is the one short-circuit that discards usable work — the invoice does have fields and validation issues, and `route` could have reached a verdict from those alone — but a straight-through posting decided without a risk score is exactly the silent pass this flow exists to prevent, and `human_review` still traces the validation issues.

`intake` follows that shape: `accepted`, `no_document` (nothing readable was handed in), `empty_document` (text arrived and it is blank). The two failures short-circuit past extract as well, so a blank document does not spend a model call to learn what intake already knows. It reports them through its own `intake_error` field rather than borrowing `extraction_error`: extract never ran, and the trail has to say which stage gave up. Rejections are explicit checks on the input, never a caught exception — a blanket `try/except` would swallow a bug in the node and report it as a bad invoice. Any node that later gains a failure mode should follow the same shape.

Without a populated `.env` the flow still runs end to end: the call fails, `extract` traces `call_failed`, and every invoice routes to human review with the reason recorded — `score` is never reached, because a failed extraction short-circuits past it. With credentials but no `RPT_DEPLOYMENT_ID`, extraction and validation run for real and `score` traces `call_failed` naming the missing key. With AI Core credentials but no `VERTEX_EXTRACT_URL`/`GCP_SA_KEY_B64`, everything runs for real and every invoice records a skipped cross-model check — routing is unchanged, which is the point. Without the `S4_*` keys the PO check records `po_exists` as skipped and every invoice goes to human review, because an unverified PO is not a cleared one.
