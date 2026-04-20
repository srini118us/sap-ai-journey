"""SAP GenAI Hub embedding client.

Thin wrapper around `gen_ai_hub.proxy.native.openai.embeddings` that matches
Lab 52's pattern exactly. The SDK reads AICORE_* env vars automatically.

Reads:
    - AICORE_AUTH_URL (auto-picked up by SDK)
    - AICORE_CLIENT_ID (auto-picked up by SDK)
    - AICORE_CLIENT_SECRET (auto-picked up by SDK)
    - AICORE_BASE_URL (auto-picked up by SDK)
    - AICORE_RESOURCE_GROUP (auto-picked up by SDK)
    - GENAI_HUB_DEPLOYMENT_ID_EMBEDDING (this module reads it explicitly)
"""
import os
import logging

logger = logging.getLogger(__name__)

EXPECTED_DIMENSIONS = 1536


def embed_text(text: str) -> list[float]:
    """Generate a 1536-dim embedding for the given text.

    Args:
        text: The text to embed (user query, typically).

    Returns:
        List of 1536 floats (matching HANA REAL_VECTOR(1536) column).
    """
    if not text or not text.strip():
        raise ValueError("Cannot embed empty text")

    deployment_id = os.getenv("GENAI_HUB_DEPLOYMENT_ID_EMBEDDING")
    if not deployment_id:
        raise RuntimeError(
            "GENAI_HUB_DEPLOYMENT_ID_EMBEDDING not set in .env"
        )

    # Lazy import so credential validation can surface env errors first
    from gen_ai_hub.proxy.native.openai import embeddings

    logger.info("[GENAI] Embedding via deployment %s", deployment_id)
    response = embeddings.create(
        input=text,
        deployment_id=deployment_id,
    )

    vector = response.data[0].embedding

    if len(vector) != EXPECTED_DIMENSIONS:
        raise ValueError(
            f"Expected {EXPECTED_DIMENSIONS}-dim embedding, got {len(vector)}. "
            f"Wrong model deployment?"
        )
    return vector
