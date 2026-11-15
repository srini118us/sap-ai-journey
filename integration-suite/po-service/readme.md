# Procurement PO Lookup (SAP Integration Suite + CAP + HANA Cloud)

A practice lab on the SAP BTP trial. It replaces hardcoded answers in an
Integration Suite iFlow with a real database lookup: a purchase order is
read from SAP HANA Cloud through a CAP OData service, driven by the PO
number the caller sends.

This folder holds the CAP service only. The iFlow lives in the
Integration Suite tenant. No production or customer data is included; the
dataset is a public SAP purchase order sample.

## Architecture
1. Data: table PROCUREMENT_PURCHASEORDERITEMS in SAP HANA Cloud, 500 sample rows.
2. Service: this CAP app exposes the table as a read only OData v4 service.
3. Flow: the GetPOStatus iFlow reads the PO number from a header, calls the
   OData service filtered by it, and returns the row.

## Build and deploy (run in Business Application Studio)
    npm install
    mbt build
    cf deploy mta_archives/po-service_1.0.0.mtar

If the app is stopped after trial inactivity, restart it:
    cf start po-service-srv

## Verify
    https://<srv-app-host>/odata/v4/procurement/PurchaseOrderItems
    https://<srv-app-host>/odata/v4/procurement/PurchaseOrderItems?$filter=poNumber eq '19007185'

## Authentication note
For this read only lab the service runs with open auth (package.json:
"cds": { "requires": { "auth": "dummy" } }) so the iFlow can call it
without a token. In a real landscape, JWT and xsuaa stay on.

## Notes learned
- Custom HTTP headers are dropped unless listed in Allowed Headers.
- CSRF protection must be off for a read only OData query.
- The OData adapter fetches $metadata before the real call; a route 404
  there usually means the CAP app is stopped (cf start it).
- Trial Cloud Foundry apps stop after inactivity.
