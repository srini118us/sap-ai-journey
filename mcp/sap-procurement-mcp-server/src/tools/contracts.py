"""Contract semantic search tool.

Embeds the user query and runs COSINE_SIMILARITY against CONTRACT_MASTER.EMBEDDING.
Returns active contracts matching the query intent, joined to vendor info.
Mirrors Lab 52's semantic_search_contracts pattern.
"""
import os
import logging
from typing import Any

from src.hana import get_cursor
from src.genai import embed_text

logger = logging.getLogger(__name__)


def search_contracts(
    query: str,
    max_results: int = 5,
    active_only: bool = True,
) -> dict[str, Any]:
    """Semantic search on vendor contracts.

    Use this when the user asks about contract terms, pricing, discounts,
    or wants to find contracts related to a topic (e.g., "SaaS consulting
    contracts" or "annual maintenance agreements").

    Args:
        query: Natural language description of what contract info is needed.
        max_results: Maximum contracts to return (default 5, cap 10).
        active_only: If True, only return contracts with STATUS='Active' (default True).

    Returns:
        Dict with:
            - query: Echo of input
            - results: List of contract records with vendor info and similarity scores
            - count: Number of results returned
            - error: Present if embedding or query failed
    """
    if not query or not query.strip():
        return {"query": query, "results": [], "count": 0, "error": "Empty query"}

    max_results = min(max(max_results, 1), 10)
    schema = os.getenv("HANA_SCHEMA", "PROC_AI")

    logger.info(
        "[search_contracts] query=%r max_results=%d active_only=%s",
        query, max_results, active_only,
    )

    # Step 1: Embed the query
    try:
        query_vector = embed_text(query)
    except Exception as exc:
        logger.exception("[search_contracts] Embedding failed")
        return {
            "query": query,
            "results": [],
            "count": 0,
            "error": f"Embedding failed: {exc}",
        }

    # Step 2: Vector search with vendor join
    active_filter = "AND c.STATUS = 'Active'" if active_only else ""
    sql = f"""
        SELECT
            c.CONTRACT_ID,
            c.VENDOR_ID,
            v.VENDOR_NAME,
            c.CONTRACT_TYPE,
            c.TITLE,
            c.TOTAL_VALUE,
            c.CURRENCY,
            c.START_DATE,
            c.END_DATE,
            c.AUTO_RENEW,
            c.DISCOUNT_PCT,
            c.STATUS,
            COSINE_SIMILARITY(c.EMBEDDING, TO_REAL_VECTOR(?)) AS SIMILARITY
        FROM {schema}.CONTRACT_MASTER c
        JOIN {schema}.VENDOR_MASTER v ON c.VENDOR_ID = v.VENDOR_ID
        WHERE c.EMBEDDING IS NOT NULL
        {active_filter}
        ORDER BY SIMILARITY DESC
        LIMIT ?
    """

    try:
        with get_cursor() as cursor:
            vector_str = "[" + ",".join(str(v) for v in query_vector) + "]"
            cursor.execute(sql, (vector_str, max_results))
            rows = cursor.fetchall()
    except Exception as exc:
        logger.exception("[search_contracts] HANA query failed")
        return {
            "query": query,
            "results": [],
            "count": 0,
            "error": f"HANA query failed: {exc}",
        }

    results = [
        {
            "contract_id": row[0],
            "vendor_id": row[1],
            "vendor_name": row[2],
            "contract_type": row[3],
            "title": row[4],
            "total_value": float(row[5]) if row[5] is not None else 0.0,
            "currency": row[6],
            "start_date": str(row[7]) if row[7] else None,
            "end_date": str(row[8]) if row[8] else None,
            "auto_renew": bool(row[9]) if row[9] is not None else False,
            "discount_pct": float(row[10]) if row[10] is not None else 0.0,
            "status": row[11],
            "similarity": round(float(row[12]), 4),
        }
        for row in rows
    ]

    logger.info("[search_contracts] Returned %d contracts", len(results))
    return {"query": query, "results": results, "count": len(results)}
