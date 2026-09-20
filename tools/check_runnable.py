#!/usr/bin/env python
"""可运行树的一致性门（`zhizhou-v3/` 手写版与 `zhizhou-v4/` 框架版）。

为什么需要它：正文里贴的代码是**节选**，而节选会漂——改了真实文件却忘了改正文，
或者正文里贴的是「当时想写的版本」。漂了以后读者照着敲必然跑不通，而这正是
「项目能不能跑」最容易被忽略的一环：文件存在 ≠ 正文里那段就是文件里的那段。

八道检查（前七道**对 `SPECS` 表里的每一棵树各跑一遍**，末尾那道只跑一次）：
  1. 一致性：每个标注了文件路径的代码块，其**每一行**都必须能在它声称的文件里按顺序找到；
  2. 结构：树里的每个 `app/` 模块都必须能导入，且模块级导入不发请求（离线可跑）；
  3. 自检：树内的测试全绿 + 该树的离线入口跑通（都不需要密钥）；
  4. 回归：评测集（`experiments/eval_run.py --offline --check`）不得比已提交的基线差；
  5. 密钥：仓库里（被跟踪的 ＋ 还没提交的）不得出现形如真实密钥的串；
  6. 行数格：正文表格里标的文件行数必须与树里的真实行数相等；
  7. 条数格：正文里「N 条夹具」「N 条用例」必须与**实得**相等——
     两个数**都是跑出来的**：夹具数靠跑那个脚本的 `--self-test`（读它自报的条数），
     用例数取第 3 道那一趟**真调起来几条**（同一把尺子量出「树内测试 N 条通过」），
     拿不到才退回数文件里的 `def test_`，而两把尺子量出的不一样时会明说；
  8. 输出块：正文里那些**标了命令**的输出围栏（```text $ python scripts/x.py --offline），
     重跑那条命令，引用的行必须还能**按顺序**找到（同一棵树同一条命令只跑一次，
     与第 3 道共用缓存；`…` 只推进游标，不赦免漏掉的引用）。

第六道是 2026-09-17 补的：**正文表格里标的行数必须与树里真实行数相等**。
它补的是一条被反复踩到的缝：正文里的代码块逐行校验、正文里的汇总数字有对账门，
而**正文章节里那些「文件 ＋ 行数」的表格**两边都不管——它们既不是代码块，也不是汇总数字。
5.9 那一轮在树那一侧接上了同一条检查（`scripts/recap.py` 的第四条对账），
书这一侧当时还是手抄；这一道把书也接上了（当时 4.2／4.3／5.6／5.7／5.8 五章共 14 格已漂）。

第七道同日补上，接的是**树那一侧第五条**（`recap.py` 的自描述条数）的同一类数字：
「N 条夹具」与「N 条用例」。它的主语与行数格不同——**条数的主语是一个脚本**，
所以真值得**跑出来**（`python <脚本> --self-test`，读它自报的 `N/M 通过`），
不像行数那样看一眼盘就有。这也是它只到现在才接上的原因：
在一个把「声称输出必须实跑」写进体例的项目里，**「跑得动」本身就是一条断言**。

用例数那一半起初是数 `def test_` 数出来的，后来改成取自检那一趟跑起来的条数：
同一份工作只做一次，而且读者拿到手上的就是那个数（测试运行时说的话）。

第八道同日补上，接的是那句写在体例里、却一直只有人看着的约定——**声称输出必须实跑**。
它抓的是一类被反复踩到的数字：贴在围栏里的「真实输出」（本书里最典型的是
5.9 那句「其中夹具 23 条是本脚本实有」，脚本长到 28 条之后它还写着 23）。
接上它的当天把 28 个块标上了命令（`4.5` 5 个、`5.3` 6 个、`5.4` 5 个、`5.5` 3 个、
`5.7` 6 个、`5.8` 2 个、`5.9` 1 个）——标的时候逐个跑过：每一个块的引用行都**只**能被
一条命令输出解释（能对上两条时宁可不标，模糊的断言比没有断言更坏）。
两条路都留着——数文件是拿不到实跑值时的退路，两个数不一样时会另报一行。

用法：
    python tools/check_runnable.py              # 七道检查（逐棵树，另加末尾那一趟密钥扫描）
    python tools/check_runnable.py --self-test  # 只跑本工具自己的夹具
"""
from __future__ import annotations

import argparse
import os
import importlib
import re
import subprocess
import sys
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parent.parent
# 两棵树并存：v3 是手写版（第 3 篇），v4 是框架版（第 4 篇）。
# 这一关从一个作用域变成两个之后，**两边的清单都不能写死**——所以下面每个函数
# 都把「哪一章的目录、哪一棵树」当参数，默认值仍是 v3（历史调用不受影响）。
BOOK = ROOT / "book" / "03-大模型与Agent原理"
TREE = ROOT / "zhizhou-v3"
BOOK_V4 = ROOT / "book" / "04-AI应用开发框架"
TREE_V4 = ROOT / "zhizhou-v4"
BOOK_V5 = ROOT / "book" / "05-RAG与生产级系统"
TREE_V5 = ROOT / "zhizhou-v5"
BOOK_V6 = ROOT / "book" / "06-模型接入与成本工程"
TREE_V6 = ROOT / "zhizhou-v6"
BOOK_V7 = ROOT / "book" / "07-AI应用工程化"
TREE_V7 = ROOT / "zhizhou-v7"
BOOK_V8 = ROOT / "book" / "08-交付与产品化"
TREE_V8 = ROOT / "zhizhou-v8"
# 要校验的章节**从盘上长出来**。这里原本是一份写死的文件名元组，于是「写完新章忘了
# 加进清单」就等于新章的代码块一条都没被检查——三处同类静默漏账里最早的一处：
# 3.7 写成后 8 个代码块全部无人校验，而输出里只有一个看上去正常的「20 个块」。
# 按文件名排序：章号是两位数点一位（3.1、3.10），字符串序恰好等同于章序。
def chapters(book: Path = BOOK) -> tuple[str, ...]:
    """某一篇里的章文件名。传目录而不是写死清单，理由见上面的注释。"""
    return tuple(sorted(p.name for p in book.glob("*.md") if re.match(r"\d+\.\d+-", p.name)))


CHAPTERS = chapters()
CHAPTERS_V4 = chapters(BOOK_V4)
CHAPTERS_V5 = chapters(BOOK_V5)
CHAPTERS_V6 = chapters(BOOK_V6)
CHAPTERS_V7 = chapters(BOOK_V7)
CHAPTERS_V8 = chapters(BOOK_V8)


@dataclass(frozen=True)
class TreeSpec:
    """一棵可运行树的全部参数。

    为什么要把它做成一张表：这一关原本只有一个硬编码的作用域（第 3 篇 ＋ `zhizhou-v3`）。
    第四篇的树建起来的当天，所有检查都还会「全绿」——因为它们本来就没在看那棵树。
    这就是本文件里反复出现的同一课，只不过这次漏的不是一个文件名，而是**一整棵树**。

    每棵树必须把这几件事说清楚，缺一项都会退化成静默略过：
      · `book` / `tree`：篇目录与树目录（两个都是作用域，不能只给一个）；
      · `offline_cmds` / `marker`：它的离线入口有哪几个、该打印哪句话
        （v3 是 `demo.py --offline`；v4 **一章一个脚本**，所以那是一项元组——
        只写第一个的话，后面几章的脚本一个都不会被跑到）；
      · `min_chapters` / `min_modules`：反向守的下限。**树的规模在长，下限要跟着长**；
        这里给四篇写的是当前真实规模，不是随便填的小数。
    """

    book: Path
    tree: Path
    label: str
    offline_cmds: tuple[tuple[str, ...], ...]
    marker: str
    min_chapters: int
    min_modules: int
    # 测试模块数与 `app/` 模块数**是两个不同的下限**，初版把它们合成了一个，
    # 于是第四篇的树刚有 6 个 app 模块、2 个测试模块时被判「与规模不符」。
    min_tests: int = 1
    #: 正文里的条数格（「N 条夹具」「N 条用例」）数下限。同 `min_chapters` 一样从盘上量：
    #: v3 是 2、v4 是 2、v5 是 30（把「等三个文件」那种含糊写法改成可核的断言之后）。
    min_claim_cells: int = 0
    #: 正文围栏里「跑了几条」的引用数（`# N passed` 与 `# 全树 N 条`）下限。
    #: 同样从盘上量：它守的是「扫描退化成一格都没有，而输出安静地说全部相等」。
    min_pytest_cells: int = 0
    #: 正文表格里的「文件 ＋ 行数」格数下限。**同 `min_chapters` 一样从盘上量**：
    #: 它守的是「扫描退化成 0 格而两边一起空着」——那种时候输出里只会说「0 格全部相等」。
    #: v3 的行数格是 0（它的章节用的是「文件 ＋ 职责」表）；v4 是 16、v5 是 13。
    min_line_cells: int = 0
    #: 正文里那些标了命令的输出块（```text $ python …）数下限。同样从盘上量，
    #: 守的是「标注被删光而扫描说全部相等」。当然，**一个没标的输出块也不天然可疑**：
    #: 模型输出、模板、演示「把文档改坏之后的报错」都复现不出来，它们不属于这一类。
    min_output_blocks: int = 0
    #: 这棵树的评测脚本在输出里打的**读数行标记**。v3 的评测单位是「次试验」，
    #: v5 的是「条用例」——提取器里写死其中一个的话，另一棵树就会静默变成「（没有读数）」。
    #: 这与本文件里反复出现的同一课同源：**凡是跨作用域共用的字符串常量，都要进这张表。**
    eval_summary: str = "次试验"


SPECS: tuple[TreeSpec, ...] = (
    TreeSpec(book=BOOK, tree=TREE, label="（第 3 篇）", marker="离线自检通过",
             offline_cmds=(("demo.py", "--offline"),), min_chapters=10, min_modules=6,
             min_tests=6, min_line_cells=0, min_claim_cells=5, min_pytest_cells=9),
    # 第四篇的离线入口**一章一个**（4.1 的 `first_app.py`、4.2 的 `prompt_chain.py`……），
    # 所以这里是一个元组而不是一个命令：只写第一个的话，后面几章的脚本一个都不会被跑到——
    # 与本文件里反复出现的「清单写死」同一族。每写一章就补一行。
    TreeSpec(book=BOOK_V4, tree=TREE_V4, label="（第 4 篇）", marker="离线自检通过",
             offline_cmds=(("scripts/first_app.py", "--offline"),
                           ("scripts/prompt_chain.py", "--offline"),
                           ("scripts/agent_tools.py", "--offline"),
                           ("scripts/state_graph.py", "--offline"),
                           ("scripts/persistence_multiagent.py", "--offline")),
             min_chapters=5, min_modules=13, min_tests=5, min_line_cells=16,
             min_claim_cells=2, min_output_blocks=5),
    # 第 5 篇是**第三棵树**（检索版）。建它的当天就写进这张表——
    # 4.1 那次的教训还在这里挂着：新树建起来而表里没它，所有检查仍会静默全绿。
    # 5.2 起它的离线入口也是**一章一个**（`why_rag.py` → `split_reader.py`），
    # 所以这是第二项；只写第一项的话，新脚本一个块都不会被跑到。
    TreeSpec(book=BOOK_V5, tree=TREE_V5, label="（第 5 篇）", marker="离线自检通过",
             offline_cmds=(("scripts/why_rag.py", "--offline"),
                           ("scripts/split_reader.py", "--offline"),
                           ("scripts/vector_reader.py", "--offline"),
                           ("scripts/retrieve_reader.py", "--offline"),
                           ("scripts/generate_reader.py", "--offline"),
                           ("scripts/serve_reader.py", "--offline"),
                           # 5.8 的入口是**验收**（入库 → 三套库对照 → 端到端 → 清单），
                           # 它同时是这一章的读数脚本：从盘上算的三套库、逐项对基线、八个勾。
                           ("scripts/acceptance.py", "--offline"),
                           # 5.9 的入口是对账：**文档 ↔ 树**（模块双向点名、ADR 六字段、
                           # 读数引用对实跑证据）。它是这一章的交付物本身，
                           # 所以它必须在提交门里——否则「文档漂了」没有任何人会知道。
                           ("scripts/recap.py", "--offline")),
             # 下限跟着真实规模走（旧值 5/13/5 是 5.5 时的）。**三处都要量过再写**：
             # 5.8 写完后是章 8／模块 20／测试模块 11；5.9 写完后是 **章 9／模块 20／
             # 测试模块 12**（新增 `tests/test_recap.py`，`app/` 不增不减）。
             # 2026-09-17 写 5.9 时发现 `min_chapters` 还停在 8——**这条下限自己漂了一次**：
             # 它当时仍然是「过去某一章的值」，而它守不守得住当章根本没人看得见
             # （9 章 ≥ 8，输出里一个字都不会变）。正是本文件反复出现的那一课。
             # 这一条与「章清单从盘上长出来」是同一件事的两面：**树的规模在长，
             # 下限不跟着长，就退化成「只守住一章」**。
             min_chapters=9, min_modules=20, min_tests=12, min_line_cells=13,
             min_claim_cells=30, min_output_blocks=23, eval_summary="条用例"),
    # 第 6 篇是**第四棵树**（网关版）。它与前三棵最大的不同：**它不调模型**。
    # 前三篇的读数都要密钥、要网络；这一篇的读数是**算出来的账单**，
    # 所以它在提交门里能一直跑，而且每一组数都能用手再算一遍。
    # 建树当天写进这张表——4.1 那次的教训（新树建起来而表里没它，所有检查静默全绿）。
    # 第 6 篇的离线入口同样是**一章一个**（6.1 的账单、6.2 的翻译表），所以它也是元组。
    TreeSpec(book=BOOK_V6, tree=TREE_V6, label="（第 6 篇）", marker="离线自检通过",
             offline_cmds=(("scripts/select_reader.py", "--offline"),
                           # 6.2 的入口是**翻译**：同一件事在三家方言里的形状。
                           # 它不发请求——与 6.1 一样，读数是算出来的。
                           ("scripts/wire_reader.py", "--offline"),
                           # 6.3 的入口是**网关**：错误分档、退避、预算、熔断、
                           # 降级链与重发。它同样不发请求——网关那一趟跑在一条
                           # **脚本化的传输**上（第几次回什么由夹具写死）。
                           ("scripts/gateway_reader.py", "--offline"),
                           # 6.4 的入口是**计量**：四栏账、长档与缓存、断点顺序、
                           # 批量通道、分流、分桶与看板。它连「一条脚本化的传输」
                           # 都不需要——这一章的每一组数都是纯算术。
                           ("scripts/meter_reader.py", "--offline")),
             # 下限**逐个量过再写**：1 章、**2 个 `app/` 模块**（`registry` / `select`；
             # `__init__` 与前三棵树一样不计）、2 个测试模块、正文里 **6 个行数格**
             # （交付物清单六行）与 **4 个条数格**（`scripts/select_reader.py` 的 11 条夹具
             # 印了两处，两个测试文件的 7／10 条用例）、**5 个标了命令的输出块**
             # （六组读数分四段 ＋ 夹具那一行）。
             # 与前三棵树一样：**只量当天的真实规模**，估一个「安全的小数」等于没守。
             # 第一版写的是 8／2／1，两处都当场报了：行数格「只扫到 6 格（下限 8）」、
             # 模块数「只扫到 2 个（下限 3）」——**估一个安全数，等于让这道守永远沉默**。
             # 6.2 写完后逐个重量的值：**章 2／`app/` 模块 4**（上一行的两个＋ `wire`
             # 与 `dialects`）／测试模块 4（新增 `test_wire` 与 `test_dialects`）／
             # 行数格 **17**（6.1 六格 ＋ 6.2 十一格）／条数格 **11**／
             # 输出块 **11**（6.1 五块 ＋ 6.2 六块）。
             # 与上一行同一条纪律：**只量当天的真实规模**——这一篇的下限已经因为
             # 「估一个安全的小数」当场报过两次，而那两个数当时都**偏小**。
             # 6.3 写完后逐个重量的值：**章 3／`app/` 模块 6**（新增 `gateway`
             # 与 `router`）／测试模块 6（新增 `test_gateway` 与 `test_router`）／
             # 行数格 **33**（6.1 六格 ＋ 6.2 十一格 ＋ 6.3 十六格——而 6.1／6.2
             # 各有一行 `app/__init__.py` 也跟着从 33 长到 47，那两格是**同一份数字的
             # 副本**，行数格正是为了让它们当场红）／条数格 **21**／输出块 **18**。
             # 6.1 与 6.2 各量过一次「6 格／17 格」；这一篇的下限已经因为
             # 「估一个安全的小数」当场报过两次，所以这一次照旧**只量当天的规模**。
             # 6.4 写完后逐个重量的值：**章 4／`app/` 模块 7**（新增 `meter`）／
             # 测试模块 7（新增 `test_meter`）／行数格 **37**（6.1 六格 ＋ 6.2
             # 十一格 ＋ 6.3 十六格 ＋ 6.4 四格——而 `app/__init__.py` 那一格
             # 这一回**又会动**：它从 47 行长到 60，四章的交付物表里各印一次）／
             # 条数格 **25**／输出块 **24**。
             min_chapters=4, min_modules=7, min_tests=7,
             min_line_cells=37, min_claim_cells=25, min_output_blocks=29),
    # 第 7 篇是**第五棵树**（工程化版）。它与前四棵最大的不同：前四棵回答
    # 「怎么把它做出来」，这一棵回答「**怎么知道它还行**」。它同样不调模型、
    # 不联网——不过它比 v6 多一个需要说明的地方：离线树里那份「系统记录」
    # 是**造出来的**（7.1.4 的六组读数全从它算出来），所以那一章的边界里
    # 写明了「它量不了模型质量」。
    # 建树当天写进这张表——4.1 那次的教训（新树建起来而表里没它，所有检查静默全绿）。
    # 第 7 篇的离线入口同样是**一章一个**，所以它也是元组。
    TreeSpec(book=BOOK_V7, tree=TREE_V7, label="（第 7 篇）", marker="离线自检通过",
             # 这一篇的离线入口是**一章一个**，所以它是元组——而 7.2 是第一次真的用上
             # 这条约定（前四篇分别只有 1／5／9／4 个入口，第 7 篇在 7.1 那天还只有 1 个）。
             offline_cmds=(("scripts/pipeline_reader.py", "--offline"),
                           ("scripts/trace_reader.py", "--offline"),
                           ("scripts/rollout_reader.py", "--offline"),
                           ("scripts/security_reader.py", "--offline"),
                           ("scripts/privacy_reader.py", "--offline")),
             # 下限**逐个量过再写**（建树当天量的值，7.2 落地时重量了一遍，
             # **7.3 落地时再量了一遍**）：3 章／**7 个 `app/` 模块**（`suite` /
             # `metrics` / `gate` ＋ 7.2 的 `trace` / `board` ＋ 7.3 的
             # `registry` / `rollout`；`__init__` 与前面四棵树一样不计）／
             # 7 个测试模块／正文里 **20 个行数格**（7.1 八行 ＋ 7.2 六行 ＋ 7.3 六行）
             # 与 **18 个条数格**（7.1：33 条夹具印两处 ＋ 12／11／19 条用例；
             # 7.2：50 条夹具印两处 ＋ 15／13 条用例各印两处；7.3：91 条夹具印两处
             # ＋ 19／16 条用例各印两处）／**30 个标了命令的输出块**
             # （7.1 十三块 ＋ 7.2 九块 ＋ 7.3 八块）。
             # 这条下限**自己漂过一次，而它是这四个数里唯一没人回头看的一个**：
             # 7.2 与 7.3 两次登记时，账是按「这一章有几组读数块」数的（七组／七组），
             # 而扫描器数的是**所有标了命令的围栏**——每一章的 `--self-test` 尾巴
             # 也是一块。于是下限从 13 → 20 → 26 一路走，真值却从 13 → 22 → 30：
             # **一个低于真值的下限不响**（它只在「扫描整个坏掉」时才响），
             # 这就是 `min_modules` 那条注释讲过的同一件事（曾长期写着 13 而 v5 已到 20）。
             # 这一次重量：**7.1 十三块 ＋ 7.2 九块 ＋ 7.3 八块 ＝ 30**，逐个从盘上数出来。
             # **7.4 落地时重量了一遍六处**（这一次是**全量重数**，不是在前一个数上累加
             # ——因为上面那条 `min_output_blocks` 的教训就是「累加时用错了一把尺子」）：
             # 4 章（7.1–7.4）／**9 个 `app/` 模块**（7.4 的 `guard` 与 `policy`）／
             # **9 个测试模块**（新增 `test_guard` 与 `test_policy`）／正文里 **26 个行数格**
             # （7.1 八行 ＋ 7.2 六行 ＋ 7.3 六行 ＋ 7.4 六行）／**24 个条数格**
             # （7.4：53 条夹具印两处 ＋ 18／20 条用例各印两处）／**39 个标了命令的输出块**
             # （7.1 十三块 ＋ 7.2 九块 ＋ 7.3 八块 ＋ 7.4 九块）——逐个从盘上数出来，
             # 每一处都与实际相等（「低于真值的下限不响」这一条已经在本篇报过一次）。
             # **7.5 落地时量了第三遍六处**（同样全量重数）：5 章（7.1–7.5，本篇收口）／
             # **10 个 `app/` 模块**（7.5 的 `privacy`）／**10 个测试模块**
             # （新增 `test_privacy`）／正文里 **30 个行数格**
             # （7.1 八行 ＋ 7.2 六行 ＋ 7.3 六行 ＋ 7.4 六行 ＋ 7.5 四行）／**27 个条数格**
             # （7.5：60 条夹具印三处 ＋ 42 条用例印两处）／**47 个标了命令的输出块**
             # （7.1 十三块 ＋ 7.2 九块 ＋ 7.3 八块 ＋ 7.4 九块 ＋ 7.5 八块）。
             # 另：`app/__init__.py` 在本章从 74 行长到 **84 行**，而它的行数格
             # 在 7.1–7.4 四张交付物表里**各有一格**——四格当场全红（第三道检查
             # 报的 4 处不一致），改回真值即绿。这一处已经连续四章扮演同一个角色：
             # 「行数格存在的理由」每次都由同一行格子自己演示一遍。
             min_chapters=5, min_modules=10, min_tests=10,
             min_line_cells=30, min_claim_cells=27, min_output_blocks=47),
    # 第 8 篇是**第六棵树**（交付版）。它与前五棵最大的不同：前五棵的每一层都能
    # 在**你机器上**被验（循环、检索、账单、门），而这一棵问的是「**把它运到
    # 另一台机器上，它会是什么样**」——镜像有多重、改一行要重打多久、
    # `compose up` 之后应用第一次请求会不会失败、这个容器跑起来能做什么。
    # 它同样不装 Docker、不联网：镜像的大小与层数是**文件系统剧本**算出来的，
    # 构建耗时是**脚本化的每层秒数**，编排的时钟是**写死的秒数**。
    # 建树当天写进这张表——4.1 那次的教训（新树建起来而表里没它，所有检查静默全绿）。
    TreeSpec(book=BOOK_V8, tree=TREE_V8, label="（第 8 篇）", marker="离线自检通过",
             # 这一篇的离线入口同样是**一章一个**（8.1 的 `deploy_reader.py`），
             # 所以它也是元组——每写一章补一行。
             offline_cmds=(("scripts/deploy_reader.py", "--offline"),
                           ("scripts/ci_reader.py", "--offline"),
                           ("scripts/stream_reader.py", "--offline"),
                           ("scripts/quota_reader.py", "--offline"),
                           ("scripts/slo_reader.py", "--offline")),
             # 下限**逐个量过再写**（每章落地时全量重数一遍，不是估一个安全的小数——
             # 第 6 篇因为「估一个安全的小数」当场报过两次，那两个数当时都偏小；
             # 第 7 篇则报过「下限自己漂了三次而真值一路领先」）：
             # 建树当天（8.1 落地）：1 章／4 个 `app/` 模块／4 个测试模块／**10 个行数格**
             # （交付物清单十行）／**7 个条数格**（96 条夹具印两处 ＋ 26／15／20／16 条用例）／
             # **10 个标了命令的输出块**（六组读数分九块 ＋ 夹具那一行）／**1 处全树条数**
             # （77 条）。
             # **8.2 落地时全量重数六处**：2 章（8.1–8.2）／**10 个 `app/` 模块**
             # （新增 `trigger` / `graph` / `caching` / `perms` / `gate` / `release`）／
             # **10 个测试模块**／正文里 **24 个行数格**（8.1 十行 ＋ 8.2 十四行）／
             # **16 个条数格**（8.2：138 条夹具印两处 ＋ 六个测试模块的 18／17／17／15／13／15
             # 条用例）／**24 个标了命令的输出块**（8.1 十块 ＋ 8.2 十四块）／
             # **2 处全树条数**（8.1 与 8.2 各一行 `# 全树 172 条`）。
             # 这一章的两处红都是「同一行格子第二次扮演同一个角色」：
             # `app/__init__.py` 从 47 行长到 **66 行**，而它的行数格在
             # **8.1 与 8.2 的交付物表里各有一格**——两格同时报；
             # 另一处是 8.1 围栏里那句「全树 77 条」（8.2 的 95 条用例加进来之后
             # 真值变 172）——**围栏里的用例引用是唯一一处「跨章才会漂」的格子**，
             # 因为它记的是全树而不是本章，而它的检查只跑得起来当章那一次。
             # **8.3 落地时全量重数六处**：3 章（8.1–8.3）／**12 个 `app/` 模块**
             # （新增 `sse` / `stream_ui`）／**12 个测试模块**／正文里 **30 个行数格**
             # （8.1 十行 ＋ 8.2 十四行 ＋ 8.3 六行）／**21 个条数格**（8.3：62 条夹具印两处
             # ＋ `29`／`23` 条用例）／**35 个标了命令的输出块**（8.1 十块 ＋ 8.2 十四块
             # ＋ 8.3 十一块）／**3 处全树条数**（8.1／8.2／8.3 各一行，真值都是 224）。
             # 这一章的红又落在同一族上：`app/__init__.py` 从 66 行长到 **86 行**，
             # 而它的行数格在 **8.1 与 8.2 的交付物表里各有一格**——加上 8.3 这一格，
             # **同一个数现在由三处手抄**；而 8.1／8.2 围栏里那句「全树 172 条」也跟着变 224
             # ——**跨章才会漂的格子这一篇现在有三处**。
             # **8.4 落地时全量重数七处**：4 章（8.1–8.4）／**15 个 `app/` 模块**
             # （新增 `tenant` / `quota` / `billing`）／**15 个测试模块**／正文里 **38 个行数格**
             # （8.1 十行 ＋ 8.2 十四行 ＋ 8.3 六行 ＋ 8.4 八行）／**29 个条数格**
             # （8.4：63 条夹具印两处 ＋ 15／17／17 条用例）／**48 个标了命令的输出块**
             # （前 35 块 ＋ 8.4 的十三块）／**4 处全树条数**（真值都是 273）。
             # 这一章的红有两条，两条都值得记：
             #   ① 同一个数由**四只手抄**（`app/__init__.py` 86 → **108 行**，行数格在 8.1–8.4 各一格，
             #      四格同时报）——这是上一章「三处手抄」的下一步，而它反而更好：报得多总比不报好；
             #   ② **条数格的主语取错了**：验收命令原写成一行 pytest 命令 ＋ 「# 49 条用例」，
             #      而规则是「主语取左边最近的一个 `tests/*.py`」——于是一句「三个模块合计 49 条」
             #      被当成「`test_billing.py` 有 49 条」而判红（实得 17）。
             #      **改法不是改检查，而是改写法**：三条命令各占一行、各带自己的条数（15／17／17），
             #      合计那句留给「全树 273 条」。这一类错的形状：**一句话里带两个主语，机械规则只能取最近的那个**。
             # **8.5 落地时全量重数七处（本篇收口）**：5 章（8.1–8.5）／**19 个 `app/` 模块**
             # （新增 `slo` / `alert` / `drill` / `capacity`）／**19 个测试模块**／正文里 **48 个行数格**
             # （8.1 十行 ＋ 8.2 十四行 ＋ 8.3 六行 ＋ 8.4 八行 ＋ 8.5 十行）／**39 个条数格**
             # （8.5：77 条夹具印两处 ＋ 18／15／13／17 条用例）／**63 个标了命令的输出块**
             # （前 48 块 ＋ 8.5 的十五块）／**4 处全树条数**（真值都是 336——**这一篇的围栏里
             # 一共有四处记着「全树 N 条」，而它们的检查只跑得起来当章那一次**）。
             # 这一章的三处红都属于同一族，而它们第一次把这一族的形状说全了：
             #   ① `app/__init__.py` 108 → **137 行**，行数格在 8.1–8.5 各一格（五格同时报）
             #      ——**同一个数由五只手抄**，从 8.2 的「两处」到 8.3 的「三处」到 8.4 的「四处」，
             #      这是第五次，也是这一篇的收口；
             #   ② 8.1–8.4 四章围栏里的「全树 273 条」现在都不对（真值 336）——**只有写 8.5 这一趟
             #      才看得见它们**，因为它们记的是全树而检查跑的是当章；
             #   ③ 交付物表里的行数是我**先写表、后写模块**的：写完再 `wc -l`，十个格里有六个
             #      与真值差（129/125、155/166、101/90、115/127、103/119、99/118）——
             #      **它们全部当场报红**，而这一条恰好证明行数格在守着「表与文件不许各说各话」。
             min_chapters=5, min_modules=19, min_tests=19,
             min_line_cells=48, min_claim_cells=39, min_output_blocks=63,
             min_pytest_cells=5),
    # 5.6 的入口是 `experiments/eval_run.py`——它**不在这张元组里**，
    # 而是被第四道检查（回归门）每次跑两遍：一遍 `--self-test`、一遍 `--offline --check`。
    # 所以“每写一章补一行”这条规则这里不用重复登记；反过来说，
    # 如果哪天这一章换了读数脚本而没换上面的 `eval_summary`，输出里会变成「没读到读数行」。
)

#: 评测门自己的夹具条数下限。**条数每棵树可以不同**（v3 是 5、v5 是 11），
#: 所以它不能写成字符串比对——第一版写的是 `"自检 5/5 通过" not in stdout`，
#: 于是第 5 篇的评测脚本（11 条夹具、全过）被判成「自检不过」：
#: **一个把数字写死的检查，换一棵树就从「太松」变成「误报」。**
FIXTURE_RE = re.compile(r"自检 (\d+)/(\d+) 通过")
MIN_EVAL_FIXTURES = 5


def selftest_counts(stdout: str) -> tuple[int | None, int]:
    """从评测脚本的输出里读「自检 N/M 通过」。**读不出来返回 `(None, 0)`。**

    两件事都必须分得开：「没打印这句话」与「夹具全过」在字符串上不同，
    而只判后者的话，一个把夹具删光的脚本会安静地通过（与「18 条用例白写」同族）。
    取最后一次出现的匹配：一棵树可能先跑一段别人的自检再跑自己的。
    """
    found = FIXTURE_RE.findall(stdout)
    if not found:
        return None, 0
    ok, total = found[-1]
    return int(ok), int(total)


# `migrations/` 与 `experiments/` 也在树里：迁移与实验脚本同样会被读者照着敲，同样会漂。
# `scripts/` 是 3.10 新增的目录，而**它一开始落在这条范围之外**——写进正文的那个验收脚本
# 一个块都不会被校验，输出里照样是「全部命中」。目录清单与模块清单同一个毛病：
# 手写枚举必漏，所以新增目录时要一并加进来，并用自检守住“扫得到”。
PATH_RE = re.compile(r"\b((?:app|tests|migrations|experiments|scripts)/[\w/]+\.py)\b")
#: 围栏的**开**围栏：信息串可以是语言名（` ```python `），
#: 也可以是带命令标注的那一类（` ```text $ python scripts/x.py --offline `）。
#: **这条正则必须两种都认**——它曾经只认第一种，而后果不是报错，是**错位**：
#: 带命令标注的输出块那道**开**围栏匹配不上，于是它下面的**闭**围栏被当成了一块的开——
#: 从那一刻起开与闭全部反了，隔在中间的那个 ` ```python ` 块就**不会被扫到**，
#: 而输出里照旧印着「N 个标注了路径的代码块，全部命中」（实测第 6 篇四章
#: 只扫到 5 个，剩下那几个里的漂一个也看不见）。
#: 与 `lint_book.py` 那次围栏错位是同一族：**改一处体例，量它的那把尺子要一起改。**
FENCE_OPEN_RE = re.compile(r"^```(.*)$")
SECRET_RE = re.compile(r"\bsk-[A-Za-z0-9]{20,}")
# 块内的文件分段标注（“# app/api/agent.py —— 一个端点”）是正文的导航，不是文件里的代码
CAPTION_RE = re.compile(r"^#\s*(?:app|tests|migrations|experiments|scripts)/[\w/]+\.py\b")


def is_caption(line: str) -> bool:
    """题注行：只为了让读者知道「下面这段属于哪个文件」，两边都不该有它。"""
    return bool(CAPTION_RE.match(line.strip()))


def fences_of(text: str) -> list[tuple[str, str]]:
    """按行扫出所有围栏，返回 [(语言, 块内容)]。

    **这里曾经用一个非贪婪正则配对**（``r"```(\\w*)\\n(.*?)```"`` ＋ `re.S`），
    而它在正文里出现「带命令标注的输出块」之后会**整体错位**：那类围栏的信息串是
    `text $ python scripts/x.py --offline`，`(\\w*)` 匹配不到它，于是它那道
    **开**围栏被当成了上一块的**闭**围栏——从那一刻起，这一篇里开与闭全部反了。

    错位的后果不是报错，而是**少扫**：实测第 6 篇三章里 13 个带路径标注的代码块
    只扫到 5 个，而输出里照旧印着「5 个标注了路径的代码块，全部命中」——
    **「全部命中」这四个字在少扫一半时是假绿**，而少掉的那些块里就包括 6.3 新写的
    五个（它们看起来都「过了」，因为它们压根没被看过）。

    这与 2026-09-17 那次 `lint_book._FENCE` 是同一族——**改一处体例，量它的那把尺子
    要一起改**——只不过这一次的尺子长在另一个工具里，所以它多躲了一天。
    """
    out: list[tuple[str, str]] = []
    lines = text.replace("\r\n", "\n").splitlines()
    i = 0
    while i < len(lines):
        m = FENCE_OPEN_RE.match(lines[i])
        if not m:
            i += 1
            continue
        body: list[str] = []
        j = i + 1
        while j < len(lines) and not lines[j].startswith("```"):
            body.append(lines[j])
            j += 1
        out.append((m.group(1), "\n".join(body)))
        i = j + 1
    return out


def blocks_of(path: Path) -> list[tuple[int, list[str], list[str]]]:
    """返回 [(块序号, 代码行, 声称的文件路径)]，只收首行带路径标注的块。

    三处都必须小心，都是真撞过的：
      · **先归一化换行**。章节文件里既有 LF 也有 CRLF（3.2 整篇是 CRLF），
        不归一化的话 ```` ```python\n ```` 匹配不到，工具会「一个块都没找到」而**静默全绿**。
      · **首行是题注，不是代码**。`# app/llm/tokens.py —— ...` 只存在于正文里，
        文件里没有这一行，所以它不参与比对（否则每个块都注定差一行）。
      · **配对按行扫**（`fences_of()`），不许拿正则去配 ` ``` ` 与 ` ``` `——
        信息串带命令标注的那一类会让正则错位，而错位之后的症状是**少扫**。
    """
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    out = []
    for i, (lang, body) in enumerate(fences_of(text), 1):
        if lang != "python":
            continue
        lines = body.strip("\n").splitlines()
        if not lines or not PATH_RE.findall(lines[0]):
            continue
        out.append((i, lines[1:], PATH_RE.findall(lines[0])))
    return out


def match_runs(block: list[str], files: dict[str, list[str]]) -> list[str]:
    """把代码块按「最长连续段」的方式贴回文件，返回**贴不上**的那些行。

    逐行比对太松（同一个 `return None` 到处都是），逐块比对太严（节选本来就是拼的），
    所以取中间：**一段一段地连续匹配**，每一段必须真的存在，而且**位置只能往前**。

    那个「只能往前」不是形式主义：少了它，一个把文件里几行**打乱顺序**的代码块
    会被判为「全部命中」——而读者照着敲就是错位的。夹具里专门留了这条用例（自检第 5 条）。

    多文件块（“甲与乙——两文件节选合并”）按**每个文件一个游标**处理：
    在同一文件内部必须递增，但允许在文件之间来回切换（节选本来就是按段拼的）。
    """
    buf = {p: [ln.rstrip() for ln in t.splitlines()] for p, t in files.items()}
    cursor = {p: 0 for p in buf}
    uncovered, i = [], 0
    while i < len(block):
        if not block[i].strip() or is_caption(block[i]):
            i += 1
            continue
        best = (0, "")
        for path, lines in buf.items():
            for start in range(cursor[path], len(lines)):
                k = 0
                while (i + k < len(block) and start + k < len(lines)
                       and block[i + k].rstrip() == lines[start + k] and block[i + k].strip()):
                    k += 1
                if k > best[0]:
                    best = (k, path, start)
        if best[0] == 0:
            uncovered.append(block[i])
            i += 1
        else:
            _, path, start = best
            cursor[path] = start + best[0]
            i += best[0]
    return uncovered


#: 正文里的「行数格」：表格行的第一格是反引号里的一个树内文件路径，第二格是一个
#: 光秃秃的数字（可带「行」），形如 `| `app/x.py` | 268 |`。
#: **形状必须这么窄**：同一批表格里还有「24 条」「6 份」「21 项」「29 条用例」这些格，
#: 它们不是行数；把规则放宽一格，就会把它们也当成断言（那名叫假红，而假红会让人
#: 把整条检查关掉）。
LINE_CELL_RE = re.compile(r"^\|\s*`([^`]+)`\s*\|\s*(\d[\d,]*)\s*行?\s*\|")
#: 行数格认的路径：与 `recap.py` 的 `COUNTED_RE` 同形，但**各写一份是故意的**——
#: 共用的话，正则本身写错时两边一起错而无人发现（本文件里反复出现的那一课）。
LINE_PATH_RE = re.compile(
    r"^(?:(?:app|scripts|tests|experiments|migrations)/[\w/]+\.py|docs/[\w/.-]+\.md)$")


def line_cells(text: str) -> list[tuple[int, str, int]]:
    """一份正文里所有行数格：(行号, 相对路径, 声称的行数)。

    拷进去（而不是扫目录）是因为夹具要能凭空造出「写 267、盘上 268」这种状态，
    而真目录里造不出来——造不出来就没法验「它真的会响」（同 `match_runs`）。
    """
    out: list[tuple[int, str, int]] = []
    for i, line in enumerate(text.replace("\r\n", "\n").splitlines(), 1):
        m = LINE_CELL_RE.match(line)
        if m and LINE_PATH_RE.match(m.group(1)):
            out.append((i, m.group(1), int(m.group(2).replace(",", ""))))
    return out


def line_cell_issues(where: str, cells: list[tuple[int, str, int]], *,
                     exists: Callable[[str], bool], count_lines: Callable[[str], int]) -> list[str]:
    """行数格逐格与盘上比。报错必须带**两个数**（写的与盘的）：只报「不一致」
    的对账，拿到报错还得自己去 `wc -l`，而人一旦要自己再算一次，就会选择把这一格删掉。"""
    bad: list[str] = []
    for i, rel, claimed in cells:
        if not exists(rel):
            bad.append(f"{where}:{i} 表里写了 {rel} 的行数，而树里没有这个文件")
        elif (real := count_lines(rel)) != claimed:
            bad.append(f"{where}:{i} 写 {rel} 是 {claimed} 行，盘上是 {real} 行")
    return bad


def check_line_cells(book: Path = BOOK, tree: Path = TREE, names: tuple[str, ...] = CHAPTERS,
                     *, label: str = "", min_cells: int = 0) -> list[str]:
    """第六道检查：正文里的行数格逐格与树里真值比（＋「一格都没解析到」的反向守）。"""
    bad: list[str] = []
    total = 0
    for name in names:
        cells = line_cells((book / name).read_text(encoding="utf-8"))
        total += len(cells)
        bad += line_cell_issues(
            name, cells,
            exists=lambda rel: (tree / rel).exists(),
            count_lines=lambda rel: len((tree / rel).read_text(encoding="utf-8").splitlines()))
    if total < min_cells:
        # 反向守：解析一退化，输出会变成「0 格全部相等」——与「这一篇没有行数格」长得一样。
        bad.append(f"{label}只解析到 {total} 个行数格（下限 {min_cells}）：{names}"
                   f"——表被删空或解析坏了，先修它")
    print(f"  行数格{label}：{total} 个（表格里标的文件行数，逐格与盘上比），"
          f"{'全部相等' if not bad else f'{len(bad)} 处对不上'}")
    return bad


#: 中文数字（1–99）。它不是为了好看：本书表格里真的写着「七个用例」「十三个用例」，
#: 而这些格在这条规则放宽之前**一格都没被核过**——3.2 的表里写着七个、文件里已有十三个。
#: 只认到 99：「一百多条」那种含糊写法本来就是不该当断言的东西。
_CN_DIGIT = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
             "六": 6, "七": 7, "八": 8, "九": 9}


def cn_number(s: str) -> int | None:
    """把 `七` / `十三` / `二十四` / `13` 读成一个整数；读不出来返回 None。"""
    if s.isdigit():
        return int(s)
    if "十" not in s:
        return _CN_DIGIT.get(s) if len(s) == 1 else None
    head, _, tail = s.partition("十")
    if (head and head not in _CN_DIGIT) or (tail and tail not in _CN_DIGIT):
        return None
    return (_CN_DIGIT.get(head, 1) if head else 1) * 10 + (_CN_DIGIT.get(tail, 0) if tail else 0)


#: 条数格：正文里写的「N 条夹具」「N 条用例」——也认「N 个用例」与中文数字（见上）。
#: **两类的主语不同，形状也不同**：`N 条夹具` 的主语是它左边最近的一个
#: `scripts/`或`experiments/` 脚本（跑它的 `--self-test` 就能得到真值），
#: `N 条用例` 的主语是左边最近的一个 `tests/*.py`（数它的 `def test_`）。
#: 中间允许缀几个字（「20 条离线用例」「10 条夹具自检」都是本书真写法）。
CLAIM_RE = re.compile(r"(\d+|[一二三四五六七八九十]+)\s*(?:条|个)[^\s，。；、|]{0,4}?(夹具|用例)")
#: 主语的后缀写成 `\.[A-Za-z0-9]+`（不挑扩展名），而不写死 `.py`。
#: 这是被一次探针逼出来的：把主语改成 `scripts/README.md`（相当于改错文件名）之后，
#: 写死 `.py` 的版本会**认不出主语，于是这一格静静消失**——数字错了却一个字不报，
#: 只剩「这篇少了一格」这种汇总层的迹象。现在它会走到「这个文件跑不出条数」那一句，
#: 而这句话恰好就是改错文件名时最想听到的那一句。
FIXTURE_SUBJECT_RE = re.compile(r"(?:(zhizhou-v\d)/)?((?:scripts|experiments)/[\w/]+\.[A-Za-z0-9]+)")
#: `N 条用例` 的主语还得**长得像测试模块**（`tests/` 下、文件名以 `test` 开头），
#: 与树自己的测试发现规则（`test_modules()`）同一把尺子。不然 3.9 那一行会当场变成假红：
#: `tests/agent/eval_cases.jsonl`（6 条用例的**评测集**）会走进来，而它没有 `def test_`。
CASE_SUBJECT_RE = re.compile(r"(?:(zhizhou-v\d)/)?(tests/(?:[\w-]+/)*test[\w]*\.[A-Za-z0-9]+)")
#: 自检输出里的条数行。两种写法都要认：`夹具自检：10/10 通过`（v5 的几个脚本）
#: 与 `自检 27/27 通过`（`eval_run.py` 与 `recap.py` 都是这一种写法）。**取最后一处**：
#: 一个脚本可能先跑一段别人的自检再跑自己的。
SELFTEST_OUT_RE = re.compile(r"(\d+)/(\d+)\s*通过")


def claim_cells(text: str, tree_name: str) -> list[tuple[int, str, str, int]]:
    """一份正文里的条数格：(行号, 种类, 相对路径, 声称的条数)。

    两条边界写在代码里，而不是留给读者猜：
      · **没有主语的数不算**——正文里「6 条用例」这种**评测用例**的泛指到处都是
        （3.9 那一行 `eval_run.py --offline # 6 条用例` 指的就是题集），把它当断言全是假红；
      · **跨树引用不算**——`zhizhou-v3/xxx.py` 出现在第 4 篇里时跳过：那属于另一棵树的那一趟。
        两趟都不核它，但也不会因此误报；本文件里反复出现的那句「窄得写得出形状」同义。
    """
    out: list[tuple[int, str, str, int]] = []
    for i, line in enumerate(text.replace("\r\n", "\n").splitlines(), 1):
        for m in CLAIM_RE.finditer(line):
            kind = m.group(2)
            found = (FIXTURE_SUBJECT_RE if kind == "夹具" else CASE_SUBJECT_RE).findall(line[:m.start()])
            if not found:
                continue
            prefix, rel = found[-1]
            if prefix and prefix != tree_name:
                continue
            if m.group(1) == "一":
                # 中文里的「一」是**量词习惯**，不是条数断言：「里有一条用例把这件事钉死」
                # 说的是「有一条」，不是「这个文件总共一条」（5.4 那两处就是这么被误抓的）。
                # 数字形式的 `1 条用例` 才算断言——中英两种写法在这里是两件事。
                continue
            if (n := cn_number(m.group(1))) is None:
                # 读不出来的数字（「一百多个用例」）**不算格**，也不报错：
                # 它不是一条能核的断言，硬当断言只会得到一堆没法修的假红。
                continue
            out.append((i, kind, rel, n))
    return out


def selftest_count(tree: Path, rel: str, cache: dict[str, int | None]) -> int | None:
    """跑一个脚本的 `--self-test`，读它自报的条数。**每个脚本只跑一次**（结果进缓存）。

    跑不出来（不支持这个开关、或它自己坏了）返回 `None`——**「没法核」与「核过了」
    必须分得开**：不然一条没人能核的断言会缩在「全部通过」里。
    """
    if rel not in cache:
        proc = subprocess.run([sys.executable, rel, "--self-test"], cwd=tree,
                              capture_output=True, text=True, encoding="utf-8", timeout=300)
        found = SELFTEST_OUT_RE.findall((proc.stdout or "") + (proc.stderr or ""))
        cache[rel] = int(found[-1][1]) if found and proc.returncode == 0 else None
    return cache[rel]


def claim_issues(where: str, cells: list[tuple[int, str, str, int]], *, case_count,
                 fixture_count) -> list[str]:
    """条数格逐格与实得比。两个数都报出来（只报「不一致」的对账，拿到报错还得自己再算一次）。"""
    bad: list[str] = []
    for i, kind, rel, n in cells:
        real = case_count(rel) if kind == "用例" else fixture_count(rel)
        if real is None:
            # 报错话术按种类分开：主语改了名时，两种格该改的地方不一样
            # （夹具那格是「它跑不起来」，用例那格是「它根本数不出条数」）。
            how = ("这个文件跑不出条数——要么换个写法，要么让它能自检"
                   if kind == "夹具" else
                   "这个文件读不出条数——先看文件名对不对（测试模块得能导入）")
            bad.append(f"{where}:{i} 写 {rel} 有 {n} 条{kind}，而{how}")
        elif real != n:
            bad.append(f"{where}:{i} 写 {rel} 有 {n} 条{kind}，实得 {real} 条")
    return bad


#: 「跑了哪些测试、通过多少」：围栏里的命令行与它后面那行注释。
#: 两种真写法：`python -m pytest tests/x.py -q # 7 passed`（3.1–3.5）
#: 与 `$ python -m pytest tests/ -q # 全树 89 条`（3.6–3.8）。
#: 主语只认两种：一个**测试文件**（带 `.py`，与 `test_module_files` 同一把尺子）
#: 或**全树**（写「全树」的那个数）；只写 `pytest tests/ -q` 不带数不算格。
PYTEST_CMD_RE = re.compile(r"pytest\s+(\S*test\S*\.py)")
PASSED_RE = re.compile(r"#\s*(\d+)\s*passed")
WHOLE_TREE_RE = re.compile(r"全树\s*(\d+)\s*条")


def pytest_cells(text: str) -> list[tuple[int, str | None, int]]:
    """围栏里那些「跑了几条」的格：(行号, 测试文件或 None（全树）, 声称的条数)。

    三条边界都是被真事逼出来的：
      · **只在围栏内扫**。正文里也有「pytest 全量 42 passed」这种叙述（2.1 那一句），
        它占的是另一段时间的账，没有主语文件可核；把它当断言只会得到假红。
      · **数可以写在下一行**（3.4 就是「命令一行、`# 4 passed` 一行」），
        但主语只在**同一个围栏内**继承——出了这个块就重算，否则两个块会互相借主语。
      · **块里没出现过 pytest 命令的 `# N passed` 不算格**：那种数字的主语我们猜不出来，
        而猜错的主语会指到别的文件上去（那是比不核更坏的错）。
    """
    out: list[tuple[int, str | None, int]] = []
    in_fence, subject = False, None
    for i, line in enumerate(text.replace("\r\n", "\n").splitlines(), 1):
        if line.startswith("```"):
            in_fence, subject = not in_fence, None
            continue
        if not in_fence:
            continue
        if (m := PYTEST_CMD_RE.search(line)) is not None:
            subject = m.group(1)
        if (m := WHOLE_TREE_RE.search(line)) is not None:
            out.append((i, None, int(m.group(1))))
            continue
        if (m := PASSED_RE.search(line)) is not None and subject:
            out.append((i, subject, int(m.group(1))))
    return out


def pytest_issues(where: str, cells: list[tuple[int, str | None, int]], *,
                  case_count, tree_total: int | None) -> list[str]:
    """逐格比。**「拿不到真值」与「对得上」必须分得开**（本项目里反复出现的那一课）。"""
    bad: list[str] = []
    for i, rel, n in cells:
        real, what = (tree_total, "这一棵树") if rel is None else (case_count(rel), rel)
        if real is None:
            bad.append(f"{where}:{i} 写了「{what} 跑出 {n} 条」而**真值拿不到**"
                       f"（这一趟没跑起测试，或这个文件不在树里）——没法核不等于核过了")
        elif real != n:
            bad.append(f"{where}:{i} 写 {what} 跑出 {n} 条，实得 {real} 条")
    return bad


def check_pytest_claims(book: Path = BOOK, tree: Path = TREE, names: tuple[str, ...] = CHAPTERS,
                        *, label: str = "", min_cells: int = 0,
                        runs: dict[str, int] | None = None) -> list[str]:
    """第九道检查：正文围栏里「跑了哪些测试、通过多少」的引用逐处与实得比。

    与第七道（条数格）是同一件事的两种写法：第七道盯表格里的「N 条用例」，
    这一道盯命令行注释里的 `# N passed` 与 `# 全树 N 条`。两者都曾没人管——
    树从 89 长到 150 条之后，正文里还留着 89、122、`7 passed`、`9 passed`、`6 passed`，
    每一处都是手抄的。手抄的数只会单向漂，而且**漂了之后每一处都看起来很正常**。
    """
    bad: list[str] = []
    cells: list[tuple[str, int, str | None, int]] = []
    for name in names:
        text = (book / name).read_text(encoding="utf-8")
        cells += [(name, i, rel, n) for i, rel, n in pytest_cells(text)]
    by_file = {rel: runs[mod] for mod, rel in test_module_files(tree) if runs and mod in runs}
    static: dict[str, int | None] = {}
    total = sum(by_file.values()) if by_file else None
    for name in names:
        bad += pytest_issues(name, [(i, rel, n) for nm, i, rel, n in cells if nm == name],
                             case_count=lambda rel: case_count_of(tree, rel, by_file, static),
                             tree_total=total)
    if len(cells) < min_cells:
        bad.append(f"{label}只解析到 {len(cells)} 处「跑了几条」的引用（下限 {min_cells}）"
                   f"——扫描一退化，输出会变成「全部相等」")
    print(f"  用例引用{label}：{len(cells)} 处（围栏里的 `# N passed` 与 `# 全树 N 条`，"
          f"逐处与实跑条数比），{'全部相等' if not bad else f'{len(bad)} 处对不上'}")
    return bad


#: 输出块：正文里**引用了某条命令真实输出**的围栏。约定写在信息串里：
#: ```text $ python scripts/x.py --offline —— **`$` 后面就是那条命令**。
#: 只许 ASCII：围栏行里的汉字会进篇幅账（体例里围栏内的汉字是算数的），
#: 一处标注顺手给全篇加十几个字，那是噪声。
#: 不标的输出块不属于这一类：模型输出、模板、还有演示「把文档改坏之后的报错」，
#: 它们本来就不可能靠重跑复现（5.9 里那两处就是）。
OUTPUT_FENCE_RE = re.compile(r"^(?:text|console)\s+\$\s+(python\S*)\s+(\S.*)$")
#: 节选标记：引用里写一行 `…`（或 `...`）就表示「这里跳过了几行」。
#: 它只影响这一段之后从哪里接着找，**不会**让漏掉的引用变成合法。
ELISION_RE = re.compile(r"^\s*(?:\.\.\.|…)\s*$")


def output_blocks(text: str) -> list[tuple[int, tuple[str, ...], list[str]]]:
    """一份正文里被标注了命令的输出块：`(围栏行号, 命令 argv, 引用的行)`。"""
    lines = text.replace("\r\n", "\n").splitlines()
    out: list[tuple[int, tuple[str, ...], list[str]]] = []
    i = 0
    while i < len(lines):
        m = re.match(r"^```(.*)$", lines[i])
        if not m:
            i += 1
            continue
        om = OUTPUT_FENCE_RE.match(m.group(1).strip())
        body: list[str] = []
        j = i + 1
        while j < len(lines) and not lines[j].startswith("```"):
            body.append(lines[j])
            j += 1
        if om:
            out.append((i + 1, tuple([om.group(1)] + om.group(2).split()), body))
        i = j + 1
    return out


def output_issues(where: str, blocks: list[tuple[int, tuple[str, ...], list[str]]], *,
                  runner: Callable[[tuple[str, ...]], tuple[int, list[str]]],
                  exists: Callable[[str], bool]) -> list[str]:
    """第八道：标注了命令的输出块，**重跑那条命令，引用的行必须还能按顺序找到**。

    只判两件事，都是机器能判的：
      · 命令得跑得通（跑不通就说那条命令，不说「输出不一致」——两件事修法不同）；
      · 每一条被引用的非空行，必须在实跑输出里**按顺序**找到（`…` 只推进游标）。
    **不判**「是不是贴全了」：那要看作者是想给一段节选还是给全量，人来看（STYLE 8.8 第 2 条）。
    """
    bad: list[str] = []
    for at, argv, body in blocks:
        rel = argv[1]
        if not exists(rel):
            bad.append(f"{where}:{at} 标注的命令指向树外：`{' '.join(argv)}`——"
                       f"输出块只能引用本树里的命令")
            continue
        code, real = runner(argv)
        if code != 0:
            bad.append(f"{where}:{at} 标注的命令没跑通（退出码 {code}）：`{' '.join(argv)}`")
            continue
        cur = 0
        for k, want in enumerate(body):
            if not want.strip() or ELISION_RE.match(want):
                continue
            found = None
            for idx in range(cur, len(real)):
                if real[idx] == want:
                    found = idx
                    break
            if found is None:
                bad.append(f"{where}:{at + 1 + k} 引用的「{want.strip()}」在"
                           f"`{' '.join(argv)}` 的实跑输出里找不到——要么重跑一遍把真行贴回来，"
                           f"要么这行本来就不是它的输出（那就别标命令）")
            else:
                cur = found + 1
    return bad


def check_output_blocks(book: Path = BOOK, tree: Path = TREE, names: tuple[str, ...] = CHAPTERS,
                        *, label: str = "", min_blocks: int = 0,
                        runner: Callable[[tuple[str, ...]], tuple[int, list[str]]] | None = None
                        ) -> list[str]:
    """第八道（逐棵树）：把带命令标注的输出块再跑一遍。"""
    bad: list[str] = []
    total = 0
    for name in names:
        blocks = output_blocks((book / name).read_text(encoding="utf-8"))
        total += len(blocks)
        bad += output_issues(name, blocks,
                             runner=runner or (lambda argv: run_tree_cmd(tree, argv)),
                             exists=lambda rel: (tree / rel).exists())
    if total < min_blocks:
        bad.append(f"{label}只解析到 {total} 个带命令标注的输出块（下限 {min_blocks}）"
                   f"——标注被删光时，这一道会安静地说「全部相等」")
    print(f"  输出块{label}：{total} 个标注了命令的输出块（重跑一遍，引用的行逐行比），"
          f"{'全部对得上' if not bad else f'{len(bad)} 处对不上'}")
    return bad


def check_claims(book: Path = BOOK, tree: Path = TREE, names: tuple[str, ...] = CHAPTERS,
                 *, label: str = "", min_cells: int = 0,
                 runs: dict[str, int] | None = None) -> list[str]:
    """第七道检查：正文里的条数格（夹具数、用例数）逐格与实得比。

    `runs`：上一道（`check_tests`）那一趟记下来的「每个测试模块跑起来几条」。
    有它就用它——**用例数也是实跑出来的**，与树内测试那个总数同一把尺子；
    没有（比如单独调这个函数）就退回数 `def test_`。
    """
    bad: list[str] = []
    cells: list[tuple[str, int, str, str, int]] = []
    for name in names:
        text = (book / name).read_text(encoding="utf-8")
        cells += [(name, i, kind, rel, n) for i, kind, rel, n in claim_cells(text, tree.name)]
    # 模块名 → 相对路径，两张表从同一份扫描里长出来（不手写）。
    by_file = {rel: runs[mod] for mod, rel in test_module_files(tree) if runs and mod in runs}
    fixtures: dict[str, int | None] = {}
    static: dict[str, int | None] = {}
    for name in names:
        bad += claim_issues(
            name, [(i, kind, rel, n) for nm, i, kind, rel, n in cells if nm == name],
            case_count=lambda rel: case_count_of(tree, rel, by_file, static),
            fixture_count=lambda rel: selftest_count(tree, rel, fixtures))
    # 两把尺子量同一批文件：实跑出来的条数与数 `def test_` 数出来的必须一样。
    # 不一样时上面那几格用的是**实跑**那个数（读者拿到的是它），但差异本身也要说出来——
    # 那说明这个文件里的用例不是顶层 `def test_`（类里、或从别处引进来的），
    # 而这正是「数文件」那把尺子会数错的那种文件。别让一个数把这个事实盖过去。
    for rel, ran in sorted(by_file.items()):
        st = case_count_of(tree, rel, None, static)
        if st is not None and st != ran:
            bad.append(f"{label}{rel}：实跑 {ran} 条用例、数文件 {st} 条——两把尺子量出的不一样，"
                       f"先弄清这个文件的用例是怎么数的")
    if len(cells) < min_cells:
        bad.append(f"{label}只解析到 {len(cells)} 个条数格（下限 {min_cells}）"
                   f"——解析一退化，输出会变成「全部相等」")
    print(f"  条数格{label}：{len(cells)} 个（夹具数逐格跑一次那个脚本的自检、用例数取上一道"
          f"真跑起来的条数；跑了 {len(fixtures)} 个脚本的自检），"
          f"{'全部相等' if not bad else f'{len(bad)} 处对不上'}")
    return bad


def case_count_of(tree: Path, rel: str, runs: dict[str, int] | None = None,
                  static: dict[str, int | None] | None = None) -> int | None:
    """一个测试文件里有多少条用例。

    优先用**实跑出来的那个数**（自检那一趟逐个调起来的条数，`runs` 按相对路径给），
    没有就退回数文件里的 `def test_`。两条路都要能拿到 `None`——「读不出来」与
    「读出来是 0」在正文写「0 条用例」时长得一样，不能混。
    """
    if runs and rel in runs:
        return runs[rel]
    if static is not None:
        if rel not in static:
            try:
                text = (tree / rel).read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                static[rel] = None
            else:
                static[rel] = sum(1 for ln in text.splitlines() if ln.startswith("def test_"))
        return static[rel]
    try:
        text = (tree / rel).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    return sum(1 for ln in text.splitlines() if ln.startswith("def test_"))


def check_consistency(book: Path = BOOK, tree: Path = TREE, names: tuple[str, ...] = CHAPTERS,
                      *, min_chapters: int = 6, label: str = "") -> list[str]:
    bad: list[str] = []
    total = 0
    if len(names) < min_chapters:
        # 反向守：扫到的章太少时先怀疑扫描本身（写死清单的 bug 就是两边一起错而无人发现）。
        return [f"{label}只扫到 {len(names)} 章：{names}——与这一篇的实际规模不符"]
    if not any(blocks_of(book / n) for n in names):
        # 一个都没找到通常是解析坏了，而不是「没有要检查的东西」：宁可报错也别静默全绿。
        return [f"{label}没有解析到任何带路径标注的代码块——检查器本身坏了，先修它"]
    for name in names:
        for idx, lines, named in blocks_of(book / name):
            total += 1
            files, missing = {}, []
            for rel in named:
                p = tree / rel
                if not p.exists():
                    missing.append(rel)
                else:
                    files[rel] = p.read_text(encoding="utf-8")
            if missing:
                bad.append(f"{name} 块{idx}：可运行树里没有 {', '.join(missing)}")
                continue
            if uncovered := match_runs(lines, files):
                bad.append(f"{name} 块{idx}：{len(uncovered)} 行在 {'、'.join(named)} 里找不到，"
                           f"第一处是 {uncovered[0].strip()[:60]!r}")
    print(f"  一致性{label}：{total} 个标注了路径的代码块，"
          f"{'全部命中' if not bad else f'{len(bad)} 处对不上'}")
    return bad


def top_packages(tree: Path) -> list[str]:
    """树根下的顶层包名（含 `.py` 的目录）。

    两棵树都用 `app` 做服务本体，**包名撞车**：第二棵树第一次跑就出了
    `No module named 'app.config'`——因为 `app` 已在第一棵树那轮被缓存进
    `sys.modules`，第二次 import 拿到的是**第一棵树的 `app`**（它的目录里没有 `config.py`）。
    这类错很危险：它长得像「新树的模块写错了」，实际是两道检查互相污染。
    """
    return sorted(p.name for p in tree.iterdir() if p.is_dir() and any(p.rglob("*.py")))


def purge_modules(tree: Path) -> None:
    """把上一棵树留在这棵树的包名上的缓存清掉（两棵树共用 `app` / `tests` 这两个名字）。"""
    for name in top_packages(tree):
        for mod in [m for m in list(sys.modules) if m == name or m.startswith(name + ".")]:
            del sys.modules[mod]


def module_names(tree: Path = TREE) -> list[str]:
    """要比导入的模块**从盘上长出来**：写死的清单会静默漏账（这是本项目第四次同一课）。

    范围只取 `app/`：它是服务本体，树内每个模块都应该能在没有密钥、没有网络时导入。
    `experiments/` 是外部脚本（有些要读环境、有些要联网），不纳入这一关的承诺。
    """
    return sorted("app." + str(p.relative_to(tree / "app").with_suffix("")).
                  replace("/", ".").replace("\\", ".")
                  for p in (tree / "app").rglob("*.py") if p.name != "__init__.py")


def check_structure(tree: Path = TREE, *, label: str = "", min_modules: int = 2) -> list[str]:
    """模块能不能导入 ＋ **扫到的模块数是不是对得上这一篇的规模**。

    `min_modules` 原先只是 `TreeSpec` 里的一个字段，**谁也没读它**——
    一个「看起来在守、其实没接线」的旋钮。本族的第五次（前四次：写死的章节清单、
    写死的测试清单、路径范围漏 `scripts/`、单命令的离线入口）。
    修它的时候要顺手看一眼各树的下限是不是真值，不然新接的线也是个摆设：
    v3 实测 21 个模块（下限 6）、v4 实测 13（下限 13）、v5 实测 20（下限 20）。
    最后那个数也是量的：它曾长期写着 13，而 v5 早已长到 20——**一个下限低于真值的一半，
    等于没有下限**（它只在「扫描整个坏掉」时才响，扫漏一半时沉默）。
    """
    bad: list[str] = []
    mods = module_names(tree)
    if len(mods) < min_modules:             # 反向守：扫到的太少时，先怀疑扫描本身
        return [f"{label}只扫到 {len(mods)} 个模块（下限 {min_modules}）：{mods}"
                f"——与树的实际规模不符"]
    purge_modules(tree)
    sys.path.insert(0, str(tree))
    try:
        for m in mods:
            try:
                importlib.import_module(m)
            except Exception as exc:                     # noqa: BLE001
                bad.append(f"导入 {m} 失败：{type(exc).__name__}: {exc}")
    finally:
        sys.path.remove(str(tree))
    print(f"  结构{label}：{len(mods)} 个模块，{'全部可导入' if not bad else f'{len(bad)} 个失败'}")
    return bad


def test_modules(tree: Path = TREE) -> list[str]:
    """把 `tests/` 下的测试模块全扫出来。

    这里原本是一份**写死的模块名清单**，于是新加的文件永远不会被跑到：
    3.7 那一份 18 条用例就这么白写了两天，而输出里只有一个看不出问题的「71 条」。
    静默漏账的共同修法都一样：**让清单从盘上长出来**，再另外用反例守住“扫得到”。
    """
    return sorted(mod for mod, _rel in test_module_files(tree))


def test_module_files(tree: Path = TREE) -> list[tuple[str, str]]:
    """（模块名, 相对路径）两张**从同一份扫描里长出来的**对照表。

    两张表不能手写：正文里写的是路径，自检那一趟数的是模块，它们必须对得上；
    分开写就等于又造了一份没人核的清单。
    """
    out: list[tuple[str, str]] = []
    for p in sorted((tree / "tests").rglob("test_*.py")):
        rel = p.relative_to(tree).as_posix()
        out.append((rel[:-3].replace("/", "."), rel))
    return out


#: 跑一条树内命令的输出缓存。**同一棵树、同一条命令只跑一次**：
#: 离线入口那一张要跑一遍（看它打不打标记），正文里引用的输出块也要跑一遍
#: （看引用的行还算不算得出来）——两处问的是同一个东西，没理由跑两次。
RUN_CACHE: dict[tuple[str, tuple[str, ...]], tuple[int, list[str]]] = {}


def run_tree_cmd(tree: Path, argv: tuple[str, ...]) -> tuple[int, list[str]]:
    """在一棵树里跑一条命令，返回 `(退出码, stdout 的行)`。结果进缓存。

    它同时服务两处：离线入口的「打没打标记」与正文输出块的「引用的行还在不在」。
    **两处看到的必须是同一次运行的输出**，不然一份正文可能对着两次不同的运行都对上。
    """
    # `argv` 的头部允许写成 `python` / `python3`（正文里的标注就是那个样子）：
    # 那一段是**给人看的提示符**，真跑的时候用当前解释器。
    # 剥掉它再当键，两处（离线入口与输出块）就真的是**一次运行、两个读法**；
    # 不剥的话不只是多跑一遍：命令会被当成 `python python scripts/x.py`，
    # 退出码 2 而报出来的话看起来像「这条命令自己坏了」。这一处刚写的时候就踩过一次。
    argv = tuple(argv[1:]) if argv and argv[0].startswith("python") else tuple(argv)
    key = (str(tree), argv)
    if key not in RUN_CACHE:
        proc = subprocess.run([sys.executable, *argv], cwd=tree, capture_output=True,
                              text=True, encoding="utf-8", timeout=300)
        RUN_CACHE[key] = (proc.returncode, (proc.stdout or "").splitlines())
    return RUN_CACHE[key]


def check_tests(tree: Path = TREE, *, label: str = "", min_modules: int = 6,
                offline_cmds: tuple[tuple[str, ...], ...] = (("demo.py", "--offline"),),
                marker: str = "离线自检通过",
                runs: dict[str, int] | None = None) -> list[str]:
    """不依赖 pytest：把树内的测试函数逐个调起来。装了 pytest 的话命令在 README 里。

    离线的那个入口在两棵树里名字不同（v3 是 `demo.py --offline`，v4 是
    `scripts/first_app.py --offline`），所以它是个参数而不是写死的常量——
    第四篇的树刚建起来时，这一关正是这么把 v4 的演示整段漏掉的。

    `runs`：把**这一趟真跑起来的条数**按测试文件记下来，交给下一道（正文里的
    「N 条用例」）用。同一份工作只做一次，而正文那个数就不再是数文件数出来的，
    与「树内测试 N 条通过」用的是同一把尺子。
    """
    bad: list[str] = []
    purge_modules(tree)
    sys.path.insert(0, str(tree))
    mods = test_modules(tree)
    if len(mods) < min_modules:             # 反向守：扫到的东西太少时，先怀疑扫描本身
        bad.append(f"{label}只扫到 {len(mods)} 个测试模块，与树的实际规模不符：{mods}")
    ok = 0
    try:
        for m in mods:
            try:
                mod = importlib.import_module(m)
            except Exception as exc:                     # noqa: BLE001
                bad.append(f"{label}{m} 导入失败：{type(exc).__name__}: {exc}")
                continue
            names = sorted(n for n in dir(mod) if n.startswith("test_"))
            ran = 0
            for name in names:
                try:
                    getattr(mod, name)()
                    ran += 1
                except Exception as exc:                 # noqa: BLE001
                    bad.append(f"{label}{m}::{name} → {type(exc).__name__}: {exc}")
            ok += ran
            if runs is not None:
                # 卡住的用例也计入：正文说的「N 条用例」是**数出来多少条**，
                # 过不过由上面那行 bad 说话——别把两件事并成一个数。
                runs[m] = len(names)
    finally:
        sys.path.remove(str(tree))
    demo_ok = True
    for cmd in offline_cmds:
        code, out = run_tree_cmd(tree, tuple(cmd))
        if code != 0:
            bad.append(f"{label}{' '.join(cmd)} 退出码 {code}：{chr(10).join(out[-6:])[-300:]}")
            demo_ok = False
        elif marker not in "\n".join(out):
            bad.append(f"{label}{' '.join(cmd)} 没打印「{marker}」")
            demo_ok = False
    print(f"  自检{label}：树内测试 {ok} 条通过；离线演示 {len(offline_cmds)} 个，"
          f"{'全部通过' if demo_ok else '有问题'}")
    return bad


def check_eval(tree: Path = TREE, *, label: str = "", summary: str = "次试验") -> list[str]:
    """评测回归门（3.9）：先自检（改坏一档必须被拦下），再与基线比。

    它是**第四道**而不是挂在第三道里：它检的不是“跑得动”，而是“有没有变差”。
    两道门的失败含义完全不同——前者去修代码，后者先问“这是不是一次有意的改动”。

    只有已经有评测集的树才跑这一道（v3 有，v4 要等到它自己长出评测集那一章）。
    没有就**明说跳过**，不装作通过——静默略过是这一族里最难发现的一种。
    """
    bad: list[str] = []
    if not (tree / "experiments" / "eval_run.py").exists():
        print(f"  回归{label}：这一棵树还没有评测集，跳过（不是通过）")
        return bad
    fixture = subprocess.run([sys.executable, "experiments/eval_run.py", "--self-test"],
                             cwd=tree, capture_output=True, text=True, encoding="utf-8",
                             timeout=180)
    ok, total = selftest_counts(fixture.stdout)
    if fixture.returncode != 0 or ok is None or ok != total or total < MIN_EVAL_FIXTURES:
        bad.append(f"{label}评测门的自检不过（它坏了，或者不再能拦下退步）："
                   f"判读到 {ok}/{total}（下限 {MIN_EVAL_FIXTURES}）｜"
                   f"{(fixture.stdout or fixture.stderr)[-300:]}")
    run = subprocess.run([sys.executable, "experiments/eval_run.py", "--offline", "--check"],
                         cwd=tree, capture_output=True, text=True, encoding="utf-8",
                         timeout=300)
    if run.returncode != 0:
        tail = [ln for ln in (run.stdout or "").splitlines() if "·" in ln][-4:]
        bad.append(f"{label}评测集比基线差（可能是一次真退步）：" + " ｜ ".join(tail))
    elif "回归门通过" not in run.stdout:
        bad.append(f"{label}评测门没打印「回归门通过」——要先确认它真的跑到了比对那一步")
    line = next((ln.strip() for ln in run.stdout.splitlines() if summary in ln), "")
    if not line:
        # 「（没有读数）」当提示语是错的：这一行的缺失意味着**这段输出没人核对**，
        # 而它与「读数为空」在输出里长得一样。所以它是失败项，不是一句提示。
        bad.append(f"{label}评测门没打印读数行（标记「{summary}」）——这段输出没人核对")
    print(f"  回归{label}：{line or f'（没读到读数行：输出里没有「{summary}」）'}")
    return bad


def check_secrets() -> list[str]:
    """密钥：**被跟踪的 ＋ 还没提交的**文件都要扫。

    这里原本只扫 `git ls-files`（= 已被跟踪的）。而两棵树在新写的时候都还是
    「未跟踪」状态：于是这一关在**最需要它的那几天**里恰好什么都没扫到，
    输出照样是「干净」。补上 `--others --exclude-standard` 之后，
    「准备提交但还没 add」的那些文件才第一次真的被查过。
    """
    bad: list[str] = []
    files: list[str] = []
    for extra in (["--cached"], ["--others", "--exclude-standard"]):
        proc = subprocess.run(["git", "ls-files", *extra], cwd=ROOT, capture_output=True,
                              text=True, encoding="utf-8")
        files += proc.stdout.split()
    files = sorted(set(files))
    for rel in files:
        p = ROOT / rel
        try:
            text = p.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if SECRET_RE.search(text):
            bad.append(f"仓库里的文件有形如真实密钥的串：{rel}")
    print(f"  密钥：检查了 {len(files)} 个文件（被跟踪 ＋ 未提交），"
          f"{'干净' if not bad else '发现疑似泄漏'}")
    return bad


def self_test() -> int:
    """夹具：一段真节选要能贴上，一行改动或**顺序变化**都要能被抓住。"""
    x = "def f():\n    a = 1\n    b = 2\n    return a + b\n\n\ndef g():\n    return 3\n"
    y = "def h():\n    return 9\n"
    one, two = {"app/x.py": x}, {"app/x.py": x, "app/y.py": y}
    cases = [
        ("整段节选：应沉默", one, ["def f():", "    a = 1", "    b = 2"], 0),
        ("跨段节选：应沉默", one, ["def g():", "    return 3"], 0),
        ("空行忽略：应沉默", one, ["def f():", "", "    a = 1"], 0),
        ("改了一个字：应报出", one, ["def f():", "    a = 11"], 1),
        ("顺序颠倒：应报出", one, ["    return a + b", "def f():"], 1),
        ("两个文件按序拼接：应沉默", two, ["def g():", "    return 3", "def h():", "    return 9"], 0),
        ("空行不算内容：应沉默", one, ["def f():", "", "", "    a = 1"], 0),
    ]
    bad = 0
    total = 0

    def chk(ok: bool, msg: str) -> None:
        """一处断言。**分母由这里数出来，不由末尾那个手写的算式算出来。**

        那个算式曾经是 `len(cases) + len(counts) + 4 * len(SPECS)`，而每棵树的
        固定检查其实有 **6 处**（外加逐个离线入口）——于是分母比真数少 7，
        「42/42 通过」里的 42 从来没人核过。这正是本书反复检的那一族错：
        **手写的数字没有一条会响的路**。写法改成「过一次记一次」，它就不可能再漂。
        """
        nonlocal total, bad
        total += 1
        if not ok:
            print(f"  ✗ {msg}")
            bad += 1

    for label, files, block, want in cases:
        got = len(match_runs(block, files))
        chk(got == want, f"{label}：期望 {want} 行贴不上，实得 {got}")
    # 围栏配对：**带命令标注的输出块不许把后面那个块吃掉**（2026-09-19 修的真事故）。
    # 两种顺序都要量：输出块在前，以及代码块在前。
    out_block = "```text $ python scripts/x.py --offline\n读数的第一行\n```"
    py_block = "```python\n# app/suite.py —— 题注\n        return 1\n```"
    for label, text in (("输出块在前", f"前面一段话\n{out_block}\n中间一段话\n{py_block}"),
                        ("代码块在前", f"前面一段话\n{py_block}\n中间一段话\n{out_block}")):
        fs = fences_of(text)
        chk(len(fs) == 2, f"围栏配对（{label}）：期望 2 块，实得 {len(fs)}")
        chk(any(lang == "python" for lang, _ in fs),
            f"围栏配对（{label}）：`python` 那一块没被扫到")
        chk(sum(1 for lang, _ in fs if lang.startswith("text ")) == 1,
            f"围栏配对（{label}）：带命令标注的那一块没被认出来")
        chk(any(bool(PATH_RE.findall(body.strip().splitlines()[0]))
                for lang, body in fs if lang == "python"),
            f"围栏配对（{label}）：题注行没被 PATH_RE 认出来")
    # 反向守：测试模块的扫描结果要与**另一种写法**扫出来的对上。
    # 不能两边用同一个函数：写过死清单的那个 bug 就是两边一起错而无人发现。
    walked = []
    for root, _dirs, names in os.walk(TREE / "tests"):
        walked += [n for n in names if n.startswith("test_") and n.endswith(".py")]
    found = {m.rsplit(".", 1)[-1] + ".py" for m in test_modules()}
    chk(sorted(set(walked)) == sorted(found),
        f"测试模块扫描对不上：os.walk 得到 {sorted(set(walked))}，"
        f"test_modules() 得到 {sorted(found)}")
    # 同一把尺子量章节清单：另一种写法（os.listdir）扫出来的章文件数必须与 chapters() 一致。
    # 两篇都要量：只在第 3 篇上量，第四篇的扫描坏了同样没人知道。
    for spec in SPECS:
        if not spec.book.exists():
            chk(False, f"{spec.label}的篇目录不存在：{spec.book}")
            continue
        listed = [n for n in os.listdir(spec.book)
                  if n.endswith(".md") and len(n) > 4 and n[1] == "."]
        got = list(chapters(spec.book))
        # 反向守：这篇正文里的行数格数与条数格数不得低于下限。它们守的是「扫描退化成 0 格」——
        # 那种时候主检查只会安静地说「0 格全部相等」，与「这一篇没有这类格」长得一样。
        found_cells = sum(len(line_cells((spec.book / n).read_text(encoding="utf-8")))
                          for n in got)
        found_claims = sum(len(claim_cells((spec.book / n).read_text(encoding="utf-8"),
                                           spec.tree.name)) for n in got)
        found_blocks = sum(len(output_blocks((spec.book / n).read_text(encoding="utf-8")))
                           for n in got)
        # 逐条摆出来再跑：清单守与离线入口混在一起，是为了让**分母由这些断言自己数出来**，
        # 不必再手写一句「每棵树固定 N 处」（那正是这一节反复抓的那族错）。
        checks = [
            (sorted(listed) == sorted(got),
             f"{spec.label}章节扫描对不上：os.listdir 得到 {sorted(listed)}，"
             f"chapters() 得到 {sorted(got)}"),
            (len(got) >= spec.min_chapters,
             f"{spec.label}只扫到 {len(got)} 章（下限 {spec.min_chapters}）：{got}"),
            (found_cells >= spec.min_line_cells,
             f"{spec.label}只扫到 {found_cells} 个行数格（下限 {spec.min_line_cells}）"),
            (found_claims >= spec.min_claim_cells,
             f"{spec.label}只扫到 {found_claims} 个条数格（下限 {spec.min_claim_cells}）"),
            # 反向守：标注了命令的输出块。标注删光时，第八道会安静地说「全部对得上」。
            (found_blocks >= spec.min_output_blocks,
             f"{spec.label}只扫到 {found_blocks} 个标注了命令的输出块"
             f"（下限 {spec.min_output_blocks}）"),
        ]
        # 反向守：清单里写的离线入口必须真的在盘上。改文件名的同一天就会报出来，
        # 而不是等到「演示通过」这句话再也不出现（那时它其实根本没跑）。逐个入口各算一处。
        checks += [((spec.tree / cmd[0]).exists(),
                    f"{spec.label}清单里的离线入口不存在：{cmd[0]}")
                   for cmd in spec.offline_cmds]
        for ok, msg in checks:
            chk(ok, msg)
    # 行数格：既要能报出「写 267、盘上 268」,也要对「不是行数的格」保持沉默。
    # 后者不是挑剔：同一批表格里真的混着「14 条用例」「6 份」「24 条」这些格。
    fake = {"app/x.py": 268}
    cells_ok = line_cells("| `app/x.py` | 268 | 服务本体的入口层 |")
    cell_cases = [
        ("行数格写对了：沉默",
         not line_cell_issues("c.md", cells_ok, exists=lambda r: r in fake,
                              count_lines=lambda r: fake[r])),
        ("**改一行就红**（写 267、盘上 268）",
         bool(line_cell_issues("c.md", [(7, "app/x.py", 267)], exists=lambda r: r in fake,
                               count_lines=lambda r: fake[r]))),
        ("格里的文件不在树里：要报",
         bool(line_cell_issues("c.md", [(7, "app/gone.py", 1)], exists=lambda r: r in fake,
                               count_lines=lambda r: fake[r]))),
        ("第二格写着「14 条用例」而不是数字：不算行数格",
         not line_cells("| `tests/test_x.py` | 14 条用例 | 三档拒收、戳的三条性质 |")),
        ("第二格写着「6 份」：不算行数格",
         not line_cells("| `knowledge/` | 6 份 | 多格式语料：csv / txt / html |")),
        ("第一格不是路径（提示词正文）：不算行数格",
         not line_cells("| `你是客服助手。` | 5 | 两行模板 |")),
        ("第一格是路径但后面还缀着字（`tests/test_cache.py` 节）：不算行数格",
         not line_cells("| `tests/test_cache.py` 节 | 29 条用例 | 10 、 8 、 11 条 |")),
        ("带「行」的写法同样认（186 行）",
         line_cells("| `app/x.py` | 268 行 | 服务本体的入口层 |") == [(1, "app/x.py", 268)]),
        ("千位逗号也认（1,024）",
         line_cells("| `app/x.py` | 1,024 | 服务本体的入口层 |") == [(1, "app/x.py", 1024)]),
    ]
    # `cell_cases` 与下面那批都是 `(标签, 真值)` 两格，得用另一条路跑。
    # **别写成 `cases += cell_cases`**：`cases` 里的四格元组由上面那条循环拆包，
    # 两格的在里面拆不出来；而更要紧的是「加进清单」不等于「跑过」——
    # 摆在这里而没人迭代的话，断言一条都不会执行，分母却会把它算成通过。
    for label, ok in cell_cases:
        chk(ok, f"行数格夹具没通过：{label}")

    # 条数格：两类的主语不同（夹具→脚本、用例→测试文件），而**没有主语的数不算**。
    # 它不是挑剔：正文里「6 条用例」这种评测用例的泛指到处都是（3.9 那一行就是）。
    claims_ok = claim_cells("| `scripts/x.py` | 3 条夹具自检 | 五组读数 |", "zhizhou-v5")
    claim_cases = [
        ("夹具格写对了：沉默",
         not claim_issues("c.md", [(9, "夹具", "scripts/x.py", 3)],
                          case_count=lambda r: 5, fixture_count=lambda r: 3)),
        ("**夹具少写一条就红**（写 2、实跑 3）",
         bool(claim_issues("c.md", [(9, "夹具", "scripts/x.py", 2)],
                           case_count=lambda r: 5, fixture_count=lambda r: 3))),
        ("用例格写对了：沉默",
         not claim_issues("c.md", [(9, "用例", "tests/y.py", 5)],
                          case_count=lambda r: 5, fixture_count=lambda r: 3)),
        ("**用例少写一条就红**（写 4、实得 5）",
         bool(claim_issues("c.md", [(9, "用例", "tests/y.py", 4)],
                           case_count=lambda r: 5, fixture_count=lambda r: 3))),
        ("跑不出自检的脚本：报「没法核」而不是叛它过",
         bool(claim_issues("c.md", [(9, "夹具", "scripts/x.py", 3)],
                           case_count=lambda r: 5, fixture_count=lambda r: None))),
        ("没主语的「6 条用例」（评测用例）不算格",
         not claim_cells("$ python experiments/eval_run.py --offline     # 6 条用例",
                         "zhizhou-v5")),
        ("跨树引用不算格（第 4 篇里写 zhizhou-v3 的脚本）",
         not claim_cells("- `zhizhou-v3/scripts/demo.py`（5 条夹具）", "zhizhou-v4")),
        ("前缀写的就是这一棵树时算格",
         claim_cells("- `zhizhou-v5/tests/test_generate.py`：**20 条离线用例**",
                     "zhizhou-v5") == [(1, "用例", "tests/test_generate.py", 20)]),
        ("带夹字的真写法（缩成 3 条夹具自检）也要认",
         bool(claims_ok) and claims_ok[0][1:] == ("夹具", "scripts/x.py", 3)),
        ("主语改了名（`scripts/README.md`）：要红，而不是让这格静默消失",
         claim_cells("| `scripts/README.md` | 3 条夹具自检 | 五组读数 |", "zhizhou-v5")
         == [(1, "夹具", "scripts/README.md", 3)]
         and bool(claim_issues("c.md", [(1, "夹具", "scripts/README.md", 3)],
                               case_count=lambda r: 5, fixture_count=lambda r: None))),
        ("测试文件改了名（`tests/test_yy.py`）：认出来、报「读不出条数」",
         claim_cells("| `tests/test_yy.py` | 5 条用例 | 三档拒收 |", "zhizhou-v5")
         == [(1, "用例", "tests/test_yy.py", 5)]
         and bool(claim_issues("c.md", [(1, "用例", "tests/test_yy.py", 5)],
                               case_count=lambda r: None, fixture_count=lambda r: 3))),
        ("`tests/agent/eval_cases.jsonl` 是评测集不是用例主语（3.9 那一行）：不算格",
         not claim_cells("`tests/agent/eval_cases.jsonl`（6 条用例、15 次试验的评测集）、",
                         "zhizhou-v3")),
        # 用例数优先取**实跑**那个数：两把尺子打起来时，以真跑起来的为准（也是读者看到的那个）。
        ("用例数取实跑值（实跑 3、数文件 5）时判 3",
         case_count_of(Path("."), "tests/x.py", {"tests/x.py": 3}, {"tests/x.py": 5}) == 3),
        ("实跑记录里没有这个文件：退回数文件（5）",
         case_count_of(Path("."), "tests/x.py", {}, {"tests/x.py": 5}) == 5),
        ("两张表从同一份扫描里长出来（模块名与相对路径对得上）",
         all(mod.replace(".", "/") + ".py" == rel for mod, rel in test_module_files(TREE))
         and len(test_module_files(TREE)) >= 6),
        # 中文数字与「个」：「七个用例」这种写法在 3.1–3.5 的交付物表里各有一格，
        # 而这批格在这条规则放宽之前**一格都没被核过**（3.2 写着七、文件里十三个）。
        ("中文数字的主语：十三个用例 = 13",
         claim_cells("| `tests/test_x.py` | 十三个用例，不需要凭据 | — |", "zhizhou-v5")
         == [(1, "用例", "tests/test_x.py", 13)]),
        ("「七个用例」要认成 7，而且**写错就红**",
         claim_cells("| `tests/test_x.py` | 七个用例 | — |", "zhizhou-v5")
         == [(1, "用例", "tests/test_x.py", 7)]
         and bool(claim_issues("c.md", [(1, "用例", "tests/test_x.py", 7)],
                               case_count=lambda r: 13, fixture_count=lambda r: 0))),
        ("两种写法等价：`13 个用例` 与 `十三个用例` 都算 13",
         claim_cells("| `tests/test_x.py` | 13 个用例 | — |", "zhizhou-v5")
         == claim_cells("| `tests/test_x.py` | 十三个用例 | — |", "zhizhou-v5")),
        ("读不出来的数字（「一百多个用例」）不算格，也不报错",
         not claim_cells("| `tests/test_x.py` | 一百多个用例 | — |", "zhizhou-v5")),
        ("中文的「一」是量词不是条数：「里有一条用例」不算格（5.4 那两处）",
         not claim_cells("所以 `tests/test_retrieve.py` 里有一条用例把这件事钉死了。",
                         "zhizhou-v5")
         and claim_cells("| `tests/test_x.py` | 1 条用例 | — |", "zhizhou-v5")
         == [(1, "用例", "tests/test_x.py", 1)]),
        ("没主语的「五个用例里第 1、3 个失败」不算格（2.6 那一句）",
         not claim_cells("1. **开头是 `F.F..`**：五个用例里第 1、3 个失败。", "zhizhou-v3")),
    ]
    for label, ok in claim_cases:
        chk(ok, f"条数格夹具没通过：{label}")

    # 用例引用：围栏里「跑了哪些测试、通过多少」（`# N passed` / `# 全树 N 条`）。
    # 这一族的真事：树从 89 长到 150 条之后，正文里还留着 89、122、7 passed、9 passed。
    py_cells = pytest_cells
    py_cases = [
        ("文件主语写对了：沉默（同一行）",
         not pytest_issues("c.md", py_cells("```bash\npython -m pytest tests/x.py -q # 13 passed\n```"),
                           case_count=lambda r: 13, tree_total=150)),
        ("**改一条就红**（写 7 passed、实得 13）",
         bool(pytest_issues("c.md", py_cells("```bash\npython -m pytest tests/x.py -q # 7 passed\n```"),
                            case_count=lambda r: 13, tree_total=150))),
        ("数写在下一行（3.4 的写法）：也认",
         py_cells("```bash\npython -m pytest tests/agent/test_plan.py -q\n# 5 passed\n```")
         == [(3, "tests/agent/test_plan.py", 5)]),
        ("全树那一格：与整棵树的条数比",
         not pytest_issues("c.md", py_cells("```text\n$ python -m pytest tests/ -q   # 全树 150 条\n```"),
                           case_count=lambda r: 13, tree_total=150)
         and bool(pytest_issues("c.md", py_cells("```text\n$ python -m pytest tests/ -q   # 全树 89 条\n```"),
                                case_count=lambda r: 13, tree_total=150))),
        ("全树格不误读成文件主语（`pytest tests/ -q` 后面那个数不是某个文件）",
         py_cells("```text\n$ python -m pytest tests/ -q   # 全树 150 条；本章 23 条\n```")
         == [(2, None, 150)]),
        ("围栏外的叙述不算格（2.1 那句「pytest 全量 42 passed」占的是另一段时间的账）",
         not py_cells("验证：pytest 全量 42 passed（此前 39 passed，新增 3 条）\n")),
        ("围栏里没有 pytest 命令的 `# N passed`：不算格（主语猜不出来就宁可不猜）",
         not py_cells("```bash\n# 4 passed\n```\n")),
        ("两块之间不借主语（第一块有命令、第二块只剩数）",
         py_cells("```bash\npython -m pytest tests/x.py -q\n```\n\n```bash\n# 5 passed\n```\n")
         == []),
        ("真值拿不到（这一趟没跑测试）：报「没法核」而不是叛它过",
         any("真值拿不到" in m for m in pytest_issues(
             "c.md", py_cells("```bash\npython -m pytest tests/x.py -q # 13 passed\n```"),
             case_count=lambda r: None, tree_total=None))),
    ]
    for label, ok in py_cases:
        chk(ok, f"用例引用夹具没通过：{label}")

    # 输出块：标注了命令的围栏，重跑一遍再看引用的行。
    # **这里用的是一条真命令的输出形状**（三行，第二行带后缀），而不是凭空造三行——
    # 夹具要比的是「引用行在不在实跑输出里」，假数据很容易连「顺序」都测不到。
    out_lines = ("  模块：文档点名 26 个路径（其中 app 模块 20 个）｜ 树里 20 个",
                 "  行数：8 处「N 行」标注（8 份文件），逐处与盘上的行数比",
                 "文档对账：五条全过 ｜ 离线自检通过")
    run_ok = lambda argv: (0, list(out_lines))                  # noqa: E731
    run_dead = lambda argv: (2, [])                             # noqa: E731
    scripted = lambda rel: rel.startswith("scripts/")            # noqa: E731

    def fence(cmd: str, body: tuple[str, ...] | list[str]) -> str:
        return "```text $ " + cmd + "\n" + "\n".join(body) + "\n```\n"

    out_cases = [
        ("输出块引用的行按顺序都找得到：沉默",
         not output_issues("c.md", output_blocks(fence("python scripts/x.py --offline", out_lines)),
                           runner=run_ok, exists=scripted)),
        ("**改一个字就红**（引用的行与实跑不符）",
         bool(output_issues("c.md", output_blocks(fence(
             "python scripts/x.py --offline", [out_lines[1].replace("8 处", "9 处")])),
             runner=run_ok, exists=scripted))),
        ("顺序倒了要红（先引末行、再引首行）",
         bool(output_issues("c.md", output_blocks(fence(
             "python scripts/x.py --offline", [out_lines[2], out_lines[0]])),
             runner=run_ok, exists=scripted))),
        ("节选（带一行 `…`）里两段各自按顺序：沉默",
         not output_issues("c.md", output_blocks(fence(
             "python scripts/x.py --offline", [out_lines[0], "…", out_lines[2]])),
             runner=run_ok, exists=scripted)),
        ("命令自己没跑通：就说「没跑通」，不说「引用不符」（两件事修法不同）",
         any("没跑通" in m for m in output_issues(
             "c.md", output_blocks(fence("python scripts/x.py --offline", out_lines)),
             runner=run_dead, exists=scripted))),
        ("标注指向树外（docs/x.py）：要报",
         bool(output_issues("c.md", output_blocks(fence("python docs/x.py --offline", out_lines)),
                            runner=run_ok, exists=scripted))),
        ("没标命令的输出块不算这一类：沉默（模型输出、模板、改坏后重跑的演示都在这一类）",
         not output_blocks("```text\n帮我写一个登录接口\n```\n")),
        ("参数剥得干净（python3 scripts/x.py --offline --check）",
         output_blocks(fence("python3 scripts/x.py --offline --check", ["一"]))[0][1]
         == ("python3", "scripts/x.py", "--offline", "--check")),
        ("空行与节选标记不参与比对",
         not output_issues("c.md", output_blocks(fence(
             "python scripts/x.py --offline", ["", out_lines[0], "", "...", ""])),
             runner=run_ok, exists=scripted)),
    ]
    for label, ok in out_cases:
        chk(ok, f"输出块夹具没通过：{label}")

    # 夹具条数的判读：**「全过」与「没读到」必须分得开**，而条数不能写死。
    # 这一条是被真事故补上的：第 5 篇的评测脚本有 11 条夹具，而这里比的是字符串
    # `"自检 5/5 通过"`——全过却被判成不过，且「判错」与「判不了」在输出里同一句话。
    counts = [
        ("5 条全过（第 3 篇那棵树）", "自检 5/5 通过\n", (5, 5)),
        ("11 条全过（第 5 篇那棵树）", "  ✔ 命中率掉一条\n自检 11/11 通过\n", (11, 11)),
        ("两条没过：要读出来，而不是当全过", "自检 9/11 通过\n", (9, 11)),
        ("没打印那句话：判为『判不了』", "夹具都过了\n", (None, 0)),
        ("两段自检：取最后一次", "自检 3/3 通过\n自检 11/11 通过\n", (11, 11)),
    ]
    for label, stdout, want in counts:
        got = selftest_counts(stdout)
        chk(got == want, f"{label}：期望 {want}，实得 {got}")
    # 分母的来路也印出来：一个没有来路的「N/N」与手写的「N/N」没区别。
    # 末一项用减法得出来，是为了让这行拆分**必然**加起来等于 `total`——
    # 写死一个「每棵树 4 处」的话，哪天给某棵树多加一处，它又会变成一个没人核的数。
    rest = (total - len(cases) - len(cell_cases) - len(claim_cases) - len(py_cases)
            - len(out_cases) - len(counts))
    print(f"  自检 {total - bad}/{total} 通过（块节选 {len(cases)} ＋ 行数格 {len(cell_cases)}"
          f" ＋ 条数格 {len(claim_cases)} ＋ 用例引用 {len(py_cases)} ＋ 输出块 {len(out_cases)}"
          f" ＋ 自检读数 {len(counts)} ＋ 每棵树的清单/标注守与离线入口 {rest} 处）")
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    print("== check_runnable 自检 ==")
    code = self_test()
    if args.self_test or code:
        return code
    print("== 可运行树一致性 ==")
    bad: list[str] = []
    for spec in SPECS:
        print(f"-- {spec.label} {spec.tree.name} --")
        bad += check_consistency(spec.book, spec.tree, chapters(spec.book),
                                 min_chapters=spec.min_chapters, label=spec.label)
        # 两个下限各接各的：`min_modules` 是 app/ 的模块数，`min_tests` 是测试模块数。
        # 4.2 把那两个名字搞混过一次（同一个值被当成两个下限），现在它们真的分开了。
        bad += check_structure(spec.tree, label=spec.label, min_modules=spec.min_modules)
        runs: dict[str, int] = {}
        bad += check_tests(spec.tree, label=spec.label, offline_cmds=spec.offline_cmds,
                           marker=spec.marker, min_modules=spec.min_tests, runs=runs)
        # 第六道：正文表格里标的行数（与代码块同一类「正文关于树盘的断言」）。
        bad += check_line_cells(spec.book, spec.tree, chapters(spec.book),
                                label=spec.label, min_cells=spec.min_line_cells)
        # 第七道：正文里的条数格（夹具数要真跑一次那个脚本的自检；用例数用上一步跑出来的条数）
        bad += check_claims(spec.book, spec.tree, chapters(spec.book),
                            label=spec.label, min_cells=spec.min_claim_cells, runs=runs)
        # 第八道：标注了命令的输出块（重跑那条命令，引用的行逐行比）
        bad += check_output_blocks(spec.book, spec.tree, chapters(spec.book),
                                   label=spec.label, min_blocks=spec.min_output_blocks)
        # 第九道：围栏里的「跑了几条」（`# N passed` / `# 全树 N 条`），逐个与实跑条数比
        bad += check_pytest_claims(spec.book, spec.tree, chapters(spec.book),
                                   label=spec.label, min_cells=spec.min_pytest_cells,
                                   runs=runs)
        bad += check_eval(spec.tree, label=spec.label, summary=spec.eval_summary)
    bad += check_secrets()
    if bad:
        print("\n✖ 有问题：")
        for line in bad:
            print(f"  · {line}")
        return 1
    print("\n✔ 通过")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:                                    # noqa: BLE001
        traceback.print_exc()
        raise SystemExit(1)
