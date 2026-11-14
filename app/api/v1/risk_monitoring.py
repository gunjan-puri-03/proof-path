
"""Risk Monitoring API endpoints."""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.kyc_models import (
    Customer,
    RiskLevel,
    RiskRating,
)

router = APIRouter()


def serialize_risk_rating(rating):
    customer = rating.customer

    return {
        "id": rating.id,
        "risk_rating_id": rating.risk_rating_id,

        "customer_id": (
            customer.customer_id if customer else None
        ),

        "customer_name": (
            customer.full_name if customer else None
        ),

        "risk_level": (
            rating.risk_level.value
            if rating.risk_level else None
        ),

        "risk_score": (
            float(rating.risk_score)
            if rating.risk_score is not None else None
        ),

        "assessed_by": rating.assessed_by,

        "assessed_at": (
            rating.assessed_at.isoformat()
            if rating.assessed_at else None
        ),

        "effective_from": (
            rating.effective_from.isoformat()
            if rating.effective_from else None
        ),

        "effective_to": (
            rating.effective_to.isoformat()
            if rating.effective_to else None
        ),

        "rationale": rating.rationale,

        "pep_flag": bool(rating.pep_flag),
        "sanctions_flag": bool(rating.sanctions_flag),

        "geographic_risk": rating.geographic_risk,
        "industry_risk": rating.industry_risk,

        "customer_is_pep": (
            bool(customer.is_pep) if customer else False
        ),

        "customer_is_sanctioned": (
            bool(customer.is_sanctioned) if customer else False
        ),
    }


def current_ratings_query(db: Session):
    return (
        db.query(RiskRating)
        .join(
            Customer,
            RiskRating.customer_id == Customer.id
        )
        .filter(RiskRating.effective_to.is_(None))
    )


@router.get("/summary")
def get_risk_summary(
    db: Session = Depends(get_db)
):
    ratings = current_ratings_query(db).all()

    counts = {
        level.value: 0
        for level in RiskLevel
    }

    for rating in ratings:
        if rating.risk_level:
            counts[rating.risk_level.value] += 1

    return {
        "total_monitored": len(ratings),

        "low": counts["LOW"],
        "medium": counts["MEDIUM"],
        "high": counts["HIGH"],
        "very_high": counts["VERY_HIGH"],

        "pep_count": sum(
            1 for r in ratings
            if r.pep_flag or (
                r.customer and r.customer.is_pep
            )
        ),

        "sanctions_count": sum(
            1 for r in ratings
            if r.sanctions_flag or (
                r.customer and r.customer.is_sanctioned
            )
        ),

        "as_of": date.today().isoformat(),
    }


@router.get("/")
def get_risk_monitoring_records(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    risk_level: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    query = current_ratings_query(db)

    if risk_level:
        try:
            level = RiskLevel(risk_level.upper())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid risk level: {risk_level}"
            )

        query = query.filter(
            RiskRating.risk_level == level
        )

    if search:
        term = f"%{search.strip()}%"

        query = query.filter(
            or_(
                RiskRating.risk_rating_id.ilike(term),
                Customer.customer_id.ilike(term),
                Customer.full_name.ilike(term),
            )
        )

    ratings = (
        query
        .order_by(
            RiskRating.assessed_at.desc(),
            RiskRating.id.desc()
        )
        .offset(skip)
        .limit(limit)
        .all()
    )

    return [
        serialize_risk_rating(rating)
        for rating in ratings
    ]


@router.get("/{risk_rating_id}")
def get_risk_rating(
    risk_rating_id: str,
    db: Session = Depends(get_db)
):
    rating = (
        db.query(RiskRating)
        .join(
            Customer,
            RiskRating.customer_id == Customer.id
        )
        .filter(
            RiskRating.risk_rating_id == risk_rating_id
        )
        .first()
    )

    if not rating:
        raise HTTPException(
            status_code=404,
            detail="Risk rating not found"
        )

    return serialize_risk_rating(rating)
