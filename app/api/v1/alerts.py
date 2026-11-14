"""Alerts API endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Optional
from app.db.session import get_db
from app.models.kyc_models import Alert

router = APIRouter()

@router.get("/")
def list_alerts(skip: int = 0, limit: int = 100,
                anomaly_only: bool = False,
                db: Session = Depends(get_db)):
    q = db.query(Alert)
    if anomaly_only:
        q = q.filter(Alert.is_anomaly == True)
    alerts = q.offset(skip).limit(limit).all()
    return [
        {
            "alert_id": a.alert_id,
            "alert_type": a.alert_type.value,
            "severity": a.severity.value,
            "status": a.status.value,
            "title": a.title,
            "description": a.description,
            "is_anomaly": a.is_anomaly,
            "anomaly_label": a.anomaly_label,
            "triggered_at": a.triggered_at.isoformat(),
        }
        for a in alerts
    ]
