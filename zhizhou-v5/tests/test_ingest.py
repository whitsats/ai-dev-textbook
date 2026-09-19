# tests/test_ingest.py —— 不需要密钥、不需要网络：一个目录怎么变成一份知识库
"""这一份测的是 5.8 的入库层（`app/ingest.py`）。十四组断言：

1. **三档拒收各一条，理由分得开**：缺解析器／内容太少／乱码超线——
   混成一句「有文件读失败」，收到报告的人没法行动；
2. **进库的行也带格式**：报告要能回答「这一版进来了哪几种格式」。
   这一条是拿验收清单的 ✖ 换来的——第一版只有被拒的行带 `fmt`；
3. **一份坏文件不中断整批**：`split.load_directory` 的文档里承诺过、实现里没有；
4. **二次入库复用旧片**：内容戳没变就不重切不重嵌（`reused` 计数）；
5. **戳随内容变、不随 mtime 变**：`touch` 不触发重算，`git checkout` 必须触发；
6. **被拒文件进出不影响戳**：它们本来就没进库；
7. **差量五种结果分得开**：新增／更新／删除／未变／被拒；
8. **文档名折相对路径**：两个子目录里的同名文件不能撞成一个引用；
9. **发现阶段的顺序固定**：同一份目录两次跑，报告逐行相同（可复现）；
10. **片按（文档，序号）排序**：引用序与阅读序一致；
11. **临时文件不被收进来**：`.DS_Store`、`笔记~` 进来会跟真文档抢名次；
12. **空目录给空报告**，而戳仍然算得出来（不是 `None`）；
13. **真实语料守一遍**：`knowledge/` 现在是 3 进库 3 被拒，三档各一条；
14. **报告的字段与明细一致**：`as_dict()` 里的数与逐行的数不许对不上。
"""
from __future__ import annotations

import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.ingest import (MAX_GARBLED, MIN_HANZI, SKIP_NAMES, discover,  # noqa: E402
                        doc_id_of, ingest)

BODY = "知舟的发布说明包含范围、回滚、通知三段，缺一段即为不合格。"


def make_dir(**files: str) -> Path:
    """一个临时目录。键是文件名（`.` 换成 `_`），值是内容。"""
    tmp = Path(tempfile.mkdtemp())
    for name, text in files.items():
        p = tmp / name.replace("_", ".")
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    return tmp


def test_三档拒收各一条且理由分得开() -> None:
    tmp = make_dir(好_md=BODY * 3, 空_md="", 坏_xyz="随手写的")
    (tmp / "坏.xyz").write_bytes(b"\x80\x81\x82\x83\x84\x85")
    (tmp / "乱.txt").write_text("\x01\x02\x03" * 10 + "这是一份乱码文件，请人工核对。" * 3,
                                encoding="utf-8")
    rep = ingest(tmp)
    assert rep.as_dict()["kept"] == 1
    assert rep.by_reason() == {"缺解析器": 1, "内容太少": 1, "乱码超线": 1}


def test_进库的行也带格式() -> None:
    """**这一条守的是一个缺陷**：第一版 `_one()` 给进库的行传了空串格式，

    于是「这一版进来了哪几种格式」只有报告能回答、而报告答不上来。
    验收清单在第一次运行里就把它报成 ✖（见 5.8.7）——测试把它钉住。
    """
    # 格式是**按内容**判的，不是按后缀：`.md` 要有一行 `# ` 标题才算 md，
    # 否则它会被判成 txt（把一份没标题的正文改名成 `.md` 是合法的）。
    tmp = make_dir(说明_md="# 发布说明\n\n" + BODY * 3,
                   值班表_csv="姓名,时段,职责\n甲,夜间,值守与告警\n乙,白天,值守与发布\n")
    rep = ingest(tmp)
    fmts = {e.fmt for e in rep.kept}
    assert "" not in fmts, "进库的行不许有空的格式"
    assert fmts == {"md", "csv"}, fmts


def test_一份坏文件不中断整批() -> None:
    """`load_directory` 的文档里写着「读不了的记在案上，不中断」，

    而实现里是直接 `load_document()`——一份坏文件把整批停下。这一层补上了它。
    """
    tmp = make_dir(甲_md=BODY * 3, 乙_md=BODY * 2)
    (tmp / "丙.xyz").write_bytes(b"\x00" * 32)
    rep = ingest(tmp)
    assert rep.as_dict()["kept"] == 2 and rep.as_dict()["rejected"] == 1
    assert len(rep.chunks) > 0


def test_二次入库复用旧片() -> None:
    tmp = make_dir(说明_md=BODY * 3)
    first = ingest(tmp, prefix="t.")
    second = ingest(tmp, prefix="t.", previous=first)
    assert first.as_dict()["reused"] == 0 and second.as_dict()["reused"] == 1
    assert [c.text for c in first.chunks] == [c.text for c in second.chunks]


def test_戳随内容变不随修改时间变() -> None:
    tmp = make_dir(说明_md=BODY * 3)
    before = ingest(tmp).stamp
    p = tmp / "说明.md"
    os.utime(p, (time.time() + 5, time.time() + 5))
    assert ingest(tmp).stamp == before, "只 touch 不该触发重算"
    p.write_text(BODY * 3 + "补充一段。", encoding="utf-8")
    assert ingest(tmp).stamp != before, "内容变了必须触发重算"


def test_被拒文件进出不影响戳() -> None:
    tmp = make_dir(说明_md=BODY * 3)
    before = ingest(tmp).stamp
    (tmp / "扫描件.xyz").write_bytes(b"\x00" * 16)
    assert ingest(tmp).stamp == before, "没进库的文件不该改语料戳"


def test_差量五种结果分得开() -> None:
    tmp = make_dir(甲_md=BODY * 3, 乙_md=BODY * 2)
    first = ingest(tmp)
    (tmp / "甲.md").write_text(BODY * 3 + "改过。", encoding="utf-8")
    (tmp / "乙.md").unlink()
    (tmp / "丙.md").write_text(BODY * 4, encoding="utf-8")
    (tmp / "丁.md").write_text("", encoding="utf-8")
    second = ingest(tmp)
    diff = second.diff(first)
    assert diff["added"] == ["丙"] and diff["updated"] == ["甲"]
    assert diff["removed"] == ["乙"] and diff["unchanged"] == []
    assert diff["rejected"] == ["丁.md"]


def test_两个子目录的同名文件不撞() -> None:
    tmp = make_dir()
    for sub in ("甲", "乙"):
        (tmp / sub).mkdir()
        (tmp / sub / "说明.md").write_text(BODY * 3, encoding="utf-8")
    rep = ingest(tmp)
    # **不比顺序，只比集合**：谁在前由路径序决定（`乙` 的码位比 `甲` 小），
    # 而这一条要守的是「两个同名文件不撞成一个引用」，不是排序。
    assert {e.doc_id for e in rep.kept} == {"甲.说明", "乙.说明"}
    assert len({c.cite() for c in rep.chunks}) == len(rep.chunks), "引用不许撞"


def test_文档名可带根名前缀() -> None:
    tmp = make_dir(说明_md=BODY * 3)
    assert ingest(tmp, prefix="knowledge.").kept[0].doc_id == "knowledge.说明"
    assert doc_id_of(tmp / "说明.md", tmp) == "说明"


def test_发现阶段顺序固定() -> None:
    tmp = make_dir(乙_md=BODY * 2, 甲_md=BODY * 3, 丙_md=BODY)
    once = [e.path for e in ingest(tmp).entries]
    twice = [e.path for e in ingest(tmp).entries]
    assert once == twice == sorted(once)


def test_片按文档与序号排序() -> None:
    tmp = make_dir(乙_md=BODY * 3, 甲_md=BODY * 3)
    keys = [(c.doc_id, c.index) for c in ingest(tmp).chunks]
    assert keys == sorted(keys)


def test_临时文件不被收进来() -> None:
    tmp = make_dir(好_md=BODY * 3)
    for junk in (".DS_Store", "笔记.md~", "草稿.md.bak"):
        (tmp / junk).write_text("x", encoding="utf-8")
    assert ".DS_Store" in SKIP_NAMES
    assert [p.name for p in discover(tmp)] == ["好.md"]


def test_空目录给空报告而戳仍然算得出来() -> None:
    tmp = Path(tempfile.mkdtemp())
    rep = ingest(tmp)
    d = rep.as_dict()
    assert (d["files"], d["kept"], d["rejected"], d["chunks"]) == (0, 0, 0, 0)
    assert isinstance(rep.stamp, str) and len(rep.stamp) == 12


def test_真实知识的目录与逐行明细对得上() -> None:
    """守住真实语料：`knowledge/` 现在是 3 进库 3 被拒，三档各一条。"""
    rep = ingest(ROOT / "knowledge", prefix="knowledge.")
    d = rep.as_dict()
    assert (d["kept"], d["rejected"]) == (3, 3)
    assert rep.by_reason() == {"乱码超线": 1, "缺解析器": 1, "内容太少": 1}
    assert d["files"] == len(rep.entries)
    assert d["hanzi"] == sum(e.hanzi for e in rep.kept)
    assert d["chunks"] == len(rep.chunks)
    assert all(e.fmt for e in rep.kept), "三种格式都该被认出来"
    assert MIN_HANZI == 20 and MAX_GARBLED == 0.10, "两个阈值是选择，写在这里便于对照"


def run() -> int:
    """不依赖 pytest 的跑法：`python tests/test_ingest.py`。"""
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
