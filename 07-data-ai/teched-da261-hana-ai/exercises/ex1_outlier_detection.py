"""
DA261 Exercise 1: Outlier Detection using PAL Isolation Forest
TechEd 2025 - SAP HANA Cloud AI Capabilities
Author: Srinivasa Dasari
"""

import pandas as pd
import numpy as np
from hana_ml import dataframe
from hana_ml.dataframe import create_dataframe_from_pandas
from hana_ml.algorithms.pal.preprocessing import IsolationForest

# =============================================================================
# 1. CONNECT TO HANA CLOUD
# =============================================================================
def connect_to_hana():
    """Connect to HANA Cloud using PAL_USER"""
    conn = dataframe.ConnectionContext(
        address='04aefaf5-8823-4aef-b849-6e2bdfb3bd7b.hna1.prod-us10.hanacloud.ondemand.com',
        port=443,
        user='PAL_USER',
        password='Initial123',
        encrypt=True,
        sslValidateCertificate=False
    )
    print(f"Connected: {conn.connection.isconnected()}")
    return conn

# =============================================================================
# 2. GENERATE SYNTHETIC ACDOCA DATA
# =============================================================================
def generate_acdoca_data(n_rows=500):
    """Generate synthetic ACDOCA financial transaction data"""
    np.random.seed(42)
    
    company_codes = ['CC01', 'CC02', 'CC03', 'CC04', 'CC05']
    profit_centers = ['PC001', 'PC002', 'PC003', 'PC004', 'PC005', 
                      'PC006', 'PC007', 'PC008', 'PC009', 'PC010']
    account_types = ['P+L Statement', 'Balance Sheet Asset', 
                     'Balance Sheet Liability', 'Equity']
    debit_credit = ['S', 'H']  # S=Debit, H=Credit
    
    data = {
        'Document Number': [f'DOC{str(i).zfill(7)}' for i in range(1, n_rows + 1)],
        'Company Code': np.random.choice(company_codes, n_rows),
        'Fiscal Year': np.random.choice([2023, 2024, 2025], n_rows),
        'Fiscal Period': np.random.randint(1, 13, n_rows),
        'Profit Center': np.random.choice(profit_centers, n_rows),
        'Cost Center': [f'COST{str(np.random.randint(100, 999))}' for _ in range(n_rows)],
        'G/L Account': [f'{np.random.randint(100000, 999999)}' for _ in range(n_rows)],
        'Financial Account Type': np.random.choice(account_types, n_rows, p=[0.5, 0.25, 0.2, 0.05]),
        'Debit/Credit': np.random.choice(debit_credit, n_rows),
        'Amount (Transaction)': np.random.uniform(-10000, 20000, n_rows).round(2),
        'Transaction Currency': np.random.choice(['USD', 'EUR', 'GBP'], n_rows),
        'Amount (USD)': np.random.uniform(-10000, 20000, n_rows).round(2),
        'Posting Date': pd.date_range(start='2024-01-01', periods=n_rows, freq='h').strftime('%Y-%m-%d').tolist()
    }
    
    return pd.DataFrame(data)

# =============================================================================
# 3. UPLOAD DATA TO HANA
# =============================================================================
def upload_to_hana(conn, df, table_name='ACDOCA', schema='DBADMIN'):
    """Upload DataFrame to HANA Cloud"""
    hdf = create_dataframe_from_pandas(
        conn,
        df,
        table_name=table_name,
        schema=schema,
        force=True
    )
    print(f"Uploaded {hdf.count()} rows to {schema}.{table_name}")
    return hdf

# =============================================================================
# 4. PREPARE DATA FOR PAL (ENCODE CATEGORICALS)
# =============================================================================
def prepare_for_pal(hdf, company_code='CC01', profit_center='PC002'):
    """Filter data and encode categorical columns for PAL"""
    
    # Filter slice
    hdf_slice = hdf.filter(
        f"\"Company Code\" = '{company_code}' AND \"Profit Center\" = '{profit_center}'"
    )
    print(f"Filtered to {hdf_slice.count()} rows")
    
    # Encode categorical columns using SQL CASE statements
    hdf_encoded = hdf_slice.select(
        '*',
        ('CASE WHEN "Debit/Credit" = \'S\' THEN 1 ELSE 0 END', 'DC_CODE'),
        ('''CASE 
            WHEN "Financial Account Type" = 'P+L Statement' THEN 1 
            WHEN "Financial Account Type" = 'Balance Sheet Asset' THEN 2
            WHEN "Financial Account Type" = 'Balance Sheet Liability' THEN 3
            ELSE 4 
        END''', 'FAT_CODE')
    )
    
    return hdf_encoded

# =============================================================================
# 5. TRAIN ISOLATION FOREST
# =============================================================================
def train_isolation_forest(hdf_encoded):
    """Train PAL Isolation Forest for anomaly detection"""
    
    # Add ID column for prediction
    hdf_with_id = hdf_encoded.add_id('ID')
    
    # Create and train model
    isof = IsolationForest(
        n_estimators=100,
        max_samples=hdf_encoded.count(),
        bootstrap=False
    )
    
    features = ['DC_CODE', 'FAT_CODE', 'Amount (USD)', 'Amount (Transaction)']
    
    print("Training Isolation Forest...")
    isof.fit(data=hdf_with_id, features=features)
    print("Training complete!")
    
    return isof, hdf_with_id, features

# =============================================================================
# 6. DETECT OUTLIERS
# =============================================================================
def detect_outliers(isof, hdf_with_id, features, contamination=0.05):
    """Predict outliers using trained model"""
    
    results = isof.predict(
        data=hdf_with_id,
        key='ID',
        features=features,
        contamination=contamination
    )
    
    # Separate outliers and normal
    outliers = results.filter('LABEL = -1')
    normal = results.filter('LABEL = 1')
    
    print(f"\nResults:")
    print(f"  Total: {results.count()}")
    print(f"  Outliers: {outliers.count()} ({outliers.count()/results.count()*100:.1f}%)")
    print(f"  Normal: {normal.count()}")
    
    return results, outliers, normal

# =============================================================================
# 7. ANALYZE OUTLIERS
# =============================================================================
def analyze_outliers(hdf_with_id, outliers):
    """Join outlier labels back to original data for analysis"""
    
    outlier_ids = outliers.select('ID', 'LABEL', 'SCORE')
    
    # Join to get full outlier records
    outlier_details = hdf_with_id.join(
        outlier_ids,
        condition='ID',
        how='inner'
    )
    
    print("\nOutlier Details:")
    print(outlier_details.select(
        'Document Number', 'Amount (USD)', 'Financial Account Type', 
        'Debit/Credit', 'SCORE'
    ).collect())
    
    return outlier_details

# =============================================================================
# MAIN EXECUTION
# =============================================================================
if __name__ == "__main__":
    # Connect
    conn = connect_to_hana()
    
    # Generate and upload data
    acdoca_df = generate_acdoca_data(500)
    print(f"Generated {len(acdoca_df)} synthetic ACDOCA transactions")
    
    hdf_acdoca = upload_to_hana(conn, acdoca_df)
    
    # Prepare for PAL
    hdf_encoded = prepare_for_pal(hdf_acdoca)
    
    # Train model
    isof, hdf_with_id, features = train_isolation_forest(hdf_encoded)
    
    # Detect outliers
    results, outliers, normal = detect_outliers(isof, hdf_with_id, features)
    
    # Analyze
    if outliers.count() > 0:
        outlier_details = analyze_outliers(hdf_with_id, outliers)
    
    print("\n✅ Exercise 1 Complete!")
