using { sap.rpt1.paymentrisk as db } from '../db/schema';

service PaymentRiskService @(path: '/payment-risk') {

  // ─── Read-only views ───────────────────────
  @readonly entity PaymentHistory    as projection on db.PaymentHistory;
  @readonly entity NewCustomers      as projection on db.NewCustomers;
  @readonly entity PredictionResults as projection on db.PredictionResults;

  // ─── RPT-1 Prediction Action ───────────────
  // Calls https://rpt.cloud.sap/api/predict
  // Uses historical data as context (few-shot examples)
  // Predicts payment_risk for new customers
  action runPrediction(rpt1Token: String) returns array of {
    customer_id    : String;
    customer_name  : String;
    predicted_risk : String;
    confidence     : String;
  };

  // ─── Summary KPIs for Dashboard ───────────
  function getRiskSummary() returns {
    total_predicted  : Integer;
    high_risk_count  : Integer;
    medium_risk_count: Integer;
    low_risk_count   : Integer;
    high_risk_pct    : Integer;
  };
}
