"""SAP GenAI Hub access.

The only module in this project that imports the GenAI Hub SDK, so there is
one place to change when the call pattern or the SDK moves.

Call pattern taken from the proven Stage 1 script (../ai-core-test/app.py):
gen_ai_hub.proxy.native.openai chat completions, credentials from .env, model
deployment named by MODEL_NAME.

Credentials are read from the project's .env by the SDK itself:
AICORE_AUTH_URL, AICORE_BASE_URL, AICORE_CLIENT_ID, AICORE_CLIENT_SECRET,
AICORE_RESOURCE_GROUP. They are never hardcoded here and never printed --
including in the error messages this module raises.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# NOTE: `gen_ai_hub.proxy.native.openai.chat` is deliberately NOT imported at
# module level. Accessing that attribute constructs the AI Core proxy client,
# which reads the credentials immediately -- so a module-level import raises
# at import time when .env is missing, before any node can catch it. Importing
# inside complete() keeps every failure catchable and keeps this module safe
# to import without credentials.

# Load this project's .env explicitly rather than whatever load_dotenv() finds
# by walking up from the current working directory.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

DEFAULT_MODEL = "gpt-4o-mini"


class GenAIHubError(RuntimeError):
    """The GenAI Hub call could not be completed.

    Raised for missing credentials, auth failures, network errors, and bad
    deployments alike -- callers treat them the same way: trace it and route
    the invoice to a human.
    """


def model_name() -> str:
    """The GenAI Hub deployment to call."""
    return os.getenv("MODEL_NAME", DEFAULT_MODEL)


def complete(messages: list[dict], max_tokens: int = 1500, temperature: float = 0.0) -> str:
    """Run a chat completion and return the message content.

    temperature defaults to 0.0: extraction should be reproducible, not
    creative.
    """
    try:
        from gen_ai_hub.proxy.native.openai import chat  # constructs the proxy client

        response = chat.completions.create(
            model_name=model_name(),
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
    except Exception as e:  # noqa: BLE001 -- every failure mode routes the same way
        raise GenAIHubError(f"{type(e).__name__}: {e}") from e

    return response.choices[0].message.content
