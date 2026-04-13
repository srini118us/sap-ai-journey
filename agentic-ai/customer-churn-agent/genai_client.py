"""
SAP GenAI Hub API Client (Orchestration)
=========================================
Updated for SAP AI Core Orchestration API

Author: Srinivasa Dasari
Date: March 2026
"""

import os
import requests
from typing import Optional, Dict, List
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class GenAIConfig:
    ai_api_url: str
    auth_url: str
    client_id: str
    client_secret: str
    resource_group: str = "default"
    orchestration_deployment_id: str = "deb03e6b331ed77b"
    
    @classmethod
    def from_env(cls) -> 'GenAIConfig':
        return cls(
            ai_api_url=os.getenv('AI_API_URL', ''),
            auth_url=os.getenv('AUTH_URL', ''),
            client_id=os.getenv('CLIENT_ID', ''),
            client_secret=os.getenv('CLIENT_SECRET', ''),
            resource_group=os.getenv('RESOURCE_GROUP', 'default'),
            orchestration_deployment_id=os.getenv('ORCH_DEPLOYMENT_ID', 'deb03e6b331ed77b')
        )
    
    def validate(self) -> bool:
        required = [self.ai_api_url, self.auth_url, self.client_id, self.client_secret]
        return all(required)


class GenAIHubClient:
    def __init__(self, config: GenAIConfig):
        self.config = config
        self._token: Optional[str] = None
        self._token_expires: Optional[datetime] = None
        self.default_model = "gpt-4.1-mini"
        
    def _get_token(self) -> str:
        if self._token and self._token_expires:
            if datetime.now() < self._token_expires - timedelta(minutes=5):
                return self._token
        
        token_url = f"{self.config.auth_url}/oauth/token"
        response = requests.post(
            token_url,
            data={
                "grant_type": "client_credentials",
                "client_id": self.config.client_id,
                "client_secret": self.config.client_secret
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        if response.status_code != 200:
            raise Exception(f"Failed to get token: {response.status_code} - {response.text}")
        
        token_data = response.json()
        self._token = token_data["access_token"]
        expires_in = token_data.get("expires_in", 43200)
        self._token_expires = datetime.now() + timedelta(seconds=expires_in)
        print(f"✓ Token obtained (expires in {expires_in // 3600} hours)")
        return self._token
    
    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self._get_token()}",
            "AI-Resource-Group": self.config.resource_group,
            "Content-Type": "application/json"
        }
    
    def list_deployments(self) -> List[Dict]:
        url = f"{self.config.ai_api_url}/v2/lm/deployments"
        response = requests.get(url, headers=self._get_headers())
        if response.status_code != 200:
            raise Exception(f"Failed to list deployments: {response.status_code}")
        return response.json().get("resources", [])
    
    def chat(
        self,
        message: str,
        model: Optional[str] = None,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> str:
        model = model or self.default_model
        
        # Build template
        template = []
        if system_prompt:
            template.append({"role": "system", "content": system_prompt})
        template.append({"role": "user", "content": "{{?user_message}}"})
        
        url = f"{self.config.ai_api_url}/v2/inference/deployments/{self.config.orchestration_deployment_id}/completion"
        
        payload = {
            "orchestration_config": {
                "module_configurations": {
                    "templating_module_config": {
                        "template": template
                    },
                    "llm_module_config": {
                        "model_name": model,
                        "model_params": {
                            "max_tokens": max_tokens,
                            "temperature": temperature
                        }
                    }
                }
            },
            "input_params": {
                "user_message": message
            }
        }
        
        response = requests.post(url, headers=self._get_headers(), json=payload)
        
        if response.status_code != 200:
            raise Exception(f"Chat failed: {response.status_code} - {response.text}")
        
        result = response.json()
        return result["module_results"]["llm"]["choices"][0]["message"]["content"]


def quick_test():
    print("=" * 60)
    print("SAP GenAI Hub - Connection Test (Orchestration)")
    print("=" * 60)
    
    config = GenAIConfig.from_env()
    
    if not config.validate():
        print("Missing configuration. Set: AI_API_URL, AUTH_URL, CLIENT_ID, CLIENT_SECRET")
        return False
    
    print(f"✓ Config loaded")
    print(f"  API URL: {config.ai_api_url}")
    print(f"  Orchestration ID: {config.orchestration_deployment_id}")
    
    client = GenAIHubClient(config)
    
    print("\n--- Test Chat ---")
    try:
        response = client.chat("Say 'Hello from SAP GenAI Hub!' and nothing else.", temperature=0)
        print(f"  Response: {response}")
        print("\n✅ GenAI Hub connection successful!")
        return True
    except Exception as e:
        print(f"  ❌ Chat failed: {e}")
        return False


if __name__ == "__main__":
    try:
        from dotenv import load_dotenv
        load_dotenv('.env')
    except ImportError:
        pass
    quick_test()