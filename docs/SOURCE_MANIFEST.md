# YottaFlex KYC – Source Manifest

Generated: 2026-11-14\
Project root: `Proof_Path` (local checkout path is environment-specific)

---

## Source Files

| File | Purpose | Lines (approx) |
|---|---|---|
| `app/__init__.py` | Package init | 1 |
| `app/main.py` | FastAPI app entry point | 25 |
| `app/core/__init__.py` | Package init | 1 |
| `app/core/config.py` | Settings management (pydantic-settings) | 30 |
| `app/db/__init__.py` | Package init | 1 |
| `app/db/session.py` | SQLAlchemy engine + session | 25 |
| `app/models/__init__.py` | Package init | 1 |
| `app/models/kyc_models.py` | All 10 ORM entities + enums + bridge | ~400 |
| `app/services/__init__.py` | Package init | 1 |
| `app/services/kyc_service.py` | Business logic layer | ~120 |
| `app/api/__init__.py` | Package init | 1 |
| `app/api/v1/__init__.py` | API v1 router assembly | 10 |
| `app/api/v1/router.py` | Router stub | 2 |
| `app/api/v1/customers.py` | Customer API endpoints | 60 |
| `app/api/v1/documents.py` | Document API endpoints | 40 |
| `app/api/v1/reviews.py` | Review API endpoints | 35 |
| `app/api/v1/alerts.py` | Alert API endpoints | 35 |
| `data_generator/__init__.py` | Package init | 1 |
| `data_generator/generator.py` | Synthetic data generator (seed 20261022) | ~700 |
| `data_generator/exporter.py` | CSV / JSON / SQL export | ~150 |
| `data_generator/validator.py` | Validation and checksums | ~180 |
| `migrations/env.py` | Alembic env configuration | 45 |
| `migrations/script.py.mako` | Alembic migration template | 25 |
| `migrations/versions/001_initial_schema.py` | Initial schema migration | ~220 |
| `tests/__init__.py` | Package init | 1 |
| `tests/test_kyc.py` | Pytest suite (39 tests at last verification) | ~380 |

## Configuration Files

| File | Purpose |
|---|---|
| `.env.example` | Environment variable template |
| `.gitignore` | Git ignore rules |
| `alembic.ini` | Alembic configuration |
| `pytest.ini` | Pytest configuration |
| `requirements.txt` | Python dependencies |

## Documentation

| File | Purpose |
|---|---|
| `README.md` | Complete setup and execution guide |
| `docs/ARCHITECTURE.md` | Architecture diagram and design decisions |
| `docs/KYC_BUSINESS_RULES.md` | All business rules documented |
| `docs/KYC_DATA_DICTIONARY.md` | Full data dictionary for all 11 tables |
| `docs/AI_PROMPT_HISTORY.md` | AI transparency log |
| `docs/SOURCE_MANIFEST.md` | This file |

## Generated Artifacts

| File | Purpose |
|---|---|
| `exports/sql/kyc_schema.sql` | PostgreSQL DDL schema + views |
| `exports/sql/kyc_seed_data.sql` | SQL INSERT seed data (all rows in generated tables) |
| `exports/csv/*.csv` | CSV exports of all tables |
| `exports/json/*.json` | JSON exports of key tables |
| `exports/csv/ground_truth_run1.csv` | Anomaly ground truth (CSV) |
| `exports/json/ground_truth_run1.json` | Anomaly ground truth (JSON) |
| `exports/validation_report.json` | Starter dataset validation and checksum results (25/25 checks passed in review) |
| `exports/reproducibility_report.json` | Starter-mode table-content checksum comparison across two runs |

## Dependency Summary

| Package | Version | Purpose |
|---|---|---|
| fastapi | 0.162.x | REST API framework |
| uvicorn | 0.54.x | ASGI server |
| sqlalchemy | 2.0.x | ORM (pre-installed) |
| alembic | 1.20.x | Database migrations |
| pydantic | 2.14.x | Data validation |
| pydantic-settings | 2.16.x | Settings management |
| psycopg2-binary | 2.9.x | PostgreSQL driver |
| faker | 40.x | Synthetic data generation |
| pytest | 9.2.x | Test framework |
| pytest-asyncio | 1.5.x | Async test support |
| python-dotenv | 1.2.x | Environment variable loading |
| httpx | 0.28.x | HTTP client for testing |
