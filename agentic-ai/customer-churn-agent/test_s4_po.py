"""
Test S/4HANA Purchase Order API
"""
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv
import os

load_dotenv()

# S/4HANA connection
base_url = 'http://mtsapserver3.themdlabs.com:8003'
user = os.getenv('S4_USER', 'sdasari')
password = os.getenv('S4_PASSWORD')

if not password:
    password = input("Enter S/4HANA password: ")

# Test Purchase Order API
url = f'{base_url}/sap/opu/odata/sap/API_PURCHASEORDER_PROCESS_SRV/A_PurchaseOrder?$top=5&$format=json'

print(f'User: {user}')
print(f'Testing: {url}')

try:
    response = requests.get(url, auth=HTTPBasicAuth(user, password), timeout=30)
    print(f'Status: {response.status_code}')

    if response.status_code == 200:
        data = response.json()
        pos = data.get('d', {}).get('results', [])
        print(f'\nFound {len(pos)} Purchase Orders:\n')
        for po in pos[:5]:
            po_num = po.get('PurchaseOrder', 'N/A')
            vendor = po.get('Supplier', 'N/A')
            comp_code = po.get('CompanyCode', 'N/A')
            print(f"  PO: {po_num} | Vendor: {vendor} | Company: {comp_code}")
    else:
        print(f'Error: {response.text[:500]}')
        
except Exception as e:
    print(f'Exception: {e}')