from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.config.db_config import get_db
from app.dependencies.service_dp.article_dp import get_article_service
from app.services.article_service import ArticleService


def get_article_service_dep(
    db: Session = Depends(get_db),
) -> ArticleService:
    return get_article_service(db)


ArticleServiceDep = Annotated[ArticleService, Depends(get_article_service_dep)]
