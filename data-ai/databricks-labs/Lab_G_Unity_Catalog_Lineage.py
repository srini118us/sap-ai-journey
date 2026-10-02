# Databricks notebook source
# MAGIC %sql
# MAGIC -- Show all catalogs (data sources) available
# MAGIC SHOW CATALOGS

# COMMAND ----------

# MAGIC %sql
# MAGIC -- List all BDC delta share tables
# MAGIC SELECT 
# MAGIC     table_catalog as Catalog,
# MAGIC     table_schema as Schema,
# MAGIC     table_name as TableName,
# MAGIC     table_type as Type
# MAGIC FROM system.information_schema.tables
# MAGIC WHERE table_catalog LIKE '%share%'
# MAGIC ORDER BY table_catalog, table_schema

# COMMAND ----------

# MAGIC %md
# MAGIC All BDC Tables (Filtered)

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Show actual business tables only (exclude information_schema)
# MAGIC SELECT 
# MAGIC     table_catalog as Catalog,
# MAGIC     table_schema as Schema,
# MAGIC     table_name as TableName,
# MAGIC     table_type as Type
# MAGIC FROM system.information_schema.tables
# MAGIC WHERE table_catalog LIKE '%share%'
# MAGIC   AND table_schema != 'information_schema'
# MAGIC ORDER BY table_catalog, table_schema

# COMMAND ----------

# MAGIC %md
# MAGIC Column Details for Key Tables

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Show column metadata for cashflow table
# MAGIC SELECT 
# MAGIC     column_name as ColumnName,
# MAGIC     data_type as DataType,
# MAGIC     is_nullable as Nullable
# MAGIC FROM system.information_schema.columns
# MAGIC WHERE table_catalog = 'bdc_share_cash_flow'
# MAGIC   AND table_schema = 'cashflow'
# MAGIC   AND table_name = 'cashflow'
# MAGIC ORDER BY ordinal_position

# COMMAND ----------

# MAGIC %md
# MAGIC  Lineage Summary (Visual)

# COMMAND ----------

# MAGIC %sql
# MAGIC -- BDC Data Lineage Map
# MAGIC SELECT 
# MAGIC     'S/4HANA' as Source,
# MAGIC     '→' as Flow1,
# MAGIC     'SAP Datasphere' as Integration,
# MAGIC     '→' as Flow2,
# MAGIC     table_catalog as DatabricksCatalog,
# MAGIC     table_schema as Schema,
# MAGIC     table_name as TableName
# MAGIC FROM system.information_schema.tables
# MAGIC WHERE table_catalog LIKE '%share%'
# MAGIC   AND table_schema != 'information_schema'
# MAGIC ORDER BY table_catalog

# COMMAND ----------

# MAGIC %sql
# MAGIC -- BDC Data Lineage Summary by Domain
# MAGIC SELECT 
# MAGIC     table_catalog as BDC_Catalog,
# MAGIC     table_schema as Schema,
# MAGIC     COUNT(*) as TableCount,
# MAGIC     'S/4HANA → Datasphere → Databricks' as Lineage
# MAGIC FROM system.information_schema.tables
# MAGIC WHERE table_catalog LIKE '%share%'
# MAGIC   AND table_schema != 'information_schema'
# MAGIC GROUP BY table_catalog, table_schema
# MAGIC ORDER BY TableCount DESC

# COMMAND ----------

import matplotlib.pyplot as plt

# BDC Delta Share Catalog Summary
catalogs = {
    'bdc_share_cash_flow': ['cashflow', 'cashflowforecast'],
    'bdc_share_journal_entry': ['operationalacctgdocitem'],
    'bdc_share_vendorperformance': ['s4custom_vendorperformance'],
    'companycode_share': ['companycode', 'currencyrole', 'hierarchy (5 tables)'],
    'product_share': ['product', 'productplant', '+ 20 related tables']
}

fig, ax = plt.subplots(figsize=(14, 6))

# Create lineage flow
y_pos = 0
for catalog, tables in catalogs.items():
    ax.annotate('', xy=(0.7, y_pos), xytext=(0.3, y_pos),
                arrowprops=dict(arrowstyle='->', color='steelblue', lw=2))
    ax.annotate('', xy=(1.1, y_pos), xytext=(0.7, y_pos),
                arrowprops=dict(arrowstyle='->', color='green', lw=2))
    
    ax.text(0.15, y_pos, 'S/4HANA', ha='center', va='center', fontsize=10, 
            bbox=dict(boxstyle='round', facecolor='lightblue'))
    ax.text(0.5, y_pos, 'Datasphere', ha='center', va='center', fontsize=10,
            bbox=dict(boxstyle='round', facecolor='lightyellow'))
    ax.text(0.9, y_pos, catalog.replace('_share', '').replace('bdc_', ''), 
            ha='center', va='center', fontsize=9,
            bbox=dict(boxstyle='round', facecolor='lightgreen'))
    ax.text(1.25, y_pos, ', '.join(tables[:2]), ha='left', va='center', fontsize=8)
    
    y_pos -= 0.15

ax.set_xlim(0, 1.6)
ax.set_ylim(y_pos - 0.1, 0.15)
ax.axis('off')
ax.set_title('BDC Data Lineage: S/4HANA → SAP Datasphere → Databricks', fontsize=14, fontweight='bold')

plt.tight_layout()
plt.show()

print("\n" + "="*60)
print("BDC DELTA SHARE LINEAGE SUMMARY")
print("="*60)
print("Total Catalogs: 5")
print("Total Tables: 39")
print("Source: SAP S/4HANA")
print("Integration: SAP Datasphere (Delta Share)")
print("Target: Databricks Unity Catalog")
print("="*60)