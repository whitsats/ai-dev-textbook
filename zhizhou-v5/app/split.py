"""v5 的第二段增量：把「读进来」从「六个 .md」扩到「五花八门的文件」，并把切法换掉。

5.1 的 `corpus.split_paragraphs` 是**故意的笨切法**（按空行切），它留下了一条实测读数：
「答案片排第 5」——`发布规范#0`（一句引子）拿 19.79 分，而装着「回滚」的
`发布规范#1`（四条目）只有 1.40 分。**检索没错，错的是那句话被切成了两片**，
而提问那半句落在前一片上。这一章就是来换掉它的。

模块分三段，顺序与正文一致：

1. **入口**：格式检测（看魔数，不看扩展名）→ 路由到解析器 → 清洗；
2. **切分**：四代切法（定长 / 滑动 / 递归 / 结构感知）＋ 父子片，
   它们都能在**同一份语料**上跑，这样第 3 段的读数才是一次对照；
3. **读数**：`scripts/split_reader.py` 把每一代的召回与块长分布量出来。

一条纪律沿用 5.1：**离线这一侧只用标准库就能跑**。需要第三方库的解析器
（PDF / Word / PPT / OCR）做成**可选适配器**：库不在时抛 `Unsupported` 并说清缺哪一个，
而不是让 `ImportError` 冒到用户脸上——离线读数不依赖它们，也不该被它们挡住。
"""
from __future__ import annotations

import csv
import html.parser
import io
import re
import unicodedata
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from app.corpus import Chunk, Doc, NgramIndex, CORPUS_DIR, load_corpus, split_paragraphs

#: 单文件大小上限（MB）。超过就拒收并说清大小——不是「读着试试看」。
MAX_MB = 50.0

#: 魔数表。**只看开头几个字节，不看文件名。** 扩展名是给人看的，魔数是给解析器看的：
#: 前者可以被随手改名（实测：把一份真 PDF 存成 `report.txt` 是合法的），
#: 后者不会——`%PDF-` 就是 `%PDF-`。
MAGIC: tuple[tuple[bytes, str], ...] = (
    (b"%PDF-", "pdf"),
    (b"\x89PNG\r\n\x1a\n", "png"),
    (b"\xff\xd8\xff", "jpg"),
    (b"PK\x03\x04", "zip"),
)

#: ZIP 容器里有三种我们要区分的 Office 格式，靠**包内路径**分：
#: 只看魔数只能知道「这是个 zip」，而 `.docx`／`.pptx`／`.xlsx` 三者同宗。
_ZIP_KIND: tuple[tuple[str, str], ...] = (
    ("word/document.xml", "docx"),
    ("ppt/presentation.xml", "pptx"),
    ("xl/workbook.xml", "xlsx"),
)

#: 文本文件之间靠**内容特征**分，不靠后缀。顺序有意义：先判最具体的。
#: CSV 判定不能只看「有逗号」——中文正文里的顿号、列举句都有逗号，
#: 所以它要求「**大多数非空行都是同列数的逗号分隔行**」（见 `_looks_like_csv`）。
_TEXT_KIND: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"^\s*(<!DOCTYPE html|<html)", re.I), "html"),
    (re.compile(r"^#{1,6}\s", re.M), "md"),
)

#: 递归切分的分隔符级联：从「最像段落边界」到「最像词边界」。
#: 中文的句子边界是 `。！？；`，这是**必须自己列**的——
#: LangChain 的默认分隔符是给英文准备的（`\n\n`、`\n`、` `），
#: 中文文本里没有空格，它会一路退到按字切。
SEPARATORS: tuple[str, ...] = ("\n\n", "\n", "。", "！", "？", "；", "，", "、", " ")


class Unsupported(RuntimeError):
    """这类文件读不了，而且**能说清为什么**。`lib` 缺哪个库就报哪个库。"""

    def __init__(self, fmt: str, why: str, lib: str = ""):
        self.fmt, self.why, self.lib = fmt, why, lib
        super().__init__(f"{fmt}：{why}" + (f"（需要 {lib}）" if lib else ""))


class Locked(RuntimeError):
    """加密且密码不对。**与「解析失败」分开**：它需要的是密码，不是换解析器。"""

    def __init__(self, path: Path, tried: int):
        self.path, self.tried = path, tried
        super().__init__(f"{path.name} 已加密，试了 {tried} 个密码都打不开")


# --------------------------------------------------------------------------- ① 入口

def sniff_format(path: Path) -> str:
    """按**魔数**判格式。返回 `pdf`／`png`／`jpg`／`docx`／`pptx`／`xlsx`／
    `html`／`md`／`csv`／`txt`／`unknown`。

    两条与「按扩展名判」不同的行为，都是这一章要量出来的：

    - 一份**真 PDF 改名成 `.txt`**，这里照样判出 `pdf`；
    - 一个 `.md` 文件里装的是 HTML，这里判出 `html`——**内容说了算**。
    """
    head = path.read_bytes()[:16]
    for sig, fmt in MAGIC:
        if head.startswith(sig):
            return _zip_kind(path) if fmt == "zip" else fmt
    return _text_kind(path)


def _zip_kind(path: Path) -> str:
    """ZIP 容器里到底是 docx、pptx 还是 xlsx。不是 Office 就返回 `zip`。"""
    try:
        with zipfile.ZipFile(path) as z:
            names = set(z.namelist())
    except (zipfile.BadZipFile, OSError):
        return "zip"
    for member, fmt in _ZIP_KIND:
        if member in names:
            return fmt
    return "zip"


def _text_kind(path: Path) -> str:
    """文本文件之间怎么分：先解码，再看内容特征，最后才看后缀。

    解码本身也是检测：二进制文件在这��会解不出来，于是判 `unknown`——
    这比「按后缀当文本读，读到一半抛 UnicodeDecodeError」要在前面一步就分清楚。
    """
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        try:
            text = raw.decode("gb18030")     # 中文环境里的另一种常见编码
        except UnicodeDecodeError:
            return "unknown"
    for pattern, fmt in _TEXT_KIND:
        if pattern.search(text):
            return fmt
    return "csv" if _looks_like_csv(text) else "txt"


def _looks_like_csv(text: str) -> bool:
    """像不像 CSV：**至少两行、每行都含逗号、且列数一致**。

    判据故意写紧：中文正文里逗号满地都是，只看「有逗号」会把普通文本判成表格。
    要的是「这是一张表」的证据——列数一致才算。
    """
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if len(lines) < 2:
        return False
    widths = {ln.count(",") for ln in lines}
    return len(widths) == 1 and widths.pop() >= 1


#: 一行只有页码的噪声。PDF 抽取出来的文本里最常见的一种脏东西。
#: **阿拉伯数字与中文数字都要认**：实测里 `第一页` 这种形式一样常见，
#: 只写 `\d` 的话它会整行留着——而且清洗完看起来「已经干净了」，最难发现。
#: 代价也要知道：一行只有 `1` 的小节号会被它误删，所以它是个可关的开关。
_PAGE_NUMBER = re.compile(
    r"^\s*(?:第\s*)?[0-9一二三四五六七八九十百]{1,4}\s*(?:页|/\s*[0-9]{1,4})?\s*$")


def clean_text(text: str, *, drop_page_numbers: bool = True) -> str:
    """清洗：**顺序不能换**。四步各有它负责的脏东西，换顺序就会有一步白做：

    1. 去掉控制字符（`\\x00`–`\\x1f` 里除 `\\n\\t` 之外的）；
    2. NFKC 规范化——全角字母、全角数字、`①②③` 这类序号在这一步对齐；
    3. 全角空格与不换行空格回正——它们在 `split()` 眼里不是空白；
    4. 连续空行压成一个空行，行尾空白去掉。

    页码行单独一步：它只在 `drop_page_numbers=True` 时删，因为**它长得太像正常内容**
    （一行里只有一个数字），在有编号的文档里会误删真实的小节号。
    """
    text = "".join(ch for ch in text if ch == "\n" or ch == "\t" or unicodedata.category(ch)[0] != "C")
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\u3000", " ").replace("\u00a0", " ")
    lines = [ln.rstrip() for ln in text.splitlines()]
    if drop_page_numbers:
        lines = [ln for ln in lines if not _PAGE_NUMBER.match(ln)]
    out, blank = [], 0
    for ln in lines:
        if ln.strip():
            blank = 0
            out.append(ln)
        elif blank == 0:
            blank = 1
            out.append("")
    return "\n".join(out).strip()


def garbled_ratio(text: str) -> float:
    """乱码比：**控制字符 ＋ 替换字符 ＋ 私用区**占前 1000 字的比例。

    为什么是这三类：OCR 出来的乱码最常落在这三处。替换字符 `U+FFFD` 是解码失败留的，
    私用区（`U+E000`–`U+F8FF`）是字体映射错了的结果——正常中文文本里它们一个都不该有。
    """
    head = text[:1000]
    if not head:
        return 0.0
    # `\n` 与 `\t` 也是 `Cc`，但它们**不是乱码**——不排掉的话，
    # 每一份多行文本都会自带一个 5%–10% 的乱码比，这个指标就废了。
    odd = sum(1 for ch in head
              if (ch not in "\n\t" and unicodedata.category(ch) == "Cc")
              or ch == "\ufffd" or "\ue000" <= ch <= "\uf8ff")
    return round(odd / len(head), 4)


def quality(text: str) -> dict:
    """一份文本的质量报告。**这四个数是「要不要人工抽查」的依据，不是结论。**"""
    n = len(text) or 1
    return {
        "chars": len(text),
        "han_ratio": round(sum(1 for c in text if "\u4e00" <= c <= "\u9fff") / n, 4),
        "garbled": garbled_ratio(text),
        "avg_line": round(n / (text.count("\n") + 1), 1),
    }


# --------------------------------------------------------------------------- 解析器

def parse_text(path: Path) -> Doc:
    """纯文本（含 Markdown）。**先解码再看格式**，所以编码错在这里就该暴露。"""
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("gb18030")
    return Doc(doc_id=path.stem, title=_first_title(text) or path.stem, text=text, path=path)


class _TagStripper(html.parser.HTMLParser):
    """只用标准库的 HTML 取文本：**块级标签换行、其余原样**。

    为什么不直接上 BeautifulSoup：这一层要能在「什么都没装」的环境里跑。
    要按选择器精确取节点时才需要 bs4（`parse_html_soup`），那是加分项，不是前提。
    """

    _BLOCK = {"p", "div", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "pre", "table", "br"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.title = ""
        self._in_title = False
        self._skip = 0

    def handle_starttag(self, tag: str, attrs) -> None:  # noqa: ANN001
        if tag in ("script", "style"):
            self._skip += 1
        elif tag == "title":
            self._in_title = True
        elif tag in self._BLOCK:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:  # noqa: ANN001
        if tag in ("script", "style") and self._skip:
            self._skip -= 1
        elif tag == "title":
            self._in_title = False
        elif tag in self._BLOCK:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip:
            return
        if self._in_title:
            self.title += data.strip()
        else:
            self.parts.append(data)


def parse_html(path: Path) -> Doc:
    """HTML：取正文文本，**丢掉脚本与样式**。"""
    p = _TagStripper()
    p.feed(path.read_text(encoding="utf-8", errors="replace"))
    text = clean_text("".join(p.parts))
    return Doc(doc_id=path.stem, title=p.title or path.stem, text=text, path=path)


def parse_csv(path: Path) -> Doc:
    """CSV／表格：**每一行变成一段 `列名：值`**。

    为什么不直接拼成一行：一行一个记录，切分时才可能按记录切开——
    拼成一长行的话，定长切分一定会把某条记录拦腰切断，而那正是表格类文档最怕的事。
    """
    raw = path.read_bytes()
    text = raw.decode("utf-8", errors="replace")
    rows = list(csv.reader(io.StringIO(text)))
    if not rows:
        return Doc(doc_id=path.stem, title=path.stem, text="", path=path)
    head = [c.strip() for c in rows[0]]
    body = []
    for row in rows[1:]:
        cells = [c.strip() for c in row]
        if not any(cells):
            continue
        pairs = [f"{h}：{v}" for h, v in zip(head, cells) if v != ""]
        body.append("# " + (cells[0] or path.stem) + "\n" + "\n".join(pairs))
    return Doc(doc_id=path.stem, title=head[0] if head else path.stem,
               text=clean_text("\n\n".join(body)), path=path)


def parse_markdown(path: Path) -> Doc:
    """Markdown：**正文原样留着**，因为标题层级是切分要用的结构（见 `sections`）。"""
    return parse_text(path)


def parse_pdf(path: Path, *, passwords: tuple[str, ...] = ()) -> Doc:
    """PDF：PyMuPDF 逐页抽文本。**表格与图片要另配解析器**（本节末尾会讲为什么不合并）。

    加密件的处理是「先试密码，再决定」：`needs_pass` 为真时逐个 `authenticate`，
    全试不通才抛 `Locked`——`Locked` 与 `Unsupported` 是两件事，
    前者要的是密码，后者要的是换解析器，混成一个异常就会让人去修错地方。
    """
    try:
        import fitz                       # noqa: PLC0415
    except ImportError as exc:
        raise Unsupported("pdf", "PyMuPDF 不在", "PyMuPDF") from exc
    doc = fitz.open(path)
    if doc.needs_pass:
        if not any(doc.authenticate(pw) for pw in passwords):
            doc.close()
            raise Locked(path, len(passwords))
    pages = []
    for i, page in enumerate(doc, start=1):
        text = page.get_text("text").strip()
        if text:
            pages.append(f"<!-- p.{i} -->\n{text}")
    total_pages = len(doc)
    doc.close()
    if not pages:
        # **没有文本层 ≠ 解析失败。** 它是「这份文件需要 OCR 管道」——
        # 两件事的处置完全不同（换解析器 vs 补一条 OCR 工序），所以异常也要分开。
        raise Unsupported("pdf", f"{total_pages} 页全部没有文本层，是扫描件，需要 OCR 管道",
                          "paddleocr 或 pytesseract")
    return Doc(doc_id=path.stem, title=path.stem,
               text=clean_text("\n\n".join(pages)), path=path)


def parse_docx(path: Path) -> Doc:
    """Word：**用标题样式换出 `#` 层级**，后面的切分逻辑因此不用为 docx 写分支。"""
    try:
        from docx import Document as _Docx   # noqa: PLC0415
    except ImportError as exc:
        raise Unsupported("docx", "python-docx 不在", "python-docx") from exc
    d = _Docx(str(path))
    out = []
    for para in d.paragraphs:
        text = para.text.strip()
        if not text:
            continue
        style = (para.style.name or "").lower()
        if style.startswith("heading"):
            tail = style.split()[-1]
            level = int(tail) if tail.isdigit() else 1
            out.append("#" * min(level, 6) + " " + text)
        else:
            out.append(text)
    for table in d.tables:
        rows = [[cell.text.strip() for cell in row.cells] for row in table.rows]
        out.append(_rows_to_markdown(rows))
    return Doc(doc_id=path.stem, title=path.stem,
               text=clean_text("\n\n".join(x for x in out if x)), path=path)


def parse_pptx(path: Path) -> Doc:
    """PPT：一张幻灯片一节（标题取第一个文本框），**备注页也算正文**——
    讲解要点常常只写在备注里。"""
    try:
        from pptx import Presentation      # noqa: PLC0415
    except ImportError as exc:
        raise Unsupported("pptx", "python-pptx 不在", "python-pptx") from exc
    prs = Presentation(str(path))
    out = []
    for i, slide in enumerate(prs.slides, start=1):
        texts = [s.text_frame.text.strip() for s in slide.shapes
                 if s.has_text_frame and s.text_frame.text.strip()]
        title = texts[0] if texts else f"幻灯片 {i}"
        body = texts[1:]
        if slide.has_notes_slide:
            note = slide.notes_slide.notes_text_frame.text.strip()
            if note:
                body.append(f"备注：{note}")
        out.append(f"# {title}\n\n" + "\n".join(body))
    return Doc(doc_id=path.stem, title=path.stem,
               text=clean_text("\n\n".join(out)), path=path)


def parse_image(path: Path) -> Doc:
    """图片 OCR。**本机两个引擎都没装，所以这里是真的 `Unsupported`**（见读数 ①）。

    这一条不做「猜一个结果」的兜底：OCR 读不出来就是读不出来，
    硬拼一个空文档进索引，等于把「这份资料没进来」这件事藏起来。

    「没有引擎」有两种形态，**要归到同一档**，因为对读者来说修法是同一条：
      · **壳不在**：`import pytesseract` 就失败（本机）；
      · **壳在、引擎不在**：包装装上了，而系统里没有 `tesseract` 二进制
        （CI 上正是这一种：requirements 装了它，runner 里没有那个二进制）。
    第二种只有**真去问引擎一次**才会露出来——`import` 成功不等于引擎在。
    文案两条完全一致：两边都归 Unsupported，差别只在日志里说得清缺的是什么，
    而给读者的修法就是「两样都装上」，那就没必要分成两种说法。
    """
    try:
        import pytesseract                  # noqa: PLC0415
        from PIL import Image               # noqa: PLC0415
    except ImportError as exc:
        raise Unsupported("image", "OCR 引擎不在", "pytesseract ＋ Pillow") from exc
    try:
        pytesseract.get_tesseract_version()  # 壳在？再问一句引擎在不在
    except pytesseract.TesseractNotFoundError as exc:
        raise Unsupported("image", "OCR 引擎不在", "pytesseract ＋ Pillow") from exc
    text = pytesseract.image_to_string(Image.open(path), lang="chi_sim+eng")
    return Doc(doc_id=path.stem, title=path.stem, text=clean_text(text), path=path)


def _rows_to_markdown(rows: list[list[str]]) -> str:
    """把二维表拼成 Markdown 表。**空行要补**，否则列会错位。"""
    rows = [r for r in rows if any(c for c in r)]
    if not rows:
        return ""
    width = max(len(r) for r in rows)
    fixed = [r + [""] * (width - len(r)) for r in rows]
    head, *body = fixed
    lines = ["| " + " | ".join(head) + " |",
             "| " + " | ".join(["---"] * width) + " |"]
    lines += ["| " + " | ".join(r) + " |" for r in body]
    return "\n".join(lines)


#: 格式 → 解析器。**这张表是路由的全部**：加一种格式＝加一行，
#: 而不是在 `load_document` 里加一个 `elif`。
PARSERS: dict[str, Callable[[Path], Doc]] = {
    "md": parse_markdown,
    "txt": parse_text,
    "csv": parse_csv,
    "html": parse_html,
    "pdf": parse_pdf,
    "docx": parse_docx,
    "pptx": parse_pptx,
    "png": parse_image,
    "jpg": parse_image,
}


def load_document(path: Path, *, passwords: tuple[str, ...] = (),
                  max_mb: float = MAX_MB) -> Doc:
    """一个文件 → 一份 `Doc`。三步：**大小 → 格式 → 路由**。

    第三步的 `except Unsupported` 是故意放出去的：这一层不吞异常，
    但也不猜格式。`load_directory` 才负责把「读不了」记成一条结果。
    """
    size_mb = path.stat().st_size / 1024 / 1024
    if size_mb > max_mb:
        raise Unsupported(path.suffix.lower() or "unknown",
                          f"文件 {size_mb:.1f}MB 超过上限 {max_mb:g}MB", "")
    fmt = sniff_format(path)
    parser = PARSERS.get(fmt)
    if parser is None:
        raise Unsupported(fmt, "没有注册解析器", "")
    if fmt == "pdf":
        return parse_pdf(path, passwords=passwords)
    return parser(path)


def load_directory(root: Path, *, passwords: tuple[str, ...] = ()) -> tuple[Doc, ...]:
    """一个目录 → 一批 `Doc`。**读不了的记在案上，不中断**：一批几百份文件里
    坏一份就把整批停下，是这一层最容易犯的错。顺序按文件名排序，保证可复现。"""
    docs = []
    for p in sorted(root.rglob("*")):
        if p.is_file():
            docs.append(load_document(p, passwords=passwords))
    return tuple(docs)


def _first_title(text: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return ""


# --------------------------------------------------------------------------- ② 切分

@dataclass(frozen=True)
class Section:
    """一节：**标题路径 ＋ 正文**。标题进 `heading` 而不进 `text`。

    这一条沿用 5.1 的纪律，而且它有个更容易被忽略的后果：如果标题留在正文里，
    问「发布说明要写几段」会把**标题那一行**召回，看起来是命中、实际是标题自证，
    召回率虚高。标题是**元数据**，它的用途是过滤与展示，不是打分。
    """

    doc_id: str
    heading: str
    text: str


@dataclass(frozen=True)
class Piece:
    """待入库的一片。比 `corpus.Chunk` 多一个 `heading`——
    结构感知切分是唯一知道「这一片属于哪一节」的那一代。"""

    doc_id: str
    index: int
    text: str
    heading: str = ""

    def as_chunk(self) -> Chunk:
        """换成检索层认的形状（`NgramIndex` 只认 `Chunk`）。"""
        return Chunk(doc_id=self.doc_id, index=self.index, text=self.text)


_HEADING = re.compile(r"^(#{1,6})\s+(.*)$")


def sections(doc: Doc) -> tuple[Section, ...]:
    """按标题切节，**返回标题路径**（`父 › 子`）。没有标题的文档整体算一节。

    没标题时不是「切不出来」，而是「这份文档没有可用的结构」——
    它照样能被切，只是退化成第 1 段那一种。
    """
    out: list[Section] = []
    stack: list[str] = []      # 当前标题路径：`del stack[level-1:]` 保证同级互相顶掉
    buf: list[str] = []
    have_head = False

    def flush() -> None:
        body = "\n".join(buf).strip()
        if body:
            out.append(Section(doc.doc_id, " › ".join(stack), body))

    for line in doc.text.splitlines():
        m = _HEADING.match(line)
        if m:
            flush()
            buf.clear()
            level, title = len(m.group(1)), m.group(2).strip()
            del stack[level - 1:]
            stack.append(title)
            have_head = True
        else:
            buf.append(line)
    flush()
    if not out and not have_head:
        return (Section(doc.doc_id, "", clean_text(doc.text)),)
    return tuple(out)


def chunk_fixed(text: str, *, size: int = 300) -> tuple[str, ...]:
    """第 1 代：**每 `size` 个字一刀**。最快，也最不讲道理——

    它会在句子中间、表格中间、代码中间切，切完还看不出来（片与片之间没有标记）。
    留着它不是为了用，是为了当对照：后面三代都要跟它比。
    """
    if size <= 0:
        raise ValueError("size 必须为正")
    return tuple(text[i:i + size] for i in range(0, len(text), size))


def chunk_sliding(text: str, *, size: int = 300, overlap: int = 60) -> tuple[str, ...]:
    """第 2 代：**带重叠的定长**。重叠是为了让「被切断的那句话」在相邻两片里各出现一次。

    它的代价是**指数级的冗余**：重叠 60／片长 300 就是 20% 的重复入库，
    检索时相邻两片常常一起进提示，等于把同一个证据说两遍。
    `overlap >= size` 会让步长为 0，直接死循环——所以这里显式挡掉。
    """
    if size <= 0:
        raise ValueError("size 必须为正")
    if not 0 <= overlap < size:
        raise ValueError(f"overlap 必须在 [0, size) 内，实得 {overlap}")
    step = size - overlap
    return tuple(text[i:i + size] for i in range(0, len(text), step))


def chunk_recursive(text: str, *, size: int = 300, overlap: int = 60,
                    separators: tuple[str, ...] = SEPARATORS) -> tuple[str, ...]:
    """第 3 代：**按分隔符级联切**——先用最像段落边界的分隔符切，
    仍然超长才退到下一级。这是「尽量在语义边界落刀」的最低成本做法。

    实现有两点值得说：

    1. 递归的终止不是「切到够短」，而是「**分隔符用完了**」——
       分隔符表里最后一项是 `" "`，到那时候只能按字符硬切（Python 里没有空串 `split`，
       所以最后一级是切片的循环）；
    2. 重叠是**在拼片时**加的（`_pack` 的 `carry`），不是在递归里加的——
       在递归里加会让每一层各加重叠一次，实测片数会翻倍。
    """
    if size <= 0:
        raise ValueError("size 必须为正")
    if not 0 <= overlap < size:
        raise ValueError(f"overlap 必须在 [0, size) 内，实得 {overlap}")
    units = _split_units(text, size, separators)
    return _pack(units, size, overlap)


def _split_units(text: str, size: int, separators: tuple[str, ...]) -> list[str]:
    """递归到「每一块都不超过 `size`」为止，返回最细的那一层单元。

    这里有一条**必须守住的实现不变式**：把这些单元按顺序拼回去，要能**逐字复原**原文
    （除最外层的空白外）。第一版在函数开头写了一句 `text = text.strip()`，
    于是分隔符被吃掉了："1. …方言；\n" 与 "2. …" 两片被重新拼成 "…方言；2. …"，
    **换行没了，片与片合成了半句话**。它不报错、也看不出来，只是让检索的字面重合变差——
    与 5.1 那条「多行片从第二行起静默丢掉」是同一族：**跨层的格式契约只能写死在一侧。**
    """
    if not text:
        return []
    if len(text) <= size:
        return [text]
    for i, sep in enumerate(separators):
        parts = _split_keep(text, sep)
        if len(parts) <= 1:
            continue
        # 用这一级分隔符切完，任何一块仍然超长，就交给下一级继续拆。
        # **不过滤空白单元**：上一版在这里写了 `if u.strip()`，于是 `"\n\n"`
        # 被拆成 `"\n"` ＋ `"\n"` 时两个都被丢掉，拼回去就少了一个换行——
        # 一段表格与它下面那个标题被粘成了一行。要丢的是「整片都是空白的片」，
        # 那是 `_pack` 收尾的事，不是这里的事。
        rest = separators[i + 1:]
        return [u for p in parts for u in _split_units(p, size, rest)]
    # 分隔符用完了：只能按字符硬切。这里是递归的**唯一出口**，不是兜底——
    # 它会在长表格行、无标点的英文串上被真的走到。
    return [text[i:i + size] for i in range(0, len(text), size)]


def _split_keep(text: str, sep: str) -> list[str]:
    """按分隔符切但**把分隔符留在前一块的尾巴上**——
    中文的 `。` 是句子的收尾，切掉的应该是它**后面**，不是它本身。"""
    if not sep:
        return [text]
    parts = text.split(sep)
    out = [p + sep for p in parts[:-1]]
    if parts[-1]:
        out.append(parts[-1])
    # **这里同样不能过滤空白块。** 上一版写成 `if p.strip()`，
    # 于是一个「两行换行」在换成单行换行时被整个丢掉——
    # 表现是表格最后一行与它下面的标题粘成了一行。丢掉空白块是 `_pack` 收尾的事，
    # `_split_keep` 的职责只有一条：**让拼回去等于原文**。
    return out


def _pack(units: list[str], size: int, overlap: int) -> tuple[str, ...]:
    """把细单元**贪心地装回 `size` 以内**的片，并让相邻两片重叠 `overlap` 个字。

    一条可机检的不变式：**每一片都必须是原文的连续子串**。
    「回退尾巴」这个做法天然满足它（`carry` 是上一片的结尾，接上去仍是一段连续区间）；
    一旦有人在中间插一句“清理一下空白”，这条就断了，而它断了不会报错——
    只会让引用指向一段原文里找不到的文字。测试里有一条守着它。

    重叠的实现是「回退」而不是「复制前缀」：装完一片后，从片尾取 `overlap` 个字
    接到下一片的开头。这样重叠部分**与上一片的结尾逐字相同**，
    检验它是可核对的（读数 ③ 就靠这一点判断重叠有没有真的发生）。
    """
    pieces: list[str] = []
    cur = ""
    for unit in units:
        if cur and len(cur) + len(unit) > size:
            pieces.append(cur)
            carry = cur[-overlap:] if overlap else ""
            cur = carry + unit
        else:
            cur += unit
    pieces.append(cur)
    # **这里不 `strip()`。** 第一版在返回前对每一片做了 `strip()`，
    # 片尾的一个空格被吃掉，于是片不再是原文的子串——
    # 表现是「候选文本在原文里搜不到」，引用回查直接失败。
    # 区分「丢掉空白单元」与「改写留下的片」：前者该丢，后者一个字都不能动。
    return tuple(p for p in pieces if p.strip())


def chunk_sections(doc: Doc, *, size: int = 300, overlap: int = 60) -> tuple[Piece, ...]:
    """第 4 代：**结构感知**——先按标题分节，节内再递归切。

    它治的正是 5.1 留下的那条读数：`发布规范` 的「一句引子 ＋ 四条目」
    本来会被空行切成两片，而提问那半句落在前一片上（答案片排第 5）。
    按节切之后，引子与四条目在同一片里，答案片回到第 1。

    **代价要一起说清**：节的粒度是文档自己定的，作者写一节写了两千字，
    这一片就有两千字（所以要保留 `size` 上限，超长仍然递归切）；
    而对**没有标题**的文档，这一代退化成递归切分，没有任何增益。
    """
    out: list[Piece] = []
    i = 0
    for sec in sections(doc):
        for part in chunk_recursive(sec.text, size=size, overlap=overlap):
            out.append(Piece(sec.doc_id, i, part, sec.heading))
            i += 1
    return tuple(out)


def chunk_parent_child(doc: Doc, *, parent: int = 300, child: int = 100,
                       overlap: int = 20) -> tuple[tuple[Piece, ...], tuple[Piece, ...]]:
    """父子片：**拿子片去检索，把小片换成它所属的父片再交给模型**。

    它治的是这一篇最根本的那对矛盾：检索要小（准），生成要大（全）。
    做法是同一份文本存两遍（父、子各一份索引），检索命中子片后**回查父片**。

    返回 `(parents, children)`：这不是「两种切法选一个」，
    而是**一套要同时入库的两层**——第 5.4 节会把它接进检索。
    """
    parents, children = [], []
    pi = 0
    for sec in sections(doc):
        for ptext in chunk_recursive(sec.text, size=parent, overlap=0):
            p = Piece(sec.doc_id, pi, ptext, sec.heading)
            parents.append(p)
            pi += 1
            for ci, ctext in enumerate(chunk_recursive(ptext, size=child, overlap=overlap)):
                children.append(Piece(f"{sec.doc_id}#p{p.index}", ci, ctext, sec.heading))
    return tuple(parents), tuple(children)


#: 五代切法的名字 → 实现（第 0 代是 5.1 的基线）。
#: **「哪一代更好」不在这张表里**：它是量出来的（读数 ②）。
#: 把基线留在同一张表里，是因为没有基线就没有对照——
#: 「新切法更好」这句话，只有在同一份语料、同一个检索器上跟旧切法比过才算数。
STRATEGIES: dict[str, Callable[..., tuple]] = {
    "paragraph": lambda doc, **kw: tuple(Piece(c.doc_id, c.index, c.text)
                                         for c in split_paragraphs(doc)),
    "fixed": lambda doc, **kw: tuple(Piece(doc.doc_id, i, t)
                                     for i, t in enumerate(chunk_fixed(
                                         doc.text, size=kw.get("size", 300)))),
    "sliding": lambda doc, **kw: tuple(Piece(doc.doc_id, i, t)
                                       for i, t in enumerate(chunk_sliding(
                                           doc.text, size=kw.get("size", 300),
                                           overlap=kw.get("overlap", 60)))),
    "recursive": lambda doc, **kw: tuple(Piece(doc.doc_id, i, t)
                                         for i, t in enumerate(chunk_recursive(
                                             doc.text, size=kw.get("size", 300),
                                             overlap=kw.get("overlap", 60)))),
    "sections": chunk_sections,
}


def split_document(doc: Doc, *, strategy: str = "sections", size: int = 300,
                   overlap: int = 60) -> tuple[Piece, ...]:
    """一句话拿到「一份文档在某一种切法下的所有片」。"""
    if strategy not in STRATEGIES:
        raise KeyError(f"没有这种切法：{strategy}（可选 {sorted(STRATEGIES)}）")
    return STRATEGIES[strategy](doc, size=size, overlap=overlap)


def build_index(*, strategy: str = "sections", size: int = 300, overlap: int = 60,
                root: Path | None = None) -> tuple[NgramIndex, tuple[Doc, ...], tuple[Piece, ...]]:
    """**同一个检索器，换一种切法**——这是本章做对照的全部机关。

    它刻意与 `corpus.build_index`（5.1 那个）并存：那一份是基线，
    改了它，5.1 那一章的读数就不再可复现。**两条路要能同时跑，才叫对照。**
    """
    docs = load_corpus(root or CORPUS_DIR)
    pieces = tuple(p for d in docs
                   for p in split_document(d, strategy=strategy, size=size, overlap=overlap))
    return NgramIndex(tuple(p.as_chunk() for p in pieces)), docs, pieces


#: `count_markdown_tables` 的判定：一行以 `|` 开头算表格行，分隔行 `| --- |` 是表头的一部分。
_TABLE_ROW = re.compile(r"^\s*\|.*\|\s*$")
_TABLE_SEP = re.compile(r"^\s*\|(?:\s*:?-+:?\s*\|)+\s*$")


def table_rows(text: str) -> int:
    """数 Markdown 表格行。用来量「定长切分把表格切成了几段」（读数 ③）。"""
    return sum(1 for ln in text.splitlines() if _TABLE_ROW.match(ln))


def broken_tables(pieces: tuple[Piece, ...]) -> tuple[str, ...]:
    """**被切坏的表格**：一片里有表格行、却没有表头分隔行。

    这条判据只认一种病：一片从表格中间开始。它是可机检的，所以能进测试；
    「表格语义有没有丢」不能机检，那要人看（本节末尾的清单）。
    """
    bad = []
    for p in pieces:
        if table_rows(p.text) and not any(_TABLE_SEP.match(ln) for ln in p.text.splitlines()):
            bad.append(f"{p.doc_id}#{p.index}")
    return tuple(bad)


def piece_stats(pieces: tuple[Piece, ...]) -> dict:
    """块长分布：片数、平均长度、**长度标准差**、均匀度。

    均匀度 `1 / (1 + 标准差 / 均值)` 抄自素材里的那个写法，
    这里保留它并把它标注清楚：**它是块长的一致性，不是语义的一致性。**
    定长切分在这一项上必然接近 1（它天生就均匀），而它恰恰是最会把语义切坏的一代——
    所以这个数**不能单独用来选切法**，这正是读数 ② 要立的那条规矩。
    """
    if not pieces:
        return {"count": 0, "avg": 0.0, "std": 0.0, "uniformity": 0.0}
    lens = [len(p.text) for p in pieces]
    avg = sum(lens) / len(lens)
    var = sum((x - avg) ** 2 for x in lens) / len(lens)
    std = var ** 0.5
    return {"count": len(pieces), "avg": round(avg, 1), "std": round(std, 1),
            "uniformity": round(1 / (1 + std / max(avg, 1e-9)), 3)}
