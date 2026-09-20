"""数据合规与脱敏：把「留多久、谁能认出谁、删掉到底删没删」变成三件可查的事。

前四对模块回答的是「它还行吗」「有人想让它不行的时候谁会拦住」，这一对回答的是
**「它留下的东西，我们能不能说清楚」**。三件事各自有一条最容易被糊过去的判据：

**① 写了期限 ≠ 会删。** 留存期是一行配置，而「数据活多久」由**写入路径**决定。
所以每类数据除了「该留几天」，还要记一个 `enforced`（有没有一条真的会删它的路径）——
没有的话，那一类的「过期条数」只会在报表上一直涨，而报表本身不会报错。

**② 脱敏 ≠ 匿名。** 掩码与哈希都把值变得「读不出来」，但**同一个人的两条记录
仍然能连起来**（掩码靠保留下来的那几位，哈希靠同一个输入的同一个输出）。
四种手法里真正除掉「可关联性」的只有两种（替换、删除），代价是**分析能力归零**
——所以这是一个取舍，不是一个「更好的做法」。

**③ 删除请求要走几个地方，由这张表决定，不由意愿决定。** 一位用户的业务数据
落在六个存储里，而删除路径通常只覆盖其中三个；落在备份与链路内容里的那两份
既不能删（它们是只增的），也不该假装删了——**它们要写进边界，而不是写进「已完成」**。

依据是三条官方口径：OpenAI 的数据控制页（留存与「不为训练所用」的两种设置）、
NIST AI RMF 的治理那一步（留存与最小化是可度量的动作）、以及 7.2 已经落过地的那一条
（内容捕获**逐项 Opt-In、默认关闭**）——本章把这三条各变成一个数。
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

# ------------------------------------------------------------------ 一、留存

@dataclass(frozen=True)
class Policy:
    """一类数据的留存规矩。

    `days` 是写下来的期限；`enforced` 是**它有没有一条真的会删它的路径**——
    这两个东西分开记，是因为它们分开失效（见模块开头 ①）。
    """

    kind: str
    label: str
    days: int
    enforced: bool


#: 本项目的六类留存数据。**`enforced=False` 的两类不是漏写，是有原因的**：
#: 审计记录按规范是「只增」的，语料入库管线只增不删（差量只做新增，5.8）。
#: 但「有原因」不等于「不用记」——它们必须在报表上各占一行。
RETENTION: tuple[Policy, ...] = (
    Policy("prompt", "提示与回答正文", 30, True),
    Policy("trace", "链路明细（7.2 的内容捕获）", 7, True),
    Policy("cache", "缓存", 1, True),
    Policy("billing", "四栏账（6.4）", 365, True),
    Policy("corpus", "语料（5.8）", 365, False),
    Policy("audit", "审计记录（7.4）", 730, False),
)

POLICY_BY_KIND = {p.kind: p for p in RETENTION}


@dataclass(frozen=True)
class Record:
    """一条留在盘上的数据。`created_day` 是创建于第几天（整数，便于手算）。"""

    kind: str
    subject: str
    created_day: int
    text: str


def age_days(record: Record, now: int) -> int:
    return now - record.created_day


def expired(records: tuple[Record, ...], now: int) -> list[Record]:
    """**超过自己那一类期限、却仍然在盘上**的记录。"""
    return [r for r in records
            if age_days(r, now) > POLICY_BY_KIND[r.kind].days]


def retention_report(records: tuple[Record, ...], now: int) -> list[dict]:
    """每一类一行：条数、过期条数、**其中真的会被删掉的**、活得最久的那条。

    第三列与第二列分开，就是模块开头 ① 的那条判据的可查形式：
    两列相等说明这一类的期限是**被执行**的；第二列大而第三列为 0，
    说明它只有一行配置。
    """
    rows: list[dict] = []
    for policy in RETENTION:
        mine = [r for r in records if r.kind == policy.kind]
        stale = [r for r in mine if age_days(r, now) > policy.days]
        oldest = max((age_days(r, now) for r in mine), default=0)
        rows.append({
            "kind": policy.kind,
            "label": policy.label,
            "days": policy.days,
            "enforced": policy.enforced,
            "count": len(mine),
            "stale": len(stale),
            "will_delete": len(stale) if policy.enforced else 0,
            "oldest": oldest,
        })
    return rows


def retention_tally(records: tuple[Record, ...], now: int) -> dict:
    """六类合起来的两笔账：过期了多少条，其中多少条**不会**被删。"""
    rows = retention_report(records, now)
    stale = sum(r["stale"] for r in rows)
    deleted = sum(r["will_delete"] for r in rows)
    return {
        "stale": stale,
        "will_delete": deleted,
        "orphan": stale - deleted,
        "worst": max(rows, key=lambda r: r["oldest"] - r["days"])["kind"],
        "worst_over": max(r["oldest"] - r["days"] for r in rows),
    }


# ------------------------------------------------------------------ 二、脱敏

TECHNIQUES = ("mask", "placeholder", "hash", "drop")
TECHNIQUE_LABEL = {
    "mask": "掩码",
    "placeholder": "替换",
    "hash": "哈希",
    "drop": "删除",
}


def apply(technique: str, value: str) -> str:
    """四种手法各自对同一个值做了什么（**掩码与哈希在本模块的取值是固定的**）。"""
    if technique == "mask":
        if len(value) <= 4:
            return "*" * len(value)
        return value[:3] + "*" * (len(value) - 7) + value[-4:]
    if technique == "placeholder":
        return "<已隐去>"
    if technique == "hash":
        return "h:" + hashlib.sha256(value.encode("utf-8")).hexdigest()[:8]
    if technique == "drop":
        return ""
    raise KeyError(technique)


def linkability_table(values: tuple[str, ...]) -> list[dict]:
    """四法各一行：样本里有多少个**不同的输出**。

    输出的种类数比输入少 → 有碰撞（替换法只有一个输出，全部撞在一起）；
    与输入种类数相等 → **可关联**（同一个值永远得到同一个输出，于是两份数据能 join）。
    两件事都记下来，因为「撞在一起」与「连得起来」是两种相反的失效。
    """
    rows: list[dict] = []
    for technique in TECHNIQUES:
        outs = [apply(technique, v) for v in values]
        rows.append({
            "technique": technique,
            "label": TECHNIQUE_LABEL[technique],
            "distinct_in": len(set(values)),
            "distinct_out": len(set(outs)),
            "collapsed": len(set(outs)) == 1 and len(set(values)) > 1,
            "joinable": len(set(outs)) == len(set(values)) and len(set(values)) > 1,
            "sample": outs[0],
        })
    return rows


def tail_guess(population: tuple[tuple[str, str], ...]) -> dict:
    """**掩码留下的那 4 位尾号，加上一个看起来无关的字段，够不够认出人。**

    `population` 是 `(尾号4位, 生日)` 的合成总体。两问：只按尾号分组时最大的一组有多少人；
    再按（尾号 ＋ 生日）分组时，有多少组只剩一个人——**后者就是「重新识别」的成功面**。
    """
    by_tail: dict[str, int] = {}
    by_both: dict[tuple[str, str], int] = {}
    for tail, birthday in population:
        by_tail[tail] = by_tail.get(tail, 0) + 1
        by_both[(tail, birthday)] = by_both.get((tail, birthday), 0) + 1
    singles = sum(1 for n in by_both.values() if n == 1)
    return {
        "n": len(population),
        "tail_groups": len(by_tail),
        "tail_max": max(by_tail.values(), default=0),
        "both_groups": len(by_both),
        "both_singletons": singles,
        "singleton_rate": singles / len(population) if population else 0.0,
    }


# ------------------------------------------------------------------ 三、识别码

#: 「像不像」这一层的四条正则。**它们只回答形状，不回答对错**（见模块开头 ②）。
SHAPE_RULES: tuple[tuple[str, str], ...] = (
    ("phone", r"1[3-9]\d{9}"),
    ("email", r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    ("card", r"\b\d{16}\b"),
    ("cn_id", r"\b\d{17}[\dXx]\b"),
)

RULE_LABEL = {
    "phone": "手机号",
    "email": "邮箱",
    "card": "卡号（16 位）",
    "cn_id": "身份证（18 位）",
}


def luhn_ok(digits: str) -> bool:
    """Luhn 校验：**16 位卡号**里大约每 10 个随机数有 1 个会「碰巧」通过。"""
    if not digits.isdigit():
        return False
    total = 0
    for i, ch in enumerate(reversed(digits)):
        d = int(ch)
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


_CN_ID_WEIGHTS = (7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2)
_CN_ID_CHECKS = "10X98765432"


def cn_id_ok(value: str) -> bool:
    """身份证的第 18 位是前 17 位的加权校验位——**这一位让「像」与「是」分得开**。"""
    value = value.strip().upper()
    if len(value) != 18 or not value[:17].isdigit():
        return False
    total = sum(int(c) * w for c, w in zip(value[:17], _CN_ID_WEIGHTS))
    return value[17] == _CN_ID_CHECKS[total % 11]


def has_checksum(kind: str) -> bool:
    """哪几类**有**校验位可用。手机号与邮箱没有——这就是「两条规则各查一半」的由来。"""
    return kind in ("card", "cn_id")


def detect(text: str) -> list[dict]:
    """一份文本上四条形状规则的全部命中，每条附上**校验位过没过**。"""
    hits: list[dict] = []
    for kind, pattern in SHAPE_RULES:
        for m in re.finditer(pattern, text):
            value = m.group(0)
            ok = None
            if kind == "card":
                ok = luhn_ok(value)
            elif kind == "cn_id":
                ok = cn_id_ok(value)
            hits.append({
                "kind": kind,
                "label": RULE_LABEL[kind],
                "value": value,
                "start": m.start(),
                "checksum": ok,
            })
    hits.sort(key=lambda h: h["start"])
    return hits


def detect_tally(texts: tuple[str, ...]) -> dict:
    """两笔账：**只用形状规则**报出来的，与**只有校验位能确认**的。

    两者的差就是假阳——而假阳的代价是「把正常的订单号当成卡号掩掉」，
    它在报表上表现为「脱敏后查不到自己的订单」。
    """
    hits = [h for t in texts for h in detect(t)]
    with_checksum_rule = [h for h in hits if has_checksum(h["kind"])]
    confirmed = [h for h in with_checksum_rule if h["checksum"]]
    false_pos = [h for h in with_checksum_rule if not h["checksum"]]
    no_checksum = [h for h in hits if not has_checksum(h["kind"])]
    return {
        "hits": len(hits),
        "confirmed": len(confirmed),
        "false_pos": len(false_pos),
        "no_checksum": len(no_checksum),
        "texts": len(texts),
    }


# ------------------------------------------------------------------ 四、删除

#: 一位用户的业务数据会落到的六个地方（**不是六个都要删，而是六个都要交代**）。
STORES: tuple[tuple[str, str, bool], ...] = (
    ("primary", "主库（业务表）", True),
    ("cache", "缓存（5.7）", True),
    ("vector", "向量索引（5.3）", True),
    ("trace", "链路内容（7.2 的内容捕获）", False),
    ("log", "冷日志（只增）", False),
    ("backup", "备份（按轮转过期）", False),
)


def deletion_plan(subject: str) -> list[dict]:
    """一次「请删掉我」在六个地方各是什么结果。

    `reachable=True` 的三处能当场删；另外三处**删不了**——两个是只增的，
    一个只能等轮转。它们要么写进边界，要么这句「已删除」就是假的。
    """
    return [
        {"store": key, "label": label, "reachable": ok,
         "action": "删除" if ok else "随轮转过期（不可当场删）"}
        for key, label, ok in STORES
    ]


def deletion_tally(subject: str) -> dict:
    plan = deletion_plan(subject)
    reached = [p for p in plan if p["reachable"]]
    return {
        "subject": subject,
        "stores": len(plan),
        "reached": len(reached),
        "leftover": len(plan) - len(reached),
        "backup_days": 90,
    }


# ------------------------------------------------------------------ 五、内容捕获

CAPTURE_MODES = ("on", "off")
CAPTURE_LABEL = {"on": "开（存正文）", "off": "关（只存结构）"}


def capture_report(records: tuple[Record, ...], texts: tuple[str, ...]) -> list[dict]:
    """同一个旋钮的两个位置各买到什么。

    开着：出事时能回放那一趟（**可调试性**），代价是正文里带着识别码；
    关着：盘上一条识别码都没有，代价是「刚才那一次到底答了什么」查不了。
    **这个旋钮没有中间档**——所以两个数必须一起报（见正文的边界）。
    """
    captured = [r for r in records if r.kind in ("prompt", "trace")]
    dirty = sum(1 for r in captured if detect(r.text))
    rows: list[dict] = []
    for mode in CAPTURE_MODES:
        on = mode == "on"
        rows.append({
            "mode": mode,
            "label": CAPTURE_LABEL[mode],
            "records": len(captured),
            "stored": len(captured) if on else 0,
            "with_pii": dirty if on else 0,
            "replayable": len(captured) if on else 0,
        })
    return rows


# ------------------------------------------------------------------ 六、审计自查

@dataclass(frozen=True)
class Access:
    """一条「谁在什么时候看了谁的数据、为什么看」。**第三格是本模块的重点。**"""

    actor: str
    subject: str
    purpose: str
    target_field: str
    day: int


def access_tally(entries: tuple[Access, ...]) -> dict:
    """审计记录的两处自查：**缺「为什么看」的比例**，以及**它自己抄进了多少识别码**。

    第二条是本章最反直觉的一处：审计记录的用处是追责，所以它**最不愿意脱敏**
    ——而它恰恰是唯一一份「谁看了谁的全部历史」的表。
    """
    blank = [e for e in entries if not e.purpose.strip()]
    leaks = detect(" ".join(e.target_field for e in entries))
    return {
        "entries": len(entries),
        "blank_purpose": len(blank),
        "blank_rate": len(blank) / len(entries) if entries else 0.0,
        "leaked_hits": len(leaks),
        "actors": len({e.actor for e in entries}),
    }


# ------------------------------------------------------------------ 造出来的样本

#: 一份文本里**同时**出现四种识别码与两个「长得像但其实不是」的号码。
SAMPLE_TEXT = (
    "订单 A 的联系人是 13800138000，邮箱 ops@zhizhou.example，"
    "卡号 4111111111111111，身份证 11010519491231002X；"
    "另两笔订单号 1234567890123456 与 1234567890123452 只是订单号。"
)

#: 十二份请求正文（本章的样例集与 7.4 的 24 条同形：都是写死的）。
SAMPLE_TEXTS: tuple[str, ...] = (
    "帮我查一下 13800138000 的订单",
    "ops@zhizhou.example 说这批货有问题",
    "卡号 4111111111111111 是测试卡，别当真的",
    "订单号 1234567890123456",
    "身份证 11010519491231002X",
    "订单号 1234567890123452",
    "电话 13900139000 打不通",
    "邮箱 support@zhizhou.example 收不到信",
    "卡号 5500005555555559",
    "身份证 110105194912310021",
    "这一条里没有任何识别码，只是一句普通的话",
    "手机号 1X800138000 写错了位数",
)

#: 合成总体：四千个 (尾号 4 位, 生日)。写死的，**不用随机数也不用网络**。
SAMPLE_POPULATION: tuple[tuple[str, str], ...] = tuple(
    (f"{(i * i * 7919) % 10000:04d}", f"19{60 + (i * 13) % 40:02d}-{(i * 7) % 12 + 1:02d}")
    for i in range(4000)
)

#: 十二次访问记录，其中四条没有「为什么看」，三条把手机号抄进了目标字段。
SAMPLE_ACCESS: tuple[Access, ...] = tuple(
    Access(actor=f"ops-{i % 4 + 1}", subject=f"u{1000 + i}",
           purpose="" if i in (2, 5, 7, 11) else "客诉核查",
           target_field=("13800138000" if i in (1, 6, 9) else f"订单 {i}"),
           day=28 + i % 5)
    for i in range(12)
)


#: 「今天」——写死的第 60 天，所有留存读数都相对它算（不用 `time.time()`）。
NOW = 60

#: 六类各三条的创建日。手写的，因为**读数要能拿纸笔复核**：
#: 每类第一条都刚好越过自己的期限（prompt 25／trace 50／cache 58），
#: 而语料那一条在 400 天前创建——它是唯一一条「有期限、没有删除路径」的过期记录。
SAMPLE_CREATED: dict[str, tuple[int, int, int]] = {
    "prompt": (25, 50, 58),
    "trace": (50, 58, 59),
    "cache": (58, 60, 59),
    "billing": (10, 40, 55),
    "corpus": (-400, 20, 45),
    "audit": (30, 44, 57),
}


def sample_records() -> tuple[Record, ...]:
    """十八条例记录：六类各三条，**每一类都刚好有一条越过或逼近自己的期限**。"""
    records: list[Record] = []
    for policy in RETENTION:
        for created in SAMPLE_CREATED[policy.kind]:
            records.append(Record(
                kind=policy.kind,
                subject=f"u{2000 + len(records)}",
                created_day=created,
                text=SAMPLE_TEXTS[len(records) % len(SAMPLE_TEXTS)],
            ))
    return tuple(records)
