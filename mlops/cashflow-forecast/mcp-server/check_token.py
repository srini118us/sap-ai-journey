from dotenv import load_dotenv
load_dotenv()

from gen_ai_hub.proxy.core.proxy_clients import get_proxy_client

import base64
import json

proxy = get_proxy_client()
token = proxy.ai_core_client.rest_client.get_token().replace("Bearer ", "")
parts = token.split(".")

payload = json.loads(base64.urlsafe_b64decode(parts[1] + "=="))

print("=== Token claims ===")
for key in sorted(payload.keys()):
    val = payload[key]
    if key == "scope" and isinstance(val, list):
        print(f"  {key}:")
        for scope in val:
            if "prompt" in scope.lower():
                print(f"    ★ {scope}")
            else:
                print(f"    {scope}")
    elif isinstance(val, list) and len(val) > 5:
        print(f"  {key}: [{len(val)} items] {val[:3]} ...")
    else:
        print(f"  {key}: {val}")
