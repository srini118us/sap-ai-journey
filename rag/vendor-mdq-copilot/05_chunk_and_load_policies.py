#!/usr/bin/env python3
"""
Read the 4 policy PDFs, chunk them by section, and load into POLICY_CHUNKS.

Approach:
  Sections are detected by heading patterns (numeric prefix like "1.", "2.1", etc).
  Each section becomes one chunk (or split further if very long).
  Chunk text preserves section name for citation quality.

Env vars required:
  HANA_HOST      e.g. abc123.hana.prod-us10.hanacloud.ondemand.com
  HANA_PORT      usually 443
  HANA_USER      DBADMIN
  HANA_PASSWORD  the password reset earlier

Install:
  pip install hdbcli pypdf

Run:
  python 05_chunk_and_load_policies.py
"""

import os
import re
import sys
from pathlib import Path
from pypdf import PdfReader
from hdbcli import dbapi

BASE = Path(__file__).parent
POLICIES = BASE / "policies"

HANA_HOST = os.environ.get("HANA_HOST")
HANA_PORT = int(os.environ.get("HANA_PORT", "443"))
HANA_USER = os.environ.get("HANA_USER", "DBADMIN")
HANA_PASSWORD = os.environ.get("HANA_PASSWORD")

if not (HANA_HOST and HANA_PASSWORD):
    print("ERROR: set HANA_HOST and HANA_PASSWORD env vars first")
    print("  PowerShell: $env:HANA_HOST='...'; $env:HANA_PASSWORD='...'")
    print("  Bash:       export HANA_HOST=... HANA_PASSWORD=...")
    sys.exit(1)

MAX_CHUNK_CHARS = 1500  # policies are dense, keep chunks large enough for context

# Map PDF filename to friendly policy name
POLICY_NAMES = {
    "01_vendor_mdg_policy.pdf": "Vendor Master Data Governance Policy",
    "02_duplicate_detection_standard.pdf": "Duplicate Vendor Detection Standard",
    "03_vendor_onboarding_compliance.pdf": "Vendor Onboarding Compliance Requirements",
    "04_blocked_vendor_management.pdf": "Blocked Vendor Management Procedure"
}


def extract_text(pdf_path):
    """Extract full text from PDF, one page at a time joined."""
    reader = PdfReader(str(pdf_path))
    parts = []
    for page in reader.pages:
        parts.append(page.extract_text() or "")
    return "\n".join(parts)


def split_into_sections(text):
    """
    Split by section headings (numbered like '1.', '2.1', '3.2.1', etc).
    Returns list of (section_name, section_body) tuples.
    """
    # Match lines starting with digit dot pattern like "1. Purpose" or "3.2 Financial"
    # After the title, capture up to next similar heading
    pattern = re.compile(
        r'^(\d+(?:\.\d+)*\.?\s+[A-Z][^\n]*?)$',
        re.MULTILINE
    )
    matches = list(pattern.finditer(text))
    sections = []
    for i, m in enumerate(matches):
        heading = m.group(1).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        if body:
            sections.append((heading, body))
    return sections


def split_long_chunk(section_name, body, max_chars):
    """If a section body is too long, split at paragraph boundaries."""
    if len(body) <= max_chars:
        return [body]
    paras = re.split(r'\n\s*\n', body)
    chunks = []
    current = ""
    for para in paras:
        if len(current) + len(para) + 2 <= max_chars:
            current += (para + "\n\n")
        else:
            if current:
                chunks.append(current.strip())
            current = para + "\n\n"
    if current:
        chunks.append(current.strip())
    return chunks


def estimate_tokens(text):
    """Rough token estimate: 4 chars per token."""
    return max(1, len(text) // 4)


def process_all():
    all_chunks = []  # (policy_name, section_name, chunk_text, order, token_count)
    for pdf_file in sorted(POLICIES.glob("*.pdf")):
        policy_name = POLICY_NAMES.get(pdf_file.name, pdf_file.stem)
        print(f"Processing: {policy_name}")
        text = extract_text(pdf_file)
        sections = split_into_sections(text)
        chunk_order = 0
        for section_name, body in sections:
            for piece in split_long_chunk(section_name, body, MAX_CHUNK_CHARS):
                chunk_order += 1
                chunk_text = f"{section_name}\n\n{piece}"
                all_chunks.append((
                    policy_name,
                    section_name,
                    chunk_text,
                    chunk_order,
                    estimate_tokens(chunk_text)
                ))
        print(f"  Sections: {len(sections)} | Chunks: {chunk_order}")
    return all_chunks


def insert_chunks(chunks):
    print(f"\nConnecting to HANA at {HANA_HOST}:{HANA_PORT}")
    conn = dbapi.connect(
        address=HANA_HOST,
        port=HANA_PORT,
        user=HANA_USER,
        password=HANA_PASSWORD,
        encrypt=True,
        sslValidateCertificate=False
    )
    cursor = conn.cursor()

    # Clear existing chunks (safe rerun)
    cursor.execute("DELETE FROM POLICY_CHUNKS")
    print(f"Cleared existing POLICY_CHUNKS rows")

    # Insert new chunks (vectors will be NULL, populated by script 06)
    insert_sql = """
        INSERT INTO POLICY_CHUNKS
        (CHUNK_ID, POLICY_NAME, SECTION_NAME, CHUNK_TEXT, CHUNK_ORDER, TOKEN_COUNT)
        VALUES (?, ?, ?, ?, ?, ?)
    """
    for i, (policy, section, text, order, tokens) in enumerate(chunks, 1):
        chunk_id = f"PC{i:018d}"
        cursor.execute(insert_sql, (chunk_id, policy, section, text, order, tokens))

    conn.commit()
    print(f"Inserted {len(chunks)} chunks into POLICY_CHUNKS")

    # Verify
    cursor.execute("SELECT POLICY_NAME, COUNT(*) FROM POLICY_CHUNKS GROUP BY POLICY_NAME ORDER BY POLICY_NAME")
    print("\nChunks per policy:")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]}")

    cursor.close()
    conn.close()


if __name__ == "__main__":
    chunks = process_all()
    print(f"\nTotal chunks generated: {len(chunks)}")
    if not chunks:
        print("No chunks produced. Check PDF extraction.")
        sys.exit(1)
    insert_chunks(chunks)
    print("\nDONE. Ready for script 06 (embedding population).")
