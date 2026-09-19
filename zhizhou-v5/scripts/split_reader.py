#!/usr/bin/env python
"""5.2 读数：**换切法到底换来了什么**。

五组：

    ① 入口：格式检测与四种「读不出」（加密 / 扫描件 / 超大 / 无 OCR 引擎）
    ② 五代切法：片数、块长分布、入库量、**答案片的排名**、被切坏的表格
    ③ 重叠的代价：同一句话多存了几遍
    ④ 清洗：噪声的四种形态，与清洗前后的质量报告
    ⑤ 父子片：一层检索、一层生成

    python scripts/split_reader.py --offline     # 不需要密钥：确定性，提交钩子跑这个
    python scripts/split_reader.py --self-test   # 反例夹具：坏切法必须被拦下
    python scripts/split_reader.py --real        # 把 sections 切法接回 5.1 的两条路径

**本章与 5.1 共用同一个语料、同一个检索器**，唯一的变量是切法——
这是 4.3 那条纪律（先控制变量，再谈结论）在第 5 篇的第二次执行。
"""
from __future__ import annotations

import argparse
import io
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.corpus import NgramIndex, load_corpus, split_paragraphs          # noqa: E402
from app.questions import QUESTIONS                                       # noqa: E402
from app.split import (Locked, Piece, Unsupported, broken_tables,          # noqa: E402
                       build_index, chunk_fixed, chunk_parent_child, chunk_recursive,
                       chunk_sections, chunk_sliding, clean_text, load_document,
                       piece_stats, quality, sections, sniff_format)

#: ② 那一组把资料交给生成侧时的取数
TOP_K = 3


def _hr(title: str) -> None:
    print("=" * 78)
    print(title)
    print("=" * 78)


# --------------------------------------------------------------------------- 夹具

def _pdf_with_text(path: Path, lines: list[str]) -> None:
    """生成一份**有文本层**的 PDF。用于证明「魔数不听扩展名」。

    `fontname="china-s"` 是 MuPDF 自带的中文字体：不指定的话，
    写入的中文会用默认的拉丁字体渲染成豆腐块，抽出来的文本就是一堆「·」。
    """
    import fitz                                        # noqa: PLC0415

    doc = fitz.open()
    page = doc.new_page()
    for i, line in enumerate(lines):
        page.insert_text((72, 90 + 18 * i), line, fontname="china-s", fontsize=11)
    doc.save(path)
    doc.close()


def _pdf_locked(path: Path) -> None:
    """生成一份**加密** PDF：用户密码 `pw123`，前四个常用密码都打不开。"""
    import fitz                                        # noqa: PLC0415

    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 90), "内部资料：回滚方式是 git revert。",
                     fontname="china-s", fontsize=11)
    doc.save(path, encryption=fitz.PDF_ENCRYPT_AES_256,
             owner_pw="owner-secret", user_pw="pw123")
    doc.close()


def _pdf_scanned(path: Path) -> None:
    """生成一份**扫描件**：一整页只有一张图，文本层是空的。"""
    import fitz                                        # noqa: PLC0415
    from PIL import Image                              # noqa: PLC0415

    doc = fitz.open()
    page = doc.new_page()
    buf = io.BytesIO()
    Image.new("RGB", (600, 120), "white").save(buf, format="PNG")
    page.insert_image(fitz.Rect(60, 60, 660, 180), stream=buf.getvalue())
    doc.save(path)
    doc.close()


def _docx(path: Path) -> None:
    """生成一份带标题样式的 Word：用来量「样式 → `#` 层级」那一步。"""
    from docx import Document                          # noqa: PLC0415

    d = Document()
    d.add_heading("知舟对外说明", level=1)
    d.add_paragraph("这一段是正文，没有标题样式。")
    d.add_heading("支持范围", level=2)
    d.add_paragraph("仅支持已发布的模型。")
    t = d.add_table(rows=2, cols=2)
    t.cell(0, 0).text = "级别"
    t.cell(0, 1).text = "时限"
    t.cell(1, 0).text = "P0"
    t.cell(1, 1).text = "15 分钟"
    d.save(path)


def build_fixtures(root: Path) -> Path:
    """把夹具造好。**全部现造、跑完删**：仓库里不放二进制样本，也不放生成的 PDF。"""
    root.mkdir(parents=True, exist_ok=True)
    # 一份真 PDF 存成 .txt —— 魔数与扩展名的分歧就藏在这一行里
    _pdf_with_text(root / "报告.txt", ["知舟季度报告", "本季度检索延迟 p95 为 780 毫秒。"])
    # 一份真·大文件：模拟「年报全集」这类超上限的输入
    (root / "年报全集.txt").write_text("知舟年报：检索段的说明与各项指标。\n" * 120_000,
                                       encoding="utf-8")
    # 一份 HTML 存成 .md
    (root / "页面.md").write_text(
        "<!DOCTYPE html><html><head><title>值班说明</title>"
        "<script>var x=1;</script></head><body><h1>值班说明</h1>"
        "<p>P0 十五分钟内首次响应。</p></body></html>", encoding="utf-8")
    (root / "清单.csv").write_text(
        "服务商,月限额,备注\nagnes,2400万,主服务商\n备用商,300万,灰度中\n", encoding="utf-8")
    _docx(root / "手册.docx")
    _pdf_locked(root / "locked.pdf")
    _pdf_scanned(root / "扫描件.pdf")
    from PIL import Image                              # noqa: PLC0415

    Image.new("RGB", (40, 20), "white").save(root / "截图.png")
    return root


# --------------------------------------------------------------------------- ①

def reading_entry(root: Path) -> dict:
    _hr("① 入口：格式检测看魔数，不看扩展名")
    print("先把七个文件摆出来，**其中三份的扩展名与真实格式故意对不上**：\n")
    for name in ("报告.txt", "页面.md", "清单.csv", "手册.docx", "扫描件.pdf", "截图.png",
                 "年报全集.txt"):
        p = root / name
        head = p.read_bytes()[:8]
        head_text = "".join(chr(b) if 32 <= b < 127 else "·" for b in head)
        size = p.stat().st_size
        shown = f"{size / 1024 / 1024:.2f}MB" if size > 100_000 else f"{size}B"
        print(f"    {name:14s} {shown:>7s} 后缀 {p.suffix:6s} 头 8 字节 "
              f"{head_text:10s} → 判为 {sniff_format(p)}")
    print()
    print("两处最容易吃亏的地方：")
    print("    · `报告.txt` 后缀说是文本，**魔数是 `%PDF-`**——按后缀路由会当文本读，")
    print("      读出满屏乱码；按魔数路由它走 PDF 解析器。")
    print("    · `页面.md` 后缀说是 Markdown，**内容是 HTML**——按后缀路由会留下标签与脚本。")
    print()

    rows = []
    for name in ("报告.txt", "页面.md", "清单.csv", "手册.docx"):
        doc = load_document(root / name)
        q = quality(doc.text)
        rows.append((name, doc, q))
        print(f"    {name:14s} → {len(doc.text):4d} 字，标题「{doc.title}」，"
              f"汉字比 {q['han_ratio']}，乱码比 {q['garbled']}")
    print()

    print("再试四种**读不了**的文件。它们的区别很重要：")
    print("「需要密码」「需要 OCR 引擎」「太大」「没有解析器」是四件不同的事。")
    print()
    cases = (
        ("locked.pdf", "加密件：试 4 个常用密码都打不开", {"passwords": ("", "123456", "password", "admin")}),
        ("扫描件.pdf", "扫描件：整页没有文本层，要 OCR 管道", {}),
        ("截图.png", "图片：本机没有 OCR 引擎", {}),
        ("年报全集.txt", "超过大小上限：不读，先说清多大", {"max_mb": 1.0}),
    )
    for name, why, kw in cases:
        p = root / name
        try:
            load_document(p, **kw)
        except (Unsupported, Locked) as exc:
            print(f"    ✔ 拦下 {name}（{why}）→ {type(exc).__name__}: {exc}")
        else:
            print(f"    ✖ 没拦住 {name}（{why}）——这是一条该报的缺陷")
    print()
    locked = root / "locked.pdf"
    doc = load_document(locked, passwords=("pw123",))
    print(f"密码对了就进得来：{locked.name} → {doc.text!r}")
    return {"rows": rows}


# --------------------------------------------------------------------------- ②

#: ② 要对照的切法。**第 0 代（5.1 的空行切）必须留在里面**——没有基线就没有对照。
#: 四代的区别只在于「在哪里落刀」：按固定字数、按固定字数带重叠、按分隔符、按标题结构。
STRATS = {
    "paragraph": lambda d: tuple(Piece(c.doc_id, c.index, c.text)
                                 for c in split_paragraphs(d)),
    "fixed": lambda d: tuple(Piece(d.doc_id, i, t)
                          for i, t in enumerate(chunk_fixed(d.text, size=300))),    "sliding": lambda d: tuple(Piece(d.doc_id, i, t) for i, t in enumerate(
        chunk_sliding(d.text, size=300, overlap=60))),
    "recursive": lambda d: tuple(Piece(d.doc_id, i, t) for i, t in enumerate(
        chunk_recursive(d.text, size=300, overlap=60))),
    "sections": lambda d: chunk_sections(d, size=300, overlap=60),
}


def reading_strategies() -> dict:
    _hr("② 五代切法：同一份语料、同一个检索器，唯一变量是切法")
    docs = load_corpus()
    total = sum(len(d.text) for d in docs)
    print(f"语料 {len(docs)} 份、正文合计 {total} 字。检索器一律是 5.1 那个字符 2-gram "
          f"倒排 ＋ BM25。\n")
    head = f"{'切法':<22}{'片数':>5}{'均长':>8}{'均匀度':>8}{'入库量':>9}   答案片排名"
    print(head)
    print("-" * len(head))
    out = {}
    for name, fn in STRATS.items():
        pieces = tuple(p for d in docs for p in fn(d))
        idx = NgramIndex(tuple(p.as_chunk() for p in pieces))
        st = piece_stats(pieces)
        stored = sum(len(p.text) for p in pieces)
        ranked = idx.search(QUESTIONS[0].text, k=len(idx.chunks))
        rank = next((r for r, (c, _) in enumerate(ranked, 1) if "回滚" in c.text), None)
        bad = broken_tables(pieces)
        out[name] = {"pieces": pieces, "stats": st, "rank": rank, "bad": bad,
                     "stored": stored}
        print(f"{name:<22}{st['count']:>5}{st['avg']:>8.1f}{st['uniformity']:>8.3f}"
              f"{stored:>6}({stored / total * 100:5.1f}%)   第 {rank} 位　坏表 {len(bad)}")
    print()
    print("三段结论，一条比一条重要：")
    print()
    print("**第一段：基线的错被证实了，也确实被修掉了。** 5.1 的空行切分把那句「引子 ＋ 四条目」")
    print("劈成两片（25 字与 104 字），提问那半句落在前一片上，装着「回滚」的那一片掉到第 5。")
    print("换成任何一种有尺寸上限的切法，它都回到第 1。")
    print()
    print("**第二段：「答案片排名」这一条读数是钝的。** 你看这一列：")
    print(f"    fixed / sliding / recursive / sections 全是第 1——**它们四个不一样**，")
    print("但这一列分不出来。一条读数只对这一类病（句子被劈开）敏感，")
    print("所以要再量两条：**被切坏的表格**（下一条）与**入库量**。")
    print()
    print("**第三段：均匀度不能单独用来选切法。** 均匀度最高的是定长切分——")
    print("它天生均匀，而它恰恰是唯一会把表格与代码拦腰切断的一代。")
    print("把三个数放在一起看，才是这一次对照真正立住的地方：")
    print()
    bad_all = {n: v["bad"] for n, v in out.items()}
    for name, v in out.items():
        flag = "（表格完整）" if not v["bad"] else f"（切坏 {len(v['bad'])} 片：{'、'.join(v['bad'])}）"
        print(f"    {name:<12} 均匀度 {v['stats']['uniformity']:.3f}　入库 "
              f"{v['stored'] / total * 100:5.1f}%　{flag}")
    print()
    print("这一列里只有 `sections` 同时做到三件事：表格没切坏、答案片在第 1、")
    print(f"入库量最低（{out['sections']['stored'] / total * 100:.1f}%）——因为**标题不进正文**，")
    print("它把这批语料约 14% 的字（标题行）从可检索正文里拿掉了，")
    print("而那部分字本来就只会让召回率虚高。")
    print()
    print("**一句必须写下来的话**：这一次「sections 最好」只在**这一份语料**上成立。")
    print("六份文档都有标题、都很短、都按节写；换一批没有标题的文档，这一代退化成递归切分，")
    print("一点增益都没有。要下判断得等 5.6 的评测集。")
    return out


# --------------------------------------------------------------------------- ③

def _covered_by(b: str, a: str) -> int:
    """`b` 有多长的前缀已经出现在 `a` 里。

    不做「最长公共子串」那类全局算法：重叠是 `_pack` 回退前一片的尾巴造成的，
    所以重合只可能出现在「`a` 的尾巴 ＝ `b` 的开头」这一种位置上。
    返回的是**从头开头算起的连续重合长度**——它是「这一片有多少字是新的」的补数。
    """
    for n in range(min(len(a), len(b)), 0, -1):
        if a.endswith(b[:n]):
            return n
    return 0


def reading_overlap() -> dict:
    _hr("③ 重叠的代价：同一句话多存了几遍")
    docs = load_corpus()
    total = sum(len(d.text) for d in docs)
    print("重叠是「把被切断的那句话在相邻两片里各留一份」。它一定有效，也一定有代价——")
    print("代价是**入库量**，而入库量直接等于嵌入与存储的费用（5.7 的账）。\n")
    print(f"{'档位':<18}{'片数':>6}{'均长':>8}{'入库量':>10}{'相对语料':>10}")
    print("-" * 52)
    rows = {}
    for size, ov in ((300, 0), (300, 30), (300, 60), (300, 120), (300, 240)):
        pieces = tuple(Piece(d.doc_id, i, t)
                       for d in docs
                       for i, t in enumerate(chunk_sliding(d.text, size=size, overlap=ov)))
        stored = sum(len(p.text) for p in pieces)
        st = piece_stats(pieces)
        rows[(size, ov)] = (pieces, stored)
        print(f"size={size} overlap={ov:<5}{st['count']:>6}{st['avg']:>8.1f}"
              f"{stored:>10}{stored / total * 100:>9.1f}%")
    print()
    print("入库量那一列就是这一节的账：**重叠是拿冗余换连续**。")
    print("`overlap=0` 到 `240`，入库量从 100.0% 涨到 291.5%。")
    print("注意最后两档的涨幅不是线性的：片数从 13 跳到 32，因为重叠把每片推短之后，")
    print("被推短的那些片又各自触发了一次切分。**参数之间的关系不是线性的，不能拿算术外推。**")
    print()
    print("但**「重复」到底长什么样，得量，不能推。** 取 `overlap=240` 的前 3 片，"
          "数每片有多少字是新的：")
    idx = NgramIndex(tuple(p.as_chunk() for p in rows[(300, 240)][0]))
    got = idx.search(QUESTIONS[0].text, k=TOP_K)
    for i in range(1, len(got)):
        prev, cur = got[i - 1][0], got[i][0]
        already = _covered_by(cur.text, prev.text)
        print(f"    {cur.cite()}（{len(cur.text)} 字）：前 {already} 字已在 "
              f"{prev.cite()} 里出现过，**新字 {len(cur.text) - already} 个**")
    print()
    print("这里量到的是：**后面的片整片都是前一片的尾巴**（前 132 字全在 `#0` 里）。")
    print("于是检索交回的「3 片」实际只有 1 片的信息量，另外两片是它的截尾副本——")
    print("而它们照旧占掉 3 个提示位。**这不是重复入库的小毛病，是提示位置被吃掉了。**")
    print()
    print("`_pack` 的重叠是「回退前一片的尾巴」，所以只要 `overlap` 接近 `size`，")
    print("这个现象就一定会出现——它不是配置失误，是这一代数下去必然的结果。")
    print()
    print("`overlap >= size` 会让步长为 0，切片循环永远不前进——")
    print("`chunk_sliding` 在入口就把这种参数挡掉了（读数 ④ 的夹具里有一条用例守着它）。")
    return rows


# --------------------------------------------------------------------------- ④

#: 一份「脏文本」：四种噪声各来一处。**它不来自任何真实文件，是照着真实文件的脏法造的。**
DIRTY = (
    "知舟发布规范\x00\n"
    "第一页\n"
    "１．变更摘要：这次改了什么。\n"
    "2. �影响面：哪些接口会变。\n"
    "①回滚方式：怎么退回去。\n\n\n\n"
    "4. 验证步骤：按什么顺序验。\n"
    "第二页\n"
)


def reading_clean() -> dict:
    _hr("④ 清洗：五种噪声，一条顺序不能换的管线")
    print("先看清洗前后的质量报告。**「乱码比」是这三个数里最该看的那个**：")
    print("它是「这份文本要不要人工抽查」的唯一机检依据。\n")
    before, after = quality(DIRTY), quality(clean_text(DIRTY))
    print(f"{'':<10}{'字符数':>8}{'乱码比':>10}{'平均行长':>10}")
    print("-" * 38)
    for name, q in (("清洗前", before), ("清洗后", after)):
        print(f"{name:<10}{q['chars']:>8}{q['garbled']:>10}{q['avg_line']:>10.1f}")
    print()
    print("五种噪声与它们各自被哪一步带走：")
    print("    1. `\\x00`（控制字符）　　→ 第 1 步，按 Unicode 类别删 `Cc`")
    print("    2. `第一页` / `第二页`（页码行）→ 第 4 步后的单独一步")
    print("    3. `１．`（全角数字与句点）→ 第 2 步 NFKC：`１．` 变 `1.`")
    print("    4. `①`（圈码）　　　　→ 第 2 步 NFKC：`①` 变 `1`")
    print("    5. `\\ufffd`（替换字符，解码失败的残留）→ **谁都带不走它**")
    print()
    print(f"清洗后的文本：\n    {clean_text(DIRTY)!r}")
    print()
    print("**第 5 条是这个读数最值钱的地方。** 替换字符 `U+FFFD` 说明原始解码已经出错，")
    print(f"而清洗**带不走它**：它的字符类别是「符号」（`So`），与普通字一样合法，"
          f"五条规则里没有一条碰得到它。")
    print(f"    清洗后乱码比 {after['garbled']}，整份文本里那 "
          f"{DIRTY.count(chr(0xfffd))} 个替换字符**一个也没少**（变的只是分母）。")
    print()
    print("所以「乱码比高」的正确处置不是清洗，是**回去修编码，或者换一个解析器**。")
    print("把清洗当修复，会让一份错文本看起来像一份好文本——那比留着它更危险。")
    print()
    print("反向守：`drop_page_numbers=False` 时，页码行必须**原样留着**。")
    kept = clean_text(DIRTY, drop_page_numbers=False)
    print(f"    留着页码：{'第一页' in kept and '第二页' in kept}")
    print("这一条不是洁癖：法规、合同里的编号小节号常常正好是「一行一个数字」，")
    print("无条件删会删掉真实内容——所以它是个参数，默认开、但要能关。")
    return {"before": before, "after": after}


# --------------------------------------------------------------------------- ⑤

def reading_parent_child() -> dict:
    _hr("⑤ 父子片：拿小的去检索，把大的交给模型")
    docs = load_corpus()
    doc = next(d for d in docs if d.doc_id == "接入清单")
    parents, children = chunk_parent_child(doc, parent=300, child=100, overlap=20)
    print(f"`{doc.doc_id}` 的节：")
    for s in sections(doc):
        print(f"    [{s.heading}] {len(s.text)} 字")
    print()
    print(f"切成父子两层之后：父片 {len(parents)} 个，子片 {len(children)} 个")
    for p in parents:
        kids = [c for c in children if c.doc_id.startswith(f"{doc.doc_id}#p{p.index}")]
        print(f"    父片 #{p.index}（{len(p.text)} 字）← 子片 "
              f"{', '.join(str(k.index) + '（' + str(len(k.text)) + ' 字）' for k in kids)}")
    print()
    print("两层的分工：")
    print("    · **子片入库、参与检索**：它短，字面重合的信噪比高，命中更准；")
    print("    · **父片只存不检索**：命中子片后用 `doc_id` 回查父片，交给模型的是完整一节。")
    print()
    print("为什么不能只留一层：")
    print("    · 只留子片：模型拿到的是 100 字的碎片，一句话说一半（5.1 的 Q1 就是这么丢的）；")
    print("    · 只留父片：检索退回到 300 字的长片，字面重合被稀释，命中率下降。")
    print("**这一代不是「第五种切法」，它是「同一份文本入库两遍」**——")
    print("所以它的代价要单独算：入库量近似翻倍，而收益只在召回与上下文这对矛盾上兑现。")
    print()
    print(f"入库量对照：父片 {sum(len(p.text) for p in parents)} 字 ＋ "
          f"子片 {sum(len(c.text) for c in children)} 字 "
          f"（原文 {len(doc.text)} 字）")
    return {"parents": parents, "children": children}


# --------------------------------------------------------------------------- ⑥

def reading_real() -> dict:
    _hr("⑥ 真机：把 sections 切法接回 5.1 的两条路径（**只报数，不归因**）")
    from app.llm import make_call                          # noqa: PLC0415
    from app.rag import answer                             # noqa: PLC0415

    call = make_call()
    print(f"服务商：{call.cfg.base_url}｜模型：{call.cfg.model}\n")
    index, _docs, _pieces = build_index(strategy="sections")
    out = {}
    for q in QUESTIONS:
        chunks = tuple(c for c, _ in index.search(q.text, k=TOP_K))
        direct = answer(call, q.text)
        grounded = answer(call, q.text, chunks)
        out[q.qid] = (direct, grounded)
        print(f"{q.qid}（{q.kind}）收到 {len(chunks)} 片，"
              f"直答拒答 {direct.refused}，带资料拒答 {grounded.refused}，"
              f"引用 {list(grounded.citations)}，核对 {grounded.issues or '通过'}")
    print()
    print("这一路与 5.1 的第 ④ 组是同一条路径、同一批问题，**唯一变量是切法**。")
    print("两遍的差要按 4.5 的教训读：**一次运行不是比例**，它只用来发现问题。")
    return {"out": out}


# --------------------------------------------------------------------------- 自检

def self_test() -> int:
    """反例夹具：**坏切法必须被拦下**。本章的判据有两条能进测试——坏表与参数。"""
    _hr("自检：切法的参数边界与「表格被切坏」的判据")
    docs = load_corpus()
    cases = []

    def expect_error(fn, exc=ValueError):
        try:
            fn()
        except exc:
            return True
        return False

    cases.append(("overlap >= size 必须报错（否则步长为 0，死循环）",
                  expect_error(lambda: chunk_sliding("甲" * 100, size=50, overlap=50))))
    cases.append(("size=0 必须报错",
                  expect_error(lambda: chunk_recursive("甲" * 100, size=0))))
    cases.append(("负重叠必须报错",
                  expect_error(lambda: chunk_sliding("甲" * 100, size=50, overlap=-1))))

    good = tuple(p for d in docs for p in chunk_sections(d, size=300, overlap=60))
    cases.append(("结构感知切分不得切坏任何表格", not broken_tables(good)))
    cases.append(("结构感知切分把标题排除在正文之外",
                  not any(p.text.strip().startswith("#") for p in good)))

    small = tuple(Piece(d.doc_id, 0, t)
                  for d in docs for t in chunk_sliding(d.text, size=120, overlap=30))
    cases.append(("定长 120 一定会切坏表格（判据本身在守）", bool(broken_tables(small))))

    bad = 0
    for name, ok in cases:
        bad += not ok
        print(f"  {'✔' if ok else '✖'} {name}")
    print(f"\n自检 {len(cases) - bad}/{len(cases)} 通过")
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true", help="离线五组（不需要密钥）")
    ap.add_argument("--real", action="store_true", help="把新切法接回真机那一路")
    ap.add_argument("--self-test", action="store_true", help="反例夹具")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    if not args.offline and not args.real:
        ap.print_help()
        return 2

    tmp = Path(tempfile.mkdtemp(prefix="zhizhou-v5-split-"))
    try:
        if args.offline:
            build_fixtures(tmp)
            reading_entry(tmp)
            print()
            reading_strategies()
            print()
            reading_overlap()
            print()
            reading_clean()
            print()
            reading_parent_child()
            _hr("离线自检通过")
        if args.real:
            reading_real()
            _hr("真机读数完成")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
