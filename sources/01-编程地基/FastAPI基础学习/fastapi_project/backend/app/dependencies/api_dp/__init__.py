from app.dependencies.api_dp.article_dp import ArticleServiceDep
from app.dependencies.api_dp.user_dp import UserServiceDep
from app.dependencies.api_dp.comment_dp import CommentServiceDep
from app.dependencies.api_dp.favorite_dp import FavoriteServiceDep
from app.dependencies.api_dp.personal_dp import PersonalServiceDep
from app.dependencies.api_dp.index_dp import IndexArticleServiceDep

__all__ = [
    "ArticleServiceDep",
    "UserServiceDep",
    "CommentServiceDep",
    "FavoriteServiceDep",
    "PersonalServiceDep",
    "IndexArticleServiceDep",
]
