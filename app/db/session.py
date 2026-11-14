"""
Database engine and session management.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import StaticPool
from app.core.config import settings

if settings.database_url.startswith("sqlite"):
    sqlite_options = {"connect_args": {"check_same_thread": False}}
    if ":memory:" in settings.database_url or "mode=memory" in settings.database_url:
        # Share one in-memory SQLite connection across sessions/threads.
        sqlite_options["poolclass"] = StaticPool
    engine = create_engine(settings.database_url, **sqlite_options)
else:
    engine = create_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency: yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
