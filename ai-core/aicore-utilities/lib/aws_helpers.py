"""
Helper to read AWS credentials from local AWS CLI configuration.

Reads from ~/.aws/credentials (standard AWS CLI location).
Supports named profiles.
"""

import configparser
from pathlib import Path


def get_aws_credentials(profile="default"):
    """
    Read AWS access key and secret from ~/.aws/credentials.

    Args:
        profile: AWS CLI profile name. Defaults to "default".

    Returns:
        dict with keys: aws_access_key_id, aws_secret_access_key, region

    Raises:
        FileNotFoundError if credentials file does not exist
        KeyError if profile does not exist in the file
    """
    creds_path = Path("~/.aws/credentials").expanduser()
    config_path = Path("~/.aws/config").expanduser()

    if not creds_path.exists():
        raise FileNotFoundError(
            f"AWS credentials not found at {creds_path}. "
            f"Run 'aws configure' to set up."
        )

    creds = configparser.ConfigParser()
    creds.read(creds_path)

    if profile not in creds:
        raise KeyError(
            f"Profile '{profile}' not found in {creds_path}. "
            f"Available profiles: {list(creds.sections())}"
        )

    result = {
        "aws_access_key_id": creds[profile]["aws_access_key_id"],
        "aws_secret_access_key": creds[profile]["aws_secret_access_key"],
        "region": "us-east-1",
    }

    # Read region from config file if available
    if config_path.exists():
        cfg = configparser.ConfigParser()
        cfg.read(config_path)
        section_name = "default" if profile == "default" else f"profile {profile}"
        if section_name in cfg and "region" in cfg[section_name]:
            result["region"] = cfg[section_name]["region"]

    return result
