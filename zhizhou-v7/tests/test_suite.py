"""`app/suite.py` 的用例。不依赖 pytest：`tools/check_runnable.py` 会把 `test_*` 逐条调起来。"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.suite import SPLITS, Case, Suite, sample_suite  # noqa: E402


def test_整集指纹与顺序无关():
    s = sample_suite()
    assert Suite(list(reversed(s.cases))).digest() == s.digest()


def test_改一个字指纹就变():
    s = sample_suite()
    changed = Suite([Case(c.cid, c.query + "？", c.tags, c.split, c.reference)
                     for c in s.cases])
    assert changed.digest() != s.digest()


def test_干净的评测集没有违规():
    assert sample_suite().violations() == []


def test_同一句题在同一份切分里只算重复不算污染():
    s = Suite([Case("a", "同一句", split="gate"), Case("b", "同一句", split="gate")])
    assert len(s.duplicates()) == 1
    assert list(s.duplicates().values())[0] == ["a", "b"]
    assert s.contamination() == {}


def test_跨切分的重复就是污染():
    s = Suite([Case("a", "同一句", split="gate"), Case("b", "同一句", split="holdout")])
    assert s.contamination() != {}
    assert s.violations() != []


def test_切分为空会被断言拦下():
    s = Suite([Case("a", "x", split="gate")])
    assert any("是空的" in v for v in s.violations())


def test_cid重复会被断言拦下():
    s = Suite([Case("a", "x"), Case("a", "y")])
    assert any("cid 有重复" in v for v in s.violations())


def test_非法切分会被断言拦下():
    s = Suite([Case("a", "x", split="乱写")])
    assert any("不在" in v for v in s.violations())


def test_按条数抽会在二十个种子里漏掉稀有层():
    s = sample_suite()
    missed = [seed for seed in range(20)
              if not any("表格" in c.tags for c in s.sample_by_count(8, seed=seed))]
    assert missed, "按条数抽居然一次都没漏——那这一条读数就不成立了"


def test_按层抽在二十个种子里一次都不漏():
    s = sample_suite()
    for seed in range(20):
        assert any("表格" in c.tags for c in s.sample_by_stratum(8, seed=seed)), seed


def test_切分是十八四二():
    cov = sample_suite().coverage()
    assert cov == {"gate": 18, "holdout": 4, "smoke": 2}
    assert sum(cov.values()) == 24


def test_切分的名字都在表里():
    assert set(sample_suite().coverage()) == set(SPLITS)
