"""跨进程的检查点后端：把「停在哪一步」写进一个能用另一个进程读回来的地方。

4.4 用一个 `InMemorySaver` 演示了中断，也留下一个结尾问题：
**跑完的图停在一个进程的内存里，另一个进程接不上。** 这一章先把这个结论变成读数
（同一个 `thread_id`，新进程读到的快照是 `None`），再给出一个最小的替代方案。

为什么要**手写**一个，而不直接装官方那个 `langgraph-checkpoint-sqlite`：

1. 官方那几个包（`sqlite` / `postgres`）的地位是**产品**；手写一遍才看得见接口长什么样
   ——`BaseCheckpointSaver` 一共就五个方法（`get_tuple` / `list` / `put` /
   `put_writes` / `delete_thread`），每个方法的入参与返回值都是被图调用出来的契约。
2. 本书的验收要能在**不装任何新依赖**的机器上跑（`zhizhou-v4/requirements.txt`
   只有四个包），而 `sqlite3` 是标准库。
3. 这一份只有 200 多行，读者能一行行读完；官方产品要考虑并发、迁移、加密、异步驱动，
   那些是第 7、8 篇的话题。

一张表存检查点、一张表存「待写入」。三个键是这套存储的主键，缺一个都会串线：

    (thread_id, checkpoint_ns, checkpoint_id)
      · thread_id      —— 一条会话线程（等价于 3.6 的 `agent_session.id`）
      · checkpoint_ns  —— 命名空间：子图/嵌套图各自一份，同一线程下互不覆盖
      · checkpoint_id  —— 时间序 ID（`uuid6`，单调递增），**它是「恢复的游标」**

`channel_values` 这一版**直接存进检查点这一行**（官方 sqlite 包按 channel 拆表存 blob，
为了去重与增量）。简化是刻意的：本周要讲的是「快照存在哪、能不能跨进程读回来」，
而不是存储引擎的压缩率。这句话本身也是本章的一条结论——**先让机制可见，再谈优化**。
"""
from __future__ import annotations

import asyncio
import sqlite3
import threading
from collections.abc import AsyncIterator, Iterator, Sequence
from typing import Any

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import (
    WRITES_IDX_MAP,
    BaseCheckpointSaver,
    ChannelVersions,
    Checkpoint,
    CheckpointMetadata,
    CheckpointTuple,
    get_checkpoint_id,
    get_checkpoint_metadata,
)

# 两行是这套存储的全部结构。**没有 `channel_id` 那样的外键**：检查点行自己带着
# 它那个时刻的所有通道值，所以「读回来」不需要跟别的表拼。
SCHEMA = """
CREATE TABLE IF NOT EXISTS checkpoint (
    thread_id     TEXT NOT NULL,
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    checkpoint_id TEXT NOT NULL,
    parent_id     TEXT,
    ck_type       TEXT,
    ck_value      BLOB,
    md_type       TEXT,
    md_value      BLOB,
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id)
);
CREATE TABLE IF NOT EXISTS checkpoint_write (
    thread_id     TEXT NOT NULL,
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    checkpoint_id TEXT NOT NULL,
    task_id       TEXT NOT NULL,
    idx           INTEGER NOT NULL,
    channel       TEXT NOT NULL,
    type          TEXT,
    value         BLOB,
    task_path     TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id, task_id, idx)
);
"""


class SqliteCheckpointer(BaseCheckpointSaver[str]):
    """一个进程写、另一个进程读。**它存在的唯一理由就是这句话。**

    构造参数只有一个路径。路径给 `":memory:"` 也能跑，但那样它就退化成了
    `InMemorySaver`——这一条要写进契约，因为它是最容易被自己骗到的地方：
    「我换了后端」不等于「我换了存储介质」。
    """

    def __init__(self, path: str = ":memory:", *, serde: Any = None) -> None:   # noqa: ANN401
        super().__init__(serde=serde)
        self.path = path
        # `check_same_thread=False`：图可能在别的线程里跑（`asyncio.to_thread` 那几条路径）。
        # **但允许跨线程访问不等于并发是安全的**——pregel 会在后台线程里落检查点，
        # 而同一个 sqlite3 连接被两个线程同时用，会报出
        # `sqlite3.OperationalError: not an error`（一个长得不像并发问题的错）。
        # 本模块第一版没有这把锁，报错发生在第二次运行时，第一次完全正常——
        # 这类「偶发」在教材里必须变成「必然」，所以加锁并且注释清楚它为什么在。
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self._lock = threading.RLock()
        with self._lock:
            self.conn.executescript(SCHEMA)
            self.conn.commit()

    # ------------------------------------------------------------------ 读
    def get_tuple(self, config: RunnableConfig) -> CheckpointTuple | None:
        """按配置取一个快照。**不给 `checkpoint_id` 就是取最新的那一份。**

        这一行行为就是「恢复」的全部秘密：`checkpoint_id` 是从配置里来的，
        所以「回到某一步」与「接着最新一步」用的是同一个方法。
        """
        conf = config["configurable"]
        thread_id: str = conf["thread_id"]
        checkpoint_ns: str = conf.get("checkpoint_ns", "")
        checkpoint_id = get_checkpoint_id(config)
        cols = "ck_type, ck_value, md_type, md_value, parent_id"
        with self._lock:
            if checkpoint_id:
                row = self.conn.execute(
                    f"SELECT {cols} FROM checkpoint"
                    " WHERE thread_id=? AND checkpoint_ns=? AND checkpoint_id=?",
                    (thread_id, checkpoint_ns, checkpoint_id),
                ).fetchone()
            else:
                # 按 id 倒序：`uuid6` 是单调递增的，所以「最大」就是「最新」。
                # 用 `id` 排序而不是行号，是因为并发写入时行号会乱。
                row = self.conn.execute(
                    f"SELECT {cols} FROM checkpoint"
                    " WHERE thread_id=? AND checkpoint_ns=?"
                    " ORDER BY checkpoint_id DESC LIMIT 1",
                    (thread_id, checkpoint_ns),
                ).fetchone()
        if row is None:
            return None
        return self._to_tuple(thread_id, checkpoint_ns, row)

    def _to_tuple(self, thread_id: str, checkpoint_ns: str, row: tuple) -> CheckpointTuple:
        """把几列原始数据拼成一个 `CheckpointTuple`——**拼接点只有这一处**。

        注意 `serde.dumps_typed` 返回的是**二元组 `(类型, 字节)`**，不是一段字节。
        所以库里存的是两列（`ck_type` / `ck_value`），读回来要拼成元组再解。
        本模块第一版把它当一段字节绑进 `BLOB`，报出来的是
        `sqlite3.InterfaceError: Error binding parameter ...probably unsupported type`——
        一个不指向真因的错（看起来像「数据太大」，其实是「少解了一层元组」）。
        """
        ck_type, ck_value, md_type, md_value, parent_id = row
        checkpoint: Checkpoint = self.serde.loads_typed((ck_type, ck_value))
        metadata: CheckpointMetadata = self.serde.loads_typed((md_type, md_value))
        with self._lock:
            writes = self.conn.execute(
                "SELECT task_id, channel, type, value FROM checkpoint_write"
                " WHERE thread_id=? AND checkpoint_ns=? AND checkpoint_id=?"
                " ORDER BY rowid",
                (thread_id, checkpoint_ns, checkpoint["id"]),
            ).fetchall()
        return CheckpointTuple(
            config={"configurable": {"thread_id": thread_id, "checkpoint_ns": checkpoint_ns,
                                     "checkpoint_id": checkpoint["id"]}},
            checkpoint=checkpoint,
            metadata=metadata,
            pending_writes=[
                (task_id, channel, self.serde.loads_typed((type_, value)))
                for task_id, channel, type_, value in writes
            ],
            parent_config=(
                {"configurable": {"thread_id": thread_id, "checkpoint_ns": checkpoint_ns,
                                  "checkpoint_id": parent_id}}
                if parent_id else None
            ),
        )

    def list(
        self,
        config: RunnableConfig | None,
        *,
        filter: dict[str, Any] | None = None,       # noqa: A002 —— 与基类签名一致
        before: RunnableConfig | None = None,
        limit: int | None = None,
    ) -> Iterator[CheckpointTuple]:
        """列出快照，**最新在前**。`before` 是「从某一步往前翻」，`limit` 是「翻几条」。

        这三个参数不是装饰：`get_state_history` 就是靠它们才不用把整条线程读进内存。
        """
        if config is not None:
            conf = config["configurable"]
            threads = [(conf["thread_id"], conf.get("checkpoint_ns", ""))]
        else:
            threads = list(self.conn.execute(
                "SELECT DISTINCT thread_id, checkpoint_ns FROM checkpoint"))
        before_id = get_checkpoint_id(before) if before else None
        sql = ("SELECT thread_id, checkpoint_ns, ck_type, ck_value, md_type, md_value,"
               " parent_id FROM checkpoint WHERE thread_id=? AND checkpoint_ns=?")
        if before_id:
            sql += " AND checkpoint_id < ?"
        sql += " ORDER BY checkpoint_id DESC"
        if limit is not None:
            sql += " LIMIT ?"
        # 先把行读完再离开锁：`list` 是**生成器**，锁若抱着不放，
        # 调用方一边遍历它、一边再调 `get_tuple` 就会自己把自己锁住（RLock 也救不了）。
        rows: list[tuple] = []
        with self._lock:
            for thread_id, ns in threads:
                args: list[Any] = [thread_id, ns]
                if before_id:
                    args.append(before_id)
                if limit is not None:
                    args.append(limit)
                rows.extend(self.conn.execute(sql, args).fetchall())
        for row in rows:
            tup = self._to_tuple(row[0], row[1], row[2:])
            if filter and not all(tup.metadata.get(k) == v for k, v in filter.items()):
                continue
            yield tup

    # ------------------------------------------------------------------ 写
    def put(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions,
    ) -> RunnableConfig:
        """存一份快照，**并回传一个带上 `checkpoint_id` 的新配置**。

        `parent_id` 取的是「传进来那个配置里的 `checkpoint_id`」——链子就是这么串起来的，
        所以 `get_state_history` 能顺着 `parent_config` 一路走回第一步。
        `new_versions` 本类用不到（官方的按通道拆表版本要用它判「哪些通道变了」），
        但**签名不能少**：少了它，将来换成一个真正增量的后端就要改图那边的调用。
        """
        conf = config["configurable"]
        thread_id: str = conf["thread_id"]
        checkpoint_ns: str = conf.get("checkpoint_ns", "")
        ck_type, ck_value = self.serde.dumps_typed(checkpoint)
        md_type, md_value = self.serde.dumps_typed(get_checkpoint_metadata(config, metadata))
        with self._lock:
            self.conn.execute(
                "INSERT OR REPLACE INTO checkpoint"
                " (thread_id, checkpoint_ns, checkpoint_id, parent_id, ck_type, ck_value,"
                "  md_type, md_value) VALUES (?,?,?,?,?,?,?,?)",
                (thread_id, checkpoint_ns, checkpoint["id"], conf.get("checkpoint_id"),
                 ck_type, ck_value, md_type, md_value),
            )
            self.conn.commit()
        return {"configurable": {"thread_id": thread_id, "checkpoint_ns": checkpoint_ns,
                                 "checkpoint_id": checkpoint["id"]}}

    def put_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        """存「这一步算出来、但还没轮到的写入」。**中断就停在这上面。**

        索引这一段照抄官方：普通写入用列表下标，几种特殊通道用负数
        （`interrupt` → -3、`resume` → -4），于是它们既不会互相覆盖，
        也不会与普通写入撞位置。`INSERT OR IGNORE` 是恢复时**幂等**的来源——
        节点重跑一遍会再写一次同样的东西，而位置已经被占了，重复写被丢掉。
        """
        conf = config["configurable"]
        thread_id: str = conf["thread_id"]
        checkpoint_ns: str = conf.get("checkpoint_ns", "")
        checkpoint_id: str = conf["checkpoint_id"]
        rows = []
        for idx, (channel, value) in enumerate(writes):
            rows.append((thread_id, checkpoint_ns, checkpoint_id, task_id,
                         WRITES_IDX_MAP.get(channel, idx), channel,
                         *self.serde.dumps_typed(value), task_path))
        if not rows:                      # 空写入：`executemany([])` 不开事务，commit 会抛
            return                        # 「cannot commit - no transaction is active」
        with self._lock:
            self.conn.executemany(
                "INSERT OR IGNORE INTO checkpoint_write"
                " (thread_id, checkpoint_ns, checkpoint_id, task_id, idx, channel, type,"
                "  value, task_path) VALUES (?,?,?,?,?,?,?,?,?)", rows)
            self.conn.commit()

    def delete_thread(self, thread_id: str) -> None:
        """整条线程删掉。**3.8 的「按用户彻底清空」在这里落地**：

        检查点里存着完整的 `channel_values`——也就是消息正文。只删 3.6 那张消息表
        而留着检查点，等于「删了但没删干净」；两张表要一起删，这条契约写在正文里。
        """
        with self._lock:
            for table in ("checkpoint", "checkpoint_write"):
                self.conn.execute(f"DELETE FROM {table} WHERE thread_id=?", (thread_id,))  # noqa: S608
            self.conn.commit()

    def close(self) -> None:
        with self._lock:
            self.conn.close()

    # ------------------------------------------------------------- 异步包装
    # 图在 `ainvoke` 路径上会调这几个方法。用线程池包一层**不是为了性能**，
    # 而是为了不把「同步实现」变成「异步下不可用」——本课不做真异步驱动，
    # 但要让 `ainvoke` 与 `invoke` 两条路都能跑（第 8 篇才谈真异步后端）。
    async def aget_tuple(self, config: RunnableConfig) -> CheckpointTuple | None:
        return await asyncio.to_thread(self.get_tuple, config)

    async def alist(self, config: RunnableConfig | None, *,
                    filter: dict[str, Any] | None = None,      # noqa: A002
                    before: RunnableConfig | None = None,
                    limit: int | None = None) -> AsyncIterator[CheckpointTuple]:
        for tup in await asyncio.to_thread(
                lambda: list(self.list(config, filter=filter, before=before, limit=limit))):
            yield tup

    async def aput(self, config: RunnableConfig, checkpoint: Checkpoint,
                   metadata: CheckpointMetadata, new_versions: ChannelVersions
                   ) -> RunnableConfig:
        return await asyncio.to_thread(self.put, config, checkpoint, metadata, new_versions)

    async def aput_writes(self, config: RunnableConfig,
                          writes: Sequence[tuple[str, Any]],
                          task_id: str, task_path: str = "") -> None:
        await asyncio.to_thread(self.put_writes, config, writes, task_id, task_path)

    async def adelete_thread(self, thread_id: str) -> None:
        await asyncio.to_thread(self.delete_thread, thread_id)


def at_checkpoint(thread_id: str, checkpoint_id: str, checkpoint_ns: str = "") -> dict:
    """「回到某一步」的配置，**三个键一次给全**。

    为什么值得写成一个函数：少给 `checkpoint_ns` 时，两个后端**行为不一样**——
    内存后端直接 `KeyError: 'checkpoint_ns'`（它用下标读），而本模块的 SQLite 后端
    用 `.get(..., "")` 兜住、照常工作。也就是说：那份能让 SQLite 跑的配置，
    换回内存后端会当场报错，而报错发生在另一个后端上——**归因很容易找错地方**。
    统一从这一个函数造配置，这类差异就没有机会出现了。
    """
    return {"configurable": {"thread_id": thread_id, "checkpoint_ns": checkpoint_ns,
                             "checkpoint_id": checkpoint_id}}


def history(app, config: RunnableConfig) -> list[dict]:      # noqa: ANN001
    """把一条线程的快照读成一张表：**一步一行**，最新在前。

    为什么值得写成一个函数：`get_state_history` 返回的是迭代器，直接打印会看到
    一堆对象 `repr`。这里只留四个可核对的字段——第几步、从哪来（`source`）、
    这一步的节点、以及它当时看见的日志长度。
    """
    out = []
    for snap in app.get_state_history(config):
        values = snap.values or {}
        out.append({
            "checkpoint_id": snap.config["configurable"]["checkpoint_id"],
            "step": snap.metadata.get("step"),
            "source": snap.metadata.get("source"),
            "next": tuple(snap.next),
            "log_len": len(values.get("log", [])),
            "parent": (snap.parent_config or {}).get("configurable", {}).get("checkpoint_id"),
        })
    return out
