# test_release2.py
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

base_url = os.getenv('S4HANA_BASE_URL')
user = os.getenv('S4HANA_USER')
password = os.getenv('S4HANA_PASSWORD')

url = f"{base_url}/sap/opu/odata/sap/API_PURCHASEORDER_PROCESS_SRV/$metadata"

response = httpx.get(
    url,
    auth=(user, password),
    headers={'Accept': 'application/xml'},
    timeout=30.0
)

# Find Release-related elements
lines = response.text.split('\n')
print("Release-related operations:\n")
for line in lines:
    if 'Release' in line:
        print(line.strip())