#!/usr/bin/env python3
"""
Smoke test for SAP AI Core connectivity.

Verifies:
- Service key file exists and is valid JSON
- OAuth authentication works
- API endpoints are reachable
- Lists resource groups (admin operation)

Run this first whenever returning to the environment after time away
or after suspected access changes.

Usage:
    python3 scripts/smoke_test.py
"""

import sys
from pathlib import Path

# Add parent directory to path so we can import lib
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib import AICoreClient


def main():
    print("=" * 60)
    print("SAP AI Core Smoke Test")
    print("=" * 60)

    try:
        client = AICoreClient()
    except FileNotFoundError as e:
        print(f"FAIL: {e}")
        return 1

    # Test 1: Token acquisition
    print("\n[1/3] Testing OAuth token acquisition...")
    try:
        token = client.get_token()
        print(f"  OK: Token length {len(token)}, prefix {token[:20]}...")
    except Exception as e:
        print(f"  FAIL: {e}")
        return 1

    # Test 2: Resource groups (admin endpoint)
    print("\n[2/3] Listing resource groups...")
    try:
        rgs = client.list_resource_groups()
        print(f"  OK: Found {len(rgs)} resource groups:")
        for rg in rgs:
            print(f"    - {rg['resourceGroupId']}")
    except Exception as e:
        print(f"  FAIL: {e}")
        return 1

    # Test 3: Scenarios in default RG
    print("\n[3/3] Listing scenarios in 'default' resource group...")
    try:
        scenarios = client.list_scenarios()
        print(f"  OK: Found {len(scenarios)} scenarios")
        for sc in scenarios[:5]:
            print(f"    - {sc.get('id')} - {sc.get('name')}")
        if len(scenarios) > 5:
            print(f"    ... and {len(scenarios) - 5} more")
    except Exception as e:
        print(f"  FAIL: {e}")
        return 1

    print("\n" + "=" * 60)
    print("Smoke test PASSED")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
