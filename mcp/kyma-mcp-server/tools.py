"""
SAP S/4HANA MCP Tools
Connects to real S/4HANA Purchase Order API via OData
"""

import os
import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime
from typing import Optional

# S/4HANA Connection Configuration
S4_BASE_URL = os.getenv('S4_BASE_URL', 'http://mtsapserver3.themdlabs.com:8003')
S4_USER = os.getenv('S4_USER', 'sdasari')
S4_PASSWORD = os.getenv('S4_PASSWORD', '')

# OData API endpoint
PO_API = '/sap/opu/odata/sap/API_PURCHASEORDER_PROCESS_SRV'


def _get_auth():
    """Get HTTP Basic Auth for S/4HANA"""
    return HTTPBasicAuth(S4_USER, S4_PASSWORD)


def _make_request(endpoint: str, params: dict = None) -> dict:
    """Make OData request to S/4HANA"""
    url = f"{S4_BASE_URL}{PO_API}{endpoint}"
    
    default_params = {'$format': 'json'}
    if params:
        default_params.update(params)
    
    try:
        response = requests.get(
            url,
            auth=_get_auth(),
            params=default_params,
            timeout=30
        )
        
        if response.status_code == 200:
            return {'success': True, 'data': response.json()}
        else:
            return {
                'success': False,
                'error': f"HTTP {response.status_code}: {response.text[:200]}"
            }
    except Exception as e:
        return {'success': False, 'error': str(e)}


def get_purchase_orders(
    status: Optional[str] = None,
    vendor: Optional[str] = None,
    plant: Optional[str] = None,
    limit: int = 10
) -> dict:
    """
    Retrieve Purchase Orders from SAP S/4HANA
    
    Args:
        status: Filter by PO status (not directly available in API, kept for compatibility)
        vendor: Filter by vendor/supplier ID (e.g., "USSU-VSF04")
        plant: Filter by plant code
        limit: Maximum number of results to return
    
    Returns:
        Dictionary containing purchase orders and metadata
    """
    # Build OData filter
    filters = []
    if vendor:
        filters.append(f"Supplier eq '{vendor}'")
    if plant:
        filters.append(f"PurchasingOrganization eq '{plant}'")
    
    params = {'$top': str(limit)}
    if filters:
        params['$filter'] = ' and '.join(filters)
    
    # Make API request
    result = _make_request('/A_PurchaseOrder', params)
    
    if not result['success']:
        return {
            "success": False,
            "error": result['error'],
            "query_timestamp": datetime.now().isoformat(),
            "source_system": "SAP S/4HANA"
        }
    
    # Parse response
    raw_pos = result['data'].get('d', {}).get('results', [])
    
    # Transform to cleaner format
    purchase_orders = []
    total_value = 0.0
    
    for po in raw_pos:
        po_data = {
            "po_number": po.get('PurchaseOrder', ''),
            "vendor_id": po.get('Supplier', ''),
            "vendor": po.get('SupplierName', po.get('Supplier', '')),
            "company_code": po.get('CompanyCode', ''),
            "purchasing_org": po.get('PurchasingOrganization', ''),
            "purchasing_group": po.get('PurchasingGroup', ''),
            "document_type": po.get('PurchaseOrderType', ''),
            "created_date": po.get('CreationDate', ''),
            "created_by": po.get('CreatedByUser', ''),
            "currency": po.get('DocumentCurrency', 'USD'),
            "status": "Active" if not po.get('PurchasingDocumentDeletionCode') else "Deleted"
        }
        purchase_orders.append(po_data)
    
    return {
        "success": True,
        "count": len(purchase_orders),
        "purchase_orders": purchase_orders,
        "query_timestamp": datetime.now().isoformat(),
        "source_system": "SAP S/4HANA (Live)"
    }


def get_purchase_order_by_id(po_number: str) -> dict:
    """
    Retrieve a specific Purchase Order by PO Number
    
    Args:
        po_number: The Purchase Order number (e.g., "4500000001")
    
    Returns:
        Dictionary containing the purchase order details
    """
    # Make API request for specific PO
    result = _make_request(f"/A_PurchaseOrder('{po_number}')")
    
    if not result['success']:
        return {
            "success": False,
            "error": result['error'],
            "query_timestamp": datetime.now().isoformat(),
            "source_system": "SAP S/4HANA"
        }
    
    po = result['data'].get('d', {})
    
    if not po:
        return {
            "success": False,
            "error": f"Purchase Order {po_number} not found",
            "query_timestamp": datetime.now().isoformat(),
            "source_system": "SAP S/4HANA"
        }
    
    po_data = {
        "po_number": po.get('PurchaseOrder', ''),
        "vendor_id": po.get('Supplier', ''),
        "vendor": po.get('SupplierName', po.get('Supplier', '')),
        "company_code": po.get('CompanyCode', ''),
        "purchasing_org": po.get('PurchasingOrganization', ''),
        "purchasing_group": po.get('PurchasingGroup', ''),
        "document_type": po.get('PurchaseOrderType', ''),
        "created_date": po.get('CreationDate', ''),
        "created_by": po.get('CreatedByUser', ''),
        "currency": po.get('DocumentCurrency', 'USD'),
        "status": "Active" if not po.get('PurchasingDocumentDeletionCode') else "Deleted",
        "payment_terms": po.get('PaymentTerms', ''),
        "incoterms": po.get('IncotermsClassification', ''),
        "validity_start": po.get('ValidityStartDate', ''),
        "validity_end": po.get('ValidityEndDate', '')
    }
    
    return {
        "success": True,
        "purchase_order": po_data,
        "query_timestamp": datetime.now().isoformat(),
        "source_system": "SAP S/4HANA (Live)"
    }


def get_vendor_summary() -> dict:
    """
    Get summary of Purchase Orders grouped by vendor
    
    Returns:
        Dictionary containing vendor-wise PO summary
    """
    # Get all POs (up to 100 for summary)
    result = _make_request('/A_PurchaseOrder', {'$top': '100'})
    
    if not result['success']:
        return {
            "success": False,
            "error": result['error'],
            "query_timestamp": datetime.now().isoformat(),
            "source_system": "SAP S/4HANA"
        }
    
    raw_pos = result['data'].get('d', {}).get('results', [])
    
    # Group by vendor
    vendor_summary = {}
    
    for po in raw_pos:
        vendor_id = po.get('Supplier', 'Unknown')
        
        if vendor_id not in vendor_summary:
            vendor_summary[vendor_id] = {
                "vendor_id": vendor_id,
                "vendor_name": po.get('SupplierName', vendor_id),
                "po_count": 0,
                "company_codes": set(),
                "purchasing_orgs": set()
            }
        
        vendor_summary[vendor_id]["po_count"] += 1
        vendor_summary[vendor_id]["company_codes"].add(po.get('CompanyCode', ''))
        vendor_summary[vendor_id]["purchasing_orgs"].add(po.get('PurchasingOrganization', ''))
    
    # Convert sets to lists for JSON serialization
    vendors_list = []
    for vendor in vendor_summary.values():
        vendor["company_codes"] = list(vendor["company_codes"])
        vendor["purchasing_orgs"] = list(vendor["purchasing_orgs"])
        vendors_list.append(vendor)
    
    # Sort by PO count descending
    vendors_list.sort(key=lambda x: x["po_count"], reverse=True)
    
    return {
        "success": True,
        "vendor_count": len(vendors_list),
        "total_pos": len(raw_pos),
        "vendors": vendors_list,
        "query_timestamp": datetime.now().isoformat(),
        "source_system": "SAP S/4HANA (Live)"
    }
