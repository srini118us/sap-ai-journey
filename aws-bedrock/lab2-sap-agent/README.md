# AWS Bedrock Lab 2: SAP Procurement Agent

Multi-tool conversational agent demonstrating SAP-like procurement operations using AWS Bedrock Converse API.

## Overview

This lab builds an interactive agent with conversation memory, multiple tool definitions, SAP procurement mock data, and rate limit handling.

## Tools Implemented

| Tool | Description |
|------|-------------|
| get_purchase_orders | Search POs by vendor, status, date |
| get_po_details | Get PO line items and details |
| check_inventory | Check material stock levels |
| get_vendor_info | Get vendor performance metrics |
| create_sales_order | Create SO from PO |

## Files

| File | Purpose |
|------|---------|
| sap_procurement_agent.py | Main agent with tools |
| .env | Configuration (AWS region, model IDs) |
| requirements.txt | Python dependencies |

## Usage

```bash
python sap_procurement_agent.py
```

Example prompts:

- Show me all purchase orders from ACME Corp
- What are the details of PO 4500000123?
- Check inventory for Steel Plates
- Create a sales order from PO 4500000123 for customer TechCorp

## Architecture

```
User Input
    |
    v
Bedrock Converse API --> Claude Sonnet 4
    |                         |
    v                         v
Tool Router             Response Generation
    |
    v
Mock SAP Data
  - Purchase Orders
  - Inventory
  - Vendors
```

## Configuration

Environment variables in .env file:

- AWS_REGION: AWS region (default: us-east-1)
- BEDROCK_MODEL_SONNET: Model inference profile ID
- BEDROCK_RETRY_ATTEMPTS: Number of retry attempts for rate limiting
- BEDROCK_RETRY_DELAY: Delay between retries in seconds

## Next Steps

- Connect to real S/4HANA via OData APIs
- Add more tools (goods receipt, invoice processing)
- Implement streaming responses
