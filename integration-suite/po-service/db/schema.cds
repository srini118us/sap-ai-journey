namespace procurement;

entity PurchaseOrderItems {
  key poNumber    : String(20);
  key itemNumber  : String(10);
      description : String(500);
      quantity    : Decimal(18, 4);
      unit        : String(30);
      unitCost    : Decimal(18, 6);
      lineTotal   : Decimal(18, 2);
}
