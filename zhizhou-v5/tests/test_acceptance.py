# tests/test_acceptance.py —— 不需要密钥、不需要网络：验收这一层本身对不对
"""这一份测的是 5.8 的验收层（`scripts/acceptance.py`）。七组断言：

1. **`--offline` 跑得通**，退出码 0，并打印「离线自检通过」；
2. **清单全过**：八项都打 ✔，而**一项不通过就非零退出**（否则它只是八个句子）；
3. **读数摘要里有正文要引的那四个数**：片 15→17、片级 0.8333→0.8889、
   答案命中 0.9444→1.0000。**读数不在输出里，正文就不是可复算的**；
4. **端到端那一节的两把尺子是分开的**：印发出去那一份的核对通过，
   而「模型自称与绑定不符」单独报（本章第一版把两者混成一个布尔，清单因此错报 ✖）；
5. **`--self-test` 十条夹具全过**（含基线断言的两个方向、分辨率判据的两个方向）；
6. **输出里没有 ✖**：清单与夹具两处的叉号都算失败；
7. **脚本里的基线常量与 5.6 的基线文件相等**——两章共用一个锚，
   改了一边不改另一边，这一条会先报出来。
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

BASELINE_FILE = ROOT / "experiments" / "eval_baseline.json"
#: 脚本里写死的那四个数。**改它们之前先想清楚 5.1–5.7 的正文**（见下面第 7 条）。
SCRIPT_BASELINE = {"span": 0.8333, "answer": 0.9444, "missed": 1, "over": 0}


def run_script(*args: str, timeout: int = 300) -> str:
    proc = subprocess.run([sys.executable, "scripts/acceptance.py", *args],
                          cwd=ROOT, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=timeout)
    assert proc.returncode == 0, f"退出码 {proc.returncode}\n{proc.stdout[-2000:]}"
    return proc.stdout


def test_离线验收跑通并打印收尾标记() -> None:
    out = run_script("--offline")
    assert "离线自检通过" in out
    assert "① 入库报告" in out and "④ 验收清单" in out
    assert "清单 8/8 通过" in out, "八项清单必须全过"


def test_读数摘要里有正文要引的四个数() -> None:
    out = run_script("--offline")
    line = next((x for x in out.splitlines() if x.startswith("本次验收：")), "")
    assert line, "没有读数摘要行——正文引的数是它给的"
    for token in ("片 15→17", "片级 0.8333→0.8889", "答案命中 0.9444→1.0000",
                  "源文件 12 份", "扩库 20"):
        assert token in line, f"{token} 不在摘要里：{line}"


def test_端到端的两把尺子分开报() -> None:
    out = run_script("--offline")
    assert "引用核对（对发出去的那一份）：通过" in out
    assert "自称与绑定不符（绑定层改过）" in out, \
        "「模型自称」与「对外答复」必须是两个数（5.7 那一族错的第三次）"
    assert "模型的『模型自称』与绑定不符" not in out


def test_三套库的对照与归因都在输出里() -> None:
    out = run_script("--offline")
    assert "A 组与 5.6 的基线逐项相同" in out
    assert "扩库那一组的归因" in out and "24 条里有 12 条的前三名出现过新片" in out
    # 「候选变了」与「读数变了」是两件事：扩库过半的题候选变过，而四项读数一格没动。
    assert "扩库改了 13/24 条，迁移改了 22/24 条" in out, out[-1200:]
    assert "在分辨率之下，不报" in out, "扩库那一组四项没动，正文不许把它写成提升"
    assert "报得出" in out, "迁移那一组超过分辨率，正文应当报"


def test_夹具十条全过() -> None:
    out = run_script("--self-test")
    assert re.search(r"夹具自检：10/10 通过", out), out[-800:]


def test_输出里没有叉号() -> None:
    """`✖` 只用于「验收不通过」；被拒的源文件用 `✗`（那是处置记录）。

    两个记号分开之后，这一句就等于「没有一项验收失败」——不用去数缩进。
    """
    for args in (("--offline",), ("--self-test",)):
        out = run_script(*args)
        assert "✖" not in out, f"{args} 的输出里有 ✖：{out[-800:]}"
        assert "✗" in out or args == ("--self-test",), "被拒的文件要看得见"


def test_脚本里的基线与5_6的基线文件相等() -> None:
    """**两章共用一个锚。** 改了一边不改另一边，这一条先报。

    基线文件是 5.6 的 `experiments/eval_run.py --write-baseline` 写的，
    所以它记的是那一章跑出来的数；本脚本的常量是给 `.metrics.gate` 之外的人看的
    （验收脚本不跑回归门，它只对这一个锚负责）。
    """
    flat = json.loads(BASELINE_FILE.read_text(encoding="utf-8"))["flat"]
    assert flat["span.hybrid"] == SCRIPT_BASELINE["span"]
    assert flat["answer_hit"] == SCRIPT_BASELINE["answer"]
    assert flat["refusal.plain.missed"] == SCRIPT_BASELINE["missed"]
    assert flat["refusal.plain.over"] == SCRIPT_BASELINE["over"]
    # 反向守：这四个键**必须真的在基线文件里**。取不到时 `assert` 会以 KeyError
    # 的形式炸掉，而不是安静地以为「相等」。
    assert set(flat) >= {"span.hybrid", "answer_hit",
                         "refusal.plain.missed", "refusal.plain.over"}


def run() -> int:
    """不依赖 pytest 的跑法：`python tests/test_acceptance.py`。"""
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
