using { procurement as db } from '../db/schema';

@path: 'procurement'
service ProcurementService {
  @readonly
  entity PurchaseOrderItems as projection on db.PurchaseOrderItems;
}
