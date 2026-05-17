"""
Repoint the explainer deployment to a fresh GPT-4o.

Old GPT-4o: df9fcfa534c2131f (STOPPED)
New GPT-4o: d92b6e30fea5bf84 (RUNNING)

SAP-native pattern: create new Configuration, PATCH deployment.
Deployment ID stays the same — no .env update needed.
"""
import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()
from gen_ai_hub.proxy.core.proxy_clients import get_proxy_client

OLD_GPT4O = "df9fcfa534c2131f"
NEW_GPT4O = "d92b6e30fea5bf84"
DEPLOYMENT_ID = "d00c85f445274f70"
RG = "ml-training"

proxy = get_proxy_client()
base_url = proxy.ai_core_client.base_url.rstrip("/")
headers = dict(proxy.request_header)
headers["AI-Resource-Group"] = RG
headers["Content-Type"] = "application/json"

# ---- Step 1: Get current config ----
print("=== Step 1: Read current config ===")
r = requests.get(f"{base_url}/lm/deployments/{DEPLOYMENT_ID}", headers=headers, timeout=30)
r.raise_for_status()
current_config_id = r.json()["configurationId"]
print(f"Current config: {current_config_id}")

r = requests.get(f"{base_url}/lm/configurations/{current_config_id}", headers=headers, timeout=30)
r.raise_for_status()
cfg = r.json()
print(f"Current bindings:")
for b in cfg["parameterBindings"]:
    print(f"  {b['key']} = {b['value']}")
print()

# ---- Step 2: Build new config payload ----
print("=== Step 2: Build new config (in memory) ===")
new_bindings = []
for b in cfg["parameterBindings"]:
    if b["key"] == "gpt4o_deployment_id":
        new_bindings.append({"key": "gpt4o_deployment_id", "value": NEW_GPT4O})
        print(f"  REPLACE: gpt4o_deployment_id = {OLD_GPT4O} -> {NEW_GPT4O}")
    else:
        new_bindings.append(b)
        print(f"  KEEP:    {b['key']} = {b['value']}")
print()

new_config_payload = {
    "name": f"cashflow-explain-config-v02-{int(time.time())}",
    "executableId": cfg["executableId"],
    "scenarioId": cfg["scenarioId"],
    "parameterBindings": new_bindings,
    "inputArtifactBindings": cfg.get("inputArtifactBindings", []),
}
print(f"New config name: {new_config_payload['name']}")
print()

# ---- Confirm before creating ----
ans = input("Create new Configuration? [y/N] ").strip().lower()
if ans != "y":
    print("Aborted.")
    exit(0)

# ---- Step 3: Create new config ----
print()
print("=== Step 3: Create new Configuration ===")
r = requests.post(f"{base_url}/lm/configurations", headers=headers, json=new_config_payload, timeout=30)
print(f"STATUS: {r.status_code}")
print(f"BODY:   {r.text[:500]}")
r.raise_for_status()
new_config_id = r.json()["id"]
print(f"New config ID: {new_config_id}")
print()

# ---- Confirm before patching ----
ans = input(f"PATCH deployment {DEPLOYMENT_ID} -> config {new_config_id}? [y/N] ").strip().lower()
if ans != "y":
    print(f"Aborted. New config {new_config_id} exists but is unused.")
    exit(0)

# ---- Step 4: PATCH deployment ----
print()
print("=== Step 4: PATCH deployment to new config ===")
patch_body = {"configurationId": new_config_id}
r = requests.patch(f"{base_url}/lm/deployments/{DEPLOYMENT_ID}", headers=headers, json=patch_body, timeout=30)
print(f"STATUS: {r.status_code}")
print(f"BODY:   {r.text[:500]}")
r.raise_for_status()
print()

# ---- Step 5: Poll for RUNNING ----
print("=== Step 5: Poll deployment status ===")
for i in range(20):
    r = requests.get(f"{base_url}/lm/deployments/{DEPLOYMENT_ID}", headers=headers, timeout=30)
    d = r.json()
    print(f"  [{i*15}s] status={d['status']}  target={d['targetStatus']}  lastOp={d['lastOperation']}  config={d['configurationId']}")
    if d["status"] == "RUNNING" and d["configurationId"] == new_config_id:
        print()
        print("Deployment now using new config. Ready to smoke test.")
        break
    time.sleep(15)
else:
    print("Did not reach RUNNING within 5 minutes. Check AI Launchpad manually.")
