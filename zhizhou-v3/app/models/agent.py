"""知舟的三张表：会话、消息、长期记忆。

**这张表在 3.6 被改过一次，原因值得记下来。** 3.5 建它的时候只存 `content_digest`，
注释写着「只存摘要指纹，不存正文（理由见 3.8）」。当时的理由是脱敏：追踪里不该落正文。
但记忆要能**回放**——把上一次会话的历史重新装配成上下文，没有正文就无从装配，
只能装一串哈希。于是 3.6 的迁移给它补了 `content` 与 `tool_call_id` 两列。

两件事一起成立才对：**正文要存**（否则记忆是假的），**能删、能设保留期、能按用户彻底清空**
（否则脱敏是空话）。后半句在第 3.8 节。
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


def utcnow() -> datetime:
    """带时区的时间：naive 的 `datetime.utcnow()` 在跨时区部署里会悄悄差几个小时。"""
    return datetime.now(timezone.utc)


class AgentSession(Base):
    __tablename__ = "agent_session"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True)
    title: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    state: Mapped[str] = mapped_column(String(16), default="active")   # 沿用第 1 篇的「位」风格


class AgentMessage(Base):
    """一次会话里的一条消息。**正文在这里**（3.5 的版本只有指纹，装配不出上下文）。"""

    __tablename__ = "agent_message"
    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("agent_session.id"), index=True)
    role: Mapped[str] = mapped_column(String(16))             # user / assistant / tool
    content: Mapped[str] = mapped_column(Text, default="")
    content_digest: Mapped[str] = mapped_column(String(64))   # 留着：追踪与去重仍按指纹比对
    tool_call_id: Mapped[str] = mapped_column(String(64), default="")
    tokens: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (Index("ix_agent_message_session_created", "session_id", "created_at"),)


class AgentMemory(Base):
    """长期记忆：跨会话仍然成立的偏好与事实。

    三个字段是刻意的，缺一个都会出问题：
      · `key` 唯一（按用户维度）——同一个键**覆盖**而不是追加，记忆才不会无限长；
      · `source` 记下它来自哪一次会话——召回时可追溯，出了问题能定位到源头；
      · `expires_at` 允许为空（永不过期），但写入方**必须显式回答**「它能活多久」。
    """

    __tablename__ = "agent_memory"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True)
    key: Mapped[str] = mapped_column(String(64))
    value: Mapped[str] = mapped_column(String(500))
    scope: Mapped[str] = mapped_column(String(16), default="user")     # user ｜ session
    source: Mapped[str] = mapped_column(String(64), default="")        # 写入它的那次会话
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (Index("uq_agent_memory_user_key", "user_id", "key", unique=True),)


DEFAULT_TTL = timedelta(days=180)


def expires_in(**kw) -> datetime:
    """写入时的默认保留期：不写 TTL 不等于永久留存，而是落在一个显式的默认值上。"""
    return utcnow() + timedelta(**kw) if kw else utcnow() + DEFAULT_TTL
