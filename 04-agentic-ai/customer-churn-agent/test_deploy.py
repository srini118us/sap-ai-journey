import sys
sys.path.insert(0, 'part1_genai_api')
from dotenv import load_dotenv
load_dotenv('.env')
from genai_client import GenAIHubClient, GenAIConfig
config = GenAIConfig.from_env()
client = GenAIHubClient(config)
deployments = client.list_deployments()
for d in deployments:
    print(f"{d['id']}: {d['status']} - {d.get('configurationName', 'N/A')}")
