from fastapi import APIRouter

from app.api import book_api, health_api, user_api

router = APIRouter(tags=["总路由"])

router.include_router(health_api.router)
router.include_router(user_api.router)
router.include_router(book_api.router)
