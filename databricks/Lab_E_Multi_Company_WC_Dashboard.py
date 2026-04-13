# Databricks notebook source
# MAGIC %pip install pandas numpy matplotlib seaborn --quiet

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

# MAGIC %md
# MAGIC Load Data

# COMMAND ----------

from decimal import Decimal
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

df_company = spark.table("companycode_share.companycode.companycode").toPandas()
df_cashflow = spark.table("bdc_share_cash_flow.cashflow.cashflow").toPandas()

for col in df_cashflow.columns:
    df_cashflow[col] = df_cashflow[col].apply(lambda x: float(x) if isinstance(x, Decimal) else x)

print("Company Codes:", len(df_company))
print("Cashflow Records:", len(df_cashflow))
print("Unique Companies in Cashflow:", df_cashflow['CompanyCode'].nunique())

# COMMAND ----------

# MAGIC %md
# MAGIC Explore Companies

# COMMAND ----------

companies_with_data = df_cashflow['CompanyCode'].unique()
print("Companies with cashflow data:")
print(companies_with_data)

df_company_filtered = df_company[df_company['CompanyCode'].isin(companies_with_data)]
print("\nCompany Details:")
df_company_filtered[['CompanyCode', 'CompanyCodeName', 'Country', 'Currency']].sort_values('CompanyCode')

# COMMAND ----------

# MAGIC %md
# MAGIC Aggregate Cashflow by Company

# COMMAND ----------

df_merged = df_cashflow.merge(
    df_company[['CompanyCode', 'CompanyCodeName', 'Country', 'Currency']], 
    on='CompanyCode', 
    how='left'
)

company_summary = df_merged.groupby(['CompanyCode', 'CompanyCodeName', 'Country', 'Currency']).agg(
    TotalInflow=('AmountInCompanyCodeCurrency', lambda x: x[x > 0].sum()),
    TotalOutflow=('AmountInCompanyCodeCurrency', lambda x: x[x < 0].sum()),
    NetCashflow=('AmountInCompanyCodeCurrency', 'sum'),
    TransactionCount=('CashFlowID', 'count')
).reset_index()

company_summary['TotalOutflow'] = company_summary['TotalOutflow'].abs()
company_summary = company_summary.sort_values('NetCashflow', ascending=False)

print("Multi-Company Cashflow Summary:")
company_summary

# COMMAND ----------

# MAGIC %md
# MAGIC Multi-Company Dashboard

# COMMAND ----------

df_merged = df_cashflow.merge(
    df_company[['CompanyCode', 'CompanyCodeName', 'Country', 'Currency']],
    on='CompanyCode',
    how='left'
)

company_summary = df_merged.groupby(['CompanyCode', 'CompanyCodeName', 'Country']).agg(
    TotalInflow=('AmountInCompanyCodeCurrency', lambda x: x[x > 0].sum()),
    TotalOutflow=('AmountInCompanyCodeCurrency', lambda x: x[x < 0].sum()),
    NetCashflow=('AmountInCompanyCodeCurrency', 'sum'),
    TransactionCount=('CashFlowID', 'count')
).reset_index()

company_summary['TotalOutflow'] = company_summary['TotalOutflow'].abs()

print("Multi-Company Cashflow Summary:")
print("=" * 60)
display(company_summary.sort_values('NetCashflow', ascending=False))

# COMMAND ----------

# MAGIC %md
# MAGIC Dashboard Visualization

# COMMAND ----------

fig, axes = plt.subplots(2, 2, figsize=(16, 12))

# 1. Top 10 by Net Cashflow
top10 = company_summary.nlargest(10, 'NetCashflow')
colors = ['green' if x > 0 else 'red' for x in top10['NetCashflow']]
axes[0, 0].barh(top10['CompanyCode'], top10['NetCashflow'] / 1e9, color=colors)
axes[0, 0].set_xlabel('Net Cashflow (Billions)')
axes[0, 0].set_title('Top 10 Companies by Net Cashflow')
axes[0, 0].invert_yaxis()

# 2. Inflow vs Outflow Comparison
top8 = company_summary.nlargest(8, 'TransactionCount')
x = range(len(top8))
width = 0.35
axes[0, 1].bar([i - width/2 for i in x], top8['TotalInflow'] / 1e9, width, label='Inflow', color='green')
axes[0, 1].bar([i + width/2 for i in x], top8['TotalOutflow'] / 1e9, width, label='Outflow', color='red')
axes[0, 1].set_xticks(x)
axes[0, 1].set_xticklabels(top8['CompanyCode'], rotation=45)
axes[0, 1].set_ylabel('Amount (Billions)')
axes[0, 1].set_title('Inflow vs Outflow by Company')
axes[0, 1].legend()

# 3. By Country
country_summary = company_summary.groupby('Country')['NetCashflow'].sum().sort_values(ascending=False)
axes[1, 0].bar(country_summary.index, country_summary.values / 1e9, color='steelblue')
axes[1, 0].set_xlabel('Country')
axes[1, 0].set_ylabel('Net Cashflow (Billions)')
axes[1, 0].set_title('Net Cashflow by Country')

# 4. Transaction Volume
axes[1, 1].pie(top8['TransactionCount'], labels=top8['CompanyCode'], autopct='%1.1f%%')
axes[1, 1].set_title('Transaction Volume Distribution')

plt.tight_layout()
plt.show()

print("\nTotal Companies:", len(company_summary))
print("Total Net Cashflow: $", round(company_summary['NetCashflow'].sum() / 1e9, 2), "B")

# COMMAND ----------

# MAGIC %md
# MAGIC Summary Table

# COMMAND ----------

print("=" * 70)
print("MULTI-COMPANY WORKING CAPITAL DASHBOARD SUMMARY")
print("=" * 70)
print(f"Total Companies: {len(company_summary)}")
print(f"Countries: {company_summary['Country'].nunique()}")
print(f"Total Inflow: ${company_summary['TotalInflow'].sum() / 1e9:.2f}B")
print(f"Total Outflow: ${company_summary['TotalOutflow'].sum() / 1e9:.2f}B")
print(f"Net Cashflow: ${company_summary['NetCashflow'].sum() / 1e9:.2f}B")
print(f"Total Transactions: {company_summary['TransactionCount'].sum():,}")
print("=" * 70)
print("\nCompanies with Negative Cashflow (Attention Needed):")
negative = company_summary[company_summary['NetCashflow'] < 0][['CompanyCode', 'CompanyCodeName', 'NetCashflow']]
display(negative)