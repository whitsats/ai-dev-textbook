from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.config.db_config import get_db
from app.dependencies.service_dp.comment_dp import get_comment_service
from app.services.comment_service import CommentService


def get_comment_service_dep(
    db: Session = Depends(get_db),
) -> CommentService:
    return get_comment_service(db)


CommentServiceDep = Annotated[CommentService, Depends(get_comment_service_dep)]
