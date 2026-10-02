import httpx
import os
from dotenv import load_dotenv

load_dotenv()

# Get token
auth_url = os.getenv('BPA_AUTH_URL')
token_response = httpx.post(
    f"{auth_url}/oauth/token",
    data={
        'grant_type': 'client_credentials',
        'client_id': os.getenv('BPA_CLIENT_ID'),
        'client_secret': os.getenv('BPA_CLIENT_SECRET')
    },
    headers={'Content-Type': 'application/x-www-form-urlencoded'},
    timeout=30.0
)
token = token_response.json().get('access_token')
print(f"Token: {token[:50]}...")

# List available workflow definitions
api_url = os.getenv('BPA_API_URL')
url = f"{api_url}/workflow/rest/v1/workflow-definitions"

response = httpx.get(
    url,
    headers={'Authorization': f'Bearer {token}'},
    timeout=30.0
)

print(f"\nStatus: {response.status_code}")
print(f"Response: {response.text[:1000]}")
