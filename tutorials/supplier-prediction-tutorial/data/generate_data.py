"""
Synthetic vendor delivery data generator for supplier on-time prediction.

Generates realistic procurement records based on domain knowledge of
how supplier delivery patterns actually work in enterprise procurement.

The data has deliberate patterns the XGBoost model can learn:
- Historical on-time rate is the strongest signal
- Long lead times correlate with delays
- Friday deliveries fail more often (real procurement pattern)
- High concurrent POs strain vendor capacity
- Quarter-end and peak season cause delays
- Country/region affects reliability
- Material complexity affects variance

Plus random noise so the model has to actually learn patterns.

Output: CSV file ready for upload to S3 for AI Core training.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# Reproducibility
RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)

# Configuration
NUM_RECORDS = 10000
NUM_VENDORS = 100
OUTPUT_PATH = "training_data.csv"


def generate_vendor_master():
    """
    Create 100 vendors with stable attributes (category, country, history).
    Each PO record will reference one of these vendors.
    """
    vendor_categories = ["RAW", "PACK", "FINISH", "SERVICE"]
    countries = ["US", "DE", "CN", "IN", "MX"]
    
    # Country reliability priors (real procurement observation)
    country_reliability = {
        "US": 0.85,
        "DE": 0.88,
        "MX": 0.78,
        "CN": 0.72,
        "IN": 0.70,
    }
    
    vendors = []
    for i in range(NUM_VENDORS):
        country = np.random.choice(countries, p=[0.30, 0.20, 0.25, 0.15, 0.10])
        category = np.random.choice(vendor_categories, p=[0.35, 0.25, 0.30, 0.10])
        
        # Historical on-time rate centered around country prior with noise
        base_rate = country_reliability[country]
        historical_ontime = np.clip(np.random.normal(base_rate, 0.10), 0.40, 0.98)
        
        # Lead time depends on category
        if category == "RAW":
            avg_lead = np.random.uniform(7, 14)
        elif category == "PACK":
            avg_lead = np.random.uniform(5, 10)
        elif category == "FINISH":
            avg_lead = np.random.uniform(14, 28)
        else:  # SERVICE
            avg_lead = np.random.uniform(3, 7)
        
        # Lead time variance (consistency of vendor)
        lead_variance = np.random.uniform(1.0, 5.0)
        
        # PO volume in last quarter
        po_count = np.random.poisson(15)
        
        vendors.append({
            "vendor_id": f"V{i+1:04d}",
            "vendor_category": category,
            "vendor_country": country,
            "historical_ontime_rate": round(historical_ontime, 3),
            "avg_lead_time_days": round(avg_lead, 1),
            "lead_time_variance": round(lead_variance, 2),
            "po_count_last_quarter": po_count,
        })
    
    return pd.DataFrame(vendors)


def generate_po_records(vendors_df):
    """
    Generate PO records, each referencing a vendor.
    Add transactional features and the on-time label.
    """
    records = []
    
    # Generate timestamps across last year
    start_date = datetime(2025, 5, 1)
    
    for record_id in range(NUM_RECORDS):
        # Pick a vendor (weighted by volume - active vendors get more POs)
        vendor_idx = np.random.choice(len(vendors_df))
        vendor = vendors_df.iloc[vendor_idx]
        
        # PO creation date
        po_date = start_date + timedelta(days=np.random.randint(0, 365))
        
        # Expected delivery date = PO date + lead time + noise
        expected_lead = vendor["avg_lead_time_days"] + np.random.normal(0, 2)
        expected_lead = max(1, expected_lead)
        delivery_date = po_date + timedelta(days=expected_lead)
        
        # PO amount (lognormal distribution, realistic procurement range)
        po_amount = round(np.exp(np.random.normal(9.0, 1.2)), 2)  # 1k to 100k range mostly
        
        # Concurrent POs with this vendor
        concurrent_pos = np.random.poisson(5)
        
        # Material complexity (1=standard, 5=highly custom)
        if vendor["vendor_category"] == "FINISH":
            material_complexity = np.random.choice([3, 4, 5], p=[0.3, 0.4, 0.3])
        elif vendor["vendor_category"] == "SERVICE":
            material_complexity = np.random.choice([1, 2], p=[0.5, 0.5])
        else:
            material_complexity = np.random.choice([1, 2, 3, 4, 5], 
                                                    p=[0.25, 0.30, 0.25, 0.15, 0.05])
        
        # Calendar features
        delivery_day_of_week = delivery_date.weekday()  # 0=Mon, 6=Sun
        is_quarter_end = delivery_date.month in [3, 6, 9, 12] and delivery_date.day >= 20
        is_peak_season = delivery_date.month in [11, 12]
        
        # Build the on-time probability based on features
        # This is the "true" relationship the model needs to learn
        ontime_prob = vendor["historical_ontime_rate"]  # baseline
        
        # Lead time effect: longer = more variance = more risk
        if expected_lead > 21:
            ontime_prob -= 0.10
        elif expected_lead > 14:
            ontime_prob -= 0.05
        
        # Variance effect: inconsistent vendors get more late deliveries
        ontime_prob -= (vendor["lead_time_variance"] - 2.5) * 0.02
        
        # Day of week effect: Friday (4) deliveries fail more
        if delivery_day_of_week == 4:
            ontime_prob -= 0.08
        elif delivery_day_of_week == 0:  # Monday rebound
            ontime_prob -= 0.03
        
        # Concurrent PO load: vendor capacity strain
        if concurrent_pos > 10:
            ontime_prob -= 0.15
        elif concurrent_pos > 7:
            ontime_prob -= 0.08
        
        # Material complexity
        ontime_prob -= (material_complexity - 1) * 0.03
        
        # Calendar effects
        if is_quarter_end:
            ontime_prob -= 0.10
        if is_peak_season:
            ontime_prob -= 0.07
        
        # Add random noise (the model can't perfectly predict)
        ontime_prob += np.random.normal(0, 0.10)
        
        # Clamp to valid range
        ontime_prob = np.clip(ontime_prob, 0.05, 0.95)
        
        # Sample the actual label
        on_time = 1 if np.random.random() < ontime_prob else 0
        
        records.append({
            "po_id": f"PO{record_id+1:06d}",
            "vendor_id": vendor["vendor_id"],
            "vendor_category": vendor["vendor_category"],
            "vendor_country": vendor["vendor_country"],
            "historical_ontime_rate": vendor["historical_ontime_rate"],
            "avg_lead_time_days": vendor["avg_lead_time_days"],
            "lead_time_variance": vendor["lead_time_variance"],
            "po_count_last_quarter": vendor["po_count_last_quarter"],
            "po_amount": po_amount,
            "concurrent_pos": concurrent_pos,
            "material_complexity": material_complexity,
            "expected_lead_time_days": round(expected_lead, 1),
            "delivery_day_of_week": delivery_day_of_week,
            "is_quarter_end": int(is_quarter_end),
            "is_peak_season": int(is_peak_season),
            "on_time": on_time,
        })
    
    return pd.DataFrame(records)


def main():
    print(f"Generating synthetic supplier delivery data...")
    print(f"  Vendors: {NUM_VENDORS}")
    print(f"  PO records: {NUM_RECORDS}")
    print(f"  Random seed: {RANDOM_SEED}")
    
    print(f"\nStep 1: Generating vendor master ({NUM_VENDORS} vendors)...")
    vendors_df = generate_vendor_master()
    
    print(f"Step 2: Generating PO records ({NUM_RECORDS} records)...")
    records_df = generate_po_records(vendors_df)
    
    # Summary statistics
    ontime_pct = records_df["on_time"].mean() * 100
    print(f"\nSummary:")
    print(f"  Total records: {len(records_df)}")
    print(f"  On-time rate: {ontime_pct:.1f}%")
    print(f"  Late rate: {100 - ontime_pct:.1f}%")
    print(f"  Class balance: {ontime_pct:.0f}/{100-ontime_pct:.0f}")
    
    # Feature distribution check
    print(f"\nFeature distributions:")
    print(f"  Vendor countries: {records_df['vendor_country'].value_counts().to_dict()}")
    print(f"  Vendor categories: {records_df['vendor_category'].value_counts().to_dict()}")
    print(f"  Friday deliveries on-time rate: "
          f"{records_df[records_df['delivery_day_of_week']==4]['on_time'].mean()*100:.1f}%")
    print(f"  Non-Friday deliveries on-time rate: "
          f"{records_df[records_df['delivery_day_of_week']!=4]['on_time'].mean()*100:.1f}%")
    print(f"  High concurrent PO (>10) on-time rate: "
          f"{records_df[records_df['concurrent_pos']>10]['on_time'].mean()*100:.1f}%")
    print(f"  Low concurrent PO (<=5) on-time rate: "
          f"{records_df[records_df['concurrent_pos']<=5]['on_time'].mean()*100:.1f}%")
    
    # Save to CSV
    records_df.to_csv(OUTPUT_PATH, index=False)
    print(f"\nSaved to: {OUTPUT_PATH}")
    print(f"File size: {len(records_df)*150 // 1024} KB approx")


if __name__ == "__main__":
    main()
