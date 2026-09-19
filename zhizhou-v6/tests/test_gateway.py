# tests/test_gateway.py —— 不需要密钥、不需要网络：一个错误之后该发生什么
"""十二组断言。这一份测的是**机制**（`app/gateway.py`），路由那一份是另一份。

四组最值钱：

1. **同一件事在三种方言里是三个码，而处置只有一个**——所以判据必须落在码上；
2. **余额不足与限流共用 429，而修法相反**：一个要等、一个要充钱。
   把它俩归成一类，就是给一个永远不会成功的请求做退避重试；
3. **`request_timeout` 是每一次的上限**：最坏等待 ＝ timeout × 尝试 × 候选，
   而预算把这条链钉在调用方的截止时间上；
4. **熔断是跨请求的状态，而「连续失败」与「窗口内失败数」不是同一件事**。
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.gateway import (FALLBACK, FATAL, FIX, RETRY, Backoff, Breaker,  # noqa: E402
                         GatewayError, ambiguous_statuses, call, classify,
                         deadline_budget, expected_attempts, naive_worst_case,
                         payload_fingerprint, parse_retry_after, wrong_by_status)
from app.router import Candidate  # noqa: E402
from app.wire import DIALECTS  # noqa: E402


class Script:
    """一条脚本化的传输：第 n 次调用回第 n 个脚本项。**多出来的一次会报错。**"""

    def __init__(self, items, clock=None, takes=0.0, cap_to_budget=False):
        self.items = list(items)
        self.calls = 0
        self.clock = clock
        self.takes = takes
        self.cap_to_budget = cap_to_budget

    def __call__(self, model, dialect, budget):
        i = self.calls
        self.calls += 1
        assert i < len(self.items), f"脚本只有 {len(self.items)} 步，第 {i + 1} 次是多余的"
        if self.clock is not None:
            self.clock.advance(min(self.takes, budget) if self.cap_to_budget else self.takes)
        item = self.items[i]
        if isinstance(item, Exception):
            raise item
        return item


class Resp:
    def __init__(self, text="好", payload=None):
        self.text = text
        self._payload = payload or {}


def err(status, code, dialect="messages"):
    return GatewayError(status, code, dialect)


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t

    def advance(self, seconds):
        self.t += seconds
        return self.t


# ---------------------------------------------------------------- 一、分档表

def test_同一件事在三种方言里是三个码而处置只有一个() -> None:
    assert classify(429, "rate_limit_error", "messages") == RETRY
    assert classify(429, "rate_limit_exceeded", "responses") == RETRY
    assert classify(429, "rate_limit_exceeded", "chat") == RETRY


def test_拿错方言的码会落到fatal() -> None:
    """`rate_limit_error` 是 Messages 的码。**码不是跨方言的。**"""
    assert classify(429, "rate_limit_error", "chat") == FATAL


def test_余额不足与限流共用429而修法相反() -> None:
    assert classify(429, "rate_limit_exceeded", "chat") == RETRY
    assert classify(429, "credit_balance_exhausted", "chat") == FATAL
    assert set(ambiguous_statuses()[429]) == {"rate_limit", "billing"}


def test_400上有三种处置() -> None:
    """同一个状态码：请求不合法（fatal）、超窗（fix）、触发内容政策（fallback）。"""
    from app.gateway import BY_ERROR
    assert [BY_ERROR[n].disposition for n in ambiguous_statuses()[400]] \
        == [FALLBACK, FIX, FATAL]
    assert wrong_by_status() == 13, "只看状态码会判错的格数"


def test_没见过的码按fatal而没见过的5xx按retry() -> None:
    assert classify(400, "brand_new_code", "chat") == FATAL
    assert classify(599, "who_knows", "chat") == RETRY


# ---------------------------------------------------------------- 二、退避

def test_退避是算出来的而retry_after能顶破cap() -> None:
    b = Backoff(base=0.5, factor=2.0, cap=8.0, attempts=5)
    assert b.delays() == [0.5, 1.0, 2.0, 4.0, 8.0]
    assert b.total() == 15.5
    assert b.delays(30.0)[0] == 30.0, "对方说了 30 秒，我们的 cap 管不着"
    assert b.total(30.0) == 45.0


def test_认不出的retry_after不当成零() -> None:
    assert parse_retry_after("30") == 30.0
    assert parse_retry_after("1.5") == 1.5
    assert parse_retry_after("Wed, 21 Oct 2026 07:28:00 GMT") is None, "HTTP 日期不认"
    assert parse_retry_after("-1") is None
    assert parse_retry_after("") is None


def test_抖动不花额外的时间() -> None:
    import random
    b = Backoff(attempts=5)
    total = sum(sum(b.with_jitter(random.Random(s))) for s in range(500))
    assert abs(total / 500 / b.total() - 0.5) < 0.02, "期望恰好一半"


# ---------------------------------------------------------------- 三、预算

def test_最坏等待是timeout乘尝试再乘候选() -> None:
    assert naive_worst_case(10.0, 2, 3) == 90.0
    assert naive_worst_case(10.0, 0, 1) == 10.0


def test_预算把剩余时间按剩余次数切开() -> None:
    assert deadline_budget(12.0, 3) == 4.0
    assert deadline_budget(12.0, 1) == 12.0
    assert deadline_budget(0.5, 4) == 0.0, "剩下 0.125 秒的尝试注定失败，不如不给"


def test_实跑不会超过截止时间() -> None:
    """每次都报限流，每一片耗满自己的预算——**整趟仍然停在 D 上**。"""
    clock = Clock()
    transport = Script([err(429, "rate_limit_exceeded", "chat")] * 50,
                       clock=clock, takes=10.0, cap_to_budget=True)
    got = call([Candidate(f"c{i}", "chat") for i in range(3)], transport,
               backoff=Backoff(base=0.5, factor=2.0, cap=8.0, attempts=2),
               deadline_s=12.0, now=clock, sleep=clock.advance)
    assert not got.ok
    assert clock.t == 12.0, f"实跑花了 {clock.t}s，而不是 90s，也不是 12s 以上"
    assert [round(a.timeout_s, 2) for a in got.attempts] == [4.0, 3.75, 2.75]


def test_不算等待只算尝试也会停在预算上() -> None:
    """`elapsed` 把尝试与等待都算进去——它才是调用方等到的那一个数。"""
    clock = Clock()
    transport = Script([err(429, "rate_limit_exceeded", "chat")] * 50,
                       clock=clock, takes=10.0, cap_to_budget=True)
    got = call([Candidate("c0", "chat")], transport, backoff=Backoff(attempts=2),
               deadline_s=12.0, now=clock, sleep=clock.advance)
    assert got.elapsed == clock.t == 12.0


# ---------------------------------------------------------------- 四、主循环

def _chain(*names):
    return [Candidate(n, "chat") for n in names]


def test_限流两次之后成功() -> None:
    t = Script([err(429, "rate_limit_exceeded", "chat"),
                err(503, "server_is_overloaded", "chat"), Resp("好")])
    got = call(_chain("m"), t, backoff=Backoff(attempts=5), deadline_s=60.0)
    assert got.ok and t.calls == 3 and got.network_calls == 3
    assert got.waited == 0.5 + 1.0, "等的是退避表上的前两项"


def test_拒答换人而不是重试() -> None:
    t = Script([err(400, "content_policy_violation", "chat"), Resp("好")])
    got = call(_chain("m", "n"), t, backoff=Backoff(attempts=5), deadline_s=60.0)
    assert got.ok and t.calls == 2
    assert got.attempts[0].outcome == FALLBACK
    assert got.attempts[0].candidate == "m" and got.attempts[1].candidate == "n"


def test_余额不足一次都不重试() -> None:
    """**这是本章最贵的一种错法**：给一个永远不会成功的请求做退避。"""
    t = Script([err(429, "insufficient_quota", "chat"), Resp("不该到这儿")])
    got = call(_chain("m"), t, backoff=Backoff(attempts=5), deadline_s=60.0)
    assert not got.ok and t.calls == 1
    assert got.attempts[0].outcome == FATAL
    assert "再试也不会变" in got.reason


def test_超窗换人而不是原样重试() -> None:
    t = Script([err(400, "context_length_exceeded", "chat"), Resp("好")])
    got = call(_chain("m", "big"), t, backoff=Backoff(attempts=5), deadline_s=60.0)
    assert got.ok and t.calls == 2 and got.attempts[0].outcome == FIX


def test_重试的载荷逐字节相同() -> None:
    """指纹在**发出去之前**算——失败的那几次根本没回来，而它们也要在内。"""
    payload = {"model": "m", "messages": [{"role": "user", "content": "hi"}]}
    t = Script([err(429, "rate_limit_exceeded", "chat"),
                err(503, "server_is_overloaded", "chat"), Resp("好")])
    got = call(_chain("m"), t, backoff=Backoff(attempts=5), deadline_s=60.0,
               fingerprint_of=lambda m, d: payload_fingerprint(payload))
    assert got.fingerprints == 1 and got.network_calls == 3


def test_平均尝试次数是算出来的不是配置里的数() -> None:
    b = Backoff(attempts=3)
    assert b.attempts == 3, "配置说「再试 3 次」＝最多发 4 次"
    assert abs(expected_attempts(0.20, 4) - 1.248) < 1e-9
    assert abs(expected_attempts(0.0, 4) - 1.0) < 1e-9


# ---------------------------------------------------------------- 五、熔断

def test_连续三次失败之后关上而冷却只放一个探针() -> None:
    b = Breaker(allowed_fails=3, cooldown_s=30.0)
    for t in (0.0, 1.0, 2.0):
        b.allow(t)
        b.record(False, t)
    assert b.state == "open"
    assert b.allow(3.0)[0] is False
    assert b.allow(32.0) == (True, "半开（放一个探针）"), "冷却结束不等于恢复"
    assert b.allow(32.5)[0] is False, "半开只放一个"


def test_探针失败就再关一轮探针成功才复位() -> None:
    b = Breaker(allowed_fails=2, cooldown_s=10.0)
    for t in (0.0, 1.0):
        b.allow(t)
        b.record(False, t)
    b.allow(20.0)
    b.record(False, 20.0)
    assert b.state == "open" and b.allow(25.0)[0] is False
    b.allow(40.0)
    b.record(True, 40.0)
    assert b.state == "closed" and b.fails == 0


def test_不该算在它头上的错不计数() -> None:
    """400 是调用方自己的错。记进去等于让一个调用方的 bug 把模型对所有人关掉。"""
    b = Breaker(allowed_fails=3, cooldown_s=30.0)
    for t in (0.0, 1.0, 2.0, 3.0, 4.0):
        b.allow(t)
        b.record(False, t, counts=False)
    assert b.state == "closed" and b.fails == 0


def test_连续计数会被别人的成功清零() -> None:
    """**这是「熔断必须共享」这句话的另一面。**

    坏租户的错被身旁健康租户的成功间隔开，于是它永远凑不出连续三次——
    同一趟流量换成「窗口内失败数」，两者都会被关在门外。
    """
    def run(window):
        b = Breaker(allowed_fails=3, cooldown_s=30.0, window_s=window)
        fails = (True, True, True, False, False)
        good_open = 0
        for i in range(240):
            t = i * 0.5
            is_bad = i % 2 == 0
            if not b.allow(t)[0]:
                if not is_bad:
                    good_open += 1
                continue
            b.record((not is_bad) or not fails[(i // 2) % 5], t)
        return good_open
    assert run(None) == 0
    assert run(60.0) > 0


def test_熔断跳过不算network_calls() -> None:
    b = Breaker(allowed_fails=1, cooldown_s=30.0)
    b.allow(0.0)
    b.record(False, 0.0)
    t = Script([Resp("好")])
    got = call(_chain("m"), t, breaker=b, deadline_s=60.0)
    assert not got.ok and t.calls == 0
    assert [a.outcome for a in got.attempts] == ["skipped"]
    assert got.network_calls == 0


def test_三种方言的载荷指纹互不相同() -> None:
    from app.dialects import ADAPTERS
    from app.wire import Block, Message, Request
    req = lambda d: Request(model="m", system="s", dialect=d, max_output_tokens=64,
                            messages=(Message("user", (Block("text", text="你好"),)),))
    prints = {payload_fingerprint(ADAPTERS[d].to_wire(req(d))) for d in DIALECTS}
    assert len(prints) == 3, "换方言就是换一份载荷（6.2 那道翻译的另一种说法）"
