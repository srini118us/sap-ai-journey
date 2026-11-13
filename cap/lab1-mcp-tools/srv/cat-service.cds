using procurement from '../db/schema';

service ProcurementService @(path: '/odata/v4/procurement') {

  @readonly entity Suppliers      as projection on procurement.Suppliers;
  @readonly entity PurchaseOrders as projection on procurement.PurchaseOrders;

  function checkPOStatus(poNumber: String) returns {
    poNumber : String; status : String; amount : Decimal; currency : String; supplierName : String;
  };

  function setPOStatus(poNumber: String, newStatus: String, approver: String) returns {
    poNumber : String; status : String; amount : Decimal; currency : String; message : String;
  };
}
annotate ProcurementService with @mcp;
