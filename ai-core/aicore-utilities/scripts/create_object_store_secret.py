#!/usr/bin/env python3
"""
Create an S3 object store secret in SAP AI Core.

Each lab should have its own secret scoped to its own S3 path prefix.
This separates artifacts cleanly and makes cleanup easier.

Usage:
    python3 scripts/create_object_store_secret.py \\
        --name supplier-prediction \\
        --bucket amzn-aicore-2026 \\
        --path-prefix supplier-prediction \\
        --aws-profile aicore-test \\
        --region us-east-1

    python3 scripts/create_object_store_secret.py --help

By default it reads AWS credentials from the named profile in ~/.aws/credentials.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from lib import AICoreClient, get_aws_credentials


def main():
    parser = argparse.ArgumentParser(
        description="Create an object store secret in SAP AI Core.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--name", required=True,
                        help="Secret name (referenced in scenario YAML)")
    parser.add_argument("--bucket", required=True,
                        help="S3 bucket name")
    parser.add_argument("--path-prefix", required=True,
                        help="Path inside the bucket this secret can access")
    parser.add_argument("--aws-profile", default="default",
                        help="AWS CLI profile to read credentials from (default: default)")
    parser.add_argument("--region", default="us-east-1",
                        help="AWS region (default: us-east-1)")
    parser.add_argument("--resource-group", default="default",
                        help="AI Core resource group (default: default)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print payload without creating the secret")
    args = parser.parse_args()

    # Read AWS credentials
    try:
        aws = get_aws_credentials(profile=args.aws_profile)
    except (FileNotFoundError, KeyError) as e:
        print(f"AWS credentials error: {e}")
        return 1

    print(f"\nCreating object store secret:")
    print(f"  Name:         {args.name}")
    print(f"  Bucket:       {args.bucket}")
    print(f"  Path prefix:  {args.path_prefix}")
    print(f"  Region:       {args.region}")
    print(f"  AWS profile:  {args.aws_profile}")
    print(f"  AWS key:      {aws['aws_access_key_id'][:10]}...")
    print(f"  RG:           {args.resource_group}")

    if args.dry_run:
        print("\nDRY RUN - not creating")
        return 0

    client = AICoreClient(resource_group=args.resource_group)

    try:
        result = client.create_object_store_secret(
            name=args.name,
            bucket=args.bucket,
            region=args.region,
            path_prefix=args.path_prefix,
            access_key_id=aws["aws_access_key_id"],
            secret_access_key=aws["aws_secret_access_key"],
        )
        print(f"\nCreated successfully:")
        print(json.dumps(result, indent=2))
        return 0
    except RuntimeError as e:
        print(f"\nFailed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
