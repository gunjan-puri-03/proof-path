"""
Validation and reproducibility checks for the generated dataset.
"""
import json
import hashlib
import csv
import os
from datetime import date
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.db.session import SessionLocal


REFERENCE_DATE = date(2026, 10, 22)


def run_validation(db: Session) -> dict:
    """
    Run all validation checks. Returns a dict with:
    - check name
    - pass/fail
    - detail message
    - affected count
    """
    results = []

    def check(name: str, query: str, expect_zero: bool = True, description: str = ""):
        rows = db.execute(text(query)).fetchall()
        count = len(rows)
        passed = (count == 0) if expect_zero else (count > 0)
        results.append({
            "check": name,
            "passed": passed,
            "affected_count": count,
            "description": description,
            "sample": str(rows[:3]) if rows else "none",
        })
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {name}: {count} issue(s)")
        return passed

    print("\n=== Validation Report ===")

    # 1. PK Uniqueness
    for tbl, pk_col in [
        ("customers", "customer_id"),
        ("documents", "document_id"),
        ("kyc_requirements", "requirement_id"),
        ("review_cases", "review_id"),
        ("alerts", "alert_id"),
        ("beneficial_owners", "bo_id"),
        ("verifications", "verification_id"),
        ("audit_events", "audit_id"),
        ("risk_ratings", "risk_rating_id"),
    ]:
        check(
            f"PK uniqueness: {tbl}.{pk_col}",
            f"SELECT {pk_col}, COUNT(*) c FROM {tbl} GROUP BY {pk_col} HAVING COUNT(*) > 1",
            expect_zero=True,
            description=f"No duplicate {pk_col} in {tbl}",
        )

    # 2. FK Integrity
    check("FK: documents.customer_id", """
        SELECT d.document_id FROM documents d
        LEFT JOIN customers c ON d.customer_id = c.id
        WHERE c.id IS NULL
    """, expect_zero=True, description="All documents reference valid customers")

    check("FK: verifications.document_id", """
        SELECT v.verification_id FROM verifications v
        LEFT JOIN documents d ON v.document_id = d.id
        WHERE d.id IS NULL
    """, expect_zero=True, description="All verifications reference valid documents")

    check("FK: risk_ratings.customer_id", """
        SELECT r.risk_rating_id FROM risk_ratings r
        LEFT JOIN customers c ON r.customer_id = c.id
        WHERE c.id IS NULL
    """, expect_zero=True, description="All risk_ratings reference valid customers")

    check("FK: review_cases.customer_id", """
        SELECT rev.review_id FROM review_cases rev
        LEFT JOIN customers c ON rev.customer_id = c.id
        WHERE c.id IS NULL
    """, expect_zero=True, description="All review_cases reference valid customers")

    check("FK: beneficial_owners.business_customer_id", """
        SELECT bo.bo_id FROM beneficial_owners bo
        LEFT JOIN customers c ON bo.business_customer_id = c.id
        WHERE c.id IS NULL
    """, expect_zero=True, description="All beneficial_owners reference valid customers")

    # 3. Date ordering
    check("Date order: documents issue_date <= expiry_date", """
        SELECT document_id FROM documents
        WHERE expiry_date IS NOT NULL AND issue_date > expiry_date
    """, expect_zero=True, description="Issue date must be before expiry date")

    check("Date order: customers onboarding_date <= approved_date", """
        SELECT customer_id FROM customers
        WHERE approved_date IS NOT NULL AND onboarding_date > approved_date
    """, expect_zero=True, description="Onboarding date must precede approval date")

    check("Date order: review opened_at <= closed_at", """
        SELECT review_id FROM review_cases
        WHERE closed_at IS NOT NULL AND opened_at > closed_at
    """, expect_zero=True, description="Review opened before closed")

    # 4. Enum values
    check("Enum: documents.document_status valid", """
        SELECT document_id FROM documents
        WHERE document_status NOT IN ('PENDING','SUBMITTED','VERIFIED','REJECTED','EXPIRED','SUPERSEDED')
    """, expect_zero=True, description="All document statuses are valid enum values")

    check("Enum: customers.onboarding_status valid", """
        SELECT customer_id FROM customers
        WHERE onboarding_status NOT IN ('PENDING','IN_PROGRESS','APPROVED','REJECTED','SUSPENDED','EXPIRED')
    """, expect_zero=True, description="All onboarding statuses are valid")

    # 5. Ownership reconciliation
    check("Ownership > 100% (should catch anomaly 3)", """
        SELECT bo.business_customer_id, SUM(bo.ownership_percentage) total
        FROM beneficial_owners bo
        WHERE bo.is_active = TRUE
        GROUP BY bo.business_customer_id
        HAVING SUM(bo.ownership_percentage) > 100.0
    """, expect_zero=False, description="Detects ownership exceeds 100% (anomaly 3 exists)")

    # 6. KYC completeness
    check("Approved customers with 0% KYC completeness", """
        SELECT customer_id FROM customers
        WHERE onboarding_status = 'APPROVED' AND kyc_completeness_pct = 0
    """, expect_zero=False, description="Detects anomaly 2 — approved with missing evidence")

    # 7. Expired docs marked VERIFIED
    check("Expired documents marked VERIFIED (anomaly 1)", """
        SELECT d.document_id FROM documents d
        WHERE d.expiry_date IS NOT NULL
          AND d.expiry_date < '2026-10-22'
          AND d.document_status = 'VERIFIED'
          AND d.notes LIKE '%ANOMALY%'
    """, expect_zero=False, description="Detects anomaly 1 — expired doc marked verified")

    # 8. Reviews closed without resolution
    check("Reviews closed without resolution (anomaly 4)", """
        SELECT review_id FROM review_cases
        WHERE closed_without_resolution = TRUE
    """, expect_zero=False, description="Detects anomaly 4")

    # 9. Duplicate document numbers across customers
    check("Duplicate document numbers (anomaly 5)", """
        SELECT d.document_number, COUNT(DISTINCT d.customer_id) cnt
        FROM documents d
        WHERE d.document_number IS NOT NULL
        GROUP BY d.document_number
        HAVING COUNT(DISTINCT d.customer_id) > 1
    """, expect_zero=False, description="Detects anomaly 5 — duplicate doc numbers")

    # 10. Ground truth anomaly alerts
    check("Ground truth anomaly alerts present", """
        SELECT alert_id FROM alerts WHERE is_anomaly = TRUE
    """, expect_zero=False, description="Anomaly alerts must exist")

    # 11. Record counts
    counts = {}
    for tbl in ["customers", "documents", "verifications", "review_cases",
                "alerts", "audit_events", "beneficial_owners", "risk_ratings"]:
        cnt = db.execute(text(f"SELECT COUNT(*) FROM {tbl}")).scalar()
        counts[tbl] = cnt
        results.append({
            "check": f"record_count:{tbl}",
            "passed": cnt > 0,
            "affected_count": cnt,
            "description": f"{tbl} has {cnt} records",
            "sample": "n/a",
        })
        print(f"  [COUNT] {tbl}: {cnt}")

    # Summary
    total = len([r for r in results if "record_count" not in r["check"]])
    passed_count = sum(1 for r in results if r["passed"] and "record_count" not in r["check"])
    print(f"\n=== Validation Summary: {passed_count}/{total} checks passed ===\n")

    return {"results": results, "record_counts": counts, "passed": passed_count, "total": total}


def compute_checksums(db: Session) -> dict:
    """Compute row counts and SHA-256 checksums over complete table contents."""
    checksums = {}
    tables = ["customer_types", "customers", "kyc_requirements", "documents",
              "verifications", "risk_ratings", "review_cases", "beneficial_owners",
              "alerts", "audit_events", "customer_document_requirements"]

    for tbl in tables:
        result = db.execute(text(f"SELECT * FROM {tbl} ORDER BY id"))
        digest = hashlib.sha256()
        count = 0
        for row in result.fetchall():
            payload = json.dumps(list(row), default=str, separators=(",", ":"))
            digest.update(payload.encode("utf-8"))
            digest.update(b"\n")
            count += 1
        checksum = digest.hexdigest()
        checksums[tbl] = {"count": count, "checksum": checksum}
        print(f"  {tbl:40s}: count={count}, checksum={checksum[:12]}...")

    return checksums


if __name__ == "__main__":
    db = SessionLocal()
    try:
        print("Running validation...")
        val_result = run_validation(db)

        print("\nComputing checksums...")
        checksums = compute_checksums(db)

        # Save validation report
        report = {
            "validation": val_result,
            "checksums": checksums,
        }
        out_path = os.path.join(os.path.dirname(__file__), '..', 'exports', 'validation_report.json')
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        print(f"\nValidation report saved to {out_path}")
    finally:
        db.close()
