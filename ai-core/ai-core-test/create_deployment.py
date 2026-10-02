import os
import time
from dotenv import load_dotenv
from ai_core_sdk.ai_core_v2_client import AICoreV2Client

load_dotenv()

# Initialize raw AI Core client using environment variables
client = AICoreV2Client(
    base_url=os.getenv("AICORE_BASE_URL"),
    auth_url=os.getenv("AICORE_AUTH_URL"),
    client_id=os.getenv("AICORE_CLIENT_ID"),
    client_secret=os.getenv("AICORE_CLIENT_SECRET"),
    resource_group=os.getenv("AICORE_RESOURCE_GROUP", "default")
)

# 1. Create a configuration for gpt-4o-mini
print("Creating configuration for gpt-4o-mini...")
config = client.configuration.create(
    name="gpt-4o-mini-config",
    scenario_id="foundation-models",
    executable_id="azure-openai",
    parameter_bindings=[
        {"key": "modelName", "value": "gpt-4o-mini"},
        {"key": "modelVersion", "value": "latest"}
    ]
)
print(f"Configuration created: {config.id}")

# 2. Trigger deployment
print("Triggering deployment...")
deployment = client.deployment.create(configuration_id=config.id)
print(f"Deployment created with ID: {deployment.id}")

# 3. Poll until running
print("Waiting for deployment to enter RUNNING state (takes ~1-3 minutes)...")
while True:
    dep_status = client.deployment.get(deployment.id)
    print(f"Current status: {dep_status.status}")
    if dep_status.status == "RUNNING":
        print("\n Deployment is RUNNING and ready for traffic!")
        break
    elif dep_status.status in ["DEAD", "STOPPED", "FAILED"]:
        print(f"\n❌ Deployment ended with status: {dep_status.status}")
        break
    time.sleep(15)