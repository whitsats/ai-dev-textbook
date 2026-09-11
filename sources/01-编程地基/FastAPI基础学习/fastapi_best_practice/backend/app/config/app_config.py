import os
from pathlib import Path

from pydantic_settings import BaseSettings


class AppConfig(BaseSettings):
    env: str = "dev"

    # 最简演示：SQLite 文件数据库（backend/.data/app.db）
    db_url: str = "sqlite+pysqlite:///./.data/app.db"
    db_echo: bool = False

    @property
    def project_root(self) -> Path:
        # backend/app/config/app_config.py -> backend/app/config -> backend/app -> backend -> fastapi_project
        return Path(__file__).resolve().parents[3]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = AppConfig()
