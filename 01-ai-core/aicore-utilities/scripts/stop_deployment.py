#!/usr/bin/env python3
"""
Stop one or more AI Core deployments to save compute cost.

Custom serving deployments (not foundation-models) consume compute hours
while running. Stop them when not actively in use.

Usage:
    python3 scripts/stop_deployment.py --deployment-id d74ee8a32f950025
    python3 scripts/stop_deployment.py --all-custom    # stop all non-foundation deployments
    python3 scripts/stop_deployment.py --list           # just list, do not stop
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from lib import AICoreClient


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--deployment-id", help="Specific deployment ID to stop")
    parser.add_argument("--all-custom", action="store_true",
                        help="Stop all RUNNING deployments except foundation-models")
    parser.add_argument("--list", action="store_true",
                        help="List deployments without stopping any")
    parser.add_argument("--resource-group", default="default")
    args = parser.parse_args()

    client = AICoreClient(resource_group=args.resource_group)

    deployments = client.list_deployments()

    if args.list:
        print(f"\n{'ID':<20} {'Status':<10} {'Scenario':<30}")
        print("-" * 60)
        for d in deployments:
            print(f"{d.get('id'):<20} {d.get('status', '?'):<10} {d.get('scenarioId', '?'):<30}")
        return 0

    targets = []
    if args.deployment_id:
        targets = [d for d in deployments if d.get("id") == args.deployment_id]
        if not targets:
            print(f"Deployment {args.deployment_id} not found")
            return 1
    elif args.all_custom:
        targets = [d for d in deployments
                   if d.get("status") == "RUNNING"
                   and d.get("scenarioId") not in ("foundation-models", "orchestration")]
    else:
        parser.print_help()
        return 1

    if not targets:
        print("No deployments to stop")
        return 0

    print(f"\nWill stop {len(targets)} deployment(s):")
    for d in targets:
        print(f"  {d.get('id')} - {d.get('scenarioId')}")

    response = input("\nProceed? (yes/no): ")
    if response.lower() != "yes":
        print("Cancelled")
        return 0

    for d in targets:
        try:
            client.stop_deployment(d["id"])
            print(f"  Stopped: {d['id']}")
        except RuntimeError as e:
            print(f"  Failed:  {d['id']} - {e}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
