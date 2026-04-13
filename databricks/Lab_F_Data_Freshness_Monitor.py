# Databricks notebook source
# MAGIC %md
# MAGIC Data Freshness

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Data Freshness Monitor: Tables with __TIMESTAMP metadata
# MAGIC
# MAGIC SELECT 
# MAGIC     'Cashflow' as TableName,
# MAGIC     COUNT(*) as TotalRecords,
# MAGIC     MAX(__TIMESTAMP) as LatestUpdate,
# MAGIC     MIN(__TIMESTAMP) as OldestRecord,
# MAGIC     DATEDIFF(CURRENT_DATE(), MAX(__TIMESTAMP)) as DaysStale
# MAGIC FROM bdc_share_cash_flow.cashflow.cashflow
# MAGIC
# MAGIC UNION ALL
# MAGIC
# MAGIC SELECT 
# MAGIC     'Journal Entry',
# MAGIC     COUNT(*),
# MAGIC     MAX(__TIMESTAMP),
# MAGIC     MIN(__TIMESTAMP),
# MAGIC     DATEDIFF(CURRENT_DATE(), MAX(__TIMESTAMP))
# MAGIC FROM bdc_share_journal_entry.entryviewjournalentry.operationalacctgdocitem
# MAGIC
# MAGIC UNION ALL
# MAGIC
# MAGIC SELECT 
# MAGIC     'Company Code',
# MAGIC     COUNT(*),
# MAGIC     MAX(__TIMESTAMP),
# MAGIC     MIN(__TIMESTAMP),
# MAGIC     DATEDIFF(CURRENT_DATE(), MAX(__TIMESTAMP))
# MAGIC FROM companycode_share.companycode.companycode
# MAGIC
# MAGIC ORDER BY DaysStale DESC

# COMMAND ----------

# MAGIC %md
# MAGIC Operation Type Breakdown

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Operation Type Distribution (I=Insert, U=Update, D=Delete, L=Load)
# MAGIC
# MAGIC SELECT 
# MAGIC     'Cashflow' as TableName,
# MAGIC     __OPERATION_TYPE as OperationType,
# MAGIC     COUNT(*) as RecordCount
# MAGIC FROM bdc_share_cash_flow.cashflow.cashflow
# MAGIC GROUP BY __OPERATION_TYPE
# MAGIC
# MAGIC UNION ALL
# MAGIC
# MAGIC SELECT 
# MAGIC     'Journal Entry',
# MAGIC     __OPERATION_TYPE,
# MAGIC     COUNT(*)
# MAGIC FROM bdc_share_journal_entry.entryviewjournalentry.operationalacctgdocitem
# MAGIC GROUP BY __OPERATION_TYPE
# MAGIC
# MAGIC UNION ALL
# MAGIC
# MAGIC SELECT 
# MAGIC     'Company Code',
# MAGIC     __OPERATION_TYPE,
# MAGIC     COUNT(*)
# MAGIC FROM companycode_share.companycode.companycode
# MAGIC GROUP BY __OPERATION_TYPE
# MAGIC
# MAGIC ORDER BY TableName, OperationType

# COMMAND ----------

# MAGIC %md
# MAGIC  Replication Timeline (When did changes happen?)

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Replication Timeline: Group by date to see when data was replicated
# MAGIC
# MAGIC SELECT 
# MAGIC     'Cashflow' as TableName,
# MAGIC     DATE(__TIMESTAMP) as ReplicationDate,
# MAGIC     COUNT(*) as RecordCount
# MAGIC FROM bdc_share_cash_flow.cashflow.cashflow
# MAGIC GROUP BY DATE(__TIMESTAMP)
# MAGIC
# MAGIC UNION ALL
# MAGIC
# MAGIC SELECT 
# MAGIC     'Journal Entry',
# MAGIC     DATE(__TIMESTAMP),
# MAGIC     COUNT(*)
# MAGIC FROM bdc_share_journal_entry.entryviewjournalentry.operationalacctgdocitem
# MAGIC GROUP BY DATE(__TIMESTAMP)
# MAGIC
# MAGIC ORDER BY TableName, ReplicationDate DESC
# MAGIC LIMIT 20

# COMMAND ----------

# MAGIC %md
# MAGIC Health Summary & Alerts

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Data Health Summary with Alert Status
# MAGIC
# MAGIC SELECT 
# MAGIC     TableName,
# MAGIC     TotalRecords,
# MAGIC     LatestUpdate,
# MAGIC     DaysStale,
# MAGIC     CASE 
# MAGIC         WHEN DaysStale <= 1 THEN '🟢 Fresh'
# MAGIC         WHEN DaysStale <= 7 THEN '🟡 Warning'
# MAGIC         ELSE '🔴 Stale'
# MAGIC     END as HealthStatus
# MAGIC FROM (
# MAGIC     SELECT 
# MAGIC         'Cashflow' as TableName,
# MAGIC         COUNT(*) as TotalRecords,
# MAGIC         MAX(__TIMESTAMP) as LatestUpdate,
# MAGIC         DATEDIFF(CURRENT_DATE(), MAX(__TIMESTAMP)) as DaysStale
# MAGIC     FROM bdc_share_cash_flow.cashflow.cashflow
# MAGIC
# MAGIC     UNION ALL
# MAGIC
# MAGIC     SELECT 
# MAGIC         'Journal Entry',
# MAGIC         COUNT(*),
# MAGIC         MAX(__TIMESTAMP),
# MAGIC         DATEDIFF(CURRENT_DATE(), MAX(__TIMESTAMP))
# MAGIC     FROM bdc_share_journal_entry.entryviewjournalentry.operationalacctgdocitem
# MAGIC
# MAGIC     UNION ALL
# MAGIC
# MAGIC     SELECT 
# MAGIC         'Company Code',
# MAGIC         COUNT(*),
# MAGIC         MAX(__TIMESTAMP),
# MAGIC         DATEDIFF(CURRENT_DATE(), MAX(__TIMESTAMP))
# MAGIC     FROM companycode_share.companycode.companycode
# MAGIC )
# MAGIC ORDER BY DaysStale DESC

# COMMAND ----------

# MAGIC %md
# MAGIC Visual Dashboard (Python)

# COMMAND ----------

import pandas as pd
import matplotlib.pyplot as plt

# Run SQL query and get results
query = """
SELECT 
    TableName,
    TotalRecords,
    DaysStale,
    CASE 
        WHEN DaysStale <= 1 THEN 'Fresh'
        WHEN DaysStale <= 7 THEN 'Warning'
        ELSE 'Stale'
    END as Status
FROM (
    SELECT 
        'Cashflow' as TableName,
        COUNT(*) as TotalRecords,
        DATEDIFF(CURRENT_DATE(), MAX(__TIMESTAMP)) as DaysStale
    FROM bdc_share_cash_flow.cashflow.cashflow

    UNION ALL

    SELECT 
        'Journal Entry',
        COUNT(*),
        DATEDIFF(CURRENT_DATE(), MAX(__TIMESTAMP))
    FROM bdc_share_journal_entry.entryviewjournalentry.operationalacctgdocitem

    UNION ALL

    SELECT 
        'Company Code',
        COUNT(*),
        DATEDIFF(CURRENT_DATE(), MAX(__TIMESTAMP))
    FROM companycode_share.companycode.companycode
)
ORDER BY DaysStale DESC
"""

df = spark.sql(query).toPandas()

# Visualization
fig, ax = plt.subplots(figsize=(10, 4))
colors = ['red' if d > 7 else 'orange' if d > 1 else 'green' for d in df['DaysStale']]
bars = ax.barh(df['TableName'], df['DaysStale'], color=colors)
ax.set_xlabel('Days Since Last Update')
ax.set_title('BDC Data Freshness Monitor (Live)')
ax.axvline(x=7, color='orange', linestyle='--', label='Warning Threshold')

for i, row in df.iterrows():
    status_icon = '🔴' if row['Status'] == 'Stale' else '🟡' if row['Status'] == 'Warning' else '🟢'
    ax.text(row['DaysStale'] + 2, i, f"{row['DaysStale']} days {status_icon}", va='center')

plt.tight_layout()
plt.show()

# Summary Table
print("\n" + "="*60)
print("BDC DATA FRESHNESS DASHBOARD")
print("="*60)
display(df)
print("="*60)