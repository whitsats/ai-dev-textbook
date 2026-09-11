from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.config.db_config import get_db
from app.dependencies.service_dp.favorite_dp import get_favorite_service
from app.services.favorite_service import FavoriteService


def get_favorite_service_dep(
    db: Session = Depends(get_db),
) -> FavoriteService:
    return get_favorite_service(db)


FavoriteServiceDep = Annotated[FavoriteService, Depends(get_favorite_service_dep)]
