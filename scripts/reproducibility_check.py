"""
Run this script to perform a reproducibility check:
generates data twice with the same seed and compares checksums.
"""
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from data_generator.generator import run_generator
from data_generator.validator import compute_checksums, run_validation
from app.db.session import SessionLocal


def run_reproducibility_check():
    print("=" * 60)
    print("REPRODUCIBILITY CHECK — Running generator twice")
    print("=" * 60)

    # Run 1
    print("\n--- Run 1 ---")
    summary1 = run_generator(mode="starter", seed=20261022)
    db1 = SessionLocal()
    checksums1 = compute_checksums(db1)
    validation1 = run_validation(db1)
    db1.close()

    # Run 2
    print("\n--- Run 2 ---")
    summary2 = run_generator(mode="starter", seed=20261022)
    db2 = SessionLocal()
    checksums2 = compute_checksums(db2)
    validation2 = run_validation(db2)
    db2.close()

    # Compare
    print("\n" + "=" * 60)
    print("COMPARISON RESULTS")
    print("=" * 60)

    all_match = True
    for table in checksums1:
        c1 = checksums1[table]
        c2 = checksums2[table]
        match = c1 == c2
        if not match:
            all_match = False
        status = "MATCH" if match else "MISMATCH"
        print(f"  [{status}] {table:40s}: run1={c1['count']} rows, run2={c2['count']} rows | "
              f"checksum1={c1['checksum'][:8]}..., checksum2={c2['checksum'][:8]}...")

    # Ground truth comparison
    gt1 = summary1.get("ground_truth", [])
    gt2 = summary2.get("ground_truth", [])
    gt_match = gt1 == gt2
    print(f"\n  Ground truth anomalies: run1={len(gt1)}, run2={len(gt2)} — {'MATCH' if gt_match else 'MISMATCH'}")

    if all_match and gt_match:
        print("\n✓ REPRODUCIBILITY CHECK PASSED — identical results across both runs")
    else:
        print("\n✗ REPRODUCIBILITY CHECK FAILED — results differ between runs")

    # Save report
    report = {
        "run1_checksums": checksums1,
        "run2_checksums": checksums2,
        "all_tables_match": all_match,
        "ground_truth_match": gt_match,
    }
    out = os.path.join(os.path.dirname(__file__), "..", "exports", "reproducibility_report.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\nReport saved to {os.path.abspath(out)}")

    return all_match and gt_match


if __name__ == "__main__":
    success = run_reproducibility_check()
    sys.exit(0 if success else 1)
