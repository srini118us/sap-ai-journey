"""
Smoke test for UC2.4 cashflow forecast deployments on SAP AI Core.

Reads a service key JSON file (downloaded from BTP Cockpit), exchanges
client_id/secret for an OAuth bearer token, then exercises all three
endpoints on each of the two deployments.

Mirrors the local test_local.sh from UC2.4 session 1, but against the
real AI Core endpoints with proper auth.

Usage:
    python test_deployed.py

Pre-reqs:
    - venv-uc23 active (pip install requests if not already there)
    - SERVICE_KEY_PATH below points at your downloaded service key JSON

Environment:
    Service key holds clientid, clientsecret, url (auth server),
    serviceurls.AI_API_URL (AI Core base URL).
"""
import json
import sys
from pathlib import Path

import requests


# ---- CONFIG -----------------------------------------------------------------

# Path to the service key JSON downloaded from BTP Cockpit.
# Adjust if you saved it elsewhere.
SERVICE_KEY_PATH = Path.home() / "sap-aicore-key.json"

RESOURCE_GROUP = "ml-training"

DEPLOYMENTS = {
    "1010": "d50ff74ca07c9968",
    "1710": "d8ecefa36dd1b465",
}


# ---- HELPERS ----------------------------------------------------------------

def load_service_key() -> dict:
    if not SERVICE_KEY_PATH.exists():
        print(f"[error] service key not found at {SERVICE_KEY_PATH}")
        print("        download from BTP Cockpit and save to that path,")
        print("        or edit SERVICE_KEY_PATH at the top of this script.")
        sys.exit(1)
    return json.loads(SERVICE_KEY_PATH.read_text())


def get_bearer_token(key: dict) -> str:
    """Exchange clientid/clientsecret for an OAuth bearer token."""
    auth_url = f"{key['url']}/oauth/token"
    print(f"[auth] requesting token from {auth_url}")
    resp = requests.post(
        auth_url,
        params={"grant_type": "client_credentials"},
        auth=(key["clientid"], key["clientsecret"]),
        timeout=30,
    )
    resp.raise_for_status()
    token = resp.json()["access_token"]
    print(f"[auth] token acquired (length={len(token)})")
    return token


def call(method: str, url: str, headers: dict, body: dict | None = None):
    """Call a deployment endpoint, return (status_code, parsed_body)."""
    if method == "GET":
        r = requests.get(url, headers=headers, timeout=60)
    else:
        r = requests.post(url, headers=headers, json=body or {}, timeout=60)
    try:
        return r.status_code, r.json()
    except ValueError:
        return r.status_code, r.text


def pretty(obj, max_lines: int = 20) -> str:
    """Truncate large JSON for readable output."""
    s = json.dumps(obj, indent=2, default=str) if not isinstance(obj, str) else obj
    lines = s.splitlines()
    if len(lines) <= max_lines:
        return s
    return "\n".join(lines[:max_lines]) + f"\n... ({len(lines) - max_lines} more lines)"


# ---- SMOKE TEST -------------------------------------------------------------

def smoke_test_deployment(company: str, deployment_id: str, base_url: str, headers: dict):
    print("\n" + "=" * 70)
    print(f"DEPLOYMENT: company={company}, id={deployment_id}")
    print("=" * 70)

    deploy_url = f"{base_url}/v2/inference/deployments/{deployment_id}"

    # /v2/healthz
    print("\n--- GET /v2/healthz ---")
    code, body = call("GET", f"{deploy_url}/v2/healthz", headers)
    print(f"HTTP {code}")
    print(pretty(body))
    if code != 200:
        print(f"[fail] healthz did not return 200, aborting further tests for {company}")
        return False

    # /v2/info
    print("\n--- GET /v2/info ---")
    code, body = call("GET", f"{deploy_url}/v2/info", headers)
    print(f"HTTP {code}")
    print(pretty(body))

    # Verify the deployed model matches what we expect for this company
    served_company = body.get("company_code") if isinstance(body, dict) else None
    if served_company != company:
        print(f"[warn] /info reports company_code={served_company}, expected {company}")
        print(f"       Configuration parameter may have been bound to wrong .pkl file.")

    # /v2/predict (default horizon — 14)
    print("\n--- POST /v2/predict (default horizon) ---")
    code, body = call("POST", f"{deploy_url}/v2/predict", headers, {})
    print(f"HTTP {code}")
    print(pretty(body, max_lines=30))

    # /v2/predict (forecast_length=30)
    print("\n--- POST /v2/predict (forecast_length=30) ---")
    code, body = call("POST", f"{deploy_url}/v2/predict", headers, {"forecast_length": 30})
    print(f"HTTP {code}")
    if isinstance(body, dict) and "horizon" in body:
        print(f"horizon returned: {body['horizon']}")
        print(f"forecast points: {len(body.get('forecast', []))}")
        if body.get("forecast"):
            print(f"first point: {body['forecast'][0]}")
            print(f"last point:  {body['forecast'][-1]}")

    # /v2/predict (out-of-range, expect 422)
    print("\n--- POST /v2/predict (forecast_length=999, expect 422) ---")
    code, _ = call("POST", f"{deploy_url}/v2/predict", headers, {"forecast_length": 999})
    print(f"HTTP {code} {'PASS' if code == 422 else 'FAIL (expected 422)'}")

    return True


def main():
    key = load_service_key()
    token = get_bearer_token(key)

    base_url = key["serviceurls"]["AI_API_URL"]
    headers = {
        "Authorization": f"Bearer {token}",
        "AI-Resource-Group": RESOURCE_GROUP,
        "Content-Type": "application/json",
    }

    results = {}
    for company, deployment_id in DEPLOYMENTS.items():
        ok = smoke_test_deployment(company, deployment_id, base_url, headers)
        results[company] = ok

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    for company, ok in results.items():
        print(f"  {company}: {'PASS' if ok else 'FAIL'}")


if __name__ == "__main__":
    main()
