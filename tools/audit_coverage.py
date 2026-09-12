#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
素材覆盖度审计：逐章核算"可用素材汉字量"与"计划篇幅"的关系，用于校准 PLAN.md。

为什么需要这个脚本
------------------
PLAN.md 初版的篇幅估算是按"素材页数"拍的，而页数会骗人：

  - LangChain 素材 23 页，听着够写一章，实际全篇只有约 2,200 个汉字（其余是乱序代码），
    撑不起计划中的 7,000 字。
  - Python 手册的"进阶部分"没有编号标题，按关键词检索会误判成"没素材"，
    实际藏着 3.0 万字的异常/装饰器/OOP/网络/并发内容。

所以审计按**汉字量**计量，并把素材分成两类，绝不混算：

  散文素材：可直接改写为教材正文（Python 手册、FastAPI 讲义、RAG 教程……）
  题库素材：问答格式，只能提供考点清单与问法，答案必须重写，且质量差异极大

判定口径
--------
教材正文不是素材的压缩：一章 6,000 字，需要 1.2 倍以上的散文素材才算充裕，
因为要重写表述、补例子、加练习。

    散文比值 = 散文素材汉字 / 计划汉字
    ≥1.20 充裕 | 0.80–1.20 够用 | 0.45–0.80 偏薄 | <0.45 严重不足 | 无素材

题库驱动型章节（第 6 篇）不做散文比值判定，改看题库是否足量、是否可信。

篇级不用"各章相加"——同一段素材会被多章共用，相加必然虚高。
改为统计该篇真正能调用的**素材池**（按素材段落去重）。

用法
----
    python tools/audit_coverage.py            # 覆盖度报表
    python tools/audit_coverage.py --md       # markdown 表格，便于贴进 PLAN.md
    python tools/audit_coverage.py --pool     # 打印素材池明细，核对分段是否合理
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "sources"
HAN = re.compile(r"[\u4e00-\u9fff]")
FA_DIR = SRC / "01-编程地基" / "FastAPI基础学习"
PY_MANUAL = SRC / "01-编程地基" / "Python核心语法手册.md"

PROSE_KINDS = {"file", "py", "pys", "fa", "proj"}

# 参考项目里**有意不采用**的讲解文档（前缀匹配，相对项目目录）。
# 白名单必须带理由——没有理由的白名单与「静默跳过」没有区别。
PROJ_UNUSED: dict[str, str] = {
    "fastapi_project/项目讲解/前端讲解/":
        "第 1 篇是后端工程；前端形态属第 8 篇（SSE 与流式 UI），素材形态不同",
}

# 解析素材规格时发现的问题（如选择器写错、指向不存在的子文件）。
# 这些错误以前是**静默跳过**的：选择器没匹配上就 continue，结果两篇素材既没进
# 素材池、也没进分配检查，总量少了一截而报表照常漂亮。收集起来一并报出。
_WARNINGS: list[str] = []
BANK_KINDS = {"bank"}


def han(text: str) -> int:
    return len(HAN.findall(text))


def strip_header(text: str) -> str:
    """去掉 extract_sources.py 生成的溯源头部，只留素材正文。

    头部是我们自己写进去的元信息（约 96 个汉字），把它算进素材量会让
    LangChain 这种小文件虚胖 4%，所以计量前先剥掉。
    识别方式：文件开头是 `# 标题` 且前 600 字内出现 `**素材来源**`，
    则截到其后第一条 `---` 分隔线的下一行为止。
    """
    if not text.startswith("# "):
        return text
    head = text[:600]
    if "**素材来源**" not in head:
        return text
    pos = text.find("\n---\n")
    return text[pos + 5:] if pos != -1 else text


# --------------------------------------------------------------- 素材读取
_fc: dict[str, int] = {}


def file_han(rel: str) -> int:
    """素材**正文**的汉字量（已剥除生成的溯源头部）。"""
    if rel not in _fc:
        p = SRC / rel
        if not p.exists():
            raise FileNotFoundError(f"素材不存在：{rel}")
        _fc[rel] = han(strip_header(p.read_text("utf-8", errors="ignore")))
    return _fc[rel]


# Python 手册进阶块的主题分段：每段用"起锚点正则"定位，最后一段取余下全部。
# 锚点是内容里的稳定标记，不写死行号，素材重新生成后依然有效。
PY_SEGMENTS: list[tuple[str, str | None, str]] = [
    ("base",     None,               "JSON/异常/日志/时间/格式化等基础扩展"),
    ("contain",  r"^list\.append\(", "内置方法与容器操作"),
    ("func",     r"^3，函数参数详解",  "函数参数、装饰器、模块"),
    ("oop",      r"^2\.1 私有属性",    "面向对象进阶（私有属性/继承/多态）"),
    ("net",      r"^## 五层协议",      "网络编程（TCP/IP 五层协议）"),
    ("concur",   r"^11\.1 操作系统发展史", "并发编程（进程/线程/池）"),
    ("gen",      r"^g = func1\(\)",   "生成器与异步 IO"),
]

_pc: dict[int, str] | None = None
_ps: dict[str, str] | None = None


def py_manual() -> tuple[dict[int, str], dict[str, str]]:
    """返回 (编号章块, 进阶块主题分段)。

    手册的 25-数据类型转换 之后并未结束，还续写了 JSON/异常/日志/装饰器/模块/
    OOP 进阶/网络编程/并发编程 等内容。它们既没有编号标题，也不是新的一章，
    实测约 3.0 万字（占手册 55%），是全书最有价值的部分之一。

    末章边界不是拍脑袋定的：末章最后一节是 `25.8`，其后第一个 `## ` 二级标题
    即进阶块起点。硬编码行号会随素材重新生成而失效，因此用规则定位。
    """
    global _pc, _ps
    if _pc is not None and _ps is not None:
        return _pc, _ps

    lines = strip_header(PY_MANUAL.read_text("utf-8", errors="ignore")).split("\n")
    marks: list[tuple[int, int]] = []
    for i, ln in enumerate(lines):
        m = re.match(r"^(\d+)- (.+)$", ln)
        if m and int(m.group(1)) <= 25:
            marks.append((i, int(m.group(1))))
    marks.sort()
    if not marks:
        _pc, _ps = {}, {}
        return _pc, _ps

    last_num, last_start = marks[-1][1], marks[-1][0]
    subs = [i for i in range(last_start, len(lines))
            if re.match(rf"^{last_num}\.\d", lines[i])]
    tail = subs[-1] if subs else last_start
    heads = [i for i in range(tail, len(lines)) if lines[i].startswith("## ")]
    boundary = heads[0] if heads else len(lines)

    blocks: dict[int, str] = {}
    for k, (i, num) in enumerate(marks[:-1]):
        blocks[num] = "\n".join(lines[i:marks[k + 1][0]])
    blocks[last_num] = "\n".join(lines[last_start:boundary])

    # 进阶块分段
    starts: list[int] = [boundary]
    for _name, pat, _desc in PY_SEGMENTS[1:]:
        hit = next((i for i in range(boundary, len(lines))
                    if re.search(pat, lines[i])), None)
        if hit is None:  # 锚点丢失则退化为整块，避免静默算错
            print(f"警告：进阶块锚点未命中 {pat}，该段并入上一段", file=sys.stderr)
            starts.append(len(lines))
        else:
            starts.append(hit)
    for k, (name, _p, _d) in enumerate(PY_SEGMENTS):
        end = starts[k + 1] if k + 1 < len(starts) else len(lines)
        seg = lines[starts[k]:end]
        _ps = _ps or {}
        _ps[name] = "\n".join(seg)

    _pc = blocks
    return _pc, _ps


def py(sel: str) -> int:
    """按章号选择 Python 手册编号章，如 '1-7,25'。"""
    blocks, _ = py_manual()
    total = 0
    for part in sel.split(","):
        part = part.strip()
        if "-" in part:
            a, b = (int(x) for x in part.split("-"))
            total += sum(han(v) for k, v in blocks.items() if a <= k <= b)
        elif part:
            total += han(blocks.get(int(part), ""))
    return total


def pys(names: str) -> int:
    """按主题段选择 Python 手册进阶块，如 'base,contain'。"""
    _, segs = py_manual()
    return sum(han(segs.get(n.strip(), "")) for n in names.split(",") if n.strip())


_fc_dirs: dict[str, str] | None = None


def fa_dirs() -> dict[str, str]:
    """FastAPI 讲义的 章号前缀 -> 目录名。"""
    global _fc_dirs
    if _fc_dirs is None:
        _fc_dirs = {}
        for d in FA_DIR.iterdir():
            if d.is_dir():
                m = re.match(r"^(\d{2})", d.name)
                if m:
                    _fc_dirs[m.group(1)] = d.name
    return _fc_dirs


def fa_files(n: str, sub: str = "") -> list[Path]:
    """取某个讲义章（目录）下的 .md 文件；sub 非空时只取其中第 1 起编号的若干篇。

    为什么需要子文件级选择：`02` 目录的 8 篇横跨三章内容（应用配置 / 生命周期 /
    中间件与依赖注入 / 生产实践），整目录记到某一章，就会把别的章的素材算进来，
    让该章看起来比实际充裕。用 `02/01-05` 这种写法只取其中一段。
    """
    name = fa_dirs().get(n)
    if not name:
        return []
    files = sorted((FA_DIR / name).rglob("*.md"))
    if not sub:
        return files
    idx = _num_range(sub)
    return [f for i, f in enumerate(files, 1) if i in idx]


def _fa_expand(sel: str) -> list[str]:
    """展开 '02-13' 为 ['02',...,'13']；必须补零，否则匹配不上目录名前缀。"""
    out: list[str] = []
    for part in sel.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = (int(x) for x in part.split("-"))
            out.extend(f"{n:02d}" for n in range(a, b + 1))
        else:
            out.append(part.zfill(2))
    return out


def resolve(spec) -> dict[str, int]:
    """把一条素材规格解析为 {去重键: 汉字量}（未乘相关系数）。"""
    kind, sel, _ratio = spec
    if kind == "file":
        return {f"file:{sel}": file_han(sel)}
    if kind == "py":
        return {f"py:{n}": han(v) for n, v in py_manual()[0].items()
                if n in _num_range(sel)}
    if kind == "pys":
        segs = py_manual()[1]
        return {f"pys:{n.strip()}": han(segs.get(n.strip(), ""))
                for n in sel.split(",") if n.strip()}
    if kind == "fa":
        out = {}
        for part in sel.split(","):
            part = part.strip()
            if not part:
                continue
            sub = ""
            if "/" in part:
                part, sub = part.split("/", 1)
            hit = False
            for n in _fa_expand(part):
                files = fa_files(n, sub)
                if not files:
                    continue
                hit = True
                key = f"fa:{n}" if not sub else f"fa:{n}/{sub}"
                out[key] = sum(file_han(f.relative_to(SRC).as_posix())
                               for f in files)
            # 静默跳过是这里最危险的失败方式：`20/01-05,07,10` 会被顶层逗号切开，
            # 后两项解析不出任何文件，于是两篇素材**看起来被分配了、其实没有**，
            # 而且素材总量也少了——错得很安静。子文件列表改用 `+` 分隔后，
            # 任何解析不出文件的片段都显式报出来。
            if not hit:
                _WARNINGS.append(f"素材选择器无匹配：{kind} {sel}（片段 {part!r}）")
        return out
    if kind == "proj":
        # 一个项目目录里有三块内容：后端讲解、前端讲解、源码注释。整目录计入会把
        # 前端讲解（3,597 汉字）算给「后端 API」那一章——与 1.9 「一个目录装了三个章
        # 的素材」是同一个错误，所以支持按路径过滤：
        #   ("proj", "项目讲解/后端讲解", 1.0)    只要后端讲解那 7 篇
        # 子选择器用 `+` 分隔（逗号是顶层素材规格的分隔符）。
        out: dict[str, int] = {}
        # 注意：这里**不能**对空片断 `continue`。空选择器（`sel=""`）就是「整目录」，
        # 写成空片断列表后 `all(... for s in [])` 恒为真，天然匹配全部文件；
        # 若在此处跳过，整目录引用会静默变成 0 汉字（比「未分配」更难发现）。
        for part in sel.split("+"):
            segs = [s for s in part.strip().split("/") if s]
            hit = False
            for d in sorted(FA_DIR.iterdir()):
                if not (d.is_dir() and d.name in ("fastapi_project", "fastapi_best_practice")):
                    continue
                for f in d.rglob("*.md"):
                    rel = f.relative_to(d).as_posix()
                    if not all(s in rel for s in segs):
                        continue
                    hit = True
                    key = f"proj:{rel}" if segs else f"proj:{d.name}"
                    out[key] = out.get(key, 0) + file_han(f.relative_to(SRC).as_posix())
            if not hit:
                _WARNINGS.append(f"素材选择器无匹配：{kind} {sel}（片段 {part!r}）")
        return out
    if kind == "bank":
        return {f"bank:{sel}": file_han("06-求职冲刺/" + sel)}
    raise ValueError(f"未知素材类型：{kind}")


def _num_range(sel: str) -> set[int]:
    """解析子文件号：`01-05`、`07`，多项用 `+` 连（**不用逗号**——逗号是顶层
    素材规格的分隔符，`20/01-05,07` 会被切成两段，`07` 就丢了）。"""
    out: set[int] = set()
    for part in re.split(r"[,+]", sel):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = (int(x) for x in part.split("-"))
            out.update(range(a, b + 1))
        else:
            out.add(int(part))
    return out


# --------------------------------------------------------------- 章节计划
# (篇, 章号, 标题, 计划汉字, [素材规格], 备注)
#   素材规格 = (kind, selector, ratio)
#     ratio 表示该素材中真正相关、可改写的比例（保守估计）
PLAN = [
    # ---------------- 第 0 篇 导论
    ("0", "0.1", "岗位地图：AI 应用开发岗到底要什么", 4000, [], "完全原创"),
    ("0", "0.2", "能力模型与 180 天学习路线", 5000, [], "完全原创"),
    ("0", "0.3", "本教材使用说明与素材索引", 3000, [], "完全原创"),

    # ---------------- 第 1 篇 编程地基
    ("1", "1.1", "环境搭建：Python、依赖管理、IDE 与 Git", 4000,
     [("fa", "01", 1.0)], "素材仅 2.2k；venv/Git 须原创"),
    ("1", "1.2", "Python 语法速通：变量、类型、控制流", 6000,
     [("py", "1-7", 1.0), ("py", "12-17", 1.0), ("py", "25", 0.5),
      ("pys", "base", 0.20)],
     "含控制流（if/for/while）与循环练习"),
    ("1", "1.3", "常用数据结构与推导式", 6000,
     [("py", "8-11", 1.0), ("py", "21", 1.0), ("pys", "contain", 0.80)], ""),
    ("1", "1.4", "函数、装饰器与高阶用法", 6000,
     [("py", "18-20", 1.0), ("pys", "func", 0.90), ("pys", "gen", 0.50)], ""),
    # 1.5 计划值按实测校准：概念密度最高的章（类 / 继承 / MRO / 魔术方法 / 选型 / 综合示例），
    # 初版估 6,000 严重低估，实写 9,418（有效字数）。此处改为 9,000，而不是删掉素材覆盖的内容。
    ("1", "1.5", "面向对象：类、继承、魔术方法", 9000,
     [("py", "23-24", 1.0), ("pys", "oop", 0.90)], "魔术方法零素材，须原创"),
    # 1.6 同样按实测校准：异常 + 文件 + 模块化三块合在一章，初版估 5,000 偏低，
    # 实写 7,579（有效字数），改为 7,500。
    ("1", "1.6", "异常处理、文件操作与模块化", 7500,
     [("py", "22", 1.0), ("pys", "base", 0.55)], "异常/日志/模块在此段"),
    # 1.7 同样按实测校准：线程 + 进程 + 协程 + FastAPI 并发模型四块内容，
    # 初版估 6,000 偏低，实写 8,386（有效字数），改为 8,000。
    # 已完稿 8 章的经验：单一主题的章达成 80%–105%；概念密度高或一章装三块以上
    # 内容的章会超到 140%–157%（1.5/1.6/1.7），后续同类章应直接按 7,500–9,000 估。
    ("1", "1.7", "并发与异步：线程、进程与 asyncio", 8000,
     [("pys", "concur", 0.90), ("pys", "gen", 0.30), ("fa", "14", 1.0)],
     "asyncio 须补"),
    # 1.8 按已定稿 8 章的规律预先估：五层模型 + TCP/UDP + HTTP 报文/方法/状态码 +
    # HTTPS + CORS 属多块内容，直接估 8,000（避免事后反复校准）。
    # fa 04-05（路由 / 请求与响应）被 1.8 与 1.9 共用：1.8 只取其中的 HTTP 协议部分
    # （方法表、状态码、Cookie），1.9 取 FastAPI 用法。两边按 0.45 / 1.0 分记，
    # 否则同一份讲义会被完整计入两章，两章都显得比实际充裕。
    ("1", "1.8", "Web 与 HTTP 基础（面试必考）", 8000,
     [("pys", "net", 0.85), ("fa", "04-05", 0.45)],
     "网络编程段含 TCP/IP 五层协议；fa 04-05 与 1.9 共用，此处只记 HTTP 协议部分"),
    # 1.9 的经历值得记一笔：初稿把「统一响应格式」与「表单/文件上传」也塞了进来，
    # 十小节共写 22,341 有效字（达成 186%）——素材充裕不等于该堆在一章里。
    # 处理是把两摇内容归位（fa 10 → 1.14，fa 11-12 → 1.15；Cookie 写入 → 1.13），
    # 并删掉重复的平行示例（七种方法、六种响应类型各留一个代表 + 表格），
    # 实写 15,381。这里按实测校准为 15,000，而不是删掉已覆盖的内容。
    ("1", "1.9", "FastAPI 入门：路由、请求与响应", 15000,
     [("fa", "02/01-05,03-09", 1.0)],
     "素材最充裕；02 只取第 1-5 篇，03-09 为路由与四类参数"),
    # 1.10 的教训与 1.5/1.6/1.7 相反方向：那几章是「素材多、计划少」，这章是
    # 「素材几乎为零，但绝不是薄章」。素材只有 1,356 字（最薄），可 Pydantic v2
    # 的完整面貌（数据契约 → 模型定义 → Field → 常用类型 → ConfigDict → 校验器 →
    # 嵌套继承联合 → 别名序列化 → FastAPI 集成 → 综合示例）本身就是十节的量，
    # 实写 11,807（有效字数，达成按 6,000 算的 197%）。
    # 处理同 1.5：按实测校准为 11,500，而不是删掉已覆盖的内容。
    # 估法教训：字数按「小节数 × 800~1,100 + 代码折算」估，不按素材量估——
    # 零素材只说明要自己写，不说明写得少。
    ("1", "1.10", "数据校验：Pydantic 模型", 11500,
     [("fa", "15", 1.0)], "素材仅 1.4k（最薄），几乎全原创"),
    # 1.11 又踩了一次 1.9 的坑，只是方向相反：fa 20 是十篇中间件，整目录计入
    # 就等于把「认证 / 限流 / 日志 / 连接池」全塞进一章——而它们各自的主题
    # 在 1.13（认证）、1.14（日志）、1.12（连接池）里讲得更透。
    # 因此只留 01-05+07+10（中间件本体 + 内置中间件 + 限流），其余三篇归位。
    #
    # 篇幅再次估错，这次错在**漏算代码行项**：事前按「13 小节 × 约 1,000」估
    # 13,000，但本章 732 行代码 × 15 = 10,980，占了实测 20,589 的一半。
    # STYLE 8.7 的公式本就含这一项，是估算时只看小节数、没看代码密度。
    # 按实测校准为 20,500（而不是为了凑 13,000 删掉四个内置中间件）。
    ("1", "1.11", "依赖注入与中间件", 20500,
     [("fa", "16", 1.0), ("fa", "20/01-05+07+10", 1.0), ("fa", "02/07", 1.0)],
     "fa 20 只取 01-05+07+10；06/08/09 归位到 1.13/1.14/1.12；代码 732 行"),
    # 1.12 按 8.7 的公式**事前**估 13,000，实写 17,472（134%）——
    # 公式本身是有偏的：对代码密度高的章（本节 624 行代码）它会低估汉字量，
    # 因为代码块前后的解释性散文往往比估算里的 900 字/节多。
    # 仍按实测校准为 17,500，而不是靠 ±40% 的容差把它放过去。
    # 另：Redis 那一段在本机**无法实跑**（redis 3.5.3 没有 redis.asyncio，需 ≥4.2），
    # 正文已如实标注，比假装跑过诚实。
    ("1", "1.12", "数据库与缓存：SQLAlchemy + Redis", 17500,
     [("fa", "17-18", 1.0), ("fa", "20/09", 1.0)],
     "含连接池中间件（fa 20/09 归位于此，它讲的是会话生命周期）"),
    # 1.13 的两次估算都错了，错在不同地方，两次都记下来：
    #  ① 原计划 6,000 是「素材 6,876 × 0.9」倒推的，属于用素材量估篇幅——
    #     正是 8.7 明确禁止的做法。素材薄只说明要自己写，不说明写得少（同 1.10）。
    #  ② 改按公式事前估 17,000（14 小节 × 约 800 + 预估代码行），
    #     实写 20,649（汉字 11,949 + 代码 580 行）——**代码行又估少了**。
    #     这是 1.11（732 行）、1.12（624 行）之后第三次同因超标：
    #     带「综合示例」的章，代码实际都在 550–750 行（15 × 580 = 8,700，占实测 42%），
    #     而凭感觉估代码往往只给 400 行左右。已在 STYLE 8.7 记下这个先验区间。
    # 按实测校准为 20,500，与 1.11 同档。
    ("1", "1.13", "认证与授权：JWT、OAuth2 与权限设计", 20500,
     [("fa", "19", 1.0), ("fa", "13", 1.0), ("fa", "20/06", 1.0)],
     "含 Cookie 的写入、删除与会话安全属性；含 JWT 认证中间件（fa 20/06）"),
    # 1.14 接管了 fa 10（统一响应格式）、fa 20/08（日志中间件）；
    # 1.15 接管了 fa 11-12（表单与文件上传）。
    # 各章的计划篇幅随新增内容上调，而不是把新内容塞进原篇幅。
    # 1.14 是第 1 篇装得最多的一章：**六个主题**（统一响应格式、异常处理、日志、
    # 三层架构、单元测试、生命周期与生产实践），其中后两个是从 1.9 与 1.11 归位过来的。
    # 原计划 10,000 是按素材量定的（10,535 × 0.95），所以实际是「够用」档。
    # 按 8.7 的公式事前估：16 小节 × 800 = 12,800 + 代码（有综合示例，按 600 行起估）
    # 9,000 ≈ 21,800，取 21,500。素材比值降到 0.49（偏薄），这是实情：
    # 日志工程化、测试组织、统一响应格式的取舍都要按官方文档原创。
    # 实写 24,118（112%）——第四次低估，偏差仍在代码那头：813 行代码 × 15 = 12,195，
    # 略高于预估的 9,000，且实跑审阅后正文又长了一截（补了中间件异常边界的四组对照、
    # AsyncMock、脱敏深度上限等实测结论）。已按实测校准为 24,000，不留容差。
    ("1", "1.14", "三层架构、日志、异常与单元测试", 24000,
     [("fa", "21-25", 1.0), ("fa", "10", 1.0), ("fa", "02/06,02/08", 1.0),
      ("fa", "20/08", 1.0)],
     "含统一响应格式与异常处理器、生命周期与生产实践、日志中间件"),
    # 原计划 12,000 是按「素材 10,991 × 0.92」倒推的，但 10,991 里有 3,597 是
    # **前端讲解**（不属于本篇：第 1 篇是后端工程）。修正素材归属后，后端可用的散文
    # 只有 ~7,000，比值降到 0.35（严重不足）——这是实情：表设计、表单、上传、
    # 下载与断点续传、静态挂载、图片路径契约、评论树与楼层号都要按官方文档原创，
    # 但这些技术点**只在这一章讲**（fa 11-12 从 1.9 归位过来，1.9–1.14 都没覆盖）。
    # 按 8.7 公式事前估：14 小节 × 800 = 11,200 + 代码（表格/示例密集，按 675 行）
    # ≈ 10,125 → 21,325，取 21,000。
    ("1", "1.15", "项目实战：知舟博客 API 从零到一", 21000,
     [("proj", "项目讲解/后端讲解+backend/README", 1.0), ("fa", "11-12", 1.0)],
     "两个完整项目（只用后端角度）；含表单与文件上传；前端讲解归第 8 篇"),

    # ---------------- 第 2 篇 AI 时代的开发方式
    # 2.1 由 5,000 提到 8,000（事前重估，按 8.7 公式：9 小节 × 约 600 + 固定段约 2,000
    #      + 实跑演示约 80 行代码）。原值是按「素材充裕就少写」倒推的，但素材（6,180）
    #      只覆盖「思维模型」一条主线（Vibe Coding → Harness 的框架与五阶段）；
    #      「能力边界」与「风险」两节必须回到 OWASP LLM Top 10 / METR / DORA / CCS'23 /
    #      USENIX'25 原创。判定因此由「充裕」改为「偏薄」（6,180 / 8,000 = 0.77）。
    ("2", "2.1", "与 AI 协作编程：思维模型、能力边界与风险", 11000,
     [("file", "02-AI编程工具链/AI-Harness入门与实践.md", 0.7)], ""),
    #     权重按**章节实际用到的节**实测拆分，不再写「整份文件的百分比」：
    #     原来 2.2 记 0.9、2.5 又记 0.5，合计 1.4——同一份文件被算了两次，
    #     两章都显得比实际充裕。Codex 与 AI-Harness 同病（详见 weight_sum_lines）。
    #     拆分依据：2.2 用第 1–8、10–14、17–20 节（含开篇「15 件事」）＝ 12,436；
    #     2.5 用第 9 节与 16.3–16.5（规则文件 / MCP / Skills / Hooks）≈ 1,627；
    #     2.6 用第 15 节与 16.1–16.2（Actions / Subagents / 动态工作流）≈ 817。
    #     事前估按 8.7 公式：11 节 × 约 800 + 固定段约 2,200 + 约 150 行命令/模板 × 15
    #     ——这一章的「代码」不是算法而是**命令、工单模板与配置**，代码行项占比高，
    #     不能按纯叙述章估。原定 7,000 是「素材量 × 1.24」倒推的。
    #     事后校准（实写 20,805，事前估 11,000，达成 189%）：两项都估低了，且原因不同。
    #     ① 代码行项：事前估 150 行，实际 **324 行**——这一章的提示词模板/工单/配置
    #        每个都是 10–30 行，而它们是正文内容本身，不是附录；
    #     ② 散文项：事前估约 8,800 汉字，实际 15,945——多出来的主要是**素材没有的原创**：
    #        权限模式全集（素材只列了一半且说法过时）、沙箱的平台限制与两个开关、
    #        会话恢复的“不还原”清单，这三块只能回官方文档写。
    #     归因结论：不是“装了两章”（§9/§15/§16 已归 2.5/2.6），是估法对
    #     「模板密集章」失效——同一个错方向第 5 次出现（参见 STYLE 8.7）。
    ("2", "2.2", "Claude Code 实战：从对话到工程化", 21000,
     [("file", "02-AI编程工具链/Claude-Code从入门到实战.md", 0.84)], "实测 12,420 汉字"),
    #     Codex：2.3 用第 1–8、10–14、16–19 节 ＝ 10,325；
    #     2.5 用第 9 节与 15.4–15.6（AGENTS.md / MCP / Skills / Automations）≈ 1,633；
    #     2.6 用 15.1–15.3（Plan / Goal / Subagents）≈ 512。
    #     2.3 事后校准：13,000 → 16,500（写后按实测）。事前估 13,000、实写 16,856（130%）。
    #     归因：不是「装了两章」（归位已完成），而是两项低估——
    #     ① 固定段的规模：决策表、对照表、五步综合示例各占一节，不是附录；
    #     ② 实跑带出的新内容：git apply 与 --3way 的原子性差别、索引被改写、
    #        两种恢复来源的差别，这一整块照文档写不出来，只能先跑再写。
    #     2.3 事前重估：6,000 → 13,000（写作前改，按 8.7 式子）。
    #     原来那个 6,000 是「素材 10,325 汉字 × 比例」推出来的，方向错了——
    #     素材量不决定篇幅。按式子：11 小节（9 长 × 900 + 2 短 × 450 ≈ 9,000）
    #     + 约 205 行配置/命令/校验脚本 × 15 ≈ 3,075 + 固定段约 1,200 ≈ 13,275，
    #     取 13,000。注意这一章的代码行以**配置片段**为主（config.toml、
    #     `codex exec` 家族、JSONL 事件），按 8.7「模板密集章」的提醒逐个数。
    ("2", "2.3", "Codex 实战：云端与本地的工作流", 16500,
     [("file", "02-AI编程工具链/Codex从入门到实战.md", 0.81)], "实测 10,325 汉字"),
    ("2", "2.4", "AI 编辑器与 Vibe Coding 全栈开发", 6000,
     [("file", "02-AI编程工具链/Vibe-Coding与AI编辑器全栈开发.md", 0.8)], "截图多，示例须重写"),
    #     2.5 / 2.6 当初是按「每份文件切一半」估的，与两份手册里真正讲
    #     上下文工程/流水线的节毫无关系。改为按节实测后，两章的素材量大幅
    #     回落——判定也跟着从「充裕/够用」变成「偏薄/严重不足」，这是实情：
    #     规则文件的写法要自己去官方文档补，Skills/Hooks 更是官方文档独有。
    ("2", "2.5", "上下文工程：规则文件、Skills、Hooks 与 MCP", 8000,
     [("file", "02-AI编程工具链/Claude-Code从入门到实战.md", 0.11),
      ("file", "02-AI编程工具链/Codex从入门到实战.md", 0.13),
      ("file", "02-AI编程工具链/AI-Harness入门与实践.md", 0.15)], "跨三份素材，须自行织合"),
    ("2", "2.6", "AI Harness：把 AI 编程接入工程流水线", 6000,
     [("file", "02-AI编程工具链/AI-Harness入门与实践.md", 0.15),
      ("file", "02-AI编程工具链/Claude-Code从入门到实战.md", 0.05),
      ("file", "02-AI编程工具链/Codex从入门到实战.md", 0.05)], "跨三份素材，须自行织合"),

    # ---------------- 第 3 篇 大模型与 Agent 原理
    ("3", "3.1", "大模型基础：从 Transformer 到 Token", 7000, [], "素材零覆盖，完全原创"),
    ("3", "3.2", "提示工程与链式推理", 7000,
     [("file", "03-大模型与Agent原理/大模型与AI-Agent从0到1笔记.md", 0.15),
      ("bank", "AI-Agent面试题合集-1038道.md", 0.05)], "题库只作考点索引"),
    ("3", "3.3", "Agent 是什么：LLM + 规划 + 工具 + 记忆", 6000,
     [("file", "03-大模型与Agent原理/大模型与AI-Agent从0到1笔记.md", 0.45)],
     "笔记本体覆盖最好的部分"),
    ("3", "3.4", "规划与决策策略", 7000,
     [("file", "03-大模型与Agent原理/大模型与AI-Agent从0到1笔记.md", 0.10),
      ("bank", "AI-Agent面试题合集-1038道.md", 0.05)], "题库该专题混入强化学习题"),
    ("3", "3.5", "工具调用与函数编排", 7000,
     [("file", "03-大模型与Agent原理/大模型与AI-Agent从0到1笔记.md", 0.20),
      ("bank", "AI-Agent面试题合集-1038道.md", 0.05)], ""),
    ("3", "3.6", "记忆与上下文管理机制", 6000,
     [("file", "03-大模型与Agent原理/大模型与AI-Agent从0到1笔记.md", 0.10),
      ("bank", "AI-Agent面试题合集-1038道.md", 0.05)], ""),
    ("3", "3.7", "多 Agent 协作框架设计", 6000,
     [("bank", "AI-Agent面试题合集-1038道.md", 0.05)], "以原创为主"),
    ("3", "3.8", "安全、对齐与防护", 6000,
     [("bank", "AI-Agent面试题合集-1038道.md", 0.05)], "以原创为主"),
    ("3", "3.9", "可观测性与评估", 7000,
     [("bank", "AI-Agent面试题合集-1038道.md", 0.05)], "以原创为主"),

    # ---------------- 第 4 篇 AI 应用开发框架
    ("4", "4.1", "LangChain 核心抽象与第一个应用", 7000,
     [("file", "04-AI应用开发框架/LangChain从入门到实战.md", 0.6)], "素材仅 2.3k 汉字"),
    ("4", "4.2", "提示模板、输出解析与 LCEL 编排", 7000,
     [("file", "04-AI应用开发框架/LangChain从入门到实战.md", 0.4)], ""),
    ("4", "4.3", "工具与 Agent：让模型动手干活", 7000,
     [("file", "04-AI应用开发框架/LangChain从入门到实战.md", 0.3),
      ("file", "04-AI应用开发框架/LangGraph智能体从入门到实战.md", 0.3)],
     "须以官方文档为准重写"),
    ("4", "4.4", "LangGraph：StateGraph 与状态编排", 7000,
     [("file", "04-AI应用开发框架/LangGraph智能体从入门到实战.md", 0.5)],
     "素材仅 2.5k 汉字"),
    ("4", "4.5", "持久化、多智能体编排与实战", 5000,
     [("file", "04-AI应用开发框架/LangGraph智能体从入门到实战.md", 0.2)],
     "以原创为主"),

    # ---------------- 第 5 篇 RAG 与生产级系统
    ("5", "5.1", "RAG 全景：为什么需要检索增强", 6000,
     [("file", "05-RAG与生产级系统/RAG技术从入门到深入.md", 0.30)], ""),
    ("5", "5.2", "文档解析与切分策略", 7000,
     [("file", "05-RAG与生产级系统/RAG技术从入门到深入.md", 0.25),
      ("file", "05-RAG与生产级系统/生产级RAG系统构建实战.md", 0.25)], ""),
    ("5", "5.3", "向量化与向量数据库", 7000,
     [("file", "05-RAG与生产级系统/RAG技术从入门到深入.md", 0.20),
      ("file", "05-RAG与生产级系统/生产级RAG系统构建实战.md", 0.20)],
     "含 Milvus 实战与 ADR 选型"),
    ("5", "5.4", "检索增强：混合检索、重排与查询改写", 8000,
     [("file", "05-RAG与生产级系统/RAG技术从入门到深入.md", 0.15),
      ("file", "05-RAG与生产级系统/生产级RAG系统构建实战.md", 0.20)],
     "含 ADR-004 检索策略"),
    ("5", "5.5", "生成、引用与幻觉抑制", 6000,
     [("file", "05-RAG与生产级系统/RAG技术从入门到深入.md", 0.15)], ""),
    ("5", "5.6", "RAG 评估：指标、实验与迭代", 7000,
     [("file", "05-RAG与生产级系统/生产级RAG系统构建实战.md", 0.15)],
     "含 RAGAS 评估框架"),
    ("5", "5.7", "生产级工程：缓存、并发、版本与成本", 8000,
     [("file", "05-RAG与生产级系统/生产级RAG系统构建实战.md", 0.25)],
     "含流式通信与可观测性"),
    ("5", "5.8", "综合项目：企业级多格式知识库问答系统", 10000,
     [("file", "05-RAG与生产级系统/生产级RAG系统构建实战.md", 0.30),
      ("file", "05-RAG与生产级系统/实战-智能出行Agent助手.md", 0.30)],
     "改用生产级 RAG 自带项目为主干"),
    ("5", "5.9", "项目复盘：从能跑到能讲", 4000, [], "完全原创"),

    # ---------------- 第 6 篇 模型接入与成本工程（方案 A 新增；素材零覆盖）
    ("6", "6.1", "模型选型：能力、价格与上下文窗口的三角权衡", 7000, [], "完全原创"),
    ("6", "6.2", "多厂商接入：Messages、Responses 与 OpenAI 兼容层", 7000, [], "完全原创"),
    ("6", "6.3", "模型网关：统一接口、路由、重试与降级", 7000, [], "完全原创"),
    ("6", "6.4", "成本与性能工程：Token 计费、缓存与模型分流", 7000, [], "完全原创"),

    # ---------------- 第 7 篇 AI 应用工程化（方案 A 新增；素材零覆盖）
    ("7", "7.1", "评测流水线：数据集、指标与 CI 回归", 7000, [], "完全原创"),
    ("7", "7.2", "可观测性：链路追踪、指标与成本看板", 7000, [], "完全原创"),
    ("7", "7.3", "Prompt 与配置版本化：灰度发布与 A/B 实验", 6000, [], "完全原创"),
    ("7", "7.4", "安全落地：提示注入、越狱与工具权限治理", 7000, [], "完全原创"),
    ("7", "7.5", "数据合规与脱敏：留存、隐私与审计", 6000, [], "完全原创"),

    # ---------------- 第 8 篇 交付与产品化（方案 A 新增；素材零覆盖）
    ("8", "8.1", "容器化部署：Docker、镜像瘦身与 Compose", 7000, [], "完全原创"),
    ("8", "8.2", "CI/CD 与发布：自动化测试、构建与灰度上线", 7000, [], "完全原创"),
    ("8", "8.3", "前端流式交互：SSE 与 AI SDK 对话式 UI", 7000, [], "完全原创"),
    ("8", "8.4", "多租户、配额与计费", 6000, [], "完全原创"),
    ("8", "8.5", "线上运维：SLO、告警、故障演练与容量规划", 6000, [], "完全原创"),

    # ---------------- 第 10 篇 求职冲刺（题库驱动；第 9 篇预留给进阶方向）
    ("10", "10.1", "简历：AI 应用开发岗怎么写才有回音", 6000, [], "完全原创"),
    ("10", "10.2", "项目讲述法：STAR、亮点提炼与追问防御", 6000, [], "完全原创"),
    ("10", "10.3", "AI 系统设计面试", 8000, [], "完全原创（方案 A 新增）"),
    ("10", "10.4", "AI Agent 面试考点手册", 15000,
     [("bank", "AI-Agent面试题合集-1038道.md", 0.05)], "题库仅作考点索引，答案须重写"),
    ("10", "10.5", "后端高频考点（Python / AI 岗位视角）", 15000,
     [("bank", "后端高频面试题大集合.md", 0.45)], "原档为 Java 体系，须换视角"),
    ("10", "10.6", "移动端考点：Android 与 Flutter-Dart", 12000,
     [("bank", "Android面试题合集-1136道.md", 0.30),
      ("bank", "Flutter-Dart面试题合集-714道.md", 0.20)], "须逐题筛选"),
    ("10", "10.7", "模拟面试与复盘清单", 5000, [], "完全原创"),
]

BANK_QUALITY = {
    "AI-Agent面试题合集-1038道.md":
        "低：结构完整但答案为通用套话，存在专题漂移（规划专题混入强化学习题），仅可作考点索引",
    "Android面试题合集-1136道.md":
        "中：结构完整，抽样内容有实质，但仍需人工筛选",
    "Flutter-Dart面试题合集-714道.md":
        "偏低：714 题中至少 20 题答案为模板占位，无实质内容",
    "后端高频面试题大集合.md":
        "高：165 题含考点/难度/答案，但体系为 Java，须换成 Python/AI 岗位视角",
}

THRESHOLDS = [(1.20, "充裕"), (0.80, "够用"), (0.45, "偏薄")]


def needs_original(row: dict) -> bool:
    """该章是否必须原创补写。

    除"偏薄/严重不足/无素材"外，还要纳入**零散文素材的题库驱动章**——
    它们的题库不可信（例如 3.7/3.8/3.9 靠 AI Agent 题库撑不起正文），
    不能因为打卡到题库就当作"有素材"。
    """
    if row["verdict"] in ("偏薄", "严重不足", "无素材"):
        return True
    return row["verdict"] == "题库驱动" and row["prose"] == 0


def verdict(ratio: float, has_prose: bool, has_bank: bool = False) -> str:
    """判定章节的素材状况。

    完全没有散文素材但题库充实时，不能记作"无素材"——那会掩盖真正的问题。
    这类章节（第 6 篇）标注为"题库驱动"，提醒写手：素材是问答格式，
    只能取考点与问法，答案必须重写。
    """
    if not has_prose:
        return "题库驱动" if has_bank else "无素材"
    for t, name in THRESHOLDS:
        if ratio >= t:
            return name
    return "严重不足"


def assigned_proj_segs() -> list[list[str]]:
    """计划里所有 `proj` 选择器的路径片断列表。

    空选择器（`sel=""`）表示「整目录都要」，写成空片断列表——`all(s in rel for s in [])`
    恒为真，天然覆盖全部文件，不会把整目录误报为「未分配」。
    """
    out: list[list[str]] = []
    for entry in PLAN:
        for kind, sel, _factor in entry[4]:
            if kind != "proj":
                continue
            for part in str(sel).split("+"):
                part = part.strip()
                out.append([s for s in part.split("/") if s])
    return out


def project_doc_lines() -> list[str]:
    """两个参考项目的讲解文档是否都被某条计划覆盖。

    与 fa 的检查同源：`proj` 支持路径过滤后，只写 `项目讲解/后端讲解` 就会把
    前端那七篇**静静地排除在外**（总量少了、报表却没有异常）。所以任何一篇
    没被覆盖的讲解文档都必须显式报出来。
    """
    sel_segs = assigned_proj_segs()
    miss: list[str] = []
    for d in sorted(FA_DIR.iterdir()):
        if not (d.is_dir() and d.name in ("fastapi_project", "fastapi_best_practice")):
            continue
        for f in sorted(d.rglob("*.md")):
            key = f"{d.name}/{f.relative_to(d).as_posix()}"
            if any(key.startswith(p) for p in PROJ_UNUSED):
                continue
            rel = f.relative_to(d).as_posix()
            if not any(all(s in rel for s in segs) for segs in sel_segs):
                miss.append(key)
    if not miss:
        return []
    return ["**参考项目未分配的讲解文档**：" + "、".join(f"`{m}`" for m in miss)]


def assigned_units() -> tuple[set[int], set[str], set[str]]:
    """统计计划章已经用到的素材单元：手册编号章 / 进阶块分段 / FastAPI 讲义章。"""
    py_ids: set[int] = set()
    seg_names: set[str] = set()
    fa_ids: set[str] = set()
    for entry in PLAN:
        for kind, sel, _factor in entry[4]:
            for part in str(sel).split(","):
                part = part.strip()
                if not part:
                    continue
                if kind == "py":
                    if "-" in part:
                        a, b = (int(x) for x in part.split("-"))
                        py_ids.update(range(a, b + 1))
                    else:
                        py_ids.add(int(part))
                elif kind == "pys":
                    seg_names.add(part)
                elif kind == "fa":
                    sub = ""
                    if "/" in part:
                        part, sub = part.split("/", 1)
                    for n in _fa_expand(part):
                        if not sub:
                            fa_ids.add(n)          # 整目录
                        else:
                            fa_ids.update(f"{n}#{i}" for i in _num_range(sub))
    return py_ids, seg_names, fa_ids


def unassigned_lines() -> list[str]:
    """找出「没有被任何计划章用到」的素材单元。

    这是防丢的关键一步：素材没被分配，就等于从教材里静静消失。
    必须在规划阶段发现，而不是写完 68 章才回头找。
    """
    blocks, segs = py_manual()
    py_ids, seg_names, fa_ids = assigned_units()
    out: list[str] = []

    miss_py = [(n, han(blocks[n])) for n in sorted(blocks) if n not in py_ids]
    miss_seg = [(n, han(segs.get(n, ""))) for n, _p, _d in PY_SEGMENTS if n not in seg_names]
    miss_fa = []
    for n, name in sorted(fa_dirs().items()):
        files = fa_files(n)
        uncovered = [f.relative_to(SRC).as_posix() for i, f in enumerate(files, 1)
                     if n not in fa_ids and f"{n}#{i}" not in fa_ids]
        if uncovered:
            miss_fa.append((n, name, uncovered))

    if miss_py:
        out.append("**Python 手册未分配的编号章**：" + "、".join(
            f"第 {n} 章（{c:,} 汉字）" for n, c in miss_py))
    if miss_seg:
        out.append("**手册进阶块未分配的分段**：" + "、".join(
            f"`{n}`（{c:,} 汉字）" for n, c in miss_seg))
    if miss_fa:
        out.append("**FastAPI 讲义未分配的章**：" + "、".join(
            (f"{n} {name}" if len(files) == len(fa_files(n))
             else f"{n} {name}（仅 {len(files)} 篇未分配）")
            for n, name, files in miss_fa))
    out.extend(project_doc_lines())
    if not out:
        out.append("全部素材单元均已分配到至少一个计划章。")
    else:
        out.append("> ⚠️ 未分配不等于无用：请确认是「有意不用」还是「漏了」。"
                   "漏掉的需补进对应章的素材池，有意的需在 §[`LEDGER.md`](../LEDGER.md) 里标 `⏭` 并写原因。")
    return out


def build_rows():
    rows = []
    for part, num, title, plan, specs, note in PLAN:
        prose = bank = 0
        keys: dict[str, int] = {}
        for s in specs:
            d = resolve(s)
            keys.update(d)
            tot = sum(d.values())
            if s[0] in BANK_KINDS:
                bank += int(tot * s[2])
            else:
                prose += int(tot * s[2])
        ratio = prose / plan if plan else 0.0
        rows.append(dict(part=part, num=num, title=title, plan=plan, prose=prose,
                         bank=bank, ratio=ratio,
                         verdict=verdict(ratio, prose > 0, bank > 0),
                         note=note, keys=keys))
    return rows


def write_report(path: Path) -> None:
    """生成 COVERAGE.md：素材池规模 + 逐章覆盖度 + 题库质量分级。"""
    rows = build_rows()
    blocks, segs = py_manual()
    L: list[str] = []
    A = L.append

    A("# 素材覆盖度审计报告（COVERAGE.md）")
    A("")
    A("> 本文件由 `python tools/audit_coverage.py --out COVERAGE.md` 自动生成，请勿手工编辑。")
    A("> 素材或章节规划变更后重新运行即可刷新。")
    A("")
    A("## 一、计量口径")
    A("")
    A("- 一律按**汉字量**计量，不按页数——页数会骗人（LangChain 素材 23 页，实际仅约 2,200 个汉字）。")
    A("- 计量前先剥除 extract_sources.py 生成的溯源头部，只算素材正文。")
    A("- 散文素材与题库素材分列，绝不混算：题库是问答格式，只能提供考点与问法，答案必须重写。")
    A("- 散文比值 = 散文素材汉字 / 计划汉字。")
    A("  **≥1.20 充裕 ｜ 0.80–1.20 够用 ｜ 0.45–0.80 偏薄 ｜ <0.45 严重不足 ｜ 无素材**")
    A("- 分篇汇总用**素材池**（按素材段落去重），因为同一段素材会被多章共用，各章相加必然虚高。")
    A("")
    A("## 二、素材池规模")
    A("")
    A(f"### Python 核心语法手册（编号章合计 {sum(han(v) for v in blocks.values()):,} 汉字）")
    A("")
    A("| 章 | 汉字 | 章 | 汉字 |")
    A("| --- | ---: | --- | ---: |")
    items = sorted(blocks.items())
    half = (len(items) + 1) // 2
    for i in range(half):
        left = f"{items[i][0]} | {han(items[i][1]):,}"
        right = f"{items[i+half][0]} | {han(items[i+half][1]):,}" if i + half < len(items) else "| "
        A(f"| {left} | {right} |")
    A("")
    A("#### 手册进阶块主题分段（无编号标题，实测占手册 55%）")
    A("")
    A("| 段标识 | 汉字 | 内容 |")
    A("| --- | ---: | --- |")
    for name, _pat, desc in PY_SEGMENTS:
        A(f"| `{name}` | {han(segs.get(name, '')):,} | {desc} |")
    A("")
    A("#### 素材分配完整性检查（防丢）")
    A("")
    for line in unassigned_lines():
        A(line)
    A("")
    A("### FastAPI 基础学习文档")
    A("")
    A("| 章 | 汉字 | 标题 |")
    A("| --- | ---: | --- |")
    for n, name in sorted(fa_dirs().items()):
        d = FA_DIR / name
        tot = sum(file_han(f.relative_to(SRC).as_posix()) for f in d.rglob("*.md"))
        A(f"| {n} | {tot:,} | {name[2:]} |")
    A("")
    A("### 题库质量分级")
    A("")
    A("| 题库 | 汉字 | 质量 |")
    A("| --- | ---: | --- |")
    for name, q in BANK_QUALITY.items():
        A(f"| {name} | {file_han('06-求职冲刺/' + name):,} | {q} |")
    A("")

    A("## 三、逐章覆盖度")
    A("")
    A("| 章 | 标题 | 计划字数 | 散文素材 | 题库素材(折算) | 散文比值 | 判定 | 说明 |")
    A("| --- | --- | ---: | ---: | ---: | ---: | --- | --- |")
    for r in rows:
        A(f"| {r['num']} | {r['title']} | {r['plan']:,} | {r['prose']:,} | "
          f"{r['bank']:,} | {r['ratio']:.2f} | {r['verdict']} | {r['note']} |")
    A("")

    A("## 四、分篇汇总")
    A("")
    A("| 篇 | 章数 | 计划字数 | 散文素材池 | 题库池 | 散文比值 | 判定 |")
    A("| --- | ---: | ---: | ---: | ---: | ---: | --- |")
    parts: dict[str, list] = {}
    for r in rows:
        parts.setdefault(r["part"], []).append(r)
    for p, rs in parts.items():
        plan = sum(x["plan"] for x in rs)
        pool: dict[str, int] = {}
        for x in rs:
            pool.update(x["keys"])
        prose = sum(v for k, v in pool.items() if not k.startswith("bank:"))
        bank = sum(v for k, v in pool.items() if k.startswith("bank:"))
        A(f"| {p} | {len(rs)} | {plan:,} | {prose:,} | {bank:,} | "
          f"{(prose/plan if plan else 0):.2f} | {verdict(prose/plan, prose > 0, bank > 0) if plan else '无素材'} |")
    A(f"| **合计** | **{len(rows)}** | **{sum(r['plan'] for r in rows):,}** | | | | |")
    A("")

    # 全书口径：第 9 篇（进阶方向）预留未启用，本就不在 rows 里；
    # 旧版这里写死排除 `6.`，那是改编号之前「第 6 篇 = 未启用的进阶篇」的遗留——
    # 现在的第 6 篇是零素材的「模型接入与成本工程」，被它静默漏掉 4 章。
    prose_rows = [r for r in rows if r["plan"]]
    weak = [r for r in prose_rows if needs_original(r)]
    zero = [r for r in weak if r["prose"] == 0]
    weak_plan = sum(r["plan"] for r in weak)
    base_plan = sum(r["plan"] for r in prose_rows)
    A("## 五、结论")
    A("")
    A("1. **第 1、2、5 篇素材可靠**（散文比值 0.94–1.36），可以「整理改写」为主。")
    A("2. **第 3、4 篇素材严重不足**（0.22 / 0.14），必须原创撰写或压缩篇幅。")
    A("3. **第 10 篇为题库驱动**：题量充足但质量分层，只能取考点与问法，答案须逐题重写；"
      "**第 6–8 篇零素材**（扩展篇），须逐条回到官方文档原创。")
    A(f"4. 全书需原创补写 **{len(weak)} / {len(prose_rows)} 章**，"
      f"合计计划 {weak_plan:,} 字，占全书的 {weak_plan/base_plan:.0%}；"
      f"其中 {len(zero)} 章散文素材为零："
      + "、".join(r["num"] for r in zero) + "。")
    A("")
    path.write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")


def part_aggregates() -> dict[int, dict[str, float]]:
    """返回 {篇号: {n, plan, prose, bank, ratio}}，与报表「分篇汇总」同口径。"""
    rows = build_rows()
    grouped: dict[str, list] = {}
    for r in rows:
        grouped.setdefault(r["part"], []).append(r)
    out: dict[int, dict[str, float]] = {}
    for part, rs in grouped.items():
        plan = sum(x["plan"] for x in rs)
        pool: dict[str, int] = {}
        for x in rs:
            pool.update(x["keys"])
        prose = sum(v for k, v in pool.items() if not k.startswith("bank:"))
        bank = sum(v for k, v in pool.items() if k.startswith("bank:"))
        out[int(part)] = {"n": len(rs), "plan": plan, "prose": prose, "bank": bank,
                          "ratio": prose / plan if plan else 0.0}
    return out


def _as_int(cell: str) -> int | None:
    digits = re.sub(r"[^\d]", "", cell)
    return int(digits) if digits else None


def _chapter_effective_words() -> dict[str, int]:
    """调 lint_book.py 拿到每章实测的有效字数，返回 {章号: 有效字数}。

    不在这里重算公式：字数口径必须只有一份实现，否则两边会各自漂。

    这里曾被文件名里的**一个空格**骗过去：原来的正则写的是 `(\d+\.\d+)-[^\s]*\.md`，
    而 `2.2-Claude Code 实战.md` 的说明部分含空格，于是这一章**被静默跳过**——
    它既不计入实测总数、也不算作“已完成”，而输出上没有任何异常。
    所以现在两道保险：文件名部分用 `[^-]` 而不是 `[^\s]`；
    再用 `uncounted_chapter_files()` 揪出“文件在、但一个数字都没被解析出来”的章。
    """
    import subprocess

    script = Path(__file__).with_name("lint_book.py")
    if not script.exists():
        return {}
    proc = subprocess.run([sys.executable, str(script)], cwd=str(script.parent.parent),
                          capture_output=True, text=True, encoding="utf-8", errors="replace")
    out: dict[str, int] = {}
    for line in proc.stdout.splitlines():
        # 章号后面一律宽松匹配：文件名里可能有空格、可能有连字符，
        # 这两种都曾让某章静默漏计（空格一次、`-` 尚未发生但同样致命）。
        m = re.search(r"^(\d+\.\d+)-.*?\.md\s+有效字数\s+([\d,]+)", line.strip())
        if m:
            out[m.group(1)] = int(m.group(2).replace(",", ""))
    return out


def uncounted_chapter_files(measured: dict[str, int]) -> list[str]:
    """book/ 下已存在的章文件，但没有出现在实测字典里——即“写了却没被统计到”。

    这正是上面那次静默跳过的形态：文件明明在，字数却不算进完成度，
    于是汇报里看起来就是“没写”。这类“静默漏账”比数字算错更危险，
    因为报表本身不会看起来奇怪。
    """
    out: list[str] = []
    book = Path(__file__).resolve().parents[1] / "book"
    for f in sorted(book.rglob("*.md")):
        # 守卫自己用**更宽松**的写法（不要求有连字符），这样“解析器漏掉”才会被它抓到；
        # 若守卫与解析器用同一条规则，它就只能永远沉默。
        m = re.match(r"^(\d+\.\d+)", f.name)
        if m and m.group(1) not in measured:
            out.append(f"{f.relative_to(book.parent).as_posix()}（章号 {m.group(1)} 不在实测里）")
    return out


def weight_sum_lines() -> list[str]:
    """同一份素材被多章计入的权重之和超过 1.0 的文件。

    `STYLE.md` 8.9 要求「共用素材按权重分记」，但此前只检查了「有没有被分配」
    （`unassigned_lines`），没检查「有没有被重复计入」——于是同一份文件可以在
    2.1 记 0.7、2.5 再记 0.5、2.6 又记 0.8，合计 2.0：三章都显得比实际充裕，
    而没有任何一处会报错。这类「静默虚高」比虚低更危险——它同时把篇幅基线与
    判定都抬高，让「素材充裕」成为错觉。

    第 2 篇已按实测的**节级拆分**修正（见各行注释）；第 4、5 篇的三份仍有此问题，
    需逐份量出各章实际用到的节才能改，不能拍脑袋对半砍。
    """
    acc: dict[str, list[tuple[str, float]]] = {}
    for row in PLAN:
        for kind, key, w in row[4]:
            acc.setdefault(f"{kind}:{key}", []).append((row[1], w))
    out: list[str] = []
    for key, users in sorted(acc.items()):
        total = sum(w for _, w in users)
        if total > 1.0001:
            out.append(f"{key} 合计 {total:.2f} ← "
                       + "、".join(f"{c}（{w}）" for c, w in users))
    return out


def weak_summary(part_max: int = 5) -> list[tuple[str, list[str], int, int]]:
    """PLAN「判定为偏薄及以下的章节汇总」表应有的内容（限第 0–part_max 篇）。

    这张表是手写的，数据源却在 build_rows() 里，两者已经漂过一次：
    `1.14`、`1.15` 被判定为严重不足却没进表，`2.1` 降为偏薄也没进——
    而漏记的后果很实际：后续排期会低估「需原创补写」的工作量。
    所以这里算一份，交给 check_plan 对账（与 8.5「机器能查的不靠人记」一致）。
    """
    rows = [r for r in build_rows()
            if str(r["part"]).isdigit() and int(r["part"]) <= part_max]
    groups = [
        ("严重不足", lambda r: r["verdict"] == "严重不足"),
        ("偏薄", lambda r: r["verdict"] == "偏薄"),
        ("无素材", lambda r: r["verdict"] == "无素材"),
        ("题库驱动（散文为零）",
         lambda r: r["verdict"] == "题库驱动" and r["prose"] == 0),
    ]
    out: list[tuple[str, list[str], int, int]] = []
    for label, pred in groups:
        sel = [r for r in rows if pred(r)]
        out.append((label, [r["num"] for r in sel], len(sel),
                    sum(r["plan"] for r in sel)))
    return out


def check_plan(plan_path: Path, coverage_path: Path) -> int:
    """把 PLAN.md / COVERAGE.md 里手写的汇总数字与实测结果对账。

    为什么需要它：数据一旦在多个文档里各写一遍，就一定会漂——本次就出现过
    PLAN 写「素材 1.24 / 116,218」而实测已是「1.25 / 121,052」的情况。
    数量对不上不影响写作，但会持续误导后续的篇幅与优先级判断。
    """
    agg = part_aggregates()
    total_chapters = sum(int(a["n"]) for a in agg.values())
    total_plan = sum(int(a["plan"]) for a in agg.values())

    # 已完稿章数以**正文文件是否存在**为准（判定口径见 lint_book.py），
    # 不采信文档里手写的「已完成」——本轮它就报过一个 stale 值：第 0 篇 3 章 + 第 1 篇 9 章，
    # 看板的合计却写着 3。
    done: dict[int, int] = {}
    measured_words = _chapter_effective_words()
    for cid in measured_words:
        head = cid.split(".")[0]
        if head.isdigit():
            done[int(head)] = done.get(int(head), 0) + 1
    done_total = sum(done.values())

    problems: list[str] = []

    text = plan_path.read_text(encoding="utf-8")

    def cells_of(line: str) -> list[str]:
        return [c.strip().strip("*").strip() for c in line.strip().strip("|").split("|")]

    # 1) 进度看板：| 1 编程地基 | 15 | 94,000 | 1.24 | 0 | 状态 |
    if "## 八、进度看板" in text:
        board = text.split("## 八、进度看板", 1)[1].split("前置工作进度", 1)[0]
        for line in board.splitlines():
            cells = cells_of(line)
            if len(cells) < 4:
                continue
            if cells[0] == "合计":
                if _as_int(cells[1]) != total_chapters:
                    problems.append(f"PLAN 看板合计：章数 {cells[1]} ≠ 实测 {total_chapters}")
                if _as_int(cells[2]) != total_plan:
                    problems.append(f"PLAN 看板合计：计划字数 {cells[2]} ≠ 实测 {total_plan:,}")
                if len(cells) >= 5 and re.fullmatch(r"\d+", cells[4]) \
                        and _as_int(cells[4]) != done_total:
                    problems.append(
                        f"PLAN 看板合计：已完成 {cells[4]} ≠ 实测 {done_total}")
                continue
            m = re.match(r"^(\d+)\s", cells[0])
            if not m or int(m.group(1)) not in agg:
                continue
            p = int(m.group(1))
            a = agg[p]
            if _as_int(cells[1]) != a["n"]:
                problems.append(f"PLAN 看板第 {p} 篇：章数 {cells[1]} ≠ 实测 {a['n']}")
            if _as_int(cells[2]) != a["plan"]:
                problems.append(f"PLAN 看板第 {p} 篇：计划字数 {cells[2]} ≠ 实测 {int(a['plan']):,}")
            if re.fullmatch(r"\d+\.\d+", cells[3]) and abs(float(cells[3]) - a["ratio"]) > 0.005:
                problems.append(f"PLAN 看板第 {p} 篇：素材比值 {cells[3]} ≠ 实测 {a['ratio']:.2f}")
            if len(cells) >= 5 and re.fullmatch(r"\d+", cells[4]) \
                    and _as_int(cells[4]) != done.get(p, 0):
                problems.append(
                    f"PLAN 看板第 {p} 篇：已完成 {cells[4]} ≠ 实测 {done.get(p, 0)}")

    # 2) 篇级覆盖度表：| 1 编程地基 | 15 | 94,000 | 116,218 | 0 | 1.24 | 充裕 |
    header_mark = "| 篇 | 章数 | 计划字数 | 散文素材池 | 题库池 | 散文比值 | 判定 |"
    if header_mark in text:
        block = text.split(header_mark, 1)[1]
        started = False
        for line in block.splitlines():
            if not line.strip():
                continue          # 表头行本身的尾巴是空串，先跳过
            if not line.startswith("|"):
                if started:
                    break
                continue
            cells = cells_of(line)
            if len(cells) < 4:
                continue
            started = True
            if cells[0] == "合计":
                if _as_int(cells[1]) != total_chapters:
                    problems.append(f"PLAN 篇级表合计：章数 {cells[1]} ≠ 实测 {total_chapters}")
                if _as_int(cells[2]) != total_plan:
                    problems.append(f"PLAN 篇级表合计：计划字数 {cells[2]} ≠ 实测 {total_plan:,}")
                continue
            m = re.match(r"^(\d+)\s", cells[0])
            if not m or int(m.group(1)) not in agg:
                continue
            p = int(m.group(1))
            a = agg[p]
            if _as_int(cells[1]) != a["n"]:
                problems.append(f"PLAN 篇级表第 {p} 篇：章数 {cells[1]} ≠ 实测 {a['n']}")
            if _as_int(cells[2]) != a["plan"]:
                problems.append(f"PLAN 篇级表第 {p} 篇：计划字数 {cells[2]} ≠ 实测 {int(a['plan']):,}")
            if re.fullmatch(r"\d+", cells[3].replace(",", "")) and _as_int(cells[3]) != a["prose"]:
                problems.append(f"PLAN 篇级表第 {p} 篇：散文素材池 {cells[3]} ≠ 实测 {int(a['prose']):,}")
            if len(cells) >= 6 and re.fullmatch(r"\d+", cells[4].replace(",", "")) \
                    and _as_int(cells[4]) != a["bank"]:
                problems.append(f"PLAN 篇级表第 {p} 篇：题库池 {cells[4]} ≠ 实测 {int(a['bank']):,}")
            if len(cells) >= 6 and re.fullmatch(r"\d+\.\d+", cells[5]) \
                    and abs(float(cells[5]) - a["ratio"]) > 0.005:
                problems.append(f"PLAN 篇级表第 {p} 篇：散文比值 {cells[5]} ≠ 实测 {a['ratio']:.2f}")

    # 3) 分篇章节标题里的「N 章 / N 字，素材 X.XX」
    for m in re.finditer(r"### 第 (\d+) 篇[^\n]*（([\d,]+) 章 / ([\d,]+) 字([^）]*)）", text):
        p, chapters, words, tail = int(m.group(1)), _as_int(m.group(2)), _as_int(m.group(3)), m.group(4)
        if p not in agg:
            continue
        a = agg[p]
        if chapters != a["n"]:
            problems.append(f"PLAN 第 {p} 篇标题：{m.group(2)} 章 ≠ 实测 {a['n']}")
        if words != a["plan"]:
            problems.append(f"PLAN 第 {p} 篇标题：{m.group(3)} 字 ≠ 实测 {int(a['plan']):,}")
        rm = re.search(r"素材\s*(\d+\.\d+)", tail)
        if rm and abs(float(rm.group(1)) - a["ratio"]) > 0.005:
            problems.append(f"PLAN 第 {p} 篇标题：素材比值 {rm.group(1)} ≠ 实测 {a['ratio']:.2f}")

    # 3) COVERAGE.md 的分篇汇总表（应由 --out 生成，不一致说明忘了刷新）
    if coverage_path.exists():
        cov = coverage_path.read_text(encoding="utf-8")
        if "## 四、分篇汇总" in cov:
            block = cov.split("## 四、分篇汇总", 1)[1].split("## 五、", 1)[0]
            seen: set[int] = set()
            for line in block.splitlines():
                cells = [c.strip().strip("*").strip() for c in line.strip().strip("|").split("|")]
                if len(cells) < 3 or not cells[0].isdigit():
                    continue
                p = int(cells[0])
                seen.add(p)
                if p not in agg:
                    problems.append(f"COVERAGE 分篇汇总：第 {p} 篇不在规划中")
                    continue
                a = agg[p]
                if _as_int(cells[1]) != a["n"]:
                    problems.append(f"COVERAGE 第 {p} 篇：章数 {cells[1]} ≠ 实测 {a['n']}")
                if _as_int(cells[2]) != a["plan"]:
                    problems.append(f"COVERAGE 第 {p} 篇：计划字数 {cells[2]} ≠ 实测 {int(a['plan']):,}")
            missing = set(agg) - seen
            if missing:
                problems.append("COVERAGE 分篇汇总缺少篇："
                                + "、".join(str(x) for x in sorted(missing)))
        else:
            problems.append("COVERAGE.md 缺少「四、分篇汇总」——请重跑 --out 刷新")
    else:
        problems.append(f"未找到 {coverage_path.name}，请先跑 --out 生成")

    # 4) 逐章状态列里的「✅ N 字」必须等于正文实测的有效字数。
    #    字数口径由 lint_book.py 单一实现，所以这里直接解析它的输出而不重写公式——
    #    公式只有一份，才不会“两边各自漂”。
    #
    #    章号必须**锚定在行的第一个单元格**。曾经写成 `\|\s*1\.10\s*\|`，结果
    #    1.8 那一行的「素材比值」列恰好是 1.10，于是把 1.8 的状态当成 1.10 的状态，
    #    报出「第 1.10 章：✅ 6,237 字 ≠ 11,807 字」这种看起来很像真问题、其实是
    #    误报的错误。校验器的误报会被当成噪声而整体忽略，所以这类锚定必须写死。
    for cid, actual in _chapter_effective_words().items():
        for m in re.finditer(rf"^\|\s*{re.escape(cid)}\s*\|([^\n]*)", text, re.M):
            row = m.group(1)
            sm = re.search(r"✅\s*([\d,]+)\s*字", row)
            if not sm:
                problems.append(
                    f"PLAN 第 {cid} 章：正文已存在，但章节表状态仍是 ⬜——"
                    "请回填「✅ N 字（达成 N%）」")
                continue
            if _as_int(sm.group(1)) != actual:
                problems.append(
                    f"PLAN 第 {cid} 章状态：✅ {sm.group(1)} 字 ≠ 正文实测 {actual:,} 字")

    # 4.5) 「素材 X.XX」示意图：它长着注释的样子，漂了两个月也没人发现
    #      （1.8 已从 1.36 降到 1.26，而图上还写着 1.36）。按「篇号与数值
    #      在文档里出现的先后**成对**」校验：先攒篇号，碰到一行数值就成对消掉。
    fence = None
    for m in re.finditer(r"```\n(.*?)```", text, re.S):
        if "素材" in m.group(1) and re.search(r"第\s*\d+\s*篇", m.group(1)):
            fence = m.group(1)
            break
    if fence:
        pending: list[int] = []
        for line in fence.splitlines():
            parts = [int(x) for x in re.findall(r"第\s*(\d+)\s*篇", line)]
            vals = [float(x) for x in re.findall(r"素材\s*(\d+\.\d+)", line)]
            if parts:
                pending.extend(parts)
            if not vals:
                continue
            if len(vals) > len(pending):
                problems.append(f"PLAN 素材示意图：{len(vals)} 个数值配 {len(pending)} 个篇号")
                continue
            for p, v in zip(pending, vals):
                if p in agg and abs(v - agg[p]["ratio"]) > 0.005:
                    problems.append(
                        f"PLAN 素材示意图第 {p} 篇：{v:.2f} ≠ 实测 {agg[p]['ratio']:.2f}")
            pending = pending[len(vals):]

    # 5) 批次表：批次一写「106,000」而第 1 篇已是 116,500 —— 同一份数字抄了两处
    #    就会漂，而且漂在**没有人会去核对**的地方（开工顺序表看起来不像数字表）。
    batch_mark = "| 批次 | 范围 | 章数 | 字数 | 工作量特征 | 里程碑 |"
    if batch_mark in text:
        block = text.split(batch_mark, 1)[1]
        for line in block.splitlines():
            if not line.strip():
                continue
            if not line.startswith("|"):
                break
            cells = cells_of(line)
            if len(cells) < 4:
                continue
            if cells[0] == "合计":
                if _as_int(cells[2]) != total_chapters:
                    problems.append(f"PLAN 批次表合计：章数 {cells[2]} ≠ 实测 {total_chapters}")
                if _as_int(cells[3]) != total_plan:
                    problems.append(f"PLAN 批次表合计：字数 {cells[3]} ≠ 实测 {total_plan:,}")
                continue
            parts = [int(x) for x in re.findall(r"第\s*(\d+)\s*篇", cells[1])]
            if not parts or any(p not in agg for p in parts):
                continue
            want_n = sum(int(agg[p]["n"]) for p in parts)
            want_plan = sum(int(agg[p]["plan"]) for p in parts)
            if _as_int(cells[2]) != want_n:
                problems.append(f"PLAN 批次表 {cells[0]}：章数 {cells[2]} ≠ 实测 {want_n}")
            if _as_int(cells[3]) != want_plan:
                problems.append(
                    f"PLAN 批次表 {cells[0]}：字数 {cells[3]} ≠ 实测 {want_plan:,}")

    # 6) 风险汇总表（手写、且此前无人核对）。它漏记的后果很实际：
    #    排期会低估「需原创补写」的量，所以按整块文本对账而不只比合计。
    risk_mark = "| 判定 | 章节 | 章数 | 计划字数 |"
    if risk_mark in text:
        got: list[str] = []
        for line in text.split(risk_mark, 1)[1].splitlines():
            if not line.strip():
                continue
            if not line.startswith("|"):
                break
            got.append(line.strip())
        want = [f"| {label} | {'、'.join(nums)} | {n:,} | {plan:,} |"
                for label, nums, n, plan in weak_summary()]
        summary = weak_summary()
        want.append(f"| **合计** | | **{sum(x[2] for x in summary):,}** | "
                    f"**{sum(x[3] for x in summary):,}** |")
        body = [ln for ln in got if not set(ln) <= set("|-: ")]
        if body != want:
            problems.append("PLAN 风险汇总表与实测不一致，应为：\n    "
                            + "\n    ".join(want))
    else:
        problems.append("PLAN 缺少「判定为偏薄及以下的章节汇总」表")

    # 7) 文首的进度句。它同时携带三个数（已完稿章数 / 总章数 / 实测字数），
    #    而这三个数在别处都有单一来源——漂了就会出现「文首 18/68、看板 19/68」
    #    这种同一页里自相矛盾的状态。
    pm = re.search(r"全书进度\s*\*\*(\d+)\s*/\s*(\d+)\s*章\*\*，实测\s*([\d,]+)\s*字", text)
    if not pm:
        problems.append("PLAN 文首缺少「全书进度 **N / 68 章**，实测 N 字」句")
    else:
        measured = sum(_chapter_effective_words().values())
        if _as_int(pm.group(1)) != done_total:
            problems.append(f"PLAN 文首进度：已完稿 {pm.group(1)} 章 ≠ 实测 {done_total}")
        if _as_int(pm.group(2)) != total_chapters:
            problems.append(f"PLAN 文首进度：总章数 {pm.group(2)} ≠ 实测 {total_chapters}")
        if _as_int(pm.group(3)) != measured:
            problems.append(f"PLAN 文首进度：实测 {pm.group(3)} 字 ≠ 正文实测 {measured:,} 字")

    # 8) 章文件存在、却没被统计到（**拦提交**）。这是「写了却没记账」的另一种形态：
    #    文件名一旦不符合解析规则，这章的字数就不进完成度，报表上看起来就是“没写”，
    #    而所有数字之间仍然自洽——所以它必须自己报出来，不能靠人盯着看。
    for line in uncounted_chapter_files(measured_words):
        problems.append(f"章文件未被统计：{line}")

    # 9) 素材重复计入（提示，不拦提交）。它不是文档数字漂移，而是**规划本身**
    #    的错：不报出来就会被当成「这两章素材很充裕」而一路写下去。
    over = weight_sum_lines()
    if over:
        print("⚠️ 同一份素材被多章重复计入（权重之和 > 1.0）：")
        for line in over:
            print(f"  · {line}")
        print("  影响：这些章的素材量与判定偏高，篇幅基线不可直接采信。"
              "\n  修法：按章节**实际用到的节**量出拆分比例，再改 tools/audit_coverage.py。")

    if problems:
        print("文档数字与实测不一致：")
        for p in problems:
            print(f"  ✖ {p}")
        print("\n修法：先改 tools/audit_coverage.py 里的规划值，再重跑"
              " `python tools/audit_coverage.py --out COVERAGE.md`，最后同步 PLAN.md。")
        return 1
    print("文档对账通过：PLAN.md 与 COVERAGE.md 的汇总数字与实测一致。")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--md", action="store_true", help="输出 markdown 表格")
    ap.add_argument("--pool", action="store_true", help="打印素材池明细")
    ap.add_argument("--out", metavar="FILE", help="把 markdown 报表写入文件（如 COVERAGE.md）")
    ap.add_argument("--check", action="store_true",
                    help="对账：PLAN.md / COVERAGE.md 的汇总数字是否与实测一致")
    ap.add_argument("--risk-table", action="store_true",
                    help="打印 PLAN「偏薄及以下」汇总表的应有内容，便于粘回去")
    args = ap.parse_args()

    if args.check:
        return check_plan(Path("PLAN.md"), Path("COVERAGE.md"))

    if _WARNINGS:
        print("素材规格告警：")
        for w in dict.fromkeys(_WARNINGS):
            print(f"  ⚠️ {w}")

    if args.out:
        write_report(Path(args.out))
        print(f"已写入 {args.out}")
        return 0

    if args.pool:
        blocks, segs = py_manual()
        print("=== Python 手册：编号章块 ===")
        for n, body in sorted(blocks.items()):
            print(f"  第 {n:>2} 章  {han(body):>7,} 汉字")
        print(f"  {'编号章小计':<8}{sum(han(v) for v in blocks.values()):>7,} 汉字")
        print("\n=== Python 手册：进阶块主题分段 ===")
        for name, _pat, desc in PY_SEGMENTS:
            print(f"  {name:<9}{han(segs.get(name, '')):>7,} 汉字  {desc}")
        print(f"  {'分段小计':<9}{sum(han(v) for v in segs.values()):>7,} 汉字")
        print("\n=== FastAPI 讲义 ===")
        for n, name in sorted(fa_dirs().items()):
            d = FA_DIR / name
            print(f"  {n}  {sum(file_han(f.relative_to(SRC).as_posix()) for f in d.rglob('*.md')):>7,} 汉字  {name}")
        print("\n=== 题库 ===")
        for name, q in BANK_QUALITY.items():
            print(f"  {name:<34} {file_han('06-求职冲刺/' + name):>9,} 汉字\n      {q}")
        return 0

    if args.risk_table:
        summary = weak_summary()
        print("| 判定 | 章节 | 章数 | 计划字数 |")
        print("| --- | --- | ---: | ---: |")
        for label, nums, n, plan in summary:
            print(f"| {label} | {'、'.join(nums)} | {n:,} | {plan:,} |")
        print(f"| **合计** | | **{sum(x[2] for x in summary):,}** | "
              f"**{sum(x[3] for x in summary):,}** |")
        return 0

    rows = build_rows()

    print("\n=== 素材分配完整性检查（防丢）===")
    for line in unassigned_lines():
        print("  " + line)
    over = weight_sum_lines()
    if over:
        print("\n  ⚠️ 重复计入（权重之和 > 1.0，素材量与判定会偏高）：")
        for line in over:
            print("    · " + line)

    if args.md:
        print("| 章 | 标题 | 计划字数 | 散文素材 | 题库素材(折算) | 散文比值 | 判定 | 说明 |")
        print("| --- | --- | ---: | ---: | ---: | ---: | --- | --- |")
        for r in rows:
            print(f"| {r['num']} | {r['title']} | {r['plan']:,} | {r['prose']:,} | "
                  f"{r['bank']:,} | {r['ratio']:.2f} | {r['verdict']} | {r['note']} |")
    else:
        cur = None
        for r in rows:
            if r["part"] != cur:
                cur = r["part"]
                print(f"\n{'='*104}\n第 {cur} 篇\n{'='*104}")
                print(f"{'章':<6}{'标题':<38}{'计划':>7}{'散文素材':>9}{'题库':>7}{'比值':>7}  判定")
            print(f"{r['num']:<6}{r['title'][:36]:<38}{r['plan']:>7,}{r['prose']:>9,}"
                  f"{r['bank']:>7,}{r['ratio']:>7.2f}  {r['verdict']}")

    print(f"\n{'='*104}\n分篇汇总（素材池按段落去重，不大于各章相加）\n{'='*104}")
    print(f"{'篇':<4}{'章数':>5}{'计划字数':>10}{'散文素材池':>11}{'题库池':>10}"
          f"{'散文比值':>9}  判定")
    parts: dict[str, list] = {}
    for r in rows:
        parts.setdefault(r["part"], []).append(r)
    for p, rs in parts.items():
        plan = sum(x["plan"] for x in rs)
        pool: dict[str, int] = {}
        for x in rs:
            pool.update(x["keys"])
        prose = sum(v for k, v in pool.items() if not k.startswith("bank:"))
        bank = sum(v for k, v in pool.items() if k.startswith("bank:"))
        v = verdict(prose / plan, prose > 0, bank > 0) if plan else "无素材"
        print(f"{p:<4}{len(rs):>5}{plan:>10,}{prose:>11,}{bank:>10,}"
              f"{(prose/plan if plan else 0):>9.2f}  {v}")
    tp = sum(r["plan"] for r in rows)
    print(f"{'合计':<4}{len(rows):>5}{tp:>10,}")

    # 需原创补写：散文素材不足以支撑成章者（口径见 needs_original）。
    # 全书口径——第 9 篇（进阶方向）预留未启用，不在 rows 里，无需排除。
    prose_rows = [r for r in rows if r["plan"]]
    weak = [r for r in prose_rows if needs_original(r)]
    total_plan = sum(r["plan"] for r in prose_rows)
    print(f"\n需原创补写的章节：{len(weak)} / {len(prose_rows)} 章"
          f"（全书口径），合计计划 {sum(r['plan'] for r in weak):,} 字"
          f"，占全书的 {sum(r['plan'] for r in weak)/total_plan:.0%}")
    zero = [r for r in weak if r["prose"] == 0]
    print(f"其中散文素材为零（只能原创）：{len(zero)} 章 —— "
          + "、".join(r["num"] for r in zero))
    hard = [r for r in weak if r["verdict"] in ("严重不足", "无素材")]
    print(f"风险最高（严重不足/无素材）：{len(hard)} 章 —— "
          + "、".join(r["num"] for r in hard))
    return 0


if __name__ == "__main__":
    sys.exit(main())
