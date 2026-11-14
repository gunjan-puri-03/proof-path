# YottaFlex KYC – Data Dictionary

Version: 1.0\
Reference Date: 2026-10-22\
Seed: 20261022

---

## 1. customer_types

Master list of customer classification types.

| Column | Type | Nullable | Description |
|---|---|---|---|
| id | INTEGER | NO | Surrogate primary key |
| code | VARCHAR(50) | NO | Unique type code (enum) |
| name | VARCHAR(100) | NO | Human-readable name |
| description | TEXT | YES | Full description |
| requires_beneficial_owner | BOOLEAN | NO | Whether BO records are required |
| min_beneficial_owner_pct | NUMERIC(5,2) | YES | Minimum disclosure threshold (default 25%) |
| periodic_review_months | INTEGER | NO | Default review frequency in months |
| is_active | BOOLEAN | NO | Whether type is currently in use |
| created_at | TIMESTAMP | NO | Record creation timestamp |

**Allowed values for `code`:**\
`INDIVIDUAL`, `SOLE_TRADER`, `PARTNERSHIP`, `PRIVATE_COMPANY`, `PUBLIC_COMPANY`, `TRUST`, `NON_PROFIT`

---

## 2. customers

8,000 synthetic customer records. Seed 20261022.

| Column | Type | Nullable | Description |
|---|---|---|---|
| id | INTEGER | NO | Surrogate PK |
| customer_id | VARCHAR(20) | NO | Business key: `CUS-000001` |
| full_name | VARCHAR(200) | NO | Individual: legal name; Business: entity name |
| date_of_birth | DATE | YES | Individuals only |
| nationality | VARCHAR(100) | YES | Country of citizenship |
| country_of_residence | VARCHAR(100) | NO | Current country of residence |
| email | VARCHAR(200) | YES | Contact email |
| phone | VARCHAR(50) | YES | Contact phone |
| address_line1 | VARCHAR(200) | YES | Street address |
| address_line2 | VARCHAR(200) | YES | Address continuation |
| city | VARCHAR(100) | YES | City |
| state_province | VARCHAR(100) | YES | State or province |
| postal_code | VARCHAR(20) | YES | Postal/ZIP code |
| country | VARCHAR(100) | YES | Address country |
| customer_type_id | INTEGER | NO | FK → customer_types.id |
| onboarding_status | VARCHAR(20) | NO | Current lifecycle status |
| business_registration_number | VARCHAR(100) | YES | Business customers only |
| business_name | VARCHAR(200) | YES | Business customers only |
| incorporation_date | DATE | YES | Business customers only |
| incorporation_country | VARCHAR(100) | YES | Business customers only |
| kyc_completeness_pct | NUMERIC(5,2) | YES | 0–100; calculated field |
| is_pep | BOOLEAN | YES | Politically Exposed Person flag |
| is_sanctioned | BOOLEAN | YES | Sanctions flag |
| source_of_funds | VARCHAR(200) | YES | Declared source of funds |
| onboarding_date | DATE | YES | Date customer application received |
| approved_date | DATE | YES | Date customer was approved |
| next_review_date | DATE | YES | Scheduled next review date |
| created_at | TIMESTAMP | NO | Record creation timestamp |
| updated_at | TIMESTAMP | YES | Last update timestamp |

**Allowed values for `onboarding_status`:**\
`PENDING`, `IN_PROGRESS`, `APPROVED`, `REJECTED`, `SUSPENDED`, `EXPIRED`

---

## 3. kyc_requirements

27 KYC requirement rules across all 7 customer types.

| Column | Type | Nullable | Description |
|---|---|---|---|
| id | INTEGER | NO | Surrogate PK |
| requirement_id | VARCHAR(25) | NO | Business key: `KYC-2026-000001` |
| customer_type_id | INTEGER | NO | FK → customer_types.id |
| document_category | VARCHAR(20) | NO | Category of required document |
| document_type | VARCHAR(100) | NO | Specific document type name |
| requirement_type | VARCHAR(20) | NO | MANDATORY / CONDITIONAL / OPTIONAL |
| risk_level_applicable | VARCHAR(20) | YES | NULL = all risk levels |
| description | TEXT | YES | Rule description |
| max_age_months | INTEGER | YES | Maximum document age in months |
| is_active | BOOLEAN | YES | Whether rule is current |
| effective_from | DATE | NO | Rule effective start date |
| effective_to | DATE | YES | Rule effective end date (NULL = current) |
| created_at | TIMESTAMP | NO | Record creation timestamp |

**Allowed values for `document_category`:**\
`IDENTITY`, `ADDRESS`, `BUSINESS`, `FINANCIAL`, `OWNERSHIP`, `COMPLIANCE`, `OTHER`

---

## 4. risk_ratings

One or more risk ratings per customer. Latest rating has `effective_to = NULL`.

| Column | Type | Nullable | Description |
|---|---|---|---|
| id | INTEGER | NO | Surrogate PK |
| risk_rating_id | VARCHAR(25) | NO | Business key: `RR-CUS-000001-001` |
| customer_id | INTEGER | NO | FK → customers.id |
| risk_level | VARCHAR(20) | NO | Risk classification |
| risk_score | NUMERIC(5,2) | YES | Numeric score 0–100 |
| assessed_by | VARCHAR(100) | YES | Officer who assessed |
| assessed_at | TIMESTAMP | NO | Assessment timestamp |
| effective_from | DATE | NO | Rating effective start |
| effective_to | DATE | YES | Rating effective end (NULL = current) |
| rationale | TEXT | YES | Assessment rationale |
| pep_flag | BOOLEAN | YES | PEP indicator |
| sanctions_flag | BOOLEAN | YES | Sanctions indicator |
| geographic_risk | VARCHAR(50) | YES | LOW / MEDIUM / HIGH |
| industry_risk | VARCHAR(50) | YES | LOW / MEDIUM / HIGH |
| created_at | TIMESTAMP | NO | Record creation timestamp |

**Allowed values for `risk_level`:** `LOW`, `MEDIUM`, `HIGH`, `VERY_HIGH`

---

## 5. beneficial_owners

Beneficial owners linked to business customers.

| Column | Type | Nullable | Description |
|---|---|---|---|
| id | INTEGER | NO | Surrogate PK |
| bo_id | VARCHAR(25) | NO | Business key: `BO-CUS-000001-001` |
| business_customer_id | INTEGER | NO | FK → customers.id (the business) |
| individual_customer_id | INTEGER | YES | FK → customers.id (if BO is also a customer) |
| full_name | VARCHAR(200) | NO | BO full legal name |
| date_of_birth | DATE | YES | BO date of birth |
| nationality | VARCHAR(100) | YES | BO nationality |
| country_of_residence | VARCHAR(100) | YES | BO country of residence |
| ownership_percentage | NUMERIC(5,2) | NO | Individual ownership share (0–100) |
| control_type | VARCHAR(100) | YES | Direct / Indirect / Joint |
| is_pep | BOOLEAN | YES | PEP indicator |
| is_sanctioned | BOOLEAN | YES | Sanctions indicator |
| is_verified | BOOLEAN | YES | Whether BO identity has been verified |
| verification_date | DATE | YES | Date of BO verification |
| is_active | BOOLEAN | YES | Whether BO record is current |
| created_at | TIMESTAMP | NO | Record creation timestamp |
| updated_at | TIMESTAMP | YES | Last update timestamp |

**Constraint:** `ownership_percentage` must be between 0 and 100 per individual owner.

---

## 6. documents

20,000 documents linked to customers.

| Column | Type | Nullable | Description |
|---|---|---|---|
| id | INTEGER | NO | Surrogate PK |
| document_id | VARCHAR(30) | NO | Business key: `DOC-CUS-000001-001` |
| customer_id | INTEGER | NO | FK → customers.id |
| document_category | VARCHAR(20) | NO | IDENTITY / ADDRESS / BUSINESS / etc. |
| document_type | VARCHAR(100) | NO | e.g. "Passport", "Utility Bill" |
| document_number | VARCHAR(100) | YES | Issuer-assigned document number |
| issuing_authority | VARCHAR(200) | YES | Issuing body |
| issuing_country | VARCHAR(100) | YES | Country of issue |
| issue_date | DATE | NO | Date document was issued |
| expiry_date | DATE | YES | Date document expires (NULL = no expiry) |
| document_status | VARCHAR(20) | NO | Lifecycle status |
| file_reference | VARCHAR(500) | YES | Storage reference (placeholder) |
| notes | TEXT | YES | Free-text notes; anomaly annotations |
| is_mandatory | BOOLEAN | YES | Whether document fulfils a mandatory requirement |
| is_duplicate_suspect | BOOLEAN | YES | TRUE for anomaly 5 |
| duplicate_of_document_id | VARCHAR(30) | YES | Reference to original if duplicate |
| submitted_at | TIMESTAMP | YES | Submission timestamp |
| created_at | TIMESTAMP | NO | Record creation timestamp |
| updated_at | TIMESTAMP | YES | Last update timestamp |

**Allowed values for `document_status`:**\
`PENDING`, `SUBMITTED`, `VERIFIED`, `REJECTED`, `EXPIRED`, `SUPERSEDED`

**Constraint:** `issue_date <= expiry_date` (when expiry_date is not NULL)

---

## 7. verifications

Verification history for documents.

| Column | Type | Nullable | Description |
|---|---|---|---|
| id | INTEGER | NO | Surrogate PK |
| verification_id | VARCHAR(35) | NO | Business key: `VER-DOC-CUS-000001-001-001` |
| document_id | INTEGER | NO | FK → documents.id |
| verified_by | VARCHAR(100) | NO | Officer name or "System" |
| verified_at | TIMESTAMP | NO | Verification timestamp |
| decision | VARCHAR(20) | NO | PASS / FAIL / REFER / PENDING |
| decision_reason | TEXT | YES | Reason for decision |
| name_match | BOOLEAN | YES | TRUE if name on doc matches customer name |
| name_on_document | VARCHAR(200) | YES | Exact name as it appears on document |
| expiry_check_passed | BOOLEAN | YES | Whether expiry check passed |
| authenticity_check_passed | BOOLEAN | YES | Whether authenticity check passed |
| override_flag | BOOLEAN | YES | TRUE if decision was manually overridden |
| override_reason | TEXT | YES | Reason for override |
| created_at | TIMESTAMP | NO | Record creation timestamp |

---

## 8. review_cases

3,000 review cases.

| Column | Type | Nullable | Description |
|---|---|---|---|
| id | INTEGER | NO | Surrogate PK |
| review_id | VARCHAR(25) | NO | Business key: `REV-CUS-000001-2026-01` |
| customer_id | INTEGER | NO | FK → customers.id |
| trigger | VARCHAR(20) | NO | Review trigger type |
| status | VARCHAR(30) | NO | Review lifecycle status |
| opened_at | TIMESTAMP | NO | When review was opened |
| due_date | DATE | NO | When review must be completed |
| closed_at | TIMESTAMP | YES | When review was closed |
| assigned_to | VARCHAR(100) | YES | Assigned officer |
| findings | TEXT | YES | Review findings |
| resolution | TEXT | YES | Resolution notes |
| closed_without_resolution | BOOLEAN | YES | TRUE for anomaly 4 |
| created_at | TIMESTAMP | NO | Record creation timestamp |
| updated_at | TIMESTAMP | YES | Last update timestamp |

**Allowed values for `trigger`:**\
`PERIODIC`, `RISK_CHANGE`, `DOCUMENT_EXPIRY`, `ALERT`, `MANUAL`

**Allowed values for `status`:**\
`OPEN`, `IN_PROGRESS`, `CLOSED_RESOLVED`, `CLOSED_NO_ACTION`, `CLOSED_WITHOUT_RESOLUTION`, `OVERDUE`

---

## 9. alerts

Alerts generated from business rule violations and anomalies.

| Column | Type | Nullable | Description |
|---|---|---|---|
| id | INTEGER | NO | Surrogate PK |
| alert_id | VARCHAR(20) | NO | Business key: `ALT-2026-000001` |
| customer_id | INTEGER | NO | FK → customers.id |
| review_case_id | INTEGER | YES | FK → review_cases.id |
| document_id | INTEGER | YES | FK → documents.id |
| alert_type | VARCHAR(30) | NO | Type of alert |
| severity | VARCHAR(20) | NO | LOW / MEDIUM / HIGH / CRITICAL |
| status | VARCHAR(20) | NO | OPEN / ACKNOWLEDGED / RESOLVED / SUPPRESSED |
| title | VARCHAR(300) | NO | Short title |
| description | TEXT | YES | Full description |
| triggered_at | TIMESTAMP | NO | When alert was triggered |
| acknowledged_at | TIMESTAMP | YES | When acknowledged |
| resolved_at | TIMESTAMP | YES | When resolved |
| resolved_by | VARCHAR(100) | YES | Who resolved |
| resolution_notes | TEXT | YES | Resolution notes |
| is_anomaly | BOOLEAN | YES | TRUE for 5 injected anomaly records |
| anomaly_label | VARCHAR(100) | YES | Ground-truth anomaly label |
| created_at | TIMESTAMP | NO | Record creation timestamp |
| updated_at | TIMESTAMP | YES | Last update timestamp |

---

## 10. audit_events

Immutable audit trail of all important state changes.

| Column | Type | Nullable | Description |
|---|---|---|---|
| id | INTEGER | NO | Surrogate PK |
| audit_id | VARCHAR(20) | NO | Business key: `AUD-2026-000001` |
| customer_id | INTEGER | YES | FK → customers.id |
| entity_type | VARCHAR(50) | NO | Entity class: Customer / Document / ReviewCase / etc. |
| entity_id | VARCHAR(50) | NO | Business ID of affected record |
| action | VARCHAR(30) | NO | Action performed |
| performed_by | VARCHAR(100) | NO | Officer or system |
| performed_at | TIMESTAMP | NO | When action was performed |
| old_value | TEXT | YES | JSON snapshot of previous state |
| new_value | TEXT | YES | JSON snapshot of new state |
| ip_address | VARCHAR(45) | YES | IP address |
| session_id | VARCHAR(100) | YES | Session identifier |
| notes | TEXT | YES | Additional notes |
| created_at | TIMESTAMP | NO | Record creation timestamp |

---

## 11. customer_document_requirements (Bridge)

Tracks fulfilment of KYC requirements per customer.

| Column | Type | Nullable | Description |
|---|---|---|---|
| id | INTEGER | NO | Surrogate PK |
| customer_id | INTEGER | NO | FK → customers.id |
| requirement_id | INTEGER | NO | FK → kyc_requirements.id |
| document_id | INTEGER | YES | FK → documents.id (NULL if unfulfilled) |
| is_fulfilled | BOOLEAN | NO | Whether requirement is met |
| fulfilled_at | TIMESTAMP | YES | When requirement was fulfilled |
| waived | BOOLEAN | YES | Whether requirement was waived |
| waiver_reason | TEXT | YES | Reason for waiver |
| created_at | TIMESTAMP | NO | Record creation timestamp |
| updated_at | TIMESTAMP | YES | Last update timestamp |

**Unique constraint:** `(customer_id, requirement_id)` — one row per customer per requirement.

---

## Glossary

| Term | Definition |
|---|---|
| KYC | Know Your Customer — regulatory identity and risk verification process |
| PEP | Politically Exposed Person — person in a prominent public function |
| Beneficial Owner | Individual who ultimately owns or controls a legal entity |
| Mandatory Requirement | A KYC document that must be verified for onboarding approval |
| Conditional Requirement | Required only under certain conditions (e.g. specific risk level) |
| Completeness | Percentage of mandatory requirements that have a verified document |
| Anomaly | A deliberately injected data quality or compliance exception |
| Ground Truth | Separate file listing the true labels for injected anomalies |
| Reference Date | The fixed date (2026-10-22) used for expiry and review calculations |
