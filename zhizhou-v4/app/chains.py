"""v4 的编排：用 `|` 把「提示 → 模型 → 解析」连起来。

对照点。v3 里这条路径是一个函数：

    def summarize(cfg, article) -> ArticleSummary:
        prompt = render(prompt_file, article=article)      # 手拼
        raw = chat(cfg, [...], schema=ArticleSummary....)   # 手传 schema
        return validate(json.loads(raw))                    # 手校验

v4 里它是**一个对象**：

    chain = SUMMARY_PROMPT | model | StrOutputParser()

`|` 不是语法糖。它的结果是 `Runnable`，于是「能一次跑一条、也能一次跑一批、
也能流式、也能被塞进另一条链」这些能力**从类型上就有**，不需要你为每一种用法再包一层。
这一节要证明的就是这件事——以及它**不**替你做的那些事（见模块末尾）。
"""
from __future__ import annotations

from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from langchain_core.runnables import Runnable, RunnableLambda, RunnableParallel, RunnablePassthrough

from app.prompts import DRAFT_PROMPT, SUMMARY_PROMPT
from app.schemas import ArticleSummary, ToolAction

# 正文先裁再送。这一刀不是优化，是**预算**（承接 3.1 的上下文预算）：
# 一篇 5,000 字的正文与一篇 1,200 字的正文，摘要质量差别很小，成本差别是四倍。
MAX_ARTICLE_CHARS = 1200


def clip(payload: str | dict, limit: int = MAX_ARTICLE_CHARS) -> dict:
    """把正文裁到上限，并把「裁了没有」变成一个**能读到的字段**。

    返回 `dict` 而不是 `str`：`RunnableLambda` 的输出会喂给下一环，
    而下一环是提示模板——它要的是一个带 `article` 键的映射。
    同时多带一个 `clipped` 键，这样「这次是不是裁过」在链的输出里可查，
    不必靠事后去猜。它是纯函数，所以也能被单独测（不经过任何模型）。
    """
    text = payload.get("article", "") if isinstance(payload, dict) else (payload or "")
    return {"article": text[:limit], "clipped": len(text) > limit}


# 包成 `Runnable` 的那一行本身就是知识点：**普通函数不是 Runnable，`RunnableLambda` 才是**。
# 包一次之后，它能与提示、模型、解析器用同一个 `|` 组合，也能被 `.batch()` 调用。
CLIP = RunnableLambda(clip)


def summary_chain(model) -> Runnable:
    """纯文本摘要：**最朴素的一条链**。输出是 `str`，不做任何结构化保证。"""
    return SUMMARY_PROMPT | model | StrOutputParser()


def structured_chain(model) -> Runnable:
    """结构化摘要：把「解析」这一步换成模型侧的结构化输出。

    `with_structured_output(ArticleSummary)` 返回的就是一个 `Runnable`，
    它的输出**已经是校验过的 `ArticleSummary` 实例**（Pydantic 类进、Pydantic 类出）。
    与 `summary_chain` 的差别不只是「格式更整齐」：一个是 `str`，一个是带字段的对象，
    下游能用类型去取字段，而不是用正则去捞（v3 的 `validate()` 就在做这件事，只是它是手写的）。
    """
    return SUMMARY_PROMPT | model.with_structured_output(ArticleSummary)


def clipped_chain(model) -> Runnable:
    """入参是**裸正文**的一条链：裁剪 → 提示 → 模型 → 解析。

    它与 `summary_chain` 用的是同一个提示模板，但入参形状不同——`summary_chain` 要
    `{"article": ...}`，它要一个 `str`。这不是刻意设计，是 `|` 的自然结果：
    **入参由链的第一环决定**，所以同一条链换个前置步骤就换了接口。
    `describe()` 会把这件事读出来，别靠记。
    """
    return CLIP | SUMMARY_PROMPT | model | StrOutputParser()


def draft_chain(model) -> Runnable:
    """把「该调哪个工具」写成 JSON：少样本提示 ＋ 解析器。

    这一条故意**不用** `with_structured_output`，而是要手写解析——因为工具调用这种场景里，
    模型可能返回一段解释而不是 JSON，那时你需要的是**把解析失败变成可读的字段**，
    而不是一个异常。这由 `tool_call_chain` 那一支负责。
    """
    return DRAFT_PROMPT | model | JsonOutputParser()


def tool_call_chain(model, *, include_raw: bool = False) -> Runnable:
    """工具调用 ＋ 可选保留原文：这是「解析失败要能进指标」的落点。

    官方文档里最容易被跳过的一页：`with_structured_output(..., include_raw=True)` 时，
    输出恒为 `{'raw': BaseMessage, 'parsed': ... | None, 'parsing_error': BaseException | None}`。
    于是「模型今天把 JSON 写坏了」从一个异常变成一条**可以记进指标的数据**（承接 3.9 的失败分档）。
    """
    return DRAFT_PROMPT | model.with_structured_output(ToolAction, include_raw=include_raw)


def parallel_chain(model) -> Runnable:
    """两条独立验收过的链并行跑：`RunnableParallel` 的值是两条链，入参是同一份。

    它证明的是「链是对象」的后半句：两条链可以**各自独立存在**，再组合成一条更宽的链，
    而组合本身不要求它们知道对方存在。代价是一片论文级的账——一次并行就是两次调用，
    见 4.2.6 的读数。
    """
    return RunnableParallel(summary=structured_chain(model), draft=draft_chain(model))


def with_passthrough(model) -> Runnable:
    """`RunnablePassthrough`：把入参原样带下去，让一条链**既产出、又保留输入**。

    为什么需要它：出了问题时第一个要问的是「当时送进去的到底是什么」，
    而链的默认行为是只把最后一环的结果给你。带上原文之后，
    这条链的返回值自己就是一份可复盘的记录（承接 3.9 的内容捕获「默认不记、显式开」）。
    """
    return RunnablePassthrough.assign(result=structured_chain(model))


def describe(chain: Runnable) -> dict:
    """把一条链的形状读出来：输入要什么、输出是什么、中间有几步。

    这是这一节最实用的一段。**链的输入输出是带类型的**，所以它能回答
    「我该传 dict 还是 str」这种问题——答案是读出来的，不是试出来的。
    """
    graph = chain.get_graph()
    return {
        "输入": _schema_name(chain.input_schema),
        "输出": _schema_name(chain.output_schema),
        "步数": len(graph.nodes),
        "节点": sorted(graph.nodes),
    }


def _schema_name(schema) -> str:
    """把 schema 里的字段名列出来。没有名字的（如裸 `str`）就报它的类型名。"""
    fields = getattr(schema, "model_fields", None) or getattr(schema, "__annotations__", None)
    if fields:
        return "{" + ", ".join(sorted(fields)) + "}"
    return getattr(schema, "__name__", str(schema))


# ---------------------------------------------------------------------------
# 这条链**不**替你做什么（第 4.2.7 节，逐条都有读数）
#
#   1. 不替你限流、不替你重试到有界：那是模型出口的事（4.1 的 `build_model`）；
#   2. 不替你记账：`StrOutputParser` 的输入里有用量，但它的输出是 `str`——**账在链外**；
#   3. 不告诉你是哪一步坏了：异常类型能分出「模型失败」与「解析失败」，
#      但分不出「是第 3 条链还是第 7 条」——那要靠 3.9 的追踪层；
#   4. 不替你保证字段的语义：`Field(max_length=120)` 保证不超过 120 字，
#      保证不了这 120 字是不是正文里写过的事实。
# ---------------------------------------------------------------------------
