import httpx
import json
import time
import os
from dotenv import load_dotenv

load_dotenv()

# ============ DIE CREDENTIALS ============
die_api_url = "https://aiservices-dox.cfapps.us10.hana.ondemand.com"
die_token_url = "https://sap-btp-joule.authentication.us10.hana.ondemand.com/oauth/token"
die_client_id = "sb-0ebb7b58-8c2a-4432-a9bb-a5b499cbe7d0!b612484|dox-xsuaa-std-production!b9505"
die_client_secret = "bc86d2a4-ed70-49ad-8c8b-3c3fd988eff2$_FbsbJL2WCdiovb8Js1QNBC1ZkmopZ6MmAutMIazFBE="  # Fill this

# ============ BPA CREDENTIALS (from .env) ============
bpa_api_url = os.getenv('BPA_API_URL')
bpa_auth_url = os.getenv('BPA_AUTH_URL')
bpa_client_id = os.getenv('BPA_CLIENT_ID')
bpa_client_secret = os.getenv('BPA_CLIENT_SECRET')

def get_die_token():
    response = httpx.post(
        die_token_url,
        data={
            'grant_type': 'client_credentials',
            'client_id': die_client_id,
            'client_secret': die_client_secret
        },
        headers={'Content-Type': 'application/x-www-form-urlencoded'},
        timeout=30.0
    )
    return response.json().get('access_token')

def get_bpa_token():
    response = httpx.post(
        f"{bpa_auth_url}/oauth/token",
        data={
            'grant_type': 'client_credentials',
            'client_id': bpa_client_id,
            'client_secret': bpa_client_secret
        },
        headers={'Content-Type': 'application/x-www-form-urlencoded'},
        timeout=30.0
    )
    return response.json().get('access_token')

def extract_po_from_pdf(pdf_path):
    """Upload PDF to DIE and extract PO fields"""
    print(f"\n[1] Uploading PDF to DIE: {pdf_path}")
    
    token = get_die_token()
    
    options = {
        "extraction": {
            "headerFields": [
                "documentNumber", "documentDate", "deliveryDate",
                "senderName", "grossAmount", "currencyCode"
            ],
            "lineItemFields": [
                "description", "quantity", "unitPrice", "customerMaterialNumber"
            ]
        },
        "clientId": "default",
        "documentType": "purchaseOrder"
    }
    
    with open(pdf_path, 'rb') as f:
        files = {
            'file': (os.path.basename(pdf_path), f, 'application/pdf'),
            'options': (None, json.dumps(options), 'application/json')
        }
        
        response = httpx.post(
            f"{die_api_url}/document-information-extraction/v1/document/jobs",
            headers={'Authorization': f'Bearer {token}'},
            files=files,
            timeout=60.0
        )
    
    job_id = response.json().get('id')
    print(f"    Job ID: {job_id}")
    
    # Poll for result
    print("[2] Waiting for extraction...")
    for i in range(20):
        time.sleep(3)
        result = httpx.get(
            f"{die_api_url}/document-information-extraction/v1/document/jobs/{job_id}",
            headers={'Authorization': f'Bearer {token}'},
            timeout=30.0
        ).json()
        
        status = result.get('status')
        print(f"    Attempt {i+1}: {status}")
        
        if status == "DONE":
            return result
        elif status == "FAILED":
            raise Exception(f"DIE extraction failed: {result}")
    
    raise Exception("DIE extraction timeout")

def parse_die_result(die_result):
    """Extract relevant fields from DIE response"""
    extraction = die_result.get('extraction', {})
    header = {f['name']: f['value'] for f in extraction.get('headerFields', [])}
    
    # Get first line item
    line_items = extraction.get('lineItems', [])
    first_item = {}
    if line_items:
        first_item = {f['name']: f['value'] for f in line_items[0]}
    
    return {
        'purchaseordernumber': header.get('documentNumber', ''),
        'customername': header.get('senderName', ''),
        'deliverydate': header.get('deliveryDate', ''),
        'materialnumber': first_item.get('customerMaterialNumber', 'TG11'),  # Default TG11
        'quantity': int(first_item.get('quantity', 1)),
        'pocontent': f"PO {header.get('documentNumber')} from {header.get('senderName')}"
    }

def trigger_sbpa_workflow(po_data):
    """Trigger SBPA workflow with extracted PO data"""
    print("\n[3] Triggering SBPA workflow...")
    
    token = get_bpa_token()
    
    payload = {
        "definitionId": "us10.sap-btp-joule.socreationfrompo.pOtoSOProcess",
        "context": po_data
    }
    
    print(f"    Payload: {json.dumps(po_data, indent=2)}")
    
    response = httpx.post(
        f"{bpa_api_url}/workflow/rest/v1/workflow-instances",
        json=payload,
        headers={
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        },
        timeout=30.0
    )
    
    result = response.json()
    print(f"    Status: {response.status_code}")
    print(f"    Instance ID: {result.get('id')}")
    print(f"    Workflow Status: {result.get('status')}")
    
    return result

def main():
    # PDF path
    pdf_path = r"C:\Users\nivas\repos\sap-ai-journey\05-sap-build\sbpa-workflows\po-to-so-demo\Customer_PO_GlobalTech_PO2026001.pdf"
    
    print("="*60)
    print("PO-to-SO AUTOMATION: PDF → DIE → SBPA → S/4HANA")
    print("="*60)
    
    # Step 1 & 2: Extract from PDF
    die_result = extract_po_from_pdf(pdf_path)
    
    # Parse extracted fields
    po_data = parse_die_result(die_result)
    print(f"\n[2b] Extracted Fields:")
    for k, v in po_data.items():
        print(f"     {k}: {v}")
    
    # Step 3: Trigger SBPA
    workflow_result = trigger_sbpa_workflow(po_data)
    
    print("\n" + "="*60)
    print("SUCCESS! Check SBPA Monitoring for workflow status.")
    print("="*60)

if __name__ == "__main__":
    main()