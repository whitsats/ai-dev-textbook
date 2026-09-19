"""最小检索闭环：**同一句问题、同一个模型，只差「有没有资料」**。

这是 5.1 的全部机关。要做「为什么需要检索增强」这个判断，必须让两条路径**只差一个变量**：

    直答（direct）：   提示 = 问题
    带资料（grounded）：提示 = 资料 ＋ 问题 ＋ 「只能用资料回答，并标出引用编号」

两次调用的模型、温度、问题一字不差；唯一的差别是提示里有没有那几片资料。
如果两条路径换的不止这一个变量，谁的功劳就说不清了——这是 4.3 那条
「同一条路径跑两遍的差可能大于两条路径之差」的同一族纪律：**先控制变量，再谈结论**。

## 引用为什么长这样

带资料那一路要求模型在句末写 `[1]`、`[2]`——编号是**提示里给资料的顺序**。
于是引用是可机检的：编号越界、或者一条引用都不给，都能被 `check_citations` 抓到。
5.1 只做到「抓得到」，5.5 才讲「抓到了怎么办」（回退、重问、还是直接承认不知道）。

## 一条容易被忽略的接口约定

`answer()` 收的是 `call`（一个 `(messages) -> str` 的可调用对象），不是一个模型对象。
离线时传剧本模型、真机时传真实服务商，**这条路径一个字都不用改**。
3.10 起全书用的「离线当门、真机报数」就是靠这个形状做到的。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.corpus import Chunk

#: 拒答标记。模型在资料里找不到依据时必须写这个，而不是编一个答案。
NO_ANSWER = "【资料未提及】"

PROMPT_DIRECT = (
    "你是知舟的助手。请直接回答用户的问题。",
    "问题：{question}",
)

PROMPT_GROUNDED = (
    "你是知舟的助手。**只允许依据下面给出的资料回答**；"
    "资料里没有的就回答 " + NO_ANSWER + "，不要补充任何资料以外的内容。\n"
    "每用到一处资料，在句末标出它的编号，形如 [1]。",
    "资料：\n{context}\n\n问题：{question}",
)

_CITE = re.compile(r"\[(\d+)\]")


@dataclass
class Answer:
    """一次调用的结果。`citations` 是**解析出来的编号**，不是模型说它引了几条。"""

    question: str
    text: str
    grounded: bool
    citations: tuple[int, ...] = ()
    issues: tuple[str, ...] = ()
    meta: dict = field(default_factory=dict)

    @property
    def refused(self) -> bool:
        return NO_ANSWER in self.text

    @property
    def chars(self) -> int:
        return len(self.text.strip())


#: 检索一片都没召回时，提示里要**明明白白写出这件事**，而不是留一段空白。
#: 留空白的话，「没检索」与「检索了但没命中」在提示里长得一模一样——
#: 这一条是被一次实测逼出来的（见下面 `build_messages` 的注释）。
NO_CONTEXT = "（本次检索没有召回任何资料）"


def render_context(chunks: tuple[Chunk, ...]) -> str:
    """把资料渲染成提示里那一段：**一行一片**。编号从 1 开始，顺序就是检索的排序。

    这里连 `cite()`（文档名#段号）一起写进去：模型看不到它，
    但读者与程序都能顺着编号回到原文——「可核对」是引用唯一的意义。

    **「一行一片」是硬契约，不是排版偏好。** 第一版没把片内的换行吞掉，
    于是：渲染出来的片是多行的，而回读时用的是逐行正则——
    **从第二行起的内容静默丢掉了**。表现很迷惑：`调用预算#0` 明明装着
    「每月 2,400 万词元」，而「带资料」的答案在「预算上限是」那里就断了。
    现在在渲染这一侧把所有空白折成单空格：**跨层的契约要么写死在一处，
    要么两边都得会解——而后者在换手时一定会漂。**
    """
    if not chunks:
        return NO_CONTEXT
    return "\n".join(
        f"[{i}] {c.cite()}｜{' '.join(c.text.split())}" for i, c in enumerate(chunks, start=1)
    )


def build_messages(question: str, chunks: tuple[Chunk, ...] | None = None) -> list[dict]:
    """`chunks=None` 是**不检索**（直答）；`chunks=()` 是**检索了但一片都没召回**。

    **这两件事必须能分开表达，第一版没分开、当场就被试出来了。** 原来的写法是
    `PROMPT_GROUNDED if chunks else PROMPT_DIRECT`——于是「召回为空」落到 `else` 上，
    走的是**直答**那条提示，模型于是照旧编了一个答案（实测：Q3 的「带资料」输出
    与直答一字不差）。正确行为恰恰相反：召回为空时最该走的**正是**那条
    「只允许依据资料、没有就说未提及」的提示。

    这类错误的形状值得记下来：**一个用 `if 值` 判分支的地方，把「空」当成了「无」。**
    空列表与 `None` 在 Python 里不等价，但在一个 `if x:` 里会合并成同一个分支。
    """
    system, user = (PROMPT_GROUNDED if chunks is not None else PROMPT_DIRECT)
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user.format(question=question,
                                                context=render_context(chunks or ()))},
    ]


def check_citations(text: str, chunks: tuple[Chunk, ...]) -> tuple[str, ...]:
    """引用核对。返回**问题清单**，空元组才算过。三条规则：

    1. 编号必须在 `1..len(chunks)` 内；
    2. 给了资料、又没写拒答标记，就必须至少有一条引用——
       「一句引用都没有的断言」在这套契约里是非法的；
    3. 拒答时不要求引用（但拒答本身在 5.5 还要过一遍「资料里真的没有吗」，
       5.1 不做这层核对，所以这一条**不是**「拒答一定正确」的保证）。
    """
    nums = tuple(int(m) for m in _CITE.findall(text))
    issues: list[str] = []
    out_of_range = sorted({n for n in nums if not 1 <= n <= len(chunks)})
    if out_of_range:
        issues.append(f"引用编号越界：{out_of_range}（资料只有 {len(chunks)} 片）")
    if chunks and not nums and NO_ANSWER not in text:
        issues.append("给了资料却一条引用都没标")
    return tuple(issues)


def answer(call, question: str, chunks: tuple[Chunk, ...] | None = None, **meta) -> Answer:
    """跑一条路径。`call(messages) -> str`——**这里是离线与真机的唯一分岔点**。

    `chunks=None` 走直答，`chunks=()` 走带资料（而资料是空的）。
    """
    messages = build_messages(question, chunks)
    text = call(messages)
    return Answer(
        question=question,
        text=text,
        grounded=chunks is not None,
        citations=tuple(int(m) for m in _CITE.findall(text)),
        issues=check_citations(text, chunks) if chunks is not None else (),
        meta=meta,
    )
