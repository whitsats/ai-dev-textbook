# tests/test_agent_tools.py —— 不需要密钥、不需要网络：工具契约、四条护栏、两条路径的读数
"""这一份测的是 4.3 的结论，**全部不需要模型服务商**。

需要真实模型的那几件事（工具描述够不够模型判断、真机词元）不在这里假装通过——
它们由 `scripts/agent_tools.py --real` 报读数（**离线当门、真机报数**，从 3.9 起的做法）。

一条纪律：凡是本章断言了「框架会怎样」的地方，这里都必须有一份**可重复跑的**证据。
框架的默认行为是最容易凭印象写错的一类断言（本章就抓到三条：工具异常抛穿、
`"42"` 被静默转成 `42`、`when` 谓词在 1.3.2 上静默失效）。
"""
from __future__ import annotations

import importlib.metadata as md
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from contextlib import contextmanager

from langchain.agents.middleware import HumanInTheLoopMiddleware, ModelCallLimitMiddleware
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import ToolException, tool
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from app.agent import (DEFAULT_RECURSION_LIMIT, agent_config, create_zhizhou, describe_agent,
                       run_agent, run_handwritten)
from app.middleware import bucket_error, guard_tools, idem_key
from app.scripted import ScriptedModel, final, tool_call
from app.tools import MAX_PAYLOAD_CHARS, _fit, build_tools, tool_sheet

TOOLS_NAMES = ["search_article", "read_article", "articles", "get_tags",
               "create_draft", "publish_article"]


@contextmanager
def raises(exc_type, match: str = ""):
    """一份不依赖 pytest 的「应当抛异常」。

    本书的一致性门是**直接调测试函数**的（本机不装 pytest 也能跑），
    所以测试文件不能引 pytest——那会让「没装 pytest」直接变成「测试跑不了」。
    """
    try:
        yield
    except exc_type as exc:
        if match and match not in str(exc):
            raise AssertionError(f"异常消息里没有 {match!r}：{exc}") from exc
    else:
        raise AssertionError(f"应当抛 {exc_type.__name__}，但没有")


def sheet() -> dict:
    return {r["name"]: r for r in tool_sheet(build_tools(user_id=7))}


# ---------------------------------------------------------------- 一、工具定义

def test_六个工具的名字与必填与_v3_逐条一致() -> None:
    rows = sheet()
    assert list(rows) == TOOLS_NAMES
    assert rows["search_article"]["必填"] == ["q"]
    assert rows["read_article"]["必填"] == ["article_id"]
    assert rows["get_tags"]["必填"] == []
    assert rows["create_draft"]["必填"] == ["article_id", "body"]


def test_类型提示里的约束会进_schema_且_Optional_与_Literal_各自成立() -> None:
    rows = sheet()
    article = rows["read_article"]["schema"]["properties"]["article_id"]
    assert article["type"] == "integer" and article["minimum"] == 1     # Annotated[Field(ge=1)]
    assert article["description"] == "文章 id，正整数"                  # 来自 docstring 的 Args
    mode = rows["articles"]["schema"]["properties"]["mode"]
    assert mode["enum"] == ["by_tag", "recent", "count"]                # Literal → enum
    tag = rows["articles"]["schema"]["properties"]["tag"]
    assert "default" in tag and tag["default"] is None                  # Optional[str] = None
    assert rows["articles"]["必填"] == ["mode"]                         # 选填不进 required


def test_默认的_parse_docstring_会把_Args_段整段漏进描述里() -> None:
    """对照实验：差异只有两行（`parse_docstring=True`），后果是**每轮请求都多一段**。

    这是 4.3.2 的一条读数：不写 `parse_docstring=True` 时，
    `Args:` 那段既是描述的一部分、又**没有**变成参数自己的 `description`——
    模型拿到的是一段散文，而不是一份带说明的 schema。
    """
    @tool
    def naive(query: str) -> str:
        """搜一下。

        Args:
            query: 关键词
        """
        return query

    assert "Args:" in (naive.description or "")
    assert "description" not in naive.tool_call_schema.model_json_schema()["properties"]["query"]


def test_框架生成的定义带着_Pydantic_自动加的_title字段() -> None:
    """`title` 是白送的开销，但它是可量的：六份定义里占 280 字符（4.3.2 的读数）。"""
    import json
    specs = [{"name": t.name, "description": t.description,
              "input_schema": t.tool_call_schema.model_json_schema()}
             for t in build_tools(user_id=7)]
    with_title = sum(len(json.dumps(s, ensure_ascii=False)) for s in specs)
    assert with_title > 2500
    assert any("title" in t.tool_call_schema.model_json_schema() for t in build_tools(user_id=7))


# ---------------------------------------------------------------- 二、参数与授权

def test_越权在工具体里被拦下并抛框架认识的_ToolException() -> None:
    tools = {t.name: t for t in build_tools(user_id=7)}
    tools["read_article"].invoke({"article_id": 42})              # 自己的文章：通过
    with raises(ToolException, match="不属于你"):
        tools["read_article"].invoke({"article_id": 43})          # 别人的文章：拦下
    with raises(ToolException, match="不存在"):
        tools["read_article"].invoke({"article_id": 99})


def test_类型不严_字符串_42_被静默纠正而不是被拒绝() -> None:
    """**与 v3 相反的一条**：v3 的手写校验判「类型错」，v4 的 Pydantic 把它转成了 42。

    宽进有利于模型（少一次失败重试），但它意味着**不能靠类型来挡参数**；
    真正的拦截只能写在工具体里（授权、范围、幂等）。
    """
    tools = {t.name: t for t in build_tools(user_id=7)}
    out = tools["read_article"].invoke({"article_id": "42"})
    assert out["article_id"] == 42


def test_体积上限按序列化后的字符数算并且裁过的会被标出来() -> None:
    from app.tools import BODY_OF
    big = {"article_id": 42, "title": "JWT 刷新令牌怎么做", "body": BODY_OF[42]}
    import json
    assert len(json.dumps(big, ensure_ascii=False)) > MAX_PAYLOAD_CHARS      # 先确认它真的超了
    fitted = _fit(big)
    assert fitted["截断"] is True
    assert len(json.dumps(fitted, ensure_ascii=False)) <= MAX_PAYLOAD_CHARS
    small = {"article_id": 42, "title": "短"}
    assert "截断" not in _fit(small)


# ---------------------------------------------------------------- 三、四条护栏

def test_框架默认不接住工具异常_没有中间件时整轮崩掉() -> None:
    """**这是本章最该记住的一条默认行为。** 越权（调用对了但做不成）会抛穿整轮。"""
    script = [tool_call("read_article", {"article_id": 43}, 50), final("收工", 20)]
    agent = create_zhizhou(ScriptedModel(script=list(script)), build_tools(user_id=7))
    stats = run_agent(agent, "试", config=agent_config())
    assert "ToolException" in stats.crashed and stats.answer == ""


def test_框架自己接得住参数形状错误() -> None:
    """缺必填、工具名不存在、枚举越界：框架把它们变成 status=error 的工具消息。"""
    cases = [("read_article", {}), ("no_such_tool", {"x": 1}), ("articles", {"mode": "latest"})]
    for name, args in cases:
        script = [tool_call(name, args, 50), final("收工", 20)]
        agent = create_zhizhou(ScriptedModel(script=list(script)), build_tools(user_id=7))
        stats = run_agent(agent, "试", config=agent_config())
        assert stats.crashed == "", (name, stats.crashed)
        assert stats.tool_results[0]["status"] == "error"


def test_中间件把异常收成可读文本并填上工具名() -> None:
    script = [tool_call("read_article", {"article_id": 43}, 50), final("收工", 20)]
    audit: list[dict] = []
    agent = create_zhizhou(ScriptedModel(script=list(script)), build_tools(user_id=7),
                           middleware=[guard_tools(run_id="t", audit=audit)])
    stats = run_agent(agent, "试", config=agent_config())
    first = stats.tool_results[0]
    assert first["status"] == "error" and first["name"] == "read_article"
    assert "不属于你" in first["content"] and stats.answer == "收工"
    assert audit[0]["error_type"] == "越权"


def test_审批闸默认拒绝且被拒的调用也留痕() -> None:
    script = [tool_call("create_draft", {"article_id": 42, "body": "改后的"}, 60),
              tool_call("publish_article", {"article_id": 42}, 60), final("好了", 20)]
    audit: list[dict] = []
    agent = create_zhizhou(ScriptedModel(script=list(script)), build_tools(user_id=7),
                           middleware=[guard_tools(run_id="t", audit=audit)])
    stats = run_agent(agent, "改完就发布", config=agent_config())
    assert [r["name"] for r in stats.tool_results] == ["create_draft", "publish_article"]
    assert stats.tool_results[1]["status"] == "error"
    assert "未获人工确认" in [a.get("error_type") for a in audit]


def test_审批通过后发布真的执行() -> None:
    script = [tool_call("create_draft", {"article_id": 42, "body": "改后的"}, 60),
              tool_call("publish_article", {"article_id": 42}, 60), final("好了", 20)]
    store: dict = {}
    tools = build_tools(user_id=7, store=store)
    agent = create_zhizhou(ScriptedModel(script=list(script)), tools,
                           middleware=[guard_tools(run_id="t", approve=lambda n, a: True)])
    stats = run_agent(agent, "改完就发布", config=agent_config())
    assert all(r["status"] == "success" for r in stats.tool_results)
    assert store["draft"]["status"] == "published"


def test_幂等键带上_run_id_于是同一任务只执行一次() -> None:
    assert idem_key("A", "create_draft", {"x": 1}) != idem_key("B", "create_draft", {"x": 1})
    script = [tool_call("create_draft", {"article_id": 42, "body": "同一份"}, 60),
              tool_call("create_draft", {"article_id": 42, "body": "同一份"}, 60),
              final("写完了", 20)]
    audit: list[dict] = []
    agent = create_zhizhou(ScriptedModel(script=list(script)), build_tools(user_id=7),
                           middleware=[guard_tools(run_id="A", audit=audit)])
    stats = run_agent(agent, "写两次一样的草稿", config=agent_config())
    assert sum(1 for a in audit if a.get("repeated")) == 1
    assert "幂等键命中" in stats.tool_results[1]["content"]


def test_错误分档的取值集合是有限的() -> None:
    assert bucket_error("文章 43 不属于你，无权读写。") == "越权"
    assert bucket_error("缺少幂等键") == "缺幂等键"
    assert bucket_error("随便什么别的") == "工具执行失败"


# ---------------------------------------------------------------- 四、两条路径

def _happy_script() -> list[dict]:
    return [tool_call("get_tags", {}, 160), tool_call("read_article", {"article_id": 42}, 900),
            tool_call("create_draft", {"article_id": 42, "body": "改后的"}, 220),
            final("标签四个，草稿写好了。", 180)]


def test_两条路径在同一个剧本上读数完全一致() -> None:
    """差的是「循环归谁」，不是「循环怎么走」。**这一条是 4.3.6 那张表的地基。**"""
    handwritten = run_handwritten(ScriptedModel(script=_happy_script()), build_tools(user_id=7),
                                  "看看标签再读一篇", run_id="t")
    agent = create_zhizhou(ScriptedModel(script=_happy_script()), build_tools(user_id=7),
                           middleware=[guard_tools(run_id="t")])
    framework = run_agent(agent, "看看标签再读一篇", config=agent_config())
    for field in ("model_calls", "super_steps", "tool_calls", "tokens"):
        assert getattr(handwritten, field) == getattr(framework, field), field
    assert handwritten.super_steps == 7        # 4 次模型调用 ＋ 3 个工具节点
    assert framework.stop == "模型给出最终答案"


def test_recursion_limit_数的是_super_step_而不是模型调用次数() -> None:
    """实测（langgraph 1.2.2）：limit=6 → 只走了 **3 次模型调用**。

    `recursion_limit` 数的是 super-step；一次带工具调用的往返占 2 步（模型节点 ＋ 工具节点），
    所以把它当「步数」读会高估一倍。四个取值的实测：6 → 3、8 → 4、10 → 5。
    """
    loop = [tool_call("get_tags", {}, 50)]      # 剧本走完就重复最后一格 → 死循环
    agent = create_zhizhou(ScriptedModel(script=list(loop)), build_tools(user_id=7))
    stats = run_agent(agent, "死循环", config=agent_config(recursion_limit=6))
    assert "GraphRecursionError" in stats.crashed
    assert stats.model_calls == 3
    assert stats.super_steps == 2 * stats.model_calls


def test_剧本模型每轮换一个_tool_call_id() -> None:
    """回归守：复用同一个 id 会让框架报一个完全不指向真因的 `KeyError: 'model'`。"""
    from app.scripted import ScriptedModel as SM
    model = SM(script=[tool_call("get_tags", {}, 10)])
    ids = []
    for _ in range(3):
        reply = model.invoke([AIMessage("hi")])
        ids.append(reply.tool_calls[0]["id"])
    assert len(set(ids)) == 3


def test_两个上限谁先撞到_决定你拿到异常还是拿到一句话() -> None:
    """**本章第二条最重要的默认行为。**

    手写版撞上限时会**多问一次模型要结论**（收口）；框架的限额中间件是「停下 ＋ 留一句话」。
    但实测发现：那句话能不能拿到，取决于 `recursion_limit` 留了多少余量——
    同样是 `run_limit=3`，`recursion_limit=8`（本书的默认）**撞的是图递归上限、空手回来**，
    提到 20 才拿到「Model call limits exceeded: run limit (3/3)」。
    两个闸门都装了，但**没有对过账**——与 3.10 的「写了 ≠ 接上了」同一族。
    """
    loop = [tool_call("get_tags", {}, 50)]

    def run(limit: int):
        agent = create_zhizhou(ScriptedModel(script=list(loop)), build_tools(user_id=7),
                               middleware=[ModelCallLimitMiddleware(run_limit=3)])
        return run_agent(agent, "死循环", config=agent_config(recursion_limit=limit))

    tight = run(DEFAULT_RECURSION_LIMIT)
    assert "GraphRecursionError" in tight.crashed and tight.answer == ""
    loose = run(20)
    assert loose.crashed == "" and "Model call limits exceeded" in loose.answer


def test_图的节点与边是读出来的() -> None:
    agent = create_zhizhou(ScriptedModel(script=[final("好", 10)]), build_tools(user_id=7))
    shape = describe_agent(agent)
    assert shape["节点"] == ["__end__", "__start__", "model", "tools"]
    assert "tools→model（条件）" in shape["边"]


# ---------------------------------------------------------------- 五、审批的两种做法

def _hitl_agent(interrupt_on: dict, script: list[dict]):
    return create_zhizhou(ScriptedModel(script=list(script)), build_tools(user_id=7),
                          middleware=[HumanInTheLoopMiddleware(interrupt_on=interrupt_on)],
                          checkpointer=InMemorySaver())


def test_中断发生在执行之前_工具体一次都没执行() -> None:
    store: dict = {}
    script = [tool_call("create_draft", {"article_id": 42, "body": "改后的"}, 60),
              tool_call("publish_article", {"article_id": 42}, 60), final("好了", 20)]
    agent = create_zhizhou(ScriptedModel(script=list(script)),
                           build_tools(user_id=7, store=store),
                           middleware=[HumanInTheLoopMiddleware(
                               interrupt_on={"publish_article": True})],
                           checkpointer=InMemorySaver())
    config = {"configurable": {"thread_id": "t-hitl"}}
    out = agent.invoke({"messages": [{"role": "user", "content": "改完就发布"}]},
                       config=config, version="v2")
    assert out.interrupts, "应当中断"
    assert out.interrupts[0].value["action_requests"][0]["name"] == "publish_article"
    assert store["draft"]["status"] == "draft"           # **关键**：中断前发布没发生
    resumed = agent.invoke(Command(resume={"decisions": [{"type": "approve"}]}),
                           config=config, version="v2")
    assert store["draft"]["status"] == "published"
    assert resumed.value["messages"][-1].content == "好了"


def test_拒绝把人的话原样回给模型_而工具不执行() -> None:
    store: dict = {}
    script = [tool_call("create_draft", {"article_id": 42, "body": "改后的"}, 60),
              tool_call("publish_article", {"article_id": 42}, 60), final("先不发", 20)]
    agent = create_zhizhou(ScriptedModel(script=list(script)),
                           build_tools(user_id=7, store=store),
                           middleware=[HumanInTheLoopMiddleware(
                               interrupt_on={"publish_article": True})],
                           checkpointer=InMemorySaver())
    config = {"configurable": {"thread_id": "t-reject"}}
    agent.invoke({"messages": [{"role": "user", "content": "改完就发布"}]},
                 config=config, version="v2")
    resumed = agent.invoke(
        Command(resume={"decisions": [{"type": "reject", "message": "用户说先别发"}]}),
        config=config, version="v2")
    tool_messages = [m for m in resumed.value["messages"] if isinstance(m, ToolMessage)]
    assert tool_messages[-1].content == "用户说先别发"
    assert store["draft"]["status"] == "draft"


def test_when_谓词在小版本边界上静默不生效_按实测断言() -> None:
    """文档写「需要 langchain>=1.3.3」。本机是 1.3.2——它**不报错**，只是不生效。

    这条测试按版本分支断言：升级到 1.3.3 之后，同一份测试会自己转到另一支，
    于是「版本边界上发生了什么」变回一条可查的读数，而不是一句传闻。
    """
    script = [tool_call("create_draft", {"article_id": 42, "body": "改后的"}, 60),
              tool_call("publish_article", {"article_id": 42}, 60), final("好了", 20)]
    version = md.version("langchain")
    supported = tuple(int(x) for x in version.split(".")[:3]) >= (1, 3, 3)
    for predicate in (True, False):
        agent = _hitl_agent({"publish_article": {"when": lambda req, p=predicate: p}}, script)
        out = agent.invoke({"messages": [{"role": "user", "content": "改完就发布"}]},
                           config={"configurable": {"thread_id": f"w-{predicate}"}},
                           version="v2")
        assert bool(out.interrupts) is (supported and predicate), (version, predicate)


def test_两个默认值都是显式的_而不是框架的() -> None:
    """本书给出的上限必须写在自己的代码里：`recursion_limit` 框架默认 9999。"""
    assert DEFAULT_RECURSION_LIMIT == 8
    assert agent_config()["recursion_limit"] == DEFAULT_RECURSION_LIMIT
    assert agent_config(thread_id="x")["configurable"] == {"thread_id": "x"}
