from fastapi import APIRouter

from app.api import (
    user_api,
    article_api,
    favorite_api,
    comment_api,
    personal_api,
    index_api,
)

router = APIRouter(tags=["总路由"])

router.include_router(user_api.router)
router.include_router(article_api.router)
router.include_router(favorite_api.router)
router.include_router(comment_api.router)
router.include_router(personal_api.router)
router.include_router(index_api.router)
