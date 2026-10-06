-- Validation checks run as unsaved SQL view previews in UC4_Procurement

-- V1 column check
SELECT it."PurchaseOrder", it."PurchaseOrderItem",
       it."NetAmount", hd."DocumentCurrency"
FROM "C_PURCHASEORDERITEMDEX" it
JOIN "C_PURCHASEORDERDEX" hd ON hd."PurchaseOrder" = it."PurchaseOrder"
LIMIT 5;

-- V2 currency distribution of delayed PO items
SELECT COALESCE(NULLIF(hd."DocumentCurrency", ''), 'BLANK') AS "Currency",
       COUNT(*) AS "DelayedItems",
       SUM(CAST(COALESCE(it."NetAmount", 0) AS DECIMAL(23,2))) AS "ItemValue"
FROM (SELECT DISTINCT "PurchaseOrder", "PurchaseOrderItem"
      FROM "V_DELAYED_SCHEDULE_LINES") d
JOIN "C_PURCHASEORDERITEMDEX" it
  ON it."PurchaseOrder" = d."PurchaseOrder"
 AND it."PurchaseOrderItem" = d."PurchaseOrderItem"
JOIN "C_PURCHASEORDERDEX" hd ON hd."PurchaseOrder" = d."PurchaseOrder"
GROUP BY COALESCE(NULLIF(hd."DocumentCurrency", ''), 'BLANK');

-- V3 reconciliation against delayed lines
SELECT COUNT(*) AS "TotalDelayedLines",
       SUM(CASE WHEN r."SUPPLIER" IS NOT NULL THEN 1 ELSE 0 END) AS "LinesScoredSuppliers",
       SUM(CASE WHEN r."SUPPLIER" IS NULL     THEN 1 ELSE 0 END) AS "LinesUnscoredSuppliers",
       COUNT(DISTINCT CASE WHEN r."SUPPLIER" IS NULL THEN dl."Supplier" END) AS "UnscoredSuppliers"
FROM "V_DELAYED_SCHEDULE_LINES" dl
LEFT JOIN (SELECT DISTINCT "SUPPLIER" FROM "V_SUPPLIER_RISK_LATEST") r
  ON r."SUPPLIER" = dl."Supplier";

-- V4 product checks (expected: 32 rows, 0 duplicates, 1,711 lines, 1 NULL risk row for SKIPPED_DQ)
SELECT COUNT(*)                                   AS "RowCount",
       COUNT(*) - COUNT(DISTINCT p."Supplier")    AS "DuplicateSuppliers",
       SUM(p."DelayedLineCount")                  AS "DelayedLinesInProduct",
       SUM(CASE WHEN p."DelayedLineCount" = 0 THEN 1 ELSE 0 END) AS "ZeroDelaySuppliers",
       SUM(CASE WHEN p."HistoricalOntimeRate" IS NULL THEN 1 ELSE 0 END) AS "NullOntimeRate",
       SUM(CASE WHEN p."AvgLeadTimeDays" IS NULL THEN 1 ELSE 0 END) AS "NullLeadTime",
       SUM(CASE WHEN p."RiskBand" IS NULL THEN 1 ELSE 0 END) AS "NullRiskBand"
FROM (
  SELECT r."SUPPLIER" AS "Supplier",
         r."RISK_BAND" AS "RiskBand",
         CAST(COALESCE(s."DelayedLineCount", 0) AS INTEGER) AS "DelayedLineCount",
         CAST(f."historical_ontime_rate" AS DECIMAL(6,4)) AS "HistoricalOntimeRate",
         CAST(f."avg_lead_time_days" AS DECIMAL(10,1)) AS "AvgLeadTimeDays"
  FROM "V_SUPPLIER_RISK_LATEST" r
  LEFT JOIN "V_SUPPLIER_FEATURES" f ON f."Supplier" = r."SUPPLIER"
  LEFT JOIN (SELECT "Supplier", COUNT(*) AS "DelayedLineCount"
             FROM "V_DELAYED_SCHEDULE_LINES" GROUP BY "Supplier") s
    ON s."Supplier" = r."SUPPLIER"
) p;
