"""发布与灰度：**发布这一步的每一个默认值都站在「快」那一边，而灰度买的是「慢一点、但知道」。**

这一块把「上线」拆成三个各自能单独出错的部件：

1. **钉法**：部署清单里写的是 `:latest`、`:v1.2.3` 还是 `@sha256:…`。它们决定的是
   **八小时之后回滚时回到的是不是同一份字节**。官方对 action 的那句话在这里同样成立
   （标签可以被移动、也可以被删除）：**可变的引用等于把「你审过的那一版」交给别人保管**。
   内容寻址的摘要（`@sha256:…`）是唯一「只能指一份」的写法，**而它也是回滚的前提**——
   没有它，「回到上一版」靠的是人记得上一次的标签，而那个标签可能已经不在原处。
2. **审批**：`environment` 上的必需审阅人。它买到的东西要说准：**不是更安全，是「一次发布有一个名字」**
   （官方：环境密钥在批准之前那一格拿不到）。而它有一个不会出现在任何输出里的连带后果——
   **待批准的 run 仍然占着 `concurrency` 组**，于是后面推的那一次会被排队或取消（见 `graph` 那一块）。
3. **灰度的判据**：这一块最反直觉的一节。金丝雀阶梯本身不救人，
   **救人或不救人的是「判红」这一门判据的形态**：

   · 判据是**固定样本数**（攒够 N 个错误就判红）时，金丝雀**一分钱也省不下来**——
     「攒够 N 个错误」所需的请求数是 `N ÷ 真实错误率`，与流量档位无关；
     小档位只是把判红**拖长**，而拖长的这段时间里它照样在错；
   · 判据是**固定时间窗**（一个窗口里的真实错误率超阈值）时，一个小档位就是真的少错——
     因为窗口是固定的、流量小 20 倍，被放过去的坏请求就少 20 倍。

   还有一笔比判红更贵的账：**回滚**。它由两段构成（人批准 ＋ 生效），而这两段里的流量
   都是当前档位的全量。所以「回滚多快」往往比「多快判红」贵两个数量级——
   而它恰恰是「钉法」那一节在工程上唯一的作用。
"""

from __future__ import annotations

from dataclasses import dataclass


# ------------------------------------------------------- 一、钉法

@dataclass(frozen=True)
class Pin:
    """部署清单里的三种写法。`same_bytes_after` 回答的是「八小时后回滚回到的是不是同一份」。"""

    kind: str
    sample: str
    mutable: bool
    same_bytes_after: bool
    trace: str          # 它被改掉之后，改动留在哪里
    note: str


PINS: tuple[Pin, ...] = (
    Pin("浮动标签 `latest`", "image: zhizhou:latest", True, False,
        "不留在任何地方",
        "每一次发布会动它；回滚回到的不是你要的那一份"),
    Pin("版本标签 `v1.2.3`", "image: zhizhou:v1.2.3", True, False,
        "一次 `docker push`（同一个标签覆盖推）",
        "**同名标签可以被移动**：回滚回到的是「它现在指向的那一份」"),
    Pin("内容摘要 `@sha256:…`", "image: zhizhou@sha256:9f2c…", False, True,
        "清单里那串字符（＝一次可审的提交）",
        "只能指一份——**它也是「一键回到那一份」的前提**"),
)


def pin_table() -> list[dict]:
    """三种钉法：谁能改它、回滚回到同一份吗、改动留不留痕、静默改动能改到几处。"""
    rows: list[dict] = []
    for pin in PINS:
        rows.append({
            "kind": pin.kind,
            "sample": pin.sample,
            "same_bytes": pin.same_bytes_after,
            "silent_spots": 1 if pin.mutable else 0,
            "trace": pin.trace,
            "note": pin.note,
        })
    return rows


# ------------------------------------------------------- 二、审批

#: 一次发布的等待（本项目口径）：自动发布 0 秒；必需审阅人的环境等一次人去看。
AUTO_APPROVE_S = 0
HUMAN_APPROVE_S = 240
RELEASES_PER_DAY = 6


def approval_report() -> dict:
    """审批买到的是什么。**含那句容易被忽略的连带后果**：待批准仍占着并发组。"""
    return {
        "auto_wait_s": AUTO_APPROVE_S,
        "human_wait_s": HUMAN_APPROVE_S,
        "day_wait_s": RELEASES_PER_DAY * HUMAN_APPROVE_S,
        "bought": "一次发布有一个名字（以及那一格的密钥在批准前拿不到）",
        "side_effect": "待批准的 run 仍然占着 concurrency 组——后面推的那一次会被排队或取消",
    }


# ------------------------------------------------------- 三、金丝雀与回滚

TOTAL_RPS = 1000            # 全量流量
BAD_ERROR_RATE = 0.03       # 坏版本的真实错误率
STEPS: tuple[tuple[int, str], ...] = ((5, "5%"), (25, "25%"), (100, "100%"))

GATE_COUNT = 40             # 判据一：累计 40 个错误就判红（固定样本数）
WINDOW_S = 60               # 判据二：一个窗口的长度（固定窗口）
WINDOW_RATE = 0.01          # 判据二：窗口内的错误率阈值

ROLLBACK_APPROVE_S = 240    # 回滚要一个人点（与发布同一个环境）
ROLLBACK_EFFECT_S = 90      # 回滚生效（拉镜像、滚动重启）


def canary_table() -> list[dict]:
    """三档 × 两门判据：判红要多久、放过去多少坏请求。**两门判据的差额才是这一节的结论。**"""
    rows: list[dict] = []
    for pct, label in STEPS:
        rps = TOTAL_RPS * pct // 100
        count_seconds = GATE_COUNT / (BAD_ERROR_RATE * rps)
        window_bad = int(BAD_ERROR_RATE * rps * WINDOW_S)
        threshold_bad = int(WINDOW_RATE * rps * WINDOW_S)
        rows.append({
            "step": label,
            "rps": rps,
            "count_s": round(count_seconds, 1),
            "count_bad": int(GATE_COUNT / BAD_ERROR_RATE),     # 与档位无关
            "window_bad": window_bad,
            "window_ok": window_bad > threshold_bad,
            "min_window_s": WINDOW_S,
        })
    return rows


def rollback_report() -> dict:
    """回滚那两段的账，以及它与判红相比贵多少。"""
    total_s = ROLLBACK_APPROVE_S + ROLLBACK_EFFECT_S
    at_full = total_s * TOTAL_RPS
    detect = int(GATE_COUNT / BAD_ERROR_RATE)
    return {
        "total_s": total_s,
        "approve_s": ROLLBACK_APPROVE_S,
        "effect_s": ROLLBACK_EFFECT_S,
        "bad_requests": at_full,
        "detect_bad": detect,
        "ratio": round(at_full / detect, 1),
        "at_canary": total_s * (TOTAL_RPS * STEPS[0][0] // 100),
    }
