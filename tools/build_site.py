#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把全书拼进一个临时目录，供站点生成器（Zensical）构建。

为什么需要这一步
----------------
站点生成器只有**一个** docs_dir，而这本书的正文天然分居两处：69 章在 `book/<篇>/`、
14 份根级文档在仓库根目录，两者还互相引用。两种做法里选后者：

  ✗ 把正文复制一份进 `docs/` 再提交 —— 仓库里于是同时存在两份教材，改一处忘一处。
    这本书已经因为「手抄的第二份数不会自己跟着改」交过好几次学费（台账、PLAN 看板、
    INDEX.md、附录），多一份正文只会是同一个坑的第六次。
  ✓ **构建时临时拼装**（本脚本）—— 仓库里始终只有一份原文，站点是它的产物。
    `site-src/` 与 `site-out/` 都在 .gitignore 里。

拼装做三件事
------------
1. **排布**：`README.md` → `index.md`（站点没有 README 这个概念，首页必须是 index.md）；
   正文按 `<篇>/<章>.md` 原结构搬；读者向的参考文档进 `90-参考/`；工程向的进 `99-元文档/`。
   14 份根级文档**保持同一个目录、同一个文件名**——它们之间 142 处互相引用都是裸文件名
   （`](PLAN.md)`），不动目录就等于不动链接。
2. **重命名**：章文件名里的次版本号补零（`1.2-…` → `1.02-…`）。理由只有一个：站点导航按
   文件名排序，而 `1.10` 的字典序在 `1.2` 之前——不补零，第 10 章会排到第 2 章前面。
   **排序是文件名的事，不是人手写一份 nav 的事**：手写 nav 就是又一份会漂的清单
   （新增一章忘了改 nav，那一章在站上直接消失，而构建照样绿）。篇与篇之间由目录名
   前缀（`01-`、`10-`）定序，本来就是两位，不用动。
3. **改写 + 去硬换行**：跨目录的 `.md` 链接改指到新位置；中文段落里被硬换行拆开的行接
   回去（否则站上每个接缝处都会多出一个空格）。**只改副本，源文件一个字节不动。**

一种弄坏的姿势特别值得防：**站点会静默地少东西**。链接指向站里没有的页 ⇒ 构建红或读者
点空；排序把章排错 ⇒ 目录顺序看着正常但没有一章在它该在的位置。所以本脚本宁可失败：
解析不到的链接会列出来并让退出码非 0（见 `main()` 末尾）。

用法（三步，本脚本是第一步）
----------------------------
    python tools/build_site.py                                    # 生成 site-src/
    uvx --with-requirements requirements-docs.txt zensical serve  # 本地预览
    uvx --with-requirements requirements-docs.txt zensical build --strict --clean

CI 在推送到 main 时做同样的事并部署到 GitHub Pages，见 .github/workflows/docs.yml。
"""

from __future__ import annotations

import argparse
import posixpath
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "site-src"
BOOK = ROOT / "book"

#: 读者向：术语表、学习计划、全书索引、官方出处。
REF_DIR = "90-参考"
REFERENCE_DOCS = ("GLOSSARY.md", "LEARNING.md", "INDEX.md", "REFERENCES.md")
#: 工程向：这本书是怎么做出来的（体例、台账、计划、覆盖度、风险、附录、普查、跨篇结论）。
META_DIR = "99-元文档"
META_DOCS = ("STYLE.md", "LEDGER.md", "PLAN.md", "PROJECT.md", "COVERAGE.md",
             "GAPS.md", "APPENDIX.md", "REVISIT.md", "CROSSCHECK.md")
#: 首页。
HOME = ("README.md", "index.md")
#: 仓库里存在但**不进站点**的文件（LICENSE 等）：链接改指 GitHub——读得到，又不把仓库
#: 杂项摊进正文。`--strict` 会把指向站外的相对链接当死链，所以必须换掉。
BLOB = "https://github.com/whitsats/ai-dev-textbook/blob/main/"

#: 链接语法：`[文字](目标 "可选标题")`。`![...]` 是图片，不在此列（这本书没有图片）。
LINK_RE = re.compile(r"(?<!!)\[([^\]\n]*)\]\(\s*(<[^>\n]*>|[^)\s]+)(\s+\"[^\"]*\")?\s*\)")
#: 章文件名：`10.4-标题.md`。
CHAPTER_RE = re.compile(r"^(\d+)\.(\d+)(-.*)$")
#: 中文（连全角标点一起）：判断两行之间该不该有空格。
CJK_RE = re.compile(r"[\u3000-\u303f\u4e00-\u9fff\uff00-\uffef]")
#: 行首这些字符意味着「这行不是散文」。
BLOCK_START = ("#", "|", ">", "-", "*", "+", "=", "<", "!", " ", "\t")
LIST_START = re.compile(r"^(\d+[.、)]|[-*+]\s)")
FENCE = ("```", "~~~")


def pad_chapter(name: str) -> str:
    """`1.2-Python语法速通.md` → `1.02-Python语法速通.md`（排序用，不是改章号）。"""
    m = CHAPTER_RE.match(name)
    if not m:
        return name
    major, minor, rest = m.groups()
    return f"{major}.{minor.zfill(2)}{rest}"


def site_plan() -> dict[str, str]:
    """计划：仓库相对路径（posix） → 站点相对路径（posix）。

    这个计划是脚本**唯一**的事实来源：搬哪些、搬去哪、叫什么，全都从这里读；
    页数与自检里的「有没有两个源撞到同一个站点路径」也基于它。
    """
    plan: dict[str, str] = {HOME[0]: HOME[1]}
    for doc in REFERENCE_DOCS:
        plan[doc] = f"{REF_DIR}/{doc}"
    for doc in META_DOCS:
        plan[doc] = f"{META_DIR}/{doc}"
    for part in sorted(p for p in BOOK.iterdir() if p.is_dir()):
        for chapter in sorted(part.glob("*.md")):
            plan[chapter.relative_to(ROOT).as_posix()] = f"{part.name}/{pad_chapter(chapter.name)}"
    return plan


def by_basename(plan: dict[str, str]) -> dict[str, str]:
    """文件名 → **源路径**（仓库相对）。兜底用：正文里有几处把根级文档写成裸文件名
    （`[STYLE.md](STYLE.md)` 写在章节目录里），从章节目录出发解析不到——但它指的是谁
    一望可知，所以按文件名兜底。同名两个源就直接炸，不猜（猜错的链接比不写链接更坏）。
    """
    out: dict[str, str] = {}
    for src in plan:
        name = posixpath.basename(src)
        if name in out and out[name] != src:
            raise SystemExit(f"✖ 两个源文件同名（{name}）——按文件名兜底会猜错，请手工修链接")
        out[name] = src
    return out


def rel_url(to_site_path: str, from_site_path: str) -> str:
    """站点内相对链接（两个都是站内相对 posix 路径）。"""
    return posixpath.relpath(to_site_path, posixpath.dirname(from_site_path) or ".")


def lookup(src_rel: str, path_part: str, plan: dict[str, str],
           by_name: dict[str, str]) -> str | None:
    """一个本地链接目标 → 它对应的**源**路径（仓库相对）；解析不到返回 None。

    两步：① 按相对路径解析（`./`、`../` 都算）；② 解析不到再按**文件名**兜底。
    """
    guess = posixpath.normpath(posixpath.join(posixpath.dirname(src_rel), path_part))
    if guess in plan:
        return guess
    return by_name.get(posixpath.basename(path_part))


def rewrite_links(text: str, src_rel: str, plan: dict[str, str], by_name: dict[str, str],
                  report: list[str]) -> tuple[str, int, int]:
    """把链接指到站点里的新位置。返回（新文本, 改写处数, 指去 GitHub 处数）。

    只碰两种目标：以 `.md` 结尾的（站内页）、以及仓库里存在但不进站点的文件。
    **不碰**外链、`#锚点`、图片，以及那些看起来像 `](?:cmd|exec|url)` 的**假目标**
    ——它们是正文里的正则与代码，不是链接（用宽正则扫描时就会把它们数成链接）。
    """
    dst_rel = plan[src_rel]
    changed = blobs = 0

    def sub(m: re.Match) -> str:
        nonlocal changed, blobs
        label, raw, title = m.group(1), m.group(2), m.group(3) or ""
        angled = raw.startswith("<") and raw.endswith(">")
        target = raw[1:-1] if angled else raw
        if re.match(r"^[a-z][a-z0-9+.-]*:", target) or target.startswith("#"):
            return m.group(0)                                  # 外链 / 页内锚点
        path_part, sep, anchor = target.partition("#")
        guess = posixpath.normpath(posixpath.join(posixpath.dirname(src_rel), path_part))
        if not path_part.lower().endswith(".md"):
            if path_part and (ROOT / guess).is_file():
                blobs += 1
                return f"[{label}]({BLOB}{guess})"             # LICENSE 这类：指去 GitHub
            return m.group(0)                                  # 假目标：不动
        src_of_target = lookup(src_rel, path_part, plan, by_name)
        if src_of_target is None:
            report.append(f"{src_rel} → {target}")
            return m.group(0)                                  # 原样留着，由调用方报错
        url = rel_url(plan[src_of_target], dst_rel) + (sep + anchor if sep else "")
        if url == target:
            return m.group(0)
        changed += 1
        return f"[{label}]({'<' + url + '>' if angled else url}{title})"

    return LINK_RE.sub(sub, text), changed, blobs


def unwrap_paragraphs(text: str) -> tuple[str, int]:
    """把被硬换行拆开的**中文**段落接回去。返回（新文本, 接了几处）。

    为什么需要它：正文是硬换行的（按列宽折断），而 Markdown 段落里的换行在浏览器里会
    折成一个**空格**——中文句子中间于是每行多一个空格。判据故意收得很紧：上一行末尾是
    中文（允许跟一串强调符号）、这一行开头也是中文、且两行都是散文行。中英混排的缝
    **保留空格**（那里本来就该有空格），代码围栏、表格、列表、引用块、缩进行一律不碰
    ——宁可漏接，不可接错。
    """
    out: list[str] = []
    joined = 0
    in_fence = False
    for line in text.split("\n"):
        if line.lstrip().startswith(FENCE):
            in_fence = not in_fence
            out.append(line)
            continue
        if in_fence or not line.strip():
            out.append(line)
            continue
        prev = out[-1] if out else ""
        prev_plain = (bool(prev.strip())
                      and not prev.lstrip().startswith(BLOCK_START)
                      and not LIST_START.match(prev.lstrip())
                      and not prev.endswith(("  ", "\\")))
        cur_plain = (not line.startswith(BLOCK_START)
                     and not LIST_START.match(line)
                     and CJK_RE.match(line[:1]) is not None)
        if prev_plain and cur_plain:
            core = prev.rstrip("*_`）)】]「”’")
            if core and CJK_RE.search(core[-1]):
                out[-1] = prev + line
                joined += 1
                continue
        out.append(line)
    return "\n".join(out), joined


def main() -> int:
    ap = argparse.ArgumentParser(description="拼装站点源文件到 site-src/（供 Zensical 构建）")
    ap.add_argument("--self-test", action="store_true", help="用合成状态自检")
    args = ap.parse_args()
    if args.self_test:
        return self_test()

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

    plan = site_plan()
    if len(set(plan.values())) != len(plan):
        print("✖ 两个源文件映射到了同一个站点路径（站点上会少一页）", file=sys.stderr)
        return 1
    by_name = by_basename(plan)
    try:
        if OUT.exists():
            shutil.rmtree(OUT)
        OUT.mkdir(parents=True)
    except OSError as exc:
        print(f"✖ 清理/创建 {OUT.name}/ 失败：{exc}", file=sys.stderr)
        return 1

    report: list[str] = []
    links = blobs = joined = 0
    for src_rel, dst_rel in sorted(plan.items()):
        src = ROOT / src_rel
        if not src.is_file():
            print(f"✖ 计划里的源文件不存在：{src_rel}", file=sys.stderr)
            return 1
        text = src.read_text(encoding="utf-8")
        text, n_links, n_blobs = rewrite_links(text, src_rel, plan, by_name, report)
        text, n_joined = unwrap_paragraphs(text)
        dst = OUT / dst_rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(text, encoding="utf-8")
        links += n_links
        blobs += n_blobs
        joined += n_joined

    chapters = sum(1 for s in plan if s.startswith("book/"))
    print(f"✓ 已生成 {OUT.relative_to(ROOT)}/：{len(plan)} 页"
          f"（正文 {chapters} ＋ 参考与元文档 {len(plan) - chapters}）")
    print(f"  跨目录链接改写 {links} 处 ｜ 指去 GitHub 的 {blobs} 处 ｜ "
          f"中文段落去硬换行 {joined} 处")
    if report:
        # 不许静默：链接解析不到的后果是「站上少一页 / 读者点空」，而它在日志里
        # 与「一切正常」长得一样——所以这里直接判失败（--strict 那一趟也会红）。
        print(f"\n✖ {len(report)} 处链接指向站点里没有的页：", file=sys.stderr)
        for line in report[:20]:
            print(f"    {line}", file=sys.stderr)
        return 1
    print("  本地预览：uvx --with-requirements requirements-docs.txt zensical serve")
    return 0


# ---------------------------------------------------------------- 夹具

def self_test() -> int:
    """合成输入：每条判据都要能响，且不许在无关的地方响。

    守的不是「页面好不好看」，而是站点**会静默地少东西**的那三种方式：链接指向站里
    没有的页、排序把章排错、以及把代码/表格当散文接回去（那会改坏正文，而站上看起来
    仍然「有内容」）。最后两条夹具读盘上真实的书稿——它们守的是「计划本身自洽」。
    """
    bad = 0
    total = 18

    def eq(name: str, got, want) -> None:
        nonlocal bad
        if got != want:
            print(f"  ✖ 夹具「{name}」：期望 {want!r}，实得 {got!r}")
            bad += 1

    # ①–③ 排序：补零，且补完后的字典序就是章序
    eq("章名补零", pad_chapter("1.2-Python语法速通.md"), "1.02-Python语法速通.md")
    eq("两位次版本号不动", pad_chapter("1.15-项目实战.md"), "1.15-项目实战.md")
    eq("补零后的字典序就是章序",
       sorted(pad_chapter(n) for n in ("1.2-甲", "1.10-乙", "1.1-丙", "1.15-丁")),
       ["1.01-丙", "1.02-甲", "1.10-乙", "1.15-丁"])

    plan = {
        "README.md": "index.md",
        "STYLE.md": "99-元文档/STYLE.md",
        "PLAN.md": "99-元文档/PLAN.md",
        "book/01-编程地基/1.1-环境搭建.md": "01-编程地基/1.01-环境搭建.md",
        "book/03-大模型与Agent原理/3.1-大模型基础.md": "03-大模型与Agent原理/3.1-大模型基础.md",
    }
    by_name = by_basename(plan)
    rep: list[str] = []

    def rw(text: str, src: str) -> tuple[str, int]:
        got, n, _ = rewrite_links(text, src, plan, by_name, rep)
        return got, n

    # ④ 同目录裸名：站点里它们仍在同一目录，一个字都不用改
    eq("同目录裸名链接不动", rw("[`PLAN.md`](PLAN.md)", "STYLE.md"),
       ("[`PLAN.md`](PLAN.md)", 0))
    # ⑤ 跨目录：章 → 根级文档
    eq("跨目录链接改对", rw("[STYLE.md](../../STYLE.md)", "book/01-编程地基/1.1-环境搭建.md"),
       ("[STYLE.md](../99-元文档/STYLE.md)", 1))
    # ⑥ 改名后的章互链（补零让路径变了，链接得跟着）
    eq("改名后的章互链", rw("[环境搭建](./1.1-环境搭建.md)", "book/01-编程地基/1.1-环境搭建.md"),
       ("[环境搭建](1.01-环境搭建.md)", 1))
    # ⑦ 从章节目录出发的裸文件名 → 按名字兜底
    eq("裸文件名按名字兜底", rw("[STYLE.md](STYLE.md)", "book/03-大模型与Agent原理/3.1-大模型基础.md"),
       ("[STYLE.md](../99-元文档/STYLE.md)", 1))
    # ⑧ 仓库里有、但不进站点的文件 → 指去 GitHub（否则 --strict 当死链）
    eq("LICENSE 指去 GitHub",
       rw("[许可](LICENSE)", "STYLE.md")[0],
       f"[许可]({BLOB}LICENSE)")
    # ⑨–⑪ 三类不许动的目标
    eq("正则里的假目标不动", rw("`[a-z](?:cmd|exec|url)`", "book/01-编程地基/1.1-环境搭建.md"),
       ("`[a-z](?:cmd|exec|url)`", 0))
    eq("页内锚点不动", rw("[跳](#四、附录)", "book/01-编程地基/1.1-环境搭建.md"),
       ("[跳](#四、附录)", 0))
    eq("外链不动", rw("[官网](https://example.com/a.md)", "book/01-编程地基/1.1-环境搭建.md"),
       ("[官网](https://example.com/a.md)", 0))
    # ⑫ 解析不到的必须被报出来（不许静默通过）
    rep2: list[str] = []
    got, n, _ = rewrite_links("[野](../no-such-page.md)", "STYLE.md", plan, by_name, rep2)
    eq("野链接被报出来", (got, n, len(rep2)), ("[野](../no-such-page.md)", 0, 1))

    # ⑬–⑯ 去硬换行：该接的接、不该接的一个都不许接
    eq("中文缝接回去", unwrap_paragraphs("这一段被硬换行了，\n下一行的开头还是中文。"),
       ("这一段被硬换行了，下一行的开头还是中文。", 1))
    eq("中英缝保留空格", unwrap_paragraphs("这一行以中文结尾，\nnext line 是英文。"),
       ("这一行以中文结尾，\nnext line 是英文。", 0))
    eq("代码围栏不碰", unwrap_paragraphs("```\nx = 1\n下一行还是代码\n```"),
       ("```\nx = 1\n下一行还是代码\n```", 0))
    eq("表格与列表不碰",
       (unwrap_paragraphs("| 甲 | 乙 |\n| 一 | 二 |")[1], unwrap_paragraphs("- 第一条，\n- 第二条")[1]),
       (0, 0))

    # ⑰ 计划自洽：14 份根级文档全部有落点，正文一章不漏（读盘上真实的书稿）
    real = site_plan()
    eq("根级 14 份都在计划里", sum(1 for s in real if not s.startswith("book/")), 14)
    eq("正文 69 章都在计划里", sum(1 for s in real if s.startswith("book/")),
       len(list(BOOK.glob("*/*.md"))))

    print(f"站点拼装自检：{total - bad}/{total} 通过" + ("" if not bad else "（见上）"))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
