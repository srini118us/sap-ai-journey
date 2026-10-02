# Vendor MDQ Copilot: Data Load Runbook

Two loading paths documented below. Pick whichever is fastest.

---

## Path A: HANA Database Explorer Import Wizard (UI)

Fastest for one time load. Repeat 4 times (one per table).

### Steps

1. Open **SAP HANA Database Explorer** connected to `hana-cloud`, schema `DBADMIN`
2. In left panel, expand **DBADMIN** → **Tables**
3. Right-click **VENDORS** table
4. Select **Import Data** (or similar wording depending on version)
5. Choose **Import from Local File**
6. Upload `data/vendors.csv`
7. Confirm:
   - File encoding: UTF-8
   - Delimiter: comma
   - Column header: first row is header
   - Column mapping: auto-mapped by name (verify all 16 columns matched)
8. Click **Import** → wait for confirmation (150 rows loaded)
9. Repeat for the remaining 3 tables:
   - TRANSACTIONS → `transactions.csv` (500 rows)
   - QUALITY_RULES → `quality_rules.csv` (30 rows)
   - QUALITY_ISSUES → `quality_issues.csv` (200 rows)

### Verify

```sql
SELECT 'VENDORS' AS TABLE_NAME, COUNT(*) AS ROW_COUNT FROM VENDORS
UNION ALL SELECT 'TRANSACTIONS', COUNT(*) FROM TRANSACTIONS
UNION ALL SELECT 'QUALITY_RULES', COUNT(*) FROM QUALITY_RULES
UNION ALL SELECT 'QUALITY_ISSUES', COUNT(*) FROM QUALITY_ISSUES;
```

Expected result: 150, 500, 30, 200

---

## Path B: Bulk INSERT SQL Script (portable, repeatable)

Single file, run once, all 880 rows inserted.

### Steps

1. Open `03_load_data.sql` in Database Explorer SQL editor
2. Click **Run** to execute the entire script
3. Watch bottom panel for success messages
4. Final SELECT will show row counts

### File contents

- Optional DELETE at top clears existing data (safe rerun)
- 4 INSERT blocks (batched 100 rows per statement)
- Verification SELECT at bottom

### If script size is too big for the editor

Split file into 4 parts by table:
- Section 1: VENDORS block
- Section 2: TRANSACTIONS block
- Section 3: QUALITY_RULES block
- Section 4: QUALITY_ISSUES block

Run each section separately.

---

## Sanity queries to run after load

Confirm the intentional MDQ defects landed correctly:

```sql
-- Should return 5 vendors (no tax ID)
SELECT COUNT(*) AS MISSING_TAX_COUNT 
FROM VENDORS 
WHERE STATUS = 'ACTIVE' AND (TAX_ID IS NULL OR TAX_ID = '');

-- Should return 5 pairs (duplicate addresses)
SELECT ADDRESS_LINE1, CITY, COUNT(*) AS DUP_COUNT
FROM VENDORS
GROUP BY ADDRESS_LINE1, CITY
HAVING COUNT(*) > 1
ORDER BY DUP_COUNT DESC;

-- Should return 10 transactions (posted to BLOCKED vendors)
SELECT T.TXN_ID, T.VENDOR_ID, V.STATUS, T.AMOUNT
FROM TRANSACTIONS T
JOIN VENDORS V ON T.VENDOR_ID = V.VENDOR_ID
WHERE V.STATUS = 'BLOCKED';

-- Should return 10 (round amount weekend postings)
SELECT TXN_ID, POSTING_DATE, AMOUNT
FROM TRANSACTIONS
WHERE MOD(AMOUNT, 5000) = 0
  AND AMOUNT >= 10000
  AND WEEKDAY(POSTING_DATE) IN (5, 6);

-- Spend by category (top 5)
SELECT V.CATEGORY, COUNT(*) AS TXN_COUNT, SUM(T.AMOUNT) AS TOTAL_SPEND
FROM TRANSACTIONS T
JOIN VENDORS V ON T.VENDOR_ID = V.VENDOR_ID
GROUP BY V.CATEGORY
ORDER BY TOTAL_SPEND DESC
LIMIT 5;
```

---

## Troubleshooting

**Error: cannot import due to character encoding**
- Confirm CSV saved as UTF-8 (not Latin-1)
- If HANA rejects some rows, check for special characters in vendor names

**Error: value too long for column**
- All columns sized generously in DDL, this should not happen with generated data
- If custom data added, extend NVARCHAR sizes in the DDL

**Error: primary key duplicate**
- Someone previously loaded data. Run DELETE FROM statements at top of `03_load_data.sql` first, then reload.

**Import wizard not found**
- Some Database Explorer versions place it under **Tools** menu instead of right-click
- If missing entirely, use Path B (INSERT SQL) instead

---

## Next steps after successful load

1. Run the sanity queries above → confirm data quality defects visible
2. Move to Phase 3: policy PDF chunking and Grounding upload
3. Then: AI Core embedding population via Python script
