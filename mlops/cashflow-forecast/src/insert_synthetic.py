"""
Synthetic cashflow data insertion for UC2.5 scheduled retraining.

Time-compressed simulation: each invocation advances the dataset by ONE
business day, regardless of wall-clock cadence. When called from the
hourly Schedule, this produces ~1 month of simulated business activity
per day of wall-clock time.

Idempotent: if the day after MAX(TXN_DATE) already has rows, skip.
This makes re-runs of the same scheduled instance safe.

Schema (from UC2.3):
    PROC_AI.CASHFLOW_DAILY (
        TXN_DATE DATE NOT NULL,
        COMPANY_CODE NVARCHAR(4) NOT NULL,
        CASHFLOW_AMOUNT DECIMAL(15,2) NOT NULL,
        CURRENCY NVARCHAR(3) NOT NULL,
        TXN_TYPE NVARCHAR(20) NOT NULL,
        CREATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (TXN_DATE, COMPANY_CODE, TXN_TYPE)
    )

Pattern logic mirrors the original UC2.3 seed SQL:
    - Weekend (Sat/Sun): ~10% of weekday baseline
    - End-of-month last 3 days: ~1.8x baseline (payroll/vendor spike)
    - End-of-quarter (Mar/Jun/Sep/Dec, day >= 25): ~2.2x baseline
    - Normal weekday: baseline
    - Deterministic noise: ±15% based on day-of-year × company multiplier
"""
import calendar
import os
import sys
from datetime import date, timedelta
from decimal import Decimal

from hdbcli import dbapi


HANA_HOST = os.environ.get("HANA_HOST")
HANA_PORT = int(os.environ.get("HANA_PORT", "443"))
HANA_USER = os.environ.get("HANA_USER")
HANA_PASSWORD = os.environ.get("HANA_PASSWORD")
HANA_SCHEMA = os.environ.get("HANA_SCHEMA", "PROC_AI")

# Per-company baselines, mirrored from UC2.3 seed SQL.
COMPANIES = {
    "1710": {"currency": "USD", "base_inflow": 50000, "base_outflow": 35000},
    "1010": {"currency": "EUR", "base_inflow": 30000, "base_outflow": 22000},
}


def connect():
    if not all([HANA_HOST, HANA_USER, HANA_PASSWORD]):
        print("[error] missing HANA env vars - check Generic Secret binding", file=sys.stderr)
        sys.exit(1)
    print(f"[hana] connecting to {HANA_HOST}:{HANA_PORT} as {HANA_USER}")
    return dbapi.connect(
        address=HANA_HOST,
        port=HANA_PORT,
        user=HANA_USER,
        password=HANA_PASSWORD,
        encrypt=True,
        sslValidateCertificate=True,
    )


def get_max_date(cur) -> date:
    cur.execute(f"SELECT MAX(TXN_DATE) FROM {HANA_SCHEMA}.CASHFLOW_DAILY")
    row = cur.fetchone()
    if not row or row[0] is None:
        print("[error] CASHFLOW_DAILY is empty - run UC2.3 seed SQL first", file=sys.stderr)
        sys.exit(1)
    return row[0]


def date_already_exists(cur, target: date) -> bool:
    """Idempotency check: does target date already have rows?"""
    cur.execute(
        f"SELECT COUNT(*) FROM {HANA_SCHEMA}.CASHFLOW_DAILY WHERE TXN_DATE = ?",
        (target,),
    )
    return cur.fetchone()[0] > 0


def compute_amount(target: date, company_code: str, txn_type: str) -> Decimal:
    """Replicates the UC2.3 seed SQL pattern logic in Python."""
    cfg = COMPANIES[company_code]
    base = cfg["base_inflow"] if txn_type == "INFLOW" else cfg["base_outflow"]

    weekday = target.weekday()  # 0=Mon ... 6=Sun
    last_day_of_month = calendar.monthrange(target.year, target.month)[1]
    days_until_month_end = last_day_of_month - target.day

    if weekday in (5, 6):
        # Weekend: ~10% of weekday baseline
        multiplier = 0.1
    elif target.month in (3, 6, 9, 12) and target.day >= 25:
        # End-of-quarter: ~2.2x baseline (checked BEFORE end-of-month, since EOQ
        # days are also EOM days and we want EOQ to win)
        multiplier = 2.2
    elif days_until_month_end <= 2:
        # End-of-month last 3 days: ~1.8x baseline
        multiplier = 1.8
    else:
        multiplier = 1.0

    # Deterministic noise: ±15% based on day-of-year × company multiplier
    company_mult = 7 if company_code == "1710" else 11
    day_of_year = target.timetuple().tm_yday
    noise_factor = 1 + ((day_of_year * company_mult) % 31 - 15) / 100.0

    amount = Decimal(str(round(base * multiplier * noise_factor, 2)))
    return amount


def insert_one_day(cur, target: date) -> int:
    """Insert all 4 rows for one day (2 companies × 2 txn types)."""
    rows = []
    for company_code, cfg in COMPANIES.items():
        for txn_type in ("INFLOW", "OUTFLOW"):
            amount = compute_amount(target, company_code, txn_type)
            rows.append((target, company_code, amount, cfg["currency"], txn_type))

    cur.executemany(
        f"""INSERT INTO {HANA_SCHEMA}.CASHFLOW_DAILY
            (TXN_DATE, COMPANY_CODE, CASHFLOW_AMOUNT, CURRENCY, TXN_TYPE)
            VALUES (?, ?, ?, ?, ?)""",
        rows,
    )
    return len(rows)


def main() -> int:
    print("=" * 60)
    print("UC2.5 - Synthetic data insertion (time-compressed)")
    print("=" * 60)

    conn = connect()
    cur = conn.cursor()

    try:
        max_date = get_max_date(cur)
        target = max_date + timedelta(days=1)
        print(f"[plan] current MAX(TXN_DATE)={max_date}, advancing to {target}")

        if date_already_exists(cur, target):
            print(f"[skip] {target} already has rows - idempotent skip, exiting 0")
            return 0

        inserted = insert_one_day(cur, target)
        conn.commit()
        print(f"[done] inserted {inserted} rows for {target}")

        # Show running totals so the workflow log tells a useful story
        cur.execute(f"SELECT COUNT(*), MIN(TXN_DATE), MAX(TXN_DATE) FROM {HANA_SCHEMA}.CASHFLOW_DAILY")
        total, min_d, max_d = cur.fetchone()
        print(f"[stats] table now has {total} rows, range {min_d}..{max_d}")
        return 0
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
