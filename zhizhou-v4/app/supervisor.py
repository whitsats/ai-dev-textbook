"""多智能体编排：一个调度者 ＋ 三个专业角色，而**交接次数是账上的一个数**。

3.7 用手写的 `orchestrator.py` 做过同一件事（检索者 / 写作者 / 审校者三角色交接），
那时交接契约是一个函数返回值里的元组。这一章把它装成一张图，于是三件事第一次可以量：

1. **调度者的决策是一次模型调用，还是一个纯函数？** 两条路都能跑，代价不同：
   模型的判断更宽，但它会漂；纯函数可测，但它只会做你写死的判断。
2. **交接必须有限额。** 两个角色互相委派时，图不会自己停下来——它会一直转到
   `recursion_limit` 抛 `GraphRecursionError`。限额不是一个「保险」，而是**流程的一部分**。
3. **交接有两种载体**：状态里放一个 `next` 键（由图的条件边读），
   或者节点直接 `return Command(goto=...)`（跳转写在节点里）。
   后者更短，但**目标名写错不会报错**——第 4 节的读数里有一条就是这个。

与 4.4 那张流水线图的分工：4.4 的图是**一条**工序链（摘要 → 起草 → 自评 → 发布），
这一章是**一个团队**（调度者决定谁上场，角色干完再回到调度者）。前者管步骤，
后者管分工——同一个 `StateGraph`，两种拓扑。
"""
from __future__ import annotations

import operator
from typing import Annotated, Literal, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command
from pydantic import BaseModel, Field

# 三个角色的名字**就是节点名**：调度者返回的字符串直接当路由键，
# 少一层「角色名 → 节点名」的映射，也就少一处能写错的地方。
SPECIALISTS = ("researcher", "writer", "reviewer")

# 每个角色产出写到哪个通道。写成一张表而不是散在三个函数里，
# 是因为第 5 节要**逐个通道核对**「谁写了它」——散着写就没法机械核对。
OUTPUT_KEY = {"researcher": "brief", "writer": "draft", "reviewer": "verdict"}

SYSTEM = {
    "researcher": "你是知舟的检索者。只列与任务直接相关的事实，不做推断，不写建议。",
    "writer": "你是知舟的写作者。只依据给定的要点写稿，不补写要点里没有的事实。",
    "reviewer": "你是知舟的审校者。只判断稿件有没有超出给定要点，输出 通过 或 重写。",
}


class Route(BaseModel):
    """调度者的**结构化输出**：四个出口与一句理由。

    为什么要带 `reason`：调度记录是这一章的核心证据（第 5 节要按它核对「谁决定了什么」）。
    `Literal` 让服务端**只能**从这四个值里挑一个——但那不等于它一定会挑对，
    4.2 量过这件事：结构化输出保证形状，不保证语义。
    """

    next: Literal["researcher", "writer", "reviewer", "done"] = Field(
        description="下一步交给谁；全部完成时给 done")
    reason: str = Field(default="", description="一句话说明为什么这么派")


class TeamState(TypedDict):
    """团队的状态。前五个键是**接口**，后四个是内部账。

    `handoffs` 用累加归约器（`operator.add`）而不是「覆盖式自增」，与 4.4 同一条理由：
    角色节点只描述「我交了一次」，总数由归约器去加——并行或重放时才不会算错。
    """

    task: str
    brief: str
    draft: str
    verdict: str
    answer: str
    next: str
    hops: Annotated[list[str], operator.add]
    handoffs: Annotated[int, operator.add]
    max_handoffs: int
    route_log: Annotated[list[str], operator.add]


class TeamInput(TypedDict):
    """调用方只该给这两个键 ＋ 一个可调的上限（与 4.4 的输入 schema 同理）。"""

    task: str
    max_handoffs: int


class TeamOutput(TypedDict):
    answer: str
    hops: list[str]


# --------------------------------------------------------------------------- 调度
def decide_by_rules(state: TeamState) -> tuple[str, str]:
    """**纯函数版调度者**：按三个通道有没有值决定谁上场。返回 `(角色, 理由)`。

    写成纯函数不是「简化」，而是这一章要量的对照物。它有一条模型做不到的性质：
    **同一个状态永远给出同一个答案**。所以第 4 节那两组读数（交接上限、
    ping-pong）才能一次次复现——模型进来的话，同一张图跑两遍就不是同一件事了。

    三个通道全部用 `.get(..., "")` 读，**这不是防御性编程的洁癖**：本图挂了
    输入 schema（调用方只该给 `task` 与 `max_handoffs`），于是 `initial_team_state()`
    里写好的 `brief=""` 等初值**在入口就被过滤掉了**，第一次读它们时通道里什么都没有，
    直接下标会抛 `KeyError: 'brief'`（本模块第一版就是这么挂的）。
    4.4 的 `max_rounds` 是同一个坑的另一种症状：那次报错指向条件边的路由函数。
    """
    handoffs = state.get("handoffs", 0)
    if handoffs >= state.get("max_handoffs", 0):
        return ("done", f"限额用尽（已交接 {handoffs} 次）")
    if not state.get("brief"):
        return ("researcher", "缺要点")
    if not state.get("draft"):
        return ("writer", "缺草稿")
    if not state.get("verdict"):
        return ("reviewer", "缺审校结论")
    if state["verdict"].strip().startswith("通过"):
        return ("done", "审校通过")
    # 审校没通过：退回写作者，但**只有还有限额的时候**才退得回去
    return ("writer", "审校未通过，退回重写")


def model_supervisor(model, reason_chars: int = 40):    # noqa: ANN001
    """**模型版调度者**：一次结构化输出调用，返回 `(角色, 理由)`。

    它替掉的是上面那个纯函数，接口完全一样——**换调度器不用改图**。
    真机那一路用它。理由截断到 `reason_chars`：路由的理由是要进日志的，
    而日志里贴模型的长篇解释会把一次运行的关键信息淹掉（3.8 的脱敏与 3.9 的追踪同一条纪律）。
    """
    router = model.with_structured_output(Route, method="function_calling")

    def decide(state: TeamState) -> tuple[str, str]:
        prompt = [
            SystemMessage("你是知舟的调度者。只从 researcher / writer / reviewer / done "
                          "里挑一个下一步，并用一句话说明理由。"),
            HumanMessage(f"任务：{state.get('task', '')}\n"
                         f"要点：{state.get('brief') or '（空）'}\n"
                         f"草稿：{state.get('draft') or '（空）'}\n"
                         f"审校：{state.get('verdict') or '（空）'}\n"
                         f"已交接 {state.get('handoffs', 0)}/"
                         f"{state.get('max_handoffs', 0)} 次"),
        ]
        out: Route = router.invoke(prompt)
        nxt = out.next
        if state.get("handoffs", 0) >= state.get("max_handoffs", 0) and nxt != "done":
            # **限额由框架外的这一行兜住**：模型不认识你的预算，所以「谁说了算」要写清楚，
            # 不能指望它自己数。4.3 的两个上限不对账，是同一件事的另一种形态。
            return ("done", f"模型想派 {nxt}，但限额已用尽")
        return (nxt, out.reason.strip()[:reason_chars])

    return decide


# --------------------------------------------------------------------------- 角色
def make_specialist(name: str, model=None, *, real: bool = False):    # noqa: ANN001
    """造一个角色节点。**它只写自己那个通道**，然后记一行交接账。

    离线时角色是**规则式**的（把任务截一段），理由与 4.4 的 `draft_node` 相同：
    这一章量的是编排，不是每个角色的文笔；模型混进来会让「交接了几次」这件事带上随机性。
    真机时才让模型写，因为那时要的是「这套编排在真模型上跑不跑得通」。
    """
    key = OUTPUT_KEY[name]

    def node(state: TeamState) -> dict:
        task = state.get("task", "")
        brief = state.get("brief", "")
        if real and model is not None:
            out = model.invoke([SystemMessage(SYSTEM[name]),
                                HumanMessage(f"{task}\n要点：{brief or '（空）'}")])
            text = str(out.text).strip()
        elif name == "researcher":
            text = "要点：" + task[:60]
        elif name == "writer":
            text = f"《{task[:20]}》" + brief[:80]
        else:
            # 审校者的规则式判断：草稿里出现了要点里的关键词就算通过。
            # **这是刻意的粗糙**——它要能在离线里复现「通过 / 不通过」两条路。
            ok = bool(brief) and brief[-10:] in state.get("draft", "")
            text = "通过：与要点一致" if ok else "重写：草稿没写全要点"
        return {key: text, "handoffs": 1,
                "hops": [f"{name} -> {key}（{len(text)} 字）"]}

    node.__name__ = f"{name}_node"
    return node


def supervisor_node(state: TeamState, *, decide=decide_by_rules) -> dict:    # noqa: ANN001
    """调度节点：问一次「下一步谁上场」，把决定写进账里（**它自己不干活**）。

    它只返回 `route_log` 一行，不改任何业务通道——这样「谁决定」与「谁干活」
    在日志里是两行不同的东西，第 5 节按这个分界核对交接契约。
    """
    nxt, reason = decide(state)
    update: dict = {"next": nxt, "route_log": [f"supervisor -> {nxt}（{reason}）"]}
    if nxt == "done":
        # 收口时才写 `answer`：它是**输出 schema 里的键**，所以「没写过」与
        # 「写了空串」在返回值里长得一样（4.4.7 那条读数的复用）。
        update["answer"] = (state.get("draft") or state.get("brief")
                            or state.get("task", ""))
    return update


def route_after_supervisor(state: TeamState) -> str:
    """条件边的映射函数：**键是 `next` 的值**（4.4 那条错法在这里又出现一次）。"""
    return state["next"]


# --------------------------------------------------------------------------- 装配
def build_team(model=None, *, checkpointer=None,                     # noqa: ANN001
               real: bool = False, decide=None):                     # noqa: ANN001
    """调度者 ＋ 三个角色 ＋ 两条边。**角色的出口回到调度者**，图才成环。

    这个环必须有一个**会自己到的出口**（`done`），否则唯一能停下图的东西是
    `recursion_limit`——而那是一个异常，不是一个结果（第 4 节的第一条读数）。

    **这里没有 `max_handoffs` 参数**，尽管它是这张图最要紧的数：上限住在**状态**里
    （`initial_team_state(task, max_handoffs=...)` 传进去），因为它是「这一次运行」的输入，
    而不是「这张图」的构造参数。构造参数只能有一个值，状态可以每一次都不一样——
    订错了地方，同一张图就没法跑两种预算的对照。
    """
    decide = decide or (model_supervisor(model) if (real and model is not None)
                        else decide_by_rules)
    builder = StateGraph(TeamState, input_schema=TeamInput, output_schema=TeamOutput)
    builder.add_node("supervisor", lambda s: supervisor_node(s, decide=decide))
    for name in SPECIALISTS:
        builder.add_node(name, make_specialist(name, model, real=real))
    builder.add_edge(START, "supervisor")
    builder.add_conditional_edges("supervisor", route_after_supervisor,
                                  {name: name for name in SPECIALISTS} | {"done": END})
    for name in SPECIALISTS:            # 每个角色干完都回到调度者：这就是「团队」的形状
        builder.add_edge(name, "supervisor")
    return builder.compile(checkpointer=checkpointer)


def build_team_with_goto(model=None):    # noqa: ANN001
    """另一种交接载体：**跳转写在节点里**（`Command(goto=...)`），图上没有条件边。

    少一行装配、多一个隐患：目标名写错**不会**在编译期或运行期报错，
    只在日志里留一句 warned 然后当作没写（第 4 节的第三条读数）。
    它值得写出来，因为它是「框架把错误藏起来」的又一例——
    与 4.4 的孤立节点、4.3 的 `when` 谓词失效是同一族。
    """
    builder = StateGraph(TeamState, input_schema=TeamInput, output_schema=TeamOutput)
    builder.add_node("supervisor", _goto_supervisor)
    for name in SPECIALISTS:
        builder.add_node(name, make_specialist(name, model))
    builder.add_edge(START, "supervisor")
    for name in SPECIALISTS:
        builder.add_edge(name, "supervisor")
    return builder.compile()


def _goto_supervisor(state: TeamState) -> Command:
    """`Command(goto=...)` 版调度者：把「记一行」与「去哪」放进**同一个返回值**。"""
    nxt, reason = decide_by_rules(state)
    return Command(goto=END if nxt == "done" else nxt,
                   update={"next": nxt, "route_log": [f"supervisor -> {nxt}（{reason}）"]})


def initial_team_state(task: str, *, max_handoffs: int = 6) -> dict:
    """一次团队运行的输入。**累加键显式给初值**（与 4.4 同一条纪律）。"""
    return {"task": task, "brief": "", "draft": "", "verdict": "", "answer": "",
            "hops": [], "handoffs": 0, "max_handoffs": max_handoffs, "route_log": []}


def new_thread(thread_id: str = "team-1") -> dict:
    """与 4.4 同名同义：它是**恢复的游标**，不是日志里的一个字段。"""
    return {"configurable": {"thread_id": thread_id}}
