"""迁移基线：3.5 建的两张表（`agent_session` / `agent_message`）。

这一版是**事后补记的**：3.5 当时用 `create_all` 建的库，没有迁移。补记它的理由不是形式主义——
一个只有「新增」若干列的第二版迁移，在别人的库上跑不起来：他不知道前一版的表长什么样。
迁移链的价值就在于**把「现在应该是什么样」拆成一串可重放的历史**。

**两个外键指向的 `user` 表也在这里**，尽管知舟的用户表属于第 1 篇。理由很硬：
外键的目标表不存在时，SQLite 会默默放过（它默认不强制外键），Postgres 会当场报
`relation "user" does not exist`。**只在 SQLite 上跑过的迁移不算跑过**，所以基线要把
引用链补全，而不是等换库那天才发现。
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001_agent_tables"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 引用链的根。字段只留迁移需要的那几个（第 1 篇有完整定义），一张表对应一条迁移线。
    op.create_table(
        "user",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("state", sa.String(16), nullable=False, server_default="active"),
    )
    op.create_table(
        "agent_session",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("title", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("state", sa.String(16), nullable=False, server_default="active"),
    )
    op.create_index("ix_agent_session_user_id", "agent_session", ["user_id"])

    op.create_table(
        "agent_message",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.Integer(), sa.ForeignKey("agent_session.id"), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("content_digest", sa.String(64), nullable=False),
        sa.Column("tokens", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_agent_message_session_id", "agent_message", ["session_id"])


def downgrade() -> None:
    op.drop_index("ix_agent_message_session_id", table_name="agent_message")
    op.drop_table("agent_message")
    op.drop_index("ix_agent_session_user_id", table_name="agent_session")
    op.drop_table("agent_session")
    op.drop_table("user")            # 先掉引用方，再掉被引用方：反过来 Postgres 会拦下
