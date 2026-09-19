"""v4 的状态编排：把「一次请求」从一串链变成一张图。

对照点。v3 里「摘要 → 起草 → 审 → 改 → 发」这条流程是**一个函数里的 if 与 while**：

    app/agent/orchestrator.py   交接契约 ＋ 预算按份切 ＋ 指纹去重（3.7）
    app/agent/loop.py           循环与终止条件；`approve` 是一个**进程内回调**（3.8、4.3）

v4 里它是同一张图的四种零件：

    State    一个 `TypedDict` ＋ 每个键各自的 reducer（默认覆盖，`Annotated` 才累加）
    Node     干活的函数，只返回**要改的字段**
    Edge     普通边 ＝ 必定走；条件边 ＝ 由函数决定下一步（循环就是条件边指回自己）
    Compile  结构检查 ＋ 挂上 checkpointer（中断的前提）

三件事在这一章第一次成为**可读的数**，而不是「框架替你做了」：

1. **`recursion_limit` 数的是 super-step**，一个节点一次算一步；4.3 在 `create_agent`
   上量到的是「一次模型往返占 2 步」，这一章要把它拆成图上的最小例子（见 4.4.4）。
2. **没写进 schema 的键会被静默丢掉**——不报错、不警告，`invoke` 回来连键都没有（4.4.2）。
3. **同一个 super-step 里两个节点写同一个没有 reducer 的键会抛 `InvalidUpdateError`**
   ——「并行分支要不要 reducer」这件事因此不是风格问题（4.4.5）。

中断（`interrupt`）放在 4.4.8，不在 4.3：工具层那次是「一次调用等人」，这一次是
**整张图停在一个检查点上**，而它能停的前提正是这一章的图与状态。
"""
from __future__ import annotations

import operator
from typing import Annotated, Literal, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

# 起草一稿的目标长度与每轮多摘一段：**自评的判据是它，不是「模型说好不好」**。
# 3.9 的结论在这里继续用：能确定性算出来的东西，不要交给模型去打分。
# 两个值一起决定了「循环跑几轮」：第 1 轮约 171 字（不够）、第 2 轮约 251 字（够）——
# 而正文短的时候两轮都不够，于是它走的是**另一个出口**（预算用尽）。
DRAFT_TARGET_CHARS = 200
PER_ROUND_CHARS = 160
MAX_ROUNDS = 2

# 系统提示与 v3 的 `app/agent/prompts/agent.md` 是同一份口径里的一句话，
# 但**不共用文件**：v3 的提示文件要给手写循环的装配用，格式是它自己的。
DRAFT_SYSTEM = "你是知舟的起草助手。只依据给定的正文写稿，不补写正文里没有的事实。"
SUMMARY_SYSTEM = "你是知舟的摘要助手。只陈述正文写过的事实，不评论、不推荐。"


# ---------------------------------------------------------------------------
# 一、状态：一份 TypedDict，但每个键的合并规则各写各的
# ---------------------------------------------------------------------------
class PipelineInput(TypedDict):
    """图的**输入** schema：调用方只该给这两个键，外加一个可调的上限。

    **这三个键是白名单，不是「建议」**：`invoke` 传进来的键只要不在这份 schema 里，
    就会被**静默丢掉**——不报错、不警告，连 `initial_state()` 里写好的初值也进不去。
    第一版就把 `max_rounds` 漏在这里，拿到的是 `KeyError: 'max_rounds'`，
    而栈顶指的是条件边的路由函数（一个**指向错地方的错**，见 4.4.3）。
    """

    article: str
    title: str
    max_rounds: int


class PipelineOutput(TypedDict):
    """图的**输出** schema：`invoke` 只回这三个键。

    这一点和普通函数的返回值是同一件事：**内部账目不必是接口**。
    但官方文档有一句必须记住的警告——`stream_mode="values"` 默认吐**全部**通道，
    私有键只对 `invoke` 隐身、不对流隐身（4.4.7 有读数）。
    """

    summary: str
    draft: str
    approved: bool


class PipelineState(TypedDict):
    """图的**内部** schema：输入 ＋ 输出 ＋ 中间账目。

    reducer 只出现两次，而这两次正好覆盖两种需求：
      * 不写 `Annotated` 的键 → **覆盖**（`summary`、`draft`、`approved` 都是「最后一次为准」）；
      * 写 `Annotated[..., operator.add]` 的键 → **累加**（`revisions`、`log`、`rounds`）。

    `rounds` 用 `operator.add` 而不是「覆盖式自增」有个实际原因：
    节点返回 `{"rounds": state["rounds"] + 1}` 在**并行**或**重放**时都会出错，
    而返回 `{"rounds": 1}` 由 reducer 加，节点就变成**只描述自己做了什么**。
    """

    article: str
    title: str
    summary: str
    draft: str
    approved: bool
    revisions: Annotated[list[str], operator.add]
    log: Annotated[list[str], operator.add]
    rounds: Annotated[int, operator.add]
    max_rounds: int


def draft_node(state: PipelineState) -> dict:
    """起草一稿。**只返回它改的字段**——返回整个 state 不会报错，但会让 reducer 白写。

    每重跑一轮就多摘一段正文，所以这一稿一定比上一稿长：循环由此**有收敛方向**。
    """
    article = state["article"]
    n = state.get("rounds", 0) + 1            # 这是**这一次**要加的 1，不是「总数」
    text = f"【草稿 {n}】{state['title']}：{article[:PER_ROUND_CHARS * n]}"
    return {"draft": text, "revisions": [text], "rounds": 1,
            "log": [f"draft#{n} {len(text)} 字"]}


def review_node(state: PipelineState) -> dict:
    """自评：**确定性规则**，不是模型打分。它决定下一步走哪条边。

    规则放在函数里而不是提示里，是因为它要能进测试：`len(draft) >= 目标 → 通过`。
    """
    draft = state["draft"]
    ok = len(draft) >= DRAFT_TARGET_CHARS
    return {"log": [f"review {'pass' if ok else 'revise'} ({len(draft)} 字)"]}


def route_after_review(state: PipelineState) -> Literal["draft", "publish"]:
    """条件边的决策函数：返回**边的名字**，映射表把它翻成节点名。

    两个出口的顺序不能反：先判「够不够好」，再判「还有没有预算」。
    反过来写的话，轮数用尽时会直接发布一份没通过的草稿。
    """
    if len(state["draft"]) >= DRAFT_TARGET_CHARS:
        return "publish"
    if state["rounds"] >= state["max_rounds"]:
        return "publish"
    return "draft"


def publish_node(state: PipelineState) -> dict:
    """发布：**在这里停一次等人**。

    `interrupt()` 的返回值就是 `Command(resume=...)` 传进来的那个值，
    而节点在恢复后会**从头重跑**——所以这行之前不能有副作用（官方文档明写）。
    本节点前半段只有一个赋值，正是为了守住这条。
    """
    answer = interrupt({"ask": "发布这份草稿吗？", "title": state["title"],
                        "chars": len(state["draft"])})
    approved = answer is True
    return {"approved": approved,
            "log": [f"publish {'approved' if approved else 'rejected'}"]}


# ---------------------------------------------------------------------------
# 二、子图：把「摘要」这一步装成一张独立的图，再当节点用
# ---------------------------------------------------------------------------
class SummaryState(TypedDict):
    """子图自己的状态。它**只**需要正文与摘要两个键。"""

    article: str
    summary: str


def summary_subgraph(model) -> object:      # noqa: ANN001 —— 返回编译后的图
    """一张只做摘要的小图，供主图当节点用。

    为什么值得这么做：摘要这一步在 v3 里是 `services/` 里一个函数，在 v4 的 4.2 里是一条链，
    到了这一章它有三种身份可挑——**链、函数、图**。挑图的唯一理由是
    「它自己将来要分叉」（比如换成 4.2 的四种结构化策略按服务商能力选一种）。
    现在它只有一步，所以这张子图的价值在演示**接口**：主图不需要知道里面有几步。
    """
    def summarize_node(state: SummaryState) -> dict:
        out = model.invoke([SystemMessage(SUMMARY_SYSTEM),
                            HumanMessage(state["article"])])
        return {"summary": str(out.text)[:200]}

    builder = StateGraph(SummaryState)
    builder.add_node("summarize", summarize_node)
    builder.add_edge(START, "summarize")
    builder.add_edge("summarize", END)
    return builder.compile()


# ---------------------------------------------------------------------------
# 三、装配
# ---------------------------------------------------------------------------
def build_pipeline(model, *, checkpointer=None, with_summary: bool = True):   # noqa: ANN001, ANN401
    """把节点与边连成图。`checkpointer=None` 时可以跑，但**不能中断**。

    中断需要两样东西同时到位：一个 checkpointer（把停在哪一步记下来）与
    一个 `thread_id`（下次从哪条线程继续）。少任何一样，`interrupt` 都不会抛错——
    它会停下来并把 `__interrupt__` 交给你，而**你再也无法继续**（4.4.8 有读数）。
    """
    builder = StateGraph(PipelineState, input_schema=PipelineInput,
                         output_schema=PipelineOutput)
    builder.add_node("draft", draft_node)
    builder.add_node("review", review_node)
    builder.add_node("publish", publish_node)
    if with_summary:
        # 子图当节点：**名字对齐即可**——子图的 `article` 从主图同名通道读，
        # 它返回的 `summary` 写回主图同名通道。这正是官方说的「共享状态键」。
        builder.add_node("summary", summary_subgraph(model))

    builder.add_edge(START, "draft")
    builder.add_edge("draft", "review")
    builder.add_conditional_edges("review", route_after_review,
                                  {"draft": "draft", "publish": "publish"})
    builder.add_edge("publish", END)
    if with_summary:
        # 摘要与起草**互不依赖**，所以并联：两条边都从 START 出发。
        # 但 `summary` 与 `draft` 写的是不同的键，因此这里不需要 reducer（4.4.5 的反面）。
        builder.add_edge(START, "summary")
        builder.add_edge("summary", END)
    return builder.compile(checkpointer=checkpointer)


def new_thread(thread_id: str = "zhizhou-1") -> dict:
    """中断要的那个 `thread_id`：它是**恢复的游标**，不是日志里的一个字段。

    换一个 `thread_id` 就是一条新线程、一份空状态；沿用同一个才会接到上次那一步。
    """
    return {"configurable": {"thread_id": thread_id}}


def initial_state(article: str, title: str, *, max_rounds: int = MAX_ROUNDS) -> dict:
    """一次运行的输入。**累加型键要显式给初值**（`rounds` 给 0、两个列表给空表）。

    不给也不会报错——`operator.add` 的 reducer 第一次接到的左值是「没有」，
    框架会用类型提示去推一个空值；但那是**推断**，不是契约（4.4.1 有读数）。
    """
    return {"article": article, "title": title, "summary": "", "draft": "",
            "approved": False, "revisions": [], "log": [], "rounds": 0,
            "max_rounds": max_rounds}
