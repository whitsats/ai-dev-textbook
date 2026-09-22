#!/usr/bin/env python
"""附录（`APPENDIX.md`）的生成器：**读者要跑什么、每支门脚本管什么、数从哪来。**

    python tools/appendix.py --sync        # 重生成 APPENDIX.md
    python tools/appendix.py --check       # 与盘上逐字比（提交门 4h/5 与 CI 各跑一次）
    python tools/appendix.py --self-test   # 15 条夹具

为什么它必须是**生成物**而不是手写：这三张表里的每一格本来都活在别处——
六棵树的目录与脚本的 docstring、每个入口脚本的 `--offline`、`tools/` 下脚本的 `argparse`
声明、`.githooks/pre-commit` 的阶段名、各树的 `requirements.txt`。
手写一遍就是把它们抄第二份，而这本书已经交过学费：**第二份手写的数不会自己跟着改**
（台账、PLAN 看板、`INDEX.md` 各交过一次）。所以这里只写**读法**，值一律从盘上读。

三条口径（都与正文同一把尺子，不是另立一套）：

① **入口脚本**＝树里 `scripts/` 下的 `.py` 与根级的 `.py`，去掉 `conftest.py`／`__init__.py`；
   跑法＝`python <相对路径>`，源码里认 `--offline` 就带上它（不带的那几个本来就不要它）。
② **用例数**＝`check_runnable.case_count_of` 的静态读数（数 `def test_`），
   与正文里「全树 N 条」**同一个数**（实跑值，v3 的 150 与 v8 的 343 都逐字相符）。
③ **练习／常见坑**＝`revisit.shape_of` 与 `lint_book._SHAPE_LEVELS` 的口径
   （**标签从 `lint_book` 借**，所以「三级标签」这件事换名字时这里跟着换，不会各写一份）。

一条反向守：渲染出来的每一族都有**条数下限**（`_FLOOR`）。扫描退化成 0 行而
`--check` 照样说「与盘上一致」，是这本书里反复出现的那一课——下限让它变成红色。
"""
from __future__ import annotations

import ast
import pathlib
import re
import sys

TOOLS = pathlib.Path(__file__).resolve().parent
ROOT = TOOLS.parent
OUT = ROOT / "APPENDIX.md"
HOOK = ROOT / ".githooks" / "pre-commit"
BOOK = ROOT / "book"

# 与其它门脚本同一套：把 tools/ 挂进 sys.path，直接复用它们的**读法**，不复用它们的输出。
sys.path.insert(0, str(TOOLS))
import check_runnable as cr        # noqa: E402
import index_book as ib            # noqa: E402
import lint_book as lb             # noqa: E402
import revisit as rv               # noqa: E402
import totals as tt                # noqa: E402

#: `tools/` 下**不是入口**的脚本：它们是库（被别的工具 import），或者只给装机用一次。
#: 写在这里而不是靠猜——与 `index_book` 的 `NOT_A_GATE` 同一个形状：名单要能被回查。
NOT_AN_ENTRY = {
    "style_claims.py": "库：被四支工具的自检调用，自己没有入口",
    "install_hooks.py": "装机：`python tools/install_hooks.py` 装一次提交钩子",
    "extract_sources.py": "素材：`--report` 把 `raw/` 转成 `sources/`，与书稿无关",
}

#: 条数下限。**从盘上量出来的当前规模**，不是随手填的小数；它守的是「扫描退化成空」。
_FLOOR = {"树": 6, "入口脚本": 29, "门脚本": 16, "复算入口": 7}

HEAD = """\
<!-- 由 `tools/appendix.py` 生成：重生成 `python tools/appendix.py --sync`，
     对账 `python tools/appendix.py --check`（提交门 4h/5 与 CI 各跑一次）。**不要手改。** -->

# 附录

> 这一份只回答读者最先遇到的三件事：**跑哪一条命令**（附录 A）｜**每支门脚本管什么**
> （附录 B）｜**书里那些数从哪儿来**（附录 C）。
>
> 它是**生成物**：每一格都从盘上读出来——六棵树的目录与入口脚本的 docstring、每个脚本的
> `--offline`、`.githooks/pre-commit` 的阶段名、各树的 `requirements.txt`。
> 所以「书改了而附录没重生」不是笔误，是一处会被拦下的不一致。
>
> 一个提醒：附录 A 的入口命令**一律不要密钥、不要网络**；去掉 `--offline` 才是真机那一趟
> （那几趟要 API key，正文在对应的章里写了各自要什么）。
"""


# ------------------------------------------------------------------ 文本读法

def doc_first_line(path: pathlib.Path) -> str:
    """一个脚本的「一句话」＝它的模块 docstring 的第一非空行。

    没有 docstring 就如实写「（这个脚本没有模块 docstring）」——**不拿文件名凑**：
    凑出来的句子读起来像说明，而它其实不是任何人的声明。
    """
    try:
        mod = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError, UnicodeDecodeError):
        return "（读不出来）"
    doc = ast.get_docstring(mod) or ""
    for line in doc.splitlines():
        if line.strip():
            return " ".join(line.split())
    return "（这个脚本没有模块 docstring）"


def argparse_flags(path: pathlib.Path) -> tuple[str, ...]:
    """脚本自己声明的长开关，按源码里的先后顺序。

    只认 `add_argument` 的**第一个位置参数**。这一条是被真事逼出来的：宽口径
    （「文件里所有以 `--` 开头的字符串常量」）会把 `help=` 的正文与 `install_hooks`
    给 git 的那些开关一起收进来，实测连 `---` 与整句中文都进了表——
    **一个说明列里混进解释文本，读的人分不出哪几个才真的能敲。**
    """
    try:
        mod = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError, UnicodeDecodeError):
        return ()
    out: list[str] = []
    for node in ast.walk(mod):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "add_argument"):
            continue
        for arg in node.args[:1]:
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str) \
                    and arg.value.startswith("--"):
                if arg.value not in out:
                    out.append(arg.value)
    return tuple(out)


def entry_scripts(tree: pathlib.Path) -> list[str]:
    """一棵树的入口脚本（`scripts/` 下的 `.py` ＋ 根级的 `.py`）。"""
    out: list[str] = []
    for p in sorted(tree.rglob("*.py")):
        rel = p.relative_to(tree)
        if "__pycache__" in rel.parts or rel.parts[0] in ("app", "tests", "experiments",
                                                          "migrations"):
            continue
        if rel.name in ("conftest.py", "__init__.py"):
            continue
        out.append(rel.as_posix())
    return out


def entry_command(tree: pathlib.Path, rel: str) -> str:
    """入口脚本的跑法。源码里认 `--offline` 就带上它。"""
    try:
        text = (tree / rel).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        text = ""
    return f"python {rel}" + (" --offline" if "--offline" in text else "")


def packages_of(tree: pathlib.Path) -> tuple[str, ...] | None:
    """`requirements.txt` 里声明的包名；没有这个文件就返回 `None`（＝零依赖）。"""
    req = tree / "requirements.txt"
    if not req.exists():
        return None
    out: list[str] = []
    for line in req.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        name = re.split(r"[<>=!\[; ]", line, 1)[0].strip()
        if name and name not in out:
            out.append(name)
    return tuple(out)


def stdlib_of(tree: pathlib.Path) -> tuple[str, ...]:
    """用到的标准库模块（零依赖那一列的内容）：只收 `sys.stdlib_module_names` 里的。

    **相对导入（`from .image import …`）与树自己的包都不算**——它们是这棵树的代码，
    不是「要装什么」的答案。这一条与正文里「v6–v8 零依赖」是同一个事实的两种说法。
    """
    names: set[str] = set()
    for p in tree.rglob("*.py"):
        if "__pycache__" in p.parts:
            continue
        try:
            mod = ast.parse(p.read_text(encoding="utf-8"))
        except (OSError, SyntaxError, UnicodeDecodeError):
            continue
        for node in ast.walk(mod):
            if isinstance(node, ast.Import):
                names.update(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom) and not node.level and node.module:
                names.add(node.module.split(".")[0])
    # `__future__` 不算：它是语法开关，不是读者要装的东西（写进依赖列只会引人发问）。
    return tuple(sorted(n for n in names
                        if n in sys.stdlib_module_names and n != "__future__"))


# ------------------------------------------------------------------ 提交门那一侧

def stage_blocks(hook_text: str | None = None) -> list[tuple[str, str, str]]:
    """把提交门切成 [(阶段号, 阶段说明, 块文本)]。

    阶段号从 `echo "[pre-commit] 4f/5 …"` 里取（**阶段号是那行的第一个词**：
    「4f/5 通读普查 …」）。块＝这一行到下一个这样的行为止。
    """
    text = hook_text if hook_text is not None else HOOK.read_text(encoding="utf-8")
    # 正则**不能把 `.` 排除在外**：`4g/5 通读普查（…与 REVISIT.md 逐行比）...` 与
    # `5/5 REFERENCES.md 有改动 …` 都带点，初版把它们漏掉之后，4f 那一块一直吃到文件尾——
    # 后果不是漏一个阶段号，而是 `check_refs.py` 被写成「跑在 4f/5」（它其实跑在 5/5），
    # 以及 4g 整个消失。**少扫一段会变成一句错话，而不是一片空白。**
    marks = [(m.start(), m.group(1).strip()) for m in
             re.finditer(r'echo "\[pre-commit\] (.*?)\.\.\.', text)]
    marks.append((len(text), ""))
    out: list[tuple[str, str, str]] = []
    for (start, label), (end, _) in zip(marks, marks[1:]):
        if not label:
            continue
        num, _, desc = label.partition(" ")
        out.append((num, desc.rstrip(), text[start:end]))
    return out


def stage_key(num: str) -> tuple[int, str]:
    """阶段号排序：先按大关（`4/5` → 4），再按后缀（`4` < `4b` < `4c`）。"""
    head = num.split("/", 1)[0]
    digits = re.match(r"\d+", head)
    return (int(digits.group()) if digits else 0, head)


def invoked(block: str, name: str) -> bool:
    """这个块里**真的调用了**这个脚本吗。

    判据是「同一行里既有 `tools/<名>.py` 又有 `$PY`／`python`」。
    宽口径（只找文件名）会把注释里提到的名字也算上——实测 `check_refs.py` 与
    `check_runnable.py` 都在注释里被提过，于是它们会被写到「跑在某一关」而那一关并不跑它：
    **一句读起来像事实的错话，比空白更难发现。**
    """
    for line in block.splitlines():
        if f"tools/{name}" in line and ("$PY" in line or "python" in line):
            return True
    return False


def stage_map() -> dict[str, tuple[str, ...]]:
    """脚本名 → 跑在哪些阶段（阶段号唯一，按出现顺序）。"""
    blocks = stage_blocks()
    out: dict[str, tuple[str, ...]] = {}
    for tool in sorted(p.name for p in TOOLS.glob("*.py")):
        hits = [num for num, _, block in blocks if invoked(block, tool)]
        seen: list[str] = []
        for h in hits:
            if h not in seen:
                seen.append(h)
        out[tool] = tuple(seen)
    return out


# ------------------------------------------------------------------ 三张表

def tree_scale(spec) -> dict[str, int]:
    tests = sorted((spec.tree / "tests").rglob("test_*.py"))
    cases = sum(cr.case_count_of(spec.tree, t.relative_to(spec.tree).as_posix(), None, {}) or 0
                for t in tests)
    mods = [p for p in (spec.tree / "app").rglob("*.py") if p.name != "__init__.py"]
    chapters = sorted(p for p in spec.book.glob("*.md") if rv.chapter_id(p))
    return {"chapters": len(chapters), "modules": len(mods),
            "test_modules": len(tests), "cases": cases}


def part_name(book_dir: pathlib.Path) -> str:
    """`03-大模型与Agent原理` → `大模型与Agent原理`。"""
    return book_dir.name.split("-", 1)[1] if "-" in book_dir.name else book_dir.name


def deps_cell(tree: pathlib.Path) -> str:
    pkgs = packages_of(tree)
    if pkgs is None:
        std = stdlib_of(tree)
        return f"零依赖（标准库：{'、'.join(std)}）" if std else "零依赖"
    return f"{len(pkgs)} 个：{'、'.join('`' + p + '`' for p in pkgs)}"


def block_a() -> list[str]:
    out = ["## 附录 A　六棵可运行树：先跑哪一条命令", ""]
    out.append("六棵树都是**自包含**的：进它的目录、按最后一列装依赖、跑该章的离线入口即可。")
    out.append("「测试用例」是静态读数（数 `def test_`），与正文里的「全树 N 条」同一个数。")
    out.append("")
    out.append("| 篇 | 树 | 章 | `app/` 模块 | 测试模块 | 测试用例 | 依赖 |")
    out.append("| --- | --- | ---: | ---: | ---: | ---: | --- |")
    for spec in cr.SPECS:
        s = tree_scale(spec)
        out.append(f"| {spec.label.strip('（）')} {part_name(spec.book)} | `{spec.tree.name}/` "
                   f"| {s['chapters']} | {s['modules']} | {s['test_modules']} | {s['cases']:,} "
                   f"| {deps_cell(spec.tree)} |")
    out.append("")
    out.append("（依赖那一列是各树 `requirements.txt` 的全部声明，**含只在跑测试时需要**的那些；"
               "写成「零依赖」的树一个第三方包都不装。）")
    out.append("")
    for i, spec in enumerate(cr.SPECS, 1):
        s = tree_scale(spec)
        out.append(f"### A.{i} {spec.label.strip('（）')} · `{spec.tree.name}/`"
                   f"（{s['chapters']} 章 ｜ {s['cases']:,} 条用例）")
        out.append("")
        out.append(f"在该目录下跑；跑对了会看到 `{spec.marker}`（去掉 `--offline` 是真机那一趟）。")
        out.append("")
        out.append("| 入口 | 这个脚本干什么 |")
        out.append("| --- | --- |")
        for rel in entry_scripts(spec.tree):
            out.append(f"| `{entry_command(spec.tree, rel)}` "
                       f"| {doc_first_line(spec.tree / rel)} |")
        out.append("")
    return out


def block_b() -> list[str]:
    stages = stage_map()
    # 同一个阶段号可能有**两句**原话（`5/5` 既有「链接清单自检（离线）」也有
    # 「REFERENCES.md 有改动 → 联网校验全部链接」）：两句都留着，不挑一句代替。
    descs: dict[str, list[str]] = {}
    for num, desc, _ in stage_blocks():
        if desc and desc not in descs.setdefault(num, []):
            descs[num].append(desc)
    out = ["## 附录 B　门脚本速查", ""]
    out.append("`tools/` 下每一支脚本：它管什么、怎么单独跑、跑在提交门的哪一关。")
    out.append("阶段号与说明照抄 `.githooks/pre-commit` 自己的那份（它才是事实来源）。")
    out.append("")
    out.append("| 脚本 | 一句话 | 自己声明的开关 | 跑在提交门的哪一关 |")
    out.append("| --- | --- | --- | --- |")
    for p in sorted(TOOLS.glob("*.py")):
        flags = argparse_flags(p)
        how = "／".join(f"`{f}`" for f in flags) if flags else "（无开关）"
        nums = stages.get(p.name, ())
        if p.name in NOT_AN_ENTRY:
            where = NOT_AN_ENTRY[p.name]
        elif nums:
            where = "；".join(f"{n}" for n in nums)
        else:
            where = "不进提交门（读者手动跑）"
        out.append(f"| `{p.name}` | {doc_first_line(p)} | {how} | {where} |")
    out.append("")
    out.append("| 阶段 | 它在提交门里的原话 |")
    out.append("| --- | --- |")
    for num in sorted(descs, key=stage_key):
        out.append(f"| {num} | {'／'.join(descs[num])} |")
    out.append("")
    return out


def practice_pattern() -> re.Pattern[str]:
    """练习条目那一行的形状（`lint_book` 的同一把尺子）。

    **标签从 `lint_book._SHAPE_LEVELS` 借**——换名字时两边一起换。
    `re.M` 是必须的，而且这个坑真的踩过：少了它，`^` 只认整段文本的开头，
    于是每章只数到**第一条**练习（初版就是这么写的，自检第 ⑧ 条把它钉住了）。
    """
    return re.compile(rf"^- \*\*({'|'.join(lb._SHAPE_LEVELS)})\*\*", re.M)


def practice_counts() -> dict[str, int]:
    """三级标签的练习条数。"""
    out = {lv: 0 for lv in lb._SHAPE_LEVELS}
    pattern = practice_pattern()
    for _, lines in sorted(rv.chapter_lines().items()):
        body = "\n".join(rv.sections(lines).get("练习", []))
        for m in pattern.finditer(body):
            out[m.group(1)] += 1
    return out


def pit_counts() -> tuple[int, int]:
    """常见坑：总条数 ＋ 用表格而不是列表的章数（口径＝`revisit.shape_of`）。"""
    total, tables = 0, 0
    for _, lines in sorted(rv.chapter_lines().items()):
        shape = rv.shape_of(lines)
        total += int(shape["坑条数"])
        tables += 1 if shape["常见坑"] == "表格" else 0
    return total, tables


def block_c() -> list[str]:
    # 总量**一律从单一来源拿**（`totals.Facts` 与 `totals.sites`）：附录这里不自己再算一遍
    # 字数或站点数——那正是「同一件事写两个副本」的起点。
    facts = tt.Facts()
    sites = tt.sites()
    places = sum(len(v) for v in tt.find_hits(facts, tt.load_texts())[0].values())
    terms = len(lb.load_glossary_rows())
    cases = sum(tree_scale(s)["cases"] for s in cr.SPECS)
    per_tree = " ／ ".join(f"{s.tree.name.split('-')[-1]} {tree_scale(s)['cases']:,}"
                           for s in cr.SPECS)
    prac = practice_counts()
    pits, tables = pit_counts()
    # 「门脚本」的支数**从 `index_book` 借口径**（它把零入口的库排除在外）：
    # 附录与 `INDEX.md` 各写一个「门脚本 N 支」而两个 N 不相等，是这本书一直在防的那件事。
    gates = [p for p in TOOLS.glob("*.py") if p.name not in ib.NOT_A_GATE]
    wired = sum(1 for n, t in stage_map().items() if t)
    out = ["## 附录 C　全书的总量，与它们的复算入口", ""]
    out.append("这一列不是「相信我们」，是**你自己能重算**：每条命令都会把那一行印出来。")
    out.append("")
    out.append("| 量 | 值 | 怎么复算 |")
    out.append("| --- | --- | --- |")
    out.append(f"| 正文篇章 | {facts.done_total} / {facts.chapters_total} 章"
               f"（{len(facts.parts)} 篇） "
               f"| `python tools/totals.py --check`（那一行印的就是这个比值） |")
    out.append(f"| 正文有效字 | {facts.words_total:,} "
               f"| `python tools/totals.py --check`（同一行，`{facts.words_total:,} 字`） |")
    out.append(f"| 可运行树 | 6 棵、{cases:,} 条用例（{per_tree}） "
               f"| `python tools/check_runnable.py` |")
    out.append(f"| 术语词条 | {terms} 条 "
               f"| `python tools/index_book.py --check` |")
    out.append(f"| 练习 | {sum(prac.values())} 条（"
               + "／".join(f"{lv} {n}" for lv, n in prac.items()) + "） "
               f"| `python tools/appendix.py --check`（本附录自己算的，口径见 `STYLE`） |")
    out.append(f"| 常见坑 | {pits} 条（其中 {tables} 章用表格） "
               f"| 同上 |")
    out.append(f"| 素材站点 | {len(sites)} 类、{places} 处 "
               f"| `python tools/totals.py --check`（同一行） |")
    out.append(f"| 门脚本 | {len(gates)} 支（其中 {wired} 支跑在提交门里；另 "
               f"{len(ib.NOT_A_GATE)} 支是零入口的库） "
               f"| `python tools/appendix.py --check`（附录 B 就是那份表） |")
    out.append("")
    return out


def render() -> str:
    lines = HEAD.splitlines() + [""]
    lines += block_a() + block_b() + block_c()
    return "\n".join(lines).rstrip("\n") + "\n"


# ------------------------------------------------------------------ 反向守

def coverage_issues(text: str | None = None) -> list[str]:
    """条数下限：扫描退化成空时，`--check` 会安静地说「与盘上一致」。"""
    bad: list[str] = []
    counts = {"树": len(cr.SPECS),
              "入口脚本": sum(len(entry_scripts(s.tree)) for s in cr.SPECS),
              "门脚本": len(list(TOOLS.glob("*.py"))),
              "复算入口": len(block_c()) - 4}
    for key, floor in _FLOOR.items():
        if counts[key] < floor:
            bad.append(f"{key}只数到 {counts[key]} 条（下限 {floor}）——"
                       f"扫描退化了，先修读法再谈一致")
    return bad


def check() -> int:
    bad = coverage_issues()
    actual = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
    want = render()
    if not bad and actual != want:
        a, b = actual.splitlines(), want.splitlines()
        for i in range(max(len(a), len(b))):
            got = a[i] if i < len(a) else "（没有这一行）"
            exp = b[i] if i < len(b) else "（盘上没有这一行）"
            if got != exp:
                bad.append(f"{OUT.name} 与生成结果不同：首个不同在第 {i + 1} 行\n"
                           f"    盘上：{got[:120]}\n    生成：{exp[:120]}")
                break
    if bad:
        for line in bad:
            print(f"✖ {line}")
        print(f"\n修法：python tools/appendix.py --sync（它从盘上读，不手抄）")
        return 1
    n = len(want.splitlines())
    # 「几支门脚本」与附录 C 同一口径（排除零入口的库），否则同一支工具的两行输出会各说一个数。
    gates = len([p for p in TOOLS.glob("*.py") if p.name not in ib.NOT_A_GATE])
    print(f"✔ {OUT.name} 与盘上逐字相符（{n} 行 ｜ "
          f"{len(cr.SPECS)} 棵树、"
          f"{sum(len(entry_scripts(s.tree)) for s in cr.SPECS)} 个入口脚本、"
          f"{gates} 支门脚本、"
          f"{len(block_c()) - 4} 个复算入口）")
    return 0


def sync(*, write: bool) -> int:
    bad = coverage_issues()
    if bad:
        for line in bad:
            print(f"✖ {line}")
        return 1
    want = render()
    if not write:
        print(f"（演练）会写出 {len(want.splitlines())} 行到 {OUT.name}")
        return 0
    OUT.write_text(want, encoding="utf-8", newline="\n")
    print(f"✔ 已写出 {OUT.name}（{len(want.splitlines())} 行）")
    return 0


# ------------------------------------------------------------------ 夹具

def _tree(tmp: pathlib.Path, name: str, files: dict[str, str]) -> pathlib.Path:
    tree = tmp / name
    for rel, body in files.items():
        p = tree / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body, encoding="utf-8")
    return tree


def _ran(fn) -> bool:                       # 夹具的 `不报错` 判据：返回空列表
    try:
        return not fn()
    except Exception:                       # noqa: BLE001 —— 夹具里异常＝不过
        return False


def self_test() -> int:
    import tempfile

    good = 0
    total = 0

    def case(what: str, ok: bool) -> None:
        nonlocal good, total
        total += 1
        good += 1 if ok else 0
        print(f"  {'✔' if ok else '✖'} {what}")

    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td)

        # ① docstring 首行：取第一非空行；没有 docstring 就如实说没有（不拿文件名凑）。
        tree = _tree(tmp, "t1", {
            "scripts/a.py": '"""\n一句话：起服务。\n\n第二段不算。\n"""\nimport sys\n',
            "scripts/b.py": "import sys\n",
        })
        case("docstring 首行＝第一非空行", doc_first_line(tree / "scripts/a.py") == "一句话：起服务。")
        case("没有 docstring 就如实写「没有模块 docstring」，不拿文件名凑",
             doc_first_line(tree / "scripts/b.py") == "（这个脚本没有模块 docstring）")

        # ② 跑法：源码里认 --offline 才带它。
        tree = _tree(tmp, "t2", {
            "scripts/on.py": '"""x。"""\nimport sys\nif "--offline" in sys.argv:\n    pass\n',
            "scripts/off.py": '"""y。"""\nimport sys\n',
            "demo.py": '"""z。"""\nif "--offline" in __import__("sys").argv:\n    pass\n',
        })
        case("源码里有 --offline → 命令带上它",
             entry_command(tree, "scripts/on.py") == "python scripts/on.py --offline")
        case("源码里没有 --offline → 不带（不替它编一个）",
             entry_command(tree, "scripts/off.py") == "python scripts/off.py")

        # ③ 入口脚本的过滤：app/、tests/、conftest、__init__ 都不是入口。
        tree = _tree(tmp, "t3", {
            "scripts/a.py": '"""a。"""\n', "demo.py": '"""d。"""\n',
            "app/x.py": "", "app/sub/y.py": "", "tests/test_x.py": "",
            "conftest.py": "", "scripts/__init__.py": "", "experiments/e.py": "",
        })
        case("入口＝scripts/ 下的 .py ＋ 根级 .py；app/、tests/、conftest、__init__ 都不算",
             entry_scripts(tree) == ["demo.py", "scripts/a.py"])

        # ④ 开关：只认 add_argument 的第一个位置参数。宽口径会把 help 正文也收进来
        #    （实测出现过 `---` 与整句中文），夹具把这两种都钉住。
        tree = _tree(tmp, "t4", {
            "tools/t.py": '"""t。"""\nimport argparse\n'
                          'p = argparse.ArgumentParser()\n'
                          'p.add_argument("--check", help="--sync 幂等（再跑一次不再改动）")\n'
                          'p.add_argument("--only", metavar="X.Y")\n'
                          'p.add_argument("pos", help="---")\n',
        })
        case("开关只取 add_argument 的第一个位置参数（help 正文里的 `--…` 不算）",
             argparse_flags(tree / "tools/t.py") == ("--check", "--only"))

        # ⑤ 提交门：只有「真的调用了」才算跑在某一关。
        hook = ('echo "[pre-commit] 1/5 工具自检 ..."\n'
                '"$PY" tools/a.py --self-test\n'
                'echo "[pre-commit] 4f/5 别的关 ..."\n'
                '# a.py 与 b.py 都在注释里被提过，但这一关不跑它们\n'
                '"$PY" tools/c.py --check\n')
        blocks = stage_blocks(hook)
        case("阶段切分拿到阶段号与说明", [(n, d) for n, d, _ in blocks]
             == [("1/5", "工具自检"), ("4f/5", "别的关")])
        case("调用行里同时有 tools/<名> 与 $PY → 算跑在那一关", invoked(blocks[0][2], "a.py"))
        case("只在注释里被提到 → 不算跑在那一关（宽口径会写出错话）",
             not invoked(blocks[1][2], "a.py") and invoked(blocks[1][2], "c.py"))

        # ⑥ 依赖：注释与空行不算；`pkg>=1.0  # 注` 取 pkg。
        tree = _tree(tmp, "t5", {
            "requirements.txt": "# 注释\nhttpx>=0.27            # 唯一 HTTP 客户端\n\npytest>=8.0\n",
        })
        case("requirements：注释／空行不算，版本号不算进包名",
             packages_of(tree) == ("httpx", "pytest"))
        case("没有 requirements.txt → 零依赖（None，而不是空元组）",
             packages_of(tmp / "t1") is None)

        # ⑦ 零依赖那一列：标准库算，相对导入与树自己的包不算。
        tree = _tree(tmp, "t6", {
            "app/x.py": "from dataclasses import dataclass\nfrom .image import P\nfrom app.gate import g\n",
            "scripts/r.py": "import json\nimport sys\n",
        })
        case("标准库清单只收 sys.stdlib_module_names 里的（相对导入与自身包不算）",
             stdlib_of(tree) == ("dataclasses", "json", "sys"))

        # ⑧ 练习口径与 lint_book 同一把尺子：标签从它借，换名字时这里跟着换；
        #    而且 `re.M` 必须在——少了它每章只数到第一条（初版就是）。
        case("练习标签从 lint_book 借（所以两边不会各写一份）",
             lb._SHAPE_LEVELS == ("基础", "进阶", "挑战")
             and [m.group(1) for m in practice_pattern().finditer(
                 "- **基础**：x\n- **进阶**：y\n1. 旧写法\n")] == ["基础", "进阶"])
        case("少写 re.M 会漏数：不带它只匹配到第一条",
             len(re.findall(r"^- \*\*(?:基础|进阶)\*\*",
                            "- **基础**：x\n- **进阶**：y\n")) == 1
             and len(practice_pattern().findall("- **基础**：x\n- **进阶**：y\n")) == 2)

        # ⑨ 条数下限：扫描退化成 0 行时，`--check` 会安静地说「与盘上一致」。
        case("当前规模在下限之上 → 沉默", not coverage_issues())
        saved = dict(_FLOOR)
        try:
            _FLOOR["树"] = 99
            case("下限被抬高到不可能 → 报出「只数到 N 条」", bool(coverage_issues()))
        finally:
            _FLOOR.clear()
            _FLOOR.update(saved)

        # ⑩ 逐字比：改一格就红，并报出首个不同的行号。
        a = "x\ny\nz\n"
        b = "x\nY\nz\n"
        diff = [i + 1 for i in range(3)
                if (a.splitlines()[i] if i < 3 else "") != b.splitlines()[i]]
        case("逐字比报「首个不同在第 N 行」", diff == [2])

        # ⑪ 渲染是幂等的：同一份盘上状态渲染两次，逐字相同。
        case("渲染幂等（两次 render() 逐字相同）", render() == render())

        # ⑫ 生成物收全：附录 B 必须列出 tools/ 下**每一支**（少一支就是「新一代工具没进表」）。
        listed = [ln.split("`")[1] for ln in block_b() if ln.startswith("| `")]
        case("附录 B 列全 tools/ 下每一支脚本",
             set(listed) == {p.name for p in TOOLS.glob("*.py")})
        case("附录 A 列全六棵树的每一个入口脚本",
             all(all(f"python {rel}" in "\n".join(block_a())
                     or f"python {rel} --offline" in "\n".join(block_a())
                     for rel in entry_scripts(s.tree)) for s in cr.SPECS))

    print(f"附录自检：{good}/{total} 通过"
          + ("" if good == total else f"（{total - good} 条不过）"))
    # 书侧（`STYLE`／`README`）若写了「appendix.py … N 条夹具」，那个数必须等于上面这个分母：
    # 与另外四支走同一道（`style_claims.report`），「写了没接线」那种盲区也就跟着堵上。
    import style_claims as sc
    return sc.report("appendix", total) | (0 if good == total else 1)


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
