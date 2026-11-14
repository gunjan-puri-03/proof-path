
"""
Customers API endpoints.
Includes Customer 360 degree activity history.
"""

from datetime import date, datetime, time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db

from app.models.kyc_models import (
    Customer,
    OnboardingStatus,
    Document,
    Verification,
    RiskRating,
    ReviewCase,
    Alert,
    AuditEvent,
)

from app.services.kyc_service import (
    evaluate_onboarding_decision,
)

router = APIRouter()


# --------------------------------------------------
# SERIALIZATION HELPERS
# --------------------------------------------------

def enum_value(value):
    if value is None:
        return None

    return value.value if hasattr(value, "value") else value


def iso_value(value):
    return value.isoformat() if value is not None else None


def sort_timestamp(value):
    if isinstance(value, datetime):
        return value.timestamp()

    if isinstance(value, date):
        return datetime.combine(value, time.min).timestamp()

    return 0.0


def make_timeline_event(
    event_type,
    event_id,
    title,
    description,
    event_date,
    status=None,
    performed_by=None,
):
    return {
        "event_type": event_type,
        "event_id": str(event_id) if event_id else None,
        "title": title,
        "description": description,
        "timestamp": iso_value(event_date),
        "status": enum_value(status),
        "performed_by": performed_by,
        "_sort_timestamp": sort_timestamp(event_date),
    }


# --------------------------------------------------
# CUSTOMER LIST
# --------------------------------------------------

@router.get("/")
def list_customers(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """List customers with optional onboarding status filter."""

    q = db.query(Customer)

    if status:
        try:
            q = q.filter(
                Customer.onboarding_status == OnboardingStatus(status)
            )
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status: {status}",
            )

    customers = q.offset(skip).limit(limit).all()

    return [
        {
            "customer_id": c.customer_id,
            "full_name": c.full_name,
            "customer_type": (
                enum_value(c.customer_type.code)
                if c.customer_type else None
            ),
            "onboarding_status": enum_value(c.onboarding_status),
            "kyc_completeness_pct": float(
                c.kyc_completeness_pct or 0
            ),
            "next_review_date": iso_value(c.next_review_date),
            "country_of_residence": c.country_of_residence,
        }
        for c in customers
    ]


# --------------------------------------------------
# CUSTOMER 360 PROFILE
# --------------------------------------------------

@router.get("/{customer_id}/activity")
def get_customer_activity(
    customer_id: str,
    db: Session = Depends(get_db),
):
    """
    Return a complete customer compliance profile,
    associated records and chronological activity timeline.
    """

    # Find customer using public customer ID.
    customer = (
        db.query(Customer)
        .filter(Customer.customer_id == customer_id)
        .first()
    )

    if not customer:
        raise HTTPException(
            status_code=404,
            detail="Customer not found",
        )

    internal_id = customer.id

    # --------------------------------------------------
    # 1. CUSTOMER PROFILE
    # --------------------------------------------------

    customer_data = {
        "customer_id": customer.customer_id,
        "full_name": customer.full_name,

        "customer_type": (
            enum_value(customer.customer_type.code)
            if customer.customer_type else None
        ),

        "onboarding_status": enum_value(
            customer.onboarding_status
        ),

        "kyc_completeness_pct": float(
            customer.kyc_completeness_pct or 0
        ),

        "date_of_birth": iso_value(customer.date_of_birth),
        "nationality": customer.nationality,
        "country_of_residence": customer.country_of_residence,

        "email": customer.email,
        "phone": customer.phone,

        "address_line1": customer.address_line1,
        "address_line2": customer.address_line2,
        "city": customer.city,
        "state_province": customer.state_province,
        "postal_code": customer.postal_code,
        "country": customer.country,

        "is_pep": bool(customer.is_pep),
        "is_sanctioned": bool(customer.is_sanctioned),

        "source_of_funds": customer.source_of_funds,

        "business_name": customer.business_name,
        "business_registration_number": (
            customer.business_registration_number
        ),

        "onboarding_date": iso_value(customer.onboarding_date),
        "approved_date": iso_value(customer.approved_date),
        "next_review_date": iso_value(customer.next_review_date),

        "created_at": iso_value(customer.created_at),
        "updated_at": iso_value(customer.updated_at),
    }

    # --------------------------------------------------
    # 2. DOCUMENTS
    # --------------------------------------------------

    documents = (
        db.query(Document)
        .filter(Document.customer_id == internal_id)
        .order_by(Document.created_at.desc())
        .all()
    )

    document_data = [
        {
            "document_id": d.document_id,
            "document_type": d.document_type,
            "document_category": enum_value(
                d.document_category
            ),
            "document_number": d.document_number,

            "document_status": enum_value(
                d.document_status
            ),

            "issuing_authority": d.issuing_authority,
            "issuing_country": d.issuing_country,

            "issue_date": iso_value(d.issue_date),
            "expiry_date": iso_value(d.expiry_date),

            "submitted_at": iso_value(d.submitted_at),
            "created_at": iso_value(d.created_at),

            "is_mandatory": d.is_mandatory,
            "is_duplicate_suspect": d.is_duplicate_suspect,
            "notes": d.notes,
        }
        for d in documents
    ]

    # --------------------------------------------------
    # 3. DOCUMENT VERIFICATIONS
    # --------------------------------------------------

    verifications = (
        db.query(Verification)
        .join(
            Document,
            Verification.document_id == Document.id,
        )
        .filter(Document.customer_id == internal_id)
        .order_by(Verification.verified_at.desc())
        .all()
    )

    verification_data = [
        {
            "verification_id": v.verification_id,

            "document_id": (
                v.document.document_id
                if v.document else None
            ),

            "verified_by": v.verified_by,
            "verified_at": iso_value(v.verified_at),

            "decision": enum_value(v.decision),
            "decision_reason": v.decision_reason,

            "name_match": v.name_match,
            "name_on_document": v.name_on_document,

            "expiry_check_passed": v.expiry_check_passed,
            "authenticity_check_passed": (
                v.authenticity_check_passed
            ),

            "override_flag": v.override_flag,
            "override_reason": v.override_reason,
        }
        for v in verifications
    ]

    # --------------------------------------------------
    # 4. RISK ASSESSMENTS
    # --------------------------------------------------

    risks = (
        db.query(RiskRating)
        .filter(RiskRating.customer_id == internal_id)
        .order_by(RiskRating.assessed_at.desc())
        .all()
    )

    risk_data = [
        {
            "risk_rating_id": r.risk_rating_id,

            "risk_level": enum_value(r.risk_level),

            "risk_score": (
                float(r.risk_score)
                if r.risk_score is not None else None
            ),

            "assessed_by": r.assessed_by,
            "assessed_at": iso_value(r.assessed_at),

            "effective_from": iso_value(r.effective_from),
            "effective_to": iso_value(r.effective_to),

            "rationale": r.rationale,

            "pep_flag": r.pep_flag,
            "sanctions_flag": r.sanctions_flag,

            "geographic_risk": r.geographic_risk,
            "industry_risk": r.industry_risk,
        }
        for r in risks
    ]

    # --------------------------------------------------
    # 5. REVIEW CASES
    # --------------------------------------------------

    reviews = (
        db.query(ReviewCase)
        .filter(ReviewCase.customer_id == internal_id)
        .order_by(ReviewCase.opened_at.desc())
        .all()
    )

    review_data = [
        {
            "review_id": r.review_id,

            "trigger": enum_value(r.trigger),
            "status": enum_value(r.status),

            "opened_at": iso_value(r.opened_at),
            "due_date": iso_value(r.due_date),
            "closed_at": iso_value(r.closed_at),

            "assigned_to": r.assigned_to,
            "findings": r.findings,
            "resolution": r.resolution,

            "closed_without_resolution": (
                r.closed_without_resolution
            ),
        }
        for r in reviews
    ]

    # --------------------------------------------------
    # 6. COMPLIANCE ALERTS
    # --------------------------------------------------

    alerts = (
        db.query(Alert)
        .filter(Alert.customer_id == internal_id)
        .order_by(Alert.triggered_at.desc())
        .all()
    )

    alert_data = [
        {
            "alert_id": a.alert_id,

            "alert_type": enum_value(a.alert_type),
            "severity": enum_value(a.severity),
            "status": enum_value(a.status),

            "title": a.title,
            "description": a.description,

            "triggered_at": iso_value(a.triggered_at),
            "acknowledged_at": iso_value(a.acknowledged_at),
            "resolved_at": iso_value(a.resolved_at),

            "resolved_by": a.resolved_by,
            "resolution_notes": a.resolution_notes,

            "is_anomaly": a.is_anomaly,
            "anomaly_label": a.anomaly_label,

        }
        for a in alerts
    ]

    # --------------------------------------------------
    # 7. AUDIT EVENTS
    # --------------------------------------------------

    audit_events = (
        db.query(AuditEvent)
        .filter(AuditEvent.customer_id == internal_id)
        .order_by(AuditEvent.performed_at.desc())
        .all()
    )

    audit_data = [
        {
            "audit_id": event.audit_id,

            "entity_type": event.entity_type,
            "entity_id": event.entity_id,

            "action": enum_value(event.action),

            "performed_by": event.performed_by,
            "performed_at": iso_value(event.performed_at),

            "old_value": event.old_value,
            "new_value": event.new_value,

            "ip_address": event.ip_address,
            "session_id": event.session_id,
            "notes": event.notes,
        }
        for event in audit_events
    ]

    # --------------------------------------------------
    # 8. BUILD CHRONOLOGICAL TIMELINE
    # --------------------------------------------------

    timeline = []

    # Customer onboarding.
    timeline.append(
        make_timeline_event(
            event_type="ONBOARDING",
            event_id=customer.customer_id,
            title="Customer Onboarded",
            description=(
                f"{customer.full_name} entered the onboarding process."
            ),
            event_date=(
                customer.onboarding_date or customer.created_at
            ),
            status=customer.onboarding_status,
        )
    )

    # Customer approval.
    if customer.approved_date:
        timeline.append(
            make_timeline_event(
                event_type="ONBOARDING",
                event_id=customer.customer_id,
                title="Customer Approved",
                description="Customer approval was recorded.",
                event_date=customer.approved_date,
                status=customer.onboarding_status,
            )
        )

    # Document submissions.
    for d in documents:
        timeline.append(
            make_timeline_event(
                event_type="DOCUMENT",
                event_id=d.document_id,
                title=f"Document: {d.document_type}",
                description=(
                    f"{d.document_type} document recorded "
                    f"with status {enum_value(d.document_status)}."
                ),
                event_date=(
                    d.submitted_at or d.created_at or d.issue_date
                ),
                status=d.document_status,
            )
        )

    # Verification events.
    for v in verifications:
        document_id = (
            v.document.document_id if v.document else "Unknown"
        )

        timeline.append(
            make_timeline_event(
                event_type="VERIFICATION",
                event_id=v.verification_id,
                title="Document Verification",
                description=(
                    f"Verification of {document_id} resulted in "
                    f"{enum_value(v.decision)}."
                ),
                event_date=v.verified_at,
                status=v.decision,
                performed_by=v.verified_by,
            )
        )

    # Risk assessment events.
    for r in risks:
        timeline.append(
            make_timeline_event(
                event_type="RISK_ASSESSMENT",
                event_id=r.risk_rating_id,
                title="Risk Assessment",
                description=(
                    f"Customer risk assessed as "
                    f"{enum_value(r.risk_level)}."
                ),
                event_date=r.assessed_at,
                status=r.risk_level,
                performed_by=r.assessed_by,
            )
        )

    # Review events.
    for r in reviews:
        timeline.append(
            make_timeline_event(
                event_type="REVIEW",
                event_id=r.review_id,
                title="Review Opened",
                description=(
                    f"Review opened with trigger "
                    f"{enum_value(r.trigger)}."
                ),
                event_date=r.opened_at,
                status=r.status,
                performed_by=r.assigned_to,
            )
        )

        if r.closed_at:
            timeline.append(
                make_timeline_event(
                    event_type="REVIEW",
                    event_id=r.review_id,
                    title="Review Closed",
                    description=(
                        r.resolution or "Review case was closed."
                    ),
                    event_date=r.closed_at,
                    status=r.status,
                    performed_by=r.assigned_to,
                )
            )

    # Alert events.
    for a in alerts:
        timeline.append(
            make_timeline_event(
                event_type="ALERT",
                event_id=a.alert_id,
                title=a.title,
                description=a.description or a.title,
                event_date=a.triggered_at,
                status=a.status,
            )
        )

    # Audit events.
    for event in audit_events:
        timeline.append(
            make_timeline_event(
                event_type="AUDIT",
                event_id=event.audit_id,
                title=f"Audit: {enum_value(event.action)}",
                description=(
                    f"{event.entity_type}: {event.entity_id}"
                ),
                event_date=event.performed_at,
                status=event.action,
                performed_by=event.performed_by,
            )
        )

    # Newest activity first.
    timeline.sort(
        key=lambda item: item["_sort_timestamp"],
        reverse=True,
    )

    for item in timeline:
        item.pop("_sort_timestamp", None)

    # --------------------------------------------------
    # 9. FINAL CUSTOMER 360 RESPONSE
    # --------------------------------------------------

    return {
        "customer": customer_data,

        "counts": {
            "documents": len(document_data),
            "verifications": len(verification_data),
            "risk_assessments": len(risk_data),
            "reviews": len(review_data),
            "alerts": len(alert_data),
            "audit_events": len(audit_data),
            "timeline_events": len(timeline),
        },

        "documents": document_data,
        "verifications": verification_data,
        "risk_assessments": risk_data,
        "reviews": review_data,
        "alerts": alert_data,
        "audit_events": audit_data,
        "timeline": timeline,
    }


# --------------------------------------------------
# INDIVIDUAL CUSTOMER
# --------------------------------------------------

@router.get("/{customer_id}")
def get_customer(
    customer_id: str,
    db: Session = Depends(get_db),
):
    """Get a single customer by public customer ID."""

    c = (
        db.query(Customer)
        .filter(Customer.customer_id == customer_id)
        .first()
    )

    if not c:
        raise HTTPException(
            status_code=404,
            detail="Customer not found",
        )

    return {
        "customer_id": c.customer_id,
        "full_name": c.full_name,

        "customer_type": (
            enum_value(c.customer_type.code)
            if c.customer_type else None
        ),

        "onboarding_status": enum_value(c.onboarding_status),

        "kyc_completeness_pct": float(
            c.kyc_completeness_pct or 0
        ),

        "next_review_date": iso_value(c.next_review_date),
        "country_of_residence": c.country_of_residence,

        "is_pep": c.is_pep,
        "is_sanctioned": c.is_sanctioned,

        "onboarding_date": iso_value(c.onboarding_date),
        "approved_date": iso_value(c.approved_date),
    }


# --------------------------------------------------
# KYC DECISION
# --------------------------------------------------

@router.get("/{customer_id}/kyc-decision")
def get_kyc_decision(
    customer_id: str,
    db: Session = Depends(get_db),
):
    """Evaluate whether a customer can be approved."""

    c = (
        db.query(Customer)
        .filter(Customer.customer_id == customer_id)
        .first()
    )

    if not c:
        raise HTTPException(
            status_code=404,
            detail="Customer not found",
        )

    return evaluate_onboarding_decision(c, db)
