import cds from '@sap/cds';

export default class ProcurementService extends cds.ApplicationService {
  init() {
    const { PurchaseOrders, Suppliers } = this.entities;

    this.on('checkPOStatus', async (req) => {
      const { poNumber } = req.data;
      if (!poNumber || !poNumber.trim()) return req.error(400, 'poNumber is required');
      const po = await SELECT.one.from(PurchaseOrders).where({ poNumber });
      if (!po) return req.error(404, `PO ${poNumber} not found`);
      const supplier = await SELECT.one.from(Suppliers).where({ ID: po.supplier_ID });
      return { poNumber: po.poNumber, status: po.status, amount: po.amount, currency: po.currency, supplierName: supplier ? supplier.name : 'Unknown' };
    });

    this.on('setPOStatus', async (req) => {
      const { poNumber, newStatus, approver } = req.data;
      if (!poNumber || !poNumber.trim()) return req.error(400, 'poNumber is required');
      const allowed = ['Open', 'Approved', 'Blocked'];
      if (!allowed.includes(newStatus)) return req.error(400, `newStatus must be one of: ${allowed.join(', ')}`);
      const po = await SELECT.one.from(PurchaseOrders).where({ poNumber });
      if (!po) return req.error(404, `PO ${poNumber} not found`);
      if (newStatus === 'Approved' && po.amount > 40000 && (!approver || !approver.trim())) {
        return req.error(403, `PO ${poNumber} is ${po.amount} ${po.currency}, above 40000. An approver is required.`);
      }
      await UPDATE(PurchaseOrders).set({ status: newStatus }).where({ poNumber });
      return { poNumber: po.poNumber, status: newStatus, amount: po.amount, currency: po.currency, message: `PO ${poNumber} set to ${newStatus}${approver ? ' by ' + approver : ''}` };
    });

    return super.init();
  }
}
