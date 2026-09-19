# tests/test_first_app.py —— 不需要密钥、不需要网络：配置、默认值、裁剪、记账
"""这一份测的是框架版的「第一步」能不能被机械验收。

四条断言各自对应正文里的一个结论，**它们都不需要模型**：
配置的缺省与脱敏、模型的默认值是不是真的被改成了有界值、
裁剪会不会裁掉系统消息、用量读不到时会不会编一个数。
"""
from __future__ import annotations

import itertools
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.config import Config
from app.history import ChatHistory, Usage
from app.llm import build_model, describe_defaults


def fake(replies: list[str]):
    """框架自带的测试替身：按序吐回复。"""
    return GenericFakeChatModel(messages=itertools.cycle([AIMessage(r) for r in replies]))


# ---------------------------------------------------------------- 配置

def test_缺密钥在装配时就报错() -> None:
    try:
        Config.from_env(lambda name, default="": "")
        raise AssertionError("缺 LLM_API_KEY 时装配必须报错，而不是等到第一次调用")
    except RuntimeError as exc:
        assert "LLM_API_KEY" in str(exc)


def test_密钥不进日志只有尾四位() -> None:
    cfg = Config.from_env(lambda name, default="": {
        "LLM_API_KEY": "sk-live-abcdefghijkl", "LLM_MODEL": "m"}.get(name, default))
    shown = cfg.redacted()
    assert cfg.api_key == "sk-live-abcdefghijkl"
    assert shown["api_key"] == "***ijkl" and "abcdefgh" not in str(shown)


# ---------------------------------------------------------------- 默认值

def test_默认值被改成有界而不落到六百秒() -> None:
    """`init_chat_model` 不传 timeout 时，**实际生效**的是下游的 600 秒——本树显式改掉了它。"""
    cfg = Config(api_key="test", base_url="http://127.0.0.1:1/v1", model="m")
    bounded = describe_defaults(build_model(cfg))
    assert bounded["实际生效的 read 超时（秒）"] == 30.0
    assert bounded["框架层 max_retries"] == 2

    from langchain_openai import ChatOpenAI
    unbounded = describe_defaults(ChatOpenAI(model="m", api_key="test",
                                             base_url="http://127.0.0.1:1/v1"))
    assert unbounded["框架层 request_timeout"] is None
    assert unbounded["实际生效的 read 超时（秒）"] == 600        # 这就是「有默认≠有界」
    assert unbounded["未设时下游兜底的 read 超时（秒）"] == 600


# ---------------------------------------------------------------- 裁剪

def test_裁剪只留最近的且不裁系统消息() -> None:
    history = ChatHistory(system="系统提示", max_messages=4)
    for i in range(4):
        history.add_user(f"问题 {i}")
        history.add_ai(fake(["答"]).invoke(history.to_messages()))
    sent = history.to_messages()
    assert isinstance(sent[0], SystemMessage) and sent[0].content == "系统提示"
    assert len(sent) == 5                                        # 系统 1 ＋ 历史 4
    # 四轮之后共八条历史，留下的应该是最近四条（实测读数，不是推算的）
    assert [m.content for m in sent[1:]] == ["问题 2", "答", "问题 3", "答"]
    assert history.trimmed_calls > 0 and history.dropped == 4     # 八条历史里丢了四条
    assert history.dropped == 4                                   # 再读一次，读数不变（属性无副作用）


def test_系统提示为空时不加空消息() -> None:
    history = ChatHistory(system="", max_messages=4)
    history.add_user("问题")
    assert all(not isinstance(m, SystemMessage) for m in history.to_messages())


# ---------------------------------------------------------------- 记账

def test_用量读不到时不编一个数() -> None:
    usage = Usage()
    assert usage.add(AIMessage("没有用元数据的回复")) is False
    assert usage.calls == 0 and usage.total == 0
    assert usage.input_share == 0.0


def test_用量按输入与输出分开记() -> None:
    usage = Usage()
    ok = usage.add(AIMessage("回复", usage_metadata={
        "input_tokens": 67, "output_tokens": 32, "total_tokens": 99}))
    assert ok and usage.calls == 1
    assert (usage.input_tokens, usage.output_tokens) == (67, 32)
    assert usage.total == 99 and usage.input_share == 0.6768


# ---------------------------------------------------------------- 端到端（脚本）

def test_离线脚本跑通并打印读数() -> None:
    """把脚本当门跑一遍：它打印的每一行都是正文里引用过的读数。"""
    import subprocess
    proc = subprocess.run([sys.executable, "scripts/first_app.py", "--offline"],
                          cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
                          timeout=120)
    assert proc.returncode == 0, proc.stderr[-300:]
    out = proc.stdout
    assert "离线自检通过" in out
    assert "裁剪：累计" in out and "账：调用" in out
    assert "['System', 'Human']" in out      # 系统消息与用户消息的形状是可打印的
    assert "离线读数不能当成本数据" in out     # 剧本模型没有用量元数据，脚本必须自己说清
