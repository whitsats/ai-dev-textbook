"""v4 的工具层：把 v3 手写的 6 个工具改成 `@tool`。

三个对照点先摆在这里：

1. **一份工具定义从哪来。** v3 的每个工具要手写三样：名字、描述、一份 JSON Schema
   （`{"type": "object", "properties": {...}, "required": [...]}`）。v4 只写一个 Python
   函数——名字取自函数名，参数 schema 由**类型提示**推出来，描述取自 **docstring**。
2. **schema 里会少掉什么。** 类型提示能表达类型，表达不了 v3 手写 schema 里的
   `minimum: 1` 与 `additionalProperties: false`；前者要 `Annotated[int, Field(ge=1)]`
   补回来，后者框架默认不生成（见 4.3.3 的逐条对照）。
3. **护栏不在这层。** v3 的 `Tool` 带 `access` 档与 `guard` 钩子，注册表统一执行
   幂等键、体积上限与审计。v4 的工具只剩「读什么、写什么」；那几件事改由中间件承担
   （`app/middleware.py`），因为它要管的是**一次调用**，而不是**一个函数**。

契约一个字没改：六个工具的名字、参数名、必填项、错误话术与 v3 逐条一致。
换框架不换契约，否则第 4 篇的对照失去基准。
"""
from __future__ import annotations

import json
import re
from collections.abc import Sequence
from typing import Annotated, Literal

from langchain_core.tools import BaseTool, ToolException, tool
from pydantic import Field

# 真实项目里这两张表分别来自第 1 篇的 `article` 表与 `article_author` 关系；
# 这里用常量替代，是为了让这一章的工具集**不需要数据库就能跑**（与 v3 同一份夹具）。
OWNER_OF = {42: 7, 43: 9}           # 文章 → 作者；会话用户是 7，所以 43 是别人的

_SECTIONS = [
    "刷新令牌要解决的问题是：访问令牌必须短期有效，但用户不想每次过期都重新登录。",
    "做法一，滑动过期：每次换新令牌时把刷新令牌也一起换掉，旧的那枚立刻作废。"
    "代价是两个标签页同时刷新时，后到的那个拿着已作废的令牌，会被判成盗用；"
    "工程上常给旧令牌留一个很短的宽限窗口。",
    "做法二，黑名单：刷新令牌长期有效，退出或检测到异常时把它的 jti 写进 Redis，"
    "TTL 设为令牌剩余寿命即可。代价是每次刷新多一次查询，黑名单一丢数据撤销就失效。",
    "做法三，版本号：用户表上存 token_version，签发时写进声明，校验时比对；"
    "改密码或强制下线就把版本号加一，该用户所有旧令牌立刻失效。"
    "代价是做不到只踢单台设备。",
    "三种做法可以叠用：滑动过期覆盖常态，版本号覆盖一键下线，"
    "黑名单只留给需要精确到单枚令牌的场景。",
    "边界一：刷新端点必须校验 aud/typ，不能接受访问令牌来换新令牌，"
    "否则等于把短期凭证升级成长期凭证。",
    "边界二：刷新令牌只走 HTTPS，不要放在 URL 里；浏览器端优先 HttpOnly Cookie。",
    "边界三：日志里不要打印令牌本体，只打印 jti 与用户 id。",
]
BODY_OF = {42: "\n\n".join(_SECTIONS * 6)}   # 约 3 千字：读回来会被 2,000 字符的上限截断

# 回给模型的那一段文本的上限（**按序列化后的字符数算**）。与 v3 的 `MAX_RESULT_CHARS` 同值。
MAX_PAYLOAD_CHARS = 2000

# 工具集就是权限面。这两个名字只做分类与展示，真正的拦截在中间件里。
WRITE_TOOLS = frozenset({"create_draft", "publish_article"})


def build_tools(user_id: int, store: dict | None = None,
                names: Sequence[str] | None = None) -> list[BaseTool]:
    """按会话构造工具列表：工具集随用户走（与 v3 的 `build` / `build_for` 同义）。

    `names` 是子代理那一支留下的口子：交接单划定了职责范围之后，
    多看到的每个工具都是一个新的走错路的机会（3.7 的做法在这里同样成立）。
    """
    store = store if store is not None else {}

    @tool(parse_docstring=True)
    def search_article(q: str) -> list[dict]:
        """按关键词检索知舟的历史文章，返回文章 id、标题与标签。

        适用于「有没有讲过 X 的文章」这类按主题找文章的问题；查询词给关键词而不是整句话。
        要正文请拿到 id 后调 read_article。一条都没命中时返回空列表而不是报错。

        Args:
            q: 检索关键词
        """
        if q.startswith("帮我"):                # 合法 string，但整句任务检索不出来
            raise ToolException("检索词像是一整句任务。请给出关键词，例如「刷新令牌」。")
        # **结果必须随查询词变化**。v3 第一版不问查什么都返回同一篇，
        # 于是「换个说法的第二次检索」在观察层看就是「没有新事实」，循环当场判卡死。
        words = [w for w in re.split(r"[\s，,。、；;]+", q) if w]
        hits = [{"article_id": 42, "title": "JWT 刷新令牌怎么做", "tags": ["安全", "后端"]}]
        return [h for h in hits
                if any(w in h["title"] or w in "".join(h["tags"]) for w in words)]

    @tool(parse_docstring=True)
    def read_article(article_id: Annotated[int, Field(ge=1)]) -> dict:
        """按 id 读一篇知舟文章的正文。

        正文超过 2,000 字符会被截断并注明原文长度。适用于已经知道 id、要看内容细节的场景；
        只知道主题时先用 search_article 拿 id。

        Args:
            article_id: 文章 id，正整数
        """
        _own(article_id, user_id)
        return _fit({"article_id": article_id, "title": "JWT 刷新令牌怎么做",
                     "body": BODY_OF.get(article_id, "正文")})

    @tool(parse_docstring=True)
    def articles(mode: Literal["by_tag", "recent", "count"], tag: str | None = None) -> list[dict] | int:
        """按条件列出知舟的文章。

        mode=by_tag 按标签列（需给 tag）、mode=recent 按发布时间倒序取最新 20 条、
        mode=count 只返回总数。用于浏览与计数；要正文请再用 read_article。

        Args:
            mode: 列文章的方式：by_tag / recent / count
            tag: 标签，mode=by_tag 时必填
        """
        if mode == "count":
            return 128
        rows = [{"article_id": 42, "title": "JWT 刷新令牌怎么做", "tags": ["安全", "后端"]}]
        return [r for r in rows if tag in r["tags"]] if mode == "by_tag" else rows

    @tool(parse_docstring=True)
    def get_tags() -> list[str]:
        """返回知舟现有的全部标签。

        用于在按标签检索之前确认标签的确切写法，避免因为猜标签而检索不到。
        """
        return ["安全", "后端", "JWT", "部署"]

    @tool(parse_docstring=True)
    def create_draft(article_id: Annotated[int, Field(ge=1)], body: str) -> dict:
        """为一篇文章创建或覆盖草稿，不改变已发布内容。

        适用于用户要求改稿、润色、另写一版；同一幂等键重复调用只会写一次。

        Args:
            article_id: 文章 id，正整数
            body: 草稿正文
        """
        _own(article_id, user_id)
        store["draft"] = {"article_id": article_id, "body": body, "status": "draft"}
        return dict(store["draft"])

    @tool(parse_docstring=True)
    def publish_article(article_id: Annotated[int, Field(ge=1)]) -> dict:
        """把已有草稿发布上线，**不可逆**。

        只有用户明确要求发布时才调用；调用前必须已有草稿，否则报错。

        Args:
            article_id: 文章 id，正整数
        """
        _own(article_id, user_id)
        if "draft" not in store:
            raise ToolException("还没有草稿可发布。先调 create_draft，发布是不可逆操作。")
        store["draft"]["status"] = "published"
        return dict(store["draft"])

    all_tools: list[BaseTool] = [search_article, read_article, articles, get_tags,
                                 create_draft, publish_article]
    if names is None:
        return all_tools
    by_name = {t.name: t for t in all_tools}
    missing = [n for n in names if n not in by_name]
    if missing:
        raise KeyError(f"交接单要了不存在的工具：{missing}（已注册的：{sorted(by_name)}）")
    return [by_name[n] for n in names]


def _own(article_id: int, user_id: int) -> None:
    """授权钩子：只读参数与作者表，不碰正文。schema 管得了类型，管不了「这是谁的文章」。

    与 v3 的差别只有抛出方式：v3 抛自定义的 `ToolError` 并由注册表转成文本，
    v4 抛框架认识的 `ToolException`——**但框架默认也不会替你接住它**，
    要靠中间件（见 `app/middleware.py` 与 4.3.5 的实测）。
    """
    if article_id not in OWNER_OF:
        raise ToolException(f"文章 {article_id} 不存在。可先用 articles(mode=recent) 取 id。")
    if OWNER_OF[article_id] != user_id:
        raise ToolException(f"文章 {article_id} 不属于你，无权读写。")


def _fit(payload: dict, limit: int = MAX_PAYLOAD_CHARS) -> dict:
    """按**序列化后的长度**限体积：超了就把最长的那个字符串字段裁到刚好放下。

    为什么必须在这一层做：框架把 `dict` 原样序列化后交给模型（实测用的是
    `json.dumps(..., ensure_ascii=False)`），**它不会替你截断**——一份 4,047 字符的
    工具结果会原封不动进上下文。v3 把这个上限放在注册表的 `payload()` 里，
    v4 没有注册表，就落在工具自己身上。

    为什么返回 `dict` 而不是 `str`：上限量的是「模型看到的那一段」，
    所以裁完必须再序列化一次核对；返回 `dict` 则让调用方（与测试）还能按字段取值。
    返回里多一个 `截断` 字段，于是「这次是不是裁过」是可读的，不必靠猜。
    """
    text = json.dumps(payload, ensure_ascii=False)
    if len(text) <= limit:
        return payload
    key = max((k for k, v in payload.items() if isinstance(v, str)),
              key=lambda k: len(payload[k]), default=None)
    if key is None:
        return payload
    original = payload[key]
    note = f"……（已截断，原文 {len(original)} 字）"
    overhead = len(text) - len(original)          # 字段名、引号、其它字段、转义都已算进去
    keep = max(0, limit - overhead - len(note))
    return {**payload, key: original[:keep] + note, "截断": True}


def tool_sheet(tools: Sequence[BaseTool]) -> list[dict]:
    """把工具清单读成一张表：名字、读写档、描述多少字符、整份定义多少字符、必填哪些。

    这张表是 4.3.3 与 v3 对照的原始数据。**定义长度直接决定每次请求的固定开销**——
    六个工具进不了任何缓存，也不随对话变化，所以它是一笔按次计费的常量。
    """
    rows = []
    for t in tools:
        # 取**送给模型的那一份**：与 v3 的 `specs()` 同形（name / description / input_schema），
        # 只是 v3 的那份是手写的，这一份是从类型提示与 docstring 生成的。
        schema = t.tool_call_schema.model_json_schema()
        spec = {"name": t.name, "description": t.description, "input_schema": schema}
        rows.append({
            "name": t.name,
            "access": "write" if t.name in WRITE_TOOLS else "readonly",
            "描述": len(t.description or ""),
            "定义": len(json.dumps(spec, ensure_ascii=False)),
            "必填": list(schema.get("required", [])),
            "schema": schema,
        })
    return rows


def fit_check(payload: dict, limit: int = MAX_PAYLOAD_CHARS) -> int:
    """把 `_fit` 的结果序列化后量一遍：它的长度必须不超过上限。**这是自检用的。**"""
    return len(json.dumps(_fit(payload, limit), ensure_ascii=False))


if __name__ == "__main__":
    rows = tool_sheet(build_tools(user_id=7))
    print("=== 六份工具定义（v4 用类型提示与 docstring 生成）===")
    for r in rows:
        print(f"  {r['name']:<16}{r['access']:<9}描述 {r['描述']:>3} 字符｜"
              f"整份定义 {r['定义']:>4} 字符｜必填 {r['必填']}")
    print(f"  合计 {sum(r['定义'] for r in rows)} 字符")
    print("\n=== 参数：schema 是推出来的，所以约束要靠类型写 ===")
    for name in ("read_article", "articles"):
        schema = next(r["schema"] for r in rows if r["name"] == name)
        print(f"  {name}: {json.dumps(schema, ensure_ascii=False)}")
    print("\n=== 体积上限：工具自己做的事 ===")
    raw = {"article_id": 42, "title": "JWT 刷新令牌怎么做", "body": BODY_OF[42]}
    print(f"  未裁 {len(json.dumps(raw, ensure_ascii=False))} 字符 → "
          f"裁后 {fit_check(raw)} 字符（上限 {MAX_PAYLOAD_CHARS}）")
