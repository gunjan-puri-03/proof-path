# ProofPath

## KYC & Compliance Management Platform

An integrated platform for customer onboarding, evidence
verification, KYC completeness, beneficial ownership,
risk monitoring, compliance alerts and audit tracking.
---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Prerequisites](#prerequisites)
3. [Quick Start](#quick-start)
4. [Database Setup](#database-setup)
5. [Running the Data Generator](#running-the-data-generator)
6. [Running the API](#running-the-api)
7. [Running Tests](#running-tests)
8. [Exporting Data](#exporting-data)
9. [Validation and Reproducibility](#validation-and-reproducibility)
10. [Project Structure](#project-structure)
11. [Architecture](#architecture)
12. [Data Model](#data-model)
13. [Business Rules Summary](#business-rules-summary)
14. [Anomaly Scenarios](#anomaly-scenarios)
15. [Ground Truth Files](#ground-truth-files)
16. [Known Limitations](#known-limitations)
17. [AI Transparency](#ai-transparency)

---

## Project Overview

This system tracks customer onboarding evidence, validates mandatory document completeness by customer type, records risk ratings, adjusts periodic review cadence by risk level, and generates alerts for expiring documents, overdue reviews, and anomalous conditions. Risk-specific mandatory-document selection is documented as a limitation, not yet implemented.

### Key capabilities

| Capability | Description |
|---|---|
| 10 Core Entities | Customer, CustomerType, KYCRequirement, Document, Verification, RiskRating, ReviewCase, BeneficialOwner, Alert, AuditEvent |
| 8,000 customers | Full-mode target volume, seed 20261022 (run locally to verify) |
| 20,000 documents | Full-mode target volume with issue dates, expiry dates and verification history |
| 1,000 business-type customers | Full-mode target; beneficial-owner data is generated, but the missing-ownership exception is not yet a generated baseline case |
| 3,000 review cases | Full-mode target volume: periodic, risk-change, alert-triggered |
| 5 anomaly scenarios | Injected and labelled in separate ground-truth files |
| FastAPI REST API | For customers, documents, reviews, and alerts |
| Alembic migrations | Versioned schema management |
| Pytest test suite | 39 collected tests covering models, logic, IDs, enums, and anomalies |

---

## Prerequisites

- Python 3.10 or later
- PostgreSQL 14 or later (running locally)
- pip

---

## Quick Start

```bash
# 1. Clone or unzip the project, then change into its root directory
cd path\to\Proof_Path

# 2. Create and activate a virtual environment (recommended)
python -m venv .venv
.venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy and configure environment variables
copy .env.example .env
# Edit .env to set your PostgreSQL credentials

# 5. Create the database user and database (see Database Setup below)

# 6. Run database migrations
python -m alembic upgrade head

# 7. Generate synthetic data (starter mode — fast)
python -m data_generator.generator --mode starter

# 8. Run tests
python -m pytest tests/ -v

# 9. Start the API server
python -m uvicorn app.main:app --reload
```

---

## Database Setup

Connect to PostgreSQL as a superuser and run:

```sql
CREATE USER kyc_user WITH PASSWORD 'kyc_password';
CREATE DATABASE yottaflex_kyc OWNER kyc_user;
GRANT ALL PRIVILEGES ON DATABASE yottaflex_kyc TO kyc_user;
```

Then set your `.env`:

```
DATABASE_URL=postgresql://kyc_user:kyc_password@localhost:5432/yottaflex_kyc
```

**Apply migrations:**

```bash
python -m alembic upgrade head
```

Alternatively, apply the raw DDL schema:

```bash
psql -U kyc_user -d yottaflex_kyc -f exports/sql/kyc_schema.sql
```

---

## Running the Data Generator

```bash
# Starter dataset (100 customers, 300 documents) — fast
python -m data_generator.generator --mode starter --seed 20261022

# Full dataset (8,000 customers, 20,000 documents, 3,000 reviews) — run against PostgreSQL
python -m data_generator.generator --mode full --seed 20261022
```

> **Important:** The generator clears existing data before generating. Run it once per environment. The full-mode target has not been completed and validated in the review environment; verify it against PostgreSQL before claiming full-volume acceptance.

**Fixed seed:** `20261022` — running with the same seed twice produces identical results.

---

## Running the API

```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API documentation is available at:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

**Run the React frontend in a second terminal:**

```bash
cd frontend
npm ci
npm run dev
```

Open the Vite URL printed in the terminal (normally http://localhost:5173). The frontend uses `http://127.0.0.1:8000` by default; set `VITE_API_BASE_URL` when the backend runs elsewhere.

**Key endpoints:**

| Method | Path | Description |
|---|---|---|
| GET | /api/v1/customers/ | List customers |
| GET | /api/v1/customers/{id} | Get customer by ID |
| GET | /api/v1/customers/{id}/kyc-decision | Evaluate onboarding decision |
| GET | /api/v1/documents/ | List documents |
| GET | /api/v1/reviews/ | List review cases |
| GET | /api/v1/alerts/ | List alerts |
| GET | /api/v1/alerts/?anomaly_only=true | List anomaly alerts only |

---

## Running Tests

```bash
# Run all tests using in-memory SQLite — no PostgreSQL server required
$env:DATABASE_URL = "sqlite:///:memory:"
python -m pytest tests/ -v
Remove-Item Env:DATABASE_URL

# Re-run with concise traceback output
python -m pytest tests/ -v --tb=short
```

The test suite covers:

- ID format conventions (all 9 ID types)
- Model instantiation (CustomerType, Customer, Document)
- Business logic (document validity, expiry, days until expiry)
- ID uniqueness (1,000+ IDs generated and checked)
- Date ordering constraints
- Anomaly label definitions
- Ownership validation (exceeds 100%)
- Risk level assignment (PEP, high-risk countries)
- Enum coverage (all enum values present)
- Review case lifecycle transitions

---

## Exporting Data

The generator CLI now exports all operational tables to CSV and JSON, writes a complete SQL seed file (without the former 500-row/table cap), and writes the separate ground-truth sidecar automatically:

```bash
python -m data_generator.generator --mode full --seed 20261022
```

To regenerate table exports from an already-populated database, run:

```bash
python -m data_generator.exporter
```

The standalone exporter does not reconstruct ground truth; run the generator command above to create the matching ground-truth CSV/JSON sidecar.

Exports are written to:

| Format | Location |
|---|---|
| CSV | `exports/csv/*.csv` |
| JSON | `exports/json/*.json` |
| SQL seed | `exports/sql/kyc_seed_data.sql` |
| Ground truth | `exports/csv/ground_truth_run1.csv`, `exports/json/ground_truth_run1.json` |
| Validation report | `exports/validation_report.json` |
| Reproducibility report | `exports/reproducibility_report.json` |

---

## Validation and Reproducibility

```bash
# Run validation checks
python -m data_generator.validator
```

Checks performed:

1. Primary key uniqueness across the core entities and bridge table
2. Foreign key integrity (all FK references valid)
3. Date ordering (issue_date ≤ expiry_date, onboarding ≤ approval)
4. Enum values (all statuses are valid)
5. Ownership reconciliation (detects > 100% anomaly)
6. KYC completeness (detects approved + 0% completeness anomaly)
7. Expired docs marked VERIFIED (anomaly 1)
8. Reviews closed without resolution (anomaly 4)
9. Duplicate document numbers (anomaly 5)
10. Ground truth anomaly alerts present

**Reproducibility test (runs the starter generator twice and compares all-table content checksums and ground-truth records):**

```powershell
$env:DATABASE_URL = "sqlite:///:memory:"
python -m scripts.reproducibility_check
Remove-Item Env:DATABASE_URL
```

The script writes `exports/reproducibility_report.json`. The starter-mode check was run during project review and passed. Run a separate full-mode generation and validation against PostgreSQL before reporting full-volume reproducibility.

---

## Project Structure

```
YottaFlex-KYC/
├── app/
│   ├── api/v1/           # FastAPI routers
│   │   ├── customers.py
│   │   ├── documents.py
│   │   ├── reviews.py
│   │   └── alerts.py
│   ├── core/
│   │   └── config.py     # Settings (pydantic-settings)
│   ├── db/
│   │   └── session.py    # SQLAlchemy engine + session
│   ├── models/
│   │   └── kyc_models.py # All 10 ORM entities + enums
│   ├── services/
│   │   └── kyc_service.py # Business logic
│   └── main.py           # FastAPI app entry point
├── data_generator/
│   ├── generator.py      # Synthetic data generator (seed 20261022)
│   ├── exporter.py       # CSV / JSON / SQL export
│   └── validator.py      # Validation and reproducibility checks
├── migrations/
│   ├── env.py            # Alembic env
│   └── versions/
│       └── 001_initial_schema.py
├── exports/
│   ├── csv/              # CSV exports + ground truth
│   ├── json/             # JSON exports + ground truth
│   └── sql/              # Schema DDL + seed SQL
├── docs/
│   ├── ARCHITECTURE.md
│   ├── KYC_BUSINESS_RULES.md
│   ├── KYC_DATA_DICTIONARY.md
│   ├── AI_PROMPT_HISTORY.md
│   └── SOURCE_MANIFEST.md
├── tests/
│   └── test_kyc.py       # 39 pytest tests
├── scripts/
│   └── reproducibility_check.py
├── .env.example
├── .gitignore
├── alembic.ini
├── pytest.ini
├── requirements.txt
└── README.md
```

---

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full architecture diagram and design rationale.

**High-level stack:**

```
PostgreSQL 18 ← SQLAlchemy 2.0 ← FastAPI ← HTTP clients
                      ↑
              Alembic (migrations)
                      ↑
         data_generator/ (Python + Faker)
```

---

## Data Model

10 core entities. See [docs/KYC_DATA_DICTIONARY.md](docs/KYC_DATA_DICTIONARY.md) for the full dictionary.

**ID conventions (immutable, deterministic):**

| Entity | Format | Example |
|---|---|---|
| Customer | CUS-NNNNNN | CUS-000001 |
| KYC Requirement | KYC-YYYY-NNNNNN | KYC-2026-000001 |
| Document | DOC-\<cust_id\>-NNN | DOC-CUS-000001-001 |
| Review Case | REV-\<cust_id\>-YYYY-NN | REV-CUS-000001-2026-01 |
| Alert | ALT-YYYY-NNNNNN | ALT-2026-000001 |
| Beneficial Owner | BO-\<cust_id\>-NNN | BO-CUS-000001-001 |
| Verification | VER-\<doc_id\>-NNN | VER-DOC-CUS-000001-001-001 |
| Audit Event | AUD-YYYY-NNNNNN | AUD-2026-000001 |
| Risk Rating | RR-\<cust_id\>-NNN | RR-CUS-000001-001 |

---

## Business Rules Summary

See [docs/KYC_BUSINESS_RULES.md](docs/KYC_BUSINESS_RULES.md) for the complete rule set.

Current rules and behavior:

- **Document completeness:** KYC completeness % = fulfilled mandatory requirements / total mandatory requirements × 100; mandatory requirements are selected by customer type.
- **Risk and reviews:** Risk ratings affect periodic review cadence (`periodic_review_months` adjusted by risk level: HIGH = −6 months, VERY_HIGH = −9 months).
- **Risk-specific evidence:** `risk_level_applicable` is present in the requirement model, but is not yet applied when selecting mandatory requirements; this remains a limitation.
- **Beneficial ownership:** Ownership records are generated for business-type customers; the required-missing-ownership exception is not yet part of baseline generation.
- **Document validity:** A document is valid only when verified and not expired as of the reference date.
- **Expiry alerts:** Triggered at configured lead times (including 30 days before expiry) and at expiry.
- **Audit history:** AuditEvent records are generated for selected generated events. Full coverage of every state change is not yet implemented, and document-event audit generation is currently capped at 5,000 documents.

---

## Anomaly Scenarios

Five specifically labelled anomalies are injected into the dataset:

| # | Label | Description | Entity |
|---|---|---|---|
| 1 | EXPIRED_BUT_MARKED_VALID | Document past expiry_date but document_status = VERIFIED | Document |
| 2 | APPROVED_WITH_MISSING_EVIDENCE | Customer approved with kyc_completeness_pct < 100% | Customer |
| 3 | OWNERSHIP_EXCEEDS_100 | Sum of beneficial_owner.ownership_percentage > 100% | BeneficialOwner |
| 4 | REVIEW_CLOSED_WITHOUT_RESOLUTION | Review case closed, closed_without_resolution = TRUE, resolution = NULL | ReviewCase |
| 5 | DUPLICATE_DOCUMENT_CROSS_CUSTOMER | Same document_number appears for two unrelated customers | Document |

Each anomaly has a corresponding ANOMALY_DETECTED alert with `is_anomaly = TRUE` and `anomaly_label` set.

---

## Ground Truth Files

Ground truth files are kept **separate** from operational data and must not be used as input features:

- `exports/csv/ground_truth_run1.csv`
- `exports/json/ground_truth_run1.json`

Each record contains: `anomaly_id`, `label`, `description`, `affected_entity`, `affected_id`, `customer_id`, `detail`. Operational CSV/JSON alert exports omit `is_anomaly` and `anomaly_label`; the separate sidecar is the label source. The SQL seed still reflects the Alert table schema, so downstream feature pipelines must explicitly exclude label columns.

---

## Known Limitations

1. The API does not implement full CRUD — it is read-only for now (GET endpoints only). Write operations go through the generator directly.
2. The SQLite test database uses string-typed enums (not PostgreSQL native enum types) — test coverage reflects the enum values, not the PG type definitions.
3. The check constraint on `beneficial_owners.ownership_percentage` only enforces 0–100 per individual owner, not the sum across owners (the sum validation is in the validator script and business logic layer).
4. File references in `Document.file_reference` are placeholder strings — no actual file storage is implemented.
5. Authentication and authorisation are not implemented in the API (out of scope per assignment brief).
6. Risk-specific mandatory KYC requirement selection is not yet enforced by the completeness calculation.
7. The generator does not yet produce a baseline customer with missing beneficial-owner records, despite documenting the exception rule.
8. Audit-event generation is incomplete: document audit events are capped at 5,000, and not every injected anomaly mutation has a corresponding event.
9. Full-mode (8,000 customer / 20,000 document / 3,000 review) generation, export and validation remain to be run locally against PostgreSQL; only starter-mode verification is included in this review package.

---

## AI Transparency

This project was built with AI assistance. See [docs/AI_PROMPT_HISTORY.md](docs/AI_PROMPT_HISTORY.md) for the full prompt history, what was AI-generated, what was reviewed, and what was modified.
