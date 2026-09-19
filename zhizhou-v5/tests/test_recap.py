# tests/test_recap.py —— 不需要密钥、不需要网络：文档这一侧的对账本身对不对
"""这一份测的是 5.9 的对账层（`scripts/recap.py`）。六条断言：

1. **`--offline` 跑得通**，退出码 0，并打印「离线自检通过」——它是提交门的入口；
2. **`--self-test` 全过**（条数**从输出里读**，不写死——写死的那种会在脚本长夹具的那天静静变假），
   且输出里没有叉号（夹具自己坏了也要拦）；
3. **架构文档点名了树里每一个 `app/` 模块**——这一条**故意用第二种实现**写：
   `recap.py` 用一条正则扫全文，这里用「切反引号再判后缀」的写法。
   两边互相对照，正则本身写错时不会两边一起错（同 `check_runnable` 自检里
   那条「两种写法互相对照」）；
4. **每条 ADR 的读数引用都能在 `experiments/eval_baseline.json` 里找得到、且相等**
   ——同样用第二种实现（自己走 JSON），并给出一条反例断言：
   **把键名拼错必须取不到值**，否则「找得到」可能只是取值函数太宽松；
5. **交付物清单里标的行数都与盘上相等**——也是第二种实现：`recap.py` 按
   「同一行里路径之后的最近一个 `N 行`」配，这里按**表格的竖线切格子**再数行。
   三种实现里这一份最脆（它认表格形状），所以要它存在：
   把配对写松的那次事故里，**另一种写法是唯一会响的东西**；
6. **自描述条数与实得相等**：`recap.py` 在进程内数 `fixture_cases()`，这里
   **跑一次 `--self-test` 读 stdout**（`自检 N/M 通过`）——两种写法互相对照，
   真的少写一条夹具时两条路都会红。
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ARCH = ROOT / "docs" / "architecture.md"
DECISIONS = ROOT / "docs" / "decisions"
EVIDENCE = ROOT / "experiments" / "eval_baseline.json"
MARKER = "离线自检通过"
#: 期望的 ADR 条数下限（每写一条就往上抬——它是反向守，不是装饰）。
MIN_ADRS = 6


def run_script(*args: str, timeout: int = 300) -> str:
    proc = subprocess.run([sys.executable, "scripts/recap.py", *args],
                          cwd=ROOT, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=timeout)
    assert proc.returncode == 0, f"退出码 {proc.returncode}\n{proc.stdout[-2000:]}"
    return proc.stdout


def backticked_paths(text: str) -> set[str]:
    """与 `recap.py` 不同的第二种写法：先把反引号里的片段切出来，再判后缀。

    两处细节都是**这一版自己踩出来的**，留着当注释：
      · 先剔掉三反引号围栏。不剔的话，围栏与内联代码的单个反引号会配成对，
        整段 Mermaid 图会被当成一个「片段」，表格里的模块名反而收不到；
      · 剔除时用非贪婪匹配，且**只删围栏本身的内容**——`recap.py` 用的是
        「全文扫路径」的松散写法，本来就不在意围栏，两种写法的差异正好互相兜底。
    """
    out = set()
    for raw in re.findall(r"`([^`]+)`", re.sub(r"```.*?```", "", text, flags=re.S)):
        token = raw.strip().strip("()")
        if token.endswith(".py") and token.split("/")[0] in {
                "app", "tests", "scripts", "experiments", "migrations"}:
            out.add(token)
    return out


def flat_lookup(doc: dict, key: str):
    """第二种实现的取值：先在 `flat` 里找，再按点号走 `raw`。"""
    if key in doc.get("flat", {}):
        return doc["flat"][key]
    node = doc.get("raw", {})
    for part in key.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node if isinstance(node, (int, float)) else None


def test_对账跑通并打印收尾标记() -> None:
    out = run_script("--offline")
    assert MARKER in out, f"没打印「{MARKER}」：{out[-500:]}"
    assert "✖" not in out, f"输出里有叉号：\n{out}"


def test_夹具自检全过且没有叉号() -> None:
    out = run_script("--self-test")
    # **不把条数写死**：这里的任务是「全过」，而条数归架构文档与第五条对账管。
    # 写死一个数就等于在这里又开一份手抄账——脚本每次长夹具都要人来改它，
    # 而「改脚本的人」与「改这个数的人」往往不是同一个脑子里的同一件事。
    m = re.search(r"自检 (\d+)/(\d+) 通过", out)
    assert m, f"输出里没有「自检 N/M 通过」这一行：{out}"
    ran, total = int(m.group(1)), int(m.group(2))
    assert total >= 20, f"自检只有 {total} 条（下限 20）——扫描退化时这一句会变成空话"
    assert ran == total, f"自检 {ran}/{total}：有夹具没过\n{out}"
    assert "✖" not in out, out


def test_架构文档点名了每一个app模块() -> None:
    named = backticked_paths(ARCH.read_text(encoding="utf-8"))
    on_disk = {p.relative_to(ROOT).as_posix()
               for p in (ROOT / "app").rglob("*.py") if p.name != "__init__.py"}
    # 反向守：两边都必须扫到东西，否则「相等」可能只是两个空集相等
    assert len(on_disk) >= 20, f"扫到的 app 模块太少（{len(on_disk)} 个）：{sorted(on_disk)}"
    assert on_disk <= named, f"这些模块没被架构文档点名：{sorted(on_disk - named)}"


def test_每条ADR的读数引用都核得上() -> None:
    doc = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    adrs = sorted(DECISIONS.glob("*.md"))
    # 反向守：ADR 太少时先怀疑扫描本身（写死清单那一族错误的修法）
    assert len(adrs) >= MIN_ADRS, f"只扫到 {len(adrs)} 条 ADR（下限 {MIN_ADRS}）"
    total = 0
    for path in adrs:
        text = path.read_text(encoding="utf-8")
        cites = re.findall(r"`([A-Za-z_][\w.]*)=(-?\d+(?:\.\d+)?)`", text)
        assert cites, f"{path.name} 一个读数引用都没有"
        for key, val in cites:
            got = flat_lookup(doc, key)
            assert got is not None, f"{path.name}：`{key}` 在证据文件里找不到"
            assert abs(float(got) - float(val)) < 1e-9, \
                f"{path.name}：`{key}={val}` 与实跑读数 {got} 不等"
            total += 1
    assert total >= 12, f"六条 ADR 合计只有 {total} 条读数引用，太少（像是背景被删空了）"
    # 反例：拼错的键必须取不到值。少了这一条，「找得到」可能只是取值太宽松。
    assert flat_lookup(doc, "span.hybird") is None
    assert flat_lookup(doc, "no.such.key") is None


def test_交付物清单里的行数都与盘上相等() -> None:
    """第二种实现：不调 `recap.py`，自己把那张表切成格子再数行。

    两处与 `recap.py` 不同，都是刻意的：
      · 配对靠**表格的竖线**，不靠「同一行里路径之后的最近一个数字」——
        `recap.py` 那边写松了，这边不会跟着松；
      · 数行用 `len(splitlines())`，不共用 `real_lines()`——共用的话，
        那个函数数错了两边一起错。
    反向守：解析到的行数不能太少（表被删空时，「相等」会是两个空集相等）。
    """
    rows: list[tuple[str, int]] = []
    for line in ARCH.read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if (len(cells) >= 2 and cells[0].startswith("`") and cells[0].endswith("`")
                and cells[1].endswith("行") and cells[1][:-1].strip().isdigit()):
            rows.append((cells[0].strip("`"), int(cells[1][:-1].strip())))
    assert len(rows) >= 8, f"交付物清单只解析到 {len(rows)} 行（下限 8）：{rows}"
    for rel, claimed in rows:
        real = len((ROOT / rel).read_text(encoding="utf-8").splitlines())
        assert real == claimed, f"{rel} 标的是 {claimed} 行，盘上是 {real} 行"


def test_自描述条数与实跑相等() -> None:
    """第二种实现：不调 `recap.py` 的检查函数，而是**跑一次子进程读它的输出**。

    两处与 `recap.py` 不同，都是刻意的：
      · 夹具数从 stdout 的「自检 N/M 通过」读回来，不在进程内数 `fixture_cases()`；
      · 用例数用最笨的办法数 `def test_` 行，不共用 `real_cases()`。
    两边互相对照：真少写一条夹具时，两条路都会红——**一条只会在顺利时沉默的检查，
    是没被验过的检查**。
    """
    out = run_script("--self-test")
    m = re.search(r"自检 (\d+)/(\d+) 通过", out)
    assert m, f"没读到自检条数：{out[-300:]}"
    assert m.group(1) == m.group(2), f"夹具自己没全过：{m.group(0)}"
    total = int(m.group(2))
    arch = ARCH.read_text(encoding="utf-8")
    claims = {int(n) for n in re.findall(r"(\d+)\s*条夹具", arch)}
    # 反向守：一处都没写时，「相等」会变成空集的相等
    assert claims, "架构文档里一个「N 条夹具」都没写——那个数字就没人核了"
    assert claims == {total}, f"文档写 {sorted(claims)} 条夹具，实跑 {total} 条"
    real = len([ln for ln in (ROOT / "tests" / "test_recap.py")
                .read_text(encoding="utf-8").splitlines() if ln.startswith("def test_")])
    claimed = [int(n) for n in re.findall(r"(\d+)\s*条用例", arch)]
    assert claimed, "架构文档里一个「N 条用例」都没写"
    assert all(c == real for c in claimed), f"文档写 {claimed} 条用例，实得 {real} 条"


def run() -> int:
    """不依赖 pytest 的跑法：`python tests/test_recap.py`。"""
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
