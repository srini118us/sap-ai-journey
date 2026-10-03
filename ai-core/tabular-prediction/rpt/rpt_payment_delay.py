"""
Payment delay prediction with SAP RPT-1, a tabular foundation model.

No training. No container. No AI Core resource plan. RPT-1 predicts by
in-context learning: the prompt IS a table, where some rows carry known
labels (context) and others carry the placeholder [PREDICT].

Contrast with the XGBoost path on the same data:

    XGBoost : build image -> push -> Application -> Configuration
              -> Execution -> Model artifact -> Deployment
    RPT     : deploy from Model Library -> one API call

Prerequisites
-------------
    pip install sap-ai-sdk-gen hdbcli pandas

Note the package name. The older `generative-ai-hub-sdk` (4.x) has no
`gen_ai_hub.proxy.native.sap` module; RPT support arrived with the
rebrand to `sap-ai-sdk-gen` (7.x). That upgrade also pulls numpy 2.x
and pandas 3.x, which breaks older scikit-learn in the same
environment, so use a dedicated virtualenv.

Deploy the model first, UI-first per SAP docs:
    AI Launchpad > Generative AI Hub > Model Library
    > filter Provider: SAP > SAP RPT 1 Small > Deploy

That creates the Configuration and Deployment automatically.

Environment variables
---------------------
    AICORE_CLIENT_ID, AICORE_CLIENT_SECRET, AICORE_AUTH_URL,
    AICORE_BASE_URL, AICORE_RESOURCE_GROUP   from the AI Core service key
    HANA_HOST, HANA_PORT, HANA_USER, HANA_PASSWORD
    HANA_SCHEMA, HANA_TABLE

PowerShell: single quote any secret containing $ or @.

Run
---
    python rpt_payment_delay.py
"""
import os
import sys

import pandas as pd
from hdbcli import dbapi

CONTEXT_ROWS = int(os.environ.get("RPT_CONTEXT_ROWS", "100"))
PREDICT_ROWS = int(os.environ.get("RPT_PREDICT_ROWS", "20"))
MODEL_NAME = os.environ.get("RPT_MODEL", "sap-rpt-1-small")

TARGET = "IS_DELAYED"
KEY = "INVOICE_ID"

# Leakage columns are excluded deliberately: DELAY_DAYS gives the answer
# away, and the date columns encode it too.
FEATURES = [
    "COMPANY_CODE",
    "CATEGORY_CODE",
    "INVOICE_AMOUNT",
    "PAYMENT_TERMS_DAYS",
    "VENDOR_RISK_SCORE",
    "PRIOR_LATE_COUNT",
    "DISPUTE_FLAG",
    "APPROVAL_LEVELS",
    "PO_MATCH_FLAG",
]

SCHEMA = os.environ.get("HANA_SCHEMA", "ML_PAYMENT")
TABLE = os.environ.get("HANA_TABLE", "VENDOR_PAYMENTS")

print("=" * 64)
print(f"Payment delay prediction with {MODEL_NAME}")
print("=" * 64)

# ------------------------------------------------------------ pull source
try:
    conn = dbapi.connect(
        address=os.environ["HANA_HOST"],
        port=int(os.environ.get("HANA_PORT", "443")),
        user=os.environ["HANA_USER"],
        password=os.environ["HANA_PASSWORD"],
        encrypt=True,
    )
except KeyError as e:
    print(f"Missing environment variable: {e}")
    sys.exit(1)

cols = ", ".join([KEY] + FEATURES + [TARGET])
df = pd.read_sql(
    f"SELECT {cols} FROM {SCHEMA}.{TABLE} "
    f"ORDER BY {KEY} LIMIT {CONTEXT_ROWS + PREDICT_ROWS}",
    conn,
)
conn.close()
print(f"[1] pulled {len(df)} rows from {SCHEMA}.{TABLE}")

context_df = df.iloc[:CONTEXT_ROWS].copy()
holdout_df = df.iloc[CONTEXT_ROWS:].copy()
truth = holdout_df[TARGET].tolist()

print(f"[2] context rows  : {len(context_df)} "
      f"({context_df[TARGET].sum()} positive)")
print(f"[3] predict rows  : {len(holdout_df)} "
      f"({sum(truth)} positive, held back for scoring)")

# ------------------------------------------------- build the table prompt
def to_row(r, predict=False):
    row = {KEY: str(r[KEY])}
    for c in FEATURES:
        v = r[c]
        row[c] = float(v) if isinstance(v, (int, float)) else str(v)
    row[TARGET] = "[PREDICT]" if predict else int(r[TARGET])
    return row

rows = [to_row(r) for _, r in context_df.iterrows()]
rows += [to_row(r, predict=True) for _, r in holdout_df.iterrows()]
print(f"[4] table prompt  : {len(rows)} rows, {len(FEATURES)} features")

# ------------------------------------------------------------- call RPT-1
print(f"[5] calling {MODEL_NAME} ...")
try:
    from gen_ai_hub.proxy.native.sap import (
        RPTClient, RPTRequest, PredictionConfig, TargetColumn,
    )

    # model_name belongs on predict(), NOT on the constructor.
    client = RPTClient()
    body = RPTRequest(
        prediction_config=PredictionConfig(
            target_columns=[TargetColumn(name=TARGET,
                                         task_type="classification")]
        ),
        index_column=KEY,
        rows=rows,
    )
    resp = client.predict(body, model_name=MODEL_NAME)
except ModuleNotFoundError:
    print("    FAILED: gen_ai_hub.proxy.native.sap not found.")
    print("    Install sap-ai-sdk-gen, not generative-ai-hub-sdk.")
    sys.exit(1)
except Exception as e:
    print(f"    FAILED: {e}")
    print("    Inspect the real signatures if the SDK version differs:")
    print("      python -c \"import inspect; "
          "from gen_ai_hub.proxy.native.sap import RPTClient; "
          "print(inspect.signature(RPTClient.predict))\"")
    sys.exit(1)

# ---------------------------------------------------------------- score
# Response shape: a list of Prediction objects, each with .root =
# {KEY: ..., TARGET: [PredictionItem(prediction='0', confidence=0.97)]}
preds, confs = [], []
for item in resp:
    root = item.root if hasattr(item, "root") else item
    best = root[TARGET][0]
    preds.append(int(float(best.prediction)))
    confs.append(best.confidence)

if len(preds) != len(truth):
    print(f"    got {len(preds)} predictions for {len(truth)} rows")
    sys.exit(1)

correct = sum(p == t for p, t in zip(preds, truth))
tp = sum(p == 1 and t == 1 for p, t in zip(preds, truth))
fp = sum(p == 1 and t == 0 for p, t in zip(preds, truth))
fn = sum(p == 0 and t == 1 for p, t in zip(preds, truth))

print("[6] scored against held back labels")
print()
print(f"    accuracy  : {correct}/{len(truth)} = {correct/len(truth):.1%}")
print(f"    precision : {tp}/{tp+fp}" if tp + fp else "    precision : n/a")
print(f"    recall    : {tp}/{tp+fn}" if tp + fn else "    recall    : n/a")
print()
print(f"    {KEY:<13} {'pred':^6} {'actual':^7} confidence")
for (_, r), p, t, c in zip(holdout_df.iterrows(), preds, truth, confs):
    mark = "" if p == t else "   <-- wrong"
    print(f"    {str(r[KEY]):<13} {p:^6} {t:^7}  {c:.2f}{mark}")

print()
print("    Read recall, not accuracy. On imbalanced data a model that")
print("    predicts the majority class everywhere scores well on")
print("    accuracy and catches nothing.")
print("=" * 64)
