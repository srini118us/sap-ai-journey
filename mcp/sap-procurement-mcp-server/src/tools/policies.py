"""Policy semantic search tool.

Embeds the user query and runs COSINE_SIMILARITY against POLICY_CHUNKS.
Column names match Lab 52's actual schema (hana-implementation/01_schema/create_schema.sql).
"""
import os
import logging
from typing import Any

from src.hana import get_cursor
from src.genai import embed_text

logger = logging.getLogger(__name__)


def search_policies(query: str, max_results: int = 5) -> dict[str, Any]:
    """Semantic search on procurement policy chunks.

    Args:
        query: Natural language query (e.g., "approval limits for consulting services").
        max_results: Maximum chunks to return (default 5, cap 10).

    Returns:
        Dict with:
            - query: Echo of input for trace
            - results: List of {chunk_id, doc_id, doc_title, section_header, chunk_text, similarity}
            - count: Number of results returned
    """
    if not query or not query.strip():
        return {"query": query, "results": [], "count": 0, "error": "Empty query"}

    max_results = min(max(max_results, 1), 10)
    schema = os.getenv("HANA_SCHEMA", "PROC_AI")

    logger.info("[search_policies] query=%r max_results=%d", query, max_results)

    # Step 1: Embed the query
    try:
        query_vector = embed_text(query)
    except Exception as exc:
        logger.exception("[search_policies] Embedding failed")
        return {
            "query": query,
            "results": [],
            "count": 0,
            "error": f"Embedding failed: {exc}",
        }

    # Step 2: Vector search in HANA
    # Join POLICY_CHUNKS to POLICY_DOCUMENTS for document title
    sql = f"""
        SELECT
            c.CHUNK_ID,
            c.DOC_ID,
            d.TITLE,
            c.SECTION_HEADER,
            c.CHUNK_TEXT,
            COSINE_SIMILARITY(c.EMBEDDING, TO_REAL_VECTOR(?)) AS SIMILARITY
        FROM {schema}.POLICY_CHUNKS c
        JOIN {schema}.POLICY_DOCUMENTS d ON c.DOC_ID = d.DOC_ID
        ORDER BY SIMILARITY DESC
        LIMIT ?
    """

    try:
        with get_cursor() as cursor:
            vector_str = "[" + ",".join(str(v) for v in query_vector) + "]"
            cursor.execute(sql, (vector_str, max_results))
            rows = cursor.fetchall()
    except Exception as exc:
        logger.exception("[search_policies] HANA query failed")
        return {
            "query": query,
            "results": [],
            "count": 0,
            "error": f"HANA query failed: {exc}",
        }

    results = [
        {
            "chunk_id": row[0],
            "doc_id": row[1],
            "doc_title": str(row[2]) if row[2] else "",
            "section_header": str(row[3]) if row[3] else "",
            "chunk_text": str(row[4]) if row[4] else "",
            "similarity": round(float(row[5]), 4),
        }
        for row in rows
    ]

    logger.info("[search_policies] Returned %d results", len(results))
    return {"query": query, "results": results, "count": len(results)}
