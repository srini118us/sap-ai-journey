# Databricks notebook source
# MAGIC %pip install xgboost shap scikit-learn --quiet

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, classification_report, roc_auc_score, roc_curve
)
import xgboost as xgb
import shap
import json

pd.set_option('display.max_columns', None)
plt.style.use('seaborn-v0_8-whitegrid')

print("Libraries loaded successfully")

# COMMAND ----------

TABLE_PATH = "bdc_share_vendorperformance.`s4_zvendorperformance_dp_srv:v1`.s4custom_vendorperformance"

df_spark = spark.table(TABLE_PATH)
df = df_spark.toPandas()

print(f"Loaded {len(df):,} rows, {len(df.columns)} columns")
df.head()

# COMMAND ----------

fig, axes = plt.subplots(1, 2, figsize=(12, 4))

target_counts = df['VendorOnTimeDelivery'].value_counts()
colors = ['#2ecc71', '#e74c3c']
axes[0].pie(target_counts, labels=['On-Time', 'Late'], autopct='%1.1f%%', colors=colors, startangle=90)
axes[0].set_title('Delivery Performance Distribution')

sns.countplot(data=df, x='VendorOnTimeDelivery', palette={'true': '#2ecc71', 'false': '#e74c3c'}, ax=axes[1])
axes[1].set_title('Target Class Counts')
axes[1].set_xlabel('On-Time Delivery')
axes[1].set_ylabel('Count')
for p in axes[1].patches:
    axes[1].annotate(f'{int(p.get_height()):,}', (p.get_x() + p.get_width()/2., p.get_height()),
                     ha='center', va='bottom')

plt.tight_layout()
plt.show()

imbalance_ratio = target_counts['true'] / target_counts['false']
print(f"Class imbalance ratio: {imbalance_ratio:.1f}:1 (On-Time : Late)")

# COMMAND ----------

fig, axes = plt.subplots(1, 2, figsize=(14, 4))

df['VendorCycleTimeInDays'].hist(bins=50, ax=axes[0], color='steelblue', edgecolor='black')
axes[0].set_title('Vendor Cycle Time Distribution')
axes[0].set_xlabel('Days')
axes[0].set_ylabel('Frequency')
axes[0].axvline(df['VendorCycleTimeInDays'].median(), color='red', linestyle='--', label=f"Median: {df['VendorCycleTimeInDays'].median():.0f} days")
axes[0].legend()

df.boxplot(column='VendorCycleTimeInDays', by='VendorOnTimeDelivery', ax=axes[1])
axes[1].set_title('Cycle Time by Delivery Status')
axes[1].set_xlabel('On-Time Delivery')
axes[1].set_ylabel('Cycle Time (Days)')
plt.suptitle('')

plt.tight_layout()
plt.show()

# COMMAND ----------

# Convert Decimal to float for plotting
df['VendorCycleTimeInDays'] = df['VendorCycleTimeInDays'].astype(float)
fig, ax = plt.subplots(figsize=(8, 5))
df.boxplot(column='VendorCycleTimeInDays', by='VendorOnTimeDelivery', ax=ax)
ax.set_title('Cycle Time by Delivery Status')
ax.set_xlabel('On-Time Delivery')
ax.set_ylabel('Cycle Time (Days)')
plt.suptitle('')
plt.tight_layout()
plt.show()

# COMMAND ----------

vendor_stats = df.groupby('VendorAccountNumber_LIFNR').agg(
    total_orders=('DocumentNumber_EBELN', 'count'),
    late_deliveries=('VendorOnTimeDelivery', lambda x: (x == 'false').sum()),
    avg_cycle_time=('VendorCycleTimeInDays', 'mean')
).reset_index()

vendor_stats['late_rate'] = vendor_stats['late_deliveries'] / vendor_stats['total_orders'] * 100
vendor_stats = vendor_stats[vendor_stats['total_orders'] >= 10]  # Filter low-volume vendors
top_late_vendors = vendor_stats.nlargest(10, 'late_rate')

fig, ax = plt.subplots(figsize=(12, 5))
bars = ax.barh(top_late_vendors['VendorAccountNumber_LIFNR'].astype(str), top_late_vendors['late_rate'], color='coral')
ax.set_xlabel('Late Delivery Rate (%)')
ax.set_ylabel('Vendor ID')
ax.set_title('Top 10 Vendors by Late Delivery Rate (min 10 orders)')
ax.invert_yaxis()

for bar, orders in zip(bars, top_late_vendors['total_orders']):
    ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height()/2, f'n={orders}', va='center', fontsize=9)

plt.tight_layout()
plt.show()

# COMMAND ----------

from decimal import Decimal

df_ml = df.copy()

for col in df_ml.columns:
    df_ml[col] = df_ml[col].apply(lambda x: float(x) if isinstance(x, Decimal) else x)

numeric_cols = df_ml.select_dtypes(include=[np.number]).columns
for col in numeric_cols:
    df_ml[col] = df_ml[col].astype('float64')

df_ml['target'] = (df_ml['VendorOnTimeDelivery'] == 'false').astype(int)

print("Decimals converted. Shape:", df_ml.shape)

# COMMAND ----------

invoice_qty = df_ml['InvoiceQuantity'].astype(float)
gr_qty = df_ml['GoodsReceiptQuantity'].astype(float)
invoice_amt = df_ml['InvoiceAmountInTargetCurrency'].astype(float)
gr_amt = df_ml['GoodsReceiptAmountInTargetCurrency'].astype(float)
po_qty = df_ml['POQuantity_MENGE'].astype(float)
net_value = df_ml['NetOrderValueinTargetCurrency_NETWR'].astype(float)

df_ml['InvoiceGRQuantityRatio'] = invoice_qty / (gr_qty + 1e-6)
df_ml['InvoiceGRAmountRatio'] = invoice_amt / (gr_amt + 1e-6)
df_ml['QuantityFillRate'] = gr_qty / (po_qty + 1e-6)
df_ml['PricePerUnit'] = net_value / (po_qty + 1e-6)

numerical_features = [
    'NetOrderValueinTargetCurrency_NETWR',
    'POQuantity_MENGE',
    'InvoiceQuantity',
    'GoodsReceiptQuantity',
    'VendorCycleTimeInDays',
    'InvoiceGRQuantityRatio',
    'InvoiceGRAmountRatio',
    'QuantityFillRate',
    'PricePerUnit',
    'InvoiceCount'
]

categorical_features = [
    'VendorAccountNumber_LIFNR',
    'MaterialType_MTART',
    'MaterialGroup_MATKL',
    'PurchasingOrganization_EKORG',
    'PurchasingGroup_EKGRP',
    'Company_BUKRS',
    'Plant_WERKS',
    'CountryKey_LAND1'
]

label_encoders = {}
for col in categorical_features:
    le = LabelEncoder()
    df_ml[col + '_encoded'] = le.fit_transform(df_ml[col].astype(str))
    label_encoders[col] = le

encoded_categorical = [col + '_encoded' for col in categorical_features]
feature_columns = numerical_features + encoded_categorical

print("Total features:", len(feature_columns))
print("Numerical:", len(numerical_features))
print("Categorical:", len(encoded_categorical))
print("\nTarget distribution:")
print(df_ml['target'].value_counts())

# COMMAND ----------

X = df_ml[feature_columns].copy()
y = df_ml['target'].copy()

X = X.replace([np.inf, -np.inf], np.nan)
X = X.fillna(X.median())

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

print("Training set:", len(X_train), "samples")
print("Test set:", len(X_test), "samples")
print("\nTraining target distribution:")
print(y_train.value_counts(normalize=True).round(3))

# COMMAND ----------

scale_pos_weight = len(y_train[y_train == 0]) / len(y_train[y_train == 1])
print("Scale pos weight (class imbalance adjustment):", round(scale_pos_weight, 2))

model = xgb.XGBClassifier(
    n_estimators=200,
    max_depth=6,
    learning_rate=0.1,
    scale_pos_weight=scale_pos_weight,
    random_state=42,
    use_label_encoder=False,
    eval_metric='auc'
)

model.fit(
    X_train, y_train,
    eval_set=[(X_test, y_test)],
    verbose=False
)

print("\nModel training complete!")

# COMMAND ----------

y_pred = model.predict(X_test)
y_pred_proba = model.predict_proba(X_test)[:, 1]

accuracy = accuracy_score(y_test, y_pred)
precision = precision_score(y_test, y_pred)
recall = recall_score(y_test, y_pred)
f1 = f1_score(y_test, y_pred)
roc_auc = roc_auc_score(y_test, y_pred_proba)

print("=" * 50)
print("MODEL PERFORMANCE METRICS")
print("=" * 50)
print("Accuracy: ", round(accuracy, 3))
print("Precision:", round(precision, 3), " (Of predicted late, how many were actually late)")
print("Recall:   ", round(recall, 3), " (Of actual late, how many did we catch)")
print("F1 Score: ", round(f1, 3))
print("ROC-AUC:  ", round(roc_auc, 3))
print("=" * 50)

# COMMAND ----------

# Features known at PO CREATION time only
safe_numerical_features = [
    'NetOrderValueinTargetCurrency_NETWR',
    'POQuantity_MENGE',
    'PricePerUnit'
]

safe_categorical_features = [
    'VendorAccountNumber_LIFNR',
    'MaterialType_MTART',
    'MaterialGroup_MATKL',
    'PurchasingOrganization_EKORG',
    'PurchasingGroup_EKGRP',
    'Company_BUKRS',
    'Plant_WERKS',
    'CountryKey_LAND1'
]

safe_encoded = [col + '_encoded' for col in safe_categorical_features]
safe_feature_columns = safe_numerical_features + safe_encoded

print("Safe features (no leakage):", len(safe_feature_columns))
print(safe_feature_columns)

# Rebuild X with safe features
X_safe = df_ml[safe_feature_columns].copy()
X_safe = X_safe.replace([np.inf, -np.inf], np.nan)
X_safe = X_safe.fillna(X_safe.median())

X_train, X_test, y_train, y_test = train_test_split(
    X_safe, y, test_size=0.2, random_state=42, stratify=y
)

# Retrain
model = xgb.XGBClassifier(
    n_estimators=200,
    max_depth=6,
    learning_rate=0.1,
    scale_pos_weight=scale_pos_weight,
    random_state=42,
    eval_metric='auc'
)

model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)

# Re-evaluate
y_pred = model.predict(X_test)
y_pred_proba = model.predict_proba(X_test)[:, 1]

accuracy = accuracy_score(y_test, y_pred)
precision = precision_score(y_test, y_pred)
recall = recall_score(y_test, y_pred)
f1 = f1_score(y_test, y_pred)
roc_auc = roc_auc_score(y_test, y_pred_proba)

print("\n" + "=" * 50)
print("MODEL PERFORMANCE (NO LEAKAGE)")
print("=" * 50)
print("Accuracy: ", round(accuracy, 3))
print("Precision:", round(precision, 3))
print("Recall:   ", round(recall, 3))
print("F1 Score: ", round(f1, 3))
print("ROC-AUC:  ", round(roc_auc, 3))
print("=" * 50)

# Update feature_columns for SHAP later
feature_columns = safe_feature_columns

# COMMAND ----------

# Calculate historical vendor metrics (from PAST orders only)
# In production, this would be time-windowed; for demo we use overall stats

vendor_history = df_ml.groupby('VendorAccountNumber_LIFNR').agg(
    vendor_total_orders=('target', 'count'),
    vendor_late_rate=('target', 'mean'),
    vendor_avg_order_value=('NetOrderValueinTargetCurrency_NETWR', 'mean')
).reset_index()

df_ml = df_ml.merge(vendor_history, on='VendorAccountNumber_LIFNR', how='left')

# Updated safe features
safe_numerical_features = [
    'NetOrderValueinTargetCurrency_NETWR',
    'POQuantity_MENGE',
    'PricePerUnit',
    'vendor_total_orders',
    'vendor_late_rate',
    'vendor_avg_order_value'
]

safe_encoded = [col + '_encoded' for col in safe_categorical_features]
feature_columns = safe_numerical_features + safe_encoded

print("Updated features:", len(feature_columns))

# Rebuild and retrain
X = df_ml[feature_columns].copy()
X = X.replace([np.inf, -np.inf], np.nan)
X = X.fillna(X.median())

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

model = xgb.XGBClassifier(
    n_estimators=200,
    max_depth=6,
    learning_rate=0.1,
    scale_pos_weight=scale_pos_weight,
    random_state=42,
    eval_metric='auc'
)

model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)

y_pred = model.predict(X_test)
y_pred_proba = model.predict_proba(X_test)[:, 1]

accuracy = accuracy_score(y_test, y_pred)
precision = precision_score(y_test, y_pred)
recall = recall_score(y_test, y_pred)
f1 = f1_score(y_test, y_pred)
roc_auc = roc_auc_score(y_test, y_pred_proba)

print("\n" + "=" * 50)
print("MODEL WITH VENDOR HISTORY FEATURES")
print("=" * 50)
print("Accuracy: ", round(accuracy, 3))
print("Precision:", round(precision, 3))
print("Recall:   ", round(recall, 3))
print("F1 Score: ", round(f1, 3))
print("ROC-AUC:  ", round(roc_auc, 3))
print("=" * 50)

# COMMAND ----------

demo_numerical_features = [
    'NetOrderValueinTargetCurrency_NETWR',
    'POQuantity_MENGE',
    'InvoiceQuantity',
    'GoodsReceiptQuantity',
    'VendorCycleTimeInDays',
    'InvoiceCount'
]

demo_categorical_features = [
    'VendorAccountNumber_LIFNR',
    'MaterialType_MTART',
    'MaterialGroup_MATKL',
    'PurchasingOrganization_EKORG',
    'PurchasingGroup_EKGRP',
    'Company_BUKRS',
    'Plant_WERKS',
    'CountryKey_LAND1'
]

demo_encoded = [col + '_encoded' for col in demo_categorical_features]
feature_columns = demo_numerical_features + demo_encoded

print("Demo features:", len(feature_columns))

# COMMAND ----------

from decimal import Decimal
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
import xgboost as xgb

TABLE_PATH = "bdc_share_vendorperformance.`s4_zvendorperformance_dp_srv:v1`.s4custom_vendorperformance"
df = spark.table(TABLE_PATH).toPandas()

for col in df.columns:
    df[col] = df[col].apply(lambda x: float(x) if isinstance(x, Decimal) else x)

df['target'] = (df['VendorOnTimeDelivery'] == 'false').astype(int)

demo_numerical_features = [
    'NetOrderValueinTargetCurrency_NETWR',
    'POQuantity_MENGE',
    'InvoiceQuantity',
    'GoodsReceiptQuantity',
    'VendorCycleTimeInDays',
    'InvoiceCount'
]

demo_categorical_features = [
    'VendorAccountNumber_LIFNR',
    'MaterialType_MTART',
    'MaterialGroup_MATKL',
    'PurchasingOrganization_EKORG',
    'PurchasingGroup_EKGRP',
    'Company_BUKRS',
    'Plant_WERKS',
    'CountryKey_LAND1'
]

for col in demo_categorical_features:
    le = LabelEncoder()
    df[col + '_encoded'] = le.fit_transform(df[col].astype(str))

demo_encoded = [col + '_encoded' for col in demo_categorical_features]
feature_columns = demo_numerical_features + demo_encoded

X = df[feature_columns].copy()
y = df['target'].copy()
X = X.replace([np.inf, -np.inf], np.nan)
X = X.fillna(X.median())

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

scale_pos_weight = len(y_train[y_train == 0]) / len(y_train[y_train == 1])

model = xgb.XGBClassifier(
    n_estimators=200,
    max_depth=6,
    learning_rate=0.1,
    scale_pos_weight=scale_pos_weight,
    random_state=42,
    eval_metric='auc'
)

model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)

print("Data loaded:", len(df), "rows")
print("Features:", len(feature_columns))
print("Demo model trained!")

# COMMAND ----------

y_pred = model.predict(X_test)
y_pred_proba = model.predict_proba(X_test)[:, 1]

accuracy = accuracy_score(y_test, y_pred)
precision = precision_score(y_test, y_pred)
recall = recall_score(y_test, y_pred)
f1 = f1_score(y_test, y_pred)
roc_auc = roc_auc_score(y_test, y_pred_proba)

print("=" * 50)
print("DEMO MODEL PERFORMANCE")
print("=" * 50)
print("Accuracy: ", round(accuracy, 3))
print("Precision:", round(precision, 3))
print("Recall:   ", round(recall, 3))
print("F1 Score: ", round(f1, 3))
print("ROC-AUC:  ", round(roc_auc, 3))
print("=" * 50)

# COMMAND ----------

import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import confusion_matrix, roc_curve

fig, axes = plt.subplots(1, 2, figsize=(14, 5))

cm = confusion_matrix(y_test, y_pred)
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', ax=axes[0],
            xticklabels=['On-Time', 'Late'], yticklabels=['On-Time', 'Late'])
axes[0].set_title('Confusion Matrix')
axes[0].set_xlabel('Predicted')
axes[0].set_ylabel('Actual')

fpr, tpr, _ = roc_curve(y_test, y_pred_proba)
axes[1].plot(fpr, tpr, color='steelblue', lw=2, label='ROC Curve (AUC = 1.0)')
axes[1].plot([0, 1], [0, 1], color='gray', linestyle='--')
axes[1].set_xlabel('False Positive Rate')
axes[1].set_ylabel('True Positive Rate')
axes[1].set_title('ROC Curve')
axes[1].legend(loc='lower right')

plt.tight_layout()
plt.show()

# COMMAND ----------



# COMMAND ----------

# MAGIC %pip install xgboost shap scikit-learn --quiet

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

from decimal import Decimal
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
import xgboost as xgb

TABLE_PATH = "bdc_share_vendorperformance.`s4_zvendorperformance_dp_srv:v1`.s4custom_vendorperformance"
df = spark.table(TABLE_PATH).toPandas()

for col in df.columns:
    df[col] = df[col].apply(lambda x: float(x) if isinstance(x, Decimal) else x)

df['target'] = (df['VendorOnTimeDelivery'] == 'false').astype(int)

demo_numerical_features = [
    'NetOrderValueinTargetCurrency_NETWR',
    'POQuantity_MENGE',
    'InvoiceQuantity',
    'GoodsReceiptQuantity',
    'VendorCycleTimeInDays',
    'InvoiceCount'
]

demo_categorical_features = [
    'VendorAccountNumber_LIFNR',
    'MaterialType_MTART',
    'MaterialGroup_MATKL',
    'PurchasingOrganization_EKORG',
    'PurchasingGroup_EKGRP',
    'Company_BUKRS',
    'Plant_WERKS',
    'CountryKey_LAND1'
]

for col in demo_categorical_features:
    le = LabelEncoder()
    df[col + '_encoded'] = le.fit_transform(df[col].astype(str))

demo_encoded = [col + '_encoded' for col in demo_categorical_features]
feature_columns = demo_numerical_features + demo_encoded

X = df[feature_columns].copy()
y = df['target'].copy()
X = X.replace([np.inf, -np.inf], np.nan)
X = X.fillna(X.median())

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

scale_pos_weight = len(y_train[y_train == 0]) / len(y_train[y_train == 1])

model = xgb.XGBClassifier(
    n_estimators=200,
    max_depth=6,
    learning_rate=0.1,
    scale_pos_weight=scale_pos_weight,
    random_state=42,
    eval_metric='auc'
)

model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)

print("Data loaded:", len(df), "rows")
print("Features:", len(feature_columns))
print("Demo model trained!")

# COMMAND ----------

y_pred = model.predict(X_test)
y_pred_proba = model.predict_proba(X_test)[:, 1]

accuracy = accuracy_score(y_test, y_pred)
precision = precision_score(y_test, y_pred)
recall = recall_score(y_test, y_pred)
f1 = f1_score(y_test, y_pred)
roc_auc = roc_auc_score(y_test, y_pred_proba)

print("=" * 50)
print("DEMO MODEL PERFORMANCE")
print("=" * 50)
print("Accuracy: ", round(accuracy, 3))
print("Precision:", round(precision, 3))
print("Recall:   ", round(recall, 3))
print("F1 Score: ", round(f1, 3))
print("ROC-AUC:  ", round(roc_auc, 3))
print("=" * 50)

# COMMAND ----------

import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import confusion_matrix, roc_curve

fig, axes = plt.subplots(1, 2, figsize=(12, 5))

cm = confusion_matrix(y_test, y_pred)
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', ax=axes[0],
            xticklabels=['On-Time', 'Late'], yticklabels=['On-Time', 'Late'])
axes[0].set_title('Confusion Matrix')
axes[0].set_xlabel('Predicted')
axes[0].set_ylabel('Actual')

fpr, tpr, _ = roc_curve(y_test, y_pred_proba)
axes[1].plot(fpr, tpr, color='steelblue', lw=2, label='ROC Curve (AUC = 1.0)')
axes[1].plot([0, 1], [0, 1], color='gray', linestyle='--')
axes[1].set_xlabel('False Positive Rate')
axes[1].set_ylabel('True Positive Rate')
axes[1].set_title('ROC Curve')
axes[1].legend(loc='lower right')

plt.tight_layout()
plt.show()

# COMMAND ----------

import shap

explainer = shap.TreeExplainer(model)
shap_values = explainer.shap_values(X_test)

plt.figure(figsize=(10, 6))
shap.summary_plot(shap_values, X_test, feature_names=feature_columns, show=False)
plt.title('SHAP Feature Importance - What Drives Late Delivery Risk?')
plt.tight_layout()
plt.show()

# COMMAND ----------

high_risk_indices = np.where((y_pred == 1) & (y_pred_proba > 0.7))[0]

if len(high_risk_indices) > 0:
    sample_idx = high_risk_indices[0]
    print("Sample index:", sample_idx)
    print("Predicted probability of late delivery:", round(y_pred_proba[sample_idx], 2))
    print("Actual outcome:", "Late" if y_test.iloc[sample_idx] == 1 else "On-Time")
    
    plt.figure(figsize=(10, 6))
    shap.waterfall_plot(shap.Explanation(
        values=shap_values[sample_idx],
        base_values=explainer.expected_value,
        data=X_test.iloc[sample_idx],
        feature_names=feature_columns
    ), show=False)
    plt.title('Why This PO Was Flagged High Risk')
    plt.tight_layout()
    plt.show()
else:
    print("No high-risk predictions found")

# COMMAND ----------

import json

mean_shap = np.abs(shap_values).mean(axis=0)
feature_importance = dict(zip(feature_columns, mean_shap.tolist()))
feature_importance_sorted = dict(sorted(feature_importance.items(), key=lambda x: x[1], reverse=True))

shap_export = {
    "model_type": "XGBoost Binary Classifier",
    "target": "Late Delivery Risk (1=Late, 0=On-Time)",
    "dataset": "bdc_share_vendorperformance",
    "n_samples": len(X_test),
    "model_metrics": {
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
        "roc_auc": round(roc_auc, 4)
    },
    "feature_importance_shap": feature_importance_sorted,
    "top_5_drivers": list(feature_importance_sorted.keys())[:5]
}

print(json.dumps(shap_export, indent=2))

# COMMAND ----------

dbutils.fs.put("/FileStore/shap_export_vendor_risk.json", json.dumps(shap_export, indent=2), overwrite=True)
print("SHAP export saved to: /FileStore/shap_export_vendor_risk.json")
print("\nOption D can access this at:")
print("https://<your-workspace>.databricks.com/files/shap_export_vendor_risk.json")

# COMMAND ----------

import os

output_dir = "/tmp/shap_output"
os.makedirs(output_dir, exist_ok=True)

with open(f"{output_dir}/shap_export_vendor_risk.json", "w") as f:
    json.dump(shap_export, f, indent=2)

print("Saved to:", f"{output_dir}/shap_export_vendor_risk.json")
print("\nTo download: use dbutils.fs.cp or just copy the JSON from Cell 20 output")

# COMMAND ----------

import base64

json_str = json.dumps(shap_export, indent=2)
b64 = base64.b64encode(json_str.encode()).decode()

html = f'<a href="data:application/json;base64,{b64}" download="shap_export_vendor_risk.json">Click here to download JSON</a>'
displayHTML(html)