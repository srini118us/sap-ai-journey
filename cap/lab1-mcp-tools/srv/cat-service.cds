using procurement from '../db/schema';

service ProcurementService @(path: '/odata/v4/procurement') {

  entity Suppliers      as projection on procurement.Suppliers;
  entity PurchaseOrders as projection on procurement.PurchaseOrders;

  function checkPOStatus(poNumber: String) returns {
    poNumber     : String;
    status       : String;
    amount       : Decimal;
    currency     : String;
    supplierName : String;
  };
}