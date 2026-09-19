"""剧本模型：一个**能发出工具调用**的确定性模型，离线跑循环用。

4.1 与 4.2 各有一份剧本模型，但它们只会「吐一段文本」或「吐一段 JSON」。
这一章第一次需要剧本发出**真正的 `tool_calls`**——因为循环要判的就是它。
所以这一份要回答三个以前不用管的问题：

1. **`bind_tools` 怎么应付？** 真实模型把它翻成服务商的工具定义；剧本模型只要返回自己。
   不实现它，`create_agent` 在装配那一刻就会抛 `NotImplementedError`。
2. **`tool_call_id` 谁来生成？** 每轮**必须换一个**。踩过的坑：第一版复用同一个 id，
   框架按 id 去重，于是第二次工具调用没有对应的 ToolMessage，
   报出来的是 `KeyError: 'model'`——一个完全不指向真因的错。见 4.3.4 的坑表。
3. **用量从哪来？** 真机从服务商拿；剧本要自己编一份，否则「词元」这一列永远是 0，
   而 0 与「没测」长得一模一样。

它不在 `app/` 之外藏着，是为了让**脚本与测试用同一份剧本**——
两个各写一份的下场是：测试通过、演示跑出别的结论。
"""
from __future__ import annotations

from typing import Any

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import Field


def tool_call(name: str, args: dict, tokens: int = 120) -> dict:
    """剧本的一步：调某个工具。`tokens` 是这一步假装的用量（「输入 ＋ 输出」）。"""
    return {"tool": name, "args": args, "tokens": tokens}


def final(text: str, tokens: int = 80) -> dict:
    """剧本的一步：不再调工具，给出最终答案。"""
    return {"final": text, "tokens": tokens}


class ScriptedModel(BaseChatModel):
    """按剧本一格一格走。**走完之后重复最后一格**——于是「卡死」与「撞上限」都可复现。"""

    script: list[dict] = Field(default_factory=list)
    pos: int = 0
    seen_messages: list[int] = Field(default_factory=list)   # 每次调用时上下文有多长

    @property
    def _llm_type(self) -> str:
        return "scripted"

    def bind_tools(self, tools: Any, **kwargs: Any) -> "ScriptedModel":   # noqa: ANN401
        """工具定义对剧本没有意义，但**必须实现**：不实现的话装配阶段就抛。"""
        return self

    def _generate(self, messages: list[BaseMessage], stop: list[str] | None = None,
                  run_manager: CallbackManagerForLLMRun | None = None,
                  **kwargs: Any) -> ChatResult:                      # noqa: ANN401
        n = self.pos
        step = self.script[min(n, len(self.script) - 1)]
        object.__setattr__(self, "pos", n + 1)
        self.seen_messages.append(len(messages))
        tokens = int(step.get("tokens", 0))
        usage = {"input_tokens": tokens // 3, "output_tokens": tokens - tokens // 3,
                 "total_tokens": tokens}
        if "final" in step:
            message = AIMessage(content=step["final"], usage_metadata=usage)
        else:
            message = AIMessage(content="", usage_metadata=usage, tool_calls=[{
                "name": step["tool"], "args": step["args"],
                "id": f"call_{n}", "type": "tool_call",     # **每轮换 id**：见模块开头第 2 条
            }])
        return ChatResult(generations=[ChatGeneration(message=message)])
