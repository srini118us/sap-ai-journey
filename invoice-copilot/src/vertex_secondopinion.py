"""Cross-cloud second-opinion extraction: a Gemini agent on Google Cloud Run.

The only module in this project that touches Google Cloud auth, so there is
one place to change when the credential pattern moves -- the same role
`genai.py` plays for GenAI Hub chat and `rpt.py` plays for RPT-1.5.

This is the one deliberate exception to "all model calls go through SAP AI
Core", and it is a narrow one. The SAP path is unchanged: `extract` still runs
through GenAI Hub and remains the primary extraction. This module exists only
so a second, independently-built extractor can be compared against it -- two
disagreeing readings of the same invoice are a signal worth having. It never
becomes the primary. See CLAUDE.md.

Note that this project still does not call a model provider directly: it calls
your Cloud Run service, which holds the Gemini credentials and makes that call
server-side. What crosses this boundary is an invoice text in and extracted
fields out.

    POST {VERTEX_EXTRACT_URL}  {"text": ...} -> {"extracted": bool, "fields": {...}}

The endpoint is private, so the call needs a Google-signed identity token whose
audience is the endpoint itself. That token is minted here from a service
account key, which arrives base64-encoded in GCP_SA_KEY_B64.

Transport and auth only. No comparison logic and no trace entries live here --
those belong to the caller, the same way `genai.py` leaves parsing to the node.

GCP_SA_KEY_B64 decodes to a JSON document containing a private key. It is
never printed and never appears in the errors raised here -- the decode path
reports exception type names only, and the HTTP paths report status codes. The
minted token is treated the same way.
"""

import base64
import binascii
import json
import os
import time
from datetime import timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

# NOTE: `google.oauth2` and `google.auth.transport.requests` are deliberately
# NOT imported at module level, for the reason `genai.py` keeps its SDK import
# inside complete(): google-auth is a dependency this project has only for
# this one module, and a module-level import would make importing this file
# fail outright where it is not installed -- before any caller can catch it.
# Importing inside the functions keeps every failure a catchable
# VertexSecondOpinionError.

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# The model behind the endpoint, for the caller's trace. The URL says nothing
# about which model is serving it.
MODEL_NAME = "gemini-via-cloud-run"

REQUEST_TIMEOUT_SECONDS = 120

# Refresh a little before the token actually expires, so a call never starts
# with a token that dies mid-flight. ID tokens last about an hour.
TOKEN_EXPIRY_MARGIN_SECONDS = 60
DEFAULT_TOKEN_LIFETIME_SECONDS = 3600


class VertexSecondOpinionError(RuntimeError):
    """The second-opinion extraction could not be completed.

    Raised for missing configuration, a malformed service account key, token
    minting failures, network errors, non-2xx responses, and unparseable
    bodies alike -- callers treat them the same way: trace it, and carry on
    with the SAP extraction alone. A second opinion that cannot be obtained is
    a missing comparison, never a failed invoice.

    An endpoint that ran and found nothing is NOT this: that comes back as
    {"extracted": False}. See extract_fields().
    """


# One token serves many invoices; tokens last about an hour. Minting one per
# call would double the request count for no benefit.
_token_cache = {"value": None, "expires_at": 0.0}


def _require(name: str) -> str:
    """Read a required setting, naming the missing key rather than its value."""
    value = os.getenv(name)
    if not value:
        raise VertexSecondOpinionError(f"{name} is not set; add it to .env (see .env.example).")
    return value


def endpoint_url() -> str:
    """The Cloud Run endpoint, which is also the identity token's audience.

    Read from .env rather than hardcoded: it carries a GCP project number,
    which is an environment-specific system identifier this repo keeps out of
    source -- the same treatment RPT_DEPLOYMENT_ID gets. Keeping it in one
    place also keeps the URL called and the audience signed for from drifting
    apart, which would fail as a 403 with nothing obvious to look at.
    """
    return _require("VERTEX_EXTRACT_URL").rstrip("/")


def _service_account_info() -> dict:
    """Decode GCP_SA_KEY_B64 into the service account key dict.

    Reports only what went wrong, never any part of the decoded content: this
    document holds a private key.
    """
    raw = _require("GCP_SA_KEY_B64")

    try:
        decoded = base64.b64decode(raw, validate=True)
    except (binascii.Error, ValueError) as e:
        # No type name here: binascii.Error renders as a bare "Error", which
        # tells the reader less than the sentence already does.
        raise VertexSecondOpinionError(
            "GCP_SA_KEY_B64 is not valid base64; re-encode the service account key JSON."
        ) from e

    try:
        info = json.loads(decoded)
    except (ValueError, UnicodeDecodeError) as e:
        raise VertexSecondOpinionError(
            f"GCP_SA_KEY_B64 did not decode to JSON ({type(e).__name__}); "
            "it should be the base64 of a service account key file."
        ) from e

    if not isinstance(info, dict):
        raise VertexSecondOpinionError(
            f"GCP_SA_KEY_B64 decoded to {type(info).__name__}, expected a JSON object."
        )

    # Named, not dumped: knowing which key is absent is the whole diagnostic,
    # and the values are secret.
    missing = [k for k in ("client_email", "private_key", "token_uri") if not info.get(k)]
    if missing:
        raise VertexSecondOpinionError(
            f"Service account key is missing required field(s): {', '.join(missing)}."
        )

    return info


def _id_token() -> str:
    """Mint a Google identity token for the endpoint, reusing the cached one.

    An *identity* token, not an access token: Cloud Run authorizes callers on
    the signed audience, so the token has to name the endpoint it is being
    presented to.
    """
    now = time.time()
    if _token_cache["value"] and now < _token_cache["expires_at"]:
        return _token_cache["value"]

    audience = endpoint_url()
    info = _service_account_info()

    try:
        from google.auth.transport.requests import Request
        from google.oauth2 import service_account
    except ImportError as e:
        raise VertexSecondOpinionError(
            "google-auth is not installed; pip install -r requirements.txt."
        ) from e

    try:
        credentials = service_account.IDTokenCredentials.from_service_account_info(
            info, target_audience=audience
        )
    except (ValueError, KeyError, TypeError) as e:
        raise VertexSecondOpinionError(
            f"Service account key was not usable: {type(e).__name__}."
        ) from e

    try:
        credentials.refresh(Request())
    except Exception as e:  # noqa: BLE001 -- google-auth raises several unrelated types here
        # Deliberately type-only: a failed token exchange can echo the request
        # back in its message, and that request is signed with the private key.
        raise VertexSecondOpinionError(
            f"Could not mint an identity token for the endpoint: {type(e).__name__}."
        ) from e

    if not credentials.token:
        raise VertexSecondOpinionError("Token minting reported success but returned no token.")

    expiry = getattr(credentials, "expiry", None)
    lifetime = DEFAULT_TOKEN_LIFETIME_SECONDS
    if expiry is not None:
        # google-auth stores a *naive UTC* datetime here, and a naive
        # datetime's .timestamp() is interpreted as local time -- so the
        # timezone has to be attached explicitly. Without it the lifetime
        # comes out wrong by the local UTC offset, which east of Greenwich
        # means every token looks already expired and the cache never hits.
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        lifetime = expiry.timestamp() - time.time()

    _token_cache["value"] = credentials.token
    _token_cache["expires_at"] = now + max(lifetime - TOKEN_EXPIRY_MARGIN_SECONDS, 0)
    return credentials.token


def extract_fields(text: str) -> dict:
    """Ask the Gemini agent to extract fields from one invoice text.

    Returns the endpoint's own verdict, unmassaged:

        {"extracted": bool, "fields": dict, "endpoint": str, "model": str}

    `extracted: False` is a *return value*, not an error. It is the endpoint
    saying it ran and found nothing -- the second-opinion analogue of the
    `parse_failed` outcome on the SAP side, and a different fact from "the
    endpoint could not be reached". Collapsing the two would make a silent
    failure look like an empty invoice.

    Raises VertexSecondOpinionError for everything that stops an answer coming
    back: missing config, a bad key, token failure, network error, non-2xx, or
    a body that is not the documented shape.

    The returned `fields` are passed through as the endpoint sent them. No
    normalization onto this project's field names happens here -- comparing
    two extractions is the caller's decision to make, and a transport module
    that quietly reshaped one side of the comparison would be the wrong place
    for it.
    """
    if not isinstance(text, str) or not text.strip():
        raise VertexSecondOpinionError(
            f"No invoice text to send: got {type(text).__name__}, expected a non-empty string."
        )

    url = endpoint_url()

    try:
        response = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {_id_token()}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            json={"text": text},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except requests.RequestException as e:
        raise VertexSecondOpinionError(
            f"Could not reach the second-opinion endpoint: {type(e).__name__}."
        ) from e

    if response.status_code in (401, 403):
        # The likely causes are worth naming: this is the failure that looks
        # like a code bug and is almost always a configuration one.
        raise VertexSecondOpinionError(
            f"Endpoint refused the identity token with HTTP {response.status_code}; "
            "check that the service account has roles/run.invoker on the service and "
            "that VERTEX_EXTRACT_URL matches the audience exactly."
        )

    if response.status_code != 200:
        raise VertexSecondOpinionError(
            f"Endpoint returned HTTP {response.status_code}: {response.text[:200]}"
        )

    try:
        body = response.json()
    except ValueError as e:
        raise VertexSecondOpinionError(
            f"Endpoint response was not JSON: {type(e).__name__}."
        ) from e

    if not isinstance(body, dict):
        raise VertexSecondOpinionError(
            f"Endpoint returned JSON of type {type(body).__name__}, expected an object."
        )

    extracted = body.get("extracted")
    if not isinstance(extracted, bool):
        raise VertexSecondOpinionError(
            f"Endpoint response carried no boolean `extracted` flag (got "
            f"{type(extracted).__name__}); cannot tell success from failure."
        )

    fields = body.get("fields")
    if extracted and not isinstance(fields, dict):
        raise VertexSecondOpinionError(
            f"Endpoint reported extracted=true but `fields` is {type(fields).__name__}, "
            "expected an object."
        )

    return {
        "extracted": extracted,
        "fields": fields if isinstance(fields, dict) else {},
        "endpoint": url,
        "model": MODEL_NAME,
    }
