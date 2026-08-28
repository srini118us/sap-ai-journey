"""
Reusable SAP AI Core client using raw HTTP.

Why raw HTTP and not the official SDK:
The ai-api-client-sdk version 2.6.x has URL path issues with SAP AI Core
endpoints (returns 404 on /admin/resourceGroups and /scenarios because
SDK does not prepend /v2 correctly). Raw HTTP is more reliable and gives
full visibility into what is happening.

Usage:
    from lib.aicore_client import AICoreClient
    client = AICoreClient()
    client.list_scenarios()
    client.list_deployments()
"""

import json
import os
import requests
from pathlib import Path


class AICoreClient:
    """SAP AI Core client using raw HTTP."""

    DEFAULT_KEY_PATH = "~/.aicore/aicore-key.json"

    def __init__(self, service_key_path=None, resource_group="default"):
        """
        Initialize the client.

        Args:
            service_key_path: Path to AI Core service key JSON file.
                Defaults to ~/.aicore/aicore-key.json
            resource_group: AI Core resource group to operate in.
                Defaults to "default"
        """
        if service_key_path is None:
            service_key_path = self.DEFAULT_KEY_PATH
        path = Path(service_key_path).expanduser()
        if not path.exists():
            raise FileNotFoundError(
                f"Service key not found at {path}. "
                f"Download from BTP Cockpit and save there."
            )

        with open(path) as f:
            self.sk = json.load(f)

        self.base_url = self.sk["serviceurls"]["AI_API_URL"]
        self.resource_group = resource_group
        self._token = None

    def get_token(self, refresh=False):
        """Get or refresh the OAuth token."""
        if self._token is None or refresh:
            r = requests.post(
                self.sk["url"] + "/oauth/token",
                data={"grant_type": "client_credentials"},
                auth=(self.sk["clientid"], self.sk["clientsecret"]),
                timeout=30,
            )
            r.raise_for_status()
            self._token = r.json()["access_token"]
        return self._token

    def _headers(self, content_type=None):
        h = {
            "Authorization": f"Bearer {self.get_token()}",
            "AI-Resource-Group": self.resource_group,
        }
        if content_type:
            h["Content-Type"] = content_type
        return h

    def _request(self, method, path, json_body=None, params=None):
        """Internal request helper. Returns (status_code, body)."""
        url = f"{self.base_url}{path}"
        kwargs = {"headers": self._headers("application/json" if json_body else None), "timeout": 30}
        if json_body is not None:
            kwargs["json"] = json_body
        if params is not None:
            kwargs["params"] = params

        r = requests.request(method, url, **kwargs)
        try:
            body = r.json() if r.text else None
        except ValueError:
            body = r.text
        return r.status_code, body

    # Resource Groups (admin endpoints)

    def list_resource_groups(self):
        """List all resource groups in the tenant. Requires admin permission."""
        code, body = self._request("GET", "/v2/admin/resourceGroups")
        if code != 200:
            raise RuntimeError(f"HTTP {code}: {body}")
        return body.get("resources", [])

    # Object Store Secrets

    def list_object_store_secrets(self):
        """List object store secrets in the current resource group."""
        code, body = self._request("GET", "/v2/admin/objectStoreSecrets")
        if code != 200:
            raise RuntimeError(f"HTTP {code}: {body}")
        return body.get("resources", [])

    def create_object_store_secret(self, name, bucket, region, path_prefix,
                                    access_key_id, secret_access_key,
                                    endpoint=None):
        """
        Create a new S3 object store secret.

        Args:
            name: Secret name (referenced in scenario YAML)
            bucket: S3 bucket name
            region: AWS region (e.g. us-east-1)
            path_prefix: Path inside the bucket this secret can access
            access_key_id: AWS IAM access key
            secret_access_key: AWS IAM secret key
            endpoint: Optional S3 endpoint override (defaults to region-based)
        """
        if endpoint is None:
            endpoint = f"s3.{region}.amazonaws.com"

        payload = {
            "name": name,
            "type": "S3",
            "bucket": bucket,
            "endpoint": endpoint,
            "region": region,
            "pathPrefix": path_prefix,
            "data": {
                "AWS_ACCESS_KEY_ID": access_key_id,
                "AWS_SECRET_ACCESS_KEY": secret_access_key,
            },
        }
        code, body = self._request("POST", "/v2/admin/objectStoreSecrets", json_body=payload)
        if code not in (200, 201):
            raise RuntimeError(f"HTTP {code}: {body}")
        return body

    def delete_object_store_secret(self, name):
        """Delete an object store secret."""
        code, body = self._request("DELETE", f"/v2/admin/objectStoreSecrets/{name}")
        if code not in (200, 204):
            raise RuntimeError(f"HTTP {code}: {body}")
        return body

    # Scenarios

    def list_scenarios(self):
        """List scenarios in the current resource group."""
        code, body = self._request("GET", "/v2/lm/scenarios")
        if code != 200:
            raise RuntimeError(f"HTTP {code}: {body}")
        return body.get("resources", [])

    # Configurations

    def list_configurations(self):
        """List configurations in the current resource group."""
        code, body = self._request("GET", "/v2/lm/configurations")
        if code != 200:
            raise RuntimeError(f"HTTP {code}: {body}")
        return body.get("resources", [])

    # Executions

    def list_executions(self):
        """List executions in the current resource group."""
        code, body = self._request("GET", "/v2/lm/executions")
        if code != 200:
            raise RuntimeError(f"HTTP {code}: {body}")
        return body.get("resources", [])

    # Deployments

    def list_deployments(self):
        """List deployments in the current resource group."""
        code, body = self._request("GET", "/v2/lm/deployments")
        if code != 200:
            raise RuntimeError(f"HTTP {code}: {body}")
        return body.get("resources", [])

    def stop_deployment(self, deployment_id):
        """Stop a running deployment to save cost."""
        code, body = self._request(
            "PATCH",
            f"/v2/lm/deployments/{deployment_id}",
            json_body={"targetStatus": "STOPPED"},
        )
        if code not in (200, 202):
            raise RuntimeError(f"HTTP {code}: {body}")
        return body

    # Applications (GitHub sync)

    def list_applications(self):
        """List applications (Git sync points) in the current resource group."""
        code, body = self._request("GET", "/v2/admin/applications")
        if code != 200:
            raise RuntimeError(f"HTTP {code}: {body}")
        return body.get("resources", [])
