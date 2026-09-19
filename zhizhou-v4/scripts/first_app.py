#!/usr/bin/env python
"""第一个框架版应用：**多轮问答 ＋ 裁剪 ＋ 记账**。

    python scripts/first_app.py --offline    # 不需要密钥：确定性剧本模型
    python scripts/first_app.py              # 需要密钥：真的调一次模型

它要证明的东西只有三条，但三条都要能看见：

1. **消息是对象，不是一段拼好的 JSON**——历史是可遍历、可打印的 `HumanMessage` /
   `AIMessage`，不是三个 `{"role": ..., "content": ...}` 字典；
2. **裁剪是现成的**：`trim_messages` 在历史超过上限时留下最近的那些，
   且**不会裁掉系统消息**（它不在被裁的那个列表里）；
3. **用量在消息里**：`usage_metadata` 直接给出输入／输出词元，
   所以「输入占比」这类账不需要自己数——但**读不到时要如实说读不到**。
"""
from __future__ import annotations

import argparse
import itertools
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.config import Config                    # noqa: E402
from app.history import ChatHistory              # noqa: E402
from app.llm import build_model, describe_defaults  # noqa: E402

SYSTEM = "你是知舟的技术助手。回答控制在两句话内，不要客套。"
QUESTIONS = [
    "刷新令牌的滑动过期有什么代价？",
    "那黑名单方案呢？",
    "两种能一起用吗？",
    "我更该先上哪一种？",
]


def fake_model():
    """离线用的剧本模型：不需要密钥，也不需要网络。

    它来自 `langchain_core.language_models.fake_chat_models`——**框架自带测试替身**。
    v3 的那份替身是自己写的（`tests/test_wiring.py` 的 `fake_chat`），
    这是「框架替你做了什么」清单上很小、但每天都会用到的一项。
    """
    from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
    from langchain_core.messages import AIMessage

    replies = [
        AIMessage("滑动过期的代价是并发刷新时的令牌冲突，工程上要给旧令牌留一个很短的宽限窗口。"),
        AIMessage("黑名单的代价是每次刷新多一次查询，而且黑名单一丢，撤销就失效了。"),
        AIMessage("能。滑动过期覆盖常态，黑名单只留给需要精确到单枚令牌的场景。"),
        AIMessage("先上滑动过期：它不需要额外存储，也是最容易被验证的一条。"),
    ]
    return GenericFakeChatModel(messages=itertools.cycle(replies))


def run(model, *, max_messages: int, turns: int, tag: str) -> ChatHistory:
    history = ChatHistory(system=SYSTEM, max_messages=max_messages)
    print(f"== {tag}（历史上限 {max_messages} 条，跑 {turns} 轮）==")
    for q in QUESTIONS[:turns]:
        history.add_user(q)
        sent = history.to_messages()
        print(f"\n  用户：{q}")
        print(f"  发出的消息 {len(sent)} 条："
              f"{[type(m).__name__.replace('Message', '') for m in sent]}")
        answer = history.add_ai(model.invoke(sent))
        print(f"  助手：{answer}")
    print(f"\n  账：{history.usage.table()}")
    if history.usage.calls == 0:
        print("       ↑ 剧本模型不产生 `usage_metadata`——**离线读数不能当成本数据**"
              "（同一个坑在 3.10 的一键验收里也踩过）")
    print(f"  裁剪：累计 {history.trimmed_calls} 次发生裁剪，当前丢弃 {history.dropped} 条")
    return history


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true", help="用剧本模型，不需要密钥")
    ap.add_argument("--max-messages", type=int, default=4, help="历史条数上限（不含系统消息）")
    ap.add_argument("--turns", type=int, default=4)
    args = ap.parse_args()

    if args.offline:
        run(fake_model(), max_messages=args.max_messages, turns=args.turns, tag="离线剧本")
        print("\n✔ 离线自检通过")
        return 0

    cfg = Config.from_env()
    print(f"配置：{cfg.redacted()}")
    model = build_model(cfg)
    print("框架与下游的默认值：", describe_defaults(model))
    run(model, max_messages=args.max_messages, turns=args.turns, tag="真机")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
