-- =================================================================
-- YottaFlex KYC – PostgreSQL Schema (DDL)
-- Generated: 2026-11-13
-- All tables, indexes, constraints, and enum types
-- =================================================================

-- Drop existing tables (order respects FK dependencies)
DROP TABLE IF EXISTS customer_document_requirements CASCADE;
DROP TABLE IF EXISTS audit_events CASCADE;
DROP TABLE IF EXISTS alerts CASCADE;
DROP TABLE IF EXISTS review_cases CASCADE;
DROP TABLE IF EXISTS verifications CASCADE;
DROP TABLE IF EXISTS documents CASCADE;
DROP TABLE IF EXISTS beneficial_owners CASCADE;
DROP TABLE IF EXISTS risk_ratings CASCADE;
DROP TABLE IF EXISTS kyc_requirements CASCADE;
DROP TABLE IF EXISTS customers CASCADE;
DROP TABLE IF EXISTS customer_types CASCADE;

-- =================================================================
-- 1. customer_types
-- =================================================================
CREATE TABLE customer_types (
    id                        SERIAL PRIMARY KEY,
    code                      VARCHAR(50)   NOT NULL UNIQUE,
    name                      VARCHAR(100)  NOT NULL,
    description               TEXT,
    requires_beneficial_owner BOOLEAN       NOT NULL DEFAULT FALSE,
    min_beneficial_owner_pct  NUMERIC(5,2)  DEFAULT 25.00,
    periodic_review_months    INTEGER       NOT NULL DEFAULT 12,
    is_active                 BOOLEAN       NOT NULL DEFAULT TRUE,
    created_at                TIMESTAMP     NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE customer_types IS 'Master list of customer classification types';
COMMENT ON COLUMN customer_types.code IS 'Unique code: INDIVIDUAL, SOLE_TRADER, PARTNERSHIP, PRIVATE_COMPANY, PUBLIC_COMPANY, TRUST, NON_PROFIT';
COMMENT ON COLUMN customer_types.periodic_review_months IS 'Default months between periodic KYC reviews';

-- =================================================================
-- 2. customers
-- =================================================================
CREATE TABLE customers (
    id                          SERIAL PRIMARY KEY,
    customer_id                 VARCHAR(20)   NOT NULL UNIQUE,   -- CUS-000001
    full_name                   VARCHAR(200)  NOT NULL,
    date_of_birth               DATE,
    nationality                 VARCHAR(100),
    country_of_residence        VARCHAR(100)  NOT NULL,
    email                       VARCHAR(200),
    phone                       VARCHAR(50),
    address_line1               VARCHAR(200),
    address_line2               VARCHAR(200),
    city                        VARCHAR(100),
    state_province              VARCHAR(100),
    postal_code                 VARCHAR(20),
    country                     VARCHAR(100),
    customer_type_id            INTEGER       NOT NULL REFERENCES customer_types(id),
    onboarding_status           VARCHAR(20)   NOT NULL DEFAULT 'PENDING',
        -- PENDING | IN_PROGRESS | APPROVED | REJECTED | SUSPENDED | EXPIRED
    business_registration_number VARCHAR(100),
    business_name               VARCHAR(200),
    incorporation_date          DATE,
    incorporation_country       VARCHAR(100),
    kyc_completeness_pct        NUMERIC(5,2)  DEFAULT 0.00,
    is_pep                      BOOLEAN       DEFAULT FALSE,
    is_sanctioned               BOOLEAN       DEFAULT FALSE,
    source_of_funds             VARCHAR(200),
    onboarding_date             DATE,
    approved_date               DATE,
    next_review_date            DATE,
    created_at                  TIMESTAMP     NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMP     DEFAULT NOW(),
    CONSTRAINT ck_customers_completeness CHECK (kyc_completeness_pct BETWEEN 0 AND 100)
);

CREATE INDEX ix_customers_customer_id      ON customers(customer_id);
CREATE INDEX ix_customers_onboarding_status ON customers(onboarding_status);
CREATE INDEX ix_customers_next_review_date  ON customers(next_review_date);

COMMENT ON TABLE customers IS '8,000 customer records; seed=20261022';
COMMENT ON COLUMN customers.customer_id IS 'Immutable business key: CUS-000001 format';
COMMENT ON COLUMN customers.kyc_completeness_pct IS '0-100; calculated from mandatory requirement fulfilment';

-- =================================================================
-- 3. kyc_requirements
-- =================================================================
CREATE TABLE kyc_requirements (
    id                   SERIAL PRIMARY KEY,
    requirement_id       VARCHAR(25)   NOT NULL UNIQUE,   -- KYC-2026-000001
    customer_type_id     INTEGER       NOT NULL REFERENCES customer_types(id),
    document_category    VARCHAR(20)   NOT NULL,
        -- IDENTITY | ADDRESS | BUSINESS | FINANCIAL | OWNERSHIP | COMPLIANCE | OTHER
    document_type        VARCHAR(100)  NOT NULL,
    requirement_type     VARCHAR(20)   NOT NULL DEFAULT 'MANDATORY',
        -- MANDATORY | CONDITIONAL | OPTIONAL
    risk_level_applicable VARCHAR(20),  -- NULL = all risk levels
    description          TEXT,
    max_age_months       INTEGER,
    is_active            BOOLEAN       DEFAULT TRUE,
    effective_from       DATE          NOT NULL,
    effective_to         DATE,
    created_at           TIMESTAMP     NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_kyc_req_customer_type ON kyc_requirements(customer_type_id);
CREATE INDEX ix_kyc_req_category      ON kyc_requirements(document_category);

-- =================================================================
-- 4. risk_ratings
-- =================================================================
CREATE TABLE risk_ratings (
    id              SERIAL PRIMARY KEY,
    risk_rating_id  VARCHAR(25)   NOT NULL UNIQUE,  -- RR-CUS-000001-001
    customer_id     INTEGER       NOT NULL REFERENCES customers(id),
    risk_level      VARCHAR(20)   NOT NULL,  -- LOW | MEDIUM | HIGH | VERY_HIGH
    risk_score      NUMERIC(5,2),
    assessed_by     VARCHAR(100),
    assessed_at     TIMESTAMP     NOT NULL,
    effective_from  DATE          NOT NULL,
    effective_to    DATE,          -- NULL = current rating
    rationale       TEXT,
    pep_flag        BOOLEAN       DEFAULT FALSE,
    sanctions_flag  BOOLEAN       DEFAULT FALSE,
    geographic_risk VARCHAR(50),
    industry_risk   VARCHAR(50),
    created_at      TIMESTAMP     NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_risk_ratings_customer_id   ON risk_ratings(customer_id);
CREATE INDEX ix_risk_ratings_effective_from ON risk_ratings(effective_from);

-- =================================================================
-- 5. beneficial_owners
-- =================================================================
CREATE TABLE beneficial_owners (
    id                      SERIAL PRIMARY KEY,
    bo_id                   VARCHAR(25)   NOT NULL UNIQUE,  -- BO-CUS-000001-001
    business_customer_id    INTEGER       NOT NULL REFERENCES customers(id),
    individual_customer_id  INTEGER       REFERENCES customers(id),
    full_name               VARCHAR(200)  NOT NULL,
    date_of_birth           DATE,
    nationality             VARCHAR(100),
    country_of_residence    VARCHAR(100),
    ownership_percentage    NUMERIC(5,2)  NOT NULL,
    control_type            VARCHAR(100),  -- Direct | Indirect | Joint
    is_pep                  BOOLEAN       DEFAULT FALSE,
    is_sanctioned           BOOLEAN       DEFAULT FALSE,
    is_verified             BOOLEAN       DEFAULT FALSE,
    verification_date       DATE,
    is_active               BOOLEAN       DEFAULT TRUE,
    created_at              TIMESTAMP     NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMP     DEFAULT NOW(),
    CONSTRAINT ck_bo_ownership_pct_range CHECK (ownership_percentage >= 0 AND ownership_percentage <= 100)
);

CREATE INDEX ix_bo_business_customer_id ON beneficial_owners(business_customer_id);

COMMENT ON COLUMN beneficial_owners.ownership_percentage IS 'Individual owner share; sum per business <= 100% normally (anomaly 3 deliberately exceeds)';

-- =================================================================
-- 6. documents
-- =================================================================
CREATE TABLE documents (
    id                      SERIAL PRIMARY KEY,
    document_id             VARCHAR(30)   NOT NULL UNIQUE,  -- DOC-CUS-000001-001
    customer_id             INTEGER       NOT NULL REFERENCES customers(id),
    document_category       VARCHAR(20)   NOT NULL,
    document_type           VARCHAR(100)  NOT NULL,
    document_number         VARCHAR(100),
    issuing_authority       VARCHAR(200),
    issuing_country         VARCHAR(100),
    issue_date              DATE          NOT NULL,
    expiry_date             DATE,
    document_status         VARCHAR(20)   NOT NULL DEFAULT 'PENDING',
        -- PENDING | SUBMITTED | VERIFIED | REJECTED | EXPIRED | SUPERSEDED
    file_reference          VARCHAR(500),
    notes                   TEXT,
    is_mandatory            BOOLEAN       DEFAULT TRUE,
    is_duplicate_suspect    BOOLEAN       DEFAULT FALSE,
    duplicate_of_document_id VARCHAR(30),
    submitted_at            TIMESTAMP,
    created_at              TIMESTAMP     NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMP     DEFAULT NOW(),
    CONSTRAINT ck_doc_date_order CHECK (expiry_date IS NULL OR issue_date <= expiry_date)
);

CREATE INDEX ix_documents_customer_id    ON documents(customer_id);
CREATE INDEX ix_documents_document_status ON documents(document_status);
CREATE INDEX ix_documents_expiry_date    ON documents(expiry_date);
CREATE INDEX ix_documents_document_number ON documents(document_number);

COMMENT ON COLUMN documents.document_id IS 'DOC-<customer_id>-<seq> e.g. DOC-CUS-000001-001';
COMMENT ON COLUMN documents.is_duplicate_suspect IS 'TRUE when anomaly 5 (duplicate document number across customers) is injected';

-- =================================================================
-- 7. verifications
-- =================================================================
CREATE TABLE verifications (
    id                       SERIAL PRIMARY KEY,
    verification_id          VARCHAR(35)   NOT NULL UNIQUE,  -- VER-DOC-CUS-000001-001-001
    document_id              INTEGER       NOT NULL REFERENCES documents(id),
    verified_by              VARCHAR(100)  NOT NULL,
    verified_at              TIMESTAMP     NOT NULL,
    decision                 VARCHAR(20)   NOT NULL,  -- PASS | FAIL | REFER | PENDING
    decision_reason          TEXT,
    name_match               BOOLEAN,
    name_on_document         VARCHAR(200),
    expiry_check_passed      BOOLEAN,
    authenticity_check_passed BOOLEAN,
    override_flag            BOOLEAN       DEFAULT FALSE,
    override_reason          TEXT,
    created_at               TIMESTAMP     NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_verifications_document_id ON verifications(document_id);
CREATE INDEX ix_verifications_decision    ON verifications(decision);
CREATE INDEX ix_verifications_verified_at ON verifications(verified_at);

COMMENT ON COLUMN verifications.name_match IS 'FALSE flags name mismatch anomaly scenario';

-- =================================================================
-- 8. review_cases
-- =================================================================
CREATE TABLE review_cases (
    id                       SERIAL PRIMARY KEY,
    review_id                VARCHAR(25)   NOT NULL UNIQUE,  -- REV-CUS-000001-2026-01
    customer_id              INTEGER       NOT NULL REFERENCES customers(id),
    trigger                  VARCHAR(20)   NOT NULL,
        -- PERIODIC | RISK_CHANGE | DOCUMENT_EXPIRY | ALERT | MANUAL
    status                   VARCHAR(30)   NOT NULL DEFAULT 'OPEN',
        -- OPEN | IN_PROGRESS | CLOSED_RESOLVED | CLOSED_NO_ACTION | CLOSED_WITHOUT_RESOLUTION | OVERDUE
    opened_at                TIMESTAMP     NOT NULL,
    due_date                 DATE          NOT NULL,
    closed_at                TIMESTAMP,
    assigned_to              VARCHAR(100),
    findings                 TEXT,
    resolution               TEXT,
    closed_without_resolution BOOLEAN      DEFAULT FALSE,
    created_at               TIMESTAMP     NOT NULL DEFAULT NOW(),
    updated_at               TIMESTAMP     DEFAULT NOW()
);

CREATE INDEX ix_review_cases_customer_id ON review_cases(customer_id);
CREATE INDEX ix_review_cases_status      ON review_cases(status);
CREATE INDEX ix_review_cases_due_date    ON review_cases(due_date);

-- =================================================================
-- 9. alerts
-- =================================================================
CREATE TABLE alerts (
    id               SERIAL PRIMARY KEY,
    alert_id         VARCHAR(20)   NOT NULL UNIQUE,  -- ALT-2026-000001
    customer_id      INTEGER       NOT NULL REFERENCES customers(id),
    review_case_id   INTEGER       REFERENCES review_cases(id),
    document_id      INTEGER       REFERENCES documents(id),
    alert_type       VARCHAR(30)   NOT NULL,
        -- DOCUMENT_EXPIRING | DOCUMENT_EXPIRED | REVIEW_OVERDUE | KYC_INCOMPLETE
        -- OWNERSHIP_MISMATCH | NAME_MISMATCH | DUPLICATE_DOCUMENT | ANOMALY_DETECTED
    severity         VARCHAR(20)   NOT NULL,  -- LOW | MEDIUM | HIGH | CRITICAL
    status           VARCHAR(20)   NOT NULL DEFAULT 'OPEN',
        -- OPEN | ACKNOWLEDGED | RESOLVED | SUPPRESSED
    title            VARCHAR(300)  NOT NULL,
    description      TEXT,
    triggered_at     TIMESTAMP     NOT NULL,
    acknowledged_at  TIMESTAMP,
    resolved_at      TIMESTAMP,
    resolved_by      VARCHAR(100),
    resolution_notes TEXT,
    is_anomaly       BOOLEAN       DEFAULT FALSE,
    anomaly_label    VARCHAR(100),
    created_at       TIMESTAMP     NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMP     DEFAULT NOW()
);

CREATE INDEX ix_alerts_customer_id ON alerts(customer_id);
CREATE INDEX ix_alerts_alert_type  ON alerts(alert_type);
CREATE INDEX ix_alerts_status      ON alerts(status);
CREATE INDEX ix_alerts_triggered_at ON alerts(triggered_at);

COMMENT ON COLUMN alerts.is_anomaly IS 'TRUE for the 5 injected anomaly records';
COMMENT ON COLUMN alerts.anomaly_label IS 'Ground-truth label for anomaly detection';

-- =================================================================
-- 10. audit_events
-- =================================================================
CREATE TABLE audit_events (
    id            SERIAL PRIMARY KEY,
    audit_id      VARCHAR(20)   NOT NULL UNIQUE,  -- AUD-2026-000001
    customer_id   INTEGER       REFERENCES customers(id),
    entity_type   VARCHAR(50)   NOT NULL,  -- Customer | Document | ReviewCase | etc.
    entity_id     VARCHAR(50)   NOT NULL,
    action        VARCHAR(30)   NOT NULL,
        -- CREATE | UPDATE | DELETE | VERIFY | APPROVE | REJECT
        -- REVIEW_OPEN | REVIEW_CLOSE | ALERT_RAISED | ALERT_RESOLVED
        -- ANOMALY_INJECTED | STATUS_CHANGE
    performed_by  VARCHAR(100)  NOT NULL,
    performed_at  TIMESTAMP     NOT NULL,
    old_value     TEXT,          -- JSON snapshot of previous state
    new_value     TEXT,          -- JSON snapshot of new state
    ip_address    VARCHAR(45),
    session_id    VARCHAR(100),
    notes         TEXT,
    created_at    TIMESTAMP     NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_audit_events_customer_id  ON audit_events(customer_id);
CREATE INDEX ix_audit_events_entity_type  ON audit_events(entity_type);
CREATE INDEX ix_audit_events_performed_at ON audit_events(performed_at);
CREATE INDEX ix_audit_events_action       ON audit_events(action);

-- =================================================================
-- Bridge: customer_document_requirements
-- =================================================================
CREATE TABLE customer_document_requirements (
    id             SERIAL PRIMARY KEY,
    customer_id    INTEGER       NOT NULL REFERENCES customers(id),
    requirement_id INTEGER       NOT NULL REFERENCES kyc_requirements(id),
    document_id    INTEGER       REFERENCES documents(id),
    is_fulfilled   BOOLEAN       NOT NULL DEFAULT FALSE,
    fulfilled_at   TIMESTAMP,
    waived         BOOLEAN       DEFAULT FALSE,
    waiver_reason  TEXT,
    created_at     TIMESTAMP     NOT NULL DEFAULT NOW(),
    updated_at     TIMESTAMP     DEFAULT NOW(),
    CONSTRAINT uq_customer_requirement UNIQUE (customer_id, requirement_id)
);

CREATE INDEX ix_cdr_customer_id ON customer_document_requirements(customer_id);

-- =================================================================
-- Useful views
-- =================================================================

CREATE OR REPLACE VIEW v_kyc_completeness AS
SELECT
    c.customer_id,
    c.full_name,
    ct.code AS customer_type,
    c.onboarding_status,
    c.kyc_completeness_pct,
    COUNT(cdr.id) AS total_requirements,
    SUM(CASE WHEN cdr.is_fulfilled THEN 1 ELSE 0 END) AS fulfilled,
    c.next_review_date
FROM customers c
JOIN customer_types ct ON c.customer_type_id = ct.id
LEFT JOIN customer_document_requirements cdr ON cdr.customer_id = c.id
LEFT JOIN kyc_requirements kr ON cdr.requirement_id = kr.id AND kr.requirement_type = 'MANDATORY'
GROUP BY c.customer_id, c.full_name, ct.code, c.onboarding_status,
         c.kyc_completeness_pct, c.next_review_date;

CREATE OR REPLACE VIEW v_expiring_documents AS
SELECT
    d.document_id,
    d.document_type,
    d.expiry_date,
    d.expiry_date - CURRENT_DATE AS days_until_expiry,
    c.customer_id,
    c.full_name,
    c.onboarding_status
FROM documents d
JOIN customers c ON d.customer_id = c.id
WHERE d.expiry_date IS NOT NULL
  AND d.expiry_date BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '90 days'
  AND d.document_status = 'VERIFIED'
ORDER BY d.expiry_date;

CREATE OR REPLACE VIEW v_ownership_validation AS
SELECT
    c.customer_id,
    c.full_name,
    ct.code AS customer_type,
    SUM(bo.ownership_percentage) AS total_ownership_pct,
    COUNT(bo.id) AS owner_count,
    CASE WHEN SUM(bo.ownership_percentage) > 100 THEN 'EXCEEDS_100'
         WHEN SUM(bo.ownership_percentage) < 25  THEN 'BELOW_THRESHOLD'
         ELSE 'OK' END AS ownership_status
FROM customers c
JOIN customer_types ct ON c.customer_type_id = ct.id
LEFT JOIN beneficial_owners bo ON bo.business_customer_id = c.id AND bo.is_active = TRUE
WHERE ct.requires_beneficial_owner = TRUE
GROUP BY c.customer_id, c.full_name, ct.code;

CREATE OR REPLACE VIEW v_anomalies AS
SELECT
    alert_id,
    alert_type,
    severity,
    anomaly_label,
    title,
    description,
    triggered_at,
    customer_id
FROM alerts
WHERE is_anomaly = TRUE
ORDER BY triggered_at;
