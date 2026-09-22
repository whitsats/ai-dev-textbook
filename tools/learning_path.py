#!/usr/bin/env python
"""分层学习计划（`LEARNING.md`）的生成器：**不同起点的人，各从哪一章进、到哪一章出。**

    python tools/learning_path.py --sync        # 重生成 LEARNING.md
    python tools/learning_path.py --check       # 与盘上逐字比（提交门 4i/5 与 CI 各跑一次）
    python tools/learning_path.py --self-test   # 24 条夹具

它和 `0.2` 的分工：`0.2` 按**你有多少时间**分叉（180 天／90 天路线），
这里按**你从哪儿来**分叉（四层起点）。两条轴是叠加的——这一份定「读哪些章」，
`0.2` 定「怎么排到日历上」。所以这里不重复排期，只把「章集合」这一个东西说准。

四层各自只是一份**章号集合**，其余全部派生：

- **章数／有效字／练习（基础·进阶·挑战）**：逐章从盘上算。有效字走 `lint_book` 那把
  尺子（汉字 ＋ 15 × 围栏行，与台账／附录同一个数）；练习的级名从 `lint_book._SHAPE_LEVELS`
  借，小节切分从 `revisit.sections` 借——**口径只有一份实现**，这里不另立一套。
- **附带的示例树**：按「篇全含」判定——第 N 篇的章全在这一层里，才把那棵树算给它。
  少一章就不算（`3.10` 没读却说「你会有 Agent 版项目」是假的）。
- **总时数／周数**：一个可复算的式子，三条假设都印在文件里。

三条对账，各自对应一种**不会报错**的漂移：

① **前置闭合**：层里每一章的「前置知识」点到的章，要么在本层里，要么在本层的
   「假定已具备」里。两头都没有，就是把人扔进半路——而计划表看上去仍然完整；
② **四层并集 ＝ 全书**：每一章至少被一层读到。漏掉一章，那一章就成了「没人读过的章」，
   而任何一层的表都不会变难看；
③ **阶段表并集 ＝ 该层的章集合**：阶段表漏一章，读者照表往下走就会跳过它。

一条反向守：每层的章数、四层并集、全书有效字都有**下限**（`_FLOOR`）。扫描退化成空
而 `--check` 照样说「与盘上一致」，是这本书里反复出现的那一课——下限让它变成红色。
"""
from __future__ import annotations

import math
import pathlib
import re
import sys
from dataclasses import dataclass

TOOLS = pathlib.Path(__file__).resolve().parent
ROOT = TOOLS.parent
OUT = ROOT / "LEARNING.md"
BOOK = ROOT / "book"

# 与其它门脚本同一套：把 tools/ 挂进 sys.path，复用它们的**读法**，不复用它们的输出。
sys.path.insert(0, str(TOOLS))
import check_runnable as cr        # noqa: E402
import lint_book as lb             # noqa: E402
import revisit as rv               # noqa: E402

#: 写计划时用的三条假设（读者照着改任一条，就能按自己的节奏重算）。
RATE = 1_200        # 有效字 / 小时：含「把正文里的命令敲一遍」的跟做时间
FIXED_H = 1.5       # 章节固定开销（小时）：做练习、跑树的自检、写笔记
WEEKLY = 12.0       # 每周投入（小时）：平日 1.5 × 5 ＋ 周末 4.5

#: 条数下限。**从盘上量出来的当前规模**；它守的是「扫描退化成空」。
_FLOOR = {"层": 4, "并集章数": 69, "并集有效字": 800_000}


def ids(part: int, *nums: int) -> tuple[str, ...]:
    """`ids(1, *range(9, 16))` → `("1.9", …, "1.15")`。章号只有这一种写法。"""
    return tuple(f"{part}.{n}" for n in nums)


@dataclass(frozen=True)
class Level:
    """一层起点：一份章集合 ＋ 它假定你已具备什么 ＋ 阶段切分。"""

    key: str
    name: str
    who: str                                   # 适合谁（一句话）
    start: str                                 # 起点（你已经会什么）
    end: str                                   # 终点（走完能做什么）
    chapters: tuple[str, ...]
    assumed: tuple[tuple[tuple[str, ...], str], ...]   # (章集合, 为什么可以算「已具备」)
    stages: tuple[tuple[str, tuple[str, ...], str, str], ...]   # (阶段, 章, 做什么, 验收物)
    out: str                                   # 走出去的判据（一条）
    note: str = ""


#: 四层。**手写的只有这张表**：每层的章集合、它假定你已具备什么、阶段怎么切、
#: 每阶段的验收物是什么。其余（章数、字数、练习、树、周数）一律从盘上派生。
LEVELS = (
    Level(
        key="L1",
        name="L1 零基础起步",
        who="没写过程序，或只照着教程抄过几行",
        start="会用电脑、装过软件；没写过代码，或只抄过几行",
        end="能自己写一个带数据库、认证与测试的 API 服务，并会用 AI 助手做第一件事",
        chapters=ids(0, 1, 2, 3) + ids(1, *range(1, 16)) + ("2.1",),
        assumed=(),
        stages=(
            ("认路", ids(0, 1, 2, 3),
             "先读岗位地图，再按 `0.2` 的自评表给自己六个能力层级各打一分，"
             "然后决定走 180 天还是 90 天路线（`0.2` 的两条路线都从这里长出来）。",
             "说出「AI 应用开发岗要的六层能力」，并给自己打完分"),
            ("Python 与 Web 地基", ids(1, *range(1, 9)),
             "从环境搭建开始：语法、数据结构、函数、类、异常、并发、HTTP 一路过。"
             "每一节都把代码敲一遍并跑通——**这一段的功夫全在手上，不在眼里**。",
             "本机跑通第一个 FastAPI 服务，能读报错并自己修"),
            ("把服务写完整", ids(1, *range(9, 15)),
             "FastAPI、Pydantic 校验、依赖注入与中间件、数据库与缓存、认证授权、"
             "三层架构与测试。",
             "一个分层清楚、有单元测试的 API 服务"),
            ("项目实战", ids(1, 15),
             "把前面 14 章拼成知舟博客 API——这是第 1 篇的收口，也是后面所有篇的地基。",
             "「知舟博客 API」：注册登录 ＋ CRUD ＋ 单元测试 ＋ README"),
            ("让 AI 帮你写", ids(2, 1),
             "第一次用 AI 助手改自己的代码：怎么给上下文、怎么验收它的输出、"
             "哪些话不能只听就信。",
             "用 AI 改一处自己的代码，产出工程规则文件与一次代码评审记录"),
        ),
        out="`1.15` 的验收物（测试全绿的 API 服务）＋ `2.1` 的一次 AI 协作记录。",
        note="第 1 篇没有配套的示例树：它的项目由读者自己写，`1.15` 的验收物就是那棵树。",
    ),
    Level(
        key="L2",
        name="L2 会写代码，要补 AI 应用那一半",
        who="在校生／转行者：会一门语言，但没做过 AI 应用",
        start="会一门语言的语法、数据结构、面向对象、异常与基本 HTTP；能自己查文档",
        end="能从文档到答案做出一条完整链路（切分 → 向量 → 混合检索 → 带引用生成），"
            "并有评测报告；外加一个可回滚的多步 Agent",
        chapters=(ids(0, 1, 2, 3) + ids(1, 1) + ids(1, *range(9, 16))
                  + ids(2, *range(1, 7)) + ids(3, *range(1, 11))
                  + ids(4, *range(1, 6)) + ids(5, *range(1, 10))),
        assumed=(
            (ids(1, *range(2, 9)),
             "会一门语言的语法／数据结构／类／异常／并发／HTTP 基础，就不必从 `1.2` 重新学起；"
             "读第 5 篇时若卡在某个细节，按章回查这七章即可"),
        ),
        stages=(
            ("认路与环境", ids(0, 1, 2, 3) + ids(1, 1),
             "岗位地图、能力自评、使用说明，再把环境搭起来（解释器、venv、Git）。"
             "第 1 篇的语法章按需回查，不必通读。",
             "venv 里跑通第一个 API；GitHub 上有一个结构清晰的仓库"),
            ("FastAPI 主线", ids(1, *range(9, 16)),
             "第 1 篇的后半段整段做一遍。它是后面所有篇的地基——"
             "第 3–8 篇的「前置知识」里反复点在它上面。",
             "「知舟博客 API」测试全绿"),
            ("与 AI 协作", ids(2, *range(1, 7)),
             "Claude Code、Codex、AI 编辑器与上下文工程、Harness 流水线。"
             "这一篇不是「工具介绍」，是「怎么把工程规则讲给模型听」。",
             "用 AI 完成一次重构，产出工程规则文件与一次代码评审记录"),
            ("原理", ids(3, *range(1, 10)),
             "Token 与生成参数、提示工程、Agent 是什么、规划与决策、工具调用、"
             "记忆、多 Agent、安全对齐、可观测性。",
             "给项目加一个对话接口；做一次提示版本对比实验并记录结论"),
            ("原理的收束", ids(3, 10),
             "从零到一写一遍 Agent 版知舟——把前九章的概念落成一个能跑的东西。",
             "`3.10` 的 Agent 版项目跑通"),
            ("框架", ids(4, *range(1, 6)),
             "LangChain 核心抽象、提示模板与 LCEL、工具与 Agent、"
             "LangGraph 的状态编排与持久化／多智能体。",
             "LangGraph 多步 Agent：能查数据、能写数据、失败可回滚"),
            ("检索", ids(5, *range(1, 10)),
             "RAG 全景、解析与切分、向量化、混合检索与重排、生成与引用、评测与迭代、"
             "生产级工程、综合项目、项目复盘。",
             "「知舟知识助手」：私有文档问答 ＋ 命中率／忠实度评测报告 ＋ 一份复盘稿"),
        ),
        out="`5.8` 的综合项目 ＋ `5.9` 的复盘稿（这两件是你面试时要讲的东西）。",
        note="第 3、4、5 篇各有一棵可运行树（`zhizhou-v3`／`v4`／`v5`），"
             "每章末尾的离线入口都能自己跑；跑对了它自己会报「离线自检通过」。",
    ),
    Level(
        key="L3",
        name="L3 有工程经验，要把它做成能上线的产品",
        who="后端／全栈转 AI：写过并维护过生产服务",
        start="写过生产服务：数据库、认证、并发、测试、CI 都碰过；缺的是 AI 那一半与交付那一半",
        end="能上线一个多租户、可观测、有成本控制、有评测回归门的生产 AI 服务",
        chapters=(ids(0, 1, 2, 3) + ids(2, *range(1, 7)) + ids(3, *range(1, 11))
                  + ids(4, *range(1, 6)) + ids(5, *range(1, 10))
                  + ids(6, *range(1, 5)) + ids(7, *range(1, 6)) + ids(8, *range(1, 6))),
        assumed=(
            (ids(1, *range(1, 16)),
             "整篇第 1 篇都不必读——它讲的是「从零写一个服务」，而这正是这一层的前提。"
             "只是「写过」与「这一篇要求的那样写」之间还有距离：哪一章点到的写法你不熟，"
             "就单独回查那一章"),
        ),
        stages=(
            ("认路与分工", ids(0, 1, 2, 3),
             "岗位地图、能力自评、使用说明。这一层跳过第 1 篇的理由就写在自评表旁边——"
             "**如果六层能力里有两层打不上分，请从 L1 或 L2 进**（`0.2` 的判据）。",
             "说清这一层读完能做什么，并记下第 1 篇按需回查的入口"),
            ("与 AI 协作", ids(2, *range(1, 7)),
             "这一篇对「已经会写代码」的人不是可选项：它讲的是怎么把工程规则讲给模型听，"
             "后面第 7 篇的提示版本化、第 8 篇的流水线都建在它上面。",
             "用 AI 完成一次重构，产出工程规则文件与一次代码评审记录"),
            ("原理", ids(3, *range(1, 11)),
             "大模型基础到项目实战，10 章一整段。它回答的是「为什么这么写」——"
             "少了这一段，后面所有读数都会变成「照着调参」。",
             "`3.10` 的 Agent 版项目跑通"),
            ("框架", ids(4, *range(1, 6)),
             "LangChain 与 LangGraph：抽象、编排、持久化。",
             "LangGraph 多步 Agent：能查数据、能写数据、失败可回滚"),
            ("检索", ids(5, *range(1, 10)),
             "RAG 从全景到综合项目与复盘，九章一整段。",
             "「知舟知识助手」＋ 评测报告 ＋ 复盘稿"),
            ("模型接入与成本", ids(6, *range(1, 5)),
             "选型三角（能力／价格／上下文窗口）、多厂商方言、网关（路由／重试／降级）、"
             "计量与分流。这一篇的读数都是**算出来的账**，不调模型、不要密钥。",
             "一张能算的账单：把某一章的调用换算成钱，并给出降本前后的对照"),
            ("工程化", ids(7, *range(1, 6)),
             "评测流水线进 CI、可观测性、提示与配置版本化（灰度与 A/B）、"
             "安全落地、数据合规与脱敏。",
             "评测门接进 CI；一次灰度或 A/B 实验的结论"),
            ("交付", ids(8, *range(1, 6)),
             "容器化、CI/CD 与灰度发布、流式前端、多租户与配额计费、线上运维。",
             "部署上线（域名 ＋ HTTPS）＋ 监控看板 ＋ 成本表"),
        ),
        out="一个能演示的线上服务：有域名与监控看板、有成本表、有评测回归门。",
        note="第 6、7、8 篇各有一棵可运行树（`zhizhou-v6`／`v7`／`v8`）。"
             "第 6 篇起**零依赖**——它们不调模型，读数是纯算术，随时能自己跑。",
    ),
    Level(
        key="L4",
        name="L4 求职冲刺",
        who="手上已经有一个跑过的 AI 应用，缺的是「怎么讲、答什么」",
        start="前八篇已经走过一遍：有项目、有读数、有交付物",
        end="一份能过筛的简历、300 字项目讲述稿、一份系统设计答题记录、3 次模拟面试记录",
        chapters=ids(10, *range(1, 8)),
        assumed=(
            (ids(0, 1, 2, 3) + ids(1, *range(1, 16)) + ids(2, *range(1, 7))
             + ids(3, *range(1, 11)) + ids(4, *range(1, 6)) + ids(5, *range(1, 10))
             + ids(6, *range(1, 5)) + ids(7, *range(1, 6)) + ids(8, *range(1, 6)),
             "第 10 篇不教技术：它的每一条题目都要求你手上有一个跑过的项目与一组读数"
             "（它点到的 `3.10`／`5.9`／`6.4`／`7.1`／`8.4`／`8.5` 都是这个意思）。"
             "所以这一层假定前八篇已经走过一遍——**没有项目就不要先读它**"),
        ),
        stages=(
            ("先清点手上的证据", ids(10, 1),
             "简历：把项目写成可信的证据——数字、边界、你负责的那一块。"
             "这一章假定你有东西可写（没有就回 L2／L3）。",
             "一页简历，每条经历后面都有可核对的数"),
            ("讲清项目与设计", ids(10, 2, 3),
             "项目讲述法（STAR、亮点提炼、追问防御）与 AI 系统设计面试的答题结构。",
             "300 字项目讲述稿 ＋ 一份系统设计白板记录"),
            ("补齐题库", ids(10, 4, 5, 6),
             "Agent 考点手册、后端高频、移动端（后两章按目标岗位选读）。"
             "每一章都是一份**可核对的索引**：每个考点都能指回书里那一章与那一条读数。",
             "每个考点都能指回书里那一章"),
            ("打一场模拟", ids(10, 7),
             "五个段落（自我介绍 3／项目讲述 12／系统设计 15／岗位知识 10／反问 5）"
             "共 45 分钟的模拟，以及复盘清单。",
             "3 次模拟面试记录（用 `10.7` 的打分表）"),
        ),
        out="`10.7` 的 3 次模拟记录 ＋ 一页简历：能过筛、能讲清、能被追问。",
        note="第 10 篇不建示例树：它的交付物是简历、讲述稿与模拟记录，不是代码。",
    ),
)


# ------------------------------------------------------------------ 盘上现状

CHAP_REF = lb.CHAP_REF                  # 章号引用：与 lint_book 同一把尺子
CHAP_FILE = re.compile(r"^(\d+\.\d+)-(.*)\.md$")


def cid_key(cid: str) -> tuple[int, int]:
    a, b = cid.split(".")
    return int(a), int(b)


def part_of(cid: str) -> int:
    return int(cid.split(".")[0])


def part_of_tree(spec) -> int:
    """树属于哪一篇：`TreeSpec.label` 写作「（第 N 篇）」。"""
    m = re.search(r"第\s*(\d+)\s*篇", spec.label)
    if not m:
        raise ValueError(f"{spec.tree.name} 的 label 里没有篇号：{spec.label!r}")
    return int(m.group(1))


@dataclass
class Corpus:
    """一次「盘上现状」的快照。派生都走它——夹具才能喂合成状态。"""

    texts: dict[str, str]
    trees: dict[str, int]                 # 树目录名 -> 篇号

    def ids(self) -> tuple[str, ...]:
        return tuple(sorted(self.texts, key=cid_key))

    def part_ids(self, part: int) -> set[str]:
        return {c for c in self.texts if part_of(c) == part}


def load_corpus() -> Corpus:
    texts: dict[str, str] = {}
    for p in sorted(BOOK.glob("*/*.md")):
        m = CHAP_FILE.match(p.name)
        if m:
            texts[m.group(1)] = p.read_text(encoding="utf-8")
    trees = {spec.tree.name: part_of_tree(spec) for spec in cr.SPECS}
    return Corpus(texts=texts, trees=trees)


# ------------------------------------------------------------------ 派生

def effective_words(text: str) -> int:
    """有效字 ＝ 汉字 ＋ 15 × 围栏行。

    与 `lint_book`／台账／附录**同一个数**：公式只有一份实现（`lint_book.han_len`
    与 `lint_book.code_lines_of`），这里只是把它们加起来，不另立一套口径。
    """
    return lb.han_len(text) + lb.CODE_LINE_EQUIV * len(lb.code_lines_of(text))


def practice_counts(text: str) -> dict[str, int]:
    """练习的三级条数。级名从 `lint_book._SHAPE_LEVELS` 借、小节切分从 `revisit` 借。"""
    body = rv.sections(text.splitlines()).get("练习", [])
    out = {lv: 0 for lv in lb._SHAPE_LEVELS}
    for ln in body:
        m = re.match(r"^- \*\*(基础|进阶|挑战)\*\*", ln)
        if m:
            out[m.group(1)] += 1
    return out


def refs_of(text: str) -> set[str]:
    """一章「前置知识」点到的章号。第 0 篇与求职篇允许裁剪这一节，那时返回空集。"""
    body = rv.sections(text.splitlines()).get("前置知识", [])
    return set(CHAP_REF.findall("\n".join(body)))


def compact(cids) -> str:
    """把章号集合压成区间文本：`1.1–1.3、1.9–1.15、2.1`（只在同篇内连续时合并）。"""
    out: list[str] = []
    for part in sorted({part_of(c) for c in cids}):
        minor = sorted(int(c.split(".")[1]) for c in cids if part_of(c) == part)
        i = 0
        while i < len(minor):
            j = i
            while j + 1 < len(minor) and minor[j + 1] == minor[j] + 1:
                j += 1
            out.append(f"{part}.{minor[i]}" if i == j
                       else f"{part}.{minor[i]}–{part}.{minor[j]}")
            i = j + 1
    return "、".join(out)


def assumed_ids(level: Level) -> set[str]:
    out: set[str] = set()
    for group, _ in level.assumed:
        out |= set(group)
    return out


def trees_of(level: Level, corpus: Corpus) -> tuple[str, ...]:
    """按「篇全含」判定：第 N 篇的章全在这一层里，才把那棵树算给它。"""
    out: list[str] = []
    inside = set(level.chapters)
    for name, part in corpus.trees.items():
        ids_of_part = corpus.part_ids(part)
        if ids_of_part and ids_of_part <= inside:
            out.append(name)
    return tuple(sorted(out))


@dataclass
class Stats:
    n: int
    words: int
    practice: dict[str, int]
    trees: tuple[str, ...]
    hours: float

    @property
    def practice_total(self) -> int:
        return sum(self.practice.values())

    def weeks(self, weekly: float = WEEKLY) -> int:
        return math.ceil(self.hours / weekly)


def stats_of(level: Level, corpus: Corpus) -> Stats:
    n = len(level.chapters)
    words = sum(effective_words(corpus.texts[c]) for c in level.chapters if c in corpus.texts)
    practice = {lv: 0 for lv in lb._SHAPE_LEVELS}
    for c in level.chapters:
        if c not in corpus.texts:
            continue
        for lv, k in practice_counts(corpus.texts[c]).items():
            practice[lv] += k
    return Stats(n=n, words=words, practice=practice, trees=trees_of(level, corpus),
                 hours=words / RATE + n * FIXED_H)


def union_ids(levels: tuple[Level, ...] = LEVELS) -> set[str]:
    out: set[str] = set()
    for lv in levels:
        out |= set(lv.chapters)
    return out


# ------------------------------------------------------------------ 对账

def level_issues(levels: tuple[Level, ...], corpus: Corpus) -> list[str]:
    """三条对账（前置闭合／阶段表／并集）＋ 每层自己的形状。返回非空就必须报错。"""
    bad: list[str] = []
    book = set(corpus.ids())
    for lv in levels:
        inside = set(lv.chapters)
        unknown = [c for c in lv.chapters if c not in book]
        if unknown:
            bad.append(f"{lv.name}：点到了盘上没有的章 {compact(unknown)}——"
                       f"章号写错或那一章还没写")
        dupes = sorted({c for c in lv.chapters if lv.chapters.count(c) > 1}, key=cid_key)
        if dupes:
            bad.append(f"{lv.name}：章 {compact(dupes)} 在本层里出现了两次")

        # ① 前置闭合：层里每一章点到的章，要么在本层，要么在「假定已具备」里。
        assumed = assumed_ids(lv)
        refs: set[str] = set()
        for c in lv.chapters:
            if c in corpus.texts:
                refs |= refs_of(corpus.texts[c])
        missing = sorted(refs - inside - assumed, key=cid_key)
        if missing:
            bad.append(f"{lv.name}：前置没闭合——{compact(missing)} 既不在本层，"
                       f"也不在「假定已具备」里（读到这里会半路断掉）")

        # ② 「假定已具备」这一栏自己也要立得住：真实存在、且与「本层要读」互斥。
        for group, why in lv.assumed:
            ghost = [c for c in group if c not in book]
            if ghost:
                bad.append(f"{lv.name}：「假定已具备」里有盘上没有的章 {compact(ghost)}")
            overlap = sorted(set(group) & inside, key=cid_key)
            if overlap:
                bad.append(f"{lv.name}：{compact(overlap)} 同时出现在「本层要读」与"
                           f"「假定已具备」里——两栏互斥")
            if not why.strip():
                bad.append(f"{lv.name}：「假定已具备」的 {compact(group)} 没写理由"
                           f"（凭什么它可以不算）")

        # ③ 阶段表并集 ＝ 该层的章集合（漏一章，读者照表走就会跳过它）。
        staged = [c for _, group, _, _ in lv.stages for c in group]
        twice = sorted({c for c in staged if staged.count(c) > 1}, key=cid_key)
        if twice:
            bad.append(f"{lv.name}：章 {compact(twice)} 出现在两个阶段里")
        skipped = sorted(inside - set(staged), key=cid_key)
        if skipped:
            bad.append(f"{lv.name}：阶段表漏了 {compact(skipped)}——"
                       f"照表走会跳过它们，而表看着是完整的")
        extra = sorted(set(staged) - inside, key=cid_key)
        if extra:
            bad.append(f"{lv.name}：阶段表里有本层没有的章 {compact(extra)}")
        for name, group, what, accept in lv.stages:
            if not group:
                bad.append(f"{lv.name}：阶段「{name}」没有章号")
            if not what.strip() or not accept.strip():
                bad.append(f"{lv.name}：阶段「{name}」缺「做什么」或「验收物」")

    # ④ 四层并集 ＝ 全书：每一章至少被一层读到。
    union = union_ids(levels)
    orphan = sorted(book - union, key=cid_key)
    if orphan:
        bad.append(f"有章没进任何一层：{compact(orphan)}——"
                   f"漏掉的那一章会成为「没人读过的章」，而任何一层的表都不会变难看")
    return bad


def coverage_issues(corpus: Corpus | None = None) -> list[str]:
    """条数下限：扫描退化成空时，`--check` 会安静地说「与盘上一致」。"""
    c = corpus if corpus is not None else load_corpus()
    union = union_ids()
    counts = {"层": len(LEVELS),
              "并集章数": len(union),
              "并集有效字": sum(effective_words(c.texts[x]) for x in union if x in c.texts)}
    bad: list[str] = []
    for key, floor in _FLOOR.items():
        if counts[key] < floor:
            bad.append(f"{key}只数到 {counts[key]:,}（下限 {floor:,}）——"
                       f"扫描退化了，先修读法再谈一致")
    return bad


# ------------------------------------------------------------------ 渲染

HEAD = """\
<!-- 由 `tools/learning_path.py` 生成：重生成 `python tools/learning_path.py --sync`，
     对账 `python tools/learning_path.py --check`（提交门 4i/5 与 CI 各跑一次）。**不要手改。** -->

# 分层学习计划：四种起点，一条主线

> 这一份计划按**你从哪儿来**分四层；`0.2` 按**你有多少时间**分两条路线（180 天／90 天）。
> 两条轴是叠加的——**这一份定「读哪些章」，`0.2` 定「怎么排到日历上」**。
> 全书只用一个项目「知舟」，它在四层里换形态（形态表在 `0.2` 第 5 节）。
"""

HOWTO = """\
## 一、怎么用这份计划

先按一句话对号入座，再看你那一层的表。**四层不是四个难度，是四条入口。**

1. **每一层就是一份章号集合**，别的都是它派生出来的：章数、有效字、练习条数、
   附带的示例树、总时数与周数。集合一变，整张表跟着变——这份文件是生成物，
   `--check` 会在提交时核一遍（口径见 `STYLE` 八·15）。
2. **每层都写清「假定已具备」**。第 1 篇的七章对会 Python 的人是回查材料，对零基础的
   人是主线；同一章在两层里的地位不同，所以「跳过什么」必须写下来，而不是留给读者猜。
   一条硬规矩：**「本层要读」与「假定已具备」互斥**，且每一条假定都要写理由。
3. **时间是估算，而且假设是印出来的**：有效字 ÷ 1,200（每小时，含跟敲）
   ＋ 章数 × 1.5（每章的练习、跑树、写笔记）＝ 总时数；再除以每周投入 12 小时。
   改任一条就能自己重算——这三条是**假设**，不是实测，别把它们读成另一份账。

**四层怎么选**：写不出 for 循环 → L1；会写代码、没做过 AI 应用 → L2；
写过生产服务、要交付上线 → L3；已经有项目、只差面试 → L4。

## 二、四层对照表

“并集”那一行是四层合起来的样子：它的章数与练习数必须等于全书（否则就是有章没人读、
或者某一章被计了两次——两条都由 `--check` 核）。
"""

RHYTHM = """\
## 五、每周节奏（四层共用）

这一张与 `0.2` 的「周节奏模板」是同一张：四个时段加起来就是本文件用的 12 小时／周。

| 时段 | 内容 | 时长 |
| --- | --- | --- |
| 周一至周五 | 读 1 节 ＋ 把该节的代码敲一遍并跑通 | 每天 1–1.5 h |
| 周三 | 只做回顾：把本周前面几节的代码从零重写一次 | 1 h |
| 周六 | 项目时间：把本周的知识点接进主线项目 | 3–4 h |
| 周日 | 输出：写一份笔记／README 段落／一个 issue | 1–2 h |

**在职版**（每周 6 小时）就是把它折半：平日每天 40 分钟、周末一次 3 小时。
每个时段都要**做出一个东西**——这门课里没有「读完了」这种状态，只有「跑出来了」。
"""

RECOMPUTE = """\
## 六、复算入口

这张表是给「不信上面的数」的人用的——本文件里每一个数都能自己跑一遍：

| 命令 | 它核什么 |
| --- | --- |
| `python tools/learning_path.py --check` | 这份计划与盘上逐字一致（层、章集合、字数、练习、树、周数） |
| `python tools/lint_book.py` | 逐章「有效字数 ＝ 汉字 ＋ 15 × 围栏行」——本文件那一列就是它 |
| `python tools/totals.py --check` | 全书与篇级的汇总字数（四层并集那一格必须等于它） |
| `python tools/revisit.py --check` | 体例形状普查（练习的三级标签就是这一列的口径） |
| `python tools/check_runnable.py` | 把某一章的离线入口真跑一遍 |
| `python tools/appendix.py --check` | 六棵树、入口脚本与门脚本速查 |
"""


def fmt(n: int) -> str:
    return f"{n:,}"


def trees_cell(trees: tuple[str, ...]) -> str:
    return "、".join(f"`{t}`" for t in trees) if trees else "无"


def comparison_table(corpus: Corpus) -> list[str]:
    lines = ["| 层 | 从哪儿来 | 章数 | 有效字 | 练习（基／进／挑） | 附带示例树 "
             "| 每周 12 小时 | 在职（每周 6 小时） |",
             "| --- | --- | ---: | ---: | ---: | --- | ---: | ---: |"]
    for lv in LEVELS:
        st = stats_of(lv, corpus)
        p = st.practice
        lines.append(f"| **{lv.key}** | {lv.who} | {st.n} | {fmt(st.words)} | "
                     f"{st.practice_total}（{p['基础']}／{p['进阶']}／{p['挑战']}） | "
                     f"{trees_cell(st.trees)} | 约 {st.weeks()} 周 | "
                     f"约 {st.weeks(WEEKLY / 2)} 周 |")
    union = union_ids()
    words = sum(effective_words(corpus.texts[x]) for x in union if x in corpus.texts)
    practice = {lv: 0 for lv in lb._SHAPE_LEVELS}
    for x in union:
        if x in corpus.texts:
            for k, v in practice_counts(corpus.texts[x]).items():
                practice[k] += v
    all_trees = tuple(sorted({t for lv in LEVELS for t in trees_of(lv, corpus)}))
    lines.append(f"| **并集** | ＝全书 | {len(union)} | {fmt(words)} | "
                 f"{sum(practice.values())}（{practice['基础']}／{practice['进阶']}／"
                 f"{practice['挑战']}） | {trees_cell(all_trees)} | — | — |")
    return lines


def level_block(lv: Level, corpus: Corpus) -> list[str]:
    st = stats_of(lv, corpus)
    p = st.practice
    lines = [f"### {lv.name}", "",
             f"**适合谁**：{lv.who}。",
             f"**起点**：{lv.start}。",
             f"**终点**：{lv.end}。", "",
             f"**规模**：{st.n} 章 ｜ {fmt(st.words)} 有效字 ｜ 练习 {st.practice_total} 条"
             f"（基础 {p['基础']}／进阶 {p['进阶']}／挑战 {p['挑战']}）"
             f" ｜ 示例树 {trees_cell(st.trees)}"
             f" ｜ 约 {st.hours:.0f} 小时（每周 12 小时约 {st.weeks()} 周，"
             f"在职约 {st.weeks(WEEKLY / 2)} 周）。", "",
             "| 阶段 | 章 | 这一阶段做什么 | 走出去的验收物 |",
             "| --- | --- | --- | --- |"]
    for name, group, what, accept in lv.stages:
        lines.append(f"| {name} | {compact(group)} | {what} | {accept} |")
    lines.append("")
    if lv.assumed:
        lines.append("**假定已具备**（不在本层，但本层要用）：")
        lines.append("")
        for group, why in lv.assumed:
            lines.append(f"- {compact(group)}：{why}")
    else:
        lines.append("**假定已具备**：无——这一层从零开始，一个字都不假定。")
    lines += ["", f"**走出去的判据**：{lv.out}"]
    if lv.note:
        lines += ["", f"> {lv.note}"]
    lines.append("")
    return lines


def union_block(corpus: Corpus) -> list[str]:
    book = set(corpus.ids())
    union = union_ids()
    lines = [f"## 四、四层拼起来就是全书", "",
             f"四层的并集是 **{len(union)} 章**（全书 {len(book)} 章）：每一章至少被一层读到。"
             f"下表反过来看——**只在这一层读的章**，就是你换层时真正要补的东西。", "",
             "| 层 | 只在这一层读的章 | 与其它层共有的章 |", "| --- | --- | ---: |"]
    for lv in LEVELS:
        others = union_ids(tuple(x for x in LEVELS if x.key != lv.key))
        own = sorted(set(lv.chapters) - others, key=cid_key)
        lines.append(f"| {lv.name} | "
                     f"{compact(own) if own else '无（它的章都出现在别的层里）'} | "
                     f"{len(lv.chapters) - len(own)} |")
    lines += ["",
              "所以三段路就能走完全书：**L1 → L3 → L4**（L1 给第 1 篇，L3 给第 2–8 篇，"
              "L4 给第 10 篇）。L2 是 L1 与 L3 之间的桥：它把第 1 篇的后半段（`1.9–1.15`）"
              "与第 3–5 篇连起来，让「会写代码但没做过 AI」的人不必先读一遍 `1.2–1.8`。", "",
              "> 第 9 篇是 `PLAN` 里明写的**预留篇（暂不启用）**，所以四层覆盖的章里没有它；"
              "第 10 篇不建示例树是有意的（它的交付物是简历、讲述稿与模拟记录）。"]
    return lines


def render(corpus: Corpus | None = None) -> str:
    c = corpus if corpus is not None else load_corpus()
    lines = HEAD.splitlines() + [""]
    lines += HOWTO.splitlines() + [""]
    lines += comparison_table(c) + [""]
    lines += ["## 三、逐层：从哪一章进、到哪一章出", ""]
    for lv in LEVELS:
        lines += level_block(lv, c)
    lines += union_block(c) + [""]
    lines += RHYTHM.splitlines() + [""]
    lines += RECOMPUTE.splitlines()
    return "\n".join(lines).rstrip("\n") + "\n"


def first_diff(actual: str, want: str) -> str:
    a, b = actual.splitlines(), want.splitlines()
    for i in range(max(len(a), len(b))):
        got = a[i] if i < len(a) else "（没有这一行）"
        exp = b[i] if i < len(b) else "（盘上没有这一行）"
        if got != exp:
            return (f"{OUT.name} 与生成结果不同：首个不同在第 {i + 1} 行\n"
                    f"    盘上：{got[:120]}\n    生成：{exp[:120]}")
    return ""


def check() -> int:
    corpus = load_corpus()
    bad = coverage_issues(corpus) + level_issues(LEVELS, corpus)
    actual = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
    want = render(corpus)
    if not bad:
        diff = first_diff(actual, want)
        if diff:
            bad.append(diff)
    if bad:
        for line in bad:
            print(f"✖ {line}")
        print("\n修法：python tools/learning_path.py --sync（它从盘上读，不手抄）")
        return 1
    union = union_ids()
    # 练习总数按**章**算一次（不按层加——层之间重叠，加起来会重复计数）。
    total_practice = sum(sum(practice_counts(corpus.texts[x]).values())
                         for x in union if x in corpus.texts)
    words = sum(effective_words(corpus.texts[x]) for x in union if x in corpus.texts)
    print(f"✔ {OUT.name} 与盘上逐字相符（{len(want.splitlines())} 行 ｜ "
          f"{len(LEVELS)} 层、{len(union)} 章、{fmt(words)} 有效字、{total_practice} 条练习）")
    return 0


def sync(*, write: bool) -> int:
    corpus = load_corpus()
    bad = coverage_issues(corpus) + level_issues(LEVELS, corpus)
    if bad:
        for line in bad:
            print(f"✖ {line}")
        return 1
    want = render(corpus)
    if not write:
        print(f"（演练）会写出 {len(want.splitlines())} 行到 {OUT.name}")
        return 0
    OUT.write_text(want, encoding="utf-8", newline="\n")
    print(f"✔ 已写出 {OUT.name}（{len(want.splitlines())} 行）")
    return 0


# ------------------------------------------------------------------ 夹具

def _text(*, refs=(), levels=("基础", "进阶"), body="这是正文。", fences=0) -> str:
    """合成一章：前置知识点到的章、练习的三级标签、正文与围栏，各自可控。"""
    lines = ["# 样章", "", "## 前置知识", ""]
    lines += [f"- **{r} 的那一节**：…" for r in refs]
    lines += ["", "## 练习", ""]
    lines += [f"- **{lv}**：做一件事" for lv in levels]
    lines += ["", body]
    for _ in range(fences):
        lines += ["```python", "x = 1", "```"]
    return "\n".join(lines) + "\n"


def _corpus(texts: dict[str, str], trees: dict[str, int] | None = None) -> Corpus:
    return Corpus(texts=dict(texts), trees=dict(trees or {}))


def _level(**kw) -> Level:
    chapters = tuple(kw.pop("chapters", ("1.1",)))
    base = dict(key="X", name="层 X", who="谁", start="起点", end="终点",
                out="判据", note="")
    base.update(kw)
    stages = base.pop("stages", (("唯一阶段", chapters, "做什么", "验收物"),))
    assumed = base.pop("assumed", ())
    return Level(chapters=chapters, assumed=tuple(assumed), stages=tuple(stages), **base)


def self_test() -> int:
    good = 0
    total = 0

    def case(name_: str, ok: bool, detail: str = "") -> None:
        nonlocal good, total
        total += 1
        good += 1 if ok else 0
        print(f"{'✔' if ok else '✖'} {name_}" + ("" if ok else f" —— {detail}"))

    two = _corpus({"1.1": _text(), "1.2": _text(refs=("1.1",))})

    # ①–③ 区间压缩：只在同篇内连续时合并（断一章、跳一篇都不能写成区间）。
    case("章号压成区间（连续才合并）", compact({"1.1", "1.2", "1.3"}) == "1.1–1.3")
    case("断层不合并", compact({"1.1", "1.3"}) == "1.1、1.3")
    case("跨篇不合并", compact({"1.15", "2.1"}) == "1.15、2.1")

    # ④–⑤ 层自己的形状。
    case("层里点到盘上没有的章 → 红",
         bool(level_issues((_level(chapters=("9.9",)),), two)))
    case("同一章在层里出现两次 → 红",
         bool(level_issues((_level(chapters=("1.1", "1.1")),), two)))

    # ⑥–⑦ 前置闭合：点到的章两栏都没有就是把人扔进半路；补进「假定」才允许。
    lone = _corpus({"1.1": _text(), "1.2": _text(refs=("1.1",))})
    # 1.1 由另一层读，1.2 的前置才只剩「假定」这一条出路（否则并集那条会先红）。
    first = (_level(key="A", chapters=("1.1",)),)
    open_level = _level(key="B", chapters=("1.2",))
    closed_level = _level(key="B", chapters=("1.2",),
                          assumed=((("1.1",), "会一门语言就够了"),))
    case("前置没闭合 → 红", bool(level_issues(first + (open_level,), lone)))
    case("同一层写进「假定已具备」后 → 不再红",
         not level_issues(first + (closed_level,), lone))

    # ⑧–⑩ 「假定已具备」这一栏自己也要立得住。
    case("「假定」里有盘上没有的章 → 红",
         bool(level_issues((_level(chapters=("1.1",),
                                   assumed=((("7.7",), "会"),)),), two)))
    case("「假定」与本层要读的章重叠 → 红",
         bool(level_issues((_level(chapters=("1.1",),
                                   assumed=((("1.1",), "会"),)),), two)))
    case("「假定」没写理由 → 红",
         bool(level_issues((_level(chapters=("1.1",), assumed=((("1.2",), ""),)),), two)))

    # ⑪–⑬ 阶段表并集 ＝ 该层章集合（漏、重、多三种都要红）。
    case("阶段表漏一章 → 红",
         bool(level_issues((_level(chapters=("1.1", "1.2"),
                                   stages=(("一", ("1.1",), "做", "收"),)),), two)))
    case("一章出现在两个阶段 → 红",
         bool(level_issues((_level(chapters=("1.1",),
                                   stages=(("一", ("1.1",), "做", "收"),
                                           ("二", ("1.1",), "做", "收"))),), two)))
    case("阶段表里有本层没有的章 → 红",
         bool(level_issues((_level(chapters=("1.1",),
                                   stages=(("一", ("1.1", "1.2"), "做", "收"),)),), two)))

    # ⑭ 四层并集必须等于全书。
    case("有章没进任何一层 → 红",
         bool(level_issues((_level(key="A", chapters=("1.1",)),), two)))

    # ⑮ 有效字 ＝ 汉字 ＋ 15 × 围栏行（与 lint_book 同一个公式）。
    one = _text(body="汉字汉字汉字", fences=2)
    case("有效字 ＝ 汉字 ＋ 15 × 围栏行",
         effective_words(one) == lb.han_len(one) + 15 * 2
         and effective_words(one) == lb.han_len(one) + lb.CODE_LINE_EQUIV * 2)

    # ⑯ 练习按**条目**数计数、分级。
    pc = practice_counts(_text(levels=("基础", "基础", "基础", "进阶", "进阶", "挑战")))
    case("练习按条目分级计数",
         (pc["基础"], pc["进阶"], pc["挑战"]) == (3, 2, 1))

    # ⑰ 附带的树按「篇全含」：少一章就不算（否则「你会有那棵树」是假的）。
    tree_corpus = Corpus(texts={"5.1": _text(), "5.2": _text(refs=("5.1",))},
                         trees={"zhizhou-v5": 5})
    full = _level(chapters=("5.1", "5.2"))
    half = _level(chapters=("5.1",))
    case("篇全含才算附带的树（含全篇 → 列）", trees_of(full, tree_corpus) == ("zhizhou-v5",))
    case("篇全含才算附带的树（缺一章 → 不列）", trees_of(half, tree_corpus) == ())

    # ⑱ 周数是算术：同一式子换周投入。（周数不减、在职版恰为减半后的结果）
    st = stats_of(full, tree_corpus)
    case("周数 ＝ 总时数 ÷ 每周投入，向上取整",
         st.weeks() == math.ceil(st.hours / WEEKLY)
         and st.weeks(WEEKLY / 2) == math.ceil(st.hours / (WEEKLY / 2))
         and st.weeks(WEEKLY / 2) >= st.weeks())
    bigger = stats_of(_level(chapters=("5.1", "5.2", "5.3")),
                      Corpus(texts={**tree_corpus.texts, "5.3": _text(refs=("5.1",))},
                             trees=tree_corpus.trees))
    case("多一章，总时数不减（单调）", bigger.hours > st.hours)

    # ⑲ 下限：合成的小状态必须被拦住——否则「扫描退化成空」会安静地绿。
    case("退化的小状态被下限拦住", bool(coverage_issues(two)))

    # ⑳–㉑ 逐字比与幂等。
    case("逐字比报「首个不同在第 N 行」",
         first_diff("x\ny\nz\n", "x\nY\nz\n").startswith(f"{OUT.name} 与生成结果不同：首个不同在第 2 行"))
    case("渲染幂等（两次 render() 逐字相同）", render(two) == render(two))

    # ㉒ 盘上现状：四层与覆盖下限都必须立得住（这条是「今天真的对」）。
    corpus = load_corpus()
    case("盘上现状：四层无缺口、覆盖下限满足",
         not level_issues(LEVELS, corpus) and not coverage_issues(corpus))

    print(f"学习计划自检：{good}/{total} 通过"
          + ("" if good == total else f"（{total - good} 条不过）"))
    # 书侧（`STYLE`／`README`）若写了「learning_path.py … N 条夹具」，那个数必须等于这个分母。
    import style_claims as sc
    return sc.report("learning_path", total) | (0 if good == total else 1)


def main() -> int:
    argv = sys.argv[1:]
    if "--self-test" in argv:
        return self_test()
    if "--check" in argv:
        return check()
    if "--sync" in argv:
        return sync(write=True)
    print(__doc__)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

