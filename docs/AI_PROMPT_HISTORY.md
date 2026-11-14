# AI Prompt History — YottaFlex KYC Project

This document records every prompt submitted to AI tools during the development of the YottaFlex KYC Onboarding Evidence Management System, in compliance with YottaFlex's AI transparency requirements.

---

## Format

Each entry records:
- **Date** — when the prompt was submitted
- **Tool** — which AI tool was used
- **Prompt** — exact or paraphrased prompt text
- **What AI helped implement** — specific output used
- **What I personally reviewed** — my review activity
- **What I modified** — changes I made
- **What I tested** — verification steps I ran
- **Known limitations** — honest assessment

---

## Session 1 — Project Kickoff

**Date:** 2026-11-13\
**Tool:** Antigravity (Claude Sonnet 4.6)

### Prompt 1.1 — Master Project Instruction

**Prompt text:**\
> MASTER PROJECT INSTRUCTION — YOTTAFLEX AI KYC ONBOARDING SYSTEM
> [Full 13-part specification covering data model, tech stack, synthetic data generation, business rules, anomalies, deliverables, and GitHub preparation]

**What AI helped implement:**
- Created the full project directory structure under `D:\project\YottaFlex-KYC`
- Wrote `app/models/kyc_models.py` — all 10 SQLAlchemy ORM entities with enums, FK constraints, indexes, and check constraints
- Wrote `app/core/config.py` — pydantic-settings configuration
- Wrote `app/db/session.py` — SQLAlchemy engine and session dependency
- Wrote `app/services/kyc_service.py` — KYC completeness calculation, document validity, ownership validation, review scheduling, onboarding decision logic
- Wrote `data_generator/generator.py` — full synthetic data generator (8,000 customers, 20,000 documents, 3,000 reviews, 5 anomalies), fixed seed 20261022
- Wrote `data_generator/exporter.py` — CSV, JSON, SQL export logic
- Wrote `data_generator/validator.py` — 15 validation checks and checksum computation
- Wrote `app/main.py` — FastAPI application entry point
- Wrote `app/api/v1/` — customer, document, review, and alert API endpoints
- Wrote `migrations/versions/001_initial_schema.py` — full Alembic migration
- Wrote `exports/sql/kyc_schema.sql` — complete PostgreSQL DDL with views
- Wrote `tests/test_kyc.py` — current suite contains 39 pytest tests after review
- Wrote `README.md` — complete setup and execution documentation
- Wrote `docs/ARCHITECTURE.md` — architecture documentation
- Wrote `docs/KYC_BUSINESS_RULES.md` — business rules documentation
- Wrote `docs/KYC_DATA_DICTIONARY.md` — full data dictionary
- Wrote `docs/SOURCE_MANIFEST.md` — source manifest
- Wrote `.env.example`, `.gitignore`, `requirements.txt`, `pytest.ini`, `alembic.ini`

**What I personally reviewed:**
- [ ] I need to review `kyc_models.py` — especially the enum definitions and FK relationships to verify they match the specification
- [ ] I need to review `generator.py` — specifically the anomaly injection logic (Steps 12–13) and the ID generation functions
- [ ] I need to review `kyc_service.py` — the completeness calculation formula and onboarding decision logic
- [ ] I need to review the validation checks in `validator.py` — especially checks 7–10 that detect the five anomalies
- [ ] I need to run the test suite and verify all tests pass
- [ ] I need to run the data generator with --mode starter and verify record counts
- [ ] I need to review the API endpoints and test at least the /customers/ and /kyc-decision endpoints

**What I modified:**
- [To be filled in after personal review and testing]

**What I tested:**
- [To be filled in after running the test suite and generator]

**Known limitations:**
- The AI-generated generator is comprehensive but may need tuning of the CDR (customer_document_requirements) logic once run against a real PostgreSQL instance — the ORM session management in `update_kyc_completeness` uses `bulk_save_objects` which may need testing against the actual schema
- The anomaly injection for Anomaly 2 selects customers by completeness but uses an index-based selection that could select the same customer as another anomaly — worth checking for overlap after running
- The check constraint on beneficial_owners only enforces 0–100 per individual (not the sum), which is by design — the sum validation is intentionally in application logic and the validator
- SQLite is used for unit tests (avoids PostgreSQL dependency), which means PostgreSQL-specific features like enum types are tested as VARCHARs only

---

## Notes on AI Involvement

The YottaFlex assignment explicitly permits AI tool use. The purpose of this log is to:

1. Be transparent about which parts of the codebase were AI-assisted
2. Record my personal understanding, review, and testing
3. Demonstrate that I understand the implementation well enough to explain and defend it

This log will be updated continuously as the project develops.

---

## Understanding I Can Demonstrate

The following are areas I personally understand and can explain in an interview:

### Data Model
- Why both a surrogate PK (`id`) and a business key (`customer_id`) are used
- The difference between MANDATORY, CONDITIONAL, and OPTIONAL KYC requirements
- How `effective_from` / `effective_to` creates a risk rating history without deleting records
- The role of the `customer_document_requirements` bridge table

### Business Logic\
- How `kyc_completeness_pct` is calculated (fulfilled mandatory requirements / total mandatory requirements)
- Why the check constraint on `beneficial_owners.ownership_percentage` only enforces individual range (not sum)
- How the onboarding decision evaluates all conditions before returning APPROVE or REFER

### Anomalies
- Each of the 5 anomaly labels and what database condition they represent
- Why ground truth is kept separate from operational data
- How `is_anomaly = TRUE` and `anomaly_label` on the alerts table serve as the ground truth link

### Generator
- Why both `random.seed()` and `Faker.seed()` must be set for full reproducibility
- How the generation order respects FK dependencies (customer_types → customers → documents → verifications → CDR)
- Why the generator clears tables before regenerating (to avoid duplicate business key violations)

### Architecture
- Why PostgreSQL is used over SQLite for production (enum types, check constraints, full ACID)
- Why SQLite is used for tests (zero-dependency, fast, portable)
- The FastAPI dependency injection pattern for database sessions (`Depends(get_db)`)


## Session 2 — ChatGPT project review and GitHub preparation

**Date:** 2026-11-14\
**Tool:** ChatGPT (GPT-6)

### Prompt record

The candidate provided the complete YottaFlex project specification in the conversation, then asked for the existing Proof_Path project ZIP to be checked and for help publishing it to a new public GitHub repository. The exact full project brief is retained in the conversation transcript; this entry summarizes the prompt rather than duplicating the full brief. The candidate should attach/export the exact prompt text and any other prompts used with ChatGPT or other tools before final submission.

### AI-assisted changes made during review

- Fixed leap-day expiry-date arithmetic by adding a calendar-year helper that clamps February 29 to February 28 when the target year is not a leap year.
- Made the full-mode business-customer target deterministic at exactly 1,000 for the 8,000-customer dataset; starter mode uses 12 business customers for proportional smoke testing.
- Updated the database engine configuration to support in-memory SQLite test URLs.
- Removed the 500-row-per-table SQL seed export limit.
- Expanded JSON export coverage to all generated tables, excluded anomaly label columns from operational alert CSV/JSON exports, and wired the generator CLI to export the separate ground-truth sidecar.
- Added a leap-day regression test and adjusted `.gitignore` so local environments/backups stay excluded while generated deliverable exports remain trackable.
- Updated README and source-manifest statements to match the observed 39-test suite and current limitations.
- Made generation timestamps deterministic and expanded reproducibility checks to hash complete row content across all generated tables, rather than comparing only identifiers.

### What the candidate personally reviewed

- [ ] Review every AI-assisted code change above and confirm it is understood.
- [ ] Review the risk-based KYC completeness limitation and decide whether to implement risk-specific requirement rules before submission.
- [ ] Review the missing-beneficial-owner coverage and incomplete audit-event coverage before submission.

### What was tested in this review

- `DATABASE_URL=sqlite:///:memory: python -m pytest -q` — **39 passed** (15 deprecation warnings).
- Starter generator with seed `20261022` — completed with 100 customers, 300 documents, 50 review cases, 12 business customers and 5 labelled anomalies.
- Starter validator — **25/25 checks passed**.
- Starter exporter — emitted CSV/JSON for all 11 tables, separate ground-truth CSV/JSON, and SQL seed output.
- Full-mode generation was attempted in the review environment but did not complete within the execution window using SQLite. The full-mode output must still be run and validated locally against PostgreSQL before claiming full-volume verification.

### Known limitations / candidate actions

- The current completeness calculation does not yet apply `risk_level_applicable` to KYC requirements.
- Missing beneficial-owner records are described in business rules but are not generated as a baseline exception.
- Document audit events are capped at 5,000 rows, and anomaly-injection state changes are not all appended to audit history.
- The original AI prompt history from the earlier Antigravity session is abbreviated in this file. The candidate must add the exact original prompt(s), all other prompts submitted to every AI tool, and accurate personal review notes; do not mark unchecked items complete unless personally done. This current ChatGPT conversation should also be included in the prompt-history record (the complete user prompt is available in the conversation transcript).
