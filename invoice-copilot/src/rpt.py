"""SAP RPT-1.5 access: tabular prediction on SAP AI Core.

The only module that talks to the RPT-1.5 deployment, so there is one place to
change when the call pattern moves -- the same role `genai.py` plays for the
GenAI Hub chat calls.

This is deliberately NOT part of genai.py. RPT-1.5 is not reached through the
GenAI Hub proxy at all: the `gen_ai_hub` SDK ships chat and embedding clients
only, and has no tabular client. RPT-1.5 is a plain AI Core inference
deployment, called over REST with an OAuth token this module fetches itself.
Different protocol, different auth, different failure surface.

    POST {AICORE_BASE_URL}/inference/deployments/{RPT_DEPLOYMENT_ID}/predict

RPT-1.5 predicts in context: there is no training run. Every call carries
labeled context rows teaching it the pattern, plus query rows whose target
cell holds PREDICT_PLACEHOLDER. It fills those cells in and returns a
confidence for each candidate value.

Credentials come from the project's .env and are never printed -- including in
the errors raised here. The token request in particular reports only its HTTP
status, never its body.
"""

import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# The deployed model, for the trace. The deployment id itself says nothing
# about which model is behind it.
MODEL_NAME = "sap-rpt-1.5"

# The value RPT-1.5 looks for to decide which cells it is being asked to fill.
PREDICT_PLACEHOLDER = "[PREDICT]"

REQUEST_TIMEOUT_SECONDS = 120
TOKEN_TIMEOUT_SECONDS = 30

# Refresh a little before the token actually expires, so a call never starts
# with a token that dies mid-flight.
TOKEN_EXPIRY_MARGIN_SECONDS = 60


class RPTError(RuntimeError):
    """The RPT-1.5 prediction could not be completed.

    Raised for missing configuration, auth failures, network errors, non-2xx
    responses, and error payloads returned under HTTP 200 alike -- callers
    treat them the same way: trace it and route the invoice to a human.
    """


# One token serves many invoices; tokens last hours. Fetching one per call
# would triple the request count for no benefit.
_token_cache = {"value": None, "expires_at": 0.0}


def _require(name: str) -> str:
    """Read a required setting, naming the missing key rather than its value."""
    value = os.getenv(name)
    if not value:
        raise RPTError(f"{name} is not set; add it to .env (see .env.example).")
    return value


def deployment_id() -> str:
    """The AI Core deployment serving RPT-1.5."""
    return _require("RPT_DEPLOYMENT_ID")


def _token() -> str:
    """Fetch an OAuth token, reusing the cached one until it is nearly stale."""
    now = time.time()
    if _token_cache["value"] and now < _token_cache["expires_at"]:
        return _token_cache["value"]

    auth_url = _require("AICORE_AUTH_URL").rstrip("/") + "/oauth/token"
    try:
        response = requests.post(
            auth_url,
            data={"grant_type": "client_credentials"},
            auth=(_require("AICORE_CLIENT_ID"), _require("AICORE_CLIENT_SECRET")),
            timeout=TOKEN_TIMEOUT_SECONDS,
        )
    except requests.RequestException as e:
        raise RPTError(f"Could not reach the auth server: {type(e).__name__}") from e

    # Deliberately status-only: the body of a failed token request is not
    # something to put in a trace.
    if response.status_code != 200:
        raise RPTError(f"Auth failed with HTTP {response.status_code}.")

    try:
        payload = response.json()
        token = payload["access_token"]
        expires_in = float(payload.get("expires_in", 3600))
    except (ValueError, KeyError, TypeError) as e:
        raise RPTError(f"Auth response was not usable: {type(e).__name__}") from e

    _token_cache["value"] = token
    _token_cache["expires_at"] = now + max(expires_in - TOKEN_EXPIRY_MARGIN_SECONDS, 0)
    return token


def predict(rows: list[dict], target_column: str, index_column: str, top_k: int = 3) -> dict:
    """Run one tabular prediction and return the parsed response body.

    `rows` is context rows (target column holding a known label) followed by
    query rows (target column holding PREDICT_PLACEHOLDER). `top_k` asks for
    that many candidate values per predicted cell, which is what turns a bare
    label into a distribution the caller can score with.

    Raises RPTError for anything that stops a prediction coming back: missing
    config, auth failure, network error, non-2xx, an unparseable body, or an
    error reported in the body under HTTP 200.
    """
    url = f"{_require('AICORE_BASE_URL').rstrip('/')}/inference/deployments/{deployment_id()}/predict"

    payload = {
        "prediction_config": {
            "target_columns": [
                {
                    "name": target_column,
                    "prediction_placeholder": PREDICT_PLACEHOLDER,
                    "task_type": "classification",
                    "top_k": top_k,
                }
            ],
            # Explanations are why RPT-1.5 can be audited rather than just
            # believed: the column scores say what drove the prediction.
            "explanations": {"top_column_scores": 3, "top_relevant_context_rows": 2},
        },
        "index_column": index_column,
        "rows": rows,
    }

    try:
        response = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {_token()}",
                "AI-Resource-Group": os.getenv("AICORE_RESOURCE_GROUP", "default"),
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            json=payload,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except requests.RequestException as e:
        raise RPTError(f"Could not reach the RPT-1.5 deployment: {type(e).__name__}") from e

    if response.status_code != 200:
        raise RPTError(f"RPT-1.5 returned HTTP {response.status_code}: {response.text[:200]}")

    try:
        body = response.json()
    except ValueError as e:
        raise RPTError(f"RPT-1.5 response was not JSON: {type(e).__name__}") from e

    # A 200 can still carry a failure: the status lives in the body.
    status = body.get("status") or {}
    if status.get("code", 0) != 0:
        raise RPTError(f"RPT-1.5 reported an error: {status.get('message', status)}")

    if not isinstance(body.get("predictions"), list):
        raise RPTError("RPT-1.5 response carried no predictions list.")

    return body
