// ═══════════════════════════════════════════════════════════════
//  SAP-RPT-1 Payment Risk Predictor — Service Handler
//  CAP + SAP-RPT-1 Integration Demo
//
//  HOW RPT-1 WORKS (In-Context Learning):
//  1. We send historical FI-AR records with KNOWN payment_risk labels
//     as "training context" rows
//  2. We append new customer rows with payment_risk = "[PREDICT]"
//  3. RPT-1 learns the pattern from context rows and fills in [PREDICT]
//  4. No model training required — works like few-shot prompting for tables
//
//  API Endpoint: https://rpt.cloud.sap/api/predict
//  Token:        Get from https://rpt.cloud.sap (login with S-user)
// ═══════════════════════════════════════════════════════════════

const cds   = require('@sap/cds');
const axios = require('axios');

const RPT1_API_URL = 'https://rpt.cloud.sap/api/predict';

module.exports = class PaymentRiskService extends cds.ApplicationService {

  async init() {
    const { PaymentHistory, NewCustomers, PredictionResults } = this.entities;

    // ── Action: runPrediction ─────────────────────────────────
    this.on('runPrediction', async (req) => {
      const { rpt1Token } = req.data;

      if (!rpt1Token || rpt1Token.trim() === '') {
        return req.error(400, 'RPT-1 token is required. Get yours from https://rpt.cloud.sap');
      }

      try {
        // Step 1: Load historical data as context (few-shot examples for RPT-1)
        const historicalData = await SELECT.from(PaymentHistory).columns(
          'customer_id', 'region', 'industry',
          'invoice_amount', 'payment_terms',
          'days_overdue_avg', 'num_late_payments',
          'credit_limit', 'outstanding_balance', 'payment_risk'
        );

        // Step 2: Load new customers to predict
        const newCustomers = await SELECT.from(NewCustomers);

        if (newCustomers.length === 0) {
          return req.error(400, 'No new customers found to predict.');
        }

        // Step 3: Build RPT-1 payload
        // Historical rows = context (known outcomes)
        // New customer rows = target rows (payment_risk = "[PREDICT]")
        const contextRows = historicalData.map(row => ({
          customer_id         : row.customer_id,
          region              : row.region,
          industry            : row.industry,
          invoice_amount      : String(row.invoice_amount),
          payment_terms       : row.payment_terms,
          days_overdue_avg    : String(row.days_overdue_avg),
          num_late_payments   : String(row.num_late_payments),
          credit_limit        : String(row.credit_limit),
          outstanding_balance : String(row.outstanding_balance),
          payment_risk        : row.payment_risk   // Known label — teaches RPT-1 the pattern
        }));

        const targetRows = newCustomers.map(row => ({
          customer_id         : row.customer_id,
          region              : row.region,
          industry            : row.industry,
          invoice_amount      : String(row.invoice_amount),
          payment_terms       : row.payment_terms,
          days_overdue_avg    : String(row.days_overdue_avg),
          num_late_payments   : String(row.num_late_payments),
          credit_limit        : String(row.credit_limit),
          outstanding_balance : String(row.outstanding_balance),
          payment_risk        : '[PREDICT]'         // RPT-1 fills this in
        }));

        const payload = {
          rows: [...contextRows, ...targetRows]
        };

        console.log(`[RPT-1] Sending ${contextRows.length} context rows + ${targetRows.length} prediction rows`);

        // Step 4: Call RPT-1 API
        const response = await axios.post(RPT1_API_URL, payload, {
          headers: {
            'Authorization': `Bearer ${rpt1Token}`,
            'Content-Type' : 'application/json'
          },
          timeout: 30000
        });

        // RPT-1 actual response shape:
        // { prediction: { predictions: [ { payment_risk: [{ prediction: "HIGH", confidence: 0.7 }] } ] } }
        const predictedRows = response.data?.prediction?.predictions;
        if (!Array.isArray(predictedRows)) {
          return req.error(500, 'Unexpected RPT-1 response: ' + JSON.stringify(response.data).substring(0, 400));
        }

        // Step 5 & 6: Map predictions to customers and persist
        const now = new Date().toISOString();
        const results = [];

        for (let i = 0; i < predictedRows.length; i++) {
          const predRow   = predictedRows[i];
          const customer  = newCustomers[i];

          // Extract from: { payment_risk: [{ prediction: "HIGH", confidence: 0.7 }] }
          const riskEntry     = predRow?.payment_risk?.[0] || {};
          const predictedRisk = riskEntry.prediction || 'UNKNOWN';
          const confidence    = riskEntry.confidence != null
                               ? (Math.round(riskEntry.confidence * 100) + '%')
                               : 'N/A';

          // Upsert into PredictionResults
          await UPSERT.into(PredictionResults).entries({
            ID              : customer.ID,
            customer_id     : customer.customer_id,
            customer_name   : customer.customer_name,
            region          : customer.region,
            industry        : customer.industry,
            invoice_amount  : customer.invoice_amount,
            predicted_risk  : predictedRisk,
            confidence      : String(confidence),
            predicted_at    : now
          });

          results.push({
            customer_id    : customer.customer_id,
            customer_name  : customer.customer_name,
            predicted_risk : predictedRisk,
            confidence     : String(confidence)
          });
        }

        console.log(`[RPT-1] Predictions complete: ${results.length} customers assessed`);
        return results;

      } catch (err) {
        const errorDetail = err.response?.data || err.message;
        console.error('[RPT-1] API Error:', errorDetail);

        if (err.response?.status === 401) {
          return req.error(401, 'Invalid RPT-1 token. Please get a valid token from https://rpt.cloud.sap');
        }
        if (err.response?.status === 429) {
          return req.error(429, 'RPT-1 rate limit reached. Please wait a moment and try again.');
        }
        return req.error(500, `RPT-1 prediction failed: ${JSON.stringify(errorDetail)}`);
      }
    });

    // ── Function: getRiskSummary ──────────────────────────────
    this.on('getRiskSummary', async () => {
      const results = await SELECT.from(PredictionResults);

      const total  = results.length;
      const high   = results.filter(r => r.predicted_risk === 'HIGH').length;
      const medium = results.filter(r => r.predicted_risk === 'MEDIUM').length;
      const low    = results.filter(r => r.predicted_risk === 'LOW').length;

      return {
        total_predicted   : total,
        high_risk_count   : high,
        medium_risk_count : medium,
        low_risk_count    : low,
        high_risk_pct     : total > 0 ? Math.round((high / total) * 100) : 0
      };
    });

    return super.init();
  }
};
