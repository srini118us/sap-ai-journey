import httpx
import os
from dotenv import load_dotenv

load_dotenv()

base_url = os.getenv('S4HANA_BASE_URL')
url = f"{base_url}/sap/opu/odata/sap/API_PURCHASEORDER_PROCESS_SRV/A_PurchaseOrder('4500000004')?$format=json&$expand=to_PurchaseOrderItem"

response = httpx.get(
    url,
    auth=(os.getenv('S4HANA_USER'), os.getenv('S4HANA_PASSWORD')),
    timeout=30.0
)

print('Status:', response.status_code)
import json
data = response.json().get('d', {})

# Check items for amount fields
items = data.get('to_PurchaseOrderItem', {}).get('results', [])
print(f"\nFound {len(items)} items\n")

if items:
    print("First item fields:")
    for key, value in items[0].items():
        if 'amount' in key.lower() or 'price' in key.lower() or 'net' in key.lower() or 'value' in key.lower():
            print(f"  {key}: {value}")