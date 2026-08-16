import os, httpx, json
base = os.environ["SAP_BASE_URL"]; auth = (os.environ["SAP_USER"], os.environ["SAP_PASSWORD"])
svc = "/sap/opu/odata/sap/API_SALES_ORDER_SRV"
with httpx.Client(base_url=base, auth=auth, verify=False, timeout=300) as c:
    t = c.get(f"{svc}/$metadata", headers={"X-CSRF-Token": "Fetch"}).headers["x-csrf-token"]
    p = {"SalesOrderType": "OR", "SalesOrganization": "1710",
         "DistributionChannel": "10", "OrganizationDivision": "00",
         "SoldToParty": "17100009", "PurchaseOrderByCustomer": "CPO-2026-0815",
         "to_Item": [{"Material": "TG11", "RequestedQuantity": "10"}]}
    r = c.post(f"{svc}/A_SalesOrder", json=p,
               headers={"X-CSRF-Token": t, "Accept": "application/json"})
    print(r.status_code)
    print(json.dumps(r.json(), indent=1)[:6000])
