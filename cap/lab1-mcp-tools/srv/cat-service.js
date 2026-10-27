import cds from '@sap/cds';

export default class ProcurementService extends cds.ApplicationService {
  init() {
    const { PurchaseOrders, Suppliers } = this.entities;

    this.on('checkPOStatus', async (req) => {
      const { poNumber } = req.data;
      const po = await SELECT.one.from(PurchaseOrders).where({ poNumber });
      if (!po) return req.error(404, `PO ${poNumber} not found`);
      const supplier = await SELECT.one.from(Suppliers).where({ ID: po.supplier_ID });
      return {
        poNumber: po.poNumber,
        status: po.status,
        amount: po.amount,
        currency: po.currency,
        supplierName: supplier ? supplier.name : 'Unknown'
      };
    });

    return super.init();
  }
}