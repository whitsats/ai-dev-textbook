from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.config.db_config import get_db
from app.dependencies.service_dp.personal_dp import get_personal_service
from app.services.personal_service import PersonalService


def get_personal_service_dep(
    db: Session = Depends(get_db),
) -> PersonalService:
    return get_personal_service(db)


PersonalServiceDep = Annotated[PersonalService, Depends(get_personal_service_dep)]
