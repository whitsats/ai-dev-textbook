"""中立请求：把「一次调用」写成不依赖任何一家的形状。

三家把同一件事说得不一样，而**不一样的地方不是术语，是形状**：

- **系统提示**：一家放在顶层字段 `system`，一家放在顶层 `instructions`，
  第三家把它当成对话数组里的第一条 `role="system"` 消息；
- **工具参数**：一家递给你一个**对象**，另外两家递给你一个 **JSON 字符串**；
- **「为什么停」**：一家是一个 `stop_reason`，一家是一个 `finish_reason`，
  第三家拆成两个字段（`status` ＋ `incomplete_details.reason`）。

所以这一层只做一件事：**先把「一次调用」写成一个中立形状**，再让三个适配器各自翻译。
不这么做也能跑——每个调用点各写一份 `if vendor == ...`，而那种写法在第四家进来时
会把三处悄悄变成四处，第四处还没有测试。

三处口径与 6.1 的登记表同源：**抄的哪一天、抄的哪一页**（`WIRE_AS_OF` / `SOURCES`），
以及**说不出来的那一格要留空、不许猜**（`STOP_LOSSY`）。
"""
from __future__ import annotations

from dataclasses import dataclass, field

#: 抄这三份协议形状的那一天。它与价格页一样会变，所以必须进表。
WIRE_AS_OF = "2026-09-17"

#: 口径出处。翻译表里每一格都指得到这里的一行。
SOURCES: dict[str, str] = {
    "claude_messages": "https://platform.claude.com/docs/en/api/messages",
    "claude_streaming": "https://platform.claude.com/docs/en/build-with-claude/streaming",
    "claude_tools": "https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview",
    "openai_responses": "https://developers.openai.com/api/docs/guides/migrate-to-responses",
    "openai_functions": "https://developers.openai.com/api/docs/guides/function-calling",
    "openai_reasoning": "https://developers.openai.com/api/docs/guides/reasoning",
}

#: 三种方言的机器名。**它们不是「三家公司」**：后两种同属一家，
#: 而其中一种是另一家的**兼容层**——第六章的整章结论都建立在这个区分上。
DIALECTS: tuple[str, ...] = ("messages", "responses", "chat")

DIALECT_NAME: dict[str, str] = {
    "messages": "Messages（Anthropic）",
    "responses": "Responses（OpenAI）",
    "chat": "Chat Completions（兼容层）",
}


class WireError(ValueError):
    """翻译时**宁可报错也不猜**的那种错：缺必填、档位说不出来、参数不是 JSON。"""


# --------------------------------------------------------------- 规范形状

@dataclass(frozen=True)
class Tool:
    """一个工具。规范形状里 `schema` **一律是对象**（JSON Schema 的那个对象）。"""

    name: str
    description: str
    schema: dict
    strict: bool = False


@dataclass(frozen=True)
class Block:
    """内容块。规范形状里只有三种：文本、工具调用、工具结果。

    `arguments` 在规范形状里**是对象**——这是刻意的：三家里有两家在线上递的是
    JSON **字符串**，把它们统一成对象的工作量很小，而把这个差别放进业务代码、
    让每个调用点自己 `json.loads`，重复的错误处理就会长在三个地方。
    """

    kind: str                       # "text" / "tool_call" / "tool_result"
    text: str = ""
    call_id: str = ""
    name: str = ""
    arguments: dict | None = None
    is_error: bool = False


@dataclass(frozen=True)
class Message:
    """一轮对话。**规范形状里没有 `system` 这个角色**——系统提示是它自己的字段。

    这一条不是洁癖：三家对系统提示的处置各不相同（顶层字段 / 顶层字段 / 数组里的一条），
    所以把它留在消息数组里，就必须在每个适配器里再判断「这条是不是系统消息」。
    """

    role: str                       # "user" / "assistant"
    blocks: tuple[Block, ...]


@dataclass(frozen=True)
class Request:
    """一次调用。字段顺序与「翻译表」一致，方便逐行对读。"""

    model: str
    system: str
    messages: tuple[Message, ...]
    tools: tuple[Tool, ...] = ()
    max_output_tokens: int | None = None
    temperature: float | None = None
    stream: bool = False
    dialect: str = "messages"


@dataclass(frozen=True)
class Response:
    """一次答复。**它也是中立的**：业务代码只认这一个形状。"""

    text: str
    tool_calls: tuple[Block, ...]
    stop: str                       # 规范档（见 CANONICAL_STOPS）
    usage: dict = field(default_factory=dict)
    dialect: str = ""
    events: int = 0                 # 流式：读过多少帧（含不必看的记账帧）


# --------------------------------------------------------------- 翻译表

#: 规范字段 → 三种方言的**落点**。这是本章最核心的一张表：
#: 它把「三家不一样」从一句印象变成一个能逐格核的东西。
FIELD_MAP: dict[str, dict[str, str]] = {
    "system": {
        "messages": "system（顶层字段，字符串）",
        "responses": "instructions（顶层字段）",
        "chat": "messages[0]（role=system）",
    },
    "messages": {
        "messages": "messages[]，角色只有 user/assistant",
        "responses": "input[]，item 列表（消息只是 item 的一种）",
        "chat": "messages[]，角色有 system/user/assistant/tool",
    },
    "tools[].schema": {
        "messages": "input_schema",
        "responses": "parameters（与 name/type 同级，扁平）",
        "chat": "function.parameters（多一层 function）",
    },
    "tool_call.arguments": {
        "messages": "input（**对象**）",
        "responses": "arguments（**JSON 字符串**）",
        "chat": "function.arguments（**JSON 字符串**）",
    },
    "tool_result": {
        "messages": "user 消息里的 tool_result 块（tool_use_id）",
        "responses": "function_call_output（item，call_id）",
        "chat": "role=tool 的消息（tool_call_id）",
    },
    "max_output_tokens": {
        "messages": "max_tokens（**必填**）",
        "responses": "max_output_tokens（选填）",
        "chat": "max_completion_tokens（选填）",
    },
    "stop": {
        "messages": "stop_reason（一个字段）",
        "responses": "status ＋ incomplete_details.reason（两个字段）",
        "chat": "finish_reason（一个字段）",
    },
    "口径/版本": {
        "messages": "anthropic-version 请求头",
        "responses": "store（默认 true，要显式关）",
        "chat": "无版本头",
    },
}

#: 规范档。**这是「为什么停」的规范名**，不是任何一家的取值。
CANONICAL_STOPS: tuple[str, ...] = (
    "end_turn", "max_output", "tool_call", "stop_sequence", "refusal",
)

#: 规范档 → 各家的取值。`None` ＝ 这家**说不出来**（不许猜、不许塞进最近的一档）。
STOP_MAP: dict[str, dict[str, str | None]] = {
    "end_turn": {"messages": "end_turn", "responses": "completed", "chat": "stop"},
    "max_output": {"messages": "max_tokens", "responses": "incomplete/max_output_tokens",
                   "chat": "length"},
    "tool_call": {"messages": "tool_use", "responses": "completed", "chat": "tool_calls"},
    "stop_sequence": {"messages": "stop_sequence", "responses": None, "chat": "stop"},
    "refusal": {"messages": "refusal", "responses": None, "chat": "content_filter"},
}

#: 两种「说不出来」不是一回事，所以分开登记：
#:   **空** ＝ 这一格压根没有取值（`None`）；
#:   **撞车** ＝ 有取值，但与另一个档共用同一个值。
#: 撞车比空更危险：空会被 `None` 拦下，撞车**什么都不报**——读的人以为读到了。
STOP_LOSSY: dict[str, str] = {
    "responses/stop_sequence": "空：incomplete_details.reason 的两个取值都不是它",
    "responses/refusal": "空：拒答在这一家是一个内容块，不是停止原因",
    "responses/tool_call": "撞车：completed 同时表示「答完了」与「请你调工具」",
    "chat/stop_sequence": "撞车：与 end_turn 共用 stop，读的人分不出来",
}

#: 反过来查：某家在线上给的取值 → 规范档。**回程表也要有一份**，
#: 否则「读回来」这件事会各自实现一遍，而它们迟早会不一致。
STOP_BACK: dict[str, dict[str, str]] = {
    "messages": {"end_turn": "end_turn", "max_tokens": "max_output",
                 "tool_use": "tool_call", "stop_sequence": "stop_sequence",
                 "refusal": "refusal"},
    "responses": {"completed": "end_turn", "incomplete/max_output_tokens": "max_output"},
    "chat": {"stop": "end_turn", "length": "max_output", "tool_calls": "tool_call",
             "content_filter": "refusal"},
}


#: **形状层**：把「叫什么」换成「长什么形状」。这一层比名字层有用：
#: 名字全不同、而形状其实分三堆——改代码要看的正是这一堆。
SHAPE_MAP: dict[str, dict[str, str]] = {
    "system": {"messages": "顶层字段", "responses": "顶层字段", "chat": "数组里的一条"},
    "messages": {"messages": "数组（user/assistant）", "responses": "item 列表",
                 "chat": "数组（四个角色）"},
    "tools[].schema": {"messages": "一个字段装它", "responses": "与 name 同级",
                       "chat": "嵌一层 function"},
    "tool_call.arguments": {"messages": "对象", "responses": "JSON 字符串",
                           "chat": "JSON 字符串"},
    "tool_result": {"messages": "消息里的一个块", "responses": "与消息平级的 item",
                    "chat": "一条独立消息"},
    "max_output_tokens": {"messages": "必填", "responses": "选填", "chat": "选填"},
    "stop": {"messages": "一个字段", "responses": "两个字段", "chat": "一个字段"},
    "口径/版本": {"messages": "请求头", "responses": "请求体里的 store", "chat": "没有"},
}


def shape_landings() -> dict[str, int]:
    """每个字段有几种**形状**（而不是几种叫法）。"""
    return {k: len(set(v.values())) for k, v in SHAPE_MAP.items()}


def table_violations(stop_map: dict | None = None, stop_back: dict | None = None,
                     lossy: dict | None = None) -> list[str]:
    """正程表与回程表必须对得上。**这是翻译表唯一会响的一条路。**

    与 6.1 的 `violations()` 同一形状，而这里要防的是另一种漂：
    正程写着 `chat` 的 `max_output` 是 `length`，而回程把 `length` 读成
    `end_turn`——两张表各自看都完整，**合起来才看得出中间断了一根线**。

    三条判据：
    ① 空的那一格必须在 `lossy` 里登记为「空」（没登记的那些，读的人会以为是漏填）；
    ② 能原样表达的那些格，**回程必须指回原档**；
    ③ 回程表里的取值不能是孤儿（正程一个都不指向它）。
    """
    stop_map = STOP_MAP if stop_map is None else stop_map
    stop_back = STOP_BACK if stop_back is None else stop_back
    lossy = STOP_LOSSY if lossy is None else lossy
    bad: list[str] = []
    for stop, row in stop_map.items():
        for d in DIALECTS:
            v = row.get(d)
            kind = lossy.get(f"{d}/{stop}", "")
            if v is None:
                if not kind.startswith("空"):
                    bad.append(f"{d} 的 {stop} 是空的，却没有登记原因")
                continue
            if v not in stop_back.get(d, {}):
                bad.append(f"{d} 的 {stop} 写成 {v!r}，而回程表里没有这个取值")
            elif not kind and stop_back[d][v] != stop:
                bad.append(f"{d} 的 {stop} → {v} → 回程读成 {stop_back[d][v]}（对不上）")
    for d in DIALECTS:
        orphans = set(stop_back.get(d, {})) - {row.get(d) for row in stop_map.values()}
        if orphans:
            bad.append(f"{d} 的回程表里有正程永远不产生的取值：{sorted(orphans)}")
    if set(stop_back) != set(DIALECTS):
        bad.append(f"回程表的方言与 DIALECTS 不一致：{sorted(stop_back)}")
    return bad


def stop_cells() -> list[tuple[str, str, str | None, str]]:
    """把映射表摊成一行一格，供读数组装。**摊平的那一份与表同源，不另写一份。**"""
    return [(stop, d, STOP_MAP[stop][d], STOP_LOSSY.get(f"{d}/{stop}", ""))
            for stop in CANONICAL_STOPS for d in DIALECTS]


def distinct_landings() -> dict[str, int]:
    """每个规范字段有几个**互不相同**的落点。`3` ＝ 三家各说各的。"""
    return {k: len(set(v.values())) for k, v in FIELD_MAP.items()}


# --------------------------------------------------------------- 校验

def validate(req: Request) -> list[str]:
    """把一个规范请求问一遍「它能不能被翻译」。**空列表才是正常。**

    这里刻意把三条「翻过去才发现」的错提前：
    ① 系统提示为空（三家里有一家把它当必填的顶层字段）；
    ② 规范档与方言对得上（`Request.dialect` 必须是三种之一）；
    ③ 工具结果必须带 `call_id`（不带的话，三家都会各自猜一个）；
    ④ 一条 **assistant** 的工具调用之后必须跟着对应的结果——历史缺一环时，
       线上报的错与这里报的错不是同一个错，提前报能省一次网络往返。
    """
    bad: list[str] = []
    if req.dialect not in DIALECTS:
        bad.append(f"未知方言 {req.dialect!r}（只有 {DIALECTS}）")
    if not req.system.strip():
        bad.append("系统提示是空的——三家里有一家把它当必填的顶层字段")
    if not req.messages:
        bad.append("一条消息都没有")
    if req.max_output_tokens is not None and req.max_output_tokens <= 0:
        bad.append(f"max_output_tokens={req.max_output_tokens} 不是正数")
    seen_calls: set[str] = set()
    for i, msg in enumerate(req.messages):
        if msg.role not in ("user", "assistant"):
            bad.append(f"第 {i} 条消息的角色是 {msg.role!r}——规范形状里只有 user/assistant")
        for b in msg.blocks:
            if b.kind == "tool_call":
                if not b.call_id or not b.name:
                    bad.append(f"第 {i} 条的工具调用缺 call_id 或 name")
                seen_calls.add(b.call_id)
            elif b.kind == "tool_result":
                if not b.call_id:
                    bad.append(f"第 {i} 条的工具结果没有 call_id——三家都会各自猜一个")
                elif b.call_id not in seen_calls:
                    bad.append(f"第 {i} 条结果指向 {b.call_id}，而历史里没有这一次调用")
                seen_calls.discard(b.call_id)
            elif b.kind != "text":
                bad.append(f"第 {i} 条的块类型 {b.kind!r} 不认识")
    for t in req.tools:
        if not t.schema or t.schema.get("type") != "object":
            bad.append(f"工具 {t.name} 的 schema 不是对象——三家都按对象收")
    return bad


def summarize(req: Request) -> dict:
    """给读数组装的**扁平描述**：这一次调用里有什么，一个数一个数地数出来。"""
    return {
        "messages": len(req.messages),
        "blocks": sum(len(m.blocks) for m in req.messages),
        "tool_calls": sum(1 for m in req.messages for b in m.blocks if b.kind == "tool_call"),
        "tool_results": sum(1 for m in req.messages
                            for b in m.blocks if b.kind == "tool_result"),
        "tools": len(req.tools),
        "system_chars": len(req.system),
        "stream": req.stream,
    }
