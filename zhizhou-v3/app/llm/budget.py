"""上下文预算：装不装得下、离水位线还有多远、两次请求能复用多少前缀。"""
from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass

from app.llm.tokens import Count, Counter, Prompt

WINDOW = 200_000          # 上下文窗口：输入与输出共用同一个（第 3.1.6 节）
MAX_OUTPUT = 4_096        # 这一次回答的预留
WATER = 0.8               # 水位线：用到窗口的这个比例就该处理，而不是等到装不下


def pad(s: str, w: int) -> str:
    """按显示宽度补齐（汉字算两列），只为表格对齐。"""
    return s + " " * max(0, w - sum(2 if ord(c) > 127 else 1 for c in s))


def cacheable_prefix(encode: Callable[[str], list[int]], a: str, b: str) -> int:
    """两次请求之间逐字不变的前缀词元数——前缀缓存命中的就是这一段。"""
    ta, tb = encode(a), encode(b)
    n = 0
    for x, y in zip(ta, tb):
        if x != y:
            break
        n += 1
    return n


@dataclass
class Verdict:
    fits: bool
    input_tokens: int
    remaining: int
    over_water: bool


class ContextBudget:
    def __init__(self, window: int = WINDOW, max_output: int = MAX_OUTPUT,
                 water: float = WATER) -> None:
        self.window, self.max_output, self.water = window, max_output, water

    def check(self, c: Count) -> Verdict:
        used = c.input_tokens + self.max_output
        return Verdict(used <= self.window, c.input_tokens, self.window - used,
                       used >= self.window * self.water)


if __name__ == "__main__":
    from app.llm.tokens import local_counter, official_counter

    local = local_counter()
    official = official_counter(local)
    # ↑ 官方计数要凭据。这里用「按官方文档口径（新分词器约 +30% 词元）」构造的假计数器代替，
    #   只用来演示「估算偏 30% 会怎样」；真实实现换成 count_tokens 接口，其余形状不变。

    TOOLS = json.dumps([
        {"name": "search_article", "description": "按关键词检索知舟的历史文章，返回标题与 id",
         "input_schema": {"type": "object",
                          "properties": {"q": {"type": "string", "description": "检索词"}},
                          "required": ["q"], "additionalProperties": False}},
        {"name": "read_article", "description": "读一篇文章的正文",
         "input_schema": {"type": "object",
                          "properties": {"article_id": {"type": "integer"}},
                          "required": ["article_id"], "additionalProperties": False}},
    ], ensure_ascii=False)

    SYSTEM = ("你是知舟博客的写作助手。只依据检索到的文章作答，并给出文章 id。\n"
              "找不到就直说找不到，不要编造标题。输出使用简体中文。")
    ASK = "帮我找一篇讲令牌过期的文章，并说清它讲到了哪几种做法。"

    def hist(rounds: int) -> str:
        return "\n".join(
            f"{r}. 用户：第 {r} 轮的问题\n   助手：第 {r} 轮的观察：命中 {r * 7 + 11} 条，"
            f"最相关的是《JWT 刷新令牌怎么做》，它给出了黑名单与滑动过期两种做法。"
            for r in range(1, rounds + 1))

    PROMPTS = {
        "A 问答": Prompt({"tools": TOOLS, "system": SYSTEM, "messages": ASK}),
        "B 摘要长文": Prompt({"system": SYSTEM, "messages": "把下面这一篇总结成三句：\n" + ASK * 20}),
        "C 多轮历史": Prompt({"tools": TOOLS, "system": SYSTEM, "messages": hist(40)}),
        "D 长任务第 95 轮": Prompt({"tools": TOOLS, "system": SYSTEM, "messages": hist(95)}),
    }

    counter = Counter(official, local)
    print("=== 一、词元构成（本地编码器 o200k_base 的估算值）===")
    print(f"{pad('提示', 20)}{'tools':>7}{'system':>8}{'messages':>10}{'输入合计':>10}  重头")
    for name, p in PROMPTS.items():
        c = counter.report(p, exact=False)
        cell = lambda k: f"{c.parts.get(k, 0):,}"           # noqa: E731
        k, n, r = c.heavy()[0]
        print(f"{pad(name, 20)}{cell('tools'):>7}{cell('system'):>8}{cell('messages'):>10}"
              f"{c.input_tokens:>10,}  {k} {n:,}（{r:.0%}）")

    print()
    print("=== 二、计数缓存：逐字相同的段落只该问一次 ===")
    probe = Counter(official, local)
    for p in PROMPTS.values():
        probe.report(p, exact=False)
    segs = sum(len(p.parts) for p in PROMPTS.values())
    print(f"  四份提示共 {segs} 段文本，去重后只算了 {probe.calls} 段（命中缓存 {probe.hits} 次）")
    print(f"  换成官方计数接口：{probe.calls} 次网络调用，而不是 {segs} 次")

    print()
    print("=== 三、前缀缓存：两次请求之间逐字不变的那一段（第 3.1.6 节）===")
    ts = "现在是 2026-09-13 21:04。"
    cases = [
        ("好顺序：tools → system（时间戳在 system 末尾）→ messages",
         Prompt({"tools": TOOLS, "system": SYSTEM + "\n" + ts, "messages": ASK}),
         Prompt({"tools": TOOLS, "system": SYSTEM + "\n" + ts.replace("21:04", "21:05"),
                 "messages": ASK})),
        ("坏顺序：时间戳在最前：system → tools → messages",
         Prompt({"system": ts + "\n" + SYSTEM, "tools": TOOLS, "messages": ASK},
                order=("system", "tools", "messages")),
         Prompt({"system": ts.replace("21:04", "21:05") + "\n" + SYSTEM, "tools": TOOLS,
                 "messages": ASK}, order=("system", "tools", "messages"))),
    ]
    for label, a, b in cases:
        n = cacheable_prefix(local, a.serialize(), b.serialize())
        tot = local(a.serialize())
        print(f"  {label}")
        print(f"    两次请求逐字相同的前缀 {n:,} 词元（占该请求 {n / tot:.0%}）；"
              f"20 轮为它支付的输入 {n * 20:,} 词元")

    print()
    print("=== 四、估算值偏 30%，判定会不会翻（窗口 8,000 / 输出预留 1,024）===")
    small = ContextBudget(window=8_000, max_output=1_024)
    print(f"  {pad('提示', 20)}{'本地估算':>10}{'官方口径':>10}{'偏差':>7}   "
          f"{'本地判定':<12}{'官方判定':<12}")
    for name, p in PROMPTS.items():
        a = Counter(official, local).report(p, exact=False)
        b = Counter(official, local).report(p, exact=True)
        va, vb = small.check(a), small.check(b)
        verdict = lambda v: "装得下" if v.fits else "装不下"  # noqa: E731
        flag = "  ← 判定翻转" if va.fits != vb.fits else ""
        print(f"  {pad(name, 20)}{a.input_tokens:>10,}{b.input_tokens:>10,}"
              f"{b.input_tokens / a.input_tokens - 1:>6.0%}   "
              f"{verdict(va):<14}{verdict(vb):<14}{flag}")
