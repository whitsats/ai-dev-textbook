#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全书索引（index_book.py）

    python tools/index_book.py --sync       # 由术语表与正文生成 INDEX.md
    python tools/index_book.py --check      # 盘上的 INDEX.md 必须与生成结果逐字相等
    python tools/index_book.py --self-test  # 夹具（含「登记了却没采用」的反向守）

为什么要有这份索引：全书 69 章没有一条**回查路径**——想找「某个术语在哪几章讲过」，
只能靠 `grep`；而 `grep` 给出的正是「第 1 篇 1 章」这种无法引用、也无法对账的东西。
索引把这条路径变成一份**生成物**：输入只有三样（术语表、`book/**/*.md`、`zhizhou-v*/` 与
`tools/` 的文件清单），所以它**不可能与书稿漂**——漂了 `--check` 就红。

它同时守住术语表的**另一个方向**：`lint_book.py` 只查「避免的写法不许出现」，
从不查「首选写法到底用了没有」。于是术语表可以登记一整批从未落地的词条而没人知道——
接上这份工具当天就查出 **14 条**，并且当天逐条裁定完（10 条改成书里实际的说法、4 条撤销），
所以 `_UNUSED_TERMS` 现在是空的（机制留着，见那一处注释）。
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import lint_book as lb            # noqa: E402 —— 术语表的**唯一**解析在那边（`load_glossary_rows`）
import style_claims as sc         # noqa: E402 —— 书侧「本工具的夹具条数」的对账

INDEX = ROOT / "INDEX.md"

#: 「登记了、而全书一次都没用到」的词条 → 一行理由（`--check` 每次都会把它们报出来）。
#: 这套登记就是本类错的处理流程：**裁定之前不拦提交、也不静默**——
#: 在册的每次跑都出声，而**新出现的**零命名词条一律报错
#: （与 `audit_coverage.py` 的 `_ESTIMATE_DEBT` 同一条思路：欠账可查、新债不许）。
#:
#: 2026-09-21 的第一批 **14 条已全部裁定**（10 条改成书里实际的说法、4 条撤销），
#: 所以现在是空的；判据与逐条理由见 [`STYLE.md`](../STYLE.md) 8.12。
#: 它一度不是空的——正是这份空字典说明那 14 条欠账已经还清：
#: 表里若再长出零命名词条，`--check` 会当场报错，那时把这一条重新填上。
_UNUSED_TERMS: dict[str, str] = {}

#: 索引第二张表的左列：`zhizhou-v*` 目录与 `tools/*.py`，名单由盘上现读。
#: **两列的尺子不一样，因为它们在书里的存在方式不一样**：
#: 树是内容（每篇建一棵，正文必然讲它），所以一棵树全书 0 次出现 → 报错；
#: 而 `tools/` 下的门脚本是**仓库工具**，读者不需要在正文里读到 `totals.py`，
#: 所以 0 次只照实写出来，不进错误。（树内脚本在正文里写作相对路径 `scripts/x.py`，
#: 各树同名时无法区分，因此不单列——它们由 `check_runnable` 的 `SPECS` 与离线入口守着。）
TREE_GLOB = "zhizhou-v*"
TOOL_GLOB = "tools/*.py"

#: 术语里既可能有中文段也可能有英文段（`KV 缓存`、`Vibe Coding`、`span`）。
#: 中文段按子串；**英文段必须带词边界**——否则 `span` 会在 `spanning` 里命中，
#: 而这类假命中的形状本书吃过一次（`mobile_index.py` 的 `Messenger`/`Fragment`）。
_PIECE = re.compile(r"[A-Za-z0-9_.\-]+|[^A-Za-z0-9_.\-]+")


def term_pattern(term: str) -> re.Pattern[str]:
    """把词条编译成匹配式：中文与空白按子串，**英文单词段**按词边界。

    只给「以字母数字开头的段」加边界：空白与标点段（`Vibe Coding` 中间那个空格）
    加了边界反而永远匹配不上——因为它的前一个字符正是前一段的尾字母。
    """
    out = ""
    for piece in _PIECE.findall(term):
        if piece and piece[0].isascii() and piece[0].isalnum():
            out += r"(?<![A-Za-z0-9_])" + re.escape(piece) + r"(?![A-Za-z0-9_])"
        else:
            out += re.escape(piece)
    return re.compile(out)


def path_pattern(name: str) -> re.Pattern[str]:
    """树名／脚本名：按**整体**匹配，两侧不许还连着同类字符。

    `zhizhou-v6` 在「``zhizhou-v6/app/gateway.py``」里要命中（后面跟的是 `/`），
    但 `zhizhou-v6` 不该在 `zhizhou-v60` 里命中。
    """
    return re.compile(r"(?<![A-Za-z0-9_.\-])" + re.escape(name) + r"(?![A-Za-z0-9_\-])")


def chapter_key(cid: str) -> tuple[int, ...]:
    """章号排序键：`1.10` 要排在 `1.2` 后面（字符串序会把它们倒过来）。"""
    return tuple(int(x) for x in cid.split("."))


def chapter_texts() -> dict[str, str]:
    out: dict[str, str] = {}
    for f in lb.chapter_files(None):
        out[f.name.split("-")[0]] = f.read_text(encoding="utf-8")
    return out


def terms() -> list[dict[str, str]]:
    return lb.load_glossary_rows()


def hits(chapters: dict[str, str], pattern: re.Pattern[str]) -> list[str]:
    """命中这个式子的章号（升序）。

    命中范围是**整份章文件**：标题、表格、围栏里的代码注释都算——
    一个词只出现在章标题里（`2.4 与 Vibe Coding 全栈开发`）也是被用到了。
    """
    return sorted((cid for cid, text in chapters.items() if pattern.search(text)),
                  key=chapter_key)


def index_rows(chapters: dict[str, str], rows: list[dict[str, str]]) -> list[dict[str, object]]:
    """术语 → 出现于哪几章。"""
    out: list[dict[str, object]] = []
    for row in rows:
        out.append({**row, "chapters": hits(chapters, term_pattern(row["preferred"]))})
    return out


def unused_terms(rows: list[dict[str, str]],
                 chapters: dict[str, str],
                 registry: dict[str, str] | None = None) -> list[str]:
    """全书 0 命中的词条（**登记表里排除**之后剩下的那些才该报错）。

    `registry` 可注入——夹具靠它钉住「在册的不报、不在册的才报」这一分叉：
    这一批 14 条已经判完、登记表是空的，而**机制必须留着可测**，
    否则下一批真的出现时，没人知道它还会不会响。
    """
    reg = _UNUSED_TERMS if registry is None else registry
    return [r["preferred"] for r in rows
            if not hits(chapters, term_pattern(r["preferred"]))
            and r["preferred"] not in reg]


def trees() -> list[str]:
    """六棵可运行树的目录名（升序）。"""
    return [d.name for d in sorted(ROOT.glob(TREE_GLOB)) if d.is_dir()]


#: `tools/` 下**不是门**的脚本：它们是被别的工具 import 的模块（零入口），
#: 写进索引只会给读者一个查不到的「0 次」——而「0 次」在这里是**照实写**的意思，
#: 会读成「这本书没讲它」。名单里的每一项都必须还在（改名／删掉就在 `--check` 里报）。
NOT_A_GATE: dict[str, str] = {
    "style_claims.py": "被 lint_book / totals / index_book / check_runnable 的自检调用（零入口）",
}


def tools() -> list[str]:
    """`tools/` 下的门脚本（按文件名，升序；不带索引里有交代的零入口模块）。"""
    return [p.name for p in sorted(ROOT.glob(TOOL_GLOB)) if p.name not in NOT_A_GATE]


def toc_lines(chapters: dict[str, str]) -> list[str]:
    """小节目录：一章一行，列它全部 `## N.M.K 标题`。"""
    lines: list[str] = []
    for cid in sorted(chapters, key=chapter_key):
        text = chapters[cid]
        m = re.search(r"^#\s+(.+)$", text, re.M)
        title = re.sub(r"^\d+\.\d+\s*", "", m.group(1).strip()) if m else cid
        secs = re.findall(r"^##\s+(\d+\.\d+\.\d+)\s+(.+?)\s*$", text, re.M)
        lines.append(f"- **{cid} {title}**（{len(secs)} 节）："
                     + " · ".join(f"{n} {t}" for n, t in secs))
    return lines


def render(chapters: dict[str, str], rows: list[dict[str, str]],
           tree_names: list[str], tool_names: list[str]) -> str:
    """生成 INDEX.md 的全文。"""
    out: list[str] = []
    out.append("# 全书索引（INDEX.md）")
    out.append("")
    out.append("> **本文件由脚本生成，不要手改。** 生成 `python tools/index_book.py --sync`；")
    out.append("> 校验 `python tools/index_book.py --check`（提交门与 CI 都跑）。")
    out.append("> 生成只有三样输入：术语表、`book/**/*.md` 的正文、盘上的树与门脚本清单——")
    out.append("> 所以它不可能与书稿漂：漂了 `--check` 就红。")
    out.append(">")
    out.append("> **三条边界**：① 「出现于」按**整份章文件**逐字命中（含标题、表格与围栏里的代码），")
    out.append("> 中文按子串、英文按词边界（`span` 不会命中 `spanning`）；")
    out.append("> ② 「首现」是 [`GLOSSARY.md`](GLOSSARY.md) 登记的那一列（概念被**讲**的章），")
    out.append("> 它与「出现于」的第一个章号**不一定相同**（0.1 是路线图章，只点名不展开）；")
    out.append("> ③ 词条若全书**一次都没出现**，`--check` 报错——术语表登记了却没用上，")
    out.append("> 是两份清单里没人核的那一处。")
    out.append("")
    out.append("---")
    out.append("")

    out.append(f"## 一、术语 → 章节（{len(rows)} 条）")
    out.append("")
    out.append("| 术语 | 英文 | 首现 | 出现于 |")
    out.append("| --- | --- | --- | --- |")
    for r in index_rows(chapters, rows):
        cs: list[str] = r["chapters"]      # type: ignore[assignment]
        where = "、".join(cs) if cs else "**全书 0 次**"
        out.append(f"| {r['preferred']} | {r['en']} | {r['first']} | {where} |")
    out.append("")

    out.append(f"## 二、可运行树与门脚本 → 章节（{len(tree_names)} ＋ {len(tool_names)}）")
    out.append("")
    out.append("> 左列是盘上现读的清单。**两列的尺子不一样**：树是内容——一棵树全书 0 次出现，")
    out.append("> `--check` 会报错；而 `tools/` 下的门脚本是仓库工具，正文不必提它，0 次只照实写。")
    out.append("")
    out.append("| 树 / 脚本 | 出现于 |")
    out.append("| --- | --- |")
    for name in tree_names:
        cs = hits(chapters, path_pattern(name))
        where = "、".join(cs) if cs else "**全书 0 次**"
        out.append(f"| `{name}/` | {where} |")
    for name in tool_names:
        cs = hits(chapters, path_pattern(name))
        where = "、".join(cs) if cs else "（仓库工具，正文不提）"
        out.append(f"| `{name}` | {where} |")
    out.append("")

    out.append(f"## 三、小节总目录（{len(chapters)} 章）")
    out.append("")
    out.extend(toc_lines(chapters))
    return "\n".join(out).rstrip("\n") + "\n"


def build() -> tuple[str, dict[str, str], list[str], list[str], list[str]]:
    """返回（生成文本, 章节正文, 树, 门脚本, 词条）。"""
    chapters = chapter_texts()
    rows = terms()
    tree_names, tool_names = trees(), tools()
    return (render(chapters, rows, tree_names, tool_names),
            chapters, tree_names, tool_names, rows)  # type: ignore[return-value]


def main() -> int:
    ap = argparse.ArgumentParser(description="全书索引")
    ap.add_argument("--sync", action="store_true", help="生成并写回 INDEX.md")
    ap.add_argument("--check", action="store_true", help="盘上的 INDEX.md 必须与生成结果相等")
    ap.add_argument("--self-test", action="store_true", help="只跑夹具")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    text, chapters, tree_names, tool_names, rows = build()
    problems: list[str] = []

    # ① 登记了却一次都没用到的词条：在册的每次跑都出声，**新出现的**报错。
    fresh = unused_terms(rows, chapters)
    for t in fresh:
        problems.append(f"词条「{t}」全书 0 次出现——要么正文漏了它，要么这一行该改／删"
                        f"（在 `_UNUSED_TERMS` 里登记理由，它就会变成一条可查的欠账）")
    present = {r["preferred"] for r in rows}
    known = [t for t in _UNUSED_TERMS
             if t in present and not hits(chapters, term_pattern(t))]
    for t in _UNUSED_TERMS:
        if t not in present:
            problems.append(f"`_UNUSED_TERMS` 里的「{t}」已不在术语表里（那一行被撤销或改名了）——"
                            f"把它从登记表里删掉")
        elif hits(chapters, term_pattern(t)):
            problems.append(f"`_UNUSED_TERMS` 里的「{t}」已经不再是 0 命中（书里补上了）——"
                            f"把它从登记表里删掉")

    # ② 每棵树都必须在全书点名（左列是现读的：新建一棵树而正文没提，就是漏写）。
    for name in tree_names:
        if not hits(chapters, path_pattern(name)):
            problems.append(f"树「{name}」在全书 0 次出现——新建的树没进正文"
                            f"（漏点名比点错名更难看见，所以这一条拦提交）")

    # ②b 被从索引里排除的零入口模块必须还在（否则那一行是凭空的豁免）。
    present_tools = {p.name for p in ROOT.glob(TOOL_GLOB)}
    for name in NOT_A_GATE:
        if name not in present_tools:
            problems.append(f"`NOT_A_GATE` 里的「{name}」已不在 `tools/` 下（改名或删掉了）——"
                            f"把那一条豁免删掉")

    if args.sync:
        INDEX.write_text(text, encoding="utf-8", newline="\n")
        print(f"已写回 {INDEX.name}：术语 {len(rows)} 条（其中 {len(known)} 条登记为未采用）"
              f" ｜ 树 {len(tree_names)} 棵、门脚本 {len(tool_names)} 支 ｜ 章节 {len(chapters)} 章")
    elif args.check:
        if not INDEX.exists():
            problems.append("INDEX.md 不存在：跑 `python tools/index_book.py --sync` 生成")
        else:
            on_disk = INDEX.read_text(encoding="utf-8").replace("\r\n", "\n")
            if on_disk != text:
                line = next((i + 1 for i, (a, b) in
                             enumerate(zip(on_disk.splitlines(), text.splitlines())) if a != b),
                            min(len(on_disk.splitlines()), len(text.splitlines())) + 1)
                problems.append(f"INDEX.md 与生成结果不一致（首个不同在第 {line} 行）："
                                f"书稿或术语表改过了，跑 `--sync` 写回")
    else:
        ap.print_help()
        return 2

    if known:
        print(f"登记为「未采用」的词条 {len(known)} 条（每次跑都出声，判定前不拦提交）：")
        for t in known:
            print(f"  · {t} —— {_UNUSED_TERMS[t]}")
    if problems:
        print()
        for p in problems:
            print(f"[错误] {p}")
        return 1
    if args.check or args.sync:
        print("索引对账通过：术语、" + "树与脚本、" + "小节目录逐处等于从书稿算出来的值。")
    return 0


# ---------------------------------------------------------------------------
# 夹具：全部喂合成输入，不读盘上任何文件——**书稿走到哪一步都不影响它们**。
_TERM_CASES = [
    ("中文词条按子串命中", "本节讲嵌入与向量。", "嵌入", True),
    ("中文词条没出现", "本节只讲提示。", "嵌入", False),
    ("英文词条：`span` 不该命中 `spanning`", "the spanning tree", "span", False),
    ("英文词条：独立出現才算", "看这个 span。", "span", True),
    ("混合词条：`KV 缓存` 按整串命中", "写入 KV 缓存。", "KV 缓存", True),
    ("混合词条：`KV` 在 `KVCache` 里不算", "写入 KVCache。", "KV 缓存", False),
    ("英文词条带空格：`Vibe Coding`", "讲 Vibe Coding 全栈。", "Vibe Coding", True),
]

_ORDER_CASES = [
    ("章号按数字序：1.10 在 1.2 之后", ["1.2", "1.10", "1.3"], ["1.2", "1.3", "1.10"]),
    ("篇也按数字序：10.1 在 2.1 之后", ["10.1", "2.1", "0.3"], ["0.3", "2.1", "10.1"]),
]

# （名称, 章正文, 候选词条, 登记表, 期望报出的）
_UNUSED_CASES = [
    ("登记了却没出现：要报（不在登记表里）", "只讲别的。",
     ["未采用词"], {}, ["未采用词"]),
    ("登记表里的不算（欠账可查、不拦提交）", "只讲别的。",
     ["未采用词"], {"未采用词": "待判"}, []),
    ("用到了就不算", "这里讲未采用词。",
     ["未采用词"], {"未采用词": "待判"}, []),
    ("登记表只挡它自己那条：别的零命中照报", "只讲别的。",
     ["未采用词", "另一个零命中词"], {"未采用词": "待判"}, ["另一个零命中词"]),
]

_TOC_CASES = [
    ("小节目录取 `## N.M.K 标题`，不取别的二级标题",
     "# 1.2 提示工程\n\n## 1.2.1 模板\n\n## 常见坑\n\n## 1.2.2 解析\n",
     ["- **1.2 提示工程**（2 节）：1.2.1 模板 · 1.2.2 解析"]),
]


def self_test() -> int:
    ok = 0
    total = 0
    for name, text, term, want in _TERM_CASES:
        total += 1
        got = bool(term_pattern(term).search(text))
        if got == want:
            ok += 1
        else:
            print(f"  ✖ [词条匹配] {name}：期望{'命中' if want else '不命中'}，实得{'命中' if got else '不命中'}")
    for name, cids, want in _ORDER_CASES:
        total += 1
        got = sorted(cids, key=chapter_key)
        if got == want:
            ok += 1
        else:
            print(f"  ✖ [章序] {name}：期望 {want}，实得 {got}")
    for name, text, cands, registry, want in _UNUSED_CASES:
        total += 1
        got = unused_terms(
            [{"preferred": t, "en": "", "avoid": "", "first": "1.1"} for t in cands],
            {"1.1": text}, registry)
        if got == want:
            ok += 1
        else:
            print(f"  ✖ [未采用词条] {name}：期望 {want}，实得 {got}")
    for name, text, want in _TOC_CASES:
        total += 1
        got = toc_lines({"1.2": text})
        if got == want:
            ok += 1
        else:
            print(f"  ✖ [小节目录] {name}：期望 {want}，实得 {got}")
    print(f"自检：{ok}/{total} 通过")
    # 书侧写到的「`index_book.py` 的夹具条数」必须等于这个 total（`STYLE` 8.12 里有一句）。
    return (0 if ok == total else 1) | sc.report("index_book", total)


if __name__ == "__main__":
    sys.exit(main())
