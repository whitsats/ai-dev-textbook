"""模型登记表：把「官方说的数」抄成一张**能核**的表。

选型表最会骗人的地方不是数字抄错，而是**抄的时候把口径丢了**：
「$2」是每百万词元，还是一整单的加成？「1M 上下文」是全程一个价，
还是过了某个数就整单翻倍？「缓存便宜」是 0.1× 还是 0.025×？
口径丢了，表**还是长得像表**——只有拿着它去算钱的那一刻才会发现。

所以这张表带着三样东西：

1. `as_of` 与 `source`——**抄的哪一天、抄的哪一页**。价格页是会变的：
   本轮抄的时候，一家把「限时价」写成了正式价、另一家多了一档按上下文长度分段的价，
   两处都不是「我们记错了」，是**它们改了**；
2. 一组**能被断言的关系**（`violations()`）。两家公布的乘法关系高度重合
   （缓存写 1.25×、缓存读 0.1×、批量 0.5×），**重合的部分就能当断言用**；
3. 不重合的部分**显式登记**，不塞进「差不多」里：Fable 5.1 系列的读价是 0.025×，
   1 小时缓存档只有一家有。把它们抹平，正是这张表开始变成小说的第一步。
"""
from __future__ import annotations

from dataclasses import dataclass

#: 抄表的那一天。**它必须进表**：读者的第一问应该是「这张表什么时候抄的」。
AS_OF = "2026-09-17"

#: 口径的出处。表里每一条都指得到这里的某一行。
SOURCES: dict[str, str] = {
    "claude_models": "https://platform.claude.com/docs/en/about-claude/models/overview",
    "claude_pricing": "https://platform.claude.com/docs/en/about-claude/pricing",
    "claude_caching": "https://platform.claude.com/docs/en/build-with-claude/prompt-caching",
    "openai_pricing": "https://developers.openai.com/api/docs/pricing",
    "openai_terra": "https://developers.openai.com/api/docs/models/gpt-5.6-terra",
}

#: 两家供应商自己写下的乘法关系。**这两个倍数是共同点**，所以它们能当不变量。
CACHE_WRITE_X = 1.25      # 写一次缓存要付的溢价
CACHE_READ_X = 0.10       # 读到一次缓存要付的价
CACHE_HOUR_X = 2.00       # 1 小时档的写价（只有一家有这一档）
BATCH_X = 0.50            # 批量通道
LONG_INPUT_X = 2.00       # 长档：整单输入 ×2
LONG_OUTPUT_X = 1.50      # 长档：整单输出 ×1.5

#: 读价的例外。官方脚注：「Cache hits and refreshes on Claude Fable 5.1 and
#: Claude Mythos 5.1 are priced at 0.025x the base input price.」
#: **例外要写成例外**——放宽全局倍数的话，八个模型里七个就没人核了。
CACHE_READ_X_EXCEPTIONS: dict[str, float] = {"claude-fable-5-1": 0.025}
CACHE_WRITE_X_EXCEPTIONS: dict[str, float] = {"claude-fable-5-1": 1.25}


@dataclass(frozen=True)
class ModelSpec:
    """一个模型的一行。价格一律是**每百万词元（MTok）的美元数**。"""

    name: str                  # 供应商给的 API ID
    vendor: str
    context: int               # 上下文窗口（词元）＝ 输入 ＋ 输出
    max_output: int            # 单次最大输出（词元）
    input_price: float
    output_price: float
    cache_write: float         # 写一次缓存（标准档）
    cache_read: float          # 读到缓存
    cache_write_hour: float | None = None   # 1 小时档；None = 这家没有这一档
    long_context_over: int | None = None    # 超过这个输入词元数进长档；None = 不分档
    cutoff: str = ""           # 可靠知识截止
    source: str = ""

    def write_price(self, ttl: str) -> float:
        """按档取写价。`ttl` 只有 `"5m"` / `"1h"` 两种；要 1 小时档而这家没有就报错。

        **报错而不是退回标准档**：静默退回会让「我按 1 小时档算的」这句话变成假的，
        而账单上没有人会提醒你——这正是本树要防的那类错。
        """
        if ttl == "5m":
            return self.cache_write
        if ttl == "1h":
            if self.cache_write_hour is None:
                raise ValueError(f"{self.name} 没有 1 小时档（表里是 None，不是漏抄）")
            return self.cache_write_hour
        raise ValueError(f"未知的缓存档：{ttl!r}")


def _claude(name: str, context: int, max_output: int, inp: float, out: float,
            write1h: float, read: float, cutoff: str) -> ModelSpec:
    """按官方定价页的三条倍数把 Anthropic 那一家的五个价推出来。

    **不是手抄五个数，是抄一个数加三条关系**：官方页上「5m cache writes」
    就是 `1.25 × 输入`、「1h cache writes」是 `2 × 输入`。手抄五个位置就有五次
    抄错的机会，而且抄错了表还是自洽的。
    """
    return ModelSpec(
        name=name, vendor="Anthropic", context=context, max_output=max_output,
        input_price=inp, output_price=out,
        cache_write=round(CACHE_WRITE_X * inp, 4), cache_read=read,
        cache_write_hour=write1h, cutoff=cutoff, source="claude_pricing",
    )


def _openai(name: str, inp: float, out: float, cached: float, cutoff: str) -> ModelSpec:
    """OpenAI 那一栏：写价 1.25×、读价即「cached input」列，**没有 1 小时档**。

    长档要单独说：官方模型页写的是「Prompts with >272K input tokens are priced at
    2x input and 1.5x output **for the full request**」——注意是整单，不是超出部分。
    """
    return ModelSpec(
        name=name, vendor="OpenAI", context=1_050_000, max_output=128_000,
        input_price=inp, output_price=out,
        cache_write=round(CACHE_WRITE_X * inp, 4), cache_read=cached,
        cache_write_hour=None, long_context_over=272_000,
        cutoff=cutoff, source="openai_pricing",
    )


#: 八个模型、两家。窗口那一栏两家都不是整数——**这本身就是一条读数的来源**：
#: 「1M」是官方页上的写法，而这家的模型页写的是 1,050,000。
MODELS: tuple[ModelSpec, ...] = (
    _claude("claude-fable-5-1", 1_000_000, 128_000, 10.0, 50.0, 20.0, 0.25, "2026-06"),
    _claude("claude-opus-5", 1_000_000, 128_000, 5.0, 25.0, 10.0, 0.50, "2026-05"),
    _claude("claude-sonnet-5", 1_000_000, 128_000, 2.0, 10.0, 4.0, 0.20, "2026-01"),
    _claude("claude-haiku-4-5", 200_000, 64_000, 1.0, 5.0, 2.0, 0.10, "2025-02"),
    _openai("gpt-6-astra", 10.0, 50.0, 1.00, "2026-04-30"),
    _openai("gpt-5.6-sol", 4.0, 20.0, 0.40, "2026-02-16"),
    _openai("gpt-5.6-terra", 2.0, 12.0, 0.20, "2026-02-16"),
    _openai("gpt-5.6-luna", 0.20, 1.20, 0.02, "2026-02-16"),
)

BY_NAME: dict[str, ModelSpec] = {m.name: m for m in MODELS}


def violations(models: tuple[ModelSpec, ...] = MODELS) -> list[str]:
    """把「表里能算出来的关系」全算一遍，返回所有对不上的地方。

    **这是这张表唯一会响的一条路**：价格改了而倍数没改、倍数改了而某一行漏改，
    都会在这里被点出名字。空列表才是正常。
    """
    bad: list[str] = []
    for m in models:
        w_x = CACHE_WRITE_X_EXCEPTIONS.get(m.name, CACHE_WRITE_X)
        r_x = CACHE_READ_X_EXCEPTIONS.get(m.name, CACHE_READ_X)
        if abs(m.cache_write - round(w_x * m.input_price, 4)) > 1e-9:
            bad.append(f"{m.name}：缓存写价 {m.cache_write} 与「输入 × {w_x}」不符")
        if abs(m.cache_read - round(r_x * m.input_price, 4)) > 1e-9:
            bad.append(f"{m.name}：缓存读价 {m.cache_read} 与「输入 × {r_x}」不符")
        if m.cache_write_hour is not None and \
                abs(m.cache_write_hour - round(CACHE_HOUR_X * m.input_price, 4)) > 1e-9:
            bad.append(f"{m.name}：1 小时写价 {m.cache_write_hour} 与「输入 × 2」不符")
        if m.long_context_over is not None and m.vendor != "OpenAI":
            bad.append(f"{m.name}：长档只在一家的表里出现过，这里却挂在 {m.vendor} 上")
        if m.context < m.max_output:
            bad.append(f"{m.name}：窗口 {m.context} 小于最大输出 {m.max_output}")
        if not m.source or m.source not in SOURCES:
            bad.append(f"{m.name}：没有出处（source={m.source!r}）——没有出处的数不进表")
        if m.cutoff == "":
            bad.append(f"{m.name}：缺知识截止日期")
    vendors = {m.vendor for m in models}
    if len(vendors) < 2:
        bad.append(f"登记表只有一家供应商：{vendors}——「选型」这个词就没了对象")
    return bad


def table_row(m: ModelSpec) -> dict:
    """给读数脚本用的扁平行。**不留任何需要再解释一次的字段。**"""
    return {
        "name": m.name, "vendor": m.vendor,
        "context": m.context, "max_output": m.max_output,
        "input": m.input_price, "output": m.output_price,
        "cache_write": m.cache_write, "cache_read": m.cache_read,
        "cache_write_hour": m.cache_write_hour,
        "long_over": m.long_context_over, "cutoff": m.cutoff,
    }
