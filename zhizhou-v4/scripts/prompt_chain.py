#!/usr/bin/env python
"""提示模板、解析器与 LCEL 编排：五段可验收的读数。

    python scripts/prompt_chain.py --offline    # 不需要密钥：模板、形状、裁剪、解析
    python scripts/prompt_chain.py              # 需要密钥：同一批链在真机上的读数

五段各自回答一个问题：

    ① 模板知道什么          —— `input_variables` 与 `optional_variables` 的差别
    ② 链的形状是什么        —— `describe()` 读出来的输入/输出/步数
    ③ 裁剪发生在哪          —— 一个纯函数，不进模型也能测
    ④ 解析失败怎么办        —— `include_raw=True` 把异常变成三个字段
    ⑤ 真机上的账            —— 三条链各自的词元与返回类型（**账靠回调，链不记账**）
"""
from __future__ import annotations

import argparse
import itertools
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from langchain_core.callbacks import BaseCallbackHandler                                     # noqa: E402
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel             # noqa: E402
from langchain_core.messages import AIMessage                                                # noqa: E402
from langchain_core.output_parsers import JsonOutputParser                                   # noqa: E402
from langchain_core.prompts import ChatPromptTemplate                                        # noqa: E402
from langchain_core.runnables import RunnableLambda                                          # noqa: E402

from app.chains import (                                                                     # noqa: E402
    CLIP, clip, clipped_chain, describe, draft_chain, parallel_chain, structured_chain,
    summary_chain, tool_call_chain, with_passthrough,
)
from app.config import Config                                                                # noqa: E402
from app.llm import build_model                                                              # noqa: E402
from app.prompts import CHAT_PROMPT, DRAFT_PROMPT, SUMMARY_PROMPT                            # noqa: E402

ARTICLE = (
    "知舟博客这周上线了标签筛选。后端把文章列表的查询重写成了 SQLAlchemy 的表达式，"
    "分页参数从 offset/limit 换成了游标，首页的 P95 从 480ms 降到 90ms。"
    "前端没改接口，只换了请求参数的拼法。"
)
LINE = "─" * 72


class TokenTally(BaseCallbackHandler):
    """把「链跑了多少次、花了多少词元」记在外面。

    这是本节的一个结论的可执行版本：**链不替你记账**——`StrOutputParser` 的输出是一个
    `str`，用量信息在它的输入里，已经被丢掉了。但回调能看见每一次调用，
    所以账可以记在链的**外面**（承接 3.9 的追踪层：观测是旁路）。
    """

    def __init__(self) -> None:
        self.calls = 0
        self.input_tokens = 0
        self.output_tokens = 0

    def on_llm_end(self, response, **kwargs) -> None:            # noqa: ANN001
        self.calls += 1
        for group in getattr(response, "generations", []) or []:
            for generation in group:
                meta = getattr(getattr(generation, "message", None), "usage_metadata", None) or {}
                self.input_tokens += int(meta.get("input_tokens", 0) or 0)
                self.output_tokens += int(meta.get("output_tokens", 0) or 0)

    def line(self, label: str) -> str:
        return (f"{label}：调用 {self.calls} 次｜输入 {self.input_tokens} / "
                f"输出 {self.output_tokens}（共 {self.input_tokens + self.output_tokens}）")


def fake_model():
    """离线剧本：一个只会吐 JSON 的模型。**它不实现 `with_structured_output`**——
    所以离线段只跑「解析器」那一支，结构化输出那一支要靠真机（第⑤段）。"""
    return GenericFakeChatModel(messages=itertools.cycle([
        AIMessage('{"tool": "get_tags", "args": {"article_id": 12}}'),
    ]))


def const(message) -> RunnableLambda:
    """把一条固定的消息包成 Runnable：用来构造「模型说了坏话」的离线场景。"""
    return RunnableLambda(lambda _payload: message)


def shape_model():
    """一个**不联网**的模型对象，只用来读链的形状。

    为什么需要它：剧本模型不支持 `with_structured_output`（它没实现那个方法），
    而第②段要读的正是结构化那几条链的形状。

    这里能这么做的原因是本节的一个结论——**建链是纯结构操作**：
    `init_chat_model` / `with_structured_output` 只拼对象、不发请求，
    所以端口填一个没人监听的地址也能读出完整的输入输出 schema。
    真正需要网络的是 `.invoke()`，不是建链。
    """
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(model="shape-only", api_key="shape-only",
                      base_url="http://127.0.0.1:1/v1")


def part1_templates() -> None:
    print(f"{LINE}\n① 模板知道什么\n{LINE}")
    for name, prompt in (("摘要", SUMMARY_PROMPT), ("多轮", CHAT_PROMPT), ("少样本", DRAFT_PROMPT)):
        optional = list(getattr(prompt, "optional_variables", []) or [])
        print(f"  {name}：必填 {prompt.input_variables}｜选填 {optional}")
    print("  少样本的变量里没有 input/output——**示例是数据，进模板时就固定了**。")
    try:
        SUMMARY_PROMPT.format_messages()
    except KeyError as exc:
        print(f"  缺必填变量 → KeyError {exc}（**渲染时就抛**，不用等模型答非所问）")
    rendered = CHAT_PROMPT.format_messages(question="在吗")
    print(f"  缺选填变量 → 不报错，历史位置安静地空着，渲染出 {len(rendered)} 条："
          f"{[type(m).__name__.replace('Message', '') for m in rendered]}")
    print("  这一条是本节最该记住的：**历史是选填的，忘了传不会报错，只会丢掉上下文**。")


def part2_shape(model) -> None:
    print(f"\n{LINE}\n② 链的形状（读出来的，不是试出来的）\n{LINE}")
    stub = shape_model()
    print("  用的是一个**不联网**的模型对象：建链只拼结构，不发请求。")
    for name, chain in (
        ("纯文本摘要", summary_chain(stub)),
        ("结构化摘要", structured_chain(stub)),
        ("裁剪＋摘要", clipped_chain(stub)),
        ("工具 JSON", draft_chain(stub)),
        ("JSON＋原文", tool_call_chain(stub, include_raw=True)),
        ("并行两条", parallel_chain(stub)),
        ("带上入参", with_passthrough(stub)),
    ):
        d = describe(chain)
        print(f"  {name:10s} 输入 {d['输入']:20s} 输出 {d['输出']:32s} {d['步数']} 步")
    nodes = describe(summary_chain(stub))["节点"]
    print(f"  节点名长这样：{nodes[0][:12]}…——**随机 id，不是可读的步骤名**。")
    print("  所以「是哪一步坏了」不能靠它回答，要靠 3.9 的追踪层。")


def part3_clip() -> None:
    print(f"\n{LINE}\n③ 裁剪：一个纯函数\n{LINE}")
    for label, payload in (("短文", "短正文"), ("长文", "x" * 1500), ("映射", {"article": "y" * 50})):
        out = clip(payload)
        print(f"  {label:4s} → 留下 {len(out['article'])} 字符，clipped={out['clipped']}")
    print(f"  `CLIP` 是它包成 Runnable 之后的样子：{type(CLIP).__name__}——"
          "普通函数不是 Runnable，包一次才能用 `|` 组合。")


def part4_parsers(model) -> None:
    print(f"\n{LINE}\n④ 解析失败怎么办\n{LINE}")
    good = draft_chain(model).invoke({"request": "给文章 3 打标签"})
    print(f"  JsonOutputParser 好输入 → {type(good).__name__} {good}")
    broken = (ChatPromptTemplate.from_messages([("human", "{q}")])
              | const(AIMessage("我觉得应该调 get_tags 吧，文章 id 大概是 12。"))
              | JsonOutputParser())
    try:
        broken.invoke({"q": "x"})
    except Exception as exc:                                     # noqa: BLE001
        print(f"  JsonOutputParser 坏输入 → {type(exc).__name__}（**异常**，进不了指标）")
    print("  所以工具调用那一支要用 include_raw=True：它把这个异常变成")
    print("  {'raw': …, 'parsed': None, 'parsing_error': …} 三个字段——可记、可统计、可报警。")


def part5_real(model) -> None:
    print(f"\n{LINE}\n⑤ 真机：三条链的读数\n{LINE}")
    tally = TokenTally()

    plain = summary_chain(model).invoke({"article": ARTICLE}, config={"callbacks": [tally]})
    print(f"  纯文本摘要 → {type(plain).__name__}：{plain[:70]}…")
    print(f"    {tally.line('账')}｜**输出是 str，用量已经丢了**")

    tally2 = TokenTally()
    obj = structured_chain(model).invoke({"article": ARTICLE}, config={"callbacks": [tally2]})
    print(f"  结构化摘要 → {type(obj).__name__}：{len(obj.summary)} 字，tags={obj.tags}")
    print(f"    {tally2.line('账')}｜输出是**校验过的对象**")

    tally3 = TokenTally()
    raw = tool_call_chain(model, include_raw=True).invoke(
        {"request": "给文章 12 打标签"}, config={"callbacks": [tally3]})
    parsed, error = raw.get("parsed"), raw.get("parsing_error")
    print(f"  工具 JSON＋原文 → parsed={type(parsed).__name__}"
          f"{' ' + str(parsed) if parsed else ''}｜parsing_error="
          f"{type(error).__name__ if error else 'None'}")
    print(f"    {tally3.line('账')}")

    both = TokenTally()
    result = parallel_chain(model).invoke(
        {"article": ARTICLE, "request": "给文章 12 打标签"}, config={"callbacks": [both]})
    print(f"  并行两条 → 键 {sorted(result)}…")
    print(f"    {both.line('一次并行')}｜**一次并行就是两次调用**，省的是墙钟不是钱")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true", help="用剧本模型，不需要密钥")
    args = ap.parse_args()

    if args.offline:
        model = fake_model()
    else:
        cfg = Config.from_env()
        print(f"配置：{cfg.redacted()}")
        model = build_model(cfg)

    part1_templates()
    part2_shape(model)
    part3_clip()
    part4_parsers(model)
    if args.offline:
        print(f"\n{LINE}\n⑤ 真机那一段在 --offline 下不跑\n{LINE}")
        print("  它也**不能**离线跑：剧本模型没有 `with_structured_output`——")
        print("  这正是「离线证装配、真机报读数」在框架版上的形态（承接 3.10）。")
    else:
        part5_real(model)

    print("\n✔ 离线自检通过" if args.offline else "\n✔ 真机读数完成")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
