"""客户端状态机：**「在流式」不是一个状态，它是六个状态里最容易卡住的那一个。**

这一块量的是浏览器这一侧（8.3.5）：一帧一帧到达时，界面要维护什么，
以及**为什么三种最常见的故障都表现为「转圈转到天荒地老」**：

1. **服务端断了，但没有发结束事件**——连接关了而 `done` 没来。客户端的 `streaming`
   会一直等下去（它等的不是连接，是一个事件）；现场是「回答停在半句，转圈还在转」。
2. **`abort` 之后没有复位**——用户点了停止，请求真的停了，而界面的状态没人改回去；
   下一次提交于是带着一个还在 `streaming` 的旧状态进去。
3. **错误之后没清掉 partial**——把半截回答留在输入框旁边，用户以为它是完整的；
   重试之后新旧两段并排出现。

三条都指向同一条纪律：**状态的转移要由「事件」驱动，而「没有事件」本身不是一个事件**
——所以必须有超时或连接关闭这条边。这一块与 `sse` 的分界同样是清楚的：
`sse` 管线上那一段（帧、头、心跳、续传），这里管**浏览器里那一段**（状态与片段）。
"""

from __future__ import annotations

from dataclasses import dataclass, field

#: 六个状态。前三个是过渡，后三个是终态——**而 `streaming` 是唯一可能永远停在那里的那个。**
STATES = ("idle", "submitting", "streaming", "done", "error", "aborted")
TERMINALS = ("done", "error", "aborted")

#: 客户端真正会看到的事件。注意 `closed` 与 `timeout` **不是服务端发的**，
#: 它们是客户端自己造的边——**少了这两条边，故障 1／2／3 就没有任何出口**。
CLIENT_EVENTS = ("submit", "start", "delta", "done", "error", "abort", "closed", "timeout")


@dataclass(frozen=True)
class Move:
    src: str
    event: str
    dst: str
    note: str


#: 允许的转移。**不在表里的转移就是 bug**（而不是「先这样、以后再补」）。
MOVES: tuple[Move, ...] = (
    Move("idle", "submit", "submitting", "发出请求，等第一个字节"),
    Move("submitting", "start", "streaming", "**第一个字节到**——用户的等待从这里结束"),
    Move("submitting", "error", "error", "首字节之前就失败了（401／429／500）"),
    Move("submitting", "timeout", "error", "**等首字节超时**：流还没开，连接也不一定有错"),
    Move("submitting", "closed", "error", "连接在首字节之前关了"),
    Move("streaming", "delta", "streaming", "累积片段（**自环**，所以它不改变状态——这正是它危险的地方）"),
    Move("streaming", "done", "done", "只有这个事件能让它停在「完成」"),
    Move("streaming", "error", "error", "生成中途失败（服务端发的事件）"),
    Move("streaming", "abort", "aborted", "用户点了停止"),
    Move("streaming", "closed", "aborted", "**连接关了而没有 `done`**：这是故障 1 的唯一出口"),
    Move("streaming", "timeout", "error", "几十秒没有新帧：**心跳没到，就当成断了**"),
    Move("error", "submit", "submitting", "重试（**先把 partial 清掉，否则它会和新回答并排显示**）"),
    Move("aborted", "submit", "submitting", "重来一次"),
    Move("done", "submit", "submitting", "下一轮对话"),
)


def moves_from(state: str) -> tuple[Move, ...]:
    return tuple(m for m in MOVES if m.src == state)


def step(state: str, event: str) -> tuple[str, str]:
    """走一步。返回（新状态, 说明）——**不在表里 ⇒ 留在原状态并说清为什么**。"""
    for m in MOVES:
        if m.src == state and m.event == event:
            return m.dst, m.note
    return state, f"{state} 收到 {event} 没有出路：**留在原状态**（表里没有这条转移）"


@dataclass(frozen=True)
class StuckCase:
    """一种「卡在流式／显示错」的现场。**它们看起来一样，而机制各不相同。**"""

    name: str
    events: tuple[str, ...]
    watch: str        # state（卡住了）／ shown（显示错了）／ none（应当正常）
    clear: bool       # 重试前清不清 partial
    why: str


#: 五种现场。①②是**同一件事的两种写法**（有没有那条边），
#: ③⑤是「状态机对了、显示却错了」——只报状态的那类检查抓不到它们。
STUCK_CASES: tuple[StuckCase, ...] = (
    StuckCase("服务端断了、`done` 没来",
              ("submit", "start", "delta", "delta", "delta"),
              "state", True,
              "连接已经关了，而客户端等的是一个**事件**——没有 `closed`／`timeout` 那条边，"
              "它就永远停在 streaming"),
    StuckCase("同一条断线，但把 `closed` 喂进来",
              ("submit", "start", "delta", "delta", "delta", "closed"),
              "none", True,
              "**同一件事，差别只在有没有那条边**——补上它，界面立刻落地（落在 aborted）"),
    StuckCase("`abort` 之后又来了一帧",
              ("submit", "start", "delta", "abort", "delta"),
              "shown", True,
              "状态机是对的（aborted），而**界面多显示了那一帧**——要靠 `mismatch` 才看得见"),
    StuckCase("错误之后清了 partial 再重试",
              ("submit", "start", "delta", "delta", "error", "submit", "start", "delta"),
              "none", True,
              "状态对、显示也对（新一轮从头累积）——**这是应当正常的那一档**"),
    StuckCase("同一次重试，但 partial 没清",
              ("submit", "start", "delta", "delta", "error", "submit", "start", "delta"),
              "shown", False,
              "状态同样是对的，而**新旧两段并排显示**——上一轮的半截留在了框里"),
)


def replay(events: tuple[str, ...], *, clear_on_retry: bool = True) -> dict:
    """把一串事件走一遍。返回终态、累积文本、以及**它是否停在了不该停的地方**。

    这里同时报三个数，而它们各自对着一种故障：
      · `state`（状态机的终态）——对着「卡在 streaming」；
      · `shown`（界面上真正显示的东西）——**与 `text` 的差就是「状态机对了、显示却错了」**，
        这一类只报状态是看不见的（本节的第三条与第四条都落在它上面）；
      · `terminal`（是不是落在终态）——它是 `done`／`error`／`aborted` 三个的并集。
    """
    state, text, shown = "idle", "", ""
    for ev in events:
        if ev == "delta" and state in ("error", "aborted"):
            # 终态收到迟到的帧：状态机按表走（error／aborted 没有 delta 的出路），
            # 而**片段的追加是另一段代码**——它照旧把这一帧写到了界面上。
            shown += "·"
            continue
        if ev == "submit" and state in ("error", "aborted", "done"):
            if clear_on_retry:
                text, shown = "", ""
        state, _ = step(state, ev)
        if ev == "start":
            # **本轮**的累积从这里重新开始；而「界面上显示什么」是另一件事：
            # 上一轮的 partial 清没清，决定了 `shown` 是重新开始还是接着往后面长。
            text = ""
            if clear_on_retry:
                shown = ""
        if ev == "delta":
            text += "·"
            shown += "·"
        if ev in ("done", "abort", "closed", "timeout", "error"):
            shown = text
    return {
        "state": state,
        "text": text,
        "shown": shown,
        "stuck": state == "streaming",
        "terminal": state in TERMINALS,
        "mismatch": shown != text,
    }


def stuck_table() -> list[dict]:
    """五种现场各走一遍，把「状态对不对」与「显示对不对」**分开报**。

    `mismatch` 是这一节唯一一处必须新加的读数：只报 `state` 的话，
    ③ 与 ⑤ 两种现场会显示成「一切正常」。
    """
    out = []
    for case in STUCK_CASES:
        r = replay(case.events, clear_on_retry=case.clear)
        out.append({
            "case": case.name,
            "state": r["state"],
            "terminal": r["terminal"],
            "stuck": r["stuck"],
            "mismatch": r["mismatch"],
            "text": r["text"],
            "shown": r["shown"],
            "watch": case.watch,
            "why": case.why,
        })
    return out


@dataclass(frozen=True)
class AbortLevel:
    """取消的三层。**它们各自保证什么，是这一节最容易被混为一谈的一栏。**"""

    name: str
    who: str
    stops_what: str
    guaranteed: str
    cost: str


ABORT_LEVELS: tuple[AbortLevel, ...] = (
    AbortLevel("客户端 `abort()`", "浏览器",
               "**停止接收**（连接被关掉）",
               "用户的界面立刻停了；**服务端不一定知道**（它下一次写才会发现）",
               "服务端可能已经把剩下的 token 生成完，**算力照付**"),
    AbortLevel("服务端停止生成", "服务端",
               "**停止产生**（模型调用被取消）",
               "后端不再计费；而**连接还在**（客户端要自己收尾）",
               "客户端要能处理「流再也没有下一帧」这种情况"),
    AbortLevel("连接关闭（两边都断）", "任一侧",
               "**两边都停**",
               "没有第三件事需要收尾",
               "**它是结果，不是操作**：只有两侧都实现了取消才有这个效果"),
)


def abort_table() -> list[dict]:
    return [{
        "level": a.name,
        "who": a.who,
        "stops": a.stops_what,
        "guaranteed": a.guaranteed,
        "cost": a.cost,
    } for a in ABORT_LEVELS]


@dataclass(frozen=True)
class Retry:
    """三种「再试一次」。它们看起来都是重试，**而用户看到的东西完全不同**。"""

    name: str
    repeats: int
    loses: int
    seen: str
    why: str


RETRIES: tuple[Retry, ...] = (
    Retry("重发整个请求", 0, 0, "**回答从头再来一遍**",
          "最简单、也最浪费：已经生成过的 token 全部重算，而用户看到两段一样的开头"),
    Retry("带 `Last-Event-ID` 续传", 0, 0, "从断点接着长",
          "服务端要留缓冲、客户端要留着 id——**这是唯一能「接着长」的做法**"),
    Retry("客户端保留 partial ＋ 重发", 3, 0, "**断点那句被说了两遍**",
          "把半截回答塞回新一轮的输入：**没有 id 的续传，靠上下文拼出来，重复就发生在这里**"),
)


def retry_table() -> list[dict]:
    return [{"retry": r.name, "repeats": r.repeats, "loses": r.loses,
             "seen": r.seen, "why": r.why} for r in RETRIES]


@dataclass(frozen=True)
class ChunkMode:
    """服务端把「这一段」发成增量还是全量——**这一条决定客户端怎么处理丢帧。**"""

    mode: str
    on_lost_frame: str
    on_reconnect: str
    example: str


CHUNK_MODES: tuple[ChunkMode, ...] = (
    ChunkMode("增量（`text-delta`）", "少一句，而**后面照常接**",
              "要 `Last-Event-ID`，否则接着的那半句没有主语",
              "AI SDK 的 `text-delta`：框架累加，你只管渲染"),
    ChunkMode("全量（每次都发整段）", "下一帧就把缺的补回来",
              "**不需要 id**：最后一帧就是全文",
              "简单、抗丢帧，代价是**流量随长度平方增长**"),
)


def chunk_table() -> list[dict]:
    return [{"mode": c.mode, "lost": c.on_lost_frame, "reconnect": c.on_reconnect,
             "example": c.example} for c in CHUNK_MODES]


@dataclass
class Session:
    """一次对话的界面侧状态。**`text` 与 `shown` 分开记——它们的差就是那一类故障。**"""

    state: str = "idle"
    text: str = ""
    shown: str = ""
    events: list[str] = field(default_factory=list)

    def feed(self, event: str) -> str:
        self.events.append(event)
        if event == "delta":
            self.text += "·"
        self.state, note = step(self.state, event)
        if event in ("done", "abort", "closed", "timeout", "error"):
            self.shown = self.text
        return note
