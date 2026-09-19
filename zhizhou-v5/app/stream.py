"""SSE 事件流：把「一个答」变成**一串可续传的事件**。

## 为什么服务端这一章要管流式

前六章的交付物是「一次请求、一次返回」。上线之后用户不等第二个 5 秒，
于是回答要在**生成的过程中**就往外发。这一步改的不是 UI，是**接口的形状**：
返回值从一个字符串变成一条有序事件流，而事件流有它自己的契约——
谁分配编号、断了怎么办、重连补什么、什么算「发完了」。

前端（`EventSource`、React Hook、URL 长度限制、多标签页的连接上限）属于第 8 篇 8.3，
本章只做服务端这一半。

## 契约来自规范，不是来自某个库

字段只有四个（MDN 的 event stream format 一页写完）：

| 字段 | 作用 | 本树怎么用 |
| --- | --- | --- |
| `event` | 事件名，客户端按名字 `addEventListener` | `sources` / `token` / `done` / `error` |
| `data` | 载荷；**多行要写成多行 `data:`**，客户端会自动用换行拼回去 | JSON |
| `id` | 事件编号，浏览器把它存成 `Last-Event-ID` | 严格递增的整数（从 1 开始） |
| `retry` | 重连间隔（毫秒，整数，非整数会被忽略） | 首帧给一次，之后不再重复 |

三条语法细节，任何一条弄错都会让客户端「静默少东西」：

1. **一帧以空行结束**（`\n\n`）；连续两行 `data:` 会被拼成带换行的一段；
2. **冒号开头的行是注释**，客户端会忽略它——这正是心跳的写法：
   周期发 `: ping`，连接不会因为长时间没有数据被代理掐断，**而它不占事件编号**；
3. **`retry` 不是浮点数**：写 `1500.0` 会被整条忽略（规范：非整数则忽略）。

第 2 条是本章最容易被写错的一处：把心跳做成一个真正的 `event: ping`，
它就会**推进编号**，于是断线重连时客户端拿着 `Last-Event-ID=7`
（其实是心跳），服务端从 8 开始补——补的却是**正文的第 3 段**。
顺序看着对、编号也对，但少了一段。本树因此把心跳写成注释行，
并在读数的夹具里钉住「心跳不占编号」这一条。

## 续传要靠服务端留一小段

`Last-Event-ID` 只是客户端报出来的「我收到几号」。要真的补齐，服务端得**留着刚发过的
那几帧**（本树留 64 帧）。留着不是「缓存优化」，是可正确性的前提：
不留就只能从头发，于是客户端拿到重复内容，而重复在拼接后的文本里
表现为「同一句话说了两遍」——它不像报错那么显眼。
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Iterable

__all__ = ["Frame", "HEARTBEAT", "StreamLog", "StreamWriter", "check", "comment",
           "encode", "parse", "publish", "sse_frame"]

#: 冒号开头就是注释行（心跳）。**它不带 id**，所以不会推进客户端的 `Last-Event-ID`。
HEARTBEAT = ": ping"


@dataclass(frozen=True)
class Frame:
    """一帧。`kind` 只有两种：`comment`（心跳）与 `event`（真正的消息）。"""

    kind: str
    event: str = ""
    data: str = ""
    id: int = 0
    retry: int | None = None


def encode(frame: Frame) -> str:
    """把一帧编成规范要求的文本。**多行 data 逐行加前缀**（不是塞一个 `\\n` 进去）。"""
    if frame.kind == "comment":
        return f"{frame.data}\n\n"
    lines: list[str] = []
    if frame.id:
        lines.append(f"id: {frame.id}")
    if frame.event:
        lines.append(f"event: {frame.event}")
    if frame.retry is not None:
        # **必须是整数**：规范写得很清楚，「非整数则整个字段被忽略」——
        # 于是 `retry: 1500.0` 不会报错，它只是**没生效**，
        # 而客户端依旧按自己的默认间隔重连（与「没写」长得一模一样）。
        lines.append(f"retry: {int(frame.retry)}")
    for line in frame.data.split("\n"):
        lines.append(f"data: {line}")
    return "\n".join(lines) + "\n\n"


def comment(text: str) -> str:
    """心跳（或任意注释）。`text` 不需要自带冒号。"""
    body = text if text.startswith(":") else f": {text}"
    return f"{body}\n\n"


def sse_frame(event: str, data, *, id: int = 0, retry: int | None = None) -> str:
    """便捷封装：把 Python 对象编成 JSON 载荷。`ensure_ascii=False` 是本树一贯的约定。"""
    payload = data if isinstance(data, str) else json.dumps(data, ensure_ascii=False)
    return encode(Frame("event", event=event, data=payload, id=id, retry=retry))


def parse(text: str) -> tuple[Frame, ...]:
    """**服务端自己也要能解**——不为了兼容别人，只为了让不变量可断言。

    读数与测试里三条坏形态（乱序、重复、缺 `done`）都必须能**从文本里看出来**，
    否则读者只能相信「我们写对了」。这一段就是「能看出来」的那只眼。
    """
    frames: list[Frame] = []
    cur: dict = {}
    for raw in text.split("\n"):
        line = raw.rstrip("\r")
        if line == "":
            if cur:
                frames.append(_finish(cur))
                cur = {}
            continue
        if line.startswith(":"):
            frames.append(Frame("comment", data=line))
            continue
        name, _, value = line.partition(":")
        value = value[1:] if value.startswith(" ") else value
        if name == "data":
            cur["data"] = cur.get("data", "") + value + "\n"
        elif name == "id":
            cur["id"] = value
        elif name == "event":
            cur["event"] = value
        elif name == "retry":
            cur["retry"] = value
    if cur:
        frames.append(_finish(cur))
    return tuple(frames)


def _finish(cur: dict) -> Frame:
    data = cur.get("data", "")
    if data.endswith("\n"):
        data = data[:-1]          # 规范：末尾的换行去掉
    raw_id = cur.get("id", "")
    raw_retry = cur.get("retry", "")
    return Frame("event", event=cur.get("event", ""), data=data,
                 id=int(raw_id) if raw_id.isdigit() else 0,
                 retry=int(raw_retry) if raw_retry.isdigit() else None)


@dataclass
class StreamLog:
    """服务端留的那一小段已发帧。只按 `id` 留**事件**，心跳不进这里。"""

    max_items: int = 64
    frames: list[Frame] = field(default_factory=list)

    def push(self, frame: Frame) -> None:
        if frame.kind != "event":
            return
        self.frames.append(frame)
        if len(self.frames) > self.max_items:
            self.frames.pop(0)

    def replay(self, last_id: int) -> tuple[Frame, ...]:
        """补齐 `last_id` 之后的所有事件。**不重不漏**是它的全部判据。"""
        return tuple(f for f in self.frames if f.id > last_id)


def publish(writer: "StreamWriter", *, sources: Iterable, segments: Iterable[str],
            beats: int = 0) -> str:
    """一次回答的发布顺序：**先来源、再正文分段、最后 done**。

    `beats` 是「每发一段插一次心跳」——真实的空闲检测由定时器做，
    本树把它写成显式参数，好让读数里的「心跳不占编号」可复现。

    为什么先发来源：用户看到「正在检索 → 命中哪几篇 → 开始生成」的过程，
    比干等一个转圈要可信任得多。而它有一个代价：**来源一旦发出就收不回来**，
    后面若判为拒答，用户已经看见了那几片。所以拒答发生在**发来源之前**才算干净——
    这正是 5.5 把判据放在生成之前的那条设计在流式下的延伸。
    """
    segments = list(segments)          # 先落成列表：生成器被数两次就空了
    out = [writer.open(), writer.event("sources", list(sources))]
    for i, seg in enumerate(segments):
        if beats and i % max(beats, 1) == 0:
            out.append(writer.heartbeat())
        out.append(writer.event("token", {"content": seg}))
    out.append(writer.event("done", {"segments": len(segments)}))
    return "".join(out)


def check(text: str) -> tuple[str, ...]:
    """把三条不变量写成**能报错的检查**（服务端自己解自己的流）。返回问题清单。

    1. **编号严格递增且不重复**：重复看起来无害（客户端会覆盖），
       但它意味着服务端在补发时把同一段发了两次，而拼接后的正文会多出来一段；
    2. **必须以 `done` 结尾**：没有它客户端不知道「生成完了」还是「连接断了」——
       两者的重试行为完全相反（一个该关，一个该续）；
    3. **心跳不许带 `id`**：带了就推进客户端的 `Last-Event-ID`，
       而那个编号指向的是一个不存在的正文位置。
    """
    issues: list[str] = []
    frames = parse(text)
    ids: list[int] = []
    events: list[str] = []
    for f in frames:
        if f.kind == "comment":
            if f.data.split(" ", 1)[-1].isdigit():
                issues.append(f"心跳带了编号：{f.data!r}")
            continue
        events.append(f.event)
        if f.event == "open":
            continue
        if not f.id:
            issues.append(f"事件 {f.event!r} 没有编号")
            continue
        ids.append(f.id)
    for prev, cur in zip(ids, ids[1:]):
        if cur <= prev:
            issues.append(f"编号没有严格递增：{prev} → {cur}")
    if len(set(ids)) != len(ids):
        issues.append("同一编号出现了多次（补发重复）")
    if not events or events[-1] != "done":
        issues.append("流没有以 done 结尾")
    if "done" in events[:-1]:
        issues.append("done 之后还有事件")
    return tuple(issues)


class StreamWriter:
    """发事件的那一方：**编号只在这里分配**。

    一处容易写错的地方：编号要在「真正发出去」的时候分配，而不是在「准备内容」的时候。
    先给一整段答案编好号、再按 token 逐个发，会让续传的补发点落在 token 中间——
    客户端于是不知道自己到底收到了哪个字。本树按**段**（片、token 组、阶段）发，
    每段一个编号，续传的粒度就等于段的粒度。
    """

    def __init__(self, *, retry_ms: int = 3000, log: StreamLog | None = None) -> None:
        self.next_id = 1
        self.log = log or StreamLog()
        self.retry_ms = retry_ms
        self._retry_sent = False
        self.sent = 0

    def open(self) -> str:
        """首帧：告诉客户端重连间隔。**只发一次**（后面重复发没有意义，只会占带宽）。"""
        self._retry_sent = True
        return encode(Frame("event", event="open", data="{}", retry=self.retry_ms))

    def event(self, name: str, data) -> str:
        frame = Frame("event", event=name, data=json.dumps(data, ensure_ascii=False),
                      id=self.next_id)
        self.next_id += 1
        self.sent += 1
        self.log.push(frame)
        return encode(frame)

    def heartbeat(self) -> str:
        """心跳。**注意它不碰 `next_id`**——这是本章那条最容易被忽略的契约。"""
        return comment("ping")

    def resume(self, last_event_id: int) -> list[str]:
        """断线之后按 `Last-Event-ID` 补发。返回要发的帧（可能为空）。"""
        return [encode(f) for f in self.log.replay(last_event_id)]
