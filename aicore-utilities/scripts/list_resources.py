#!/usr/bin/env python3
"""
List all AI Core resources in the current resource group.

Shows: scenarios, configurations, executions, deployments, secrets.
Useful before starting new work to see what already exists.

Usage:
    python3 scripts/list_resources.py
    python3 scripts/list_resources.py --resource-group ai-launchpad
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from lib import AICoreClient


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resource-group", default="default",
                        help="Resource group to inspect (default: default)")
    parser.add_argument("--limit", type=int, default=20,
                        help="Max items per section (default: 20)")
    args = parser.parse_args()

    client = AICoreClient(resource_group=args.resource_group)

    print(f"\nResource group: {args.resource_group}")
    print("=" * 60)

    # Object Store Secrets
    print("\n[Object Store Secrets]")
    try:
        secrets = client.list_object_store_secrets()
        for s in secrets:
            meta = s.get("metadata", {})
            print(f"  {s['name']}: bucket={meta.get('storage.ai.sap.com/bucket')}, "
                  f"prefix={meta.get('storage.ai.sap.com/pathPrefix')}")
    except Exception as e:
        print(f"  Error: {e}")

    # Scenarios
    print("\n[Scenarios]")
    try:
        scenarios = client.list_scenarios()
        for sc in scenarios[:args.limit]:
            print(f"  {sc.get('id')} - {sc.get('name')}")
        if len(scenarios) > args.limit:
            print(f"  ... and {len(scenarios) - args.limit} more")
    except Exception as e:
        print(f"  Error: {e}")

    # Configurations
    print("\n[Configurations]")
    try:
        configs = client.list_configurations()
        for c in configs[:args.limit]:
            print(f"  {c.get('id')[:8]}... - {c.get('name')}")
        if len(configs) > args.limit:
            print(f"  ... and {len(configs) - args.limit} more")
    except Exception as e:
        print(f"  Error: {e}")

    # Executions
    print("\n[Executions]")
    try:
        executions = client.list_executions()
        for e in executions[:args.limit]:
            print(f"  {e.get('id')} - scenario={e.get('scenarioId')} - {e.get('status')}")
        if len(executions) > args.limit:
            print(f"  ... and {len(executions) - args.limit} more")
    except Exception as ex:
        print(f"  Error: {ex}")

    # Deployments
    print("\n[Deployments]")
    try:
        deployments = client.list_deployments()
        running = sum(1 for d in deployments if d.get("status") == "RUNNING")
        stopped = sum(1 for d in deployments if d.get("status") == "STOPPED")
        print(f"  Total: {len(deployments)} | RUNNING: {running} | STOPPED: {stopped}")
        for d in deployments[:args.limit]:
            print(f"  {d.get('id')} | {d.get('status')} | scenario={d.get('scenarioId')}")
        if len(deployments) > args.limit:
            print(f"  ... and {len(deployments) - args.limit} more")
    except Exception as e:
        print(f"  Error: {e}")

    print()


if __name__ == "__main__":
    sys.exit(main() or 0)
