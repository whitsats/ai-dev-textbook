from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config.app_config import settings


def _ensure_sqlite_dir(db_url: str) -> None:
    # sqlite+pysqlite:///./.data/app.db -> ensure .data exists
    if not db_url.startswith("sqlite"):
        return
    Path(".data").mkdir(parents=True, exist_ok=True)


_ensure_sqlite_dir(settings.db_url)

engine = create_engine(
    settings.db_url,
    echo=settings.db_echo,
    connect_args={"check_same_thread": False} if settings.db_url.startswith("sqlite") else {},
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
