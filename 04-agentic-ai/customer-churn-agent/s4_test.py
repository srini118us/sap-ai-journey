"""
S/4HANA Connection Test
"""
import requests
from requests.auth import HTTPBasicAuth
import getpass

# Connection details
S4_HOST = "http://mtsapserver3.themdlabs.com:8003"
USERNAME = "sdasari"

# Get password securely
PASSWORD = getpass.getpass("Enter S/4HANA password: ")

# Test 1: Fetch customers
print("\n[TEST] Fetching customers...")
url = f"{S4_HOST}/sap/opu/odata/sap/API_BUSINESS_PARTNER/A_Customer?$top=5&$format=json"

response = requests.get(
    url,
    auth=HTTPBasicAuth(USERNAME, PASSWORD)
)

print(f"[INFO] Status: {response.status_code}")

if response.ok:
    data = response.json()
    customers = data.get("d", {}).get("results", [])
    print(f"[OK] Found {len(customers)} customers\n")
    
    for c in customers:
        print(f"  Customer ID: {c.get('Customer', 'N/A')}")
        print(f"  Name: {c.get('CustomerName', 'N/A')}")
        print(f"  Industry: {c.get('IndustrySector', 'N/A')}")
        print(f"  Created: {c.get('CreationDate', 'N/A')}")
        print("  ---")
else:
    print(f"[ERROR] {response.status_code}: {response.text[:500]}")