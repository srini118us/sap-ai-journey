import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

from gen_ai_hub.proxy.core.proxy_clients import get_proxy_client


def query(label, url, rg="ml-training"):
    proxy = get_proxy_client()
    headers = dict(proxy.request_header)
    headers["AI-Resource-Group"] = rg
    print(f"\n=== {label} ===")
    print("URL:", url)
    r = requests.get(url, headers=headers, timeout=30)
    print("STATUS:", r.status_code)
    if r.status_code >= 400:
        print("BODY:", r.text[:400])
        return
    payload = r.json()
    if isinstance(payload, dict) and "count" in payload:
        print(f"count={payload.get('count')}, returned={len(payload.get('resources', []))}")
        for t in payload.get("resources", [])[:5]:
            print(f"  - id={t.get('id', '?')[:8]}.. name={t.get('name')} version={t.get('version')} scenario={t.get('scenario') or t.get('scenarioId')}")
    else:
        print("BODY:", json.dumps(payload, indent=2)[:1500])


def main():
    proxy = get_proxy_client()
    base_url = proxy.ai_core_client.base_url.rstrip("/")

    # Variant 1 — direct list
    query("Variant 1: bare endpoint",
          f"{base_url}/lm/promptTemplates")

    # Variant 2 — scenarioId param (camelCase)
    query("Variant 2: ?scenarioId=cashflow-forecast",
          f"{base_url}/lm/promptTemplates?scenarioId=cashflow-forecast")

    # Variant 3 — scenario_id param (snake_case)
    query("Variant 3: ?scenario_id=cashflow-forecast",
          f"{base_url}/lm/promptTemplates?scenario_id=cashflow-forecast")

    # Variant 4 — nested scenarios path
    query("Variant 4: /scenarios/cashflow-forecast/promptTemplates",
          f"{base_url}/lm/scenarios/cashflow-forecast/promptTemplates")

    # Variant 5 — nested scenarios with name and version
    query("Variant 5: /scenarios/cashflow-forecast/promptTemplates/cashflow-explainer-system/0.0.2",
          f"{base_url}/lm/scenarios/cashflow-forecast/promptTemplates/cashflow-explainer-system/0.0.2")


if __name__ == "__main__":
    main()
