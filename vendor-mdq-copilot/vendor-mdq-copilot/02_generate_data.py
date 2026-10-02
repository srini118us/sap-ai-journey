#!/usr/bin/env python3
"""
Vendor Master Data Quality Copilot: synthetic data generator
Produces 4 CSV files with intentional MDQ issues embedded for RAG demo.

Output files:
  vendors.csv        150 vendor master records
  transactions.csv   500 invoice postings
  quality_rules.csv  30 business rules
  quality_issues.csv 200 historical issues (some resolved)

Design:
  Deterministic (seed=42) for reproducibility.
  Realistic industry patterns: log-normal amounts, seasonal invoice spikes.
  Intentional MDQ defects: duplicates, missing tax IDs, blocked vendors
  with active transactions, round-number fraud signals, wrong categories.

Run:
  python 02_generate_data.py
"""

import csv
import random
from datetime import date, timedelta
from pathlib import Path

random.seed(42)

OUT = Path(__file__).parent / "data"
OUT.mkdir(exist_ok=True)

# ==========================================================
# Reference data
# ==========================================================
COUNTRIES = ['USA', 'DEU', 'FRA', 'GBR', 'IND', 'CHN', 'JPN', 'BRA', 'CAN', 'AUS']
CATEGORIES = ['IT_SERVICES', 'PROFESSIONAL', 'LOGISTICS', 'FACILITIES', 'MARKETING',
              'RAW_MATERIALS', 'MRO', 'CONSULTING', 'TELECOM', 'UTILITIES']
CURRENCIES = ['USD', 'EUR', 'GBP', 'INR', 'CNY', 'JPY', 'BRL', 'CAD', 'AUD']
PAYMENT_TERMS = ['NT30', 'NT45', 'NT60', 'NT90', '2P10', 'IMM']
STATUSES = ['ACTIVE', 'ACTIVE', 'ACTIVE', 'ACTIVE', 'BLOCKED', 'PENDING']

CITIES = {
    'USA': ['New York', 'Chicago', 'Houston', 'Los Angeles', 'Atlanta'],
    'DEU': ['Berlin', 'Munich', 'Frankfurt', 'Hamburg', 'Walldorf'],
    'FRA': ['Paris', 'Lyon', 'Marseille', 'Toulouse'],
    'GBR': ['London', 'Manchester', 'Birmingham'],
    'IND': ['Bengaluru', 'Mumbai', 'Hyderabad', 'Chennai', 'Pune'],
    'CHN': ['Shanghai', 'Beijing', 'Shenzhen'],
    'JPN': ['Tokyo', 'Osaka'],
    'BRA': ['Sao Paulo', 'Rio de Janeiro'],
    'CAN': ['Toronto', 'Vancouver'],
    'AUS': ['Sydney', 'Melbourne']
}

VENDOR_NAMES = [
    "Acme Global Services", "Contoso Manufacturing", "Fabrikam Industries",
    "Wingtip Toys", "Northwind Logistics", "Adventure Works",
    "Litware Corp", "Proseware Systems", "Tailspin Toys",
    "Wide World Importers", "Blue Yonder Airlines", "Woodgrove Bank Services",
    "Trey Research", "Alpine Ski House", "Consolidated Messenger",
    "Coho Winery", "Fourth Coffee", "Graphic Design Institute",
    "Humongous Insurance", "Lucerne Publishing", "Margie Travel",
    "Nod Publishers", "Northwind Traders", "Parnell Aerospace",
    "Relecloud Communications", "School of Fine Art", "Southridge Video",
    "The Phone Company", "Van Arsdel Ltd", "World Wide Cargo"
]

CITY_STREETS = [
    "Main Street", "Broadway", "Market Street", "Park Avenue", "Elm Road",
    "Industrial Park", "Tech Park", "Commerce Way", "Central Boulevard"
]

# ==========================================================
# 1. Generate VENDORS
# ==========================================================
vendors = []
vendor_ids_all = []

def make_vendor_id(i):
    return f"V{i:07d}"

def make_tax_id(country):
    if country == 'USA':
        return f"{random.randint(10,99)}-{random.randint(1000000,9999999)}"
    if country == 'DEU':
        return f"DE{random.randint(100000000,999999999)}"
    if country == 'IND':
        return f"{random.randint(10,99)}AAAAA{random.randint(1000,9999)}A1Z{random.randint(1,9)}"
    return f"{country}{random.randint(100000,999999)}"

def make_bank_account():
    return f"{random.randint(10000000,99999999)}"

def make_description(name, category, city):
    templates = [
        f"{name} provides {category.lower().replace('_',' ')} services from {city}",
        f"Global supplier of {category.lower().replace('_',' ')} headquartered in {city}",
        f"{category.replace('_',' ').title()} partner serving enterprise clients from {city} office",
        f"Preferred vendor for {category.lower().replace('_',' ')} solutions, {city} region"
    ]
    return random.choice(templates)

# Generate 130 clean vendors first
for i in range(1, 131):
    vid = make_vendor_id(i)
    country = random.choice(COUNTRIES)
    city = random.choice(CITIES[country])
    name = f"{random.choice(VENDOR_NAMES)} {random.choice(['LLC','GmbH','Inc','SA','Pvt Ltd','Co'])}"
    category = random.choice(CATEGORIES)
    created = date(2020, 1, 1) + timedelta(days=random.randint(0, 2000))
    modified = created + timedelta(days=random.randint(0, 500))
    if modified > date(2026, 9, 1):
        modified = date(2026, 9, 1)
    vendors.append({
        'VENDOR_ID': vid,
        'VENDOR_NAME': name,
        'ADDRESS_LINE1': f"{random.randint(1,9999)} {random.choice(CITY_STREETS)}",
        'CITY': city,
        'COUNTRY': country,
        'POSTAL_CODE': f"{random.randint(10000,99999)}",
        'TAX_ID': make_tax_id(country),
        'BANK_ACCOUNT': make_bank_account(),
        'CATEGORY': category,
        'PAYMENT_TERMS': random.choice(PAYMENT_TERMS),
        'CURRENCY': random.choice(CURRENCIES),
        'STATUS': random.choice(STATUSES),
        'CREATED_ON': created.isoformat(),
        'LAST_MODIFIED': modified.isoformat(),
        'RISK_SCORE': round(random.uniform(0.05, 0.75), 2),
        'DESCRIPTION': make_description(name, category, city)
    })
    vendor_ids_all.append(vid)

# ---------- Intentional MDQ defects (20 vendors) ----------

# 1. Duplicate pairs (same address, similar names) - 5 pairs
for i in range(131, 141, 2):
    base = vendors[random.randint(0, 129)].copy()
    variant_name = base['VENDOR_NAME'].replace('LLC', 'Ltd').replace('Inc', 'Incorporated')
    if variant_name == base['VENDOR_NAME']:
        variant_name = base['VENDOR_NAME'] + " Group"
    vid_a = make_vendor_id(i)
    vid_b = make_vendor_id(i+1)
    base['VENDOR_ID'] = vid_a
    base['CREATED_ON'] = date(2023, random.randint(1,12), random.randint(1,28)).isoformat()
    vendors.append(base)
    vendor_ids_all.append(vid_a)
    dup = base.copy()
    dup['VENDOR_ID'] = vid_b
    dup['VENDOR_NAME'] = variant_name
    dup['TAX_ID'] = make_tax_id(base['COUNTRY'])
    dup['CREATED_ON'] = date(2024, random.randint(1,12), random.randint(1,28)).isoformat()
    dup['DESCRIPTION'] = f"{variant_name} similar operations at {base['CITY']}"
    vendors.append(dup)
    vendor_ids_all.append(vid_b)

# 2. Missing tax IDs - 5 vendors
for i in range(141, 146):
    vid = make_vendor_id(i)
    country = random.choice(COUNTRIES)
    city = random.choice(CITIES[country])
    name = f"{random.choice(VENDOR_NAMES)} {random.choice(['LLC','GmbH'])}"
    vendors.append({
        'VENDOR_ID': vid,
        'VENDOR_NAME': name,
        'ADDRESS_LINE1': f"{random.randint(1,9999)} {random.choice(CITY_STREETS)}",
        'CITY': city,
        'COUNTRY': country,
        'POSTAL_CODE': f"{random.randint(10000,99999)}",
        'TAX_ID': '',
        'BANK_ACCOUNT': make_bank_account(),
        'CATEGORY': random.choice(CATEGORIES),
        'PAYMENT_TERMS': random.choice(PAYMENT_TERMS),
        'CURRENCY': random.choice(CURRENCIES),
        'STATUS': 'ACTIVE',
        'CREATED_ON': date(2025, random.randint(1,12), random.randint(1,28)).isoformat(),
        'LAST_MODIFIED': date(2026, random.randint(1,9), random.randint(1,28)).isoformat(),
        'RISK_SCORE': round(random.uniform(0.5, 0.9), 2),
        'DESCRIPTION': make_description(name, random.choice(CATEGORIES), city)
    })
    vendor_ids_all.append(vid)

# 3. Blocked vendors that will have recent transactions (audit red flag) - 5 vendors
blocked_vendors_with_txns = []
for i in range(146, 151):
    vid = make_vendor_id(i)
    country = random.choice(COUNTRIES)
    city = random.choice(CITIES[country])
    name = f"{random.choice(VENDOR_NAMES)} {random.choice(['LLC','Inc'])}"
    category = random.choice(CATEGORIES)
    vendors.append({
        'VENDOR_ID': vid,
        'VENDOR_NAME': name,
        'ADDRESS_LINE1': f"{random.randint(1,9999)} {random.choice(CITY_STREETS)}",
        'CITY': city,
        'COUNTRY': country,
        'POSTAL_CODE': f"{random.randint(10000,99999)}",
        'TAX_ID': make_tax_id(country),
        'BANK_ACCOUNT': make_bank_account(),
        'CATEGORY': category,
        'PAYMENT_TERMS': random.choice(PAYMENT_TERMS),
        'CURRENCY': random.choice(CURRENCIES),
        'STATUS': 'BLOCKED',
        'CREATED_ON': date(2022, random.randint(1,12), random.randint(1,28)).isoformat(),
        'LAST_MODIFIED': date(2026, random.randint(6,9), random.randint(1,28)).isoformat(),
        'RISK_SCORE': round(random.uniform(0.8, 0.99), 2),
        'DESCRIPTION': f"{name} blocked pending compliance review, {category.lower().replace('_',' ')} vendor"
    })
    vendor_ids_all.append(vid)
    blocked_vendors_with_txns.append(vid)

# Write vendors.csv
with open(OUT / "vendors.csv", "w", newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=list(vendors[0].keys()))
    writer.writeheader()
    writer.writerows(vendors)

print(f"vendors.csv written: {len(vendors)} rows")

# ==========================================================
# 2. Generate TRANSACTIONS
# ==========================================================
transactions = []
active_vendor_ids = [v['VENDOR_ID'] for v in vendors if v['STATUS'] == 'ACTIVE']

def make_txn_id(i):
    return f"TXN{i:010d}"

# 480 clean transactions
for i in range(1, 481):
    vid = random.choice(active_vendor_ids)
    inv_date = date(2025, 1, 1) + timedelta(days=random.randint(0, 600))
    post_date = inv_date + timedelta(days=random.randint(0, 10))
    amt = round(random.lognormvariate(8, 1.5), 2)
    if amt > 500000:
        amt = round(amt / 10, 2)
    transactions.append({
        'TXN_ID': make_txn_id(i),
        'VENDOR_ID': vid,
        'INVOICE_NUMBER': f"INV-{random.randint(100000, 999999)}",
        'INVOICE_DATE': inv_date.isoformat(),
        'POSTING_DATE': post_date.isoformat(),
        'AMOUNT': amt,
        'CURRENCY': random.choice(['USD', 'EUR', 'GBP', 'INR']),
        'PAYMENT_STATUS': random.choices(['PAID','PENDING','OVERDUE'], weights=[70,20,10])[0],
        'APPROVED_BY': f"USER{random.randint(1,50):03d}",
        'NOTES': random.choice([
            'Standard invoice processing',
            'Contract renewal Q4',
            'Monthly retainer',
            'Project milestone payment',
            'Recurring service fee'
        ])
    })

# 20 defect transactions
# 10 against BLOCKED vendors (audit red flag)
for i in range(481, 491):
    vid = random.choice(blocked_vendors_with_txns)
    inv_date = date(2026, random.randint(6,9), random.randint(1,28))
    post_date = inv_date + timedelta(days=random.randint(0, 5))
    transactions.append({
        'TXN_ID': make_txn_id(i),
        'VENDOR_ID': vid,
        'INVOICE_NUMBER': f"INV-{random.randint(100000, 999999)}",
        'INVOICE_DATE': inv_date.isoformat(),
        'POSTING_DATE': post_date.isoformat(),
        'AMOUNT': round(random.uniform(5000, 80000), 2),
        'CURRENCY': 'USD',
        'PAYMENT_STATUS': 'PAID',
        'APPROVED_BY': f"USER{random.randint(1,50):03d}",
        'NOTES': 'Payment authorized despite vendor status hold'
    })

# 10 round number amounts on weekend postings (fraud signals)
for i in range(491, 501):
    vid = random.choice(active_vendor_ids)
    weekend = date(2026, random.randint(1,9), random.randint(1,28))
    while weekend.weekday() < 5:
        weekend = weekend + timedelta(days=1)
    transactions.append({
        'TXN_ID': make_txn_id(i),
        'VENDOR_ID': vid,
        'INVOICE_NUMBER': f"INV-{random.randint(100000, 999999)}",
        'INVOICE_DATE': weekend.isoformat(),
        'POSTING_DATE': weekend.isoformat(),
        'AMOUNT': random.choice([10000.00, 25000.00, 50000.00, 75000.00, 100000.00]),
        'CURRENCY': 'USD',
        'PAYMENT_STATUS': 'PAID',
        'APPROVED_BY': f"USER{random.randint(1,10):03d}",
        'NOTES': 'Expedited weekend processing per business request'
    })

with open(OUT / "transactions.csv", "w", newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=list(transactions[0].keys()))
    writer.writeheader()
    writer.writerows(transactions)

print(f"transactions.csv written: {len(transactions)} rows")

# ==========================================================
# 3. Generate QUALITY_RULES
# ==========================================================
rules = [
    ('QR001', 'Vendor Name Not Null', 'Completeness', 'CRITICAL',
     'Vendor master name field must not be null or empty',
     "SELECT VENDOR_ID FROM VENDORS WHERE VENDOR_NAME IS NULL OR TRIM(VENDOR_NAME) = ''",
     'Contact vendor to obtain legal name, update master'),
    ('QR002', 'Tax ID Present For Active', 'Completeness', 'HIGH',
     'All ACTIVE vendors must have a tax identification number',
     "SELECT VENDOR_ID FROM VENDORS WHERE STATUS = 'ACTIVE' AND (TAX_ID IS NULL OR TAX_ID = '')",
     'Request tax certificate from vendor, block until received'),
    ('QR003', 'Bank Account Format', 'Validity', 'HIGH',
     'Bank account must be numeric and at least 8 digits',
     "SELECT VENDOR_ID FROM VENDORS WHERE LENGTH(BANK_ACCOUNT) < 8",
     'Validate with treasury team, update via workflow'),
    ('QR004', 'Duplicate Vendor Detection', 'Uniqueness', 'HIGH',
     'Vendors with same address and similar name likely duplicates',
     "SELECT A.VENDOR_ID, B.VENDOR_ID FROM VENDORS A JOIN VENDORS B ON A.ADDRESS_LINE1 = B.ADDRESS_LINE1 AND A.CITY = B.CITY WHERE A.VENDOR_ID < B.VENDOR_ID",
     'MDG dedup workflow, merge or archive one record'),
    ('QR005', 'Blocked Vendor Active Transactions', 'Consistency', 'CRITICAL',
     'BLOCKED vendors should not have new transactions posted',
     "SELECT T.TXN_ID FROM TRANSACTIONS T JOIN VENDORS V ON T.VENDOR_ID = V.VENDOR_ID WHERE V.STATUS = 'BLOCKED' AND T.POSTING_DATE > CURRENT_DATE - 90",
     'Audit posting, reverse if unauthorized, notify compliance'),
    ('QR006', 'Missing Country Code', 'Completeness', 'MEDIUM',
     'Vendor country ISO code required for tax reporting',
     "SELECT VENDOR_ID FROM VENDORS WHERE COUNTRY IS NULL OR LENGTH(COUNTRY) != 3",
     'Enrich from address, validate against ISO 3166'),
    ('QR007', 'Invalid Payment Terms', 'Validity', 'MEDIUM',
     'Payment terms must match approved code list',
     "SELECT VENDOR_ID FROM VENDORS WHERE PAYMENT_TERMS NOT IN ('NT30','NT45','NT60','NT90','2P10','IMM')",
     'Update to approved payment term code'),
    ('QR008', 'High Risk Score Review', 'Consistency', 'HIGH',
     'Vendors with risk score above 0.8 require quarterly review',
     "SELECT VENDOR_ID FROM VENDORS WHERE RISK_SCORE > 0.8 AND STATUS = 'ACTIVE'",
     'Send to procurement risk committee for review'),
    ('QR009', 'Stale Vendor Records', 'Timeliness', 'LOW',
     'Vendors not modified for over 3 years may be inactive',
     "SELECT VENDOR_ID FROM VENDORS WHERE LAST_MODIFIED < ADD_YEARS(CURRENT_DATE, -3)",
     'Contact for confirmation, archive if no response'),
    ('QR010', 'Weekend Posting Anomaly', 'Consistency', 'MEDIUM',
     'Transactions posted on weekends require justification',
     "SELECT TXN_ID FROM TRANSACTIONS WHERE WEEKDAY(POSTING_DATE) IN (5,6)",
     'Review posting authorization and business reason'),
    ('QR011', 'Round Number Amount', 'Consistency', 'MEDIUM',
     'Perfectly round transaction amounts are unusual for real invoices',
     "SELECT TXN_ID FROM TRANSACTIONS WHERE MOD(AMOUNT, 5000) = 0 AND AMOUNT >= 10000",
     'Cross check with PO and receipt, flag if no support'),
    ('QR012', 'Currency Mismatch', 'Consistency', 'MEDIUM',
     'Transaction currency should match vendor default currency',
     "SELECT T.TXN_ID FROM TRANSACTIONS T JOIN VENDORS V ON T.VENDOR_ID = V.VENDOR_ID WHERE T.CURRENCY != V.CURRENCY",
     'Verify hedging policy, correct FX booking if needed'),
    ('QR013', 'Postal Code Format', 'Validity', 'LOW',
     'Postal code should match country format',
     "SELECT VENDOR_ID FROM VENDORS WHERE COUNTRY = 'USA' AND LENGTH(POSTAL_CODE) != 5",
     'Correct via address validation service'),
    ('QR014', 'New Vendor Rapid Payment', 'Consistency', 'HIGH',
     'Vendors created within last 30 days receiving payments over 50k',
     "SELECT T.TXN_ID FROM TRANSACTIONS T JOIN VENDORS V ON T.VENDOR_ID = V.VENDOR_ID WHERE V.CREATED_ON > CURRENT_DATE - 30 AND T.AMOUNT > 50000",
     'Enhanced due diligence review before payment release'),
    ('QR015', 'Pending Status Over 60 Days', 'Timeliness', 'MEDIUM',
     'Vendors in PENDING status for over 60 days need action',
     "SELECT VENDOR_ID FROM VENDORS WHERE STATUS = 'PENDING' AND CREATED_ON < CURRENT_DATE - 60",
     'Complete onboarding or reject application'),
    ('QR016', 'Category Missing', 'Completeness', 'MEDIUM',
     'Vendor category required for spend analytics',
     "SELECT VENDOR_ID FROM VENDORS WHERE CATEGORY IS NULL OR CATEGORY = ''",
     'Classify based on invoiced services'),
    ('QR017', 'Overdue Payment Ratio', 'Consistency', 'HIGH',
     'Vendors with over 50% overdue payments indicate cash flow issue',
     "SELECT VENDOR_ID FROM TRANSACTIONS WHERE PAYMENT_STATUS = 'OVERDUE' GROUP BY VENDOR_ID HAVING COUNT(*) > 5",
     'Alert AP team to investigate cash and dispute status'),
    ('QR018', 'Duplicate Invoice Number', 'Uniqueness', 'CRITICAL',
     'Same invoice number for same vendor indicates duplicate payment risk',
     "SELECT VENDOR_ID, INVOICE_NUMBER FROM TRANSACTIONS GROUP BY VENDOR_ID, INVOICE_NUMBER HAVING COUNT(*) > 1",
     'Reverse duplicate payment, recover from vendor'),
    ('QR019', 'Very Old Invoice Postings', 'Timeliness', 'LOW',
     'Invoices posted more than 90 days after invoice date',
     "SELECT TXN_ID FROM TRANSACTIONS WHERE DAYS_BETWEEN(INVOICE_DATE, POSTING_DATE) > 90",
     'Investigate posting delay, adjust period if needed'),
    ('QR020', 'Bank Account Sharing', 'Uniqueness', 'HIGH',
     'Multiple vendors sharing same bank account is high fraud risk',
     "SELECT BANK_ACCOUNT FROM VENDORS GROUP BY BANK_ACCOUNT HAVING COUNT(*) > 1",
     'Immediate investigation, freeze payments pending review'),
    ('QR021', 'Vendor Name Length Anomaly', 'Validity', 'LOW',
     'Vendor names shorter than 3 characters or longer than 150 unusual',
     "SELECT VENDOR_ID FROM VENDORS WHERE LENGTH(VENDOR_NAME) < 3 OR LENGTH(VENDOR_NAME) > 150",
     'Verify legal name, correct or standardize'),
    ('QR022', 'Description Empty', 'Completeness', 'LOW',
     'Vendor description missing hinders searchability',
     "SELECT VENDOR_ID FROM VENDORS WHERE DESCRIPTION IS NULL OR LENGTH(DESCRIPTION) < 10",
     'Add meaningful description of vendor services'),
    ('QR023', 'Zero Amount Invoices', 'Validity', 'MEDIUM',
     'Zero or negative amount invoices should not exist without credit memo',
     "SELECT TXN_ID FROM TRANSACTIONS WHERE AMOUNT <= 0",
     'Verify with AP, likely data entry error'),
    ('QR024', 'Payment To Wrong Country', 'Consistency', 'HIGH',
     'Payments to sanctioned or non doing business countries',
     "SELECT V.VENDOR_ID FROM VENDORS V WHERE V.COUNTRY IN ('IRN','PRK','SYR','CUB')",
     'Immediate compliance escalation, freeze account'),
    ('QR025', 'IT Category No IT Description', 'Consistency', 'LOW',
     'IT_SERVICES category vendors should mention IT or technology in description',
     "SELECT VENDOR_ID FROM VENDORS WHERE CATEGORY = 'IT_SERVICES' AND UPPER(DESCRIPTION) NOT LIKE '%IT%' AND UPPER(DESCRIPTION) NOT LIKE '%TECHNOLOGY%'",
     'Verify category assignment, re-classify if needed'),
    ('QR026', 'Concentration Risk', 'Consistency', 'MEDIUM',
     'Single vendor receiving over 20% of total spend in category',
     "WITH SPEND AS (SELECT V.CATEGORY, T.VENDOR_ID, SUM(T.AMOUNT) AS VENDOR_SPEND FROM TRANSACTIONS T JOIN VENDORS V ON T.VENDOR_ID = V.VENDOR_ID GROUP BY V.CATEGORY, T.VENDOR_ID) SELECT VENDOR_ID FROM SPEND WHERE VENDOR_SPEND > 0",
     'Review vendor diversification strategy'),
    ('QR027', 'Rapid Modification Frequency', 'Consistency', 'MEDIUM',
     'Vendor master modified within 24 hours of transaction posting suspicious',
     "SELECT V.VENDOR_ID FROM VENDORS V JOIN TRANSACTIONS T ON V.VENDOR_ID = T.VENDOR_ID WHERE DAYS_BETWEEN(V.LAST_MODIFIED, T.POSTING_DATE) BETWEEN 0 AND 1",
     'Audit master change log for authorization'),
    ('QR028', 'Address Format Standard', 'Validity', 'LOW',
     'Address line missing street number is non standard',
     "SELECT VENDOR_ID FROM VENDORS WHERE ADDRESS_LINE1 NOT LIKE '%[0-9]%'",
     'Standardize address via geocoding service'),
    ('QR029', 'Payment Terms Discount Unused', 'Consistency', 'LOW',
     'Vendors with 2P10 terms but no early payments captured',
     "SELECT V.VENDOR_ID FROM VENDORS V WHERE V.PAYMENT_TERMS = '2P10'",
     'Route through early payment discount workflow'),
    ('QR030', 'Currency Not Approved', 'Validity', 'MEDIUM',
     'Vendor currency must be from approved list',
     "SELECT VENDOR_ID FROM VENDORS WHERE CURRENCY NOT IN ('USD','EUR','GBP','INR','CNY','JPY','BRL','CAD','AUD')",
     'Update to approved currency or add to approved list')
]

with open(OUT / "quality_rules.csv", "w", newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['RULE_ID','RULE_NAME','RULE_CATEGORY','SEVERITY','DESCRIPTION','SQL_CHECK','REMEDIATION'])
    for r in rules:
        writer.writerow(r)

print(f"quality_rules.csv written: {len(rules)} rows")

# ==========================================================
# 4. Generate QUALITY_ISSUES (historical)
# ==========================================================
issues = []
statuses_dist = ['OPEN', 'OPEN', 'RESOLVED', 'RESOLVED', 'RESOLVED', 'RESOLVED', 'INVESTIGATING']

def make_issue_id(i):
    return f"QI{i:013d}"

descriptions_templates = {
    'CRITICAL': [
        "Vendor {vid} flagged as {category}. Immediate compliance escalation required. Payment authorization suspended pending review.",
        "Critical data quality violation detected for vendor {vid}. Business rule {rid} triggered. Audit committee notification sent.",
        "High risk anomaly on vendor {vid}. Automated block placed. Manual override requires CFO approval per policy."
    ],
    'HIGH': [
        "Vendor {vid} identified with {category} concern. AP team notified. Remediation SLA 5 business days.",
        "Quality issue for vendor {vid} pending review. Rule {rid} violation observed on last audit cycle.",
        "Recurring pattern detected for vendor {vid}. Second occurrence in 90 days. Escalated to procurement lead."
    ],
    'MEDIUM': [
        "Vendor {vid} shows {category} deviation. Non urgent remediation queued in monthly cleanup batch.",
        "Data quality alert for vendor {vid}. Rule {rid} check failed. Standard remediation workflow triggered.",
        "Minor consistency issue with vendor {vid}. Auto correction attempted, manual verification pending."
    ],
    'LOW': [
        "Housekeeping item on vendor {vid}. Rule {rid} suggests improvement. Batched with next quarterly review.",
        "Low priority quality note for vendor {vid}. Non blocking. Address at annual master data cleanup.",
        "Cosmetic data inconsistency on vendor {vid}. Rule {rid} preferred format. Optional update recommended."
    ]
}

resolution_templates = [
    "Reviewed with vendor via email correspondence dated {resdate}. Tax certificate received and validated. Master record updated. Root cause: incomplete onboarding form.",
    "Investigation completed by AP team. Root cause identified as workflow gap during vendor merger event. Process control added to prevent recurrence.",
    "MDG dedup workflow executed. Both records merged into surviving vendor {vid}. Historical transactions repointed successfully. No financial impact.",
    "Compliance review cleared vendor {vid} for reactivation. Enhanced monitoring applied for 6 months. Quarterly attestation added to control matrix.",
    "Auto remediation successful. System applied standardization rules from master data governance policy. No manual intervention required.",
    "Manual correction applied by MDG steward on {resdate}. Change log audit trail preserved. Notification sent to requesting business unit.",
    "Escalated to procurement risk committee. Committee approved vendor to remain active with enhanced quarterly reviews. Documented in risk register.",
    "Payment authorization was found to be valid emergency exception per business continuity policy section 4.2. No further action required."
]

for i in range(1, 201):
    rule = random.choice(rules)
    rid = rule[0]
    severity = rule[3]
    category = rule[2]
    vid = random.choice(vendor_ids_all)
    detected = date(2025, 1, 1) + timedelta(days=random.randint(0, 630))
    status = random.choice(statuses_dist)
    if status == 'RESOLVED':
        resolved_days = random.randint(1, 45)
        resolved_on = (detected + timedelta(days=resolved_days)).isoformat()
        resolution_template = random.choice(resolution_templates)
        resolution_notes = resolution_template.format(vid=vid, resdate=resolved_on)
    else:
        resolved_on = ''
        resolution_notes = ''
    desc_template = random.choice(descriptions_templates[severity])
    description = desc_template.format(vid=vid, category=category.lower(), rid=rid)
    issues.append({
        'ISSUE_ID': make_issue_id(i),
        'VENDOR_ID': vid,
        'RULE_ID': rid,
        'DETECTED_ON': detected.isoformat(),
        'RESOLVED_ON': resolved_on,
        'STATUS': status,
        'DESCRIPTION': description,
        'RESOLUTION_NOTES': resolution_notes
    })

with open(OUT / "quality_issues.csv", "w", newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=list(issues[0].keys()))
    writer.writeheader()
    writer.writerows(issues)

print(f"quality_issues.csv written: {len(issues)} rows")

# ==========================================================
# Summary
# ==========================================================
print("\n=== Generation complete ===")
print(f"Output folder: {OUT.resolve()}")
print(f"  vendors.csv        {len(vendors)} rows (130 clean + 10 dupes + 5 no tax + 5 blocked with active txns)")
print(f"  transactions.csv   {len(transactions)} rows (480 clean + 10 to blocked + 10 weekend round)")
print(f"  quality_rules.csv  {len(rules)} rows (Completeness, Uniqueness, Validity, Consistency, Timeliness)")
print(f"  quality_issues.csv {len(issues)} rows (mix of OPEN, RESOLVED, INVESTIGATING)")
