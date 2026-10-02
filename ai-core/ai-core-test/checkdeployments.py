from dotenv import load_dotenv
from gen_ai_hub.proxy.core.proxy_clients import get_proxy_client

load_dotenv()

client = get_proxy_client("gen-ai-hub")
deployments = client.deployments

if not deployments:
    print("No active model deployments found in this resource group.")
else:
    print(f"Found {len(deployments)} active deployment(s):")
    for d in deployments:
        print(f" - Model: {d.model_name} | Status: {d.status} | ID: {d.id}")