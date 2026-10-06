-- V_SDR_PRODUCT: curated source for the Supplier Delivery Risk data product
-- Space: UC4_Procurement | Semantic usage: Relational Dataset | Expose: Off
SELECT
  r."SUPPLIER"                                          AS "Supplier",
  r."RISK_BAND"                                         AS "RiskBand",
  CAST(r."LATE_PROBABILITY"   AS DECIMAL(6,4))          AS "LateProbability",
  CAST(r."ONTIME_PROBABILITY" AS DECIMAL(6,4))          AS "OntimeProbability",
  r."CONFIDENCE"                                        AS "Confidence",
  r."TOP_FACTOR"                                        AS "TopRiskFactor",
  r."STATUS"                                            AS "ScoringStatus",
  CAST(COALESCE(s."DelayedLineCount", 0) AS INTEGER)    AS "DelayedLineCount",
  CAST(COALESCE(s."DelayedPOCount", 0)   AS INTEGER)    AS "DelayedPOCount",
  CAST(COALESCE(v."DelayedPOValueUSD", 0) AS DECIMAL(23,2)) AS "DelayedPOValueUSD",
  CAST(f."historical_ontime_rate" AS DECIMAL(6,4))      AS "HistoricalOntimeRate",
  CAST(f."avg_lead_time_days"     AS DECIMAL(10,1))     AS "AvgLeadTimeDays",
  r."MODEL_ID"                                          AS "ModelId",
  r."RUN_ID"                                            AS "RunId",
  CAST(TO_VARCHAR(r."SCORED_AT", 'YYYY-MM-DD HH24:MI:SS') AS NVARCHAR(19)) AS "ScoredAt"
FROM "V_SUPPLIER_RISK_LATEST" r
LEFT JOIN "V_SUPPLIER_FEATURES" f
  ON f."Supplier" = r."SUPPLIER"
LEFT JOIN (
  SELECT "Supplier",
         COUNT(*)                        AS "DelayedLineCount",
         COUNT(DISTINCT "PurchaseOrder") AS "DelayedPOCount"
  FROM "V_DELAYED_SCHEDULE_LINES"
  GROUP BY "Supplier"
) s ON s."Supplier" = r."SUPPLIER"
LEFT JOIN (
  SELECT d."Supplier",
         SUM(CASE WHEN hd."DocumentCurrency" = 'USD'
                  THEN CAST(COALESCE(it."NetAmount", 0) AS DECIMAL(23,2))
                  ELSE 0 END) AS "DelayedPOValueUSD"
  FROM (
    SELECT DISTINCT "Supplier", "PurchaseOrder", "PurchaseOrderItem"
    FROM "V_DELAYED_SCHEDULE_LINES"
  ) d
  JOIN "C_PURCHASEORDERITEMDEX" it
    ON it."PurchaseOrder" = d."PurchaseOrder"
   AND it."PurchaseOrderItem" = d."PurchaseOrderItem"
  JOIN "C_PURCHASEORDERDEX" hd
    ON hd."PurchaseOrder" = d."PurchaseOrder"
  GROUP BY d."Supplier"
) v ON v."Supplier" = r."SUPPLIER"
