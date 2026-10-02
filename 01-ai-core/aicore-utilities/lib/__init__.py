"""SAP AI Core utility library."""
from .aicore_client import AICoreClient
from .aws_helpers import get_aws_credentials

__all__ = ["AICoreClient", "get_aws_credentials"]
