from app.dependencies.service_dp.article_dp import get_article_service
from app.dependencies.service_dp.user_dp import get_user_service
from app.dependencies.service_dp.comment_dp import get_comment_service
from app.dependencies.service_dp.favorite_dp import get_favorite_service
from app.dependencies.service_dp.personal_dp import get_personal_service

__all__ = [
    "get_article_service",
    "get_user_service",
    "get_comment_service",
    "get_favorite_service",
    "get_personal_service",
]
