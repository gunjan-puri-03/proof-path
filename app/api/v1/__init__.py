
"""
API v1 router.
"""

from fastapi import APIRouter

from app.api.v1 import (
    customers,
    documents,
    reviews,
    alerts,
    verifications,
    risk_monitoring,
    audit_logs,
)

router = APIRouter()

router.include_router(
    customers.router,
    prefix="/customers",
    tags=["Customers"],
)

router.include_router(
    documents.router,
    prefix="/documents",
    tags=["Documents"],
)

router.include_router(
    reviews.router,
    prefix="/reviews",
    tags=["Reviews"],
)

router.include_router(
    alerts.router,
    prefix="/alerts",
    tags=["Alerts"],
)

router.include_router(
    verifications.router,
    prefix="/verifications",
    tags=["Verifications"],
)

router.include_router(
    risk_monitoring.router,
    prefix="/risk-monitoring",
    tags=["Risk Monitoring"],
)

router.include_router(
    audit_logs.router,
    prefix="/audit-logs",
    tags=["Audit Logs"],
)
