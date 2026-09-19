"""网关：把「一个错误」分成四类，再按一张表决定下一步。

前三棵树里，模型调用点只有一行 `client.chat(...)`；线上跑起来以后，那一行周围会长出
这些东西：`except` 里判状态码、`sleep` 一下再试、试到第三个模型放弃、把「刚才那家挂了」
记进一个变量。**这四件事没有一件属于业务**，而它们每长一处都要重新想一遍
「哪些错值得重试」——想第二次的时候就开始不一致了。

所以这一层只做一件事：把「一个错误」分成**四类处置**，每一类只有一种后续动作：

| 处置 | 后续动作 | 判据 |
| --- | --- | --- |
| `retry` | 同一个候选等一会儿再试 | 错是**暂时**的（限流、过载、5xx、超时） |
| `fallback` | 换下一个候选 | 错是**这个人**的（内容政策） |
| `fix` | 改请求之后再试 | 错是**这一次请求**的（超窗） |
| `fatal` | 不试了，报给调用方 | 错**不会因为再试而消失** |

三处口径，每一处都对应一种会被重复犯的错：

1. **状态码不是判据，错误码才是**。400 一件事有三种命：请求不合法（`fatal`）、
   超窗（`fix`）、触发内容政策（`fallback`）；429 有两种命：限流（`retry`）与
   余额不足（`fatal`）。只看状态码的实现会把这些格判错，而最贵的一种错法是
   对「余额不足」做退避重试——等待、重试、账单照样是空的；
2. **退避的上限不是我们的 cap，是对方的 `Retry-After`**。两家都把这句话写在文档里
   （见 `SOURCES`），所以它是一条**共同点**，也就是一条能当断言的关系：
   算出来的等待只能更长，不能更短；
3. **`request_timeout` 是每一次的上限，不是这一次请求的上限**。它要乘以
   「每个候选试几次 × 几个候选」才是调用方真正可能等多久——所以这一层必须有
   **截止时间预算**：把剩下的时间按剩下的尝试次数切。
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

#: 抄这几页的那一天。错误码与处置是**协议的一部分**，与价格一样会变。
AS_OF = "2026-09-18"

#: 口径出处。分档表里每一格都指得到这里的一行。
SOURCES: dict[str, str] = {
    "claude_errors": "https://platform.claude.com/docs/en/api/errors",
    "openai_errors": "https://developers.openai.com/api/docs/guides/error-codes",
    "litellm_reliability": "https://docs.litellm.ai/docs/proxy/reliability",
    "litellm_routing": "https://docs.litellm.ai/docs/routing",
}

# --------------------------------------------------------------- 四类处置

RETRY = "retry"
FALLBACK = "fallback"
FIX = "fix"
FATAL = "fatal"

DISPOSITIONS: tuple[str, ...] = (RETRY, FALLBACK, FIX, FATAL)

DISPOSITION_NAME: dict[str, str] = {
    RETRY: "同一个候选等一会儿再试",
    FALLBACK: "换下一个候选",
    FIX: "改请求之后再试",
    FATAL: "不试了，报给调用方",
}


@dataclass(frozen=True)
class ErrorSpec:
    """一个规范错误档：它叫什么、怎么处置、在三种方言里长什么样。

    `codes` 里 `None` ＝ 这家**没有这个错误码**。那两格不是漏填，是事实：
    一家把「拒答」写在**停止原因**里（`refusal`，见 6.2 的 `STOP_MAP`），
    根本不产生错误；两家把「超时」交给**客户端**判定，所以它连状态码都没有。
    """

    name: str
    disposition: str
    codes: dict[str, tuple[int | None, str]]
    note: str = ""

    def status(self, dialect: str) -> int | None:
        return self.codes[dialect][0]

    def code(self, dialect: str) -> str:
        return self.codes[dialect][1]


def _spec(name: str, disposition: str, messages, responses, chat, note: str = "") -> ErrorSpec:
    return ErrorSpec(name, disposition,
                     {"messages": messages, "responses": responses, "chat": chat}, note)


#: **规范错误档 → 处置 ＋ 三方言的（状态码, 错误码）**。这是本章最核心的一张表：
#: 它把「哪些错值得重试」从一句经验变成一个能逐格核的东西。
#:
#: 处置那一列**与厂商无关**——这是这张表存在的理由：三家的码没有一个相同
#: （同族的 6.2 里，八栏也没有一栏同名），而「接下来该干什么」只有四种。
ERROR_TABLE: tuple[ErrorSpec, ...] = (
    _spec("rate_limit", RETRY, (429, "rate_limit_error"),
          (429, "rate_limit_exceeded"), (429, "rate_limit_exceeded")),
    _spec("overloaded", RETRY, (529, "overloaded_error"),
          (503, "server_is_overloaded"), (503, "server_is_overloaded")),
    _spec("server_error", RETRY, (500, "api_error"),
          (500, "server_error"), (500, "server_error")),
    # 超时这一格**没有状态码**：它是客户端自己判定的（等不到响应）。
    _spec("timeout", RETRY, (504, "timeout_error"),
          (None, "APITimeoutError"), (None, "APITimeoutError"),
          "一家有 504，两家交给客户端——所以这一格可能永远收不到码"),
    _spec("content_filter", FALLBACK, (None, "(不产生错误)"),
          (400, "content_policy_violation"), (400, "content_policy_violation"),
          "一家把拒答写在停止原因里，另外两家报 400"),
    _spec("context_overflow", FIX, (400, "invalid_request_error: prompt is too long"),
          (400, "context_length_exceeded"), (400, "context_length_exceeded"),
          "唯一的 fix 档：修法是换一个窗口更大的候选"),
    _spec("auth", FATAL, (401, "authentication_error"),
          (401, "invalid_api_key"), (401, "invalid_api_key")),
    _spec("permission", FATAL, (403, "permission_error"),
          (403, "unsupported_country_region_territory"),
          (403, "unsupported_country_region_territory")),
    _spec("bad_request", FATAL, (400, "invalid_request_error"),
          (400, "invalid_request_error"), (400, "invalid_request_error")),
    _spec("not_found", FATAL, (404, "not_found_error"),
          (404, "model_not_found"), (404, "model_not_found")),
    # 余额与限流共用 429，而修法相反：等一会儿（retry）／去充钱（fatal）。
    _spec("billing", FATAL, (402, "billing_error"),
          (429, "credit_balance_exhausted"), (429, "insufficient_quota"),
          "与限流共用 429，而重试不会让余额变多"),
    _spec("too_large", FATAL, (413, "request_too_large"),
          (413, "request_too_large"), (413, "request_too_large"),
          "按字节超限：缩不下就只能换通道（批量通道的上限更大）"),
)

BY_ERROR: dict[str, ErrorSpec] = {s.name: s for s in ERROR_TABLE}


class GatewayError(RuntimeError):
    """线上回来的一个错误。**它必须带着错误码**——只有状态码判不出下一步。"""

    def __init__(self, status: int | None, code: str, dialect: str, message: str = ""):
        super().__init__(f"[{dialect}] {status} {code} {message}".strip())
        self.status = status
        self.code = code
        self.dialect = dialect
        self.message = message


def classify(status: int | None, code: str, dialect: str) -> str:
    """一个错误该走四类里的哪一类。**判据是错误码，不是状态码。**

    找不到就按 `fatal` 处理：**没登记过的错不许当成「再试一次」**——
    那个方向的错法是把一个永远不会成功的请求重试到超时，
    而它在外表上与「努力过了」一模一样。
    """
    for spec in ERROR_TABLE:
        if spec.code(dialect) == code:
            return spec.disposition
    if status is not None and 500 <= status < 600:
        return RETRY          # 没见过的 5xx：按「暂时的」处理
    return FATAL


def classify_error(err: GatewayError) -> str:
    return classify(err.status, err.code, err.dialect)


# --------------------------------------------------------------- 同码不同命

def ambiguous_statuses() -> dict[int, list[str]]:
    """哪些状态码对应**不止一种**处置，各自是哪些错误档。

    这是「状态码不是判据」这句话的可计算形式。空字典才是「只看状态码也行」，
    而它不是空的——它是这张表最值钱的那一列。
    """
    out: dict[int, list[str]] = {}
    for spec in ERROR_TABLE:
        for st, _ in spec.codes.values():
            if st is None:
                continue
            out.setdefault(st, [])
            if spec.name not in out[st]:
                out[st].append(spec.name)
    return {st: names for st, names in out.items()
            if len({BY_ERROR[n].disposition for n in names}) > 1}


def wrong_by_status() -> int:
    """只看状态码会判错的**格数**（三方言 × 落在多义状态码上的错误档）。"""
    bad = ambiguous_statuses()
    return sum(1 for spec in ERROR_TABLE for st, _ in spec.codes.values()
               if st in bad)


# --------------------------------------------------------------- 退避

@dataclass(frozen=True)
class Backoff:
    """指数退避的三个数：起手、倍数、上限。抖动是额外的一档（见 `waits()`）。

    `cap` 的含义要写清：它**不是**这次请求的上限，是**一次等待**的上限。
    真正的上限由 `deadline_budget()` 决定——两张表管两件事，混起来就会
    「配了 8 秒上限，实际等了 40 秒」。
    """

    base: float = 0.5
    factor: float = 2.0
    cap: float = 8.0
    attempts: int = 5          # 上限 = 1 次首发 ＋ attempts 次重试

    def delays(self, retry_after: float | None = None) -> list[float]:
        """每一次重试前等多久。**`retry_after` 可以把它顶上去**。

        两家文档都写「honoring the `retry-after` header when present」，
        所以这是一条共同点：我们算出来的等待**只能更长，不能更短**。
        把 Retry-After 当成「建议」而截到 cap 以下的实现，
        会在对方明确说了「30 秒后再来」的时候，第 8 秒就再去撞一次。
        """
        out: list[float] = []
        for i in range(self.attempts):
            wait = min(self.base * (self.factor ** i), self.cap)
            out.append(wait)
        if retry_after is not None and out and retry_after > out[0]:
            out[0] = float(retry_after)
        return out

    def total(self, retry_after: float | None = None) -> float:
        return sum(self.delays(retry_after))

    def with_jitter(self, rng) -> list[float]:
        """**full jitter**：每一次等待取 `[0, 该次等待]` 里的一个随机数。

        它治的是「所有客户端同时被限流、同时在同一毫秒重试」——
        没有抖动时，重试风暴的形状与限流的形状一模一样。
        期望总等待恰好是原来的一半，所以它花的不是额外的时间。
        """
        return [rng.random() * d for d in self.delays()]


def parse_retry_after(value: str | None) -> float | None:
    """`Retry-After` 头可以是一个秒数，也可以是一个 HTTP 日期。**只认前者。**

    认不出的值不能当成 0：那会把「对方说等 30 秒」读成「马上可以再试」。
    返回 `None` ＝ 这一格我们不知道，于是退回自己算的等待。
    """
    if value is None:
        return None
    text = value.strip()
    try:
        got = float(text)
    except ValueError:
        return None
    return got if got >= 0 else None


def deadline_budget(deadline_s: float, attempts_left: int,
                    min_slice: float = 0.25) -> float:
    """把**剩下的时间**按**剩下的尝试次数**切开，返回这一次该给多少秒。

    这就是「`request_timeout` 是每一次的上限，不是这一次请求的上限」的修法：

    - 每试一次都拿满 `request_timeout` 的话，最坏等待 ＝
      `request_timeout × 尝试次数 × 候选数`（见 `naive_worst_case()`）；
    - 切成片以后，**最坏等待不会超过调用方给的截止时间**——超了就报超时，
      而不是让调用方在 120 秒里以为请求还活着。

    `min_slice` 是下限：剩下 0.3 秒时切出来的 0.1 秒注定失败，
    不如直接报「来不及了」——**给它一个必然失败的尝试，是拿延迟换一个假动作**。
    """
    if attempts_left <= 0:
        return 0.0
    slice_s = deadline_s / attempts_left
    return slice_s if slice_s >= min_slice else 0.0


def expected_attempts(p_fail: float, max_attempts: int) -> float:
    """一次失败概率为 `p` 的调用，**平均要发几次**（含首发，最多 `max_attempts`）。

    `p=0` 时是 1；`p` 很小且次数不限时趋近 `1/(1−p)`。
    这个数不是「重试几次」的配置，是**配置的效果**——写 `num_retries: 3`
    的人常常以为它等于「三次里总有一次成」，而它其实是「最多发四次」。
    """
    total = 0.0
    for k in range(max_attempts):
        total += (1 - p_fail) * p_fail ** k * (k + 1)
    total += max_attempts * p_fail ** max_attempts
    return total


def naive_worst_case(request_timeout_s: float, retries_per_candidate: int,
                     candidates: int) -> float:
    """按「每次拿满 timeout」算出来的最坏等待。**它与截止时间无关。**

    这一项刻意写成一个函数而不是一句注释：它是 `request_timeout` 那个名字
    最容易被误读的地方，而误读的代价是**调用方等满这个数**。
    """
    return request_timeout_s * (1 + retries_per_candidate) * candidates


# --------------------------------------------------------------- 熔断

@dataclass
class Breaker:
    """熔断器：一个候选失败到 `allowed_fails` 次，就关它 `cooldown_s` 秒。

    两个参数借自 LiteLLM 的 Router（`allowed_fails` / `cooldown_time`）。
    四处要与「重试」分开想的地方：

    1. **它是跨请求的状态**。重试是「这一次请求再试一下」，熔断是
       「接下来的请求都别再打它了」——所以它**必须**是共享的，
       而共享意味着**一个租户的失败会把模型对所有人关掉**。这不是缺陷，
       是选择：不共享的话，一百个并发请求会各撞一遍那面墙；
    2. **「连续失败」与「窗口内失败数」不是同一件事**（`window_s`）。
       连续计数会被**别人的成功清零**：一个时不时失败的坏租户，
       它的计数总被身旁那个健康租户的响应清掉，于是永远触不了熔断；
       窗口计数不看别人，坏租户的错误率直接变成别人的不可用。
       两个都有人用（LiteLLM 的参数说明写的是「一分钟内超过几次」＝窗口），
       而选哪个决定了「共享」到底约定了什么；
    3. **半开只放一个**。冷却结束不等于恢复，而是「放一个探针过去」；
       探针成功就复位，失败就再关一轮——否则恢复的那一刻所有积压请求一起冲上去；
    4. **它只该被「这个人自己的错」计数**。把 400 / 401 记进去，
       会让一个调用方的 bug 把模型对所有人关掉。
    """

    allowed_fails: int = 3
    cooldown_s: float = 30.0
    window_s: float | None = None        # None ＝ 连续失败计数
    fails: int = 0
    opened_at: float | None = None
    half_open: bool = False
    marks: list[float] = field(default_factory=list)

    def allow(self, now: float) -> tuple[bool, str]:
        """现在能不能打它。返回 `(放行, 理由)`——**理由要能进日志**。"""
        if self.opened_at is None:
            return True, "闭合（正常）"
        if now - self.opened_at < self.cooldown_s:
            return False, f"熔断中（还有 {self.cooldown_s - (now - self.opened_at):.1f}s）"
        if not self.half_open:
            self.half_open = True
            return True, "半开（放一个探针）"
        return False, "半开中（探针还没回来）"

    def record(self, ok: bool, now: float, counts: bool = True) -> None:
        """记一次结果。`counts=False` ＝ 这一次的错不该算在它头上。

        成功在两种模式下的含义不同：**连续模式里它把计数清零，窗口模式里它不清**
        （窗口只看时间，不看顺序）——这正是这两种模式在共享场景下分道的地方。
        """
        if ok:
            if self.window_s is None:
                self.fails = 0
            self.opened_at = None
            self.half_open = False
            return
        if not counts:
            return
        if self.half_open:
            self.opened_at = now          # 探针失败：再关一轮
            self.half_open = False
            return
        if self.window_s is None:
            self.fails += 1
        else:
            self.marks = [t for t in self.marks if now - t < self.window_s] + [now]
            self.fails = len(self.marks)
        if self.fails >= self.allowed_fails and self.opened_at is None:
            self.opened_at = now

    @property
    def state(self) -> str:
        if self.opened_at is None:
            return "closed"
        return "half-open" if self.half_open else "open"


# --------------------------------------------------------------- 载荷指纹

def payload_fingerprint(payload: dict) -> str:
    """一份载荷的指纹。**重试的判据是「这一次发出去的与上一次逐字节相同」。**

    少了这一条，「重试」会悄悄变成「发一个新的请求」：在载荷里放一个时间戳、
    一个 nonce、或者把消息顺序按 `set` 迭代一遍，都会让三次重试变成三次不同的调用——
    而它在日志里仍然长得像三次重试。
    """
    blob = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:12]


# --------------------------------------------------------------- 网关主循环

@dataclass
class Attempt:
    """发出去的一次尝试。**它是读数的最小单位。**"""

    candidate: str
    dialect: str
    number: int                  # 第几次尝试（从 1 开始，跨候选连续）
    waited_s: float
    outcome: str                 # "ok" / 处置名 / "skipped"
    detail: str = ""
    fingerprint: str = ""
    timeout_s: float | None = None
    elapsed_s: float = 0.0


@dataclass
class CallResult:
    ok: bool
    text: str = ""
    attempts: list[Attempt] = field(default_factory=list)
    reason: str = ""

    @property
    def network_calls(self) -> int:
        """真正发出去的次数。**被熔断跳过的那些不算**。"""
        return sum(1 for a in self.attempts if a.outcome != "skipped")

    @property
    def waited(self) -> float:
        return sum(a.waited_s for a in self.attempts)

    @property
    def elapsed(self) -> float:
        """这一次调用一共花了多久（尝试各自的耗时 ＋ 中间的等待）。

        它才是调用方等到的那一个数——`request_timeout` 与它没有固定关系。
        """
        return sum(a.elapsed_s + a.waited_s for a in self.attempts)

    @property
    def fingerprints(self) -> int:
        """不同的载荷指纹有几个。**它必须等于「发出去的次数」**，
        否则那几次「重试」里有几次其实发的是另一份请求。
        """
        return len({a.fingerprint for a in self.attempts if a.fingerprint})


def call(candidates, transport, *, backoff: Backoff | None = None,
         breaker: Breaker | None = None, deadline_s: float = 30.0,
         sleep=None, now=None, retry_after: float | None = None,
         fingerprint_of=None) -> CallResult:
    """网关的主循环：**候选在外、重试在内**。

    顺序不能换。换成「重试在外」的话，一个候选限流时所有候选都会被撞一遍，
    而「第一个候选恢复了没有」这件事永远轮不到——第二圈回到它时，
    调用方的时间早就用光了。

    `sleep` 与 `now` 是注入的**虚拟时钟**：读数要的是「等了多久」，
    而真的 `time.sleep` 会让一个能在提交门里跑的脚本变成几十秒。
    传输自己花掉的时间也由它报（传输推进同一个时钟）——
    **「这一次尝试花了多久」这件事不能在网关里猜**，猜出来的数会直接进预算。

    `fingerprint_of(model, dialect)` 在**发出去之前**算出这一次载荷的指纹——
    它必须在这里算，不能等回来再算：失败的那几次根本没回来，
    而「重试发的是不是同一份」正是要在它们身上看。
    """
    backoff = backoff or Backoff()
    _clock = _Clock()
    now = now or _clock
    sleep = sleep or _clock.advance
    attempts: list[Attempt] = []
    number = 0
    skipped: list[str] = []
    for cand in candidates:
        model = cand.model if hasattr(cand, "model") else str(cand)
        dialect = getattr(cand, "dialect", "")
        if breaker is not None:
            allowed, why = breaker.allow(now())
            if not allowed:
                attempts.append(Attempt(model, dialect, number + 1, 0.0, "skipped", why))
                skipped.append(f"{model}：{why}")
                continue
        for k in range(1 + backoff.attempts):
            number += 1
            left = backoff.attempts + 1 - k
            budget = deadline_budget(max(0.0, deadline_s - now()), left)
            if budget <= 0.0:
                attempts.append(Attempt(model, dialect, number, 0.0, "fatal",
                                        "截止时间用完了，再试一次也回不来"))
                return CallResult(False, attempts=attempts,
                                  reason="截止时间用完了（不是模型错）")
            stamp = fingerprint_of(model, dialect) if fingerprint_of else ""
            t0 = now()
            try:
                got = transport(model, dialect, budget)
            except GatewayError as err:
                verdict = classify_error(err)
                if breaker is not None:
                    breaker.record(False, now(),
                                   counts=verdict in (RETRY, FALLBACK, FIX))
                attempts.append(Attempt(model, dialect, number, 0.0, verdict,
                                        f"{err.status} {err.code}", timeout_s=budget,
                                        elapsed_s=now() - t0, fingerprint=stamp))
                if verdict == FATAL:
                    return CallResult(False, attempts=attempts,
                                      reason=f"{model} 报 {err.status} {err.code}"
                                             "（再试也不会变）")
                if verdict in (FALLBACK, FIX):
                    # **两类处置在这里都换人**，但换的对象不同：
                    # `fallback` 换的是名单上的下一个；`fix` 换的那个必须**窗口更大**
                    # （排序由 `router.bigger_window()` 负责）。若把 `fix` 也当成
                    # 重试，它会带着同一份「装不下」的请求再撞一次同一面墙——
                    # 而两次撞墙在日志里长得一模一样。
                    break
                wait = backoff.delays(retry_after)[min(k, backoff.attempts - 1)]
                # 先问「等完还够不够一次」，**问完再睡**。
                # 反过来（先睡、睡醒再问）会让这一趟多出一个白等的等待：
                # 第一版就是这样，12s 的截止时间量出来 13.0s——
                # 而它长得完全正常，因为每一个数都在「合理范围」里。
                if deadline_budget(max(0.0, deadline_s - now() - wait), left - 1) <= 0.0:
                    return CallResult(False, attempts=attempts,
                                      reason=f"剩下 {deadline_s - now():.2f}s，"
                                             f"再等 {wait:.1f}s 就不够一次尝试了")
                attempts[-1].waited_s = wait
                sleep(wait)
                continue
            if breaker is not None:
                breaker.record(True, now())
            attempts.append(Attempt(model, dialect, number, 0.0, "ok",
                                    fingerprint=stamp or payload_fingerprint(
                                        getattr(got, "_payload", {}) or {}),
                                    timeout_s=budget, elapsed_s=now() - t0))
            return CallResult(True, text=getattr(got, "text", ""), attempts=attempts)
    reason = "所有候选都试过了"
    if skipped:
        reason += "；其中跳过的：" + "、".join(skipped)
    return CallResult(False, attempts=attempts, reason=reason)


class _Clock:
    """虚拟时钟：读数里所有的「等了多久」都是它走的，不是墙上钟。"""

    def __init__(self) -> None:
        self.t = 0.0

    def __call__(self) -> float:
        return self.t

    def advance(self, seconds: float) -> float:
        self.t += seconds
        return self.t


def decision_table(dialect: str) -> list[tuple[str, str, str, str]]:
    """摊平成一行一格，供读数组装。**摊平的那一份与表同源，不另写一份。**"""
    return [(s.name, DISPOSITION_NAME[s.disposition],
             f"{s.status(dialect)}", s.code(dialect)) for s in ERROR_TABLE]
