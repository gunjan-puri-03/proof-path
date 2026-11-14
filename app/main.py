
"""
ProofPath
KYC & Compliance Management Platform
FastAPI Application Entry Point
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import router as api_v1_router


app = FastAPI(
    title="ProofPath - KYC & Compliance Management Platform",
    description=(
        "ProofPath is an integrated KYC and Compliance Management "
        "Platform for customer onboarding, evidence collection, "
        "document verification, KYC completeness assessment, "
        "beneficial ownership management, risk monitoring, "
        "compliance alerts and audit history."
    ),
    version="1.0.0",
)

# Allow the React/Vite frontend to communicate with FastAPI.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(
    api_v1_router,
    prefix="/api/v1",
)


@app.get("/", tags=["Health"])
def health_check():
    return {
        "status": "ok",
        "service": "ProofPath",
        "description": "KYC & Compliance Management Platform",
        "version": "1.0.0",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )
