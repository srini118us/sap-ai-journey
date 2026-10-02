import sys
import requests
sys.path.insert(0, 'part1_genai_api')
from dotenv import load_dotenv
load_dotenv('.env')
from genai_client import GenAIHubClient, GenAIConfig

config = GenAIConfig.from_env()
client = GenAIHubClient(config)
token = client._get_token()

url = f"{config.ai_api_url}/v2/inference/deployments/deb03e6b331ed77b/completion"

payload = {
    "orchestration_config": {
        "module_configurations": {
            "templating_module_config": {
                "template": [
                    {"role": "user", "content": "{{?user_message}}"}
                ]
            },
            "llm_module_config": {
                "model_name": "gpt-4.1-mini",
                "model_params": {
                    "max_tokens": 100,
                    "temperature": 0.7
                }
            }
        }
    },
    "input_params": {
        "user_message": "Say hello from SAP GenAI Hub!"
    }
}

headers = {
    "Authorization": f"Bearer {token}",
    "AI-Resource-Group": "default",
    "Content-Type": "application/json"
}

response = requests.post(url, headers=headers, json=payload)
print(f"Status: {response.status_code}")
print(f"Response: {response.text[:800]}")
