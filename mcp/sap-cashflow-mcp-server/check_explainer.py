"""Quick smoke test of UC2.6 explainer deployment."""
import os
import requests
from dotenv import load_dotenv

load_dotenv()
from gen_ai_hub.proxy.core.proxy_clients import get_proxy_client

proxy = get_proxy_client()
deployment_id = os.getenv("EXPLAIN_DEPLOYMENT_ID")
rg = os.getenv("EXPLAIN_RESOURCE_GROUP", "ml-training")

base_url = proxy.ai_core_client.base_url.rstrip("/")
url = f"{base_url}/inference/deployments/{deployment_id}/v2/explain"

headers = dict(proxy.request_header)
headers["AI-Resource-Group"] = rg
headers["Content-Type"] = "application/json"

print(f"URL: {url}")
print(f"RG:  {rg}")
print()

for company_code in ["1010", "1710"]:
    print(f"=== /v2/explain (company={company_code}) ===")
    r = requests.post(url, headers=headers, json={"company_code": company_code}, timeout=60)
    print(f"STATUS: {r.status_code}")
    print(f"BODY: {r.text[:1500]}")
    print()
