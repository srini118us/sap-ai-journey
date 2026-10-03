# SAP AI Core: tabular prediction, three ways

Working notes and runnable code from comparing three approaches to the
same prediction problem on SAP BTP: a custom XGBoost container on AI
Core, the SAP RPT-1 tabular foundation model, and HANA PAL in-database
machine learning.

The useful finding is not which model won. It is that **the three
paths fail for completely different reasons**, and which one is even
available depends on compute entitlements that are invisible until a
workload refuses to schedule.

## The distinction that explains most sandbox failures

| Workload | Runs on | Entitlement check |
|---|---|---|
| Foundation models, RPT, Orchestration, prompt templates | SAP managed infrastructure | None. Billed per token or call |
| Custom training containers | The tenant's own compute | Yes |
| Custom serving containers | The tenant's own compute | Yes |

Anything in Generative AI Hub works regardless of tenant sizing.
Anything in a custom container requests a slice of the tenant's own
Kubernetes capacity through a **resource plan**, declared as the label
`ai.sap.com/resourcePlan`.

**A resource plan the tenant is not entitled to produces indefinite
PENDING or UNKNOWN, not an error.** Nothing in the UI names the cause.
On the environment these notes come from:

| Plan | Family | Result |
|---|---|---|
| `train.l` | Training | UNKNOWN. Never submitted, never scheduled |
| `starter` | Training | PENDING. Never scheduled |
| `infer.s` | Inference | RUNNING in 2 minutes 15 seconds |

Diagnose by comparing the **Resources** tab of a stuck workload
against one that schedules. Attempting to stop a workload at UNKNOWN
returns `01010076 Invalid Request, Current status UNKNOWN cannot be
changed`, because no pod exists and there is no state to change.

## The four SAP machine learning paths

The custom container path is the one most people reach for first and
the one least often needed.

| Need | SAP option | Container? |
|---|---|---|
| LLM apps, RAG | Gen AI Hub Orchestration | No |
| Tabular prediction | SAP RPT-1 | No |
| In-database ML | HANA PAL and APL | No |
| Forecasting, classification | SAC Predictive Scenarios | No |
| Embedded in S/4 | ISLM | No |
| Notebooks and Spark | SAP Business Data Cloud (Databricks) | No |
| Custom XGBoost, PyTorch, LangGraph | AI Core BYO container | Yes |

## What is in here

```
.
├── data/generate_payments.py       synthetic data generator, seeded
├── rpt/rpt_payment_delay.py        SAP RPT-1 prediction and scoring
└── diagnostics/test_pal.py         is PAL actually usable on this instance?
```

### data/generate_payments.py

Writes seed SQL for 2000 vendor invoices. The delay label is generated
from a weighted formula over real features, so the data carries
learnable signal. Two choices are deliberate and worth knowing when
reading any model's output:

- `COMPANY_CODE` carries **zero** weight. A one-hot encoded column with
  no signal is how you check whether feature importance is telling the
  truth.
- `VENDOR_RISK_SCORE` carries the **largest** weight. Useful for testing
  whether a model finds the true strongest driver. RPT-1 ranked it
  **last** of five, which is the kind of thing you only catch when you
  know the generating process.

```bash
python data/generate_payments.py > seed_payments.sql
```

Run the verification queries at the bottom before training anything.
If the late rate does not climb across risk bands, there is no signal
and no model will find one.

### rpt/rpt_payment_delay.py

Sends a table where 100 rows carry known labels and 20 carry
`[PREDICT]`, then scores the predictions against held-back truth.

Deploy the model UI-first: **AI Launchpad > Generative AI Hub > Model
Library > filter Provider SAP > SAP RPT 1 Small > Deploy**. That button
silently creates a Configuration and a Deployment, which is why tenants
accumulate far more Configurations than Executions.

```bash
pip install sap-ai-sdk-gen hdbcli pandas
python rpt/rpt_payment_delay.py
```

**Two SDK gotchas that cost time:**

- The package is `sap-ai-sdk-gen`, not `generative-ai-hub-sdk`. The
  older 4.x package has no `gen_ai_hub.proxy.native.sap` module.
- `model_name` belongs on `predict()`, not on the `RPTClient`
  constructor.

When a signature does not match the docs, print the real one:

```bash
python -c "import inspect; from gen_ai_hub.proxy.native.sap import RPTClient; print(inspect.signature(RPTClient.predict))"
```

**On reading the output.** A run scoring 75 percent accuracy caught
only 3 of 6 late payments. Predicting "never late" on that sample would
have scored 70 percent. Read recall, not accuracy.

More interesting: **confidence did not track correctness.** Both correct
positives came at the two lowest confidences in the set (0.63, 0.64),
while three of five errors came at 0.94 or above and one wrong answer
carried confidence 1.00. Anything that auto-approves above a confidence
threshold is built on sand.

### diagnostics/test_pal.py

Answers whether PAL can actually run, rather than inferring it from
catalog tables.

```bash
pip install hana-ml hdbcli
python diagnostics/test_pal.py
```

The distinction matters because the catalog lies by omission:

| Check | Result on Free Tier | Means |
|---|---|---|
| `SYS.AFL_PACKAGES` | 3 rows: AFLPAL, APL_AREA, ERPA | Libraries **are installed** |
| `SYS.AFL_FUNCTIONS` where AREA_NAME = 'AFLPAL' | 727 | Functions **are registered** |
| `SYS.M_SERVICES` | no `scriptserver` | **No process to execute them** |
| A real PAL fit | error 34091 | Conclusive |

Registration proves installation, not capability. Only an actual call
settles it.

Script Server needs **3 vCPUs**; HANA Cloud Free Tier is fixed at **1
vCPU, 16 GB, 80 GB** and cannot be resized. The same threshold blocks
Document Store, Triple Store and the Knowledge Graph engine. The only
route is Upgrade to Paid Tier.

**A methodology note worth more than the result.** An early run of the
`AFL_PACKAGES` query returned empty and was briefly taken as proof that
PAL was absent. It was not. The session was in HANA's forced password
change state, where every statement fails silently. Any diagnostic run
during a broken session must be re-run after the session is fixed.

## HANA gotchas that cost real time

**Error 414, forced password change.** The connection handshake
succeeds and the **first statement** fails:

```
(414, 'user is forced to change password: alter password required for user DBADMIN')
```

Because connect succeeds, it reads as a query problem. Resetting again
through HANA Cloud Central does not clear it, and neither does the
Python client, **including its `newPassword=` parameter**. Only
`hdbsql` prompts interactively:

```bash
hdbsql -n <sql-endpoint>:443 -e -u DBADMIN -p <current-password>
```

It asks for the new password on the first statement issued.

**Granting AFL roles.** `GRANT AFL__SYS_AFL_AFLPAL_EXECUTE TO DBADMIN`
fails with *grantor and grantee are identical*. Create a dedicated user:

```sql
CREATE USER PAL_USER PASSWORD "<password>" NO FORCE_FIRST_PASSWORD_CHANGE;
GRANT AFL__SYS_AFL_AFLPAL_EXECUTE TO PAL_USER;
GRANT AFL__SYS_AFL_AFLPAL_EXECUTE_WITH_GRANT_OPTION TO PAL_USER;
```

**The SQL endpoint hostname.** Copy it verbatim from HANA Cloud
Central. The subdomain is `hna0`, not `hana`. Constructing it from a
remembered pattern produces `HTTP 400 Bad request`, because the client
speaks the HANA wire protocol and a web endpoint answers in HTTP.

**Free Tier instances stop nightly** and need a manual restart. One not
restarted within 30 days is deleted. A stopped instance surfaces in the
SQL editor as `Parameter resolution failed: Connection is active`,
which points nowhere useful. Check instance state before debugging SQL.

**Loading large scripts.** `\i` works for modest files. For thousands
of statements a Python loop is more reliable:

```python
import os
from hdbcli import dbapi

conn = dbapi.connect(address=os.environ["HANA_HOST"], port=443,
                     user=os.environ["HANA_USER"],
                     password=os.environ["HANA_PASSWORD"], encrypt=True)
cur = conn.cursor()
with open("seed_payments.sql", encoding="utf-8") as f:
    raw = f.read()
for chunk in raw.split(";"):
    body = "\n".join(l for l in chunk.splitlines()
                     if not l.strip().startswith("--")).strip()
    if body:
        try:
            cur.execute(body)
        except Exception as e:
            print("skip:", str(e)[:80])
conn.commit()
```

PowerShell: single quote any password containing `$` or `@`, or the
shell expands it. PowerShell also aliases `curl` to
`Invoke-WebRequest`, which takes headers as a hashtable rather than
repeated `-H` flags.

## AI Core object model, briefly

```
                    Scenario
                       |
          +------------+------------+
          |                         |
    Configuration             Configuration
   (WorkflowTemplate)        (ServingTemplate)
          |                         |
          v                         v
      Execution                 Deployment
   (Job, runs once)        (stays up, has a URL)
          |                         ^
          v                         |
    Model artifact  ----------------+
```

- **Scenario** is never created by hand. It appears when an Application
  syncs a workflow YAML carrying `scenarios.ai.sap.com/name`.
- **Configuration** is immutable. Changing a parameter means creating a
  new one, so every run traces to an exact unchanged spec.
- The **Executable type** decides what can be built. A `WorkflowTemplate`
  can only produce an Execution; a `ServingTemplate` can only produce a
  Deployment. The wrong button does not appear.
- **Artifacts** (Dataset, Model, Result Set) are typed pointers into
  object store, never the files. KServe mounts a bound Model artifact at
  `/mnt/models` when a Deployment starts.
- A **Resource Group** is literally a Kubernetes namespace, visible in
  execution logs as `namespace=rg-<id>`.

Two traps worth knowing:

- **A Scenario in the list does not prove its Application still syncs.**
  An Application pointing at a path removed by a repo restructure keeps
  its previously synced Scenario visible.
- **Execution IDs are opaque.** Two runs of different workflows look
  identical in the list. Check the Configuration on the Overview tab,
  and use `MetricTag` to label runs.

## Environment

Written against SAP AI Core (service plan `extended`) and SAP HANA
Cloud Free Tier, October 2026. Argo Workflows 4.0.6 (SAP fork) for
training, KServe for serving.

All connection details come from environment variables. Nothing in this
repo carries credentials or endpoints.

## License

MIT
