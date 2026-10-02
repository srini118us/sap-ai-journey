"""
UC2.5 promote.py — automatic model promotion to live deployments.

Runs as the second step of a scheduled Argo workflow (cashflow-promote).
Polls AI Core's REST API for the newest trained_model artifact in the
cashflow-forecast scenario, registers it as a Model if not yet registered,
creates two new Configurations (one per company), and PATCHes both
UC2.4 deployments to point at the new Configurations.

Idempotent: if the newest Model is already what current deployments are
bound to, exits with [skip] and no churn.

Authenticates to AI Core via a Generic Secret named 'aicore-self-creds'
mounted as env vars (mirrors the hana-cashflow-creds pattern from UC2.1).

Required env vars (from secret):
    AICORE_CLIENT_ID, AICORE_CLIENT_SECRET, AICORE_AUTH_URL, AICORE_API_URL
Required env vars (from workflow YAML):
    AICORE_RESOURCE_GROUP, SCENARIO_ID
"""
import json
import os
import sys
from datetime import datetime
from typing import Any

import requests


# ---- CONFIG -----------------------------------------------------------------

AUTH_URL = os.environ["AICORE_AUTH_URL"]
API_URL = os.environ["AICORE_API_URL"]
CLIENT_ID = os.environ["AICORE_CLIENT_ID"]
CLIENT_SECRET = os.environ["AICORE_CLIENT_SECRET"]
RESOURCE_GROUP = os.environ.get("AICORE_RESOURCE_GROUP", "ml-training")
SCENARIO_ID = os.environ.get("SCENARIO_ID", "cashflow-forecast")

# Each Configuration binds one .pkl filename. Both bind the same Model artifact.
COMPANY_TO_PKL = {
    "1010": "model_1010.pkl",
    "1710": "model_1710.pkl",
}

# The serving Executable that all promote-created Configurations bind to.
# This is the UC2.4 ServingTemplate; doesn't change across promote runs.
SERVING_EXECUTABLE = "cashflow-forecast-serve"


# ---- AUTH -------------------------------------------------------------------

def get_token() -> str:
    print(f"[auth] requesting token from {AUTH_URL}/oauth/token")
    resp = requests.post(
        f"{AUTH_URL}/oauth/token",
        params={"grant_type": "client_credentials"},
        auth=(CLIENT_ID, CLIENT_SECRET),
        timeout=30,
    )
    resp.raise_for_status()
    token = resp.json()["access_token"]
    print(f"[auth] token acquired (length={len(token)})")
    return token


def headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "AI-Resource-Group": RESOURCE_GROUP,
        "Content-Type": "application/json",
    }


# ---- AI CORE API CALLS ------------------------------------------------------

def call_with_diagnostics(method: str, url: str, h: dict, **kwargs):
    """Wraps requests calls so 4xx errors include the response body in the
    exception message, not just the status. AI Core's 4xx bodies usually
    explain what's wrong; without this wrapper we lose them."""
    resp = requests.request(method, url, headers=h, timeout=30, **kwargs)
    if not resp.ok:
        body = resp.text[:500] if resp.text else "<empty>"
        raise RuntimeError(
            f"{method} {url} returned {resp.status_code}: {body}"
        )
    return resp


def list_executions_completed(h: dict) -> list[dict]:
    """List COMPLETED Executions for the scenario, newest first."""
    resp = call_with_diagnostics(
        "GET", f"{API_URL}/v2/lm/executions", h,
        params={"scenarioId": SCENARIO_ID, "status": "COMPLETED", "$top": 50},
    )
    items = resp.json().get("resources", [])
    items.sort(key=lambda x: x.get("startTime", ""), reverse=True)
    return items


def list_models(h: dict) -> list[dict]:
    """List Model artifacts (kind=model) for the scenario, newest first."""
    resp = call_with_diagnostics(
        "GET", f"{API_URL}/v2/lm/artifacts", h,
        params={"scenarioId": SCENARIO_ID, "kind": "model", "$top": 100},
    )
    items = resp.json().get("resources", [])
    items.sort(key=lambda x: x.get("createdAt", ""), reverse=True)
    return items


def find_model_for_execution(models: list[dict], execution_id: str) -> dict | None:
    """A Model auto-registered (or manually registered with the right URL)
    will have URL ending in /<execution-id>/trained_model. Match on that."""
    suffix = f"/{execution_id}/trained_model"
    for m in models:
        url = m.get("url", "")
        if url.endswith(suffix):
            return m
    return None


def register_model(h: dict, execution_id: str) -> dict:
    """Manually register a Model artifact for the given Execution.
    Mirrors the manual UC2.4 fix for the auto-registration unreliability."""
    name = f"cashflow-promoted-{execution_id[:8]}"
    payload = {
        "name": name,
        "kind": "model",
        "url": f"ai://default/{execution_id}/trained_model",
        "scenarioId": SCENARIO_ID,
        "description": f"Auto-promoted by UC2.5 promote.py from execution {execution_id}",
    }
    print(f"[register] creating Model: name={name}, url={payload['url']}")
    resp = call_with_diagnostics(
        "POST", f"{API_URL}/v2/lm/artifacts", h, json=payload,
    )
    model = resp.json()
    print(f"[register] Model created: id={model['id']}")
    return model


def create_configuration(h: dict, company: str, model_id: str) -> dict:
    """Create a new Configuration binding the new Model + the company's pkl.

    Body schema uses snake_case per the SAP AI Core SDK convention
    (parameter_bindings, input_artifact_bindings) — camelCase variants are
    silently rejected by the API gateway as 404, not 400.
    """
    timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    name = f"cashflow-serve-{company}-promoted-{timestamp}"
    payload = {
        "name": name,
        "scenarioId": SCENARIO_ID,
        "executableId": SERVING_EXECUTABLE,
        "parameterBindings": [
            {"key": "model_filename", "value": COMPANY_TO_PKL[company]},
        ],
        "inputArtifactBindings": [
            {"key": "cashflowmodel", "artifactId": model_id},
        ],
    }
    print(f"[config] creating Configuration: {name}, model_filename={COMPANY_TO_PKL[company]}")
    resp = call_with_diagnostics(
        "POST", f"{API_URL}/v2/lm/configurations", h, json=payload,
    )
    config = resp.json()
    print(f"[config] Configuration created: id={config['id']}")
    return config


def list_running_deployments(h: dict) -> list[dict]:
    """List RUNNING Deployments for the scenario."""
    resp = call_with_diagnostics(
        "GET", f"{API_URL}/v2/lm/deployments", h,
        params={"scenarioId": SCENARIO_ID, "status": "RUNNING", "$top": 50},
    )
    return resp.json().get("resources", [])


def get_configuration(h: dict, config_id: str) -> dict:
    """Read a Configuration to inspect its parameter bindings."""
    resp = call_with_diagnostics(
        "GET", f"{API_URL}/v2/lm/configurations/{config_id}", h,
    )
    return resp.json()


def deployment_company(h: dict, deployment: dict) -> str | None:
    """Look up the model_filename parameter on the deployment's current
    Configuration, return '1010' or '1710'."""
    config_id = deployment.get("configurationId")
    if not config_id:
        return None
    config = get_configuration(h, config_id)
    # Read either snake_case or camelCase, since older configs may have either
    bindings = (
        config.get("parameterBindings")
        or config.get("parameter_bindings")
        or []
    )
    for b in bindings:
        if b.get("key") == "model_filename":
            v = b.get("value", "")
            for company, pkl in COMPANY_TO_PKL.items():
                if v == pkl:
                    return company
    return None


def patch_deployment(h: dict, deployment_id: str, new_config_id: str) -> None:
    """In-place swap of Configuration on a RUNNING Deployment.
    KServe rolling update; URL stays stable."""
    payload = {"configurationId": new_config_id}
    print(f"[patch] {deployment_id} -> configurationId={new_config_id}")
    call_with_diagnostics(
        "PATCH", f"{API_URL}/v2/lm/deployments/{deployment_id}", h, json=payload,
    )
    print(f"[patch] {deployment_id} updated")


def deployments_already_on_model(h: dict, deployments: list[dict], model_id: str) -> bool:
    """Idempotency check: are all deployments already bound to a Configuration
    that uses this Model?"""
    for d in deployments:
        config_id = d.get("configurationId")
        if not config_id:
            return False
        config = get_configuration(h, config_id)
        bindings = (
            config.get("inputArtifactBindings")
            or config.get("input_artifact_bindings")
            or []
        )
        bound_artifact_ids = [
            b.get("artifactId") or b.get("artifact_id")
            for b in bindings
            if b.get("key") == "cashflowmodel"
        ]
        if model_id not in bound_artifact_ids:
            return False
    return True


# ---- MAIN -------------------------------------------------------------------

def main() -> int:
    print("=" * 60)
    print("UC2.5 - Model promotion to live deployments")
    print("=" * 60)

    token = get_token()
    h = headers(token)

    # 1. Find newest COMPLETED execution
    executions = list_executions_completed(h)
    if not executions:
        print("[error] no COMPLETED executions found", file=sys.stderr)
        return 1
    latest_exec = executions[0]
    exec_id = latest_exec["id"]
    print(f"[plan] newest COMPLETED execution: {exec_id} (started {latest_exec.get('startTime')})")

    # 2. Find or create the corresponding Model artifact
    models = list_models(h)
    model = find_model_for_execution(models, exec_id)
    if model:
        print(f"[plan] Model already registered for this execution: id={model['id']}")
    else:
        print(f"[plan] no Model registered for this execution, registering manually")
        model = register_model(h, exec_id)
    model_id = model["id"]

    # 3. Find target deployments
    deployments = list_running_deployments(h)
    if not deployments:
        print("[skip] no RUNNING deployments to promote, exiting 0")
        return 0
    print(f"[plan] {len(deployments)} RUNNING deployment(s) for scenario {SCENARIO_ID}")

    # 4. Idempotency: already on this model?
    if deployments_already_on_model(h, deployments, model_id):
        print(f"[skip] all deployments already bound to Model {model_id}, no promotion needed")
        return 0

    # 5. Build company-keyed map of {company: deployment} so we PATCH the right one
    company_to_deployment: dict[str, dict] = {}
    for d in deployments:
        c = deployment_company(h, d)
        if c is None:
            print(f"[warn] could not determine company for deployment {d['id']}, skipping")
            continue
        if c in company_to_deployment:
            print(f"[warn] multiple RUNNING deployments for company {c}, using first")
            continue
        company_to_deployment[c] = d
    print(f"[plan] mapped deployments: {[(c, d['id']) for c, d in company_to_deployment.items()]}")

    # 6. For each company we have a deployment for, create new Config + PATCH
    for company, deployment in company_to_deployment.items():
        config = create_configuration(h, company, model_id)
        patch_deployment(h, deployment["id"], config["id"])

    print(f"\n[done] promoted Model {model_id} to {len(company_to_deployment)} deployment(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
