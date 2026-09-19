"""3.6 的迁移：给消息补上正文，并新建长期记忆表。

**这一版修的是一个设计错误，不是一个新需求。** 0001 里的 `agent_message` 只存
`content_digest`——当时为了脱敏，不落正文。可是「历史能重建」这件事要求正文在库里：
没有它，第二次开会话时装配出来的上下文只是一串哈希，记忆是假的。

给已有的表加列要按三步走，少一步就会在不同数据库上翻车：

1. 加**可空**列（`ADD COLUMN ... NULL`）。SQLite 的 `ALTER TABLE` 只支持加列，
   而且**不允许** `NOT NULL` 配 `CURRENT_TIMESTAMP` 这类非常量默认值；
2. **回填**。能回填的立刻回填；回填不了的（老行的正文从来没被存过）只能承认它补不回来；
3. 收紧约束（改 `NOT NULL` / 加外键）。SQLite 做不到，Postgres 可以——
   所以这一步写在这个迁移里是**有意留空**的，而不是忘了。
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0002_agent_memory"
down_revision = "0001_agent_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 第 1 步：加可空列
    op.add_column("agent_message", sa.Column("content", sa.Text(), nullable=True))
    op.add_column("agent_message", sa.Column("tool_call_id", sa.String(64), nullable=True))
    op.add_column("agent_message", sa.Column("created_at", sa.DateTime(timezone=True),
                                             nullable=True))

    # 第 2 步：回填。正文回填不了（老行只有指纹），但时间戳可以按插入顺序给个近似值；
    #          tool_call_id 回填成空串，好让第 3 步在 Postgres 上能把它收紧成 NOT NULL。
    op.execute("UPDATE agent_message SET content = '' WHERE content IS NULL")
    op.execute("UPDATE agent_message SET tool_call_id = '' WHERE tool_call_id IS NULL")
    op.execute("UPDATE agent_message SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL")

    # 第 3 步：SQLite 上的收紧留空（见文件头）。Postgres 上就写成：
    #   op.alter_column("agent_message", "content", nullable=False)
    op.create_index("ix_agent_message_session_created", "agent_message",
                    ["session_id", "created_at"])

    op.create_table(
        "agent_memory",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("key", sa.String(64), nullable=False),
        sa.Column("value", sa.String(500), nullable=False),
        sa.Column("scope", sa.String(16), nullable=False, server_default="user"),
        sa.Column("source", sa.String(64), nullable=False, server_default=""),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_agent_memory_user_id", "agent_memory", ["user_id"])
    # 唯一约束是这张表的核心：同一个键覆盖而不是追加，记忆才不会随会话数无限增长
    op.create_index("uq_agent_memory_user_key", "agent_memory", ["user_id", "key"], unique=True)


def downgrade() -> None:
    op.drop_index("uq_agent_memory_user_key", table_name="agent_memory")
    op.drop_index("ix_agent_memory_user_id", table_name="agent_memory")
    op.drop_table("agent_memory")
    op.drop_index("ix_agent_message_session_created", table_name="agent_message")
    op.drop_column("agent_message", "created_at")
    op.drop_column("agent_message", "tool_call_id")
    op.drop_column("agent_message", "content")
