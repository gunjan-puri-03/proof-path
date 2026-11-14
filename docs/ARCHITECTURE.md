# YottaFlex KYC – Architecture Documentation

## System Overview

The YottaFlex KYC Onboarding Evidence Management System is a backend-only, locally runnable Python application. It tracks customer onboarding evidence, enforces KYC business rules, generates synthetic data, and exposes a REST API.

## Component Diagram

```
┌─────────────────────────────────────────────────────┐
│                   FastAPI Application                │
│  /api/v1/customers   /documents   /reviews  /alerts  │
└──────────────────────────┬──────────────────────────┘
                           │ SQLAlchemy ORM
┌──────────────────────────▼──────────────────────────┐
│                   PostgreSQL 18                      │
│  10 core tables + bridge + 4 views                   │
│  Alembic migration: 001_initial_schema               │
└──────────────────────────┬──────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────┐
│              Data Generator (Python)                 │
│  generator.py  │  exporter.py  │  validator.py       │
│  Fixed seed: 20261022                                │
└─────────────────────────────────────────────────────┘
```

## Technology Stack

| Layer | Technology | Version |
|---|---|---|
| Database | PostgreSQL | 18.x |
| ORM | SQLAlchemy | 2.0.x |
| Migrations | Alembic | 1.20.x |
| API framework | FastAPI | 0.162.x |
| ASGI server | Uvicorn | 0.54.x |
| Data validation | Pydantic | 2.14.x |
| Synthetic data | Faker | 40.x |
| Test framework | Pytest | 9.2.x |
| Config management | pydantic-settings | 2.16.x |
| Language | Python | 3.12.x |

## Entity Relationship Overview

```
CustomerType (1) ──────────── (N) Customer
                                        │
                               ┌────────┼────────────────┐
                               │        │                 │
                             (N)     (N) RiskRating    (N) ReviewCase
                           Document         │               │
                               │            │            (N) Alert
                             (N)            │
                         Verification     (N) BeneficialOwner

Customer ──── (N) AuditEvent
Customer ──── (N) CustomerDocumentRequirement ──── KYCRequirement
```

## Key Design Decisions

### 1. String-based business IDs (immutable)
Each entity has both a surrogate integer PK (`id`) for internal FK joins (performance) and an immutable string business key (`customer_id`, `document_id`, etc.) for external references. Business keys follow the specified convention and are never changed after creation.

### 2. Enum as Python + PostgreSQL strings
Enums are defined as Python `str(enum.Enum)` subclasses and stored as `VARCHAR` in PostgreSQL. This avoids PostgreSQL ALTER TYPE operations during schema evolution while keeping Python type safety.

### 3. Soft history via effective dates
Risk ratings use `effective_from` / `effective_to` for history. The current rating has `effective_to = NULL`. Historical records are never deleted.

### 4. KYC completeness as a derived field
`kyc_completeness_pct` is stored on the Customer record as a cached computed value, recalculated whenever documents are verified or requirements change. The authoritative calculation is in `kyc_service.calculate_kyc_completeness()`.

### 5. Anomaly injection as explicit data surgery
The five required anomalies are injected after the full valid dataset is generated. Each injection modifies specific records in-place and raises a corresponding Alert with `is_anomaly = TRUE` and a labelled `anomaly_label`. Ground truth is recorded separately — never as an operational input column.

### 6. Deterministic generation with fixed seed
Both `random.seed(20261022)` and `Faker.seed(20261022)` are set before any generation. Running with the same seed and mode produces identical row counts, checksums, and ground-truth records.

## Data Flow

```
1. seed_customer_types()      →  customer_types (7 rows)
2. seed_kyc_requirements()    →  kyc_requirements (27 rows)
3. generate_customers()       →  customers (8,000)
4. generate_risk_ratings()    →  risk_ratings (8,000)
5. populate_review_dates()    →  customers.next_review_date updated
6. generate_beneficial_owners() → beneficial_owners (~2,000+)
7. generate_documents()       →  documents (20,000)
8. generate_verifications()   →  verifications (~14,000)
9. update_kyc_completeness()  →  customers.kyc_completeness_pct updated
                                 customer_document_requirements (~40,000)
10. generate_review_cases()   →  review_cases (3,000)
11. generate_alerts()         →  alerts (~variable)
12. generate_audit_events()   →  audit_events (~variable)
13. inject_anomalies()        →  modifies 5 specific records + 5 anomaly alerts
```

## Security Considerations

- Database credentials are environment-variable driven (never hardcoded)
- `.env` is git-ignored; `.env.example` is provided
- No PII is real — all data is synthetic (Faker)
- No external network calls — fully offline
- No authentication in the API (out of scope per spec)

## Scalability Notes

- The SQLAlchemy engine uses a connection pool (pool_size=10, max_overflow=20)
- Bulk operations use `db.bulk_save_objects()` for CDR records
- Indexes are created on all FK columns and commonly filtered fields
- The generator uses `db.flush()` every 500 records to manage memory
