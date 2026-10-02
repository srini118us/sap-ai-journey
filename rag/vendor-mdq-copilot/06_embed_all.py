#!/usr/bin/env python3
"""
Populate REAL_VECTOR columns using both embedding models.
Reads text from VENDORS, QUALITY_ISSUES, POLICY_CHUNKS.
Calls NVIDIA Llama 3.2 NV EmbedQA 1b (2048 dim) AND Text Embedding 3 Small (1536 dim).
Writes vectors to DESC_VEC_NVIDIA, DESC_VEC_OPENAI, CHUNK_VEC_NVIDIA, CHUNK_VEC_OPENAI.

Env vars required:
  HANA_HOST, HANA_PORT, HANA_USER, HANA_PASSWORD  (HANA connection)
  AI_CORE_URL           https://api.ai.prod.us-east-1.aws.ml.hana.ondemand.com
  AI_CORE_AUTH_URL      https://ai-core-us.authentication.us10.hana.ondemand.com/oauth/token
  AI_CORE_CLIENT_ID     from AI Core service key
  AI_CORE_CLIENT_SECRET from AI Core service key
  AI_CORE_RG            resource group (default: default)
  DEPLOY_ID_NVIDIA      d640418916259ce4
  DEPLOY_ID_OPENAI      d244bc327afbffbe

Install:
  pip install hdbcli requests

Run:
  python 06_embed_all.py
"""

import os
import sys
import time
import base64
import requests
from hdbcli import dbapi

# ==========================================================
# Config
# ==========================================================
HANA_HOST = os.environ.get("HANA_HOST")
HANA_PORT = int(os.environ.get("HANA_PORT", "443"))
HANA_USER = os.environ.get("HANA_USER", "DBADMIN")
HANA_PASSWORD = os.environ.get("HANA_PASSWORD")

AI_CORE_URL = os.environ.get("AI_CORE_URL", "https://api.ai.prod.us-east-1.aws.ml.hana.ondemand.com")
AI_CORE_AUTH_URL = os.environ.get("AI_CORE_AUTH_URL")
AI_CORE_CLIENT_ID = os.environ.get("AI_CORE_CLIENT_ID")
AI_CORE_CLIENT_SECRET = os.environ.get("AI_CORE_CLIENT_SECRET")
AI_CORE_RG = os.environ.get("AI_CORE_RG", "default")

DEPLOY_ID_NVIDIA = os.environ.get("DEPLOY_ID_NVIDIA", "d640418916259ce4")
DEPLOY_ID_OPENAI = os.environ.get("DEPLOY_ID_OPENAI", "d244bc327afbffbe")

BATCH_SIZE = 20            # rows fetched per DB batch
EMBED_SLEEP = 0.3          # gentle pause between embedding calls to avoid 429
CHECKPOINT_EVERY = 20      # commit every N rows

# Check requirements
missing = [k for k in ["HANA_HOST", "HANA_PASSWORD", "AI_CORE_AUTH_URL",
                       "AI_CORE_CLIENT_ID", "AI_CORE_CLIENT_SECRET"]
           if not os.environ.get(k)]
if missing:
    print(f"ERROR: missing env vars: {', '.join(missing)}")
    sys.exit(1)


# ==========================================================
# AI Core token
# ==========================================================
def get_token():
    auth = base64.b64encode(f"{AI_CORE_CLIENT_ID}:{AI_CORE_CLIENT_SECRET}".encode()).decode()
    r = requests.post(
        AI_CORE_AUTH_URL,
        headers={"Authorization": f"Basic {auth}"},
        data={"grant_type": "client_credentials"},
        timeout=30
    )
    r.raise_for_status()
    return r.json()["access_token"]


# ==========================================================
# Embedding calls
# ==========================================================
def embed_openai(text, token):
    """Text Embedding 3 Small via Azure OpenAI executable."""
    url = f"{AI_CORE_URL}/v2/inference/deployments/{DEPLOY_ID_OPENAI}/embeddings?api-version=2024-08-01-preview"
    r = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "AI-Resource-Group": AI_CORE_RG,
            "Content-Type": "application/json"
        },
        json={"input": text},
        timeout=60
    )
    r.raise_for_status()
    return r.json()["data"][0]["embedding"]


_NVIDIA_URL_CACHE = None

def get_nvidia_deployment_url(token):
    global _NVIDIA_URL_CACHE
    if _NVIDIA_URL_CACHE:
        return _NVIDIA_URL_CACHE
    r = requests.get(
        f"{AI_CORE_URL}/v2/lm/deployments/{DEPLOY_ID_NVIDIA}",
        headers={"Authorization": f"Bearer {token}", "AI-Resource-Group": AI_CORE_RG},
        timeout=30
    )
    r.raise_for_status()
    _NVIDIA_URL_CACHE = r.json()["deploymentUrl"]
    return _NVIDIA_URL_CACHE

def embed_nvidia(text, token):
    url = get_nvidia_deployment_url(token) + "/embeddings"
    r = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "AI-Resource-Group": AI_CORE_RG,
            "Content-Type": "application/json"
        },
        json={
            "input": [text],
            "model": "nvidia--llama-3.2-nv-embedqa-1b",
            "input_type": "passage",
            "encoding_format": "float",
            "truncate": "NONE"
        },
        timeout=60
    )
    r.raise_for_status()
    return r.json()["data"][0]["embedding"]


def to_vec_literal(vec):
    """Format Python list of floats as HANA TO_REAL_VECTOR literal."""
    inner = ",".join(f"{v:.7f}" for v in vec)
    return f"[{inner}]"


# ==========================================================
# Per table embedding driver
# ==========================================================
def embed_table(conn, cursor, table, id_col, text_col, vec_col_nvidia, vec_col_openai, token):
    print(f"\n===== Embedding {table} =====")

    # Count rows needing embedding
    cursor.execute(f"""
        SELECT COUNT(*) FROM {table}
        WHERE {vec_col_nvidia} IS NULL OR {vec_col_openai} IS NULL
    """)
    total = cursor.fetchone()[0]
    if total == 0:
        print(f"  All rows already embedded, skipping")
        return
    print(f"  Rows to embed: {total}")

    # Fetch IDs and text
    cursor.execute(f"""
        SELECT {id_col}, {text_col}
        FROM {table}
        WHERE ({vec_col_nvidia} IS NULL OR {vec_col_openai} IS NULL)
          AND {text_col} IS NOT NULL
        ORDER BY {id_col}
    """)
    rows = cursor.fetchall()

    processed = 0
    errors = 0
    for row_id, text_content in rows:
        text_str = str(text_content) if text_content else ""
        if not text_str.strip():
            continue
        # Truncate very long text to avoid embedding limits
        text_str = text_str[:8000]
        try:
            vec_nvidia = embed_nvidia(text_str, token)
            time.sleep(EMBED_SLEEP)
            vec_openai = embed_openai(text_str, token)
            time.sleep(EMBED_SLEEP)

            update_sql = f"""
                UPDATE {table}
                SET {vec_col_nvidia} = TO_REAL_VECTOR('{to_vec_literal(vec_nvidia)}'),
                    {vec_col_openai} = TO_REAL_VECTOR('{to_vec_literal(vec_openai)}')
                WHERE {id_col} = ?
            """
            cursor.execute(update_sql, (row_id,))
            processed += 1

            if processed % CHECKPOINT_EVERY == 0:
                conn.commit()
                print(f"  Progress: {processed}/{total}")
        except requests.HTTPError as e:
            errors += 1
            code = e.response.status_code if e.response else "?"
            print(f"  ERROR row {row_id} (HTTP {code}): {str(e)[:80]}")
            if code == 401:
                print("  Token expired, refreshing")
                token = get_token()
            elif code == 429:
                print("  Rate limited, sleeping 30s")
                time.sleep(30)
        except Exception as e:
            errors += 1
            print(f"  ERROR row {row_id}: {str(e)[:80]}")

    conn.commit()
    print(f"  Complete: {processed} embedded, {errors} errors")


# ==========================================================
# Main
# ==========================================================
def main():
    print("Getting AI Core token")
    token = get_token()
    print(f"Token acquired ({len(token)} chars)")

    # Test both endpoints with a probe
    print("\nProbing both embedding endpoints")
    try:
        probe = embed_openai("test", token)
        print(f"  OpenAI OK, dim={len(probe)}")
    except Exception as e:
        print(f"  OpenAI FAILED: {e}")
        sys.exit(1)
    try:
        probe = embed_nvidia("test", token)
        print(f"  NVIDIA OK, dim={len(probe)}")
    except Exception as e:
        print(f"  NVIDIA FAILED: {e}")
        sys.exit(1)

    print(f"\nConnecting to HANA {HANA_HOST}")
    conn = dbapi.connect(
        address=HANA_HOST,
        port=HANA_PORT,
        user=HANA_USER,
        password=HANA_PASSWORD,
        encrypt=True,
        sslValidateCertificate=False
    )
    cursor = conn.cursor()

    embed_table(conn, cursor, "VENDORS", "VENDOR_ID", "DESCRIPTION",
                "DESC_VEC_NVIDIA", "DESC_VEC_OPENAI", token)

    embed_table(conn, cursor, "QUALITY_ISSUES", "ISSUE_ID", "DESCRIPTION",
                "DESC_VEC_NVIDIA", "DESC_VEC_OPENAI", token)

    embed_table(conn, cursor, "POLICY_CHUNKS", "CHUNK_ID", "CHUNK_TEXT",
                "CHUNK_VEC_NVIDIA", "CHUNK_VEC_OPENAI", token)

    cursor.close()
    conn.close()
    print("\nDONE. All vectors populated.")


if __name__ == "__main__":
    main()
