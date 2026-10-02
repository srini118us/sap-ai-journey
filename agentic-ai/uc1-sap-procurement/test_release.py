# test_release.py - Run in C:\sap-ai-journey\lab11-uc1\
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

base_url = os.getenv('S4HANA_BASE_URL')
user = os.getenv('S4HANA_USER')
password = os.getenv('S4HANA_PASSWORD')

# Check metadata for Release operations
print("Checking API for Release operations...")
url = f"{base_url}/sap/opu/odata/sap/API_PURCHASEORDER_PROCESS_SRV/$metadata"

response = httpx.get(
    url,
    auth=(user, password),
    headers={'Accept': 'application/xml'},
    timeout=30.0
)

print(f"Status: {response.status_code}")

if 'Release' in response.text:
    print("\nRelease operations found!")
else:
    print("\nNo Release in this API - checking alternative...")
    
    # Try MM BAPI service
    url2 = f"{base_url}/sap/opu/odata/sap/API_PURCHASEORDER_2/$metadata"
    response2 = httpx.get(url2, auth=(user, password), timeout=30.0)
    print(f"\nAPI_PURCHASEORDER_2: {response2.status_code}")
    if response2.status_code == 200 and 'Release' in response2.text:
        print("  Release found in API_PURCHASEORDER_2!")