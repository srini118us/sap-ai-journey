-- ============================================================
-- Vendor Master Data Quality Copilot
-- HANA Cloud DDL with dual embedding vectors
-- Target: schema DBADMIN on hana-cloud instance
-- Embedding dimensions:
--   NVIDIA Llama Nemotron Embed 1b V2 = 1024
--   OpenAI text-embedding-3-small     = 1536
-- ============================================================

-- Optional: create dedicated schema (skip if using DBADMIN)
-- CREATE SCHEMA VENDOR_MDQ;
-- SET SCHEMA VENDOR_MDQ;

-- Drop existing (safe rerun)
DROP TABLE VENDORS CASCADE;
DROP TABLE TRANSACTIONS CASCADE;
DROP TABLE QUALITY_RULES CASCADE;
DROP TABLE QUALITY_ISSUES CASCADE;
DROP TABLE POLICY_CHUNKS CASCADE;

-- ============================================================
-- 1. VENDORS master table
-- ============================================================
CREATE COLUMN TABLE VENDORS (
    VENDOR_ID        NVARCHAR(10)   PRIMARY KEY,
    VENDOR_NAME      NVARCHAR(200)  NOT NULL,
    ADDRESS_LINE1    NVARCHAR(200),
    CITY             NVARCHAR(100),
    COUNTRY          NVARCHAR(3),
    POSTAL_CODE      NVARCHAR(20),
    TAX_ID           NVARCHAR(30),
    BANK_ACCOUNT     NVARCHAR(50),
    CATEGORY         NVARCHAR(50),
    PAYMENT_TERMS    NVARCHAR(10),
    CURRENCY         NVARCHAR(3),
    STATUS           NVARCHAR(20),
    CREATED_ON       DATE,
    LAST_MODIFIED    DATE,
    RISK_SCORE       DECIMAL(3,2),
    DESCRIPTION      NVARCHAR(500),
    DESC_VEC_NVIDIA  REAL_VECTOR(1024),
    DESC_VEC_OPENAI  REAL_VECTOR(1536)
);

-- ============================================================
-- 2. TRANSACTIONS (invoices posted against vendors)
-- ============================================================
CREATE COLUMN TABLE TRANSACTIONS (
    TXN_ID           NVARCHAR(15)   PRIMARY KEY,
    VENDOR_ID        NVARCHAR(10)   NOT NULL,
    INVOICE_NUMBER   NVARCHAR(30),
    INVOICE_DATE     DATE,
    POSTING_DATE     DATE,
    AMOUNT           DECIMAL(15,2),
    CURRENCY         NVARCHAR(3),
    PAYMENT_STATUS   NVARCHAR(20),
    APPROVED_BY      NVARCHAR(50),
    NOTES            NVARCHAR(300)
);

-- ============================================================
-- 3. QUALITY_RULES (business rules for data quality)
-- ============================================================
CREATE COLUMN TABLE QUALITY_RULES (
    RULE_ID          NVARCHAR(10)   PRIMARY KEY,
    RULE_NAME        NVARCHAR(100),
    RULE_CATEGORY    NVARCHAR(50),
    SEVERITY         NVARCHAR(20),
    DESCRIPTION      NVARCHAR(500),
    SQL_CHECK        NVARCHAR(2000),
    REMEDIATION      NVARCHAR(500)
);

-- ============================================================
-- 4. QUALITY_ISSUES (historical issues + resolutions)
-- ============================================================
CREATE COLUMN TABLE QUALITY_ISSUES (
    ISSUE_ID         NVARCHAR(15)   PRIMARY KEY,
    VENDOR_ID        NVARCHAR(10),
    RULE_ID          NVARCHAR(10),
    DETECTED_ON      DATE,
    RESOLVED_ON      DATE,
    STATUS           NVARCHAR(20),
    DESCRIPTION      NVARCHAR(1000),
    RESOLUTION_NOTES NVARCHAR(1000),
    DESC_VEC_NVIDIA  REAL_VECTOR(1024),
    DESC_VEC_OPENAI  REAL_VECTOR(1536)
);

-- ============================================================
-- 5. POLICY_CHUNKS (chunked policy PDF content for RAG)
-- ============================================================
CREATE COLUMN TABLE POLICY_CHUNKS (
    CHUNK_ID         NVARCHAR(20)   PRIMARY KEY,
    POLICY_NAME      NVARCHAR(100),
    SECTION_NAME     NVARCHAR(200),
    CHUNK_TEXT       NCLOB,
    CHUNK_ORDER      INT,
    TOKEN_COUNT      INT,
    CHUNK_VEC_NVIDIA REAL_VECTOR(1024),
    CHUNK_VEC_OPENAI REAL_VECTOR(1536)
);

-- ============================================================
-- Verify tables created
-- ============================================================
SELECT TABLE_NAME, RECORD_COUNT
FROM SYS.M_TABLES
WHERE SCHEMA_NAME = CURRENT_SCHEMA
  AND TABLE_NAME IN ('VENDORS', 'TRANSACTIONS', 'QUALITY_RULES', 'QUALITY_ISSUES', 'POLICY_CHUNKS')
ORDER BY TABLE_NAME;
