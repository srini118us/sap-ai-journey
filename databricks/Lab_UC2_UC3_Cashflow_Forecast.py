# Databricks notebook source
# Cell 1: Read WCI CashFlow data from BDC Delta Share
df_raw = spark.table("bdc_share_cash_flow.cashflow.cashflow")

print(f"Total rows: {df_raw.count()}")
print(f"Company Codes: {[r[0] for r in df_raw.select('CompanyCode').distinct().collect()]}")
print(f"Date range: {df_raw.agg({'PostingDate': 'min'}).collect()[0][0]} to {df_raw.agg({'PostingDate': 'max'}).collect()[0][0]}")

df_raw.select("CompanyCode", "PostingDate", "TransactionCurrency", 
              "AmountInTransactionCurrency").show(10)

# COMMAND ----------

# Cell 2: Aggregate to monthly time series per CompanyCode
from pyspark.sql import functions as F

df_monthly = (
    df_raw
    .filter(F.col("AmountInTransactionCurrency").isNotNull())
    .withColumn("YearMonth", F.date_trunc("month", F.col("PostingDate")))
    .groupBy("CompanyCode", "TransactionCurrency", "YearMonth")
    .agg(
        F.sum("AmountInTransactionCurrency").alias("TotalAmount"),
        F.sum("AmountInCompanyCodeCurrency").alias("TotalAmountCC"),
        F.count("CashFlowID").alias("TransactionCount")
    )
    .orderBy("CompanyCode", "YearMonth")
)

print(f"Monthly aggregated rows: {df_monthly.count()}")
print(f"Months available for CompanyCode 1710:")
df_monthly.filter(F.col("CompanyCode") == "1710").select(
    "YearMonth", "TotalAmount", "TransactionCount"
).orderBy("YearMonth").show(24)

# COMMAND ----------

# Cell 3: Install AutoTS
%pip install autots --quiet
dbutils.library.restartPython()

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

# Cell 4: Rebuild data + Run AutoTS (run this after restartPython)
import pandas as pd
import warnings
warnings.filterwarnings('ignore')
from autots import AutoTS
from pyspark.sql import functions as F

# Step 1: Rebuild df_raw
df_raw = spark.table("bdc_share_cash_flow.cashflow.cashflow")

# Step 2: Rebuild df_monthly
df_monthly = (
    df_raw
    .filter(F.col("AmountInTransactionCurrency").isNotNull())
    .withColumn("YearMonth", F.date_trunc("month", F.col("PostingDate")))
    .groupBy("CompanyCode", "TransactionCurrency", "YearMonth")
    .agg(
        F.sum("AmountInTransactionCurrency").alias("TotalAmount"),
        F.sum("AmountInCompanyCodeCurrency").alias("TotalAmountCC"),
        F.count("CashFlowID").alias("TransactionCount")
    )
    .orderBy("CompanyCode", "YearMonth")
)

# Step 3: Filter 1710 USD and convert to pandas
df_pd = df_monthly.filter(
    (df_monthly.CompanyCode == "1710") &
    (df_monthly.TransactionCurrency == "USD")
).toPandas()

df_pd["YearMonth"] = pd.to_datetime(df_pd["YearMonth"])
df_pd = df_pd.sort_values("YearMonth").reset_index(drop=True)
print(f"Rows for 1710 USD: {len(df_pd)}")
print(df_pd[["YearMonth","TotalAmount"]].tail(6).to_string())

# Step 4: Run AutoTS
model = AutoTS(
    forecast_length=6,
    frequency="MS",
    ensemble="simple",
    max_generations=3,
    num_validations=2,
    validation_method="backwards",
    model_list="superfast",
    verbose=1
)

model = model.fit(
    df_pd,
    date_col="YearMonth",
    value_col="TotalAmount",
    id_col=None
)

forecast = model.predict()
forecast_df = forecast.forecast.reset_index()
forecast_df.columns = ["PostingDate", "ForecastedAmount"]
foreca

# COMMAND ----------

# Cell 5: Generate forecast from trained model
import pandas as pd
from datetime import datetime

forecast = model.predict()
forecast_df = forecast.forecast.reset_index()
forecast_df.columns = ["PostingDate", "ForecastedAmount"]
forecast_df["PostingDate"] = pd.to_datetime(forecast_df["PostingDate"])

print(f"Best model selected by AutoTS: {model.best_model_name}")
print(f"\n6-Month Cashflow Forecast for CompanyCode 1710 (USD):")
print(forecast_df.to_string(index=False))

# COMMAND ----------

import pandas as pd
from datetime import datetime

actuals = df_pd[["YearMonth", "TotalAmount", "TransactionCurrency"]].tail(12).copy()
actuals["RecordType"] = "ACTUAL"
actuals["CompanyCode"] = "1710"
actuals.rename(columns={"YearMonth": "PostingDate", "TotalAmount": "AmountInTransactionCurrency"}, inplace=True)

forecast_rows = forecast_df.copy()
forecast_rows["RecordType"] = "FORECAST"
forecast_rows["CompanyCode"] = "1710"
forecast_rows["TransactionCurrency"] = "USD"
forecast_rows.rename(columns={"ForecastedAmount": "AmountInTransactionCurrency"}, inplace=True)

combined = pd.concat([actuals, forecast_rows], ignore_index=True)
combined["ForecastGeneratedAt"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
combined["ModelName"] = model.best_model_name
combined["ForecastHorizonMonths"] = 6
combined["CreatedBy"] = "GE283914"
combined["PostingDate"] = pd.to_datetime(combined["PostingDate"]).dt.strftime("%Y-%m-%d")
combined["AmountInTransactionCurrency"] = combined["AmountInTransactionCurrency"].astype(float)
combined["ForecastHorizonMonths"] = combined["ForecastHorizonMonths"].astype(int)
combined["TransactionCurrency"] = combined["TransactionCurrency"].astype(str)
combined["RecordType"] = combined["RecordType"].astype(str)
combined["CompanyCode"] = combined["CompanyCode"].astype(str)
combined["ModelName"] = combined["ModelName"].astype(str)
combined["CreatedBy"] = combined["CreatedBy"].astype(str)
combined["ForecastGeneratedAt"] = combined["ForecastGeneratedAt"].astype(str)

spark_df = spark.createDataFrame(combined)
spark.sql("CREATE SCHEMA IF NOT EXISTS workspace.srini_forecasts")
spark_df.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable("workspace.srini_forecasts.cashflow_forecast_1710")

result = spark.table("workspace.srini_forecasts.cashflow_forecast_1710")
print("Published: workspace.srini_forecasts.cashflow_forecast_1710")
print("Total rows:", result.count())
result.order

# COMMAND ----------

# Find writable catalogs
catalogs = spark.sql("SHOW CATALOGS").collect()
for c in catalogs:
    print(c[0])

# COMMAND ----------

# Check what schemas exist under workspace that you can access
spark.sql("SHOW SCHEMAS IN workspace").show()

# COMMAND ----------

# Write to DBFS — always writable in Databricks trial
output_path = "/FileStore/srini_forecasts/cashflow_forecast_1710"

spark_df.write.format("delta").mode("overwrite").save(output_path)

# Read back to verify
result = spark.read.format("delta").load(output_path)
print("Published to DBFS:", output_path)
print("Total rows:", result.count())
result.orderBy("PostingDate").show(20)

# COMMAND ----------

# Register as temp view — queryable in SQL Editor this session
spark_df.createOrReplaceTempView("srini_cashflow_forecast_1710")

# Verify it works
result = spark.sql("""
    SELECT PostingDate, 
           ROUND(AmountInTransactionCurrency/1000000, 2) as Amount_USD_Millions,
           RecordType,
           ModelName
    FROM srini_cashflow_forecast_1710
    ORDER BY PostingDate
""")

print("Cashflow Forecast registered as temp view: srini_cashflow_forecast_1710")
print("Queryable in SQL Editor for this session")
result.show(20)

# Also print forecast summary
print("\n--- FORECAST SUMMARY ---")
spark.sql("""
    SELECT RecordType, COUNT(*) as Rows,
           ROUND(SUM(AmountInTransactionCurrency)/1000000,2) as Total_USD_Millions
    FROM srini_cashflow_forecast_1710
    GROUP BY RecordType
""").show()

# COMMAND ----------

# Show only forecast rows
spark.sql("""
    SELECT PostingDate,
           ROUND(AmountInTransactionCurrency/1000000, 2) as Amount_USD_Millions,
           RecordType, ModelName, ForecastGeneratedAt
    FROM srini_cashflow_forecast_1710
    WHERE RecordType = 'FORECAST'
    ORDER BY PostingDate
""").show()

# COMMAND ----------

df = spark.table("bdc_share_vendorperformance.`s4_zvendorperformance_dp_srv:v1`.s4custom_vendorperformance")
print(df.columns)

# COMMAND ----------

df = spark.table("bdc_share_vendorperformance.`s4_zvendorperformance_dp_srv:v1`.s4custom_vendorperformance")

print(f"Total rows: {df.count()}")
print(f"\nTarget distribution:")
df.groupBy("VendorOnTimeDelivery").count().show()

print(f"\nPastDueOrOpenItems distribution:")
df.groupBy("PastDueOrOpenItems").count().show()

print(f"\nVendorCycleTimeInDays stats:")
df.select("VendorCycleTimeInDays").summary().show()