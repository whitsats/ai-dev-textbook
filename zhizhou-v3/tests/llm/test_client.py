# tests/llm/test_client.py —— 不需要模型凭据与网络
import os
import tempfile
from pathlib import Path

from app.llm.client import (Config, LlmError, LlmTransportError, RawChat, RawReply, ToolCall,
                            call_model, chat, _openai_body, _parse_reply)
from app.llm.client import prompt_version

PROMPT = "tags 只能从清单里选，最多三个。"


def make_prompt(text: str = PROMPT) -> Path:
    p = Path(tempfile.mkdtemp()) / "article_summary.md"
    p.write_text(text, encoding="utf-8")
    return p


def transport(*steps: str, data=None, tokens: int = 100):
    """按剧本返回；剧本用完后重复最后一步。"""
    seq = list(steps) or ["成功"]

    def call(body: str, cfg: Config) -> RawReply:
        step = seq.pop(0) if len(seq) > 1 else seq[0]
        if step == "成功":
            return RawReply(data if data is not None else
                            {"summary": "摘要", "tags": ["后端"]}, tokens)
        raise LlmTransportError(step, "失败")
    return call


def config(**kw) -> Config:
    return Config(api_key="来自环境变量", **kw)


def caught(fn) -> LlmError:
    """把「抛的是不是 LlmError」也变成断言的一部分。"""
    try:
        fn()
    except LlmError as exc:
        return exc
    raise AssertionError("没有抛出 LlmError")


def test_超时后重试成功():
    r = call_model(make_prompt(), "正文", transport=transport("超时", "成功"),
                   config=config())
    assert r.attempts == 2 and r.tokens == 100 and r.summary.tags == ["后端"]


def test_一直超时会在上限处停下():
    exc = caught(lambda: call_model(make_prompt(), "正文", transport=transport("超时"),
                                    config=config()))
    assert exc.kind == "超时" and exc.attempts == 2


def test_不可重试的失败只试一次():
    calls = {"n": 0}

    def t(body: str, cfg: Config) -> RawReply:
        calls["n"] += 1
        raise LlmTransportError("参数错误", "请求格式不对")

    exc = caught(lambda: call_model(make_prompt(), "正文", transport=t, config=config()))
    assert exc.kind == "参数错误" and calls["n"] == 1 and exc.spent == 0


def test_结构错不重试但词元要记账():
    exc = caught(lambda: call_model(make_prompt(), "正文",
                                    transport=transport("成功", data={"summary": "摘要",
                                                                     "tags": ["安全"]}),
                                    config=config()))
    assert exc.kind == "结构不合 schema" and exc.attempts == 1 and exc.spent == 100


def test_总耗时不超过次数乘超时():
    now = {"t": 0.0}

    def t(body: str, cfg: Config) -> RawReply:
        now["t"] += cfg.timeout
        raise LlmTransportError("超时", "慢")

    caught(lambda: call_model(make_prompt(), "正文", transport=t, config=config(),
                              clock=lambda: now["t"]))
    assert now["t"] == config().max_attempts * config().timeout   # 上限是次数 × 超时，不是无限


def test_密钥只从环境变量读():
    old = os.environ.pop("LLM_API_KEY", None)
    try:
        assert caught(Config.from_env).kind == "参数错误"   # 启动时抛，不是调用时
        os.environ["LLM_API_KEY"] = "测试用值"
        assert Config.from_env().api_key == "测试用值"
    finally:
        os.environ.pop("LLM_API_KEY", None)
        if old is not None:
            os.environ["LLM_API_KEY"] = old


def test_提示版本随内容变化():
    a, b = make_prompt(PROMPT), make_prompt(PROMPT + "。")
    assert prompt_version(a) != prompt_version(b) and len(prompt_version(a)) == 8


def test_方言只改传输层不改上层():
    """同一套重试与记账，换 provider 只换 URL 与消息形状。"""
    openai_body = _openai_body([{"role": "user", "content": "x"}], config(), None, None, None)
    assert openai_body["model"] and "messages" in openai_body
    assert openai_body["messages"][0]["content"] == "x"


def test_密钥不会出现在日志用的配置摘要里():
    assert "sk-" not in str(Config(api_key="sk-abcdef123456").redacted())


def test_并行工具调用会被完整读回来():
    """一次响应里两个调用：两个都要读到，不能只取第一个（3.5.8）。"""
    got = _parse_reply({"choices": [{"message": {"content": "", "tool_calls": [
        {"id": "c1", "function": {"name": "search_article", "arguments": '{"q":"a"}'}},
        {"id": "c2", "function": {"name": "search_article", "arguments": '{"q":"b"}'}}]}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5}}, config())
    assert len(got.tool_calls) == 2 and got.tool_calls[1].parsed() == {"q": "b"} and got.tokens == 15


def test_坏参数不抛异常而是变成一条可读的结果():
    assert ToolCall("c1", "read_article", "{oops").parsed() == {"__bad_json__": "{oops"}


def test_对话层与结构化层共用同一套重试分类():
    def t(messages, cfg, **kw):
        raise LlmTransportError("限流", "稍后再试")

    exc = caught(lambda: chat([{"role": "user", "content": "x"}], config=config(), transport=t))
    assert exc.kind == "限流" and exc.attempts == config().max_attempts


def test_收口时可以把工具收走():
    seen = {}

    def t(messages, cfg, **kw):
        seen.update(kw)
        return RawChat("答案", [], 12)

    chat([{"role": "user", "content": "x"}], config=config(), tools=[{"name": "a"}],
         tool_choice="none", transport=t)
    assert seen["tool_choice"] == "none" and seen["tools"] == [{"name": "a"}]
