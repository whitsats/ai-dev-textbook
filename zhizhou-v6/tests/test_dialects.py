# tests/test_dialects.py —— 不需要密钥、不需要网络：三个适配器能不能互相对上
"""十组断言。这一份测的是**翻译过程**，与 `test_wire.py` 那份（测表）分开。

三组最值钱：

1. **三段夹具流解出同一段答复**（文本、工具参数逐个相同）——「三种帧形」的证明；
2. **「要调工具」这家读不出来**：同一段答复，两家说「要调工具了」，
   一家只报「答完了」。这条不是缺陷，是它把两件事合成了一个取值——
   所以判「有没有工具调用」**不能只读停止原因**；
3. **坏 JSON 必须报错**：静默退回空字典会伪造一次「模型没传参数」的调用。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.dialects import (ADAPTERS, STREAM_ARGS, STREAM_TEXT, chat_stream,  # noqa: E402
                          load_arguments, messages_stream, responses_stream,
                          tool_constraint, tool_dialects)
from app.wire import Block, Message, Request, Tool, WireError  # noqa: E402


def _req(dialect: str) -> Request:
    return Request(model="gpt-5.6-terra", system="你是知舟。",
                   messages=(Message("user", (Block("text", text="查一下北京"),)),
                             Message("assistant", (Block("tool_call", call_id="c1",
                                                         name="search",
                                                         arguments={"q": "北京"}),)),
                             Message("user", (Block("tool_result", call_id="c1",
                                                    text="晴"),))),
                   tools=(Tool("search", "查资料",
                               {"type": "object", "properties": {"q": {"type": "string"}}}),),
                   max_output_tokens=1_024, dialect=dialect)


STREAMS = {"messages": messages_stream, "responses": responses_stream,
           "chat": chat_stream}


# ---------------------------------------------------------------- 一、请求翻译

def test_三种方言都把同一段系统提示带上了() -> None:
    msg = ADAPTERS["messages"].to_wire(_req("messages"))
    res = ADAPTERS["responses"].to_wire(_req("responses"))
    chat = ADAPTERS["chat"].to_wire(_req("chat"))
    assert msg["system"] == "你是知舟。", "这家是顶层字段"
    assert res["instructions"] == "你是知舟。", "这家也是顶层字段，但名字不同"
    assert chat["messages"][0] == {"role": "system", "content": "你是知舟。"}, \
        "这一家把它塞进了消息数组的第一条"


def test_同一个输出上限在三种方言里是三个名字() -> None:
    assert ADAPTERS["messages"].to_wire(_req("messages"))["max_tokens"] == 1_024
    assert ADAPTERS["responses"].to_wire(_req("responses"))["max_output_tokens"] == 1_024
    assert ADAPTERS["chat"].to_wire(_req("chat"))["max_completion_tokens"] == 1_024


def test_输出上限在messages方言里必填而另外两家选填() -> None:
    bare = Request(model="gpt-5.6-terra", system="你是知舟。",
                   messages=(Message("user", (Block("text", text="你好"),)),),
                   dialect="messages")
    try:
        ADAPTERS["messages"].to_wire(bare)
    except WireError as exc:
        assert "max_tokens 必填" in str(exc), str(exc)
    else:
        raise AssertionError("必填项要当场报错，不许替调用方猜一个数")
    for d in ("responses", "chat"):
        assert ADAPTERS[d].to_wire(Request(model="gpt-5.6-terra", system="你是知舟。",
                                           messages=bare.messages, dialect=d)), \
            f"{d} 这一家选填，不给也应当翻得出来"


def test_工具结果放进assistant消息会被拦下() -> None:
    bad = Request(model="m", system="s", max_output_tokens=256,
                  messages=(Message("assistant", (Block("tool_result", call_id="c1",
                                                        text="x"),)),),
                  dialect="messages")
    try:
        ADAPTERS["messages"].to_wire(bad)
    except WireError as exc:
        assert "要放在一条 user 消息里" in str(exc), str(exc)
    else:
        raise AssertionError("这一家只把工具结果放在 user 消息里，角色不对要报错")


# ---------------------------------------------------------------- 二、解析答复

def test_同一段答复在三种方言里解出同一个规范答复() -> None:
    msg = ADAPTERS["messages"].from_wire(
        {"content": [{"type": "text", "text": "晴"},
                     {"type": "tool_use", "id": "c1", "name": "search",
                      "input": {"q": "北京"}}],
         "stop_reason": "tool_use", "usage": {"input_tokens": 9}})
    res = ADAPTERS["responses"].from_wire(
        {"output": [{"type": "message", "content": [{"type": "output_text", "text": "晴"}]},
                    {"type": "function_call", "call_id": "c1", "name": "search",
                     "arguments": '{"q": "\u5317\u4eac"}'}],
         "status": "completed", "usage": {"input_tokens": 9}})
    chat = ADAPTERS["chat"].from_wire(
        {"choices": [{"finish_reason": "tool_calls",
                      "message": {"content": "晴",
                                  "tool_calls": [{"id": "c1", "type": "function",
                                                  "function": {
                                                      "name": "search",
                                                      "arguments": '{"q": "\u5317\u4eac"}'}}]}}],
         "usage": {"prompt_tokens": 9}})
    assert [msg.text, res.text, chat.text] == ["晴", "晴", "晴"]
    assert [m.tool_calls[0].arguments for m in (msg, res, chat)] \
        == [{"q": "北京"}] * 3, "两家给字符串、一家给对象，解出来必须一样"
    assert (msg.stop, chat.stop) == ("tool_call", "tool_call")
    assert res.stop == "end_turn", "**这一家读不出「要调工具」**——它与正常结束同形"


def test_三段流解出同一段答复() -> None:
    got = {d: ADAPTERS[d].from_stream(f()) for d, f in STREAMS.items()}
    assert {r.text for r in got.values()} == {STREAM_TEXT}
    assert {json.dumps(r.tool_calls[0].arguments, sort_keys=True)
            for r in got.values()} == {json.dumps(STREAM_ARGS, sort_keys=True)}
    assert {len(r.tool_calls) for r in got.values()} == {1}
    assert got["messages"].events == 12 and got["responses"].events == 9 \
        and got["chat"].events == 7, "同一段答复：12／9／7 帧（数的是 data: 行）"


def test_要调工具这件事在responses上读不出来() -> None:
    """这是本章最重的一条读数，所以它单独一条断言。"""
    got = {d: ADAPTERS[d].from_stream(f()) for d, f in STREAMS.items()}
    assert got["messages"].stop == "tool_call" and got["chat"].stop == "tool_call"
    assert got["responses"].stop == "end_turn", "同一段答复，这一家报的是「答完了」"
    assert len(got["responses"].tool_calls) == 1, \
        "**判有没有工具调用要看 output 里有没有那个 item，不是看停止原因**"


# ---------------------------------------------------------------- 三、坏输入

def test_坏_json报错而不是空对象() -> None:
    for d in ("chat", "responses"):
        try:
            load_arguments('{"q": ', d)
        except WireError as exc:
            assert "不是合法 JSON" in str(exc), str(exc)
        else:
            raise AssertionError("坏参数必须报错：静默成 {} 会伪造一次「没传参数」的调用")
    assert load_arguments("{}", "chat") == {}
    assert load_arguments("", "chat") == {}, "空串是「没有参数」，这一条不算坏"


def test_没登记过的停止原因会报错() -> None:
    """协议变了要说话——回程表里没有的取值意味着线上多了一个档。"""
    try:
        ADAPTERS["chat"].from_wire({"choices": [{"finish_reason": "brand_new_reason",
                                                "message": {"content": ""}}]})
    except WireError as exc:
        assert "brand_new_reason" in str(exc), str(exc)
    else:
        raise AssertionError("没登记过的取值不许塞进最近的一档")


# ---------------------------------------------------------------- 四、能力矩阵

def test_能力矩阵三条约束() -> None:
    assert tool_dialects("claude-opus-5") == ("messages",), "另一家不在兼容层的图纸上"
    assert tool_dialects("gpt-6-astra") == ("responses",), \
        "最大的那一个工具调用只走 Responses"
    assert tool_dialects("gpt-5.6-luna") == ("responses", "chat")
    note = tool_constraint("gpt-5.6-luna", "chat")
    assert note.startswith("只在") and "推理" in note, note
    assert tool_constraint("gpt-6-astra", "responses") == "", "没有前提就写空，别凑一句"
