#!/usr/bin/env python3
"""
Interactive RAG chatbot for Vendor MDQ Copilot.

Flow per question:
  1. Embed question via Text Embedding 3 Small
  2. Query HANA POLICY_CHUNKS with COSINE_SIMILARITY to find top 3 relevant chunks
  3. Also search QUALITY_ISSUES for similar past issue narratives (top 2)
  4. Build grounded prompt: question + retrieved context
  5. Call Claude Sonnet deployment
  6. Return answer with sources

Env vars required (same as script 06):
  HANA_HOST, HANA_PORT, HANA_USER, HANA_PASSWORD
  AI_CORE_URL, AI_CORE_AUTH_URL, AI_CORE_CLIENT_ID, AI_CORE_CLIENT_SECRET, AI_CORE_RG
  DEPLOY_ID_OPENAI       text embedding 3 small
  DEPLOY_ID_CLAUDE       claude sonnet 4.8 deployment id

Run:
  python 07_rag_demo.py
"""

import os
import sys
import base64
import json
import requests
from hdbcli import dbapi

HANA_HOST = os.environ.get("HANA_HOST")
HANA_PORT = int(os.environ.get("HANA_PORT", "443"))
HANA_USER = os.environ.get("HANA_USER", "DBADMIN")
HANA_PASSWORD = os.environ.get("HANA_PASSWORD")

AI_CORE_URL = os.environ.get("AI_CORE_URL")
AI_CORE_AUTH_URL = os.environ.get("AI_CORE_AUTH_URL")
AI_CORE_CLIENT_ID = os.environ.get("AI_CORE_CLIENT_ID")
AI_CORE_CLIENT_SECRET = os.environ.get("AI_CORE_CLIENT_SECRET")
AI_CORE_RG = os.environ.get("AI_CORE_RG", "default")

DEPLOY_ID_OPENAI = os.environ.get("DEPLOY_ID_OPENAI")
DEPLOY_ID_CLAUDE = os.environ.get("DEPLOY_ID_CLAUDE", "dd788f40815279d1")

TOP_K_POLICY = 3
TOP_K_ISSUES = 2

missing = [k for k in ["HANA_HOST", "HANA_PASSWORD", "AI_CORE_URL",
                       "AI_CORE_AUTH_URL", "AI_CORE_CLIENT_ID",
                       "AI_CORE_CLIENT_SECRET", "DEPLOY_ID_OPENAI",
                       "DEPLOY_ID_CLAUDE"] if not os.environ.get(k)]
if missing:
    print(f"ERROR: missing env vars: {', '.join(missing)}")
    sys.exit(1)


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


def embed_openai(text, token):
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


def ask_claude(prompt, token):
    """Call Claude Sonnet via SAP AI Core using Anthropic Messages API format."""
    url = f"{AI_CORE_URL}/v2/inference/deployments/{DEPLOY_ID_CLAUDE}/invoke"
    r = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "AI-Resource-Group": AI_CORE_RG,
            "Content-Type": "application/json"
        },
        json={
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1500,
            "messages": [{"role": "user", "content": prompt}]
        },
        timeout=90
    )
    r.raise_for_status()
    data = r.json()
    # Response shape: {"content": [{"text": "..."}], ...}
    if "content" in data and isinstance(data["content"], list):
        return data["content"][0].get("text", "")
    return json.dumps(data)[:500]


def vec_literal(vec):
    inner = ",".join(f"{v:.7f}" for v in vec)
    return f"[{inner}]"


def retrieve_from_hana(cursor, query_vec):
    v = vec_literal(query_vec)

    # Top policy chunks
    cursor.execute(f"""
        SELECT TOP {TOP_K_POLICY}
               POLICY_NAME, SECTION_NAME, CHUNK_TEXT,
               COSINE_SIMILARITY(CHUNK_VEC_OPENAI, TO_REAL_VECTOR('{v}')) AS SIM
        FROM POLICY_CHUNKS
        WHERE CHUNK_VEC_OPENAI IS NOT NULL
        ORDER BY SIM DESC
    """)
    policy_hits = cursor.fetchall()

    # Top past issues
    cursor.execute(f"""
        SELECT TOP {TOP_K_ISSUES}
               ISSUE_ID, VENDOR_ID, RULE_ID, STATUS, DESCRIPTION, RESOLUTION_NOTES,
               COSINE_SIMILARITY(DESC_VEC_OPENAI, TO_REAL_VECTOR('{v}')) AS SIM
        FROM QUALITY_ISSUES
        WHERE DESC_VEC_OPENAI IS NOT NULL
        ORDER BY SIM DESC
    """)
    issue_hits = cursor.fetchall()
    return policy_hits, issue_hits


def build_prompt(question, policy_hits, issue_hits):
    policy_ctx = "\n\n".join(
        f"[Source: {p[0]} - {p[1]} (similarity {float(p[3]):.2f})]\n{str(p[2])[:1200]}"
        for p in policy_hits
    )
    issue_ctx = "\n\n".join(
        f"[Past Issue {i[0]} on vendor {i[1]}, rule {i[2]}, status {i[3]}]\n"
        f"Description: {str(i[4])[:400]}\n"
        f"Resolution: {str(i[5])[:400] if i[5] else 'open'}"
        for i in issue_hits
    )

    return f"""You are a Vendor Master Data Quality assistant for an SAP enterprise.
Answer the user question using ONLY the provided policy excerpts and past issue history below.
If the information is not in the context, say so plainly. Cite the policy sections when relevant.

===== RELEVANT POLICY SECTIONS =====
{policy_ctx}

===== SIMILAR PAST ISSUES =====
{issue_ctx}

===== USER QUESTION =====
{question}

Answer concisely with references:"""


def main():
    print("Vendor MDQ Copilot - interactive RAG demo")
    print("Type a question (or 'quit' to exit)\n")

    print("Connecting to HANA ...")
    conn = dbapi.connect(
        address=HANA_HOST, port=HANA_PORT,
        user=HANA_USER, password=HANA_PASSWORD,
        encrypt=True, sslValidateCertificate=False
    )
    cursor = conn.cursor()
    print("HANA connected")

    print("Getting AI Core token ...")
    token = get_token()
    print("Token acquired\n")

    while True:
        try:
            question = input("Question: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not question or question.lower() in ("quit", "exit", "q"):
            break

        try:
            print("  Embedding question ...")
            qvec = embed_openai(question, token)

            print("  Retrieving from HANA ...")
            policy_hits, issue_hits = retrieve_from_hana(cursor, qvec)

            print(f"  Found {len(policy_hits)} policy chunks, {len(issue_hits)} past issues")
            for p in policy_hits:
                print(f"    - {p[0]} :: {p[1]} (sim {float(p[3]):.2f})")

            print("  Calling Claude Sonnet ...")
            prompt = build_prompt(question, policy_hits, issue_hits)
            answer = ask_claude(prompt, token)

            print("\n===== ANSWER =====")
            print(answer)
            print("==================\n")

        except requests.HTTPError as e:
            print(f"HTTP error: {e}")
            if e.response is not None and e.response.status_code == 401:
                print("Refreshing token ...")
                token = get_token()
        except Exception as e:
            print(f"Error: {e}")

    cursor.close()
    conn.close()
    print("Goodbye")


if __name__ == "__main__":
    main()
