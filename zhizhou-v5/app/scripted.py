"""离线剧本模型：**确定性地扮演两种行为**，好让「有没有资料」的差别可以反复复现。

它不是一个「假 AI」，它是一台**行为可预期**的替身，用途和 4.1 起一直在用的剧本模型一样：

- **无资料时**：对私有事实给一个流畅但错的答案（`FABRICATED` 那张表）。
  这一路演示的是「幻觉的**形态**」——听起来完全合理、没有一句可疑的话，
  但每个数字都是编的。有一点必须强调：**离线这一路是脚本写死的，所以它每次都错**；
  真机上模型可能直接拒答（读数第 ④ 组会把它量出来）。**「一定错」与「可能错」是两个结论**，
  别把脚本的行为当成模型的行为。
- **有资料时**：把召回到的前 `max_chunks` 片**原文照抄**下来，每片句末标它的编号。

第二条要解释一下为什么是「照抄」：剧本模型不会概括、不会改写，
所以它**不可能**把资料说错——离线这一路因此证明的只有一件事：
**装配是对的**（资料进了提示、编号标得对、引用核对能跑）。
它证明不了「生成质量」，那是真机与 5.6 评测集的活。
这个限制同时是本章第 ③ 组读数的前提：**引用格式全对、内容却是错的**这件事，
只能由真机（或一个会犯错的模型）演示出来。

刻意不做的事：不联网、不看时钟、不用随机数。同一个输入永远同一个输出——
离线这一路能进提交门，全靠这一点。
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from app.corpus import Chunk
from app.rag import NO_ANSWER

#: 直答那一路的「编造表」。**这就是本章要展示的病**：每一条都答得像真的。
FABRICATED = {
    "知舟的发布说明必须包含哪几段？":
        "知舟的发布说明包含三段：变更摘要、影响面与验证步骤。"
        "如需更详细的模板，可参考团队内部的文档规范。",
    "知舟 2026 年第三季度的月调用预算上限是多少？":
        "知舟 2026 年第三季度的月调用预算上限是每月 1,200 万词元，"
        "达到 70% 时会触发告警。",
    "用户连点两下会不会写两条记录？":
        "不会。数据库层有唯一索引兜底，重复的写入请求会被直接忽略。",
    "知舟 2027 年的营收目标是多少？":
        "知舟 2027 年的营收目标是 3.5 亿元，较上一年增长约 40%。",
}

#: 提示里资料的渲染格式（与 `app.rag.render_context` 必须一致）。
_CONTEXT_LINE = re.compile(r"\[(\d+)\]\s([^｜]+)｜(.*)")


@dataclass
class ScriptedModel:
    """`call(messages) -> str`。**与真实模型的调用签名完全一致**（见 `app.rag.answer`）。"""

    #: 最多照抄几片。这一条决定了「带资料的答案」有多长——第 ①② 组读数的字数差就来自它。
    max_chunks: int = 2
    #: 记账：跑了多少次、其中多少次是带资料的
    calls: int = 0
    grounded_calls: int = 0

    def __call__(self, messages: list[dict]) -> str:
        self.calls += 1
        system = messages[0]["content"]
        user = messages[-1]["content"]
        question = user.rsplit("问题：", 1)[-1].strip()
        if "资料：" not in system + user:
            return FABRICATED.get(question, "我不确定这个问题，但可以先从三方面来看……")
        self.grounded_calls += 1
        chunks = _parse_context(user)
        if not chunks:
            # 一片都没召回：契约要求说「未提及」，而不是硬答（5.5 把这条写完整）
            return NO_ANSWER
        return " ".join(f"{c.text.strip()} [{i}]" for i, c in enumerate(
            chunks[: self.max_chunks], start=1))


def _parse_context(user: str) -> tuple[Chunk, ...]:
    """把提示里渲染好的资料**再解析回来**——这一步是故意的。

    剧本模型走的是和真实模型同一条路：它只看得见提示里的文字，
    看不见 `Chunk` 对象。这样「提示里到底放了什么」才真的被试到了；
    如果直接把 chunks 传进去，提示渲染错了也测不出来。
    """
    if "资料：" not in user:
        return ()
    block = user.split("资料：", 1)[1].split("\n\n问题：", 1)[0]
    out = []
    for line in block.splitlines():
        m = _CONTEXT_LINE.match(line)
        if m:
            doc_id, _, idx = m.group(2).partition("#")
            out.append(Chunk(doc_id=doc_id, index=int(idx), text=m.group(3)))
    return tuple(out)
