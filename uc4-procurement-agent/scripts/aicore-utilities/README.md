# SAP AI Core Utilities

Reusable scripts and helpers for SAP AI Core work across multiple labs and use cases.

## Why this exists

Every AI Core lab needs the same operational tasks: verify connectivity, create object store secrets, list resources, stop deployments to save cost. Rather than rewriting these every time, this directory provides reusable building blocks.

The scripts use raw HTTP against the SAP AI Core REST API instead of the official `ai-api-client-sdk`. The SDK has version compatibility issues with current AI Core endpoints, while raw HTTP is stable and gives full visibility.

## Folder structure

```
aicore-utilities/
├── README.md                          ← this file
├── lib/
│   ├── __init__.py
│   ├── aicore_client.py               ← reusable AI Core HTTP client
│   └── aws_helpers.py                 ← AWS credential reader
├── scripts/
│   ├── smoke_test.py                  ← verify AI Core connectivity
│   ├── list_resources.py              ← inventory of scenarios, configs, etc.
│   ├── create_object_store_secret.py  ← create per-lab S3 secret
│   └── stop_deployment.py             ← cost hygiene
└── setup/
    ├── verify_environment.sh          ← one-shot environment check
    └── requirements.txt
```

## Prerequisites

### 1. AI Core service key

Save the service key JSON from BTP Cockpit:

```bash
mkdir -p ~/.aicore
# Cockpit > ai-core service > Service Keys > View Credentials > copy JSON
nano ~/.aicore/aicore-key.json
# paste, save, exit
chmod 600 ~/.aicore/aicore-key.json
```

### 2. Python environment

```bash
cd <repo root>
python3 -m venv venv
source venv/bin/activate
pip install -r aicore-utilities/setup/requirements.txt
```

### 3. AWS CLI (for S3-backed work)

```bash
aws configure --profile aicore-test
# enter AccessKeyId, SecretAccessKey, region us-east-1
chmod 600 ~/.aws/credentials ~/.aws/config
```

## The playbook (when to run what)

### Returning to the environment

Whenever returning to work after time away, run:

```bash
bash aicore-utilities/setup/verify_environment.sh
```

Confirms service key exists, venv is active, AWS CLI works, and AI Core API responds.

### Before starting a new lab

```bash
python3 aicore-utilities/scripts/list_resources.py
```

Shows existing scenarios, configs, deployments, and secrets. Avoid creating duplicates.

### Creating a new lab

For each new lab, create a dedicated object store secret with its own S3 path prefix:

```bash
python3 aicore-utilities/scripts/create_object_store_secret.py \
    --name <secret-name> \
    --bucket <bucket-name> \
    --path-prefix <unique-prefix> \
    --aws-profile aicore-test \
    --region us-east-1
```

Naming convention: secret name matches the lab name (e.g. `supplier-prediction`, `cashflow`, `churn`).
Path prefix should match the secret name.

### Cost hygiene

Custom serving deployments (not foundation-models) consume compute hours. Stop unused ones:

```bash
# List first
python3 aicore-utilities/scripts/stop_deployment.py --list

# Stop a specific one
python3 aicore-utilities/scripts/stop_deployment.py --deployment-id <id>

# Stop all non-foundation deployments (with confirmation prompt)
python3 aicore-utilities/scripts/stop_deployment.py --all-custom
```

Foundation models (LLM serving) are typically billed per token, so leaving them running idle is cheap. Custom serving is billed per compute hour, so stopping when idle saves real money.

## Resource group conventions

Resource groups isolate scenarios and artifacts within an AI Core tenant.

Most scripts default to `default` resource group. Override with `--resource-group <name>`.

Existing resource groups observed in the tenant:

| Resource group | Purpose |
|---|---|
| `default` | General work, default for most labs |
| `ai-launchpad` | AI Launchpad managed |
| `DocumentGrounding` | RAG document grounding |
| `ml-training` | ML training experiments |

## Object store secret naming

One secret per lab, scoped to its own S3 path prefix.

| Secret name | Bucket | Path prefix | Purpose |
|---|---|---|---|
| `default` | amzn-aicore-2026 | cashflow | Time series cashflow lab |
| `supplier-prediction` | amzn-aicore-2026 | supplier-prediction | Supplier on-time delivery |

When adding a new lab, add a row here.

## AI Core API path reference

Critical reference if writing custom scripts: AI Core API paths are namespaced.

| Path family | Purpose |
|---|---|
| `/v2/admin/*` | Tenant admin: resource groups, object store secrets, applications |
| `/v2/lm/*` | Lifecycle management: scenarios, configurations, executions, deployments |

Required headers on every call:

```
Authorization: Bearer <token>
AI-Resource-Group: <resource-group-name>
```

Without the `AI-Resource-Group` header, lm endpoints return errors.

## Service key field reference

The AI Core service key JSON contains:

```json
{
  "serviceurls": {
    "AI_API_URL": "https://api.ai.prod.us-east-1.aws.ml.hana.ondemand.com"
  },
  "clientid": "sb-...",
  "clientsecret": "...",
  "url": "https://<tenant>.authentication.us10.hana.ondemand.com"
}
```

Token endpoint: `<url>/oauth/token` with `grant_type=client_credentials` and HTTP Basic auth using clientid+clientsecret.

## Common errors and fixes

| Error | Cause | Fix |
|---|---|---|
| HTTP 404 on /scenarios | SDK version issue with URL paths | Use raw HTTP via `lib/aicore_client.py` |
| HTTP 401 on any endpoint | Token expired or wrong credentials | Re-read service key, refresh token |
| HTTP 403 on admin endpoints | Service key lacks admin scope | Check service key role in BTP Cockpit |
| NameResolutionError on hostname | Truncated URL from SDK bug | Use raw HTTP, never let SDK manipulate base URL |
| AccessDenied on IAM operations | IAM user is correctly scoped (good) | This is expected for the aicore-test profile |

## Updating this README

When adding a new utility script, update this README's "Folder structure" and add a usage entry to the relevant section.
