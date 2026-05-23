const cds = require('@sap/cds');
const { executeHttpRequest } = require('@sap-cloud-sdk/http-client');

module.exports = class PredictionService extends cds.ApplicationService {
  init() {

    this.on('predictDelay', async (req) => {
      const { invoiceAmount, paymentTerms, priorDelays,
              vendorRating, invoiceMonth, companyCode } = req.data;

      const deploymentPath =
        '/v2/inference/deployments/dad5f68790f68864/v1/predict';

      const response = await executeHttpRequest(
        { destinationName: 'PD_AICORE' },
        {
          method: 'POST',
          url: deploymentPath,
          headers: {
            'AI-Resource-Group': 'ml-training',
            'Content-Type': 'application/json'
          },
          data: [{
            INVOICE_AMOUNT: invoiceAmount,
            PAYMENT_TERMS:  paymentTerms,
            PRIOR_DELAYS:   priorDelays,
            VENDOR_RATING:  vendorRating,
            INVOICE_MONTH:  invoiceMonth,
            COMPANY_CODE:   companyCode
          }]
        }
      );

      const result = response.data[0];

      await INSERT.into('pd.PredictionLog').entries({
        ID: cds.utils.uuid(),
        createdAt: new Date().toISOString(),
        invoiceAmount, paymentTerms, priorDelays,
        vendorRating, invoiceMonth, companyCode,
        delayProbability: result.delay_probability,
        predictedDelayed: result.predicted_delayed
      });

      return {
        delayProbability: result.delay_probability,
        predictedDelayed: result.predicted_delayed
      };
    });

    return super.init();
  }

};

