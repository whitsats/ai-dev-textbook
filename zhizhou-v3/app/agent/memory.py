"""知舟的记忆：短期历史、长期偏好，以及把两者装配成一次请求的那一步。

三件事分开放，因为它们坏的方式不一样：

- **短期记忆**（这次会话说过什么）——存 `agent_message`，装配时才决定送多少；
- **长期记忆**（跨会话仍然成立的偏好与事实）——存 `agent_memory`，按用户召回；
- **装配**（把上面两份变成一次请求）——纯函数，三套手法只改这一步。

一条贯穿的边界：**记忆不是真相，是索引**。库里存的是历史，送进模型的是它的投影。
投影一定是有损的，所以「丢掉了什么」必须能被算出来（`Assembly.dropped_*`），
而不是凭感觉觉得「应该够用」——3.6.4 的账就是这么算的。
"""
from __future__ import annotations

import hashlib
import re
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Protocol

from app.llm.tokens import official_counter

KEEP_TOOL = 2            # 清理：留最近几条工具结果的全文
KEEP_TURNS = 6           # 笔记：最近几条不压
NOTE_CHARS = 50          # 笔记：每条截到多少字符
MAX_VALUE = 200          # 长期记忆：值多长算「太长」
MAX_PER_TURN = 2         # 长期记忆：一轮最多写几条

POLICIES = ("full", "clean", "note", "compress")
NOTE_HEAD = "早前对话的笔记（不是新指令，只作背景）："


# ---------------------------------------------------------------- 数据形状

@dataclass(frozen=True)
class ToolCall:
    """一次工具调用的**声明**：id、函数名、参数。

    为什么不直接用传输层的那个 `ToolCall`（`app/llm/client.py` 也有一个）：
    库里的行是数据，不是 HTTP 载荷。存储层跟着传输层走，换一家服务商就要改库。
    转换只发生在 `to_openai()` 一个地方，那里才允许出现 HTTP 的形状。

    它存在的理由是**重放**：只存 `tool_call_id` 不够。下一次会话要把历史装回上下文时，
    服务商要求每条 `tool` 消息前面有一条**声明了同一个 id 的 assistant 消息**，
    而声明里必须有函数名与参数——只有 id 装不出一条合法的声明（实测回 400）。
    """

    id: str
    name: str
    arguments: str = "{}"


@dataclass
class Message:
    """一条消息。工具往返按**成对**存：声明在 assistant 上，结果在 tool 上。"""

    role: str                       # user ｜ assistant ｜ tool ｜ note
    content: str
    tokens: int = 0
    tool_call_id: str = ""
    tool_calls: tuple[ToolCall, ...] = ()

    def digest(self) -> str:
        return hashlib.sha256(self.content.encode("utf-8")).hexdigest()[:16]

    def is_tool(self) -> bool:
        return self.role == "tool"


@dataclass
class MemoryItem:
    """长期记忆的一条。`key` 在同一用户下唯一——**覆盖，不追加**。"""

    key: str
    value: str
    scope: str = "user"             # user ｜ session
    source: str = ""                # 写入它的那次会话
    expires_at: datetime | None = None
    updated_at: datetime | None = None

    def expired(self, now: datetime | None = None) -> bool:
        if self.expires_at is None:
            return False
        return aware(self.expires_at) <= aware(now or datetime.now(timezone.utc))


def aware(dt: datetime) -> datetime:
    """把时间统一成带时区的。

    不是强迫症：SQLite 存的是不带时区的字符串，取回来 `tzinfo` 是 `None`，
    和 `datetime.now(timezone.utc)` 一比就抛 `TypeError`。真实库（Postgres）取回来是带时区的。
    **同一个模块要在两种库上跑，就先归一化，再比较。**
    """
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt


@dataclass
class Assembly:
    """装配结果：送进模型的那一段，以及它的账。"""

    messages: list[Message]
    policy: str = "full"
    note: str = ""
    dropped_tool_results: int = 0
    dropped_messages: int = 0
    input_tokens: int = 0
    baseline_tokens: int = 0          # 同一份历史在 full 下的词元数

    @property
    def saved(self) -> float:
        """相对全量省下的比例。峰值口径就是它：装配后的这一段就是最大的一次请求。"""
        return 0.0 if not self.baseline_tokens else 1 - self.input_tokens / self.baseline_tokens


# ---------------------------------------------------------------- 装配：三套手法

def count_messages(msgs: Sequence[Message], count: Callable[[str], int]) -> int:
    return sum(count(f"{m.role}: {m.content}") for m in msgs)


def clean_tool_results(history: Sequence[Message], keep_recent: int = KEEP_TOOL
                       ) -> tuple[list[Message], int]:
    """只动工具结果：更早的换成一行摘要，用户与助手的话一字不动。"""
    seen, out, replaced = 0, [], 0
    for m in reversed(history):
        if not m.is_tool():
            out.append(m)
            continue
        seen += 1
        if seen <= keep_recent:
            out.append(m)
        else:
            replaced += 1
            out.append(Message("tool", f"[工具结果已清理：{len(m.content)} 字符 → "
                                        f"{m.content[:40]}……]", tool_call_id=m.tool_call_id))
    return list(reversed(out)), replaced


def note_tail(history: Sequence[Message], keep_recent_turns: int = KEEP_TURNS,
              note_chars: int = NOTE_CHARS, summary: str = "") -> tuple[list[Message], int]:
    """把更早的对话压成一条笔记。

    `summary` 为空时用**逐行截断**（确定性、可复现，代价是丢信息）；
    不为空时用它——那是模型压缩出来的版本（3.6.5），有损且不可复现，但更短。
    """
    if len(history) <= keep_recent_turns:
        return list(history), 0
    head, tail = history[:-keep_recent_turns], list(history[-keep_recent_turns:])
    if summary.strip():
        body = summary.strip()
    else:
        lines = [f"- [{m.role}] {m.content[:note_chars]}" for m in head if not m.is_tool()]
        if not lines:
            return tail, len(head)
        body = "\n".join(lines)
    return [Message("note", f"{NOTE_HEAD}\n{body}")] + tail, len(head)


def sanitize(messages: Sequence[Message]) -> tuple[list[Message], int]:
    """去掉会让请求非法的消息。

    窗口截断（只留最近 N 条）会**从中间切断**一段工具往返，于是历史的开头可能是一条
    `tool` 消息——它的 `tool_call_id` 在上下文里找不到对应的 `assistant` 调用，
    服务商直接回 400。这不是理论问题：`max_messages` 一开就会撞上。

    同一个理由，`note` 不是合法角色，装成 `user` 消息发出去（并在文字里写明它不是指令）。
    """
    out, dropped = [], 0
    pending: set[str] = set()
    for m in messages:
        if m.role == "assistant":
            pending |= {c.id for c in m.tool_calls}
            out.append(m)
        elif m.is_tool():
            if m.tool_call_id and m.tool_call_id in pending:
                pending.discard(m.tool_call_id)
                out.append(m)
            else:
                dropped += 1                       # 没有对应的调用：丢掉，别把请求弄非法
        elif m.role == "note":
            out.append(Message("user", m.content))
        else:
            out.append(m)

    # 另一种半截：最后一条 assistant 宣布了调用、结果还没回来（流被中断、重试边界、
    # 或者历史就是在这一刻被截断的）。留着它，请求同样非法——校验的是**声明与结果配对**。
    if pending:
        for i in range(len(out) - 1, -1, -1):
            if out[i].role == "assistant" and pending & {c.id for c in out[i].tool_calls}:
                pending -= {c.id for c in out[i].tool_calls}
                dropped += 1
                del out[i]
    return out, dropped


def to_openai(messages: Sequence[Message]) -> list[dict]:
    """装配结果 → 传输层载荷。**全项目只有这里把 Message 变成 HTTP 的形状。**

    调用前必须先过 `sanitize()`：`to_openai` 只负责翻译，不负责合法化。
    真跑时把没合法化的历史直接发出去，得到的是服务商的一句
    「messages with role 'tool' must be a response to a preceding message with tool_calls」——
    这句话是本章最贵的一行字（它意味着整次会话的上下文作废，重试也一样）。
    """
    out: list[dict] = []
    for m in messages:
        if m.is_tool():
            out.append({"role": "tool", "tool_call_id": m.tool_call_id, "content": m.content})
        elif m.tool_calls:
            out.append({"role": "assistant", "content": m.content,
                        "tool_calls": [{"id": c.id, "type": "function",
                                        "function": {"name": c.name, "arguments": c.arguments}}
                                       for c in m.tool_calls]})
        else:
            # `note` 之外的未知角色也按 user 发：宁可少一层语义，不要让请求非法
            out.append({"role": m.role if m.role in ("user", "assistant") else "user",
                        "content": m.content})
    return out


def assemble(history: Sequence[Message], *, policy: str = "note", summary: str = "",
             keep_tool: int = KEEP_TOOL, keep_turns: int = KEEP_TURNS,
             note_chars: int = NOTE_CHARS, max_messages: int | None = None,
             count: Callable[[str], int] | None = None) -> Assembly:
    """三套手法（＋全量基线）都只改这一步：`full` / `clean` / `note` / `compress`。"""
    if policy not in POLICIES:
        raise ValueError(f"未知的装配策略：{policy!r}，可选 {POLICIES}")
    count = count or official_counter()

    window = list(history)
    cut = 0
    if max_messages is not None and len(window) > max_messages:
        cut = len(window) - max_messages
        window = window[-max_messages:]

    # 基线取「同一窗口下的全量装配」而不是原始历史的词元数：
    # 否则对比里混进了两件事（清理的效果 + 请求合法化的效果），得出的降幅是假的。
    baseline, _ = sanitize(window)
    baseline_tokens = count_messages(baseline, count)

    replaced = 0
    if policy == "full":
        msgs: list[Message] = window
    else:
        msgs, replaced = clean_tool_results(window, keep_tool)
        if policy in ("note", "compress"):
            msgs, compressed = note_tail(msgs, keep_turns, note_chars, summary)
            cut += compressed
    msgs, orphans = sanitize(msgs)

    note = next((m.content for m in msgs if m.role == "user" and m.content.startswith(NOTE_HEAD)), "")
    return Assembly(messages=msgs, policy=policy, note=note,
                    dropped_tool_results=replaced, dropped_messages=cut + orphans,
                    input_tokens=count_messages(msgs, count), baseline_tokens=baseline_tokens)


def render_memory(items: Iterable[MemoryItem]) -> str:
    """长期记忆进系统提示的那一段。**空的时候返回空串**，别留一个空标题占词元。"""
    rows = [f"- {i.key}：{i.value}" for i in items]
    if not rows:
        return ""
    return "以下是这位用户的长期记忆（跨会话有效；与本次对话冲突时以本次为准）：\n" + "\n".join(rows)


def compress(messages: Sequence[Message], *, config, prompt_path, chat_fn=None,
             max_tokens: int = 512) -> tuple[str, int]:
    """把更早的对话压成笔记。**全章唯一有损且不可复现的一步**，代价是一次模型调用。

    返回 `(笔记, 词元)`。词元要记账：压缩本身不省到最后一次请求上，它就是那次请求的一部分
    （所以它是「花现在的钱，买后面每一轮的空间」）。
    """
    from app.llm.client import chat          # 延迟导入：只有真压缩时才需要客户端

    chat_fn = chat_fn or chat
    prompt = prompt_path.read_text(encoding="utf-8")
    body = "\n".join(f"[{m.role}] {m.content}" for m in messages)
    reply = chat_fn([{"role": "system", "content": prompt},
                     {"role": "user", "content": body}], config=config, max_tokens=max_tokens)
    return (reply.content or "").strip(), reply.tokens


# ---------------------------------------------------------------- 长期记忆的写入

# 键名空间由**代码**拥有：模型或规则只能往这些格子里写，不能自己发明键。
TOPICS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("publish", ("发布", "上线", "公开")),
    ("tone", ("语气", "口吻", "风格")),
    ("length", ("字数", "长度", "篇幅")),
    ("tags", ("标签",)),
    ("signature", ("署名", "作者名", "落款")),
)
CUES = ("以后", "记住", "默认", "每次", "别", "不要", "一律")


def normalize(text: str) -> str:
    """键名归一：空白折成一个空格、去标点、去语气词。同一件事换个说法要落到同一个键。"""
    s = re.sub(r"[，。！？、；：,.!?;:（）()「」\"'\s]+", " ", text).strip()
    return re.sub(r"\s+", " ", s)


@dataclass
class MemoryWriter:
    """一轮对话里，什么东西值得活到下一次会话。

    三个闸都在这里，而且**都不看模型的输出**——只看用户说的话。理由有两个：
    提示注入想污染长期记忆，最短的路径就是让模型「转述」一句恶意偏好；
    而规则抽取能被单测覆盖，模型抽取不能（要用模型抽取的写法见本章练习）。
    """

    max_value: int = MAX_VALUE
    max_items: int = MAX_PER_TURN
    ttl_days: int = 180
    attribution_days: int = 2

    def topic_of(self, text: str) -> str | None:
        for key, words in TOPICS:
            if any(w in text for w in words):
                return key
        return None

    def from_turn(self, task: str, *, session_id: int = 0) -> list[MemoryItem]:
        """从用户这一轮的话里挑出偏好。**没有提示词就一条都不写**，宁可漏，不要瞎存。"""
        out: list[MemoryItem] = []
        for sentence in re.split(r"[。！？!?\n]", task):
            if not any(c in sentence for c in CUES):
                continue
            topic = self.topic_of(sentence)
            if topic is None:
                continue
            value = sentence.strip()[:self.max_value]
            out.append(MemoryItem(f"pref.{topic}", value, "user", str(session_id),
                                  datetime.now(timezone.utc) + timedelta(days=self.ttl_days)))
            if len(out) >= self.max_items:
                break
        return out

    def from_task(self, task: str, reason: str, *, session_id: int = 0) -> MemoryItem:
        """任务结果也值得记一条，但**活得短**：它描述的是一次具体经过，不是长期偏好。"""
        return MemoryItem("task.last", f"{task.strip()[:80]}（{reason}）", "user", str(session_id),
                          datetime.now(timezone.utc) + timedelta(days=self.attribution_days))


# ---------------------------------------------------------------- 存储：替身与真库

class MemoryStore(Protocol):
    """记忆的读写口。两个实现：内存替身（离线跑）与真库（`SqlMemoryStore`）。"""

    def open_session(self, user_id: int, *, title: str) -> int: ...
    def history(self, session_id: int, *, limit: int | None = None) -> list[Message]: ...
    def append(self, session_id: int, message: Message) -> None: ...
    def remember(self, user_id: int, item: MemoryItem) -> None: ...
    def recall(self, user_id: int, *, limit: int = 20) -> list[MemoryItem]: ...
    def forget(self, user_id: int, key: str) -> int: ...
    def transcript(self, session_id: int) -> dict: ...


class InMemoryStore:
    """替身：不装数据库也能把「装配 → 调用 → 写回 → 下一次会话」整条路走完。

    测试与离线演示用它；**装配逻辑一行都不用改**——这正是把存储抽成协议的目的。
    """

    def __init__(self) -> None:
        self._sessions: dict[int, dict] = {}
        self._messages: dict[int, list[Message]] = {}
        self._memory: dict[tuple[int, str], MemoryItem] = {}
        self._next = 1

    def open_session(self, user_id: int, *, title: str) -> int:
        sid = self._next
        self._next += 1
        self._sessions[sid] = {"id": sid, "user_id": user_id, "title": title[:64],
                               "created_at": datetime.now(timezone.utc), "state": "active"}
        self._messages[sid] = []
        return sid

    def history(self, session_id: int, *, limit: int | None = None) -> list[Message]:
        # **不存在的会话要报错，而不是返回空数组**：空数组会被上层当成「这段会话还没说过话」，
        # 于是一个拼错的 id 会静静地开出一段假历史（端点声称的 404 也就永远不会发生）。
        if session_id not in self._sessions:
            raise KeyError(f"会话 {session_id} 不存在")
        got = self._messages.get(session_id, [])
        return got[-limit:] if limit else list(got)

    def append(self, session_id: int, message: Message) -> None:
        self._messages.setdefault(session_id, []).append(message)

    def remember(self, user_id: int, item: MemoryItem) -> None:
        item.updated_at = datetime.now(timezone.utc)     # 覆盖：同一个键只留最新的一条
        self._memory[(user_id, item.key)] = item

    def recall(self, user_id: int, *, limit: int = 20) -> list[MemoryItem]:
        rows = [i for (uid, _), i in self._memory.items() if uid == user_id and not i.expired()]
        return sorted(rows, key=lambda i: i.key)[:limit]

    def forget(self, user_id: int, key: str) -> int:
        return 1 if self._memory.pop((user_id, key), None) else 0

    def transcript(self, session_id: int) -> dict:
        session = self._sessions.get(session_id)
        if session is None:
            raise KeyError(f"会话 {session_id} 不存在")
        return {**session,
                "messages": [{"role": m.role, "content": m.content, "digest": m.digest()}
                             for m in self.history(session_id)]}


class SqlMemoryStore:
    """真库实现。**导入不建连接**：装配层不认识数据库，只有这个类认识。

    `session_factory` 给的是 SQLAlchemy 的 `Session`——同步版。异步版（1.12 的 `AsyncSession`）
    换的只是这里的方法签名，`assemble` 与 `MemoryWriter` 一行都不用动。
    """

    def __init__(self, session_factory) -> None:
        self.session_factory = session_factory

    def open_session(self, user_id: int, *, title: str) -> int:
        from app.models.agent import AgentSession

        with self.session_factory() as s:
            row = AgentSession(user_id=user_id, title=title[:64])
            s.add(row)
            s.commit()
            return int(row.id)

    def history(self, session_id: int, *, limit: int | None = None) -> list[Message]:
        from sqlalchemy import select

        from app.models.agent import AgentMessage, AgentSession

        with self.session_factory() as s:
            # 同上：先确认会话存在。真库这里多一次查询，换来的是「拼错的 id 不会静默建库」。
            if s.get(AgentSession, session_id) is None:
                raise KeyError(f"会话 {session_id} 不存在")
            stmt = (select(AgentMessage).where(AgentMessage.session_id == session_id)
                    .order_by(AgentMessage.id))
            rows = list(s.scalars(stmt))
        msgs = [Message(r.role, r.content or "", r.tokens, r.tool_call_id or "") for r in rows]
        return msgs[-limit:] if limit else msgs

    def append(self, session_id: int, message: Message) -> None:
        from app.models.agent import AgentMessage

        with self.session_factory() as s:
            s.add(AgentMessage(session_id=session_id, role=message.role,
                               content=message.content, content_digest=message.digest(),
                               tool_call_id=message.tool_call_id, tokens=message.tokens))
            s.commit()

    def remember(self, user_id: int, item: MemoryItem) -> None:
        from sqlalchemy import select

        from app.models.agent import AgentMemory

        with self.session_factory() as s:
            row = s.scalar(select(AgentMemory).where(AgentMemory.user_id == user_id,
                                                    AgentMemory.key == item.key))
            if row is None:                       # upsert：键唯一，所以只有「插」与「改」两种
                row = AgentMemory(user_id=user_id, key=item.key)
                s.add(row)
            row.value, row.scope, row.source = item.value, item.scope, item.source
            row.expires_at, row.updated_at = item.expires_at, datetime.now(timezone.utc)
            s.commit()

    def recall(self, user_id: int, *, limit: int = 20) -> list[MemoryItem]:
        from sqlalchemy import or_, select

        from app.models.agent import AgentMemory

        now = datetime.now(timezone.utc)
        stmt = (select(AgentMemory)
                .where(AgentMemory.user_id == user_id,
                       or_(AgentMemory.expires_at.is_(None), AgentMemory.expires_at > now))
                .order_by(AgentMemory.key).limit(limit))
        with self.session_factory() as s:
            rows = list(s.scalars(stmt))
        return [MemoryItem(r.key, r.value, r.scope, r.source, r.expires_at, r.updated_at)
                for r in rows]

    def forget(self, user_id: int, key: str) -> int:
        from sqlalchemy import delete

        from app.models.agent import AgentMemory

        with self.session_factory() as s:
            got = s.execute(delete(AgentMemory).where(AgentMemory.user_id == user_id,
                                                     AgentMemory.key == key))
            s.commit()
            return int(got.rowcount or 0)

    def transcript(self, session_id: int) -> dict:
        from sqlalchemy import select

        from app.models.agent import AgentSession

        with self.session_factory() as s:
            row = s.get(AgentSession, session_id)
            if row is None:
                raise KeyError(f"会话 {session_id} 不存在")
            session = {"id": row.id, "user_id": row.user_id, "title": row.title,
                       "created_at": row.created_at, "state": row.state}
        return {**session,
                "messages": [{"role": m.role, "content": m.content, "digest": m.digest()}
                             for m in self.history(session_id)]}


__all__ = ["Message", "ToolCall", "MemoryItem", "Assembly", "assemble", "sanitize",
           "clean_tool_results", "note_tail", "render_memory", "compress", "to_openai",
           "MemoryWriter", "MemoryStore", "InMemoryStore", "SqlMemoryStore", "aware", "POLICIES"]


if __name__ == "__main__":
    from app.llm.tokens import local_counter

    local = local_counter()
    # 工具消息必须携带 `tool_call_id`，且它的 `assistant` 调用要在前面：这是请求合法的前提
    def call(i: str):
        return Message("assistant", "", tool_calls=(ToolCall(i, "read_article", '{"article_id": 42}'),))

    hist = [
        Message("user", "帮我找一篇讲刷新令牌的文章"),
        call("c1"),
        Message("tool", "命中 3 条：《JWT 刷新令牌怎么做》(id 42)……" * 20, tool_call_id="c1"),
        Message("assistant", "找到了，要读正文吗？"),
        Message("user", "读一下，读完按它的口径改稿"),
        call("c2"),
        Message("tool", "《JWT 刷新令牌怎么做》正文……" * 30, tool_call_id="c2"),
        Message("assistant", "读完了，讲了三种做法。"),
        Message("user", "作者是谁"),
        call("c3"),
        Message("tool", "作者用户 id：7；创建时间：2025-11……" * 10, tool_call_id="c3"),
        Message("assistant", "作者的用户 id 是 7。"),
        Message("user", "标签有哪些"),
        call("c4"),
        Message("tool", "安全 / 后端 / JWT / 部署" * 8, tool_call_id="c4"),
        Message("assistant", "标签最多选三个。"),
        Message("user", "直接发布吧"),
        Message("assistant", "发布需要人工确认。"),
    ]
    print("=== 三套手法在同一份历史上的账（本地估算，口径与 experiments/memory_cost.py 一致）===")
    print(f"  {'策略':<10}{'词元':>8}{'省下':>8}  换掉了什么")
    for policy in POLICIES[:3]:
        a = assemble(hist, policy=policy, count=local)
        print(f"  {policy:<10}{a.input_tokens:>8}{a.saved:>7.0%}  "
              f"工具结果换摘要 {a.dropped_tool_results} 条；合并/丢弃消息 {a.dropped_messages} 条")

    print()
    print("=== 两种半截历史：截断会同时弄坏开头与结尾 ===")
    a = assemble(hist, policy="full", max_messages=8, count=local)
    print(f"  只留最近 8 条 → 窗口第一条是 {hist[-8].role!r}（它的调用已被截掉）；"
          f"装配后第一条是 {a.messages[0].role!r}，丢掉 {a.dropped_messages} 条")
    partial = hist[:14]            # 第 14 条宣布了调用，结果还没回来：流被中断的样子
    a = assemble(partial, policy="full", count=local)
    print(f"  历史停在「assistant 宣布调用」这一步 → 装配后最后一条是 "
          f"{a.messages[-1].role!r}，丢掉 {a.dropped_messages} 条")

    print()
    print("=== 重放：只存 tool_call_id 装不出合法请求 ===")
    broken = [Message("tool", "命中 3 条……", tool_call_id="c1")]
    fixed, dropped = sanitize(broken)
    print(f"  一段没有声明的 tool 历史 → 装配后 {len(fixed)} 条（丢掉 {dropped} 条）；"
          f"它就是服务商报 400 的那种请求")
    legal = to_openai(assemble(hist, policy="full", count=local).messages[:3])
    print(f"  成对的那三行 → {[m['role'] for m in legal]}；"
          f"tool 前面那条备有 tool_calls：{bool(legal[1].get('tool_calls'))}")

    print()
    print("=== 长期记忆：同键覆盖，且「活得多久」必须有人回答 ===")
    store = InMemoryStore()
    sid = store.open_session(7, title="刷新令牌")
    writer = MemoryWriter()
    for text in ("以后发布一律先给我看草稿", "记住我的语气别太正式"):
        for item in writer.from_turn(text, session_id=sid):
            store.remember(7, item)
    again = writer.from_turn("以后发布一律先给我看草稿", session_id=sid)[0]
    store.remember(7, again)                # 同名偏好再说一遍：覆盖，不追加
    rows = store.recall(7)
    print(f"  写了 3 次，召回 {len(rows)} 条：" + "；".join(f"{i.key}={i.value[:12]}" for i in rows))
    print(f"  与本次对话冲突时的口径：{render_memory(rows).splitlines()[0]}")
    stale = MemoryItem("pref.tone", "上个月那次会话里的旧语气", "user", str(sid),
                       datetime.now(timezone.utc) - timedelta(days=1))     # 已经过期
    store.remember(7, stale)
    keys = [i.key for i in store.recall(7)]
    print(f"  写入一条已过期的偏好后才召回：{keys}（过期的那条不在里面，也不是被删了）")
