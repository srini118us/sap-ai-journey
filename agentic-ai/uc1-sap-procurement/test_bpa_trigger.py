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
print(f"Token obtained")

# Trigger workflow
api_url = os.getenv('BPA_API_URL')
definition_id = os.getenv('BPA_DEFINITION_ID')

payload = {
    "definitionId": definition_id,
    "context": {
        "purchaseorder": "4500000005",
        "netamount": 180323.42,
        "currency": "USD",
        "vendor": "USSU-VSF06",
        "vendorname": "VF Vendor 06",
        "companycode": "1710",
        "releasecode": "vp",
        "requestoremail": "support3@manbitech.com"
    }
}
print(f"\nPayload: {payload}")

url = f"{api_url}/workflow/rest/v1/workflow-instances"

response = httpx.post(
    url,
    json=payload,
    headers={
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    },
    timeout=30.0
)

print(f"\nStatus: {response.status_code}")
print(f"Response: {response.text}")