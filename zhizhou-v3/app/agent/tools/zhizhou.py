"""把知舟自己的能力变成 6 个工具：4 个只读、2 个写。

三条设计规则都在这里落地：按「谁来验收」分组（读文章 / 列文章 / 起草 / 发布）、
动作用参数而不是新工具（`articles` 的 `mode`）、描述写清「何时用」与「何时不用」。
**幂等键不出现在 schema 里**——它由循环生成，不由模型提供（第 3.5.5 节）。
"""
from __future__ import annotations

import re
from collections.abc import Sequence

from app.agent.tools.registry import READONLY, WRITE, Registry, Tool, ToolError

# 真实项目里这两张表分别来自第 1 篇的 `article` 表与 `article_author` 关系；
# 这里用常量替代，是为了让这一章的工具集**不需要数据库就能跑**。
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
BODY_OF = {42: "\n\n".join(_SECTIONS * 6)}   # 约 3 千字：读回来会被 2,000 字符的上限截断（3.5.6）


def _own(article_id: int, user_id: int) -> None:
    """授权钩子：只读参数与作者表，不碰正文。schema 管得了类型，管不了「这是谁的文章」。"""
    if article_id not in OWNER_OF:
        raise ToolError(f"文章 {article_id} 不存在。可先用 articles(mode=recent) 取 id。")
    if OWNER_OF[article_id] != user_id:
        raise ToolError(f"文章 {article_id} 不属于你，无权读写。")


def build_for(user_id: int, store: dict | None = None, names: Sequence[str] | None = None
              ) -> Registry:
    """按**角色**构造注册表：子代理只看得到自己那一份工具。

    这与 3.5 那条「先看全部工具，再决定用哪个」正好相反，而且不矛盾：
    那条针对的是**一个**要拿主意的代理；这里是「职责已经被交接单划定了」的子代理，
    它多看到的每个工具都是一个新的走错路的机会（而它的上下文窗口本来就很窄）。
    """
    reg = build(user_id, store)
    if names is None:
        return reg
    missing = [n for n in names if n not in reg.tools]
    if missing:
        raise KeyError(f"交接单要了不存在的工具：{missing}（已注册的：{sorted(reg.tools)}）")
    for name in list(reg.tools):
        if name not in names:
            del reg.tools[name]
    return reg


def build(user_id: int, store: dict | None = None) -> Registry:
    """按会话构造注册表：工具集就是权限面，所以它随用户走。"""
    store = store if store is not None else {}

    def search_article(q: str) -> list[dict]:
        if q.startswith("帮我"):                       # 合法 string，但整句任务检索不出来
            raise ToolError("检索词像是一整句任务。请给出关键词，例如「刷新令牌」。")
        # **结果必须随查询词变化**。第一版不问查什么都返回同一篇，于是「换个说法的第二次检索」
        # 在观察层看就是「没有新事实」——循环当场判卡死，而卡住的是夹具不是模型。
        # 3.9 的评测集第一次真机跑就是 0/3，查下来的原因在这里。
        words = [w for w in re.split(r"[\s，,。、；;]+", q) if w]
        hits = [{"article_id": 42, "title": "JWT 刷新令牌怎么做", "tags": ["安全", "后端"]}]
        return [h for h in hits
                if any(w in h["title"] or w in "".join(h["tags"]) for w in words)]

    def read_article(article_id: int) -> dict:
        return {"article_id": article_id, "title": "JWT 刷新令牌怎么做",
                "body": BODY_OF.get(article_id, "正文")}

    def articles(mode: str, tag: str | None = None) -> list[dict] | int:
        if mode == "count":
            return 128
        rows = [{"article_id": 42, "title": "JWT 刷新令牌怎么做", "tags": ["安全", "后端"]}]
        return [r for r in rows if tag in r["tags"]] if mode == "by_tag" else rows

    def get_tags() -> list[str]:
        return ["安全", "后端", "JWT", "部署"]

    def create_draft(article_id: int, body: str) -> dict:
        store["draft"] = {"article_id": article_id, "body": body, "status": "draft"}
        return dict(store["draft"])

    def publish_article(article_id: int) -> dict:
        if "draft" not in store:
            raise ToolError("还没有草稿可发布。先调 create_draft，发布是不可逆操作。")
        store["draft"]["status"] = "published"
        return dict(store["draft"])

    r = Registry()
    r.add(Tool(
        "search_article",
        "按关键词检索知舟的历史文章，返回文章 id、标题与标签。适用于「有没有讲过 X 的文章」"
        "这类按主题找文章的问题；查询词给关键词而不是整句话。要正文请拿到 id 后调 read_article。"
        "一条都没命中时返回空列表而不是报错。",
        {"type": "object", "properties": {"q": {"type": "string", "description": "检索关键词"}},
         "required": ["q"]}, READONLY, search_article))
    r.add(Tool(
        "read_article",
        "按 id 读一篇知舟文章的正文；正文超过 2,000 字会被截断并注明原文长度。适用于已经知道 id、"
        "要看内容细节的场景；只知道主题时先用 search_article 拿 id。",
        {"type": "object", "properties": {"article_id": {"type": "integer", "minimum": 1,
                                                         "description": "文章 id，正整数"}},
         "required": ["article_id"]}, READONLY, read_article,
        guard=lambda article_id: _own(article_id, user_id)))
    r.add(Tool(
        "articles",
        "按条件列出知舟的文章：mode=by_tag 按标签列（需给 tag）、mode=recent 按发布时间倒序取最新 20 条、"
        "mode=count 只返回总数。用于浏览与计数；要正文请再用 read_article。",
        {"type": "object", "properties": {"mode": {"type": "string",
                                                   "enum": ["by_tag", "recent", "count"]},
                                          "tag": {"type": "string", "description": "标签，by_tag 时必填"}},
         "required": ["mode"]}, READONLY, articles))
    r.add(Tool(
        "get_tags",
        "返回知舟现有的全部标签。用于在按标签检索之前确认标签的确切写法，避免因为猜标签而检索不到。",
        {"type": "object", "properties": {}, "required": []}, READONLY, get_tags))
    r.add(Tool(
        "create_draft",
        "为一篇文章创建或覆盖草稿，不改变已发布内容。适用于用户要求改稿、润色、另写一版；"
        "同一幂等键重复调用只会写一次。",
        {"type": "object", "properties": {"article_id": {"type": "integer", "minimum": 1},
                                          "body": {"type": "string", "description": "草稿正文"}},
         "required": ["article_id", "body"]}, WRITE, create_draft,
        guard=lambda article_id, body: _own(article_id, user_id)))
    r.add(Tool(
        "publish_article",
        "把已有草稿发布上线，**不可逆**。只有用户明确要求发布时才调用；调用前必须已有草稿，否则报错。",
        {"type": "object", "properties": {"article_id": {"type": "integer", "minimum": 1}},
         "required": ["article_id"]}, WRITE, publish_article,
        guard=lambda article_id: _own(article_id, user_id)))
    return r


if __name__ == "__main__":
    import json

    reg = build(user_id=7)
    print("=== 一、给模型的工具定义 ===")
    for spec in reg.specs():
        print(f"  {spec['name']:<16}{reg.tools[spec['name']].access:<9}"
              f"{len(json.dumps(spec, ensure_ascii=False))} 字符")

    print("\n=== 二、参数与授权：在调用之前拦下 ===")
    for name, args in [("read_article", {"article_id": 43}),
                       ("read_article", {"article_id": 0}),
                       ("read_article", {"article_id": "42"}),
                       ("articles", {"mode": "latest"})]:
        print(f"  {name}({json.dumps(args, ensure_ascii=False)})  →  {reg.call(name, args).error}")
    print(f"  真正执行过的工具调用：{reg.executed or '（一次都没有）'}")

    print("\n=== 三、写操作的两道闸：权限档与幂等键 ===")
    draft = {"article_id": 42, "body": "改后的正文"}
    print(f"  未授权  →  {reg.call('create_draft', draft).error}")
    print(f"  缺幂等键 →  {reg.call('create_draft', draft, allow_write=True).error}")
    first = reg.call("create_draft", draft, idem="s3-create", allow_write=True)
    again = reg.call("create_draft", draft, idem="s3-create", allow_write=True)
    print(f"  首次执行 →  ok={first.ok}；重跑同键 →  ok={again.ok}")
    print(f"  create_draft 真正被执行的次数：{reg.executed.count('create_draft')}")

    print("\n=== 四、体积上限：读一篇三千字的正文 ===")
    got = reg.call("read_article", {"article_id": 42})
    raw = len(json.dumps(got.data, ensure_ascii=False))
    print(f"  原文 {raw} 字符 → 回给模型 {len(got.payload())} 字符")
    print(f"  结尾：{got.payload()[-30:]}")

    print("\n=== 五、被拒的调用也留痕（审计用，第 3.8 节）===")
    for line in reg.audit:
        print(f"  {line}")
