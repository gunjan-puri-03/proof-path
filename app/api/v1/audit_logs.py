
"""
Audit Logs API endpoints.
Uses the existing AuditEvent model and audit_events table.
"""

from datetime import date, datetime, time, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.kyc_models import (
    AuditAction,
    AuditEvent,
    Customer,
)

router = APIRouter()


def serialize_audit_event(event: AuditEvent) -> dict:
    customer = event.customer

    return {
        "id": event.id,
        "audit_id": event.audit_id,
        "customer_id": (
            customer.customer_id if customer else None
        ),
        "customer_name": (
            customer.full_name if customer else None
        ),
        "entity_type": event.entity_type,
        "entity_id": event.entity_id,
        "action": (
            event.action.value if event.action else None
        ),
        "performed_by": event.performed_by,
        "performed_at": (
            event.performed_at.isoformat()
            if event.performed_at else None
        ),
        "old_value": event.old_value,
        "new_value": event.new_value,
        "ip_address": event.ip_address,
        "session_id": event.session_id,
        "notes": event.notes,
        "created_at": (
            event.created_at.isoformat()
            if event.created_at else None
        ),
    }


def build_audit_query(db: Session):
    return (
        db.query(AuditEvent)
        .outerjoin(
            Customer,
            AuditEvent.customer_id == Customer.id,
        )
    )


@router.get("/summary")
def get_audit_summary(
    db: Session = Depends(get_db),
):
    """Return audit event totals and action distribution."""

    total = db.query(
        func.count(AuditEvent.id)
    ).scalar() or 0

    action_rows = (
        db.query(
            AuditEvent.action,
            func.count(AuditEvent.id),
        )
        .group_by(AuditEvent.action)
        .all()
    )

    action_counts = {
        action.value: count
        for action, count in action_rows
        if action is not None
    }

    return {
        "total_events": total,
        "action_counts": action_counts,
    }


@router.get("/")
def list_audit_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    action: Optional[str] = Query(None),
    entity_type: Optional[str] = Query(None),
    performed_by: Optional[str] = Query(None),
    customer_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    sort_by: str = Query(
        "performed_at",
        pattern="^(performed_at|performed_by|action)$",
    ),
    sort_order: str = Query(
        "desc",
        pattern="^(asc|desc)$",
    ),
    db: Session = Depends(get_db),
):
    """
    List audit events with optional filters and sorting.

    Supported actions are defined by the AuditAction enum.
    """

    query = build_audit_query(db)

    # Filter by audit action.
    if action:
        try:
            action_value = AuditAction(action.upper())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid audit action: {action}",
            )

        query = query.filter(
            AuditEvent.action == action_value
        )

    # Filter by entity type.
    if entity_type:
        query = query.filter(
            AuditEvent.entity_type.ilike(
                entity_type.strip()
            )
        )

    # Filter by user.
    if performed_by:
        query = query.filter(
            AuditEvent.performed_by.ilike(
                f"%{performed_by.strip()}%"
            )
        )

    # Filter by customer public ID.
    if customer_id:
        query = query.filter(
            Customer.customer_id == customer_id.strip()
        )

    # Search audit ID, entity ID, user, notes and customer.
    if search:
        term = f"%{search.strip()}%"

        query = query.filter(
            or_(
                AuditEvent.audit_id.ilike(term),
                AuditEvent.entity_type.ilike(term),
                AuditEvent.entity_id.ilike(term),
                AuditEvent.performed_by.ilike(term),
                AuditEvent.notes.ilike(term),
                Customer.customer_id.ilike(term),
                Customer.full_name.ilike(term),
            )
        )

    # Date range filtering.
    if from_date:
        start_datetime = datetime.combine(
            from_date,
            time.min,
        )
        query = query.filter(
            AuditEvent.performed_at >= start_datetime
        )

    if to_date:
        end_datetime = datetime.combine(
            to_date + timedelta(days=1),
            time.min,
        )
        query = query.filter(
            AuditEvent.performed_at < end_datetime
        )

    # Sorting.
    sort_columns = {
        "performed_at": AuditEvent.performed_at,
        "performed_by": AuditEvent.performed_by,
        "action": AuditEvent.action,
    }

    sort_column = sort_columns[sort_by]

    if sort_order == "asc":
        query = query.order_by(
            sort_column.asc(),
            AuditEvent.id.asc(),
        )
    else:
        query = query.order_by(
            sort_column.desc(),
            AuditEvent.id.desc(),
        )

    events = (
        query
        .offset(skip)
        .limit(limit)
        .all()
    )

    return [
        serialize_audit_event(event)
        for event in events
    ]


@router.get("/{audit_id}")
def get_audit_log(
    audit_id: str,
    db: Session = Depends(get_db),
):
    """Retrieve one audit event using its public audit ID."""

    event = (
        db.query(AuditEvent)
        .filter(AuditEvent.audit_id == audit_id)
        .first()
    )

    if not event:
        raise HTTPException(
            status_code=404,
            detail="Audit event not found",
        )

    return serialize_audit_event(event)
