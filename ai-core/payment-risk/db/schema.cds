namespace sap.rpt1.paymentrisk;

// ─────────────────────────────────────────────
// Historical FI-AR Payment Records
// Simulates data from S/4HANA FI Aging Report
// ─────────────────────────────────────────────
entity PaymentHistory {
  key ID              : Integer;
  customer_id         : String(20);
  customer_name       : String(100);
  region              : String(30);
  industry            : String(50);
  invoice_amount      : Decimal(15, 2);
  payment_terms       : String(10);    // NET30, NET60, NET90
  days_overdue_avg    : Integer;       // average days overdue last 12 months
  num_late_payments   : Integer;       // count of late payments
  credit_limit        : Decimal(15, 2);
  outstanding_balance : Decimal(15, 2);
  payment_risk        : String(10);    // HIGH / MEDIUM / LOW (known outcome)
}

// ─────────────────────────────────────────────
// New Customers to Predict Risk For
// ─────────────────────────────────────────────
entity NewCustomers {
  key ID              : Integer;
  customer_id         : String(20);
  customer_name       : String(100);
  region              : String(30);
  industry            : String(50);
  invoice_amount      : Decimal(15, 2);
  payment_terms       : String(10);
  days_overdue_avg    : Integer;
  num_late_payments   : Integer;
  credit_limit        : Decimal(15, 2);
  outstanding_balance : Decimal(15, 2);
}

// ─────────────────────────────────────────────
// Prediction Results - stored after RPT-1 call
// ─────────────────────────────────────────────
entity PredictionResults {
  key ID              : Integer;
  customer_id         : String(20);
  customer_name       : String(100);
  region              : String(30);
  industry            : String(50);
  invoice_amount      : Decimal(15, 2);
  predicted_risk      : String(10);    // HIGH / MEDIUM / LOW (from RPT-1)
  confidence          : String(10);    // confidence score from RPT-1
  predicted_at        : Timestamp;
}
