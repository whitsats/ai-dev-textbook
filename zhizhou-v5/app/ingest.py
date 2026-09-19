"""v5 的第八段增量：**入库**——把「一个目录」变成「一份可检索的知识库」。

前七章的语料是 `corpus/` 里六个 `.md`，一行 `load_corpus()` 读完。真做项目时，
这一侧要做的事有四件，而且每一件都能安静地错：

| 事 | 安静错的形态 |
| --- | --- |
| **发现**：目录里有哪些该进库的文件 | 把 `.DS_Store`、编辑器临时文件、`笔记~` 一起收进来 |
| **解析**：每个文件走哪条解析路 | 读不了的当成空文档放过去，检索时空着、没人发现 |
| **质量门**：这份文本值不值得进库 | 一份乱码比 0.95 的日志进库，它会在某天冒成一条「引用」 |
| **差量**：同一批文件重跑一次会怎样 | 每次重算全部向量（省钱的反面），或者改过的文档还留着旧片 |

模块的顺序就是上面那张表。三条设计决定写在这里，理由都是「不做的话会怎样」：

1. **读不了的要进报告，不能只进日志。** 入口层把三种「读不了」分得开——
   **缺解析器**（`Unsupported`：格式认出来了，但没有对应的库）、
   **内容太少**（解析成功、汉字数不足以被回答用上）、**乱码超线**（能解码，但乱码比过高）。
   三者处置不同：第一种要装库或换格式；第二种是**源文件的问题**（一份空模板）；
   第三种要重新导出或人工核对。混成一句「有文件读失败」，收到报告的人没法行动；
2. **内容哈希即身份。** 每一份源文件记 `content_stamp`（5.7 那个前 12 位的哈希），
   判「变了没有」看它，不看修改时间：`touch` 一下不该触发重算，
   而**内容变了但时间没变**（回滚、`git checkout`）必须触发。
   报告整体的 `stamp`（语料戳）取「所有入库文档的（doc_id, 内容戳）」排序后的哈希——
   于是它可以直接喂给 5.7 的 `Versions.corpus`：**入库改了内容，缓存自动失效**；
3. **入库是「全量报告 + 差量重算」，不是「追加」。** 每次拿当前目录算一份完整报告，
   内容戳没变的文档**直接复用上一次的片**（`reused=True`），
   再与上一份比：新增、更新、删除、未变、被拒各几条。文件删了要能移除，
   否则知识库里会留下永远不被引用的幽灵片。**追加式入库的失败形态是静默的**：
   索引一直在长，而没有任何一处能回答「现在库里到底有什么」。
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

from app.cache import content_stamp
from app.corpus import Chunk, Doc
from app.split import (Locked, Unsupported, load_document, quality, sniff_format,
                       split_document)

__all__ = ["IngestReport", "SourceRef", "discover", "ingest"]

#: 乱码比的上限。**0.10 是个选择，不是定律**：它指「前 1000 字里超过十分之一是
#: 控制字符／替换字符／私用区」——正常导出的中文文档乱码比是 0.0000，
#: 而 OCR 失败或编码错乱的那一档通常在 0.05–0.95 之间。写进配置，别写在心里。
MAX_GARBLED = 0.10

#: 一份文档少于这么多汉字就不进库。判据是「它能不能被回答用上」：
#: 十来个字的文件（`# 待办`、一行配置）在检索里只会变成噪声候选。
MIN_HANZI = 20

#: 发现阶段跳过的文件名。**收进来的代价比漏掉的代价大**：
#: 编辑器临时文件与系统文件进了库，它们会跟真文档抢名次。
SKIP_NAMES = frozenset({".DS_Store", "Thumbs.db"})
SKIP_SUFFIXES = (".tmp", ".bak", ".swp", "~")


@dataclass(frozen=True)
class SourceRef:
    """一个源文件在报告里的一行。`decision` 只有两档：**kept / rejected**。

    为什么没有第三档「skipped」：一份内容没变的文档**仍然是库里的文档**，
    把它标成「跳过」会让它在差量里显示成「被删了」。变的只是**重不重算**，
    那件事由 `reused` 记——一个布尔，而不是一个决策。
    """

    path: str            # 相对根目录的路径（报告里给人看）
    doc_id: str          # 入库后的文档名（引用里出现的那个）
    fmt: str             # 解析时判出来的格式（魔数判的，不是后缀）
    decision: str
    reason: str = ""
    pieces: int = 0
    hanzi: int = 0
    stamp: str = ""      # 内容哈希（前 12 位）
    reused: bool = False  # 内容未变，直接用了上一次的片

    def as_dict(self) -> dict:
        return {"path": self.path, "doc_id": self.doc_id, "fmt": self.fmt,
                "decision": self.decision, "reason": self.reason,
                "pieces": self.pieces, "hanzi": self.hanzi, "stamp": self.stamp,
                "reused": self.reused}


@dataclass(frozen=True)
class IngestReport:
    """一次入库的完整记录。**它是「现在库里有什么」的唯一答案。**"""

    root: str
    entries: tuple[SourceRef, ...] = ()
    docs: tuple[Doc, ...] = ()
    chunks: tuple[Chunk, ...] = ()

    # ---- 两档 ----
    @property
    def kept(self) -> tuple[SourceRef, ...]:
        return tuple(e for e in self.entries if e.decision == "kept")

    @property
    def rejected(self) -> tuple[SourceRef, ...]:
        return tuple(e for e in self.entries if e.decision == "rejected")

    def by_reason(self) -> dict[str, int]:
        """被拒的按原因归类。**一张报告里最有用的是这一行**：
        「七份读不了」没法行动，「五份缺解析器 ＋ 两份乱码超线」可以。"""
        out: dict[str, int] = {}
        for e in self.rejected:
            key = e.reason.split("：", 1)[0]
            out[key] = out.get(key, 0) + 1
        return out

    @property
    def stamp(self) -> str:
        """语料戳：**由留下的内容算出来**，不是「跑一次就变一个」。

        取所有入库文档的（doc_id, 内容戳）排序后再哈希，所以：
        改一份文档的内容 → 戳变（缓存失效）；`touch` 一下 → 戳不变（缓存留着）；
        被拒的文件进来或出去 → 戳不变（它们本来就没进库）。
        """
        return content_stamp("|".join(sorted(f"{e.doc_id}:{e.stamp}" for e in self.kept)))

    def as_dict(self) -> dict:
        return {
            "root": self.root,
            "files": len(self.entries),
            "kept": len(self.kept),
            "rejected": len(self.rejected),
            "reused": sum(1 for e in self.kept if e.reused),
            "docs": len(self.docs),
            "chunks": len(self.chunks),
            "hanzi": sum(e.hanzi for e in self.kept),
            "reasons": self.by_reason(),
            "stamp": self.stamp,
        }

    def diff(self, previous: "IngestReport | None") -> dict:
        """与上一份报告比。**五种结果都要能分开数**——`updated` 与 `added` 混在一起，
        就永远看不出「这次发布到底新加了几份、改了几份」。"""
        old = {e.doc_id: e for e in (previous.kept if previous else ())}
        new = {e.doc_id: e for e in self.kept}
        added = sorted(k for k in new if k not in old)
        removed = sorted(k for k in old if k not in new)
        updated = sorted(k for k in new if k in old and old[k].stamp != new[k].stamp)
        unchanged = sorted(k for k in new if k in old and old[k].stamp == new[k].stamp)
        return {"added": added, "updated": updated, "removed": removed,
                "unchanged": unchanged, "rejected": sorted(e.path for e in self.rejected)}


def discover(root: Path) -> tuple[Path, ...]:
    """目录 → 该考虑进库的文件（按路径排序，**顺序固定才可复现**）。"""
    out = []
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        if p.name in SKIP_NAMES or p.name.endswith(SKIP_SUFFIXES):
            continue
        if any(part.startswith(".") for part in p.relative_to(root).parts):
            continue
        out.append(p)
    return tuple(out)


def doc_id_of(path: Path, root: Path, *, prefix: str = "") -> str:
    """文档名：**相对路径去掉后缀、斜杠折成点**，可带一个根名前缀。

    为什么不用文件名：两个子目录里各有一份 `说明.md` 时，同名的两片会在引用里
    指向两个不同的东西（而引用是给读者核对用的）。折成相对路径之后它们仍然不同。
    前缀由调用方决定——本章的库里带 `knowledge.` 这样的根名前缀，
    好让引用一眼看出这份资料来自哪个目录。
    """
    rel = str(path.relative_to(root).with_suffix("")).replace("\\", "/")
    return f"{prefix}{rel.replace('/', '.')}"


def _one(path: Path, root: Path, *, prefix: str, strategy: str, size: int,
         overlap: int) -> tuple[SourceRef, Doc | None, tuple[Chunk, ...]]:
    """一个文件的全部判断。返回（报告行、文档、片）；被拒时后两项为空。"""
    rel = str(path.relative_to(root)).replace("\\", "/")
    stamp = content_stamp(path.read_bytes().decode("utf-8", errors="replace"))
    doc_id = doc_id_of(path, root, prefix=prefix)

    # 格式在这里先判一次，**是为了给「进库」那一行也带上格式**。
    # 第一版只有被拒的行带格式（异常里带着），进库的行是空串——于是
    # 「这一版进来了哪几种格式」这个只有报告能回答的问题，报告答不上来。
    # 它是 5.8 的验收清单在第一次运行里报✖的那一条（见 5.8.7）。
    fmt = sniff_format(path)

    # ---- ① 解析：三种「读不了」的第一种，缺解析器 ----
    try:
        doc = load_document(path)
    except Unsupported as exc:
        return SourceRef(rel, doc_id, exc.fmt, "rejected",
                         f"缺解析器：{exc.fmt}（{exc.lib or '无可用库'}）", 0, 0, stamp), None, ()
    except Locked as exc:
        return SourceRef(rel, doc_id, fmt, "rejected", f"加密未解锁：{exc}", 0, 0, stamp), None, ()

    # **把前缀写进 `Doc`，不能只写在报告行里**：片是从 `doc` 切出来的，
    # 而引用标识取自 `Piece.doc_id`。只改报告的话，引用里看不到根目录前缀，
    # 而且「按 doc_id 取回上一次的片」会永远匹配不上（两边一个带前缀一个不带）。
    # 这一处是写读数的 `reused` 一直是 0 才查出来的。
    doc = replace(doc, doc_id=doc_id)

    q = quality(doc.text)
    hanzi = sum(1 for c in doc.text if "\u4e00" <= c <= "\u9fff")

    # ---- ② 质量门：第二、三种。内容太少与乱码超线是两件事，报告里也分两行 ----
    if hanzi < MIN_HANZI:
        return SourceRef(rel, doc_id, fmt, "rejected",
                         f"内容太少：{hanzi} 汉字（下限 {MIN_HANZI}）", 0, hanzi, stamp), None, ()
    if q["garbled"] > MAX_GARBLED:
        return SourceRef(rel, doc_id, fmt, "rejected",
                         f"乱码超线：{q['garbled']:.4f}（上限 {MAX_GARBLED}）",
                         0, hanzi, stamp), None, ()

    # ---- ③ 切分：与语料那条路同一个切法，读数才可比 ----
    pieces = split_document(doc, strategy=strategy, size=size, overlap=overlap)
    chunks = tuple(p.as_chunk() for p in pieces)
    if not chunks:
        return SourceRef(rel, doc_id, fmt, "rejected", "切不出片：清洗后没有内容",
                         0, hanzi, stamp), None, ()
    return SourceRef(rel, doc_id, fmt, "kept", "", len(chunks), hanzi, stamp), doc, chunks


def ingest(root: Path, *, prefix: str = "", strategy: str = "sections", size: int = 300,
           overlap: int = 60, previous: IngestReport | None = None) -> IngestReport:
    """跑一次入库。**任何一份文件读不了都不中断整批**。

    这正是 `split.load_directory` 的文档里承诺、而实现里没有的那件事：
    那里只写了「读不了的记在案上，不中断」，循环里却直接 `load_document()`——
    一份坏文件会把整批停下（见 `tests/test_ingest.py` 的夹具）。

    `previous` 给上一次的报告：内容戳没变的文档**直接复用上一次的片**
    （`reused=True`），不重切、不重嵌。注意差量与「切分参数」无关：
    本树按内容戳判重算，而 `strategy`／`size` 变了、内容没变时会**复用错**——
    真实系统里这一层要把切分参数一起进缓存键（5.7 的 `DEPENDS` 已经给了形状），
    这里留的是「重跑一次要重算几份」这个读数。
    """
    entries: list[SourceRef] = []
    docs: list[Doc] = []
    chunks: list[Chunk] = []
    # 上一次的片按文档归好，供复用时整份取回。
    old_chunks: dict[str, list[Chunk]] = {}
    for e in (previous.kept if previous else ()):
        old_chunks[e.doc_id] = []
    for c in (previous.chunks if previous else ()):
        old_chunks.setdefault(c.doc_id, []).append(c)
    old = {e.doc_id: e for e in (previous.kept if previous else ())}

    for path in discover(root):
        ref, doc, got = _one(path, root, prefix=prefix, strategy=strategy, size=size,
                             overlap=overlap)
        if ref.decision == "kept" and ref.doc_id in old and old[ref.doc_id].stamp == ref.stamp \
                and old_chunks.get(ref.doc_id):
            # 复用的那一行把上一次的 `fmt` 一起带过来：格式没变（内容都没变），
            # 而重判一次会多读一次文件头——这一层已经不需要重判了。
            entries.append(SourceRef(ref.path, ref.doc_id, ref.fmt, "kept", "", ref.pieces,
                                     ref.hanzi, ref.stamp, reused=True))
            docs.append(doc)
            chunks.extend(old_chunks[ref.doc_id])
            continue
        entries.append(ref)
        if doc is not None:
            docs.append(doc)
            chunks.extend(got)
    chunks.sort(key=lambda c: (c.doc_id, c.index))
    return IngestReport(root=str(root), entries=tuple(entries), docs=tuple(docs),
                        chunks=tuple(chunks))
