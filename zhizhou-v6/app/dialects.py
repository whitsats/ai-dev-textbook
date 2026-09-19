"""三个适配器：把中立请求翻成三家的载荷，再把三家的答复翻回来。

三家在这里被当成**同一件事的三种方言**。所以每个适配器只有四个动作：
`to_wire`（请求 → 载荷）、`from_wire`（非流式答复 → 中立答复）、
`from_stream`（SSE 帧 → 中立答复）、`headers`（认证与口径头）。

三处刻意的不对称，各自都对应一个真事故：

1. **`arguments` 一律翻成对象**。三家里两家的线上形状是 **JSON 字符串**，
   所以在 `from_wire` / `from_stream` 里必须 `json.loads`。解析失败**报错**——
   静默退回空字典会伪造一次「模型没传参数」的调用，那种账在线上比报错贵得多；
2. **停止原因宁可留空（`None`）也不塞进最近的一档**。兼容层上「命中停止词」
   与「正常结束」共用同一个取值，这一格**读到的是 `end_turn`**——所以
   `STOP_LOSSY` 里那三条要写在报错与文档里，而不是悄悄替读者决定；
3. **必填项先在本层报错**。Messages 的 `max_tokens` 是必填，而另外两家选填——
   规范请求里 `max_output_tokens=None` 时，翻译到 Messages 会当场 `WireError`，
   而不是替调用方猜一个数（猜出来的数会进账单，而没人知道它是猜的）。
"""
from __future__ import annotations

import json

from app.registry import MODELS
from app.wire import (DIALECTS, STOP_BACK, WIRE_AS_OF, Block, Message, Request,
                      Response, Tool, WireError)

#: 一条答复在三种方言里的公共文本与工具参数。**三段夹具流必须解出同一个它**——
#: 所以它只写一次，三段流各自只是「同一件事的三种帧形」。
STREAM_TEXT = "知舟：先查一下"
STREAM_ARGS = {"q": "北京", "top_k": 3}


def _dump(obj: dict) -> str:
    """线上的 JSON 字符串。**`ensure_ascii=False` 是给读者的**：
    线上字节一样，而读日志的人不必再解一层 `\\u`。"""
    return json.dumps(obj, ensure_ascii=False, sort_keys=True)


def load_arguments(raw: str, where: str) -> dict:
    """把那两家的 JSON 字符串解开。**坏 JSON 要报错**，不许静默成 `{}`。

    公开名字是刻意的：读数组与测试都要拿它当**第二把尺子**去量那两家的形状。
    """
    if not isinstance(raw, str):
        raise WireError(f"{where}：参数应当是 JSON 字符串，收到 {type(raw).__name__}")
    try:
        got = json.loads(raw or "{}")
    except json.JSONDecodeError as exc:
        raise WireError(f"{where}：参数不是合法 JSON（{exc.msg}）；"
                        f"原文前 60 字符：{raw[:60]!r}") from exc
    if not isinstance(got, dict):
        raise WireError(f"{where}：参数解出来是 {type(got).__name__}，不是一个对象")
    return got


def _back(dialect: str, raw: str | None, where: str) -> str:
    """线上取值 → 规范档。**表里没有的取值要报错**：它意味着协议变了。"""
    if raw in STOP_BACK[dialect]:
        return STOP_BACK[dialect][raw]
    raise WireError(f"{where}：{dialect} 方言里没有这个停止原因 {raw!r}"
                    f"（已登记：{sorted(STOP_BACK[dialect])}）")


# --------------------------------------------------------------- Messages

class MessagesAdapter:
    """Anthropic Messages：`system` 在顶层、`max_tokens` 必填、工具参数是对象。"""

    dialect = "messages"
    path = "/v1/messages"

    def headers(self, req: Request) -> dict:
        #: 口径写在头上而不是体里：同一份载荷换个版本头就是另一次调用。
        return {"x-api-key": "<从环境变量来>", "anthropic-version": "2023-06-01",
                "content-type": "application/json"}

    def to_wire(self, req: Request) -> dict:
        if req.max_output_tokens is None:
            raise WireError("Messages 方言要求 max_tokens 必填；规范请求没给——"
                            "替你猜一个数会进账单，而没人知道它是猜的")
        payload: dict = {"model": req.model, "max_tokens": req.max_output_tokens,
                         "system": req.system, "messages": []}
        for msg in req.messages:
            blocks: list[dict] = []
            for b in msg.blocks:
                if b.kind == "text":
                    blocks.append({"type": "text", "text": b.text})
                elif b.kind == "tool_call":
                    blocks.append({"type": "tool_use", "id": b.call_id,
                                   "name": b.name, "input": b.arguments or {}})
                else:
                    if msg.role != "user":
                        raise WireError("工具结果要放在一条 user 消息里——"
                                        f"这一条的角色是 {msg.role!r}")
                    blocks.append({"type": "tool_result", "tool_use_id": b.call_id,
                                   "content": b.text, "is_error": b.is_error})
            payload["messages"].append({"role": msg.role, "content": blocks})
        if req.tools:
            payload["tools"] = [
                {"name": t.name, "description": t.description,
                 "input_schema": t.schema, "strict": t.strict} for t in req.tools]
        if req.temperature is not None:
            payload["temperature"] = req.temperature
        if req.stream:
            payload["stream"] = True
        return payload

    def from_wire(self, payload: dict) -> Response:
        text, calls = [], []
        for b in payload.get("content", []):
            if b.get("type") == "text":
                text.append(b.get("text", ""))
            elif b.get("type") == "tool_use":
                calls.append(Block("tool_call", call_id=b.get("id", ""),
                                   name=b.get("name", ""),
                                   arguments=b.get("input") or {}))
        return Response(text="".join(text), tool_calls=tuple(calls),
                        stop=_back(self.dialect, payload.get("stop_reason"), "答复"),
                        usage=payload.get("usage", {}), dialect=self.dialect)

    def from_stream(self, lines: list[str]) -> Response:
        """命名事件：`event:` 行给类型，`data:` 行给内容。**记账帧要数出来。**"""
        text, calls, stop, usage = [], {}, None, {}
        #: 「帧」一律数 `data:` 行——**这不是细节**：拿 `event:` 行去数，
        #: 这一家会少一帧（它把 ping 也包成一对 event/data），三家就不可比了。
        frames = sum(1 for ln in lines if ln.startswith("data:"))
        for ln in lines:
            if not ln.startswith("data:"):
                continue
            ev = json.loads(ln[5:].strip())
            kind = ev.get("type")
            if kind == "content_block_start" and ev["content_block"]["type"] == "tool_use":
                cb = ev["content_block"]
                calls[ev["index"]] = {"id": cb["id"], "name": cb["name"], "raw": ""}
            elif kind == "content_block_delta":
                d = ev["delta"]
                if d["type"] == "text_delta":
                    text.append(d["text"])
                elif d["type"] == "input_json_delta":
                    calls[ev["index"]]["raw"] += d["partial_json"]
            elif kind == "message_delta":
                stop = ev.get("delta", {}).get("stop_reason")
                usage = ev.get("usage", {})
            elif kind == "error":
                raise WireError(f"流里出错：{ev.get('error', {}).get('type')}"
                                f"（这一档通常对应 HTTP 529）")
        blocks = tuple(Block("tool_call", call_id=c["id"], name=c["name"],
                             arguments=load_arguments(c["raw"], f"流里的 {c['name']}"))
                       for c in calls.values())
        return Response(text="".join(text), tool_calls=blocks,
                        stop=_back(self.dialect, stop, "流尾"),
                        usage=usage, dialect=self.dialect, events=frames)


# --------------------------------------------------------------- Responses

class ResponsesAdapter:
    """OpenAI Responses：`instructions` ＋ `input` 的 item 列表，工具参数是字符串。"""

    dialect = "responses"
    path = "/v1/responses"

    def headers(self, req: Request) -> dict:
        return {"authorization": "Bearer <从环境变量来>", "content-type": "application/json"}

    def to_wire(self, req: Request) -> dict:
        payload: dict = {"model": req.model, "instructions": req.system,
                         "input": [], "store": False}
        for msg in req.messages:
            for b in msg.blocks:
                if b.kind == "text":
                    payload["input"].append({
                        "role": msg.role,
                        "content": [{"type": "input_text" if msg.role == "user"
                                     else "output_text", "text": b.text}]})
                elif b.kind == "tool_call":
                    payload["input"].append({"type": "function_call", "call_id": b.call_id,
                                             "name": b.name,
                                             "arguments": _dump(b.arguments or {})})
                else:
                    #: 工具结果与消息**平级**——它是一个 item，不是消息里的一个块。
                    payload["input"].append({"type": "function_call_output",
                                             "call_id": b.call_id, "output": b.text})
        if req.tools:
            payload["tools"] = [
                {"type": "function", "name": t.name, "description": t.description,
                 "parameters": t.schema, "strict": t.strict} for t in req.tools]
        if req.max_output_tokens is not None:
            payload["max_output_tokens"] = req.max_output_tokens
        if req.temperature is not None:
            payload["temperature"] = req.temperature
        if req.stream:
            payload["stream"] = True
        return payload

    def from_wire(self, payload: dict) -> Response:
        text, calls = [], []
        for item in payload.get("output", []):
            if item.get("type") == "message":
                text.extend(c.get("text", "") for c in item.get("content", [])
                            if c.get("type") == "output_text")
            elif item.get("type") == "function_call":
                calls.append(Block("tool_call", call_id=item.get("call_id", ""),
                                   name=item.get("name", ""),
                                   arguments=load_arguments(item.get("arguments", ""),
                                                            f"item {item.get('name')}")))
        status = payload.get("status")
        reason = (payload.get("incomplete_details") or {}).get("reason")
        key = f"{status}/{reason}" if reason else status
        return Response(text="".join(text), tool_calls=tuple(calls),
                        stop=_back(self.dialect, key, "答复"),
                        usage=payload.get("usage", {}), dialect=self.dialect)

    def from_stream(self, lines: list[str]) -> Response:
        """同一段答复在这里是**类型化的 item 事件**，而且没有 `event:` 行。"""
        text, calls, stop, usage, events = [], {}, None, {}, 0
        for ln in lines:
            if not ln.startswith("data:"):
                continue
            ev = json.loads(ln[5:].strip())
            events += 1
            kind = ev.get("type", "")
            if kind == "response.output_text.delta":
                text.append(ev.get("delta", ""))
            elif kind == "response.output_item.added" and ev["item"]["type"] == "function_call":
                calls[ev["item"]["call_id"]] = {"id": ev["item"]["call_id"],
                                                "name": ev["item"]["name"], "raw": ""}
            elif kind == "response.function_call_arguments.delta":
                calls[ev["call_id"]]["raw"] += ev.get("delta", "")
            elif kind == "response.completed":
                resp = ev.get("response", {})
                usage = resp.get("usage", {})
                reason = (resp.get("incomplete_details") or {}).get("reason")
                stop = f"{resp.get('status')}/{reason}" if reason else resp.get("status")
        #: 停止原因在这一家**读不出「要调工具」**（`completed` 同时表示两种结束），
        #: 所以下面这一行不许把工具调用掺进去——它只翻停止原因，差的那一格留给读数报。
        blocks = tuple(Block("tool_call", call_id=c["id"], name=c["name"],
                             arguments=load_arguments(c["raw"], f"流里的 {c['name']}"))
                       for c in calls.values())
        return Response(text="".join(text), tool_calls=blocks,
                        stop=_back(self.dialect, stop, "流尾"),
                        usage=usage, dialect=self.dialect, events=events)


# --------------------------------------------------------------- Chat 兼容层

class ChatAdapter:
    """兼容层：`messages[0]` 是系统消息，工具结果是一个 `role=tool` 的消息。"""

    dialect = "chat"
    path = "/v1/chat/completions"

    def headers(self, req: Request) -> dict:
        return {"authorization": "Bearer <从环境变量来>", "content-type": "application/json"}

    def to_wire(self, req: Request) -> dict:
        payload: dict = {"model": req.model,
                         "messages": [{"role": "system", "content": req.system}]}
        for msg in req.messages:
            texts = [b.text for b in msg.blocks if b.kind == "text"]
            calls = [b for b in msg.blocks if b.kind == "tool_call"]
            results = [b for b in msg.blocks if b.kind == "tool_result"]
            if calls:
                payload["messages"].append({
                    "role": "assistant", "content": "".join(texts) or None,
                    "tool_calls": [{"id": b.call_id, "type": "function",
                                    "function": {"name": b.name,
                                                 "arguments": _dump(b.arguments or {})}}
                                   for b in calls]})
            if texts and not calls:
                payload["messages"].append({"role": msg.role, "content": "".join(texts)})
            for b in results:
                #: **结果是一条独立的消息**（角色 `tool`），而另外两家把它塞进消息里。
                payload["messages"].append({"role": "tool", "tool_call_id": b.call_id,
                                            "content": b.text})
        if req.tools:
            payload["tools"] = [
                {"type": "function",
                 "function": {"name": t.name, "description": t.description,
                              "parameters": t.schema, "strict": t.strict}}
                for t in req.tools]
        if req.max_output_tokens is not None:
            payload["max_completion_tokens"] = req.max_output_tokens
        if req.temperature is not None:
            payload["temperature"] = req.temperature
        if req.stream:
            payload["stream"] = True
        return payload

    def from_wire(self, payload: dict) -> Response:
        choice = payload["choices"][0]
        msg = choice.get("message", {})
        calls = tuple(Block("tool_call", call_id=c["id"],
                            name=c["function"]["name"],
                            arguments=load_arguments(c["function"]["arguments"],
                                                     f"调用 {c['function']['name']}"))
                      for c in (msg.get("tool_calls") or []))
        return Response(text=msg.get("content") or "", tool_calls=calls,
                        stop=_back(self.dialect, choice.get("finish_reason"), "答复"),
                        usage=payload.get("usage", {}), dialect=self.dialect)

    def from_stream(self, lines: list[str]) -> Response:
        """只有 `data:` 行，最后以一个哨兵值结尾（它**不是 JSON**）。"""
        text, calls, stop, usage, events = [], {}, None, {}, 0
        for ln in lines:
            if not ln.startswith("data:"):
                continue
            raw = ln[5:].strip()
            if raw.startswith("["):        # 哨兵值：[DONE]
                events += 1
                continue
            chunk = json.loads(raw)
            events += 1
            if chunk.get("usage"):
                usage = chunk["usage"]
            for choice in chunk.get("choices", []):
                delta = choice.get("delta", {})
                text.append(delta.get("content") or "")
                for c in (delta.get("tool_calls") or []):
                    slot = calls.setdefault(c["index"], {"id": c.get("id", ""),
                                                         "name": "", "raw": ""})
                    slot["id"] = c.get("id") or slot["id"]
                    slot["name"] = c["function"].get("name") or slot["name"]
                    slot["raw"] += c["function"].get("arguments") or ""
                if choice.get("finish_reason"):
                    stop = choice["finish_reason"]
        blocks = tuple(Block("tool_call", call_id=c["id"], name=c["name"],
                             arguments=load_arguments(c["raw"], f"流里的 {c['name']}"))
                       for c in calls.values())
        return Response(text="".join(text), tool_calls=blocks,
                        stop=_back(self.dialect, stop, "流尾"),
                        usage=usage, dialect=self.dialect, events=events)


ADAPTERS: dict[str, object] = {"messages": MessagesAdapter(),
                               "responses": ResponsesAdapter(),
                               "chat": ChatAdapter()}


# --------------------------------------------------------------- 谁能走哪条路

# --------------------------------------------------------------- 夹具流
#
# 三段流是**同一件事的三种帧形**：一段文本 ＋ 一次工具调用。它们不是从网上抄的，
# 而是照官方文档里那几段示例的形状写的（Messages 的命名事件、兼容层的
# `data:` 分片与哨兵值、Responses 的类型化事件）。

def messages_stream() -> list[str]:
    """Messages：**命名事件**（`event:` 行）＋ `data:` 行，中间还会夹 ping。"""
    return [
        "event: message_start",
        'data: {"type":"message_start","message":{"id":"msg_1","role":"assistant",'
        '"content":[],"usage":{"input_tokens":18,"output_tokens":1}}}',
        "event: content_block_start",
        'data: {"type":"content_block_start","index":0,'
        '"content_block":{"type":"text","text":""}}',
        "event: ping",
        'data: {"type":"ping"}',
        "event: content_block_delta",
        'data: {"type":"content_block_delta","index":0,'
        '"delta":{"type":"text_delta","text":"知舟"}}',
        "event: content_block_delta",
        'data: {"type":"content_block_delta","index":0,'
        '"delta":{"type":"text_delta","text":"：先查一下"}}',
        "event: content_block_stop",
        'data: {"type":"content_block_stop","index":0}',
        "event: content_block_start",
        'data: {"type":"content_block_start","index":1,'
        '"content_block":{"type":"tool_use","id":"toolu_1","name":"search","input":{}}}',
        "event: content_block_delta",
        'data: {"type":"content_block_delta","index":1,'
        '"delta":{"type":"input_json_delta","partial_json":"{\\"q\\": \\"北京\\""}}',
        "event: content_block_delta",
        'data: {"type":"content_block_delta","index":1,'
        '"delta":{"type":"input_json_delta","partial_json":", \\"top_k\\": 3}"}}',
        "event: content_block_stop",
        'data: {"type":"content_block_stop","index":1}',
        "event: message_delta",
        'data: {"type":"message_delta","delta":{"stop_reason":"tool_use"},'
        '"usage":{"output_tokens":57}}',
        "event: message_stop",
        'data: {"type":"message_stop"}',
    ]


def responses_stream() -> list[str]:
    """Responses：**没有 `event:` 行**，类型写在 `data:` 里的 `type` 字段上。

    注意末尾那一帧：`status` 是 `completed`——**它不知道自己是「答完了」
    还是「要调工具」**，后者由 output 里多不多一个 `function_call` item 决定。
    """
    return [
        'data: {"type":"response.created","response":{"id":"resp_1",'
        '"status":"in_progress"}}',
        'data: {"type":"response.output_item.added","item":{"type":"message",'
        '"id":"msg_1","role":"assistant","content":[]}}',
        'data: {"type":"response.output_text.delta","item_id":"msg_1","delta":"知舟"}',
        'data: {"type":"response.output_text.delta","item_id":"msg_1","delta":"：先查一下"}',
        'data: {"type":"response.output_item.done","item":{"type":"message","id":"msg_1"}}',
        'data: {"type":"response.output_item.added","item":{"type":"function_call",'
        '"call_id":"fc_1","name":"search","arguments":""}}',
        'data: {"type":"response.function_call_arguments.delta","call_id":"fc_1",'
        '"delta":"{\\"q\\": \\"北京\\""}',
        'data: {"type":"response.function_call_arguments.delta","call_id":"fc_1",'
        '"delta":", \\"top_k\\": 3}"}',
        'data: {"type":"response.completed","response":{"status":"completed",'
        '"usage":{"input_tokens":18,"output_tokens":57}}}',
    ]


def chat_stream() -> list[str]:
    """兼容层：**只有 `data:` 行**，最后以一个**不是 JSON** 的哨兵值结尾。"""
    return [
        'data: {"id":"c1","object":"chat.completion.chunk","choices":[{"index":0,'
        '"delta":{"role":"assistant","content":"知舟"}}]}',
        'data: {"id":"c1","object":"chat.completion.chunk","choices":[{"index":0,'
        '"delta":{"content":"：先查一下"}}]}',
        'data: {"id":"c1","object":"chat.completion.chunk","choices":[{"index":0,'
        '"delta":{"tool_calls":[{"index":0,"id":"call_1","type":"function",'
        '"function":{"name":"search","arguments":"{\\"q\\": \\"北京\\""}}]}}]}',
        'data: {"id":"c1","object":"chat.completion.chunk","choices":[{"index":0,'
        '"delta":{"tool_calls":[{"index":0,'
        '"function":{"arguments":", \\"top_k\\": 3}"}}]}}]}',
        'data: {"id":"c1","object":"chat.completion.chunk","choices":[{"index":0,'
        '"delta":{},"finish_reason":"tool_calls"}]}',
        'data: {"id":"c1","object":"chat.completion.chunk","choices":[],'
        '"usage":{"prompt_tokens":18,"completion_tokens":57,"total_tokens":75}}',
        "data: [DONE]",
    ]


def tool_dialects(model: str) -> tuple[str, ...]:
    """**这张模型表上的某个名字，用哪几种方言真的能调到工具。**

    这里的三条不是「我们的偏好」，是官方写下来的约束（见 `WIRE_SOURCES`）：

    - 另一家的四个模型不在兼容层的图纸上（兼容层是**一家的**形状）；
    - 其中最大的那一个**工具调用只走 Responses**（兼容层的示例都换成了小一号的模型）；
    - 其余三个在兼容层上可以调工具，但**前提是关掉推理**。

    这三条与 6.1 的登记表**共用同一份模型清单**：那里换了模型，这里会跟着变——
    这正是「一张表、两处用」的意思。
    """
    spec = {m.name: m for m in MODELS}.get(model)
    if spec is None:
        raise WireError(f"{model!r} 不在 6.1 的登记表里")
    if spec.vendor == "Anthropic":
        return ("messages",)
    if model == "gpt-6-astra":
        return ("responses",)
    return ("responses", "chat")


def tool_constraint(model: str, dialect: str) -> str:
    """这一格里有没有前提条件。**空白也是一种答复**（没有前提）。"""
    spec = {m.name: m for m in MODELS}[model]
    if dialect not in tool_dialects(model):
        return "这一家在兼容层的图纸上没有这个形状"
    if spec.vendor == "OpenAI" and dialect == "chat":
        return "只在这家叫「不开推理」的那一档下支持工具调用"
    return ""


def dialect_summary(dialect: str) -> dict:
    """给读数的**扁平描述**：一份载荷里有多少个 key 路径。"""
    req = Request(model="示例", system="你是知舟。",
                  messages=(Message("user", (Block("text", text="你好"),)),),
                  tools=(Tool("search", "查资料", {"type": "object",
                                                   "properties": {"q": {"type": "string"}}}),),
                  max_output_tokens=1_024, dialect=dialect)
    payload = ADAPTERS[dialect].to_wire(req)
    return {"dialect": dialect, "keys": len(_paths(payload)),
            "bytes": len(_dump(payload).encode("utf-8")),
            "as_of": WIRE_AS_OF}


def _paths(obj, prefix: str = "") -> list[str]:
    """把一份载荷摊成 key 路径（叶子才计数）。读数的分母就是这个数。"""
    if isinstance(obj, dict):
        out: list[str] = []
        for k, v in obj.items():
            out.extend(_paths(v, f"{prefix}.{k}" if prefix else k))
        return out
    if isinstance(obj, list):
        out = []
        for v in obj:
            out.extend(_paths(v, f"{prefix}[]"))
        return out
    return [prefix]
