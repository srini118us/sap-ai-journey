import os
import requests
from dotenv import load_dotenv

load_dotenv()

from gen_ai_hub.proxy.core.proxy_clients import get_proxy_client

proxy = get_proxy_client()
deployment_id = os.getenv("ORCHESTRATION_DEPLOYMENT_ID")
rg = os.getenv("ORCHESTRATION_RESOURCE_GROUP", "ml-training")

base_url = proxy.ai_core_client.base_url.rstrip("/")
url = f"{base_url}/inference/deployments/{deployment_id}/completion"

headers = dict(proxy.request_header)
headers["AI-Resource-Group"] = rg
headers["Content-Type"] = "application/json"

# Minimal valid orchestration request — inline messages, no template
body = {
    "orchestration_config": {
        "module_configurations": {
            "llm_module_config": {
                "model_name": "gpt-4o",
                "model_version": "latest",
                "model_params": {"max_tokens": 50, "temperature": 0.1}
            },
            "templating_module_config": {
                "template": [
                    {"role": "user", "content": "Say hello in five words."}
                ]
            }
        }
    },
    "input_params": {}
}

print("URL:", url)
print("RG:", rg)
print()

r = requests.post(url, headers=headers, json=body, timeout=60)
print("STATUS:", r.status_code)
print("BODY:", r.text[:3000])
