namespace pd;

entity PredictionLog {
  key ID               : UUID;
      createdAt        : Timestamp;
      invoiceAmount    : Decimal(15,2);
      paymentTerms     : Integer;
      priorDelays      : Integer;
      vendorRating     : Decimal(4,2);
      invoiceMonth     : Integer;
      companyCode      : String(4);
      delayProbability : Decimal(9,8);
      predictedDelayed : Integer;
}