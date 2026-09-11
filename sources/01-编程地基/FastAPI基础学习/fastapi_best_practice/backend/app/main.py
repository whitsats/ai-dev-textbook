from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.router import router
from app.config.db_config import engine
from app.models.base import Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="FastAPI Best Practice (Minimal)",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.include_router(router)

    return app
