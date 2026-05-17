"""Inspect explainer deployment to find GPT-4o config wiring."""
import os
import requests
from dotenv import load_dotenv
load_dotenv()
from gen_ai_hub.proxy.core.proxy_clients import get_proxy_client

proxy = get_proxy_client()
base_url = proxy.ai_core_client.base_url.rstrip("/")
headers = dict(proxy.request_header)
headers["AI-Resource-Group"] = "ml-training"

# Get the deployment details
print("=== Deployment d00c85f445274f70 ===")
r = requests.get(f"{base_url}/lm/deployments/d00c85f445274f70", headers=headers, timeout=30)
print(r.text[:2000])
print()

# Get the configuration it's using
import json
data = r.json()
config_id = data.get("configurationId")
print(f"=== Configuration {config_id} ===")
r = requests.get(f"{base_url}/lm/configurations/{config_id}", headers=headers, timeout=30)
print(r.text[:3000])
