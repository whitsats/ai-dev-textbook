# tests/test_split.py —— 不需要密钥、不需要网络：入口、清洗、切法、父子片
"""这一份测的是第 5 篇「第二步」能不能被机械验收。

八组断言，每一组都对应正文里的一个结论，**都不需要模型**：

1. **格式检测不听扩展名**：真 PDF 存成 `.txt`、HTML 存成 `.md`，都要判对；
2. **四种「读不出」各有各的异常**：加密、扫描件、超大、没有解析器——
   它们要的是四种不同的处置，所以不能合成一个 `Exception`；
3. **清洗的五步各治一种噪声**，而且 `\\ufffd` **谁都不该动它**；
4. **乱码比不把换行算进去**（不然每一份多行文本都自带一个假乱码率）；
5. **切法的参数边界**：`overlap >= size` 会让步长为 0；
6. **四代切法的行为**：定长会切坏表格，结构感知不会；重叠真的发生在片与片之间；
7. **回归门**：同一个问题，空行切分把答案片放到第 5，结构感知把它放回第 1——
   这两个数写死在测试里，哪天有人改了切法就会被拦下；
8. 端到端：离线脚本跑通，且打印出正文引用的那几行读数。
"""
from __future__ import annotations

import io
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.corpus import NgramIndex, load_corpus, split_paragraphs          # noqa: E402
from app.questions import by_id                                            # noqa: E402
from app.split import (Locked, Piece, Unsupported, broken_tables,          # noqa: E402
                       chunk_fixed, chunk_parent_child, chunk_recursive,
                       chunk_sections, chunk_sliding, clean_text, garbled_ratio,
                       load_document, parse_csv, piece_stats, quality, sections,
                       sniff_format, table_rows)

TOP_K = 3


def _fixtures(root: Path) -> Path:
    """两个「扩展名与真实格式对不上」的夹具。**现造、跑完删**，仓库里不留二进制。"""
    import fitz                                        # noqa: PLC0415

    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 90), "知舟季度报告", fontname="china-s", fontsize=11)
    doc.save(root / "报告.txt")                        # 真 PDF，后缀是 .txt
    doc.close()
    (root / "页面.md").write_text(                     # 真 HTML，后缀是 .md
        "<!DOCTYPE html><html><head><title>值班说明</title>"
        "<script>var x=1;</script></head><body><p>P0 十五分钟。</p></body></html>",
        encoding="utf-8")
    return root


# ---------------------------------------------------------------- 一、格式检测

def test_魔数不听扩展名() -> None:
    """**这一条是本章入口的全部意义。** 扩展名是给人看的，可以被随手改；
    魔数不会——`%PDF-` 就是 `%PDF-`。两个夹具都是「后缀骗人」的例子。"""
    with tempfile.TemporaryDirectory() as tmp:
        root = _fixtures(Path(tmp))
        assert sniff_format(root / "报告.txt") == "pdf", "真 PDF 存成 .txt，仍要判成 pdf"
        assert sniff_format(root / "页面.md") == "html", "内容是 HTML，判成 html 而不是 md"


def test_按魔数路由才读得对() -> None:
    """判对了格式，解析结果才不是乱码：PDF 那一路抽出的是正文，
    HTML 那一路把 `<script>` 丢掉、把 `<title>` 当标题。"""
    with tempfile.TemporaryDirectory() as tmp:
        root = _fixtures(Path(tmp))
        pdf_doc = load_document(root / "报告.txt")
        assert "知舟季度报告" in pdf_doc.text, "按 PDF 解析才抽得出正文"
        assert "%PDF" not in pdf_doc.text and "PK" not in pdf_doc.text, "不是二进制照搬"
        assert pdf_doc.text.startswith("<!-- p."), "PDF 要留页码锚点（引用要能指到页）"
        html_doc = load_document(root / "页面.md")
        assert html_doc.title == "值班说明"
        assert "var x" not in html_doc.text, "脚本必须被丢掉"
        assert "P0 十五分钟。" in html_doc.text


def test_csv_判定要求列数一致() -> None:
    """只凭「有逗号」会把中文正文判成表格——正文里逗号满地都是。"""
    assert sniff_format.__module__                          # 占位：真判据在 _looks_like_csv
    from app.split import _looks_like_csv                   # noqa: PLC0415
    assert _looks_like_csv("服务商,限额,备注\n甲,1,主\n乙,2,备\n")
    assert not _looks_like_csv("这是一句普通的中文，里面有一个逗号。\n再来一行，也有逗号。\n")
    assert not _looks_like_csv("只有一行,没有第二行")


# ---------------------------------------------------------------- 二、读不出的四种

def test_四种读不出分开报() -> None:
    """「需要密码」「需要 OCR」「太大」「没有解析器」是四件不同的事。
    合成一个 `Exception` 就会让人去修错地方——这是本章的一条读法纪律。"""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        import fitz                                        # noqa: PLC0415

        locked = fitz.open()
        p = locked.new_page()
        p.insert_text((72, 90), "内部资料", fontname="china-s", fontsize=11)
        locked.save(root / "locked.pdf", encryption=fitz.PDF_ENCRYPT_AES_256,
                    owner_pw="o", user_pw="pw123")
        locked.close()

        try:
            load_document(root / "locked.pdf", passwords=("", "123456"))
        except Locked:
            pass
        else:
            raise AssertionError("加密件必须抛 Locked")
        assert load_document(root / "locked.pdf", passwords=("pw123",)).text.strip(), \
            "密码对了就该读得出来"

        # 扫描件：整页只有图，没有文本层
        scanned = fitz.open()
        sp = scanned.new_page()
        from PIL import Image                              # noqa: PLC0415
        buf = io.BytesIO()
        Image.new("RGB", (80, 40), "white").save(buf, format="PNG")
        sp.insert_image(fitz.Rect(40, 40, 200, 120), stream=buf.getvalue())
        scanned.save(root / "扫描件.pdf")
        scanned.close()
        try:
            load_document(root / "扫描件.pdf")
        except Unsupported as exc:
            assert "OCR" in str(exc), "扫描件要说清它缺的是 OCR 管道，不是解析器"
        else:
            raise AssertionError("没有文本层必须抛 Unsupported，而不是交一份空文档")

        # 超大：把上限压到 1 字节
        (root / "小.md").write_text("# 标题\n正文\n", encoding="utf-8")
        try:
            load_document(root / "小.md", max_mb=0.0000001)
        except Unsupported as exc:
            assert "超过上限" in str(exc)
        else:
            raise AssertionError("超限必须拒收并说清多大")


def test_图片缺_OCR_引擎是_Unsupported() -> None:
    """本机没有 OCR 引擎，这一路是真的走不通——**不许兜底成空文档**：
    那等于把「这份资料没进来」藏起来。"""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        from PIL import Image                              # noqa: PLC0415
        Image.new("RGB", (40, 20), "white").save(root / "截图.png")
        try:
            load_document(root / "截图.png")
        except Unsupported as exc:
            assert exc.lib, "要说清缺的是哪个库"
        else:
            raise AssertionError("没有引擎就该抛 Unsupported")


# ---------------------------------------------------------------- 三、清洗

def test_清洗五步各治一种噪声() -> None:
    dirty = "标题\x00\n第一页\n１．全角\n①圈码\n\n\n\n正文\n"
    out = clean_text(dirty)
    assert "\x00" not in out, "控制字符要删"
    assert "第一页" not in out, "页码行要删（**中文数字也要认**，只写 \\d 会整行留着）"
    assert "1.全角" in out, "NFKC 要把全角数字与句点折半角"
    assert "1圈码" in out, "NFKC 要把圈码折成数字"
    assert "\n\n\n" not in out, "连续空行压成一个"


def test_页码开关能关() -> None:
    """法规、合同里的编号小节号常常正好是「一行一个数字」——
    无条件删会删掉真实内容，所以它必须是可关的参数。"""
    text = "第一条\n1\n第二条\n"
    assert "1" not in clean_text(text).split("\n"), "默认删"
    assert "1" in clean_text(text, drop_page_numbers=False).split("\n"), "关掉就留着"


def test_替换字符谁都带不走() -> None:
    """**这一条是清洗那一节最值钱的断言。** `U+FFFD` 的字符类别是「符号」，
    与普通字一样合法，五条规则里没有一条碰得到它——
    所以「乱码比高」的正确处置是回去修编码，不是清洗。"""
    text = "正文里有一个坏字\ufffd在这里。"
    out = clean_text(text)
    assert "\ufffd" in out, "清洗不该（也做不到）把它删掉"


def test_乱码比不把换行算进去() -> None:
    """`\\n` 与 `\\t` 也是 `Cc`。不排掉的话，每一份多行文本都自带假乱码率。"""
    assert garbled_ratio("第一行\n第二行\n第三行\n") == 0.0
    assert garbled_ratio("坏\ufffd字") > 0


def test_质量报告的四个数() -> None:
    q = quality("知舟发布规范\n第二行\n")
    assert q["chars"] == 11 and q["garbled"] == 0.0, q
    assert q["han_ratio"] == 0.8182 and q["avg_line"] == 3.7, q


# ---------------------------------------------------------------- 四、切法的参数

def test_参数边界必须报错() -> None:
    """`overlap >= size` 会让步长为 0，切片循环永远不前进——
    这一类错在 Python 里不报错，只挂住，所以必须自己拦。"""
    cases = (lambda: chunk_sliding("甲" * 100, size=50, overlap=50),
             lambda: chunk_sliding("甲" * 100, size=50, overlap=-1),
             lambda: chunk_recursive("甲" * 100, size=0))
    for fn in cases:
        try:
            fn()
        except ValueError:
            continue
        raise AssertionError("参数非法必须抛 ValueError")


def test_重叠真的发生了() -> None:
    """重叠是「回退前一片的尾巴」，所以相邻两片的尾／首必须**逐字相同**。"""
    text = "甲" * 200
    parts = chunk_sliding(text, size=60, overlap=20)
    assert len(parts) >= 3
    for a, b in zip(parts, parts[1:]):
        assert a[-20:] == b[:20], "片尾要原样出现在下一片开头"
    assert len(chunk_sliding(text, size=60, overlap=0)) < len(parts), "有重叠片数必更多"


def test_递归切分不超上限且落在句号后() -> None:
    text = "第一句话。第二句话。第三句话。第四句话。第五句话。第六句话。"
    parts = chunk_recursive(text, size=12, overlap=0)
    assert all(len(p) <= 12 for p in parts), [len(p) for p in parts]
    assert all(p.endswith("。") for p in parts[:-1]), "切点该落在句号之后"


def test_每一片都是原文的连续子串() -> None:
    """**这条不变式是拿真事故换来的。** 第一版 `_split_units` 开头写了一句 `strip()`，
    把分隔符吃了：「…方言；\n」与「2. …」两片重新拼成了「…方言；2. …」，
    换行没了、半句话合成了片。它不报错，只是让检索的字面重合变差。
    子串性是可机检的，所以它该进测试，而不是进注释。"""
    for d in load_corpus():
        for size in (120, 200, 300):
            for p in chunk_recursive(d.text, size=size, overlap=0):
                assert p in d.text, f"{d.doc_id} size={size} 的片不是原文子串：{p[:40]!r}"


def test_定长切分会切坏表格而结构感知不会() -> None:
    """**这是「均匀度不能单独选切法」的证据。** 定长切分天生均匀，
    而它会把表格拦腰切断；结构感知切分片长不齐，却一片也不切坏。"""
    docs = load_corpus()
    small = tuple(Piece(d.doc_id, 0, t)
                  for d in docs for t in chunk_sliding(d.text, size=120, overlap=30))
    good = tuple(p for d in docs for p in chunk_sections(d, size=300, overlap=60))
    assert broken_tables(small), "定长 120 一定会切坏表格（判据本身在守）"
    assert broken_tables(good) == (), "结构感知一片都不该切坏"
    assert table_rows(good[0].text) or table_rows(good[1].text), "语料里确实有表格"


# ---------------------------------------------------------------- 五、sections 的语义

def test_标题路径是父_子() -> None:
    doc = next(d for d in load_corpus() if d.doc_id == "发布规范")
    heads = [s.heading for s in sections(doc)]
    assert heads == ["知舟发布规范 › 发布说明必须包含的四段",
                     "知舟发布规范 › 字数与三态"], heads


def test_标题不进正文() -> None:
    """与 5.1 同一条纪律：标题留在正文里会让「标题命中」被算成「正文命中」。"""
    good = tuple(p for d in load_corpus() for p in chunk_sections(d))
    assert not any(p.text.lstrip().startswith("#") for p in good)


def test_没有标题的文档退化成整体一节() -> None:
    """**说清这一代的代价**：没有标题就没有增益，它退化成普通切分。"""
    from app.corpus import Doc                         # noqa: PLC0415
    doc = Doc("x", "x", "没有任何标题的一段正文。\n\n第二段。", Path("x.md"))
    secs = sections(doc)
    assert len(secs) == 1 and secs[0].heading == ""


# ---------------------------------------------------------------- 六、回归门

def _rank_of(strategy: str) -> int:
    """同一个问题，看装着「回滚」的那一片在第几位。`strategy` 只有两种：旧、新。"""
    docs = load_corpus()
    if strategy == "paragraph":
        pieces = tuple(Piece(c.doc_id, c.index, c.text)
                       for d in docs for c in split_paragraphs(d))
    else:
        pieces = tuple(p for d in docs for p in chunk_sections(d))
    index = NgramIndex(tuple(p.as_chunk() for p in pieces))
    ranked = index.search(by_id("Q1").text, k=len(index.chunks))
    return next(i for i, (c, _) in enumerate(ranked, start=1) if "回滚" in c.text)


def test_回归门_空行切分把答案片放到第五() -> None:
    """**基线，钉住不动。** 5.1 量到的就是这个数（`tests/test_why_rag.py` 里也有一条）。
    它必须留着：没有基线，「新切法更好」这句话就没有对照。"""
    assert _rank_of("paragraph") == 5


def test_回归门_结构感知把答案片放回第一() -> None:
    """本章的交付。哪天有人把 `sections` 改坏（比如把引子与条目又拆开），这条会先喊。"""
    assert _rank_of("sections") == 1


def test_结构感知的这一代只在有结构的语料上成立() -> None:
    """把结论限定在语料上：六份文档都有标题、都很短。
    这不是一句免责，它是这一代**唯一的适用条件**。"""
    docs = load_corpus()
    assert len(docs) == 6
    assert all(len(list(sections(d))) >= 2 for d in docs), "每份都得有两节以上"


# ---------------------------------------------------------------- 七、父子片

def test_父子片两层各司其职() -> None:
    """子片短、参与检索；父片长、只存不检索。子片必须都能在父片里找到。"""
    doc = next(d for d in load_corpus() if d.doc_id == "接入清单")
    parents, children = chunk_parent_child(doc, parent=300, child=100, overlap=20)
    assert len(parents) == 2 and len(children) == 4
    for c in children:
        owner = c.doc_id.split("#p")[0]
        assert owner == doc.doc_id
        assert any(c.text in p.text for p in parents), f"子片 {c.index} 不在任何父片里"
    assert sum(len(p.text) for p in parents) > len(doc.text) * 0.8


def test_块长统计的三个数() -> None:
    st = piece_stats((Piece("x", 0, "甲" * 100), Piece("x", 1, "乙" * 200)))
    assert st["count"] == 2 and st["avg"] == 150.0
    assert st["uniformity"] < 1.0, "长度不齐时均匀度必小于 1"


# ---------------------------------------------------------------- 八、端到端

def test_离线脚本跑通并打印读数() -> None:
    """把脚本当门跑一遍：正文引用的每一行读数都必须在里面。"""
    import subprocess
    proc = subprocess.run([sys.executable, "scripts/split_reader.py", "--offline"], cwd=ROOT,
                          capture_output=True, text=True, encoding="utf-8", timeout=300)
    assert proc.returncode == 0, proc.stderr[-400:]
    out = proc.stdout
    assert "离线自检通过" in out
    assert "→ 判为 pdf" in out and "→ 判为 html" in out
    assert "paragraph" in out and "第 5 位" in out and "第 1 位" in out
    assert "291.5%" in out, "重叠的账要印出来"
    assert "一个也没少" in out, "替换字符那条断言要印出来"


def test_自检夹具全绿() -> None:
    import subprocess
    proc = subprocess.run([sys.executable, "scripts/split_reader.py", "--self-test"], cwd=ROOT,
                          capture_output=True, text=True, encoding="utf-8", timeout=120)
    assert proc.returncode == 0, proc.stdout[-400:]
    assert "自检 6/6 通过" in proc.stdout


def run() -> int:
    """不依赖 pytest 的跑法：`python tests/test_split.py`。"""
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    bad = 0
    for fn in fns:
        try:
            fn()
            print(f"  ✔ {fn.__name__}")
        except Exception as exc:                                   # noqa: BLE001
            bad += 1
            print(f"  ✖ {fn.__name__}｜{type(exc).__name__}: {exc}")
    print(f"\n{len(fns) - bad}/{len(fns)} 通过")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(run())
