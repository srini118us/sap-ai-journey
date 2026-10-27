namespace procurement;

using { cuid, managed } from '@sap/cds/common';

entity Suppliers : cuid, managed {
  name           : String(100) @mandatory;
  country        : String(3);
  category       : String(40);
  rating         : Integer;
  purchaseOrders : Association to many PurchaseOrders on purchaseOrders.supplier = $self;
}

entity PurchaseOrders : cuid, managed {
  poNumber     : String(20) @mandatory;
  supplier     : Association to Suppliers;
  amount       : Decimal(13,2);
  currency     : String(3);
  status       : String(20);
  orderDate    : Date;
  deliveryDate : Date;
}