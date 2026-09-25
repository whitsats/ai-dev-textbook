#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""跨篇结论对账（crosscheck.py）

    python tools/crosscheck.py --check     # 与盘上的 `CROSSCHECK.md` 逐字比
    python tools/crosscheck.py --sync      # 重新生成 `CROSSCHECK.md`
    python tools/crosscheck.py --show KEY  # 单看一条的逐格对账
    python tools/crosscheck.py --self-test # 夹具（含「改一行就红」）

**它补的是哪一半**
------------------
`REVISIT.md` 已经按**体例**（导读怎么写、练习要不要标签、坑有几条）做过一次跨篇普查；
`trace_refs.py --fuzzy` 能**生成候选**——把「说得不一样但讲的是同一件事」的段落按分数排出来。
两者之间空着的那一格是：**判定**。候选要人来判，判完的结果以前只活在人的脑子里：
下一章一写、下一版一改，判过的东西就无声无息地过期（同一句话在十个章里，改一处漏九处，
一个字都不会报错）。本文件把已判过的那几条固定下来——分歧点、各篇口径、建议改法——
再让每一格去盘上**当场复算**。

**分歧不是失败，清单里的谎才是失败**
----------------------------------
这条边界决定了整个工具的成败：

- **分歧**是**读数**（本书确实有两条结论在几篇里说法不一），它被记下来、打印出来、
  跟着 `--check` 一起显示，但**不拦提交**——真拦的话，绿灯要等到有人重写完十章的措辞，
  而报警器一旦会因为「还没修完」而响，就会被 `--no-verify` 绕过；
- **清单自身的三种错**才拦提交（下表）。它们的共同点是：**清单在说自己不成立的话**。

| 清单会怎么坏 | 守卫 |
| --- | --- |
| 它说的那一处**已经不在正文里了**（被改掉、被删掉） | 句式必须在该章命中，否则报「清单过期」 |
| 它记的值**与正文此刻写的不同**（正文改了，清单没跟） | 命中的值必须与清单登记的值逐字相等 |
| 它写「一致」/「待改」**而实跑说的是反话** | `待改` 必须真的还有分歧；`一致` 必须一处分歧都没有 |

第三条是这份清单唯一无法自证的地方——一条「已修好」的旧账会永远显得干净，
所以它**两个方向都要红**：把没修的写成一致会红，把修好了的还挂在「待改」上也会红。

**权威值从哪来（不许手抄）**
--------------------------
一条结论的权威值只有两个来源，都写进登记表里、都由盘上现算：

- `owner`：**出处类**——这条纪律/结论是哪一章**定义**的（`### 离线当门，真机报数`
  在 3.9，就要写 3.9；十二处引用记成 3.10 就是分歧）；
- `span:A-B`：**计数类**——「前 N 篇 M 章」这句话讲的是第 A–B 篇，
  M 必须等于盘上那几篇的章数之和（章数从 `book/` 的目录现读）。

两类都**不接受**「清单自己说它对」：`--check` 每次都重新读正文、重新数章（统计表就印在
`CROSSCHECK.md` 第二节），所以清单里的 `wrote` 只允许等于**正文此刻写的那个值**，
判定只允许等于**实跑算出来的结论**。

**普查计数（第三条守卫，防的是「新加的那一处没人登记」）**
------------------------------------------------------
只核登记过的格子会留下一个反向盲区：**新写的第七处「（3.10 起）」不在清单里，
于是它既不错也不缺**。所以每条登记还带一份 `census`：一个句式 + 应当命中的次数，
在 `book/` 里数一遍，多一处少一处都红。这一条与 `check_runnable` 的「条数格」、
`audit_coverage` 的「夹具名字清单」是同一条思路——不只是「少了几条」，
而是「少的是哪一条」。

**边界（写在这里，免得把沉默读成覆盖）**
------------------------------------
- 只认**阿拉伯数字与章号**：汉字写的数是引文，不是断言（沿用 5.9 那一轮的约定）——
  所以「前**三**篇」里的那个「三」只作旁证登记，不进判定；
- 只扫 `book/`：台账里的同一句话归各自的工具管（`lint_book`／`style_claims`），这里不重复；
- 判定与建议改法是**人写的**，本文件只保证它们不烂在地里——不保证它们是对的。
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys
from dataclasses import dataclass, field

ROOT = pathlib.Path(__file__).resolve().parent.parent
BOOK = ROOT / "book"
DOC = ROOT / "CROSSCHECK.md"


# ---------------------------------------------------------------- 登记表
@dataclass(frozen=True)
class Site:
    """一条结论在某一章里的那一处写法。

    - `pattern`：正文里那一处的句式，**第一组就是正文写的值**；
    - `wrote`：清单登记「正文此刻写的值」——与盘上逐字比（正文改了而清单没跟就红）；
    - `role`：`断言` = 这个值要与权威值比；`旁证` = 只核它在不在（不参与判定，
      例如汉字写的篇数、以及把纪律记在别的章名下的那些前置知识行）；
    - `scope`：`owner`（定义章）或 `span:A-B`（第 A–B 篇的章数之和）。
    """
    chapter: str
    pattern: str
    wrote: str
    role: str = "断言"
    scope: str = "owner"


@dataclass(frozen=True)
class Entry:
    """一条「同一条结论在全书各篇里的说法差异」。"""
    key: str
    kind: str                 # 出处 | 计数
    claim: str                # 这条结论本身
    owner: str                # 权威章（出处类）；计数类留空
    verdict: str              # 待改 | 一致
    divergence: str           # 分歧点
    fix: str                  # 建议改法
    sites: tuple[Site, ...]
    census: tuple[tuple[str, int], ...] = ()   # (句式, 应当命中的次数)，在 book/ 里数


ENTRIES: tuple[Entry, ...] = (
    Entry(
        key="离线当门",
        kind="出处",
        claim="「离线当门、真机报数」：同一条评测集有两种跑法，只有离线那一种能当门"
              "（离线证明「评测这套机器是准的」，真机读的是被测对象此刻的表现）。",
        owner="3.9",
        verdict="待改",
        divergence=(
            "这条纪律的**定义在 3.9.6**（`### 离线当门，真机报数`：离线的剧本让「评测机器本身」"
            "变成确定性的，于是任何变化都只能来自被测的那部分）；它是从 3.10 的端到端验收"
            "**开始成为整章的验收形态**的。而十二处引用把出处记成了 3.10——六处是"
            "「（3.10 起）」，另六处是前置知识里的「3.10（组装与验收。那条「离线当门、真机报数」"
            "的纪律…」。**读者按「3.10 起」回溯，翻到的是 3.10.5 的两条读数（离线的读数、"
            "真机的读数），找不到那条纪律的定义**——而 3.9 才是它被写下来的地方。"),
        fix=(
            "两个方向都要落成一句话，不能停在现状。方向一（把出处写准）：六处「（3.10 起）」"
            "改成「（3.9 定，3.10 起成为整章验收）」，六处前置知识把 3.9 与 3.10 并列引用；"
            "代价是有效字会动（「3.10 起」四个汉字 → 十一个），要按既有那条漂移链补 "
            "`【事后校准】`，并同步 8.7 实测值、LEDGER 逐节表与 PLAN／PROJECT 的字数。"
            "方向二（承认现写法是本书口径）：把「3.10 起」定义成「3.10 起**成为整章验收形态**」"
            "写进 `STYLE` 第八节，同时改掉 3.9 的定位句——好处是零改动、零漂移，"
            "代价是读者仍要自己找到 3.9.6。**两个方向都要连 `owner` 一起改**，否则这一格永远红。"),
        # 句式**不写死那个值**（`(\d+\.\d+)` 而不是 `(3\.10)`）：写死的话，
        # 正文一改，「清单与正文不符」就会被误报成「清单过期」——两种病、两句药，
        # 分不开的话拿到报错还得自己去比一遍。
        sites=(
            Site("5.3", r"(\d+\.\d+)\s*起沿用", "3.10"),
            Site("7.1", r"（(\d+\.\d+)\s*起）", "3.10"),
            Site("7.2", r"（(\d+\.\d+)\s*起）", "3.10"),
            Site("8.1", r"（(\d+\.\d+)\s*起）", "3.10"),
            Site("8.2", r"（(\d+\.\d+)\s*起）", "3.10"),
            Site("8.3", r"（(\d+\.\d+)\s*起）", "3.10"),
            Site("4.1", r"第 (\d+\.\d+) 节的端到端验收与「离线当门、真机报数」",
                 "3.10", role="旁证"),
            Site("8.1", r"(\d+\.\d+)（组装与验收。那条「离线当门、真机报数」", "3.10", role="旁证"),
            Site("8.2", r"(\d+\.\d+)（组装与验收。那条「离线当门、真机报数」", "3.10", role="旁证"),
            Site("8.3", r"(\d+\.\d+)（组装与验收。那条「离线当门、真机报数」", "3.10", role="旁证"),
            Site("8.4", r"(\d+\.\d+)（组装与验收：那条「离线当门、真机报数」", "3.10", role="旁证"),
            Site("8.5", r"(\d+\.\d+)（组装与验收：那条「离线当门、真机报数」", "3.10", role="旁证"),
        ),
        # 只认「起沿用」与「起）」两种收尾：6.3 那句「**超时**：3.10 起，本树每一段真机读数
        # 都带着它的时限」是**另一条**结论（超时纪律），不能顺手算进这一条。
        census=((r"3\.10\s*起[沿用）]", 6),),
    ),
    Entry(
        key="前N篇",
        kind="计数",
        claim="各篇首章导读里那句「前 N 篇 M 章」——本书此前有多少内容。",
        owner="",
        verdict="待改",
        divergence=(
            "同一个句式在三章里说的是三种东西，**没有一处能与盘上对上**："
            "6.1 写「前三篇 41 章」（指第 3–5 篇 ＝ 24 章；41 不属于任何口径）；"
            "7.1 写「前六篇 52 章」（第 1–6 篇 ＝ 49 章；52 是第 1–6 篇 ＋ 导论那 3 章，"
            "也就是**七**篇的量）；8.1 写「前面七篇 52 章」（第 1–7 篇 ＝ 54 章；"
            "52 与 7.1 是同一个数——**8.1 直接沿用了 7.1 的旧数，忘了加上第 7 篇的 5 章**）。"
            "根子在「前 N 篇」**从来没被定义过**：含不含「第 0 篇 导论」、算不算本篇，"
            "书里没有一处说过。对照着看，**篇内那一层是干净的**：5.7 的「前六章」、"
            "5.8 的「前七章」、5.9 的「前八章」都等于第 5 篇的前六／七／八章，一处不差——"
            "坏的只是跨篇这一种。"),
        fix=(
            "把篇号写全，让它不再依赖「前 N 篇」这条没定义的约定，并按选定的口径重算："
            "6.1 → 「第 3–5 篇 24 章里」；7.1 → 口径一「第 1–6 篇 49 章」／口径二"
            "「第 0–6 篇 52 章」；8.1 → 口径一「第 1–7 篇 54 章」／口径二「第 0–7 篇 57 章」。"
            "**先定口径再改**（推荐口径一：**不含第 0 篇导论，且只算本篇之前的篇**——"
            "它与篇内那三章已经成立的写法同构），把定下来的那条写进 `STYLE` 第二节，"
            "本文件里把 `span:A-B` 换成定稿的那一段，判定改成「一致」。"),
        sites=(
            Site("6.1", r"前三篇\s*([\d,]+)\s*章", "41", scope="span:3-5"),
            Site("7.1", r"前六篇\s*([\d,]+)\s*章", "52", scope="span:1-6"),
            Site("8.1", r"前面七篇\s*([\d,]+)\s*章", "52", scope="span:1-7"),
            Site("6.1", r"前([一二三四五六七八九十]+)篇\s*[\d,]+\s*章", "三", role="旁证"),
            Site("7.1", r"前([一二三四五六七八九十]+)篇\s*[\d,]+\s*章", "六", role="旁证"),
            Site("8.1", r"前面([一二三四五六七八九十]+)篇\s*[\d,]+\s*章", "七", role="旁证"),
        ),
        census=((r"前面?[一二三四五六七八九十0-9]+篇\s*[\d,]+\s*章", 3),),
    ),
)

#: 条数下限：扫描/登记退化成空时，`--check` 会安静地说「与盘上一致」。
#: 三个数各接各的（与 `check_runnable` 的 `min_*` 同一形状）。
FLOORS: dict[str, int] = {"条目": 2, "格": 15, "断言格": 9}


# ---------------------------------------------------------------- 盘上事实
@dataclass
class Facts:
    """本次对账的全部输入。三个字段都能喂合成状态（夹具就是这么做的）。"""
    texts: dict[str, str]              # 章号 → 该章正文
    spans: dict[str, int] = field(default_factory=dict)      # 口径串 → 权威值
    corpus: dict[str, str] = field(default_factory=dict)     # 名 → 全文（普查用）

    def text(self, cid: str) -> str:
        return self.texts.get(cid, "")

    def truth(self, site: Site, owner: str) -> tuple[str, str]:
        """这一格的权威值从哪儿来，返回（口径, 值）。读不到就返回 `("", "")`——
        「没法核」与「核过了」必须分得开。"""
        if site.scope == "owner":
            return ("定义章", owner)
        if site.scope.startswith("span:"):
            if site.scope in self.spans:
                return (site.scope, str(self.spans[site.scope]))
        return ("", "")


def chapter_counts() -> list[tuple[str, str, int]]:
    """盘上的篇级章数：[(篇号, 目录, 章数)]，按篇号排序。"""
    out: list[tuple[str, str, int]] = []
    if not BOOK.exists():
        return out
    for d in sorted(p for p in BOOK.iterdir() if p.is_dir()):
        m = re.match(r"(\d+)", d.name)
        if not m:
            continue
        out.append((m.group(1).lstrip("0") or "0", d.name, len(list(d.glob("*.md")))))
    out.sort(key=lambda t: int(t[0]))
    return out


def load_facts(entries: tuple[Entry, ...] = ENTRIES) -> Facts:
    """从盘上现读：每个章文件、每个「span:A-B」的章数之和、普查要扫的语料。"""
    by_no = {no: n for no, _name, n in chapter_counts()}
    spans: dict[str, int] = {}
    for site in (s for e in entries for s in e.sites):
        if site.scope.startswith("span:"):
            a, b = (int(x) for x in site.scope[5:].split("-"))
            spans[site.scope] = sum(by_no.get(str(i), 0) for i in range(a, b + 1))
    texts: dict[str, str] = {}
    corpus: dict[str, str] = {}
    for p in sorted(BOOK.rglob("*.md")):
        text = p.read_text(encoding="utf-8")
        corpus[p.relative_to(ROOT).as_posix()] = text
        m = re.match(r"(\d+\.\d+|\d+)-", p.name)
        if m:
            texts[m.group(1)] = text
    return Facts(texts=texts, spans=spans, corpus=corpus)


# ---------------------------------------------------------------- 对账
def locate(site: Site, facts: Facts) -> tuple[bool, str]:
    """在那一章里找那一处，返回（找到没, 正文此刻写的值）。"""
    mo = re.search(site.pattern, facts.text(site.chapter))
    return (True, mo.group(1)) if mo else (False, "")


def reconcile(facts: Facts, entries: tuple[Entry, ...] = ENTRIES,
              floors: dict[str, int] | None = None) -> tuple[list[str], dict[str, int]]:
    """逐格对账：返回（**清单自身的错**, 统计）。

    统计里的「相符 / 分歧」是**读数**（本书确实还差着的地方），不是失败；
    只有 `issues` 非空才拦提交。每一条问题的措辞都带「写的是 X，权威值是 Y」——
    只报「不一致」的对账，拿到报错还得自己再算一次。
    """
    fl = FLOORS if floors is None else floors
    issues: list[str] = []
    stat = {"条目": len(entries), "格": 0, "断言格": 0, "相符": 0, "分歧": 0}
    for e in entries:
        diverged, broken = 0, 0
        for site in e.sites:
            stat["格"] += 1
            if site.role == "断言":
                # 数的是**声明的**断言格，不是「核成了的」：一个根因只报一条消息。
                # （否则「正文改了」会顺带把下限也拉红——那句话说的是「登记退化了」，
                #  而这里登记得好好的，修的人得先分清哪一句是真话。）
                stat["断言格"] += 1
            where = f"[{e.key}] {site.chapter}"
            found, wrote = locate(site, facts)
            if not found:
                broken += 1
                issues.append(
                    f"清单过期：{where} 那一处**已不在正文里**（句式 `{site.pattern}` "
                    f"在该章一次都没命中）——改了正文就要改清单，两件事同一笔记")
                continue
            if wrote != site.wrote:
                broken += 1
                issues.append(
                    f"清单与正文不符：{where} 正文此刻写的是 `{wrote}`，清单登记的是 "
                    f"`{site.wrote}`——改一处、漏一处，这份清单就变成了第三份口径")
                continue
            if site.role != "断言":
                continue
            _how, truth = facts.truth(site, e.owner)
            if not truth:
                broken += 1
                issues.append(f"权威值读不出来：{where} 的口径 `{site.scope}` 不在盘上"
                              f"（「没法核」与「核过了」必须分得开）")
                continue
            if wrote == truth:
                stat["相符"] += 1
            else:
                stat["分歧"] += 1
                diverged += 1
        # 判定与实跑必须同向：两个方向都要红。
        # **出了结构性错（过期/不符/读不出来）就不叠加判定这一层**：一个根因一条消息，
        # 否则「正文改了」会顺手再报一句「判定过期」，修的人得先分清哪一句是真话。
        if broken:
            continue
        if e.verdict == "待改" and diverged == 0:
            issues.append(
                f"判定过期：[{e.key}] 清单挂着「待改」，而实跑一处分歧都没有——"
                f"修好了就要在同一次提交里把判定改成「一致」（连同建议改法一起）")
        if e.verdict == "一致" and diverged:
            issues.append(
                f"判定不实：[{e.key}] 清单写着「一致」，而实跑**还有 {diverged} 处分歧**——"
                f"这一条是这份清单唯一无法自证的地方：它会一直显得干净")
    # 普查：新加的那一处没人登记，既不错也不缺
    for e in entries:
        for pattern, want in e.census:
            got = sum(len(re.findall(pattern, t)) for t in facts.corpus.values())
            if got != want:
                issues.append(
                    f"普查对不上：[{e.key}] 句式 `{pattern}` 在 `book/` 里数到 {got} 处，"
                    f"登记的是 {want} 处——多出来的那一处要么登记进来，要么改掉；"
                    f"少了的说明句式变了而清单没跟")
    for name, floor in fl.items():
        if stat.get(name, 0) < floor:
            issues.append(f"对账面退化：{name} 只有 {stat.get(name, 0)}，下限是 {floor}"
                          f"——扫描/登记坏了时，`--check` 会安静地说「与盘上一致」")
    return issues, stat


def readings(facts: Facts, entries: tuple[Entry, ...] = ENTRIES) -> list[tuple[Entry, list[str]]]:
    """每条条目的逐格读数：[(条目, [每格一行])]，供报告与 `--show` 用。"""
    out: list[tuple[Entry, list[str]]] = []
    for e in entries:
        rows: list[str] = []
        for site in e.sites:
            found, wrote = locate(site, facts)
            _how, truth = facts.truth(site, e.owner)
            if not found:
                rows.append(f"{site.chapter}\t找不到这一处\t{site.role}\t—\t**清单过期**")
            elif site.role != "断言":
                rows.append(f"{site.chapter}\t{wrote}\t旁证\t—\t"
                            + ("相符" if wrote == site.wrote else f"**清单记的是 `{site.wrote}`**"))
            elif wrote == truth:
                rows.append(f"{site.chapter}\t{wrote}\t断言\t{truth}\t✔ 相符")
            else:
                rows.append(f"{site.chapter}\t{wrote}\t断言\t{truth}\t✖ **分歧**")
        out.append((e, rows))
    return out


# ---------------------------------------------------------------- 报告
def render(facts: Facts, entries: tuple[Entry, ...] = ENTRIES) -> str:
    """生成 `CROSSCHECK.md` 全文。**三样输入**：登记表、`book/` 的正文、盘上的篇级章数。"""
    counts = chapter_counts()
    stat = {"格": 0, "断言格": 0, "相符": 0, "分歧": 0}
    for _e, rows in readings(facts, entries):
        for row in rows:
            stat["格"] += 1
            if "\t断言\t" in row:
                stat["断言格"] += 1
                if "相符" in row:
                    stat["相符"] += 1
                elif "分歧" in row:
                    stat["分歧"] += 1
    out: list[str] = []
    out.append("# 跨篇结论对账（CROSSCHECK.md）")
    out.append("")
    out.append("> **本文件由脚本生成，不要手改。** 生成 `python tools/crosscheck.py --sync`；")
    out.append("> 校验 `python tools/crosscheck.py --check`（提交门与 CI 都跑）；")
    out.append("> 单看一条 `python tools/crosscheck.py --show 离线当门`。")
    out.append(">")
    out.append("> **它管的是中间那一格**：`REVISIT.md` 按**体例**做过一次跨篇普查，")
    out.append("> `trace_refs.py --fuzzy` 负责**生成候选**（哪两句像同一件事）——")
    out.append("> 这份清单管的是**已经判过**的那几条「同一条结论」：分歧点、各篇口径、建议改法。")
    out.append(">")
    out.append("> **分歧不是失败，清单里的谎才是失败**：分歧是**读数**（本书确实还差着的地方），")
    out.append("> 记下来、打印出来，但不拦提交；拦提交的只有清单自身的三种错——")
    out.append("> **清单过期**（那一处已不在正文里）、**清单与正文不符**（正文改了清单没跟）、")
    out.append("> **判定与实跑反了**（把没修的写成「一致」，或把修好的还挂在「待改」上）。")
    out.append(">")
    out.append("> **四条边界**：① 权威值只有两个来源、都由盘上现算——`定义章`（谁是出处）")
    out.append("> 与 `span:A-B`（第 A–B 篇的章数之和，章数从 `book/` 的目录现读）；")
    out.append("> ② 清单里的值是**正文此刻写的值**，逐字比；③ `待改`／`一致` 两个方向都会红；")
    out.append("> ④ 只认阿拉伯数字与章号（汉字是引文不是断言），只扫 `book/`——")
    out.append("> 判定与建议改法是人写的，本文件只保证它们不烂在地里、不保证它们是对的。")
    out.append("")
    out.append("---")
    out.append("")
    out.append(f"## 一、逐条清单（{len(entries)} 条）")
    out.append("")
    for i, (e, rows) in enumerate(readings(facts, entries), 1):
        owner = f"`{e.owner}`" if e.owner else "—"
        out.append(f"### {CIRCLED[i - 1]} {e.key}（{e.kind} ｜ 权威值 {owner} ｜ 判定 **{e.verdict}**）")
        out.append("")
        out.append(f"**结论**：{e.claim}")
        out.append("")
        out.append(f"**分歧点**：{e.divergence}")
        out.append("")
        out.append(f"**建议改法**：{e.fix}")
        out.append("")
        out.append("| 章 | 这一处正文写的是 | 角色 | 权威值 | 逐格结果 |")
        out.append("| --- | --- | --- | --- | --- |")
        for row in rows:
            chap, wrote, role, truth, verdict = row.split("\t")
            out.append(f"| {chap} | `{wrote}` | {role} | {truth} | {verdict} |")
        out.append("")
        cens = "；".join(f"`{p}` 应当命中 {n} 处" for p, n in e.census) or "—"
        out.append(f"> 普查（`book/` 里数一遍，多一处少一处都红）：{cens}。")
        out.append("")

    out.append("---")
    out.append("")
    out.append("## 二、本书此前有多少内容（盘上现读，复核用）")
    out.append("")
    out.append("| 篇 | 目录 | 章数 | 累计 |")
    out.append("| --- | --- | ---: | ---: |")
    acc = 0
    for no, name, n in counts:
        acc += n
        out.append(f"| {no} | `{name}` | {n} | {acc} |")
    out.append(f"| — | **合计** | **{acc}** | — |")
    out.append("")
    out.append("> 「前 N 篇 M 章」这类句子写错时会看得很像真的：`52` 确实是一段真实的章数之和"
               "（第 0–6 篇，也就是七篇），只是与它前面那个「六篇／七篇」不是同一段。")
    out.append("> 这就是为什么那一格必须由盘上现算，而不是由同一句话里的另一个数推出来。")
    out.append("")

    out.append("---")
    out.append("")
    out.append("## 三、本次实跑（`--check` 的读数）")
    out.append("")
    out.append("| 条目 | 格 | 断言格 | 相符 | 分歧 |")
    out.append("| ---: | ---: | ---: | ---: | ---: |")
    out.append(f"| {len(entries)} | {stat['格']} | {stat['断言格']} | "
               f"{stat['相符']} | {stat['分歧']} |")
    out.append("")
    out.append(f"> 两类权威值的来源：`定义章`（谁是出处，如本条清单里的 `3.9`）与 "
               f"`span:A-B`（第 A–B 篇的章数之和，本节那张表现算）。")
    out.append(f"> 下限：条目 ≥ {FLOORS['条目']}、格 ≥ {FLOORS['格']}、"
               f"断言格 ≥ {FLOORS['断言格']}——退化成空时 `--check` 会安静地说「与盘上一致」。")
    out.append("")
    out.append(f"> **判定分布**：待改 {sum(1 for e in entries if e.verdict == '待改')} 条、"
               f"一致 {sum(1 for e in entries if e.verdict == '一致')} 条。"
               f"待改的那几条修好之后，**判定与建议改法要在同一笔提交里改**，否则 `--check` 两边都红。")
    out.append("")
    return "\n".join(out) + "\n"


#: 圈号（`###` 标题用，与 `STYLE` 里的写法一致）。
CIRCLED: tuple[str, ...] = tuple("①②③④⑤⑥⑦⑧⑨⑩")


# ---------------------------------------------------------------- 夹具
def self_test() -> int:
    """合成状态喂进去：每条守卫都要能响，**且不许在无关的地方响**。"""
    bad = 0
    total = 9

    def check(name: str, got: list[str], want_sub: str | None) -> None:
        nonlocal bad
        if want_sub is None:
            if got:
                print(f"  ✖ 夹具「{name}」不该响，却报出：{got[0]}")
                bad += 1
        elif not any(want_sub in msg for msg in got):
            print(f"  ✖ 夹具「{name}」应当报出含「{want_sub}」的那一条，"
                  f"实际：{got or '（没有）'}")
            bad += 1

    def entry(key: str, verdict: str, chapter: str, pattern: str, wrote: str,
              scope: str = "owner", census: tuple[tuple[str, int], ...] = ()) -> Entry:
        return Entry(key=key, kind="出处", claim="c", owner="3.9", verdict=verdict,
                     divergence="d", fix="f",
                     sites=(Site(chapter, pattern, wrote, scope=scope),), census=census)

    # 夹具自带一套小下限：真的那套（格 ≥ 15）是给整本书的，两张格的合成状态
    # 永远到不了——用真下限只会让每条夹具都顺带报一句「对账面退化」。
    floors = {"条目": 2, "格": 2, "断言格": 2}
    # 结构性错（过期/不符/读不出来）会把那几格从「断言格」里减掉，所以那几条夹具
    # 用一套更松的下限：下限本身另有一条夹具（⑦），不必在每条里都验一遍。
    mini = {"条目": 1, "格": 1, "断言格": 1}
    one = {"条目": 1, "格": 2, "断言格": 1}
    syn = (entry("出处例", "待改", "5.3", r"(\d+\.\d+)\s*起沿用", "3.10"),
           entry("计数例", "待改", "6.1", r"前三篇\s*(\d+)\s*章", "41", scope="span:3-5"))
    texts = {"5.3": "……这就是 3.10 起沿用的「离线当门、真机报数」。",
             "6.1": "前三篇 41 章里，知舟……"}

    # ① 现状：两处都与权威值不同 → 各报一条「分歧」，但**不算清单的错**
    got = reconcile(Facts(texts=texts, spans={"span:3-5": 24}), syn, floors)[0]
    check("分歧不是清单的错", got, None)

    # ② 把正文改对（清单没跟）→ 报「清单与正文不符」
    got = reconcile(Facts(texts={**texts, "5.3": "……这就是 3.9 起沿用的。"},
                          spans={"span:3-5": 24}), syn, mini)[0]
    check("正文改了清单没跟要响", got, "清单与正文不符")

    # ③ 那一处整个不在了 → 报「清单过期」（而且**不再叠加**一句「判定过期」）
    got = reconcile(Facts(texts={**texts, "5.3": "……这一章不再提那条纪律。"},
                          spans={"span:3-5": 24}), syn, mini)[0]
    check("清单过期要响", got, "清单过期")
    check("根因只报一条", [m for m in got if "判定" in m], None)

    # ④ 判定与实跑反了：两个方向都要红
    got = reconcile(Facts(texts=texts, spans={"span:3-5": 24}),
                    (entry("出处例", "一致", "5.3", r"(\d+\.\d+)\s*起沿用", "3.10"),
                     entry("计数例", "一致", "6.1", r"前三篇\s*(\d+)\s*章", "41", scope="span:3-5")),
                    floors)[0]
    check("写着「一致」而还有分歧要响", got, "判定不实")
    fixed = Facts(texts={"5.3": "……这就是 3.9 起沿用的。", "6.1": "前三篇 24 章里，知舟……"},
                  spans={"span:3-5": 24})
    got = reconcile(fixed, (entry("出处例", "待改", "5.3", r"(\d+\.\d+)\s*起沿用", "3.9"),
                            entry("计数例", "待改", "6.1", r"前三篇\s*(\d+)\s*章", "24",
                                  scope="span:3-5")), floors)[0]
    check("挂着「待改」而已经修好要响", got, "判定过期")

    # ⑤ 普查：多一处没人登记、少一处说明句式变了
    syn_c = (entry("出处例", "待改", "5.3", r"(\d+\.\d+)\s*起沿用", "3.10",
                   census=((r"3\.10\s*起", 1),)),
             entry("计数例", "待改", "6.1", r"前三篇\s*(\d+)\s*章", "41", scope="span:3-5"))
    got = reconcile(Facts(texts=texts,
                          corpus={"a.md": "……3.10 起……还有一处 3.10 起……"}), syn_c, floors)[0]
    check("普查多一处要响", got, "数到 2 处，登记的是 1 处")
    got = reconcile(Facts(texts=texts, corpus={"a.md": "……3.9 起……"}), syn_c, floors)[0]
    check("普查少一处要响", got, "数到 0 处，登记的是 1 处")

    # ⑥ 权威值读不出来（口径不认识）→ 不当成「核过了」
    got = reconcile(Facts(texts=texts),
                    (entry("出处例", "待改", "5.3", r"(\d+\.\d+)\s*起沿用", "3.10"),
                     entry("计数例", "待改", "6.1", r"前三篇\s*(\d+)\s*章", "41",
                           scope="span:9-9")), mini)[0]
    check("权威值读不出来要响", got, "权威值读不出来")

    # ⑦ 下限：登记退化成空时不许安静
    got = reconcile(Facts(texts={}), (), floors)[0]
    check("退化要响", got, "对账面退化")

    # ⑧ 干净状态下一条都不许响（含旁证格：它只核存在）
    clean = (Entry(key="a", kind="出处", claim="c", owner="3.9", verdict="一致",
                   divergence="d", fix="f",
                   sites=(Site("5.3", r"(\d+\.\d+)\s*起沿用", "3.9"),
                          Site("5.3", r"(\d+\.\d+)\s*起沿用", "3.9", role="旁证"))),)
    check("干净状态不许响",
          reconcile(Facts(texts={"5.3": "……这就是 3.9 起沿用的。"}), clean, one)[0], None)

    print(f"跨篇结论对账自检：{total - bad}/{total} 通过"
          + ("" if not bad else f"（{bad} 条不过）"))
    # 书侧（`STYLE`／`README`）若写了「crosscheck.py … N 条夹具」，那个数必须等于这个分母；
    # 没接线的后果是那颗数落在所有门的射程外（`lint_book` 的 `check_style_claims_wired` 管这件事）。
    import style_claims as sc
    return sc.report("crosscheck", total) | (1 if bad else 0)


# ---------------------------------------------------------------- 入口
def main() -> int:
    ap = argparse.ArgumentParser(description="跨篇结论对账（CROSSCHECK.md）")
    ap.add_argument("--sync", action="store_true", help="重新生成 CROSSCHECK.md")
    ap.add_argument("--check", action="store_true", help="与盘上的 CROSSCHECK.md 逐字比")
    ap.add_argument("--show", metavar="KEY", help="单看一条的逐格对账（条目名或章号）")
    ap.add_argument("--self-test", action="store_true", help="用合成状态自检")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    facts = load_facts()
    issues, stat = reconcile(facts)

    if args.show:
        hit = [(e, rows) for e, rows in readings(facts)
               if e.key == args.show or any(r.startswith(args.show + "\t") for r in rows)]
        if not hit:
            print(f"没有登记过「{args.show}」——现有条目：{'、'.join(e.key for e in ENTRIES)}")
            return 1
        for e, rows in hit:
            print(f"◆ {e.key}（{e.kind} ｜ 权威值 {e.owner or '—'} ｜ 判定 {e.verdict}）")
            print(f"  结论：{e.claim}")
            print(f"  分歧：{e.divergence}")
            print(f"  改法：{e.fix}")
            for row in rows:
                chap, wrote, role, truth, verdict = row.split("\t")
                print(f"    {chap:<5} {role:<3} 正文写 {wrote:<6} 权威 {truth:<6} {verdict}")
        return 0

    if args.sync:
        text = render(facts)
        DOC.write_text(text, encoding="utf-8")
        print(f"  · 已生成 {DOC.name}（{len(text.splitlines())} 行）：{stat['条目']} 条、"
              f"{stat['格']} 格（断言 {stat['断言格']}）")

    # 先报清单自身的错，再比生成的文档——两件事都要说，不能只报后面那一条
    for msg in issues:
        print(f"  ✖ [跨篇结论] {msg}")

    stale = ""
    if not args.sync:
        want = render(facts)
        got = DOC.read_text(encoding="utf-8") if DOC.exists() else ""
        if got != want:
            stale = f"  ✖ {DOC.name} 与盘上不一致——重跑 `python tools/crosscheck.py --sync`"
            for i, (a, b) in enumerate(zip(got.splitlines(), want.splitlines()), 1):
                if a != b:
                    stale += f"\n      第 {i} 行：\n        盘上 {a[:110]}\n        应写 {b[:110]}"
                    break
            else:
                stale += (f"\n      行数不同：盘上 {len(got.splitlines())}，"
                          f"应写 {len(want.splitlines())}")
            print(stale)

    if args.check or not (issues or args.sync):
        tail = ("——判定与实跑同向；`CROSSCHECK.md` 与盘上逐字相符"
                if not (issues or stale) else "（清单自身有问题，见上；分歧数只是读数）")
        print(f"  · 跨篇结论对账：{stat['条目']} 条 / {stat['格']} 格（断言 {stat['断言格']}）"
              f"：相符 {stat['相符']}、分歧 {stat['分歧']}{tail}")
    return 1 if (issues or stale) else 0


if __name__ == "__main__":
    sys.exit(main())
