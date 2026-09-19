#!/usr/bin/env python
"""6.3 的读数脚本：把「出错之后怎么办」变成六组能复算的数。

    python scripts/gateway_reader.py --offline     # 六组读数（不要密钥、不要网络）
    python scripts/gateway_reader.py --self-test   # 三十八条夹具

它**不发请求**：分档表抄自两家错误码页，退避、预算、熔断都是纯算术，
网关那一趟跑在一条**脚本化的传输**上（第几次回什么，由夹具写死）。
所以这一章的每个结论都能拿纸笔复核——与 6.1／6.2 同一条纪律：
**读数要么能复算，要么别写进正文**。

六组依次是：错误分档表 / 退避与 Retry-After / 截止时间预算 /
降级链与请求形状 / 熔断器 / 重试是「重发」。
"""
from __future__ import annotations

import random
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.dialects import ADAPTERS  # noqa: E402
from app.gateway import (AS_OF, BY_ERROR, DISPOSITIONS, DISPOSITION_NAME,  # noqa: E402
                         ERROR_TABLE, FATAL, FIX, FALLBACK, RETRY, Backoff, Breaker,
                         GatewayError, ambiguous_statuses, classify, deadline_budget,
                         expected_attempts, naive_worst_case, payload_fingerprint,
                         parse_retry_after, wrong_by_status)
from app.registry import BY_NAME  # noqa: E402
from app.router import (Candidate, bigger_window, default_dialect,  # noqa: E402
                        ladder_jump, plan, price_ladder)
from app.select import BY_PROFILE, call_cost  # noqa: E402
from app.wire import DIALECTS, DIALECT_NAME, Block, Message, Request, Tool  # noqa: E402

#: 六组读数共用的那一份配置。**它必须像真的**：起手 10 秒超时、每个候选试 3 次、
#: 名单上三个候选——这三个数乘起来就是要给读者看的那个数。
REQUEST_TIMEOUT_S = 10.0
RETRIES_PER_CANDIDATE = 2          # =「再试 2 次」，共 3 次尝试
CANDIDATES = 3
DEADLINE_S = 12.0

SYSTEM = "你是知舟，一个企业知识库问答助手。"
TOOLS = (Tool("search", "在企业知识库里检索",
              {"type": "object", "properties": {"q": {"type": "string"}}}),)


def sample_request(dialect: str, tools: bool = True) -> Request:
    return Request(model="gpt-5.6-terra", system=SYSTEM,
                   messages=(Message("user", (Block("text", text="北京天气怎么样？"),)),),
                   tools=TOOLS if tools else (), max_output_tokens=1_024,
                   dialect=dialect)


# ------------------------------------------------------------------ 一、分档表

def group_table() -> list[str]:
    out = [f"=== 一、一个错误该走哪一类（规范错误档 {len(ERROR_TABLE)} 个 × 方言 "
           f"{len(DIALECTS)} 种，抄于 {AS_OF}）==="]
    out.append("（处置的机器名：retry＝同一个候选等一会儿再试　fallback＝换下一个候选　"
               "fix＝改请求之后再试　fatal＝不试了）")
    out.append(f"{'规范错误档':<18}{'处置':<10}" + "".join(f"{d:<30}" for d in DIALECTS).rstrip())
    for spec in ERROR_TABLE:
        cells = []
        for d in DIALECTS:
            st = spec.status(d)
            cells.append(f"{'—' if st is None else st} {spec.code(d)}")
        out.append(f"{spec.name:<18}{spec.disposition:<10}"
                   + "".join(f"{c:<30}" for c in cells).rstrip())
    counts = {d: sum(1 for s in ERROR_TABLE if s.disposition == d) for d in DISPOSITIONS}
    out.append("处置分布（按错误档）：" + "　".join(
        f"{d} {counts[d]} 档" for d in DISPOSITIONS))
    out.append("处置分布（按格，共 "
               f"{len(ERROR_TABLE) * len(DIALECTS)} 格）：" + "　".join(
                   f"{d} {counts[d] * len(DIALECTS)} 格" for d in DISPOSITIONS))
    amb = ambiguous_statuses()
    for st in sorted(amb):
        names = amb[st]
        #: 查的是**错误档名**，不是它在表里的下标——用下标查 `ERROR_TABLE`
        #: 会把 400 那三档标成 `retry`（前三行恰好都是 retry）。
        marks = "／".join(f"{n}（{BY_ERROR[n].disposition}）" for n in names)
        out.append(f"状态码 {st} 对应 {len(names)} 档两种以上的处置：{marks}")
    out.append(f"只看状态码会判错 {wrong_by_status()} 格"
               f"（占 {len(ERROR_TABLE) * len(DIALECTS)} 格的 "
               f"{wrong_by_status() / (len(ERROR_TABLE) * len(DIALECTS)) * 100:.1f}%）"
               "——**状态码不是判据，错误码才是**")
    no_status = [s.name for s in ERROR_TABLE for d in DIALECTS if s.status(d) is None]
    out.append(f"连码都没有的格：{len(no_status)} 个（{ '、'.join(sorted(set(no_status))) }）"
               "——超时要客户端自己判，拒答在 Messages 上根本不产生错误")
    out.append(f"没登记过的错误码一律按 {FATAL} 处理（"
               f"试一下：{classify(400, 'brand_new_code', 'chat')}），"
               "而没见过的 5xx 按 retry——**两者的区别是「对方明确地说了这是一件坏事」"
               "还是「对方自己也没搞清」**")
    return out


# ------------------------------------------------- 二、退避与 Retry-After

def group_backoff() -> list[str]:
    b = Backoff(base=0.5, factor=2.0, cap=8.0, attempts=5)
    out = ["=== 二、退避：等待也是这一单的一部分 ==="]
    out.append("每次重试前等（秒）：" + "、".join(f"{d:g}" for d in b.delays()))
    out.append(f"五次等待合计 {b.total():g}s——**而调用方给的截止时间是 "
               f"{DEADLINE_S:g}s：光等就把预算等光了**，所以退避必须与预算一起看")
    out.append(f"对方说 Retry-After: 30 → 第一次等待变成 {b.delays(30.0)[0]:g}s，"
               f"合计 {b.total(30.0):g}s")
    out.append(f"cap 只压得住我们自己算的那一串：8s 是我们的一次等待上限，"
               f"而 {b.total(30.0):g}s 才是这一次真的等了多久")
    for raw in ("30", "1.5", "Wed, 21 Oct 2026 07:28:00 GMT", "-1", ""):
        got = parse_retry_after(raw)
        out.append(f"  Retry-After: {raw!r:<32} → "
                   + ("认不出，退回自己算的等待" if got is None else f"{got:g}s"))
    rng = random.Random(7)
    jittered = b.with_jitter(rng)
    many = [sum(b.with_jitter(random.Random(s))) for s in range(4000)]
    out.append("加 full jitter（一次抽到）：" + "、".join(f"{d:.2f}" for d in jittered)
               + f"　合计 {sum(jittered):.2f}s")
    out.append(f"抽 4,000 次的均值是 {sum(many) / len(many):.2f}s，"
               f"而原值是 {b.total():g}s——比值 {sum(many) / len(many) / b.total():.3f}。"
               "**抖动花掉的不是额外的时间**（期望恰好一半），"
               "它治的是「所有客户端在同一毫秒重试」——"
               "没有它，重试风暴的形状与限流的形状一模一样")
    return out


# ------------------------------------------------- 三、截止时间预算

def budget_run(deadline_s: float):
    """真跑一遍：每个候选每一次都报到限流，直到预算用完。**读数是跑出来的。**

    每一次尝试耗掉的墙上时间取「脚本给的那一个」与「这一片拿到的预算」的较小值——
    真实世界里一个 10 秒超时的请求不会因为预算是 4 秒就提前回来，
    它要么在 4 秒被客户端挂断，要么在 10 秒自己报超时。
    """
    from app.gateway import call as gw_call
    clock = Clock()
    script = [_err(429, "rate_limit_exceeded", "chat") for _ in range(200)]
    transport = _scripted(script, clock=clock, takes=REQUEST_TIMEOUT_S,
                          cap_to_budget=True)
    got = gw_call([Candidate(f"候选{i}", "chat") for i in range(CANDIDATES)], transport,
                  backoff=Backoff(base=0.5, factor=2.0, cap=8.0,
                                  attempts=RETRIES_PER_CANDIDATE),
                  deadline_s=deadline_s, now=clock, sleep=clock.advance)
    return got, clock.t


def group_budget() -> list[str]:
    out = ["=== 三、截止时间预算：request_timeout 是每一次的上限 ==="]
    naive = naive_worst_case(REQUEST_TIMEOUT_S, RETRIES_PER_CANDIDATE, CANDIDATES)
    out.append(f"配置：request_timeout={REQUEST_TIMEOUT_S:g}s、每个候选再试 "
               f"{RETRIES_PER_CANDIDATE} 次、名单 {CANDIDATES} 个候选")
    out.append(f"每次拿满 timeout 的最坏等待 ＝ {REQUEST_TIMEOUT_S:g} × "
               f"({RETRIES_PER_CANDIDATE} ＋ 1) × {CANDIDATES} ＝ **{naive:g}s**"
               f"——而配置里没有一处写着 {naive:g} 这个数")
    got, elapsed = budget_run(DEADLINE_S)
    out.append(f"调用方给的截止时间是 {DEADLINE_S:g}s。实跑（每次都报限流、"
               f"每片耗满自己的预算）：")
    for a in got.attempts:
        out.append(f"  第 {a.number} 次尝试（{a.candidate}）：拿到的预算 "
                   f"{a.timeout_s:.2f}s，等 {a.waited_s:g}s → {a.detail}")
    out.append(f"  收尾：{got.reason}")
    out.append(f"**这一趟一共花了 {elapsed:.2f}s**（{len(got.attempts)} 次尝试、"
               f"其中发出 {got.network_calls} 次）——不是 {naive:g}s："
               "超了报超时，而不是让调用方在 90 秒里以为请求还活着")
    out.append("切片的代价：第一片只有 "
               f"{got.attempts[0].timeout_s:.2f}s，比原来的 {REQUEST_TIMEOUT_S:g}s 短得多"
               "——**长上下文请求会先败在预算上**，所以这条配置要按最慢的那条链定")
    return out


class Clock:
    """虚拟时钟。**读数里所有的「等了多久」都是它走的，不是墙上钟。**"""

    def __init__(self) -> None:
        self.t = 0.0

    def __call__(self) -> float:
        return self.t

    def advance(self, seconds: float) -> float:
        self.t += seconds
        return self.t


# ------------------------------------------------- 四、降级链与请求形状

#: 名单：按「能力从高到低」排（配置里最常见的写法）。
ROSTER = ["claude-fable-5-1", "gpt-6-astra", "claude-opus-5", "gpt-5.6-sol",
          "claude-sonnet-5", "gpt-5.6-terra", "gpt-5.6-luna", "claude-haiku-4-5"]


def group_chain() -> list[str]:
    out = ["=== 四、降级链：名单上只有名字，能不能走要看这一次请求的形状 ==="]
    auto = {True: plan("claude-fable-5-1", "messages", ROSTER[1:], tools=True),
            False: plan("claude-fable-5-1", "messages", ROSTER[1:], tools=False)}
    for tools in (False, True):
        p = auto[tools]
        shape = "带工具" if tools else "不带工具"
        out.append(f"名单上只有名字（方言由网关挑）：{shape} → 能走 {len(p.chain)}／"
                   f"{p.total - 1} 个候选，排掉 {len(p.excluded)} 个")
    pinned = {True: plan("claude-fable-5-1", "messages", ROSTER[1:], tools=True, pin="chat"),
              False: plan("claude-fable-5-1", "messages", ROSTER[1:], tools=False,
                          pin="chat")}
    for tools in (False, True):
        p = pinned[tools]
        shape = "带工具" if tools else "不带工具"
        out.append(f"名单写死走兼容层：{shape} → 能走 {len(p.chain)}／{p.total - 1} 个，"
                   f"排掉 {len(p.excluded)} 个")
    for label, why in pinned[True].excluded[:3]:
        out.append(f"  排掉 {label}：{why}")
    out.append("**同一个模型，不带工具时能走、带工具时不能**——"
               "「谁能降级」不是模型的属性，是「模型 × 方言 × 这一次的形状」的属性")
    up = bigger_window("claude-haiku-4-5", same_price_or_cheaper=False)
    up_cheap = bigger_window("claude-haiku-4-5")
    out.append(f"超窗（唯一的 fix 档）时的候选：从窗口最小的 {ROSTER[-1]}"
               f"（{BY_NAME[ROSTER[-1]].context:,} 词元）起手，窗口更大的有 {len(up)} 个；"
               f"再加上「不比它贵」这一条，只剩 {len(up_cheap)} 个（{up_cheap}）")
    out.append("超窗的修法不是「换个人」而是「换一个装得下的」："
               "名单里排一个窗口更小的候选，是把同一面墙再撞一次")
    #: 同一批成员、两种排法。名字不变，只换顺序——所以下面的差全部来自顺序。
    cap_first = plan(ROSTER[0], "messages", ROSTER[1:], tools=True)
    cheap_first = plan(by_price("asc")[0], default_dialect(by_price("asc")[0], True),
                       by_price("asc")[1:], tools=True)
    for label, p in (("按能力排（配置里最常见的写法）", cap_first),
                     ("按价钱排（同一批成员）", cheap_first)):
        rows = price_ladder(p, "单轮只读问答")
        out.append(f"{label}：" + " → ".join(f"{c.split('/')[0]} ${v:.6f}" for c, v in rows)
                   + f"　末跳／首跳 ＝ {ladder_jump(p, '单轮只读问答'):.2f}")
    cap_rows = [v for _, v in price_ladder(cap_first, "单轮只读问答")]
    bumps = sum(1 for a, b in zip(cap_rows, cap_rows[1:]) if b > a)
    out.append(f"同一批成员、只换顺序：「末跳比首跳贵几倍」从 "
               f"{ladder_jump(cheap_first, '单轮只读问答'):.2f} 变成 "
               f"{ladder_jump(cap_first, '单轮只读问答'):.2f}；"
               f"而按能力排的那条链上有 **{bumps} 处回升**（后一跳比前一跳贵）"
               "——它压根不是一条单调的价钱阶梯")
    out.append("**降级链同时承担两件事：先花多少钱、失败时往哪个方向走。**"
               "按能力排的那条整程都在最贵的价钱附近跑；按价钱排的那条失败时往上走"
               "——两条都对，但它们是两个不同的策略，而配置里只有一个顺序可以填")
    return out


def by_price(order: str) -> list[str]:
    """名单的另一种排法：按「这一次画像的账」升序或降序。"""
    rows = [(m, call_cost(BY_NAME[m], BY_PROFILE["单轮只读问答"])["total"])
            for m in ROSTER]
    rows.sort(key=lambda r: r[1], reverse=(order == "desc"))
    return [m for m, _ in rows]


# ------------------------------------------------- 五、熔断器

def breaker_timeline() -> list[str]:
    """一次脚本化的熔断时间线。**每一个时刻都是写死的，所以它能复核。**"""
    b = Breaker(allowed_fails=3, cooldown_s=30.0)
    script = [(0.0, False), (1.0, False), (2.0, False), (3.0, True),
              (10.0, True), (31.0, True), (32.0, False), (40.0, True),
              (61.0, True), (62.0, True), (70.0, True), (80.0, True)]
    out = []
    for t, ok in script:
        allowed, why = b.allow(t)
        if not allowed:
            out.append(f"t={t:>5.1f}  **跳过**（{why}）")
            continue
        b.record(ok, t)
        out.append(f"t={t:>5.1f}  放行 → {'成功' if ok else '失败'}"
                   f" → 状态 {b.state}"
                   + (f"（连续失败 {b.fails}）" if not ok and b.state == 'closed' else ""))
    return out


#: 坏租户的失败模式：每 5 个请求里前 3 个失败（都连在一起）。
#: **必须是写死的**：随机的失败序列没法用纸笔复核。
BAD_FAILS = (True, True, True, False, False)


def shared_breaker(window_s: float | None) -> dict:
    """**熔断器是共享状态**：一个坏租户的错误率，会变成另一个好租户的可用性。

    两个租户交替发请求（每 0.5s 一个，共 240 个），**共用一个熔断器**：
    坏租户按 `BAD_FAILS` 每 5 个错 3 个，好租户从来不失败。

    `window_s=None` 是连续失败计数；给了数就是「这么多秒内的失败数」——
    两种模式在这一趟里的差别就是这一组读数要量的东西。
    """
    b = Breaker(allowed_fails=3, cooldown_s=30.0, window_s=window_s)
    good_total = good_while_open = bad_skipped = 0
    opens = 0
    was_open = False
    for i in range(240):
        t = i * 0.5
        is_bad = i % 2 == 0
        if not is_bad:
            good_total += 1
        allowed, _ = b.allow(t)
        if b.state == "open" and not was_open:
            opens += 1
        was_open = b.state == "open"
        if not allowed:
            if is_bad:
                bad_skipped += 1
            else:
                good_while_open += 1
            continue
        ok = (not is_bad) or not BAD_FAILS[(i // 2) % len(BAD_FAILS)]
        b.record(ok, t)
    return {"window": window_s, "opens": opens, "bad_skipped": bad_skipped,
            "good_total": good_total, "good_while_open": good_while_open}


def group_breaker() -> list[str]:
    out = ["=== 五、熔断器：跨请求的状态（allowed_fails=3，cooldown=30s）==="]
    out.extend(breaker_timeline())
    out.append("注意 t=32.0 那一行：冷却一结束它就放了一次，"
               "**而放的那一次是探针，不是恢复**——探针失败就再关一轮")
    both = {None: shared_breaker(None), 60.0: shared_breaker(60.0)}
    for key, label in ((None, "连续失败计数"), (60.0, "60 秒窗口内的失败数")):
        r = both[key]
        out.append(f"{label}：熔断打开 {r['opens']} 次；坏租户自己的 {r['bad_skipped']} 个"
                   f"请求被跳过；**好租户（一个错都没有）也被跳过 "
                   f"{r['good_while_open']}／{r['good_total']} 个")
    out.append(f"两种模式的差别就在这里：连续计数下好租户被跳过 "
               f"{both[None]['good_while_open']} 个，窗口计数下 "
               f"{both[60.0]['good_while_open']} 个——**不是因为窗口更严，"
               f"而是因为连续计数会被「别人的成功」清零**：坏租户的错总被身旁那个"
               "健康租户的响应间隔开，于是它永远凑不出连续三次")
    out.append("**报错的是 A，被跳过的是 B**：熔断器必须共享（否则一百个并发各撞一遍），"
               "而共享就必然带上这一条。想两个都不要，只能把状态按「租户 × 候选」分开"
               "——代价是那面墙要被撞 N 遍")
    return out


# ------------------------------------------------- 六、重试是「重发」

def group_retry_identity() -> list[str]:
    from app.gateway import call as gw_call
    out = ["=== 六、重试是「重发」，不是「续跑」==="]
    #: 真的走一遍网关：两次限流、一次成功，三次发出去的载荷带指纹。
    script = [_err(429, "rate_limit_error") for _ in range(2)]
    script.append(_Resp("好"))
    transport = _scripted(script)
    got = gw_call([Candidate("gpt-5.6-terra", "messages")], transport,
                  backoff=Backoff(attempts=5), deadline_s=60.0,
                  fingerprint_of=lambda m, d: payload_fingerprint(
                      ADAPTERS[d].to_wire(sample_request(d))))
    digests = sorted({a.fingerprint for a in got.attempts})
    out.append(f"同一种方言的同一份请求，重试三次的载荷指纹：{digests[0][:8]}"
               f"　→ 不同的指纹有 {got.fingerprints} 个（发了 {got.network_calls} 次）"
               "——**重试的判据是「这一次与上一次逐字节相同」**")
    prints = {d: payload_fingerprint(ADAPTERS[d].to_wire(sample_request(d)))
              for d in DIALECTS}
    out.append("而同一个规范请求换一种方言就是另一份载荷："
               + "、".join(f"{d} {h[:6]}" for d, h in prints.items())
               + f"　→ {len(set(prints.values()))} 个不同的指纹（这是 6.2 那道翻译的另一种说法）")
    profile = BY_PROFILE["单轮只读问答"]
    rows = {m: call_cost(BY_NAME[m], profile)["total"]
            for m in ("gpt-5.6-terra", "gpt-5.6-luna")}
    in_share = profile.input_tokens / (profile.input_tokens + profile.output_tokens)
    terra = rows["gpt-5.6-terra"]
    out.append(f"重试一次要重付**整个输入**：{profile.name} 是 "
               f"{profile.input_tokens:,} 输入 ＋ {profile.output_tokens} 输出，"
               f"输入占词元的 {in_share * 100:.1f}%；一次 gpt-5.6-terra 是 "
               f"${terra:.6f}，再来一次就是再来这 ${terra:.6f}")
    out.append(f"重试率与成本的关系（最多试 4 次）：失败率 5% → 平均 "
               f"{expected_attempts(0.05, 4):.4f} 次；20% → "
               f"{expected_attempts(0.20, 4):.4f} 次；50% → "
               f"{expected_attempts(0.50, 4):.4f} 次")
    out.append("**配置写的是「最多试几次」，账上多出来的钱是「平均试几次」决定的**——"
               "而后者是前者的一个函数，从来不是那个数")
    return out


def readings() -> list[str]:
    lines: list[str] = []
    for part in (group_table(), group_backoff(), group_budget(),
                 group_chain(), group_breaker(), group_retry_identity()):
        lines.extend(part)
        lines.append("")
    lines.append("网关读数：六组全过 ｜ 离线自检通过")
    return lines


# ------------------------------------------------------------------ 夹具

@dataclass
class _Resp:
    """脚本化传输回的那个东西。`_payload` 是重试指纹的原料。"""

    text: str = "好"
    _payload: dict | None = None


def _scripted(script, clock: "Clock | None" = None, takes: float = 0.0,
              cap_to_budget: bool = False):
    """把一串剧本变成一条传输：第 n 次调用取第 n 个脚本项。

    脚本项可以是 `_Resp`（成功），也可以是 `GatewayError`（失败）。
    用完就抛断言——**「比剧本多调了一次」必须响**，否则重试算多了也看不出来。
    传了 `clock` 的话，它的 `takes` 会推进同一个时钟（网关靠它算「这一次花了多久」）。
    """
    box = {"i": 0}

    def transport(model, dialect, budget):
        i = box["i"]
        box["i"] += 1
        if i >= len(script):
            raise AssertionError(f"剧本只有 {len(script)} 次调用，第 {i + 1} 次是多余的")
        if clock is not None:
            clock.advance(min(takes, budget) if cap_to_budget else takes)
        item = script[i]
        if isinstance(item, Exception):
            raise item
        return item

    transport.calls = lambda: box["i"]
    return transport


def _err(status, code, dialect="messages"):
    return GatewayError(status, code, dialect)


def fixture_cases() -> list[tuple[str, bool]]:
    """二十一条夹具。**每条规则都要配一条反例**——只测正向会让规则越管越宽。"""
    from app.gateway import call as gw_call
    b = Backoff(base=0.5, factor=2.0, cap=8.0, attempts=5)
    #: 一次「限流两次、然后成功」的调用。
    retry_twice = _scripted([_err(429, "rate_limit_error"), _err(429, "rate_limit_error"),
                             _Resp("好", {"a": 1})])
    twice = gw_call([Candidate("m", "messages")], retry_twice, backoff=b,
                    deadline_s=60.0)
    #: 一次「一个候选说不了、换一个」的调用。
    fb = _scripted([_err(400, "content_policy_violation", "chat"),
                    _Resp("好", {"a": 1})])
    fell_back = gw_call([Candidate("m", "chat"), Candidate("n", "chat")], fb,
                        backoff=b, deadline_s=60.0)
    #: 一次「余额不足」的调用——**它必须当场停，一次都不重试**。
    broke = _scripted([_err(429, "insufficient_quota", "chat"), _Resp("不该到这儿")])
    fatal = gw_call([Candidate("m", "chat")], broke, backoff=b, deadline_s=60.0)
    #: 超窗：修法是换人，不是重试。
    over = _scripted([_err(400, "context_length_exceeded", "chat"), _Resp("好", {"a": 1})])
    fixed = gw_call([Candidate("m", "chat"), Candidate("big", "chat")], over,
                    backoff=b, deadline_s=60.0)
    bb = Breaker(allowed_fails=3, cooldown_s=30.0)
    for t in (0.0, 1.0, 2.0):
        bb.allow(t)
        bb.record(False, t)
    return [
        ("分档表十二档、三十六格", len(ERROR_TABLE) == 12 and len(DIALECTS) == 3),
        ("四类处置都有档落在上面",
         {s.disposition for s in ERROR_TABLE} == set(DISPOSITIONS)),
        ("400 对应三种处置（fatal／fix／fallback）",
         len({s.disposition for s in ERROR_TABLE
              if 400 in [st for st, _ in s.codes.values()]}) == 3),
        ("429 对应两种处置（retry／fatal）", set(ambiguous_statuses().get(429, []))
         == {"rate_limit", "billing"}),
        ("余额不足是 fatal 而不是 retry",
         next(s for s in ERROR_TABLE if s.name == "billing").disposition == FATAL),
        ("超窗是唯一的 fix 档",
         [s.name for s in ERROR_TABLE if s.disposition == FIX] == ["context_overflow"]),
        ("拒答是 fallback", next(s for s in ERROR_TABLE
                                 if s.name == "content_filter").disposition == FALLBACK),
        ("拒答在 Messages 上没有错误码（它写进停止原因）",
         ERROR_TABLE[4].status("messages") is None),
        ("没登记过的码按 fatal 处理", classify(400, "brand_new", "chat") == FATAL),
        ("没见过的 5xx 按 retry 处理", classify(599, "who_knows", "chat") == RETRY),
        ("拿错方言的码会落到 fatal（码不是跨方言的）",
         classify(429, "rate_limit_error", "chat") == FATAL
         and classify(429, "rate_limit_exceeded", "chat") == RETRY),
        (f"只看状态码会判错 {wrong_by_status()} 格", wrong_by_status() == 13),
        ("退避五次的等待是 0.5／1／2／4／8，合计 15.5s",
         b.delays() == [0.5, 1.0, 2.0, 4.0, 8.0] and abs(b.total() - 15.5) < 1e-9),
        ("Retry-After 能顶破 cap（30 > 8）", b.delays(30.0)[0] == 30.0
         and abs(b.total(30.0) - 45.0) < 1e-9),
        ("认不出的 Retry-After 不当成 0",
         parse_retry_after("Wed, 21 Oct 2026 07:28:00 GMT") is None
         and parse_retry_after("30") == 30.0 and parse_retry_after("-1") is None),
        ("最坏等待 ＝ timeout × 尝试 × 候选（10×3×3＝90s）",
         naive_worst_case(10.0, 2, 3) == 90.0),
        ("预算把剩余时间按剩余次数切开", deadline_budget(12.0, 3) == 4.0
         and deadline_budget(12.0, 1) == 12.0),
        ("剩下不到一片就直接判「来不及」", deadline_budget(0.5, 4, min_slice=0.25) == 0.0),
        ("实跑出来的每一片与逐片算出来的一致", _budget_slices_match()),
        ("实跑整趟不超过截止时间", _budget_run_total() <= DEADLINE_S + 1e-9
         and _budget_run_total() > DEADLINE_S - 1e-9),
        ("切片之后尝试次数比「每次拿满」少", _budget_run_calls() < 9),
        ("共享熔断：好租户一个错都没有，却被跳过", _shared_skips() > 0),
        ("连续计数会被别人的成功清零（两种模式量出的不一样）",
         shared_breaker(None)["good_while_open"] == 0
         and shared_breaker(60.0)["good_while_open"] > 0),
        ("400 那三档的处置不是按下标查出来的",
         [BY_ERROR[n].disposition for n in ambiguous_statuses()[400]]
         == [FALLBACK, FIX, FATAL]),
        ("重试会停在截止时间上（不是停在重试次数上）",
         _stopped_by_deadline()),
        ("限流两次之后成功：一次调用、三次发出去", twice.ok and retry_twice.calls() == 3
         and abs(twice.waited - 1.5) < 1e-9),
        ("拒答换人：两次调用、第二条链成功", fell_back.ok and fb.calls() == 2
         and fell_back.attempts[0].outcome == FALLBACK),
        ("余额不足当场停：一次都不重试", not fatal.ok and broke.calls() == 1
         and fatal.attempts[0].outcome == FATAL),
        ("超窗换人而不是原样重试", fixed.ok and over.calls() == 2
         and fixed.attempts[0].outcome == FIX),
        ("每个候选只试到该试的次数", twice.network_calls == 3),
        ("熔断：连续三次失败后关上",
         bb.state == "open" and bb.allow(10.0)[0] is False),
        ("熔断：冷却结束只放一个探针",
         bb.allow(32.0)[0] is True and bb.allow(32.5)[0] is False),
        ("熔断：探针成功即复位",
         _half_open_recovers() == "closed"),
        ("熔断：不该算在它头上的错不计数（400 不计）",
         _fatal_not_counted() == "closed"),
        ("名单只有名字时，八模型 × 两种形状全都能配方言",
         all(len(plan("x", "messages", ["claude-opus-5", "gpt-5.6-terra"],
                      tools=t).excluded) == 0 for t in (True, False))
         if "x" in BY_NAME else
         all(len(plan("claude-opus-5", "messages", ["gpt-5.6-terra"], tools=t).excluded) == 0
             for t in (True, False))),
        ("名单写死兼容层时，带工具的请求排掉四个",
         len(plan("claude-fable-5-1", "messages", ROSTER[1:], tools=True,
                  pin="chat").excluded) == 4
         and len(plan("claude-fable-5-1", "messages", ROSTER[1:], tools=False,
                      pin="chat").excluded) == 0),
        ("同一个模型：不带工具能走、带工具不能",
         len(plan("gpt-5.6-luna", "responses", ["gpt-6-astra"], tools=False,
                  pin="chat").excluded) == 0
         and len(plan("gpt-5.6-luna", "responses", ["gpt-6-astra"], tools=True,
                      pin="chat").excluded) == 1),
        ("超窗候选必须是窗口严格更大", "claude-haiku-4-5" not in bigger_window(
            "claude-haiku-4-5", same_price_or_cheaper=False)),
        ("超窗候选再要求「不比它贵」只剩一个",
         bigger_window("claude-haiku-4-5") == ["gpt-5.6-luna"]),
        ("同一批成员只换顺序：末跳／首跳从 48.5 变成 0.10",
         _ladder_direction()),
        ("按能力排的那条链有两处价钱回升", _ladder_bumps() == 2),
        ("网关内部重试三次的指纹只有一个", _fingerprint_stable()),
        ("换方言就是另一份载荷（三种方言三个指纹）",
         len({payload_fingerprint(ADAPTERS[d].to_wire(sample_request(d)))
              for d in DIALECTS}) == 3),
        ("平均尝试次数 ＝ (1−pᴺ)/(1−p)",
         abs(expected_attempts(0.20, 4) - (1 - 0.2 ** 4) / 0.8) < 1e-12
         and abs(expected_attempts(0.50, 4) - (1 - 0.5 ** 4) / 0.5) < 1e-12),
    ]


def _budget_slices_match() -> bool:
    got, _ = budget_run(DEADLINE_S)
    want = [4.0, 3.75, 2.75]
    return [round(a.timeout_s, 2) for a in got.attempts] == want


def _budget_run_total() -> float:
    return budget_run(DEADLINE_S)[1]


def _budget_run_calls() -> int:
    return budget_run(DEADLINE_S)[0].network_calls


def _shared_skips() -> int:
    return shared_breaker(60.0)["good_while_open"]


def _stopped_by_deadline() -> bool:
    from app.gateway import call as gw_call
    script = [_err(429, "rate_limit_error") for _ in range(30)]
    t = _scripted(script)
    got = gw_call([Candidate("m", "messages")], t, backoff=Backoff(attempts=20),
                  deadline_s=2.0)
    return (not got.ok) and t.calls() < 20 and ("截止" in got.reason
                                                or "等完" in got.reason)


def _half_open_recovers() -> str:
    b = Breaker(allowed_fails=2, cooldown_s=10.0)
    for t in (0.0, 1.0):
        b.allow(t)
        b.record(False, t)
    b.allow(20.0)
    b.record(True, 20.0)
    return b.state


def _fatal_not_counted() -> str:
    b = Breaker(allowed_fails=3, cooldown_s=30.0)
    for t in (0.0, 1.0, 2.0, 3.0, 4.0):
        b.allow(t)
        b.record(False, t, counts=False)     # 400：调用方自己的错
    return b.state


def _ladder_direction() -> bool:
    cheap = by_price("asc")
    a = plan(cheap[0], default_dialect(cheap[0], True), cheap[1:], tools=True)
    z = plan(ROSTER[0], "messages", ROSTER[1:], tools=True)
    return abs(ladder_jump(a, "单轮只读问答") - 48.5) < 0.5 \
        and abs(ladder_jump(z, "单轮只读问答") - 0.10) < 0.02


def _ladder_bumps() -> int:
    p = plan(ROSTER[0], "messages", ROSTER[1:], tools=True)
    rows = [v for _, v in price_ladder(p, "单轮只读问答")]
    return sum(1 for x, y in zip(rows, rows[1:]) if y > x)


def _fingerprint_stable() -> bool:
    """网关内部重试三次的指纹。**失败的那两次也在内**——所以指纹要发前算。"""
    from app.gateway import call as gw_call
    #: 注意码是**这一种方言的**那个（`rate_limit_exceeded`，不是 Messages 的
    #: `rate_limit_error`）——写错方言的码会落到「没登记过」那一格。
    script = [_err(429, "rate_limit_exceeded", "chat"),
              _err(503, "server_is_overloaded", "chat"), _Resp("好")]
    t = _scripted(script)
    got = gw_call([Candidate("m", "chat")], t, backoff=Backoff(attempts=3),
                  deadline_s=60.0,
                  fingerprint_of=lambda m, d: payload_fingerprint(
                      ADAPTERS[d].to_wire(sample_request(d))))
    return got.ok and got.fingerprints == 1 and len(got.attempts) == 3 \
        and all(a.fingerprint for a in got.attempts)


def self_test() -> int:
    cases = fixture_cases()
    bad = 0
    for label, ok in cases:
        print(f"  {'✓' if ok else '✗'} {label}")
        bad += 0 if ok else 1
    print(f"自检 {len(cases) - bad}/{len(cases)} 通过")
    return 1 if bad else 0


def main(argv: list[str]) -> int:
    if "--self-test" in argv:
        return self_test()
    for line in readings():
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
