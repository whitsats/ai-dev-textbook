"""门禁与必需检查：**「没跑」不是一个结论，它是两个相反的结论。**

这一块是 8.2 里最短的一块，而它用的是本章最锋利的两句官方口径：

> 被跳过的 job 会把状态报成 **Success**。即使它是必需检查，它也不会阻止 PR 合并。

> 如果工作流因**路径过滤、分支过滤或提交信息**被跳过，那么与它相关的检查会**停留在 Pending**；
> 要求这些检查通过的 PR **会被挡住合并**。

两句话放在一起，得到这一块的主结论：**同样是「没跑」，写在 `jobs.<id>.if:` 上就是把门拆掉，
写在 `on.<event>.paths:` 上就是把门焊死**——而这两行在配置文件里的差别只有一个词。
前者的现场是「门开着、没人看过」，后者的现场是「谁都过不去，包括只改了一份文档的人」。

官方给「必需检查」的合格结论只有三种：`successful`、`skipped`、`neutral`。
于是七种形状可以按**它报出什么**分成四组：真绿、绿而没验、停在 Pending、跑了却被取消。
最后一组（`cancelled`）不在这三种里——而它的现实表现最容易被读错：
**那一格从没给出过结论，而 PR 上它看起来像是「跑过了」。**
"""

from __future__ import annotations

from dataclasses import dataclass

#: 四组的分名。这一栏是**人写下来的分类**（它决定了正文那张表怎么读）。
CATEGORIES = ("真绿", "绿而没验", "停在 Pending（挡）", "跑了却被取消（挡）")


@dataclass(frozen=True)
class Shape:
    """一种结论。`reported` 是它报出来的东西（`None` ＝ 连 check run 都没有）。"""

    name: str
    level: str                 # job / workflow / step / run
    category: str
    reported: str | None       # success / cancelled / None（没有 check run）
    seen: str                  # 在 PR 上看起来是什么
    blocks: bool               # 会不会挡住合并
    why: str


SHAPES: tuple[Shape, ...] = (
    Shape("job 跑完并通过", "job", "真绿", "success", "绿", False,
          "正常——这一格真的验过"),
    Shape("job 级 `if:` 不成立", "job", "绿而没验", "success", "绿", False,
          "官方：被跳过的 job 报 Success，**即使它是必需检查也不挡合并**"),
    Shape("`continue-on-error: true` 的那一步红了", "step", "绿而没验", "success", "绿", False,
          "这一步失败不改变 job 的结论——**外面绿、里面红**"),
    Shape("workflow 级 `paths` 过滤挡住", "workflow", "停在 Pending（挡）", None, "Pending", True,
          "官方：因路径过滤被跳过时检查停在 Pending，要求它的 PR 被挡"),
    Shape("提交信息带 `[skip ci]`", "workflow", "停在 Pending（挡）", None, "Pending", True,
          "同上；而且这一招只对 push／pull_request 生效"),
    Shape("矩阵里被 `fail-fast` 取消的兄弟", "job", "跑了却被取消（挡）", "cancelled", "已取消", True,
          "取消的格**从没跑过**，而 `cancelled` 不在合格的三状态里"),
    Shape("被 `concurrency` 取消掉的旧 run", "run", "跑了却被取消（挡）", "cancelled", "已取消", True,
          "同一个 group 只留最新一次；被取消的那个 run 仍然挂在 PR 上"),
)


def verdict(shape: Shape) -> dict:
    """这一格的账：报出什么、看起来是什么、放不放行、机制是哪一句。"""
    return {
        "shape": shape.name,
        "level": shape.level,
        "category": shape.category,
        "reported": shape.reported or "（没有 check run）",
        "seen": shape.seen,
        "verdict": "挡" if shape.blocks else "放行",
        "why": shape.why,
    }


def groups() -> dict[str, tuple[str, ...]]:
    """把七种形状按分组归拢——**这就是「没跑」为什么有两种相反后果**。"""
    out: dict[str, list[str]] = {name: [] for name in CATEGORIES}
    for shape in SHAPES:
        out[shape.category].append(shape.name)
    return {name: tuple(names) for name, names in out.items()}


def gate_table() -> list[dict]:
    return [verdict(s) for s in SHAPES]
