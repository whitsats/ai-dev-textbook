"""v4 的会话历史：**消息对象 ＋ 裁剪 ＋ 记账**。

对照点。v3 的 `app/agent/memory.py` 有四种装配策略（full / clean / note / compress）、
摘要生成、笔记提取、指纹去重与两个存储实现——那是 3.6 一整章的内容，
因为它要回答「清空上下文之后靠什么接上」。v4 的这一步只做三件小事，
而这三件事在框架里都已经是**类型**或**现成函数**了：

    v3：自己定义 Message 数据类、自己拼 OpenAI 格式、自己写裁剪与摘要
    v4：HumanMessage / AIMessage 是类型；裁剪有 `trim_messages`；用量在 `usage_metadata` 里

**但有一个坑必须点出来**：`trim_messages` 的 `max_tokens` 数什么，取决于你传的
`token_counter`。传 `len` 时它数的是**消息条数**，不是词元——名字叫 max_tokens，
数的却是条数。这在离线测试里是很方便的（不需要分词器），
但它也正是「框架的默认值必须去查」的同一个道理：**参数名不是契约，实现才是。**
"""
from __future__ import annotations

from dataclasses import dataclass, field

from langchain.messages import AIMessage, HumanMessage, SystemMessage, trim_messages


@dataclass
class Usage:
    """这一轮会话的账：**输入与输出分开**（v3 的实测：输入占比可达 96%）。"""

    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    per_call: list[tuple[int, int]] = field(default_factory=list)

    @property
    def total(self) -> int:
        return self.input_tokens + self.output_tokens

    @property
    def input_share(self) -> float:
        return round(self.input_tokens / self.total, 4) if self.total else 0.0

    def add(self, message) -> bool:
        """从一条 AI 消息里把用量抄下来。读不到就返回 False——**不编一个数**。"""
        meta = getattr(message, "usage_metadata", None) or {}
        if not meta:
            return False
        self.calls += 1
        self.input_tokens += int(meta.get("input_tokens", 0) or 0)
        self.output_tokens += int(meta.get("output_tokens", 0) or 0)
        self.per_call.append((int(meta.get("input_tokens", 0) or 0),
                              int(meta.get("output_tokens", 0) or 0)))
        return True

    def table(self) -> str:
        rows = "｜".join(f"{i + 1} 次 {a}/{b}" for i, (a, b) in enumerate(self.per_call))
        return (f"调用 {self.calls} 次｜输入 {self.input_tokens} / 输出 {self.output_tokens}"
                f"（共 {self.total}，输入占比 {self.input_share:.1%}）"
                + (f"｜逐次 {rows}" if self.per_call else ""))


class ChatHistory:
    """一次会话的消息列表。系统提示单独存，因为它**永远不该被裁掉**。"""

    def __init__(self, *, system: str = "", max_messages: int = 12) -> None:
        self.system = system
        self.max_messages = max_messages
        self._messages: list = []
        self.usage = Usage()
        self.trimmed_calls = 0

    def add_user(self, text: str) -> None:
        self._messages.append(HumanMessage(text))

    def add_ai(self, message) -> str:
        """收下模型的回复：抄账、入库、返回正文。"""
        if not isinstance(message, AIMessage):
            raise TypeError(f"只收 AIMessage，收到 {type(message).__name__}")
        self.usage.add(message)
        self._messages.append(message)
        return message.text

    def _kept(self) -> list:
        """裁剪后留下的历史（**不含**系统消息）。**纯函数式**：不改任何计数器。

        `dropped` 与 `to_messages` 都走它——否则一个「读状态」的属性会顺手加计数，
        而打印顺序一变，读数就不一样了。
        """
        return trim_messages(
            self._messages,
            max_tokens=self.max_messages,
            token_counter=len,          # 数的是**条数**，见模块文档
            strategy="last",            # 留最近的那些
            include_system=False,       # 系统消息不在这个列表里，由本类单独拼
            allow_partial=False,        # 不许把一条消息切成两半
        )

    def to_messages(self) -> list:
        """送给模型的完整入参：系统消息 ＋ 裁剪后的历史。"""
        kept = self._kept()
        if len(kept) < len(self._messages):
            self.trimmed_calls += 1
        prefix = [SystemMessage(self.system)] if self.system else []
        return prefix + kept

    @property
    def dropped(self) -> int:
        return max(0, len(self._messages) - len(self._kept()))

    def __len__(self) -> int:
        return len(self._messages)
