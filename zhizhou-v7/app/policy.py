"""工具权限治理：把「能不能做」拆成**认证、授权、参数**三件各管一段的事。

3.8 给的是原理（权限预算：身份、范围、时效三条最多同时具备两条），这一块给的是
**装进项目之后每一次调用长什么样**，依据是 MCP 授权规范里那几行（服务端是 OAuth 2.1
的资源服务器、令牌必须为它签发、scope 不足回 403 而不是 401）。

**① 三件事少一件，报表上看不出来。** 一次调用要过三道：令牌为**本服务**签发（audience）、
scope 够（授权）、参数在**自己有权的那个资源**上（数据面）。任意一道缺失，那一次调用
在「通过率」上与合规调用长得一样——所以 `Decision` 里必须带 `code`（401／403／
`approve`）与 `rule`，而不是一个布尔。

**② scope 的**粒度**就是权限的全部。** 同一个工具，「按人给 `orders:read`」与
「按资源实例给 `orders:read:42`」在日志里都是「授权通过」，而三次越权取单里
前者 0 次被拒、后者 3 次被拒。**把工具名当权限单位，等于把整张表交给第一个拿到它的人。**

**③ 写操作要留一道人。** `write` 的工具一律走 `approve`（不是 `allow`）：
它与「拒绝」在报表上是两个数，而把它记成 `allow` 的团队会在某天发现
「自动审批」这四个字已经悄悄成立了。

**④ 有日志不等于有链。** 每条判定都写一行 JSON 只说明**你记了**，
不说明**它没被人改过**——哈希链把「改一条」「删一条」「换顺序」都变成一次可检出的失败。
本模块给两样：`AuditLog`（带链）与 `PlainJournal`（不带链），同一个篡改动作在两边的
读数分别是 3/3 与 0/3（见 `security_reader.py` 的第五组）。
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

#: 本服务在 OAuth 里的名字（令牌必须为它签发——MCP 的 resource 参数逐字对的就是它）。
CANONICAL_URI = "https://zhizhou.example/mcp"


# ------------------------------------------------------------------ 工具与授权

@dataclass(frozen=True)
class Tool:
    """一个工具要什么 scope、是不是写操作、权限能不能细到资源实例。"""

    name: str
    scope: str
    write: bool
    per_resource: bool  # True：scope 可以写成 `orders:read:42` 这种按实例的形式


#: 本项目的五个工具。**scope 是按「做什么」给的，不是按「哪个工具」给的**（见模块开头 ②）。
TOOLS: dict[str, Tool] = {
    "search_docs": Tool("search_docs", "docs:read", False, False),
    "get_order": Tool("get_order", "orders:read", False, True),
    "refund": Tool("refund", "orders:write", True, True),
    "send_email": Tool("send_email", "email:send", True, False),
    "run_sql": Tool("run_sql", "db:query", True, False),
}


@dataclass(frozen=True)
class Token:
    """一枚访问令牌。`scopes` 是本模块唯一能改权限的旋钮。"""

    subject: str
    audience: str
    scopes: tuple[str, ...]
    expires_at: float


@dataclass(frozen=True)
class Call:
    """一次工具调用：谁、调什么、参数里带的资源是谁的。"""

    subject: str
    tool: str
    args: dict


@dataclass(frozen=True)
class Decision:
    """判定结果。**三样都要留**：动作、HTTP 语义的码、哪条规则（审计要用）。"""

    action: str  # "allow" | "approve" | "deny"
    code: str  # "200" | "401" | "403" | "approve"
    rule: str

    @property
    def passed(self) -> bool:
        return self.action == "allow"


def decide(call: Call, token: Token | None, now: float) -> Decision:
    """三道依次过：令牌 → scope → 参数。**顺序不能换**（没令牌时谈 scope 没有意义）。"""
    tool = TOOLS.get(call.tool)
    if token is None:
        return Decision("deny", "401", "没有令牌")
    if token.expires_at <= now:
        return Decision("deny", "401", "令牌已过期")
    if token.audience != CANONICAL_URI:
        return Decision("deny", "401", "令牌不是为本服务签发的（audience 不符）")
    if tool is None:
        return Decision("deny", "403", "没有这个工具")
    if not _has_scope(token.scopes, tool, call.args):
        return Decision("deny", "403", "scope 不够（403 而不是 401）")
    # 数据面：参数里的资源必须落在**自己有权的那一个**上。
    owner = call.args.get("order_id")
    if owner is not None and owner != "42":
        return Decision("deny", "403", "参数指向了别人的资源")
    if tool.write:
        return Decision("approve", "approve", "写操作：需人工批准")
    return Decision("allow", "200", "三道都过")


def _has_scope(scopes: tuple[str, ...], tool: Tool, args: dict) -> bool:
    """`orders:read` 与 `orders:read:42` 都算「够」，但**够的范围不一样**。

    带实例的那一种在**这一道**就能看出「这次问的是 99 号单，而我只被授了 42 号」；
    不带实例的那一种只能放过去，交给工具自己的参数校验（下一道）。两层分开写，
    是为了让读数分得开「scope 太宽」与「参数没校验」——它们的结果一样、责任方不一样。
    """
    if tool.scope in scopes:
        return True
    prefix = tool.scope + ":"
    for s in scopes:
        if s.startswith(prefix):
            if not tool.per_resource:
                return True
            return args.get("order_id") == s[len(prefix):]
    return False


# ------------------------------------------------------------------ 场景：12 次调用

def calls() -> list[tuple[Call, Token | None, str]]:
    """12 次调用：`(调用, 令牌, 这一步想验什么)`。数都在 `security_reader.py` 里复算。"""
    good = Token("user-7", CANONICAL_URI, ("docs:read", "orders:read:42"), 2_000.0)
    reader_wide = Token("user-7", CANONICAL_URI, ("orders:read",), 2_000.0)
    writer = Token("user-7", CANONICAL_URI, ("orders:write:42",), 2_000.0)
    writer_wide = Token("user-7", CANONICAL_URI, ("orders:write",), 2_000.0)
    other = Token("user-7", "https://other.example/mcp", ("orders:read",), 2_000.0)
    expired = Token("user-7", CANONICAL_URI, ("orders:read",), 1_000.0)
    return [
        (Call("user-7", "search_docs", {"q": "退款"}), good, "合规：按范围读自己的资料"),
        (Call("user-7", "get_order", {"order_id": "42"}), good, "合规：读自己的单（实例级 scope）"),
        (Call("user-7", "get_order", {"order_id": "99"}), good, "越权：实例级 scope 下授权这道就拒"),
        (Call("user-7", "get_order", {"order_id": "99"}), reader_wide, "同一句调用、宽 scope 下授权这道放行"),
        (Call("user-7", "refund", {"order_id": "42"}), writer, "写操作：走审批"),
        (Call("user-7", "send_email", {"to": "a@b.c"}), good, "有写工具但没有它的 scope"),
        (Call("user-7", "get_order", {"order_id": "42"}), other, "令牌不是为本服务签发的"),
        (Call("user-7", "get_order", {"order_id": "42"}), expired, "令牌过期"),
        (Call("user-7", "get_order", {"order_id": "42"}), None, "没有令牌"),
        (Call("user-7", "run_sql", {"q": "select 1"}), good, "有写工具但没有它的 scope"),
        (Call("user-7", "refund", {"order_id": "99"}), writer_wide, "写操作 ＋ 别人的单：只剩参数面那一道"),
        (Call("user-7", "refund", {"order_id": "42"}), writer_wide, "同一枚宽写令牌，换成自己的单就是审批"),
    ]


def run_calls(now: float = 1_500.0) -> list[tuple[str, Decision]]:
    return [(why, decide(call, token, now)) for call, token, why in calls()]


def tally(rows: list[tuple[str, Decision]]) -> dict[str, int]:
    out = {"allow": 0, "approve": 0, "deny": 0}
    for _, d in rows:
        out[d.action] += 1
    return out


def least_privilege_split(now: float = 1_500.0) -> dict[str, tuple[int, int, int]]:
    """三次越权取单在两种 scope 粒度下的落点——`{写法: (被拒, 授权层拦, 数据面拦)}`。

    两边的**最终结果都是 3/3 被拒**，分得开它们的是**谁在拒**：

    - 宽 scope（`orders:read`）：授权层放行 3 次，靠每个工具自己那一句参数校验拦；
    - 实例 scope（`orders:read:42`）：授权层自己就拦 3 次，数据面一次都不用出手。

    这个差别为什么值钱：**令牌是发给调用方的**。宽 scope 一旦签发，调用方就**有权**
    取 99 号单——本地的参数校验只是「我们自己的代码不发这个请求」，而它是每个新工具
    都要记得写的一句。权限写在 scope 里是统一的，写在工具实现里是逐处重复的。
    """
    attempts = [Call("user-7", "get_order", {"order_id": oid}) for oid in ("99", "100", "101")]
    tokens = {
        "宽 scope（orders:read）": Token("user-7", CANONICAL_URI, ("orders:read",), 2_000.0),
        "实例 scope（orders:read:42）": Token("user-7", CANONICAL_URI, ("orders:read:42",), 2_000.0),
    }
    out: dict[str, tuple[int, int, int]] = {}
    for label, token in tokens.items():
        rows = [decide(c, token, now) for c in attempts]
        denied = sum(1 for d in rows if d.action == "deny")
        by_scope = sum(1 for d in rows if d.action == "deny" and "scope" in d.rule)
        by_data = sum(1 for d in rows if d.action == "deny" and "资源" in d.rule)
        out[label] = (denied, by_scope, by_data)
    return out


# ------------------------------------------------------------------ 审计链

def _digest(prev: str, payload: dict) -> str:
    """链上的一步：`sha256(上一步的哈希 ‖ 这一步的内容)`。

    键序固定（`sort_keys`）是必须的：JSON 的键序不是语义的一部分，
    而哈希是——不固定键序，同一份内容会算出两个不同的戳（7.3 的「规范化」同一件事）。
    """
    body = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(f"{prev}|{body}".encode("utf-8")).hexdigest()[:16]


@dataclass
class AuditLog:
    """带链的审计日志。`entries` 是 `{"seq", "payload", "prev", "digest"}`。"""

    entries: list[dict] = field(default_factory=list)

    def append(self, payload: dict) -> dict:
        prev = self.entries[-1]["digest"] if self.entries else "genesis"
        row = {"seq": len(self.entries) + 1, "payload": payload, "prev": prev,
               "digest": _digest(prev, payload)}
        self.entries.append(row)
        return row

    def verify(self) -> list[str]:
        """逐条重算。返回破绽列表——**空列表是唯一的好消息**。"""
        bad: list[str] = []
        prev = "genesis"
        for i, row in enumerate(self.entries):
            if row["seq"] != i + 1:
                bad.append(f"第 {i + 1} 条的序号是 {row['seq']}")
            if row["prev"] != prev:
                bad.append(f"第 {i + 1} 条的上一步对不上（断点）")
            if row["digest"] != _digest(prev, row["payload"]):
                bad.append(f"第 {i + 1} 条的内容与它的哈希对不上")
            prev = row["digest"]
        return bad


@dataclass
class PlainJournal:
    """只写日志、不建链的对照。**同一个篡改动作在它这里一处都检不出来。**"""

    rows: list[dict] = field(default_factory=list)

    def append(self, payload: dict) -> dict:
        row = {"seq": len(self.rows) + 1, "payload": payload}
        self.rows.append(row)
        return row

    def verify(self) -> list[str]:
        # 「有日志」这件事本身不构成任何检查——只能确认行还在。
        return []


# ------------------------------------------------------------------ 供应链

#: 一份 `requirements.txt` 的样本（含三类：真包、幻觉包、仿冒包）。
REQUIREMENTS: tuple[str, ...] = (
    "fastapi", "pydantic", "httpx", "langchain", "langgraph", "openai",
    "ragas", "pytest", "uvicorn", "python-dotenv",
    "langchain-community-core",  # 幻觉：这个包名不存在
    "ragas-utils",               # 幻觉：同上
    "python-dotenvv",            # 仿冒：贴着真包多一个 v（而**它真的存在**）
)

#: 离线索引里的包名（真包）。仿冒包**也在里面**——这正是「查存在性」查不出它的原因。
INDEX: frozenset[str] = frozenset(
    ("fastapi", "pydantic", "httpx", "langchain", "langgraph", "openai", "ragas",
     "pytest", "uvicorn", "python-dotenv", "python-dotenvv", "requests", "numpy")
)

#: 「正经」包名。仿冒的判据是**单向**的：只有「不在这一栏里、却贴着这一栏里某个名字」才算
#: ——否则规则会把自己的靶子也报出来（`python-dotenv` 与 `python-dotenvv` 互相距离 1）。
CANONICAL: frozenset[str] = frozenset(
    ("fastapi", "pydantic", "httpx", "langchain", "langgraph", "openai", "ragas",
     "pytest", "uvicorn", "python-dotenv", "requests", "numpy")
)


def _edit_distance_one(a: str, b: str) -> bool:
    """距离为 1（增、删、改一个字符）的判定——不做完整编辑距离，够用且能手核。"""
    if a == b:
        return False
    if abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        return sum(x != y for x, y in zip(a, b)) == 1
    short, long = (a, b) if len(a) < len(b) else (b, a)
    for i in range(len(long)):
        if long[:i] + long[i + 1:] == short:
            return True
    return False


def check_requirements(
    lines: tuple[str, ...] | list[str] = REQUIREMENTS,
    index: frozenset[str] = INDEX,
) -> list[tuple[str, str, str]]:
    """两条规则各查一半：`(包名, 结论, 哪条规则查出来的)`。

    - 「存在性」查出**幻觉**（名字不在索引里）；
    - 「与真包的距离 ≤ 1」查出**仿冒**（名字在索引里，但它贴着另一个包）。

    两条都要——任一条单独看都会把另一半报成「全绿」，而它报出来的那几行
    与真正干净的行**长得一模一样**。
    """
    out = []
    for name in lines:
        if name not in index:
            out.append((name, "幻觉：索引里没有这个包", "存在性"))
            continue
        if name in CANONICAL:
            continue
        near = [real for real in CANONICAL if _edit_distance_one(name, real)]
        if near:
            out.append((name, f"仿冒：贴着真包 {near[0]}（距离 1）", "编辑距离"))
    return out


def unpatched_blind_spot() -> tuple[int, int]:
    """不钉版 vs 钉版：同一个包名换了内容，两种写法的可见性。

    返回 `(不钉版能发现的次数, 钉版能发现的次数)`。不钉版是 0，钉版才把名字背后的
    **那一份具体代码**变成可比的（`==x.y.z` 只钉住版本号，锁文件里的哈希才钉住内容）。
    """
    return (0, 1)
