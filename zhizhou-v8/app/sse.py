"""SSE 服务端：**它是文本协议，而它最容易坏在协议之外。**

这一块量的是 8.3 第一个反直觉的事实：**流式在本地像流水，在线上一吐一大片**——
而两边的代码一行没差。差别在三处部署件：响应头、中间代理的缓冲、以及心跳与超时。
这三处没有一处会报错：它们只让「逐块到达」变成「一次性到达」，而**结果看起来仍然是对的**。

三条官方事实撑起这一块（出处见 `REFERENCES.md` 第 8 篇）：

1. **帧的四个字段**：`event` / `data` / `id` / `retry`。一个事件由**空行结束**，
   多行 `data:` 用换行拼成同一个值；以 `:` 开头的行是**注释**——它不产生事件，
   而它正是心跳的标准写法（官方说明里就是这么写的）。
2. **重连是浏览器自己做的**，而它带什么由服务端决定：上一次收到的 `id` 会以
   `Last-Event-ID` 头回传，`retry:` 决定它隔多久重试。**于是「断线续传」不是客户端功能，
   是「服务端有没有给 id、有没有把已经发过的东西留着」**——没有 id 的重连，
   浏览器会当成一次全新订阅。
3. **`Content-Type: text/event-stream` 之外，还有三个头要显式关掉缓冲**：
   `Cache-Control: no-cache`（别缓存这次响应）、`X-Accel-Buffering: no`（告诉 Nginx
   这一条别缓冲）、`Connection: keep-alive`。中间代理默认**按自己的缓冲策略**成块转发，
   这是「本地像流、线上不像」的第一号原因。

这一块与 8.3.5／8.3.6 的分界：**它管线上那一段（服务端到浏览器之间）**，
`stream_ui` 管浏览器里那一段（状态机与部分片段），而 AI SDK 那一张对照表
说明框架把哪些账替你收了、哪些仍然要你自己报。
"""

from __future__ import annotations

from dataclasses import dataclass, field

#: 帧的四个字段。`data` 是唯一必填的那个——所以「一个事件」的最小形态是 `data: …`。
EVENT_FIELDS = ("event", "data", "id", "retry")

#: 三个要显式写的头（＋ 那个必须对的 Content-Type）。
HEADERS: tuple[tuple[str, str, str], ...] = (
    ("Content-Type", "text/event-stream",
     "协议本体。**这一条写错，浏览器就不会把它当成流**"),
    ("Cache-Control", "no-cache",
     "这次响应是「一次性的」——它不能被任何一层缓存住再重放"),
    ("X-Accel-Buffering", "no",
     "**给 Nginx 看的那一条**：这一行不写，Nginx 默认可缓冲，"
     "整段响应会被攒成一整块再发出去"),
    ("Connection", "keep-alive",
     "长连接。关掉它，代理与负载均衡会按「一次请求一个响应」处理"),
)


@dataclass(frozen=True)
class Event:
    """一个事件。`data` 里的换行会被拆成多行 `data:`——**这是协议允许的，也是它的原样**。"""

    data: str
    name: str | None = None
    id: str | None = None
    retry: int | None = None


def frame(ev: Event) -> str:
    """把一个事件写成帧：逐字段一行、`data` 的换行逐行写、最后空行结束。"""
    out = []
    if ev.name is not None:
        out.append(f"event: {ev.name}")
    if ev.id is not None:
        out.append(f"id: {ev.id}")
    if ev.retry is not None:
        out.append(f"retry: {ev.retry}")
    for line in ev.data.split("\n"):
        out.append(f"data: {line}")
    return "\n".join(out) + "\n\n"


def parse(stream: str) -> tuple[list[Event], int]:
    """把一段 SSE 文本还原成事件。返回（事件, 跳过的注释行数）。

    三处判据都来自官方那一节的原文：**空行是一个事件的结束**、
    **多行 `data:` 用换行拼起来**、**`:` 开头的行是注释**。
    第三点是这一块最实用的一条：**心跳不需要是一个合法事件**——
    它只需要是一行「不是空行、也不构成事件」的东西。
    """
    events: list[Event] = []
    comments = 0
    cur: dict[str, object] = {}
    for raw in stream.split("\n"):
        if raw.startswith(":"):
            comments += 1
            continue
        if raw == "":
            if "data" in cur:
                events.append(Event(data=str(cur["data"]), name=cur.get("name"),  # type: ignore[arg-type]
                                    id=cur.get("id"), retry=cur.get("retry")))  # type: ignore[arg-type]
            cur = {}
            continue
        if ":" not in raw:
            continue
        k, _, v = raw.partition(":")
        v = v[1:] if v.startswith(" ") else v
        if k == "data":
            cur["data"] = str(cur.get("data", "")) + ("\n" if "data" in cur else "") + v
        elif k == "event":
            cur["name"] = v
        elif k == "id":
            cur["id"] = v
        elif k == "retry":
            cur["retry"] = int(v)
    return events, comments


@dataclass(frozen=True)
class Heartbeat:
    """心跳与代理超时的账：**谁先到，谁就赢。**"""

    gap_s: int
    idle_timeout_s: int

    @property
    def survives(self) -> bool:
        return 0 < self.gap_s < self.idle_timeout_s

    @property
    def seen(self) -> str:
        if self.gap_s == 0:
            return "没有心跳——连接在第 60 秒被代理掐断"
        if self.gap_s >= self.idle_timeout_s:
            return f"心跳 {self.gap_s}s 太稀——超时先到，连接在第 {self.idle_timeout_s} 秒断"
        return f"心跳 {self.gap_s}s 先到，连接活着"


#: 代理的空闲超时。**Nginx 的 `proxy_read_timeout` 默认就是 60 秒**——
#: 而它的判据是「多久没有**任何**字节流过」，所以心跳是一条**占位**用的字节。
IDLE_TIMEOUT_S = 60

HEARTBEATS: tuple[Heartbeat, ...] = tuple(
    Heartbeat(gap, IDLE_TIMEOUT_S) for gap in (0, 15, 30, 60, 120)
)


def heartbeat_table() -> list[dict]:
    out = []
    for hb in HEARTBEATS:
        if hb.gap_s == 0:
            frames = 0
        else:
            frames = 300 // hb.gap_s
        out.append({
            "gap": "不写" if hb.gap_s == 0 else f"{hb.gap_s}s",
            "frames_5min": frames,
            "survives": hb.survives,
            "seen": hb.seen,
        })
    return out


@dataclass(frozen=True)
class Deployment:
    """一种部署件组合，以及它在浏览器里**看起来**是什么样。"""

    name: str
    headers: tuple[str, ...]
    proxy_buffering: str
    streamy: bool
    why: str


#: 四种部署。**代码一行没差**，差别只在头与代理。
DEPLOYMENTS: tuple[Deployment, ...] = (
    Deployment("直连 ASGI（开发机）", ("Content-Type",), "不经过", True,
               "没有中间件可缓冲，所以**本地永远是像流的**"),
    Deployment("Nginx ＋ 默认缓冲", ("Content-Type",), "on（默认）", False,
               "官方默认就是缓冲：整段响应攒完再发——**首字延迟等于总时长**"),
    Deployment("Nginx ＋ `X-Accel-Buffering: no`", ("Content-Type", "X-Accel-Buffering"), "on", True,
               "这一行就是给 Nginx 的**逐条放行指令**——不动全局配置也能让这一条不缓冲"),
    Deployment("Nginx ＋ 关掉 buffering", ("Content-Type",), "off", True,
               "同样有效，代价是**整个 server 的每一条响应**都逐块转发"),
)


def buffer_table() -> list[dict]:
    return [{
        "deployment": d.name,
        "headers": "、".join(d.headers),
        "buffering": d.proxy_buffering,
        "looks": "像流" if d.streamy else "**一吐一大片**",
        "why": d.why,
    } for d in DEPLOYMENTS]


@dataclass
class Journal:
    """服务端为「重连续传」留的那点东西：**最近 N 条事件的环形缓冲。**

    `keep` 是一个**产品决定**，不是实现细节：它决定「断线多久之内的重连能接着长」。
    `first_index` 是手上最老那一条的序号（`id` 就从 1 开始编），
    它让「已经被挤掉」这件事可以说清楚，而不只是「补发不了」。
    """

    keep: int
    ids: list[str] = field(default_factory=list)
    data: list[str] = field(default_factory=list)
    first_index: int = 1
    sent: int = 0

    def add(self, ev: Event) -> None:
        self.sent += 1
        self.ids.append(ev.id or "")
        self.data.append(ev.data)
        if len(self.ids) > self.keep:
            self.ids.pop(0)
            self.data.pop(0)
            self.first_index += 1

    def resume(self, last_event_id: str | None) -> dict:
        """重连时该补发什么。**这是「重连」与「重放」的分水岭。**

        三种情况必须分开报：
          · 带了 id 且在缓冲里 → 补发它之后的每一条；
          · 带了 id 但**已经被挤掉** → 只能从手上最老的那一条开始补，
            中间那一段永久丢了（**条数在这里就是不可知的**——只能报「从第几条开始补」）；
          · 没带 id（服务端从没给过）→ 浏览器把它当成**一次全新订阅**：
            一条也补不了，而**用户看到的回答会从头再来一遍**。
        """
        if not last_event_id:
            return {"replayed": [], "count": 0, "evicted": False, "lost": self.sent,
                    "seen": "客户端没带 id：浏览器当成一次全新订阅——**回答从头再来一遍**"}
        if last_event_id in self.ids:
            i = self.ids.index(last_event_id)
            tail = list(self.data[i + 1:])
            return {"replayed": tail, "count": len(tail), "evicted": False, "lost": 0,
                    "seen": f"从第 {last_event_id} 条之后接着长（补发 {len(tail)} 条）"}
        return {"replayed": list(self.data), "count": len(self.data), "evicted": True,
                "lost": None,
                "seen": f"客户端的 id 已在缓冲之外：**中间那一段永久丢了**，"
                        f"只能从手上最老的第 {self.first_index} 条开始补"}


@dataclass(frozen=True)
class Consumer:
    """一个消费者，以及它的队列上限。**没有上限的那一档是内存事故。**"""

    name: str
    per_sec: int
    queue_max: int | None


@dataclass(frozen=True)
class Backpressure:
    """一次 30 秒的生成，遇上一个慢消费者。"""

    consumer: Consumer
    produced: int
    consumed: int
    peak_queue: int
    outcome: str
    why: str


#: 服务端每秒产 20 条（常见的小模型流），30 秒共 600 条。
PRODUCED_PER_SEC = 20


def backpressure(consumer: Consumer, seconds: int = 30) -> Backpressure:
    """把「生产者恒定、消费者偏慢」这件事算成一笔账。

    上限为空 ⇒ 队列一直涨到生成结束（**没有任何一处报错，只在内存曲线上看得出来**）；
    上限为 0 ⇒ 一条都存不下，慢消费者**立刻被断开**（官方那套实现里就是立刻结束这个响应）。
    """
    produced = PRODUCED_PER_SEC * seconds
    consumed = min(produced, consumer.per_sec * seconds)
    if consumer.queue_max is None:
        peak = produced - consumed
        return Backpressure(consumer, produced, consumed, peak,
                            "**队列一直涨到结束**",
                            "没有上限＝把「发不出去」变成「先存着」，"
                            "而内存事故的报告里不会出现「流式」这个词")
    if consumer.queue_max == 0:
        return Backpressure(consumer, produced, consumed, 0, "**慢消费者立刻被断开**",
                            "存不下就直接结束——用户看到的是「回答突然没了」，"
                            "而服务端日志里只有一条正常的断开")
    peak = min(consumer.queue_max, max(0, produced - consumed))
    if peak == 0:
        return Backpressure(consumer, produced, consumed, 0, "跟得上，队列几乎为空",
                            "消费者比生产者快（或一样快）——这是唯一一个不需要做决定的档")
    if peak < consumer.queue_max:
        return Backpressure(consumer, produced, consumed, peak,
                            f"队列涨到 {peak}，没顶到上限（{consumer.queue_max}）",
                            "消费者慢，而这一段的量还不够把上限顶满")
    return Backpressure(consumer, produced, consumed, peak,
                        f"队列顶到上限（{consumer.queue_max}）",
                        "**上限把「内存事故」换成了「有界的延迟」**——"
                        "代价是超出上限的那些要么丢、要么让生产者等一下")


SLOW_CONSUMERS: tuple[Consumer, ...] = (
    Consumer("正常浏览器（跟得上）", 20, 32),
    Consumer("弱网手机（每秒 5 条）", 5, 32),
    Consumer("后台标签页（每秒 1 条）", 1, 32),
    Consumer("**完全没有消费者**（连接挂着但没人读）", 0, 32),
    Consumer("弱网手机 ＋ 无上限队列", 5, None),
    Consumer("弱网手机 ＋ 零缓冲", 5, 0),
)


def slow_consumer_table() -> list[dict]:
    return [{
        "consumer": p.consumer.name,
        "per_sec": p.consumer.per_sec,
        "queue_max": "无上限" if p.consumer.queue_max is None else p.consumer.queue_max,
        "produced": p.produced,
        "consumed": p.consumed,
        "peak_queue": p.peak_queue,
        "outcome": p.outcome,
        "why": p.why,
    } for p in (backpressure(c) for c in SLOW_CONSUMERS)]


#: 「纯 SSE」与「AI SDK 数据流协议」的分工。**框架把哪些账收了、哪些仍要自己报**，
#: 这一张表回答的就是这个（8.3.6 的落点）。
PROTOCOL_ROWS: tuple[tuple[str, str, str], ...] = (
    ("传输格式", "`text/event-stream`，四字段（`event`/`data`/`id`/`retry`）",
     "**也是 SSE**，但 `data` 里塞的是 JSON 事件（`text-delta` / `finish` / `tool-call`…）"),
    ("谁解析", "浏览器 `EventSource`（或你手写的 `fetch` ＋ reader）",
     "框架的 `useChat`／`streamText` 替你解析，并维护消息列表"),
    ("断线重连", "**浏览器自动重连**，带 `Last-Event-ID`；服务端决定补发什么",
     "框架**不自动重连**（它是一层薄适配）：要重连得自己发一次新请求"),
    ("取消", "关掉连接（`EventSource.close()` 或 `AbortController.abort()`）",
     "`stop()`／`abort()`——它做的是同一件事，但它还会把状态复位"),
    ("部分片段", "每帧是**增量**还是**全量**由服务端定，客户端要自己选一种",
     "约定为**增量**（`text-delta` 累加）——于是「重试」必须由你去重"),
    ("工具调用与多模态", "协议不认这些，全塞进 `data` 里自定义",
     "有事件类型（`tool-call` / `tool-result` / `reasoning`）——**这是它真正值钱的地方**"),
)


def protocol_table() -> list[dict]:
    return [{"topic": t, "raw_sse": a, "ai_sdk": b} for t, a, b in PROTOCOL_ROWS]


#: 一次 12 段的回答（知舟那种 60–80 字的短答案），每段一个字符块。
#: **它是这一章所有帧级读数的原料**：帧、还原、心跳、补发都从它出发。
ANSWER_CHUNKS: tuple[str, ...] = (
    "知舟", "是一", "个把", "文档", "变成", "可问", "的系", "统：", "它先", "切分",
    "、再", "检索",
)


def chat_stream() -> list[Event]:
    """把一次回答变成带 id 的事件流——**id 是「第几段」，不是「第几秒」**。"""
    return [Event(data=c, name="delta", id=str(i + 1))
            for i, c in enumerate(ANSWER_CHUNKS)]
