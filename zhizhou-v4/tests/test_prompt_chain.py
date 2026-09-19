# tests/test_prompt_chain.py —— 不需要密钥、不需要网络：模板契约、链的形状、解析与失败
"""这一份测的是 4.2 的六条结论，**全部不需要模型**。

需要模型的那几件事（结构化输出真的返回 Pydantic 实例、真机账）不在这里假装通过——
它们由 `scripts/prompt_chain.py` 的真机那一路报读数（离线当门、真机报数）。
"""
from __future__ import annotations

import itertools
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda
from langchain_openai import ChatOpenAI

from app.chains import (
    CLIP, clip, clipped_chain, describe, draft_chain, parallel_chain, structured_chain,
    summary_chain, tool_call_chain, with_passthrough,
)
from app.prompts import CHAT_PROMPT, DRAFT_PROMPT, SUMMARY_PROMPT
from app.schemas import ArticleSummary, Tag


def fake(replies: list[str]):
    return GenericFakeChatModel(messages=itertools.cycle([AIMessage(r) for r in replies]))


def stub_model():
    """不联网的模型对象：建链只拼结构，端口填一个没人听的地址也读得动 schema。"""
    return ChatOpenAI(model="shape-only", api_key="shape-only", base_url="http://127.0.0.1:1/v1")


# ---------------------------------------------------------------- 模板契约

def test_必填变量是契约且少样本的示例不算变量() -> None:
    assert SUMMARY_PROMPT.input_variables == ["article"]
    # 示例是数据：进模板之后固定了，所以 `input` / `output` 不是变量
    assert DRAFT_PROMPT.input_variables == ["request"]
    assert "input" not in DRAFT_PROMPT.input_variables


def test_缺必填变量在渲染时就抛() -> None:
    try:
        SUMMARY_PROMPT.format_messages()
        raise AssertionError("缺 article 必须在渲染时抛 KeyError，而不是等模型答非所问")
    except KeyError as exc:
        assert "article" in str(exc)


def test_历史是选填的所以忘了传不会报错() -> None:
    """这一条是本章最该记住的行为：**变量在 `optional_variables` 里，缺了不报错。**"""
    assert CHAT_PROMPT.input_variables == ["question"]
    assert getattr(CHAT_PROMPT, "optional_variables", []) == ["history"]

    without = CHAT_PROMPT.format_messages(question="在吗")
    with_history = CHAT_PROMPT.format_messages(
        history=[HumanMessage("旧问题"), AIMessage("旧回答")], question="在吗")
    assert len(without) == 2 and len(with_history) == 4
    assert without[0].content == with_history[0].content       # 系统提示两边一样


def test_少样本渲染成成对的消息而不是一段散文() -> None:
    messages = DRAFT_PROMPT.format_messages(request="给文章 3 打标签")
    assert [type(m).__name__ for m in messages] == [
        "SystemMessage", "HumanMessage", "AIMessage", "HumanMessage", "AIMessage", "HumanMessage"]
    assert messages[-1].content == "给文章 3 打标签"


# ---------------------------------------------------------------- 裁剪

def test_裁剪是纯函数且两种入参都吃() -> None:
    long_one = clip("x" * 1500)
    assert len(long_one["article"]) == 1200 and long_one["clipped"] is True
    assert clip("短正文") == {"article": "短正文", "clipped": False}
    assert clip({"article": "y" * 50})["clipped"] is False
    assert clip("") == {"article": "", "clipped": False}        # 空输入不许炸


def test_普通函数要包一次才能进链() -> None:
    assert isinstance(CLIP, RunnableLambda.__mro__[1])          # Runnable
    assert isinstance(CLIP, RunnableLambda)


# ---------------------------------------------------------------- 链的形状

def test_链的输入由第一环决定() -> None:
    stub = stub_model()
    assert describe(summary_chain(stub))["输入"] == "{article}"
    assert describe(clipped_chain(stub))["输入"] == "{root}"     # 前置是一把 str 进、dict 出
    assert describe(parallel_chain(stub))["输入"] == "{article, request}"


def test_结构化链的输出schema就是契约的字段() -> None:
    shape = describe(structured_chain(stub_model()))
    assert shape["输出"] == "{summary, tags}"
    assert set(ArticleSummary.model_fields) == {"summary", "tags"}
    assert set(Tag.__args__) == {"后端", "前端", "数据库", "AI", "运维"}


def test_保留原文时输出多出三个字段() -> None:
    """`include_raw=True` 的契约：raw / parsed / parsing_error——失败因此能被记下来。"""
    shape = describe(tool_call_chain(stub_model(), include_raw=True))
    assert shape["输出"] == "{parsed, parsing_error, raw, root}"


def test_建链不发请求() -> None:
    """端口上没人监听也读得到 schema：**需要网络的是 invoke，不是建链**。"""
    chain = structured_chain(stub_model())
    assert describe(chain)["步数"] >= 4
    assert chain.get_graph().nodes                                # 图上确实有节点
    assert all(len(n) == 32 for n in chain.get_graph().nodes)      # 但它们是随机 id


def test_带上入参让链自己成为可复盘的记录() -> None:
    shape = describe(with_passthrough(stub_model()))
    assert shape["输出"] == "{article, result}"


# ---------------------------------------------------------------- 解析失败

def test_解析器坏输入抛异常而结构化的三个字段不抛() -> None:
    broken = (ChatPromptTemplate.from_messages([("human", "{q}")])
              | RunnableLambda(lambda _p: AIMessage("我觉得应该调 get_tags 吧。"))
              | JsonOutputParser())
    try:
        broken.invoke({"q": "x"})
        raise AssertionError("不是 JSON 时 JsonOutputParser 必须抛")
    except Exception as exc:                                     # noqa: BLE001
        assert type(exc).__name__ == "OutputParserException"


def test_好输入时两种解析拿到同一种结构() -> None:
    model = fake(['{"tool": "get_tags", "args": {"article_id": 12}}'])
    assert draft_chain(model).invoke({"request": "x"}) == {"tool": "get_tags", "args": {"article_id": 12}}
    # StrOutputParser 的输出在 1.x 里是 `str` 的子类（TextAccessor），所以 str 的用法都成立
    text = summary_chain(model).invoke({"article": "正文"})
    assert isinstance(text, str) and text.startswith("{")


# ---------------------------------------------------------------- 一次跑一批

def test_batch一次跑多条() -> None:
    model = fake(['{"tool": "get_tags", "args": {"article_id": 12}}'])
    out = draft_chain(model).batch([{"request": "a"}, {"request": "b"}])
    assert len(out) == 2 and all(item["tool"] == "get_tags" for item in out)


# ---------------------------------------------------------------- 端到端（脚本）

def test_离线脚本跑通并打印五段读数() -> None:
    import subprocess
    proc = subprocess.run([sys.executable, "scripts/prompt_chain.py", "--offline"],
                          cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
                          timeout=180)
    assert proc.returncode == 0, proc.stderr[-300:]
    out = proc.stdout
    assert "离线自检通过" in out
    assert "选填 ['history']" in out                    # ① 模板契约的读数
    assert "缺必填变量 → KeyError 'article'" in out
    assert "随机 id，不是可读的步骤名" in out             # ② 节点名不可读
    assert "OutputParserException" in out               # ④ 异常 vs 三字段
    assert "真机那一段在 --offline 下不跑" in out         # ⑤ 明说跳过，不装作通过
