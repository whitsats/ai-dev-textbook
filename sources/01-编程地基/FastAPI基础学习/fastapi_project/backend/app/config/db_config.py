from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from app.config.app_config import settings

engine = create_engine(
    settings.db_url,
    echo=settings.db_echo,
    pool_size=10,
    max_overflow=30,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

