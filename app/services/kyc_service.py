"""
Business logic services for KYC operations.
"""
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List, Optional
from sqlalchemy.orm import Session

from app.models.kyc_models import (
    Customer, Document, DocumentStatus, OnboardingStatus, ReviewCase,
    ReviewCaseStatus, Alert, AlertType, AlertSeverity, AlertStatus,
    AuditEvent, AuditAction, BeneficialOwner, RiskLevel,
    CustomerDocumentRequirement, KYCRequirement, RequirementType,
)


# ---------------------------------------------------------------------------
# KYC Completeness Calculation
# ---------------------------------------------------------------------------

def calculate_kyc_completeness(customer: Customer, db: Session) -> Decimal:
    """
    Calculate KYC completeness percentage for a customer.
    Only mandatory requirements count toward completeness.
    Returns a Decimal between 0.00 and 100.00.
    """
    requirements = db.query(KYCRequirement).filter(
        KYCRequirement.customer_type_id == customer.customer_type_id,
        KYCRequirement.requirement_type == RequirementType.MANDATORY,
        KYCRequirement.is_active == True,
    ).all()

    if not requirements:
        return Decimal("100.00")

    fulfilled_count = 0
    for req in requirements:
        # Check if there is a verified document for this requirement
        cdreq = db.query(CustomerDocumentRequirement).filter(
            CustomerDocumentRequirement.customer_id == customer.id,
            CustomerDocumentRequirement.requirement_id == req.id,
            CustomerDocumentRequirement.is_fulfilled == True,
        ).first()
        if cdreq:
            fulfilled_count += 1

    pct = Decimal(str(round(fulfilled_count / len(requirements) * 100, 2)))
    return pct


# ---------------------------------------------------------------------------
# Document Validity Check
# ---------------------------------------------------------------------------

def is_document_valid(doc: Document, as_of: date = None) -> bool:
    """Return True if document is not expired and status is VERIFIED."""
    check_date = as_of or date.today()
    if doc.document_status not in (DocumentStatus.VERIFIED,):
        return False
    if doc.expiry_date and doc.expiry_date < check_date:
        return False
    return True


def days_until_expiry(doc: Document, as_of: date = None) -> Optional[int]:
    """Return number of days until document expires; None if no expiry date."""
    if not doc.expiry_date:
        return None
    check_date = as_of or date.today()
    return (doc.expiry_date - check_date).days


# ---------------------------------------------------------------------------
# Beneficial Owner Validation
# ---------------------------------------------------------------------------

def validate_ownership_percentages(business_customer: Customer, db: Session) -> dict:
    """
    Validate that ownership percentages for a business customer are consistent.
    Returns dict with 'valid', 'total_pct', 'owners' keys.
    """
    owners = db.query(BeneficialOwner).filter(
        BeneficialOwner.business_customer_id == business_customer.id,
        BeneficialOwner.is_active == True,
    ).all()

    total_pct = sum(float(o.ownership_percentage) for o in owners)
    return {
        "valid": total_pct <= 100.0,
        "total_pct": total_pct,
        "owner_count": len(owners),
        "owners": [{"bo_id": o.bo_id, "name": o.full_name, "pct": float(o.ownership_percentage)} for o in owners],
    }


# ---------------------------------------------------------------------------
# Review Scheduling
# ---------------------------------------------------------------------------

def calculate_next_review_date(customer: Customer, risk_level: RiskLevel) -> date:
    """
    Calculate next review date based on customer type and risk level.
    Higher risk = more frequent review.
    """
    base_months = customer.customer_type.periodic_review_months if customer.customer_type else 12
    risk_adjustments = {
        RiskLevel.LOW: 0,
        RiskLevel.MEDIUM: -3,
        RiskLevel.HIGH: -6,
        RiskLevel.VERY_HIGH: -9,
    }
    adjusted_months = max(3, base_months + risk_adjustments.get(risk_level, 0))
    start = customer.approved_date or date.today()
    # Add months (approximate)
    review_date = date(start.year + (start.month + adjusted_months - 1) // 12,
                       (start.month + adjusted_months - 1) % 12 + 1,
                       min(start.day, 28))
    return review_date


# ---------------------------------------------------------------------------
# Onboarding Decision
# ---------------------------------------------------------------------------

def evaluate_onboarding_decision(customer: Customer, db: Session) -> dict:
    """
    Evaluate whether a customer can be approved for onboarding.
    Returns dict with decision, reasons, completeness_pct.
    """
    reasons = []
    completeness = calculate_kyc_completeness(customer, db)

    if completeness < Decimal("100.00"):
        reasons.append(f"KYC completeness {completeness}% — mandatory documents missing")

    # Check beneficial ownership if applicable
    if customer.customer_type and customer.customer_type.requires_beneficial_owner:
        ownership_check = validate_ownership_percentages(customer, db)
        if ownership_check["owner_count"] == 0:
            reasons.append("No beneficial owners recorded")
        if not ownership_check["valid"]:
            reasons.append(f"Ownership percentages total {ownership_check['total_pct']:.2f}% (exceeds 100%)")

    # Check for expired mandatory documents
    docs = db.query(Document).filter(Document.customer_id == customer.id).all()
    for doc in docs:
        if doc.is_mandatory and doc.expiry_date and doc.expiry_date < date.today():
            reasons.append(f"Mandatory document {doc.document_id} is expired")

    can_approve = len(reasons) == 0
    return {
        "can_approve": can_approve,
        "decision": "APPROVE" if can_approve else "REFER",
        "reasons": reasons,
        "completeness_pct": float(completeness),
    }
