
"""Verification API endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.kyc_models import Verification, VerificationDecision

router = APIRouter()


@router.get("/")
def list_verifications(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    decision: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """List document verifications with optional decision filtering."""

    query = db.query(Verification)

    if decision:
        try:
            decision_value = VerificationDecision(decision.upper())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid verification decision: {decision}",
            )

        query = query.filter(
            Verification.decision == decision_value
        )

    verifications = (
        query
        .order_by(Verification.verified_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    return [
        {
            "verification_id": v.verification_id,
            "document_id": (
                v.document.document_id if v.document else None
            ),
            "verified_by": v.verified_by,
            "verified_at": (
                v.verified_at.isoformat() if v.verified_at else None
            ),
            "decision": v.decision.value,
            "decision_reason": v.decision_reason,
            "name_match": v.name_match,
            "name_on_document": v.name_on_document,
            "expiry_check_passed": v.expiry_check_passed,
            "authenticity_check_passed": v.authenticity_check_passed,
            "override_flag": v.override_flag,
            "override_reason": v.override_reason,
        }
        for v in verifications
    ]
