"""Reviews API endpoints."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.db.session import get_db
from app.models.kyc_models import ReviewCase

router = APIRouter()

@router.get("/")
def list_reviews(skip: int = 0, limit: int = 100,
                 status: Optional[str] = None,
                 db: Session = Depends(get_db)):
    q = db.query(ReviewCase)
    if status:
        q = q.filter(ReviewCase.status == status)
    reviews = q.offset(skip).limit(limit).all()
    return [
        {
            "review_id": r.review_id,
            "trigger": r.trigger.value,
            "status": r.status.value,
            "due_date": r.due_date.isoformat(),
            "opened_at": r.opened_at.isoformat(),
            "closed_without_resolution": r.closed_without_resolution,
        }
        for r in reviews
    ]
