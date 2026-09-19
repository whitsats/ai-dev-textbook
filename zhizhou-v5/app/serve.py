"""在线侧的一次请求：**把 5.1–5.6 的管线装成「一直跑着」的那个东西**。

前六章的入口都是一次性的：给问题、拿答案、打印读数。本章的入口是一个对象，
它身上挂着四件在线才需要的东西：

| 件 | 修哪条缺口 | 在哪 |
| --- | --- | --- |
| 缓存 | 同一句话第二次问还要重算一遍（问题嵌入 ＋ 检索 ＋ 模型调用） | `app/cache.py` |
| 并发与限流 | 没有上界，来多少接多少 | `Limiter` |
| 观测 | 出问题只能靠猜 | `app/observe.py` |
| 降级 | 上游抖一下，整条请求就 500 | `_model()` 的有界重试 ＋ 兜底 |

## 这一章刻意不做的两件事

1. **不做 HTTP 服务**（不引 FastAPI／uvicorn）。理由不是省事：本树在离线环境下是
   可测的，而「起一个端口、发一个请求」的验收在本机不可复现（端口、依赖、容器）。
   本文件把一次请求写成**一个纯函数 `Service.handle()`**，于是缓存、并发、降级、观测
   四件事都能在提交门里跑真读数；起服务的那一半（ASGI 装配、`/metrics` 端点、容器化）
   在第 8 篇。这与 3.10 的分工一致：**能在门里跑的写进本树，跑不了的写进正文并标注**。
2. **不做多进程／多机**。一次进程内的并发与排队已经足够把「上界」量清楚；
   跨进程的共享缓存与锁要真 Redis，属于拼接验证。

## 一条贯穿全章的纪律

**任何为了变快而做的改动，都要先在 5.6 的门里过关。**
本文件因此把「命中缓存」与「走完整路径」两条路都留着（`use_cache=False`），
读数里拿同一批 24 条评测集跑两遍：片级命中与答案命中**必须逐项相同**。
如果缓存改动把答案换了，那不是「快了一点」，那是**换了系统**。

## 三处「账要能分开看」的地方

1. **嵌入的缓存只有一笔**：问题 → 向量。片嵌入在 `build_retriever()` 里一次算完、
   不在请求路径上；把它算进命中率会让数字好看，却什么都没省；
2. **判档要再走两条原始路**：`critic.evaluate()` 要的是 `bm25` 与 `vector` 的**分数**，
   而缓存里存的是**融合后的片**。所以这一笔账单列（`retrieve_calls += 2`）——
   CRAG 的判档不是免费的；
3. **重试也是钱**：`cost.model_calls` 记的是**尝试次数**，不是成功次数。
   报「平均 1.0 次调用」而实际平均 1.3 次，是把成本算低了一档。
"""
from __future__ import annotations

import json
import random
import re
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Sequence

from app import critic
from app.cache import LayeredCache, Versions, normalize
from app.corpus import Chunk
from app.cost import QueryCost, hanzi
from app.generate import Control, bind, must_refuse, offline_control
from app.observe import JsonLog, Registry, Trace
from app.rag import NO_ANSWER, build_messages, check_citations
from app.retrieve import make_rewriter

__all__ = ["DEFAULT_ATTEMPTS", "DEFAULT_BACKOFF", "FALLBACK_TEXT", "Limiter", "Payload",
           "Reply", "RetryPolicy", "Service", "Session"]

DEFAULT_ATTEMPTS = 3
DEFAULT_BACKOFF = 0.5

#: 兜底文案。**它必须与「拒答」分开**：拒答是「资料里没有」（业务结论），
#: 兜底是「服务不可用」（运维状态）。混成一句的后果是——用户去改问题，
#: 而这时候该做的是等一会儿再试。（5.5 的 `NO_ANSWER` 是前者。）
FALLBACK_TEXT = "抱歉，服务暂时不可用（已记录）。请稍后重试；这不是「资料里没有」。"
REJECTED_TEXT = "当前请求过多，已限流。请稍后重试。"

#: 「继续」类问法。**判据写死在代码里**（与 5.5 的控制位同一做法）：
#: 它要保证「按需检索省了几次调用」这个读数在离线门里可复算。
_FOLLOWUP = re.compile(r"^(继续|接着|还有呢|还有吗|然后呢|上面|刚才|它呢|这个呢)")


@dataclass(frozen=True)
class RetryPolicy:
    """有界重试：三次、指数退避、**上限**。

    「有界」是硬要求：没有上限的重试会把一次上游抖动放大成一场雪崩
    （每个请求都在重试，上游看到的流量是原来的三倍）。三个数都要有：
    次数、退避、以及**放弃时的动作**（这里是降级，不是把异常抛给用户）。
    """

    attempts: int = DEFAULT_ATTEMPTS
    backoff: float = DEFAULT_BACKOFF
    cap: float = 4.0

    def delay(self, attempt: int, *, jitter: Callable[[], float] = random.random) -> float:
        """第 `attempt` 次失败之后等多久。**必须加抖动**：不加的话所有请求同时重试，
        上游刚缓过来就被第二波打回去（这就是「重试风暴」的字面意思）。"""
        base = min(self.backoff * (2 ** attempt), self.cap)
        return round(base * (0.5 + 0.5 * jitter()), 4)


class Limiter:
    """有界的并发闸门（信号量）＋ 排队上限。

    只有并发上限、没有排队上限，等于把压力从上游转成了内存：
    排队中的请求各自占着上下文，来得多就把进程拖垮。
    所以满了两件事一起做：**等一小会儿，然后拒**——拒绝要记进指标，
    否则「限流生效了」这件事在账面上看不见（用户看到的只是一堆失败）。
    """

    def __init__(self, *, limit: int = 8, queue: int = 32) -> None:
        self.limit = limit
        self.queue = queue
        self._sem = threading.BoundedSemaphore(limit)
        self._slots = threading.BoundedSemaphore(limit + queue)
        self._guard = threading.Lock()
        self.active = 0
        self.max_active = 0
        self.rejected = 0
        self.overlapped = 0

    def acquire(self, *, timeout: float = 0.0) -> bool:
        if not self._slots.acquire(timeout=max(timeout, 1e-6)):
            self.rejected += 1
            return False
        if not self._sem.acquire(timeout=max(timeout, 1e-6)):
            self._slots.release()
            self.rejected += 1
            return False
        with self._guard:
            self.active += 1
            self.max_active = max(self.max_active, self.active)
            if self.active > 1:
                self.overlapped += 1
        return True

    def release(self) -> None:
        with self._guard:
            self.active -= 1
        self._sem.release()
        self._slots.release()

    def stats(self) -> dict:
        return {"limit": self.limit, "queue": self.queue, "max_active": self.max_active,
                "overlapped": self.overlapped, "rejected": self.rejected}


@dataclass
class Session:
    """会话。本章只留两处最小状态：**上一轮问过什么**、**上一轮的片**。

    为什么不用 Redis 存它：会话是**有状态的那一小块**，本树把它放在进程里，
    并在正文里写明这是一处**有意的简化**——多实例部署时它会立刻出错
    （用户的下一句可能落到另一个进程上）。这一类问题属于 8.6（多租户与状态外置）。
    """

    session_id: str = ""
    turns: list[str] = field(default_factory=list)
    last: tuple[Chunk, ...] = ()

    def remember(self, question: str, chunks: tuple[Chunk, ...] = ()) -> None:
        self.turns.append(question)
        del self.turns[:-8]
        if chunks:
            self.last = chunks


@dataclass(frozen=True)
class Payload:
    """**能进缓存的那份东西**：与请求无关的纯数据。

    `Reply` 不能进缓存，因为它身上挂着 `trace`（一次请求的计时）与 `cost`——
    把上一次的计时当成这一次的，读数就会莫名其妙地「快」。
    这个划分（缓存里只放纯数据）在跨进程时会变成硬要求：
    JSON 能序列化的东西才能共享。
    """

    text: str
    chunks: tuple[Chunk, ...]
    quality: str
    refused: bool
    degraded: tuple[str, ...]
    citations_ok: bool


@dataclass
class Reply:
    """一次请求的返回值。**降级写在返回值里**（不是一个日志里的字符串）。"""

    question: str
    text: str
    chunks: tuple[Chunk, ...]
    quality: str
    refused: bool
    degraded: tuple[str, ...]
    trace_id: str
    cache_hits: tuple[str, ...]
    cost: QueryCost
    trace: Trace
    citations_ok: bool
    outcome: str = "ok"          # ok ｜ degraded ｜ rejected

    @property
    def cached(self) -> bool:
        return "answer" in self.cache_hits

    def as_dict(self) -> dict:
        return {"trace_id": self.trace_id, "outcome": self.outcome,
                "quality": self.quality, "refused": self.refused,
                "cached": self.cached, "degraded": list(self.degraded),
                "cache_hits": list(self.cache_hits), "chars": len(self.text),
                "chunks": len(self.chunks), "citations_ok": self.citations_ok,
                "cost": self.cost.as_dict(), "seconds": self.trace.total}


class Service:
    """装好的在线侧。**`handle()` 是对外唯一的入口。**"""

    def __init__(self, retriever, call: Callable[[list[dict]], str] | None = None, *,
                 cache: LayeredCache | None = None, log: JsonLog | None = None,
                 registry: Registry | None = None, retry: RetryPolicy | None = None,
                 limiter: Limiter | None = None, k: int = 3, mode: str = "hybrid",
                 depth: int = 10, budget: float = 8.0, model_rewrite: bool = False,
                 control: str = "always", judge_depth: int | None = None,
                 sleep: Callable[[float], None] = time.sleep,
                 clock: Callable[[], float] = time.perf_counter) -> None:
        if control not in ("always", "offline"):
            raise ValueError("control 只能是 always ｜ offline")
        self.retriever = retriever
        self.call = call
        self.cache = cache if cache is not None else LayeredCache()
        self.log = log if log is not None else JsonLog()
        self.registry = registry
        self.retry = retry or RetryPolicy()
        self.limiter = limiter or Limiter()
        self.k, self.mode, self.depth = k, mode, depth
        self.budget = budget            # 一次请求的时间预算（秒）；超了就不再重试
        self.model_rewrite = model_rewrite
        #: **线上默认是「总是检索」**，而不是 5.5 那套按需规则。
        #:
        #: 这一处是本章最重的一条实测（见 5.7.9）：把 5.5 的实验开关接到线上默认路径上，
        #: 同一批 24 条题的答案命中从 **0.9444 掉到 0.3333**、误拒从 0 涨到 3。
        #: 原因可复算：那套规则是**写在代码里的正则**，它不是模型，认不出
        #: 「发布说明有哪三个状态」这种没有显式关键词的问法。
        #: 所以它只能是一个**实验开关**（`control="offline"`），不能是默认值；
        #: 要真的按需检索，得让模型自己判（那是 5.5 的真机那一半，还没做）。
        self.control = control
        #: 判档时取几条候选来打分。**它是一个必须写死的值，不能「看着办」**：
        #: 5.5 的 `evaluate()` 默认 `depth=5`，5.6 调它时给的是 `k=3`——
        #: 同一批题、同一条判据，只差这一个数，拒答四格就从「漏拒 1／误拒 0」
        #: 变成「漏拒 0／误拒 1」（见 5.7.9 的读数）。默认跟 `k` 走。
        self.judge_depth = judge_depth or k
        self.sleep = sleep
        self.clock = clock
        self.sessions: dict[str, Session] = {}
        #: 当前请求的账。`_embed_cached` 是挂在 `retriever` 上的**共享**出口，
        #: 它看不到 `handle()` 的局部变量，所以用 `threading.local()` 把「这一次请求的账」
        #: 临时挂在实例上。**用线程局部而非实例属性**：并发下后者会把别人的账记到这一次上。
        self._ctx = threading.local()
        #: **唯一的注入点**：`Retriever` 只认这个可调用对象，所以把缓存包在这里，
        #: 不需要改 `retrieve.py` 一行。代价是它改的是传入对象的属性——
        #: 共享一个 `retriever` 的两个 `Service` 会互相盖掉，正文里写明了这一处。
        self._raw_embedder = retriever.embedder
        retriever.embedder = self._embed_cached
        self._metrics = self._build_metrics(registry)

    # ---------------- 观测 ----------------
    def _build_metrics(self, registry: Registry | None) -> dict:
        if registry is None:
            return {}
        return {
            "queries": registry.counter("queries_total", "请求总数", ("outcome",)),
            "cache": registry.counter("cache_lookups_total", "缓存查询数", ("layer", "outcome")),
            "degraded": registry.counter("degraded_total", "降级次数", ("kind",)),
            "latency": registry.histogram("request_duration_seconds", "一次请求的墙钟耗时",
                                          labels=("outcome",)),
        }

    def _count_cache(self, layer: str, hit: bool) -> None:
        metric = self._metrics.get("cache")
        if metric is not None:
            metric.inc(layer=layer, outcome="hit" if hit else "miss")

    # ---------------- 出口三件：嵌入、检索、模型 ----------------
    def _embed_cached(self, texts: Sequence[str]) -> list:
        """嵌入出口包一层缓存。请求路径上**只有问题那一次**嵌入。

        `use_cache=False` 的那条路走的是**完全不带缓存的原始出口**：
        读数里「冷跑」与「热跑」必须只差一个变量，而如果关掉的只是答复层，
        嵌入与检索仍在悄悄命中——那样算出来的「省下多少」就是低估的，
        甚至会在某一天变成负的（冷跑反而更快，因为你量错了）。
        """
        cost = getattr(self._ctx, "cost", None)
        enabled = getattr(self._ctx, "use_cache", True)
        out = []
        for text in texts:
            if not enabled:
                out.append(self._raw_embedder([text])[0])
                if cost is not None:
                    cost.embed_calls += 1
                continue
            vec, hit = self.cache.get_or_compute(
                "embedding", normalize(text), lambda t=text: self._raw_embedder([t])[0])
            self._count_cache("embedding", hit)
            if not hit and cost is not None:
                cost.embed_calls += 1
            out.append(vec)
        return out

    def _model(self, messages: list[dict], cost: QueryCost, degraded: list[str]) -> str:
        """调用模型：**有界重试 ＋ 退避 ＋ 时间预算**。失败时抛出，由调用方降级。

        三处刻意的选择：

        - `cost.model_calls += 1` 在 `try` 里、**每次尝试都加**：重试当然要花钱；
        - 抬 `degraded` 而不只写日志：降级必须出现在返回值里，否则调用方
          （以及读数的脚本）完全看不见它发生过；
        - 预算检查在**睡之前**：不然「重试 3 次 × 退避 4 秒」会让一次请求
          卡 12 秒，而连接早就断了。
        """
        deadline = self.clock() + self.budget
        last: Exception | None = None
        for attempt in range(1, self.retry.attempts + 1):
            try:
                cost.model_calls += 1
                return self.call(messages)
            except Exception as exc:                     # 上游什么都可能抛
                last = exc
                degraded.append(f"模型调用失败（第 {attempt} 次）：{type(exc).__name__}")
                if attempt >= self.retry.attempts:
                    break
                delay = self.retry.delay(attempt - 1)
                if self.clock() + delay > deadline:
                    degraded.append("时间预算用尽，停止重试")
                    break
                self.sleep(delay)
        raise last if last is not None else RuntimeError("模型不可用")

    def _model_bound(self, cost: QueryCost, degraded: list[str]):
        return lambda messages: self._model(messages, cost, degraded)

    def _control(self, question: str, session: "Session | None") -> Control:
        """四个控制位从哪来。两条路：

        - `always`（默认）：总是检索。**多花的那一次检索换的是「不会因为没认出问法
          而漏搜」，而这笔账在本章量出来是负的**（5.7.9 的两行读数）；
        - `offline`：5.5 的按需规则（正则），用来量「省下的调用」与「丢掉的质量」。
        """
        if self.control == "always":
            return Control("yes")
        continuing = bool(session is not None and session.turns
                          and _FOLLOWUP.search(question))
        return offline_control(question, continuing=continuing)

    # ---------------- 一次完整的路径 ----------------
    def _full_path(self, question: str, session: Session | None, trace: Trace,
                   cost: QueryCost) -> Payload:
        degraded: list[str] = []
        control = self._control(question, session)
        chunks: tuple[Chunk, ...] | None = None
        used = normalize(question)
        payload = {"q": used, "k": self.k, "mode": self.mode, "depth": self.depth,
                   "retrieve": control.retrieve}

        # ---- ① 取片（三条分支：直答 / 沿用上一轮 / 检索） ----
        if control.retrieve == "no":
            trace.span("skip_retrieve", 0.0, why="问法不需要检索")
        elif control.retrieve == "continue" and session is not None and session.last:
            chunks = session.last
            trace.span("reuse_last", 0.0, chunks=len(chunks))
        else:
            try:
                def compute():
                    rewriter = (make_rewriter(self._model_bound(cost, degraded))
                                if self.model_rewrite else None)
                    return self.retriever.search_with_rewrite(
                        question, k=self.k, depth=self.depth, rewriter=rewriter)

                with trace.measure("retrieve"):
                    if getattr(self._ctx, "use_cache", True):
                        got, hit = self.cache.get_or_compute("retrieval", payload, compute)
                    else:
                        got, hit = compute(), False
                self._count_cache("retrieval", hit)
                if not hit:
                    cost.retrieve_calls += 1
                # `search_with_rewrite` 返回的是 `Hit`（带分数与来源），
                # 而提示与引用要的是 `Chunk`。**只在这里脱一次壳**：
                # 往上游多留一份「片」会导致两处排序各说各话（5.4 的教训）。
                chunks, used, _src = tuple(h.chunk for h in got[0]), got[1], got[2]
            except Exception as exc:
                degraded.append(f"检索失败：{type(exc).__name__}")
                chunks = None                      # 当作「没有知识库」，走直答
                self._bump("degraded", kind="retrieve")

        # ---- ② 判档（CRAG）：**要两条原始路的分数，所以它不在缓存里** ----
        quality = "skipped"
        if chunks:
            with trace.measure("judge"):
                _raw, _scores, judged = critic.evaluate(self.retriever, used,
                                                        depth=self.judge_depth)
            cost.retrieve_calls += 2
            quality = getattr(judged, "value", str(judged))

        # ---- ③ 该不该调模型 ----
        reason = must_refuse(chunks or (), quality) if chunks is not None else None
        generated = False               # 「这段文字是模型对着资料产出的」——见下面的绑定那一步
        if reason:
            text = NO_ANSWER
            trace.span("refuse", 0.0, why=reason)
        else:
            messages = build_messages(question, chunks)
            cost.prompt_hanzi = hanzi(json.dumps(messages, ensure_ascii=False))
            try:
                with trace.measure("generate"):
                    text = self._model(messages, cost, degraded)
                generated = True
            except Exception as exc:
                degraded.append(f"生成失败：{type(exc).__name__}")
                text = FALLBACK_TEXT
                self._bump("degraded", kind="generate")

        # ---- ④ 绑定与引用核对（5.5）：**只对「模型对着资料产出的那段文字」做** ----
        #
        # 这一处的边界是测试逼出来的：第一版写成「有片就绑定」，于是生成失败时的
        # 兜底文案也被过了绑定层——它本来不是回答，却被按句切、按覆盖率挂上片编号，
        # 变成一句「抱歉，服务暂时不可用…… [2]」。**降级文案身上不能长引用**：
        # 引用是「这句话有依据」的声明，而它恰好相反（它声明的是「这一次没答成」）。
        citations_ok = True
        if chunks and generated:
            bound = bind(text, chunks)
            citations_ok = not bound.issues and not check_citations(bound.text, chunks)
            text = bound.text
        cost.output_hanzi = hanzi(text)

        if session is not None:
            session.remember(question, tuple(chunks or ()))
        return Payload(text=text, chunks=tuple(chunks or ()), quality=quality,
                       refused=text.strip() == NO_ANSWER, degraded=tuple(degraded),
                       citations_ok=citations_ok)

    def _bump(self, name: str, **labels) -> None:
        metric = self._metrics.get(name)
        if metric is not None:
            metric.inc(**labels)

    # ---------------- 主入口 ----------------
    def handle(self, question: str, *, session_id: str = "",
               use_cache: bool = True) -> Reply:
        """一次请求。四件事按顺序发生：**限流 → 缓存 → 完整路径 → 观测**。"""
        t0 = self.clock()
        cost = QueryCost()
        trace = Trace()
        session = self.sessions.setdefault(session_id, Session(session_id)) if session_id else None
        self.log.emit("query_start", trace_id=trace.trace_id, hanzi=hanzi(question),
                      session=session_id)

        if not self.limiter.acquire():
            self.log.emit("query_rejected", trace_id=trace.trace_id,
                          active=self.limiter.active)
            self._bump("queries", outcome="rejected")
            return Reply(question, REJECTED_TEXT, (), "skipped", False, ("限流",),
                         trace.trace_id, (), cost, trace, True, "rejected")

        self._ctx.cost = cost
        self._ctx.use_cache = use_cache
        try:
            hits: list[str] = []
            payload = {"q": normalize(question), "k": self.k, "mode": self.mode,
                       "retrieve": self._control(question, session).retrieve}
            if use_cache:
                value, hit = self.cache.get_or_compute(
                    "answer", payload,
                    lambda: self._full_path(question, session, trace, cost),
                    store_if=lambda p: not p.degraded)     # **降级结果不进缓存**
                self._count_cache("answer", hit)
                if hit:
                    hits.append("answer")
                payload_data = value
            else:
                payload_data = self._full_path(question, session, trace, cost)
            if payload_data.degraded:
                hits = [h for h in hits if h != "answer"]
        finally:
            self.limiter.release()

        seconds = self.clock() - t0
        outcome = "ok" if not payload_data.degraded else "degraded"
        reply = Reply(question, payload_data.text, payload_data.chunks,
                      payload_data.quality, payload_data.refused, payload_data.degraded,
                      trace.trace_id, tuple(hits), cost, trace,
                      payload_data.citations_ok, outcome)
        reply.trace.span("total", seconds)
        if self._metrics:
            self._metrics["queries"].inc(outcome=outcome)
            self._metrics["latency"].observe(seconds, outcome="hit" if hits else "miss")
        self.log.emit("query_done", trace_id=trace.trace_id, outcome=outcome,
                      cached=reply.cached, degraded=list(reply.degraded),
                      model_calls=cost.model_calls, seconds=round(seconds, 6))
        return reply

    # ---------------- 给读数脚本的一个只读入口 ----------------
    def retrieval_key(self, question: str) -> str:
        """**一次检索在这棵树里对应的缓存键**。

        读数脚本要报「片级命中」就必须拿到候选片，而服务对外只交答复。
        两个选择：让服务再算一遍（读数就不是它真用的那片了），
        或者把它的键开出来（脚本拿同一个键去取）。本树选后者——
        **读数与线上跑的是同一份东西，不是一份「大致相同」的复制品。**
        """
        from app.cache import cache_key
        return cache_key("retrieval", {"q": normalize(question), "k": self.k,
                                       "mode": self.mode, "depth": self.depth,
                                       "retrieve": "yes"}, self.cache.versions)

    def cached_cites(self, question: str) -> tuple[str, ...] | None:
        """从缓存里读回那一次检索的候选片（只读，不记账）。未命中返回 `None`。"""
        value = self.cache.tiers["retrieval"].peek(self.retrieval_key(question))
        if value is None:
            return None
        hits = value[0]
        return tuple(h.chunk.cite() for h in hits)

    # ---------------- 装配出这一篇的那棵树 ----------------
    @classmethod
    def from_tree(cls, root=None, call: Callable | None = None, **kw) -> "Service":
        """一条命令拿到装好的服务（与 `build_retriever()` 同一种形状）。

        版本戳从**内容**算：提示取自 `app/rag.py` 的两个模板，语料取语料清单的拼接，
        索引取「维度 ＋ n-gram ＋ 模式」。
        """
        from app.retrieve import build_retriever
        from app import rag

        retriever = build_retriever(root)
        prompt = rag.PROMPT_GROUNDED[0] + rag.PROMPT_GROUNDED[1]
        corpus_text = "\n".join(sorted(c.cite() + c.text for c in retriever.chunks))
        index_text = f"{retriever.store.dim}|{kw.get('mode', 'hybrid')}|{kw.get('depth', 10)}"
        versions = Versions.from_content(prompt=prompt, corpus=corpus_text,
                                         index=index_text, model="hashed-embedder-v1")
        return cls(retriever, call, cache=kw.pop("cache", None) or LayeredCache(versions),
                   **kw)
