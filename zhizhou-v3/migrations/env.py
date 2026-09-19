"""Alembic 的运行环境：数据库地址从环境变量来，绝不出现在配置文件里。

    set -a; source .env; set +a
    alembic upgrade head      # 建表 / 加列
    alembic downgrade -1      # 退回上一版

`create_all` 依然留给本地开发（1.12.4 的分工）：一行命令建出全表，删掉重建即可。
这个目录只在「库里有真数据、不能删」之后才派上用场。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from alembic import context
from sqlalchemy import create_engine

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.db import Base            # noqa: E402
from app.models import agent as _models  # noqa: E402,F401 —— 导入即注册三张表

config = context.config
target_metadata = Base.metadata


def db_url() -> str:
    """默认落在一个本地 SQLite 文件上；线上由 `APP_DB` 指向真实库。"""
    return os.environ.get("APP_DB", "sqlite:///zhizhou.db")


def run_migrations_offline() -> None:
    context.configure(url=db_url(), target_metadata=target_metadata,
                      literal_binds=True, render_as_batch=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(db_url())
    with engine.connect() as conn:
        context.configure(connection=conn, target_metadata=target_metadata,
                          render_as_batch=True)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
