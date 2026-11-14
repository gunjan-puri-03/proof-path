"""Documents API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.db.session import get_db
from app.models.kyc_models import Document, DocumentStatus

router = APIRouter()

@router.get("/")
def list_documents(skip: int = 0, limit: int = 100,
                   status: Optional[str] = None,
                   customer_id: Optional[str] = None,
                   db: Session = Depends(get_db)):
    q = db.query(Document)
    if status:
        try:
            q = q.filter(Document.document_status == DocumentStatus(status))
        except ValueError:
            raise HTTPException(400, f"Invalid status: {status}")
    if customer_id:
        from app.models.kyc_models import Customer
        c = db.query(Customer).filter(Customer.customer_id == customer_id).first()
        if c:
            q = q.filter(Document.customer_id == c.id)
    docs = q.offset(skip).limit(limit).all()
    return [
        {
            "document_id": d.document_id,
            "document_type": d.document_type,
            "document_status": d.document_status.value,
            "issue_date": d.issue_date.isoformat() if d.issue_date else None,
            "expiry_date": d.expiry_date.isoformat() if d.expiry_date else None,
            "is_duplicate_suspect": d.is_duplicate_suspect,
        }
        for d in docs
    ]
