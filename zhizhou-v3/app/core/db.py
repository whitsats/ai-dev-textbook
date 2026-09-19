"""第 1 篇的 `Base`。参考实现只留声明式基类：不建连接、不读配置，所以导入它不需要数据库。"""
from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
