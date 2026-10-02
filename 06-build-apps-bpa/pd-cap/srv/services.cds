using pd from '../db/schema';

service PredictionService {

  entity Predictions as projection on pd.PredictionLog;

  action predictDelay(
    invoiceAmount : Decimal(15,2),
    paymentTerms  : Integer,
    priorDelays   : Integer,
    vendorRating  : Decimal(4,2),
    invoiceMonth  : Integer,
    companyCode   : String(4)
  ) returns {
    delayProbability : Decimal(9,8);
    predictedDelayed : Integer;
  };
}