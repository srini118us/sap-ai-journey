"""List all GPT-4o deployments across resource groups."""
import os
import requests
from dotenv import load_dotenv

load_dotenv()
from gen_ai_hub.proxy.core.proxy_clients import get_proxy_client

proxy = get_proxy_client()
base_url = proxy.ai_core_client.base_url.rstrip("/")
headers = dict(proxy.request_header)

for rg in ["ml-training", "ai-launchpad", "default"]:
    print(f"=== Resource Group: {rg} ===")
    headers["AI-Resource-Group"] = rg
    r = requests.get(f"{base_url}/lm/deployments", headers=headers, timeout=30)
    if r.status_code != 200:
        print(f"  STATUS {r.status_code}: {r.text[:200]}")
        continue
    deployments = r.json().get("resources", [])
    for d in deployments:
        scenario = d.get("scenarioId", "?")
        config = d.get("configurationName", "?")
        status = d.get("status", "?")
        dep_id = d.get("id", "?")
        print(f"  {dep_id}  status={status}  scenario={scenario}  config={config}")
    print()
