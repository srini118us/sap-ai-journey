# Databricks notebook source
# MAGIC %pip install scikit-learn pandas numpy matplotlib seaborn --quiet

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

# MAGIC %md
# MAGIC Load & Prepare Data

# COMMAND ----------

from decimal import Decimal
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import LabelEncoder, StandardScaler

TABLE_PATH = "bdc_share_journal_entry.entryviewjournalentry.operationalacctgdocitem"

columns_needed = [
    "CompanyCode", "AccountingDocument", "FiscalYear", "GLAccount",
    "CostCenter", "ProfitCenter", "AccountingDocumentType", "PostingDate",
    "DebitCreditCode", "IsAutomaticallyCreated", "AmountInCompanyCodeCurrency",
    "AmountInTransactionCurrency", "Quantity"
]

df = spark.table(TABLE_PATH).select(columns_needed).limit(50000).toPandas()

for col in df.columns:
    df[col] = df[col].apply(lambda x: float(x) if isinstance(x, Decimal) else x)

print("Loaded:", len(df), "rows")

# COMMAND ----------

# MAGIC %md
# MAGIC  Feature Engineering & Model

# COMMAND ----------

df_ml = df.copy()

df_ml['PostingDate'] = pd.to_datetime(df_ml['PostingDate'], errors='coerce')
df_ml['DayOfWeek'] = df_ml['PostingDate'].dt.dayofweek
df_ml['IsWeekend'] = df_ml['DayOfWeek'].isin([5, 6]).astype(int)
df_ml['DayOfMonth'] = df_ml['PostingDate'].dt.day
df_ml['Month'] = df_ml['PostingDate'].dt.month
df_ml['AbsAmount'] = df_ml['AmountInCompanyCodeCurrency'].abs()
df_ml['LogAbsAmount'] = np.log1p(df_ml['AbsAmount'])
df_ml['IsNegative'] = (df_ml['AmountInCompanyCodeCurrency'] < 0).astype(int)
df_ml['IsManual'] = (~df_ml['IsAutomaticallyCreated']).astype(int)
df_ml['IsDebit'] = (df_ml['DebitCreditCode'] == 'S').astype(int)

categorical_cols = ['CompanyCode', 'GLAccount', 'CostCenter', 'AccountingDocumentType']
for col in categorical_cols:
    le = LabelEncoder()
    df_ml[col + '_encoded'] = le.fit_transform(df_ml[col].astype(str))

feature_columns = [
    'AbsAmount', 'LogAbsAmount', 'IsNegative', 'IsWeekend', 'DayOfWeek',
    'DayOfMonth', 'Month', 'IsManual', 'IsDebit', 'CompanyCode_encoded',
    'GLAccount_encoded', 'CostCenter_encoded', 'AccountingDocumentType_encoded'
]

X = df_ml[feature_columns].copy()
X = X.replace([np.inf, -np.inf], np.nan)
X = X.fillna(X.median())

scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

model = IsolationForest(n_estimators=100, contamination=0.05, random_state=42, n_jobs=-1)
df_ml['anomaly_score'] = model.fit_predict(X_scaled)
df_ml['anomaly_label'] = df_ml['anomaly_score'].map({1: 'Normal', -1: 'Anomaly'})

print("Anomaly Detection Complete!")
print("\nResults:")
print(df_ml['anomaly_label'].value_counts())
print("\nAnomaly Rate:", round(df_ml['anomaly_label'].value_counts(normalize=True)['Anomaly'] * 100, 2), "%")

# COMMAND ----------

# MAGIC %md
# MAGIC Visualization

# COMMAND ----------

fig, axes = plt.subplots(2, 2, figsize=(14, 10))

axes[0, 0].boxplot([
    df_ml[df_ml['anomaly_label'] == 'Normal']['LogAbsAmount'],
    df_ml[df_ml['anomaly_label'] == 'Anomaly']['LogAbsAmount']
], tick_labels=['Normal', 'Anomaly'])
axes[0, 0].set_title('Log Amount Distribution')
axes[0, 0].set_ylabel('Log(Amount)')

weekend_rates = df_ml.groupby('anomaly_label')['IsWeekend'].mean() * 100
axes[0, 1].bar(weekend_rates.index, weekend_rates.values, color=['steelblue', 'coral'])
axes[0, 1].set_title('Weekend Posting Rate')
axes[0, 1].set_ylabel('Percentage (%)')

manual_rates = df_ml.groupby('anomaly_label')['IsManual'].mean() * 100
axes[1, 0].bar(manual_rates.index, manual_rates.values, color=['steelblue', 'coral'])
axes[1, 0].set_title('Manual Entry Rate')
axes[1, 0].set_ylabel('Percentage (%)')

anomaly_dow = df_ml[df_ml['anomaly_label'] == 'Anomaly']['DayOfWeek'].value_counts().sort_index()
normal_dow = df_ml[df_ml['anomaly_label'] == 'Normal']['DayOfWeek'].value_counts().sort_index()
x = range(7)
width = 0.35
axes[1, 1].bar([i - width/2 for i in x], normal_dow.values, width, label='Normal', color='steelblue')
axes[1, 1].bar([i + width/2 for i in x], anomaly_dow.values, width, label='Anomaly', color='coral')
axes[1, 1].set_xticks(x)
axes[1, 1].set_xticklabels(['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'])
axes[1, 1].set_title('Entries by Day of Week')
axes[1, 1].legend()

plt.tight_layout()
plt.show()

# COMMAND ----------

# MAGIC %md
# MAGIC Top Anomalies & Summary

# COMMAND ----------

anomalies = df_ml[df_ml['anomaly_label'] == 'Anomaly'].copy()

print("Top 10 Anomalies by Amount:")
display(anomalies[[
    'AccountingDocument', 'PostingDate', 'CompanyCode', 'GLAccount',
    'AmountInCompanyCodeCurrency', 'IsWeekend', 'IsManual', 'anomaly_label'
]].sort_values('AmountInCompanyCodeCurrency', key=abs, ascending=False).head(10))

print("\n" + "=" * 50)
print("JOURNAL ENTRY ANOMALY DETECTION SUMMARY")
print("=" * 50)
print("Total entries:", len(df_ml))
print("Anomalies detected:", len(anomalies))
print("Anomaly rate:", round(len(anomalies) / len(df_ml) * 100, 2), "%")
print("Weekend anomaly rate:", round(anomalies['IsWeekend'].mean() * 100, 2), "%")
print("Top anomaly amount: $", round(anomalies['AmountInCompanyCodeCurrency'].abs().max(), 2))
print("Suspicious GL accounts:", anomalies['GLAccount'].nunique())
print("=" * 50)

print("\nTop 5 GL Accounts with Most Anomalies:")
print(anomalies['GLAccount'].value_counts().head())

# COMMAND ----------

# MAGIC %md
# MAGIC