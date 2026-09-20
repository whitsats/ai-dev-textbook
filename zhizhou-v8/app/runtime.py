"""运行期的最小权限：镜像跑起来那一刻，**它的权力面有多大**。

前两块管的是「打出来的东西」与「改一行要重打多少」，这一块管**它跑起来之后**。
三件事，各有一条不会报错的默认值：

**① 默认是 root。** 官方写 Dockerfile 的那一页把这件事当成一条最佳实践来说
（「setup an app user so the container doesn't run as root user」）——反过来说，
**不写 `USER` 就是 root**。root 的代价不是「它会作恶」，而是「它作恶的时候没法挡」：
容器里被打穿的那一段代码，权限面与进程本身一样大。

**② 根文件系统默认可写。** 应用需要写的其实只有少数几处（临时目录、库的缓存、
日志），但默认它**到处都能写**。把根文件系统设为只读（`--read-only`）之后，
那几处必须**显式**挂出来——这一步的价值不在于省了什么，而在于**把「它写过哪里」
从「没人知道」变成「一份清单」**。

**③ 构建上下文默认递归包含整个目录。** 官方那页的原话：指定本地目录时**所有子目录
都被包含**；`.dockerignore` 的作用是「在发出去之前把这些路径从上下文里移掉」。
所以「它没有进最终镜像」与「它没有离开这台机器」是两件事——版本历史、
本地虚拟环境、一份测试语料，三者都在后者的范围内。

依据：Docker 官方「Writing a Dockerfile」（`USER` 与那条最佳实践）、
「Build context」（递归包含与 `.dockerignore`「发送前移掉」）、以及 OWASP 的
Docker 安全速查表（`--read-only` 与挂卷那两条）。
"""

from __future__ import annotations

from dataclasses import dataclass

from .image import CONTEXT


# --------------------------------------------------------------- 一、上下文外发

def context_report(ignored: tuple[str, ...] = ()) -> dict:
    """构建上下文发出去多少、里面有哪些**不该离开这台机器**的东西。

    `ignored` 是被 `.dockerignore` 挡下来的路径。**它不改变「一共有什么」，
    只改变「发出去什么」**——这正是这一组的读数与 8.1 的 `.dockerignore` 那一招
    互为两面：那一招看镜像小了没有，这一组看**东西出去了没有**。
    """
    kept = [(p, kb) for p, kb in CONTEXT if p not in ignored]
    sent = sum(kb for _, kb in kept)
    total = sum(kb for _, kb in CONTEXT)
    return {
        "total_kb": total,
        "sent_kb": sent,
        "blocked_kb": total - sent,
        "sent_files": len(kept),
        "total_files": len(CONTEXT),
        "blocked": tuple(p for p, _ in CONTEXT if p in ignored),
    }


#: 该被挡在门外的那几项，与挡它的理由。**版本历史是其中最容易被忽略的一项**：
#: 它不带业务数据，但它带着**每一个历史提交里的每一份曾经存在过的密钥**——
#: 一份 `.env` 就算今天删了，它仍然躺在 `.git` 里。
IGNORE_REASONS: tuple[tuple[str, str], ...] = (
    ("/app/.git", "版本历史（含历史提交里的每一份旧 `.env`）"),
    ("/app/.venv", "本地虚拟环境（目标平台不对，而且它本来会被重建）"),
    ("/app/tests", "测试代码（不必进运行镜像）"),
)


# --------------------------------------------------------------- 二、谁在跑

@dataclass(frozen=True)
class Seat:
    """一种运行姿态：**谁在跑、根文件系统能不能写、另外显式挂了哪些可写路径**。"""

    name: str
    label: str
    user: str                 # "root" / "app"
    rootfs: str               # "rw" / "ro"
    writable: tuple[str, ...] = ()


SEATS: tuple[Seat, ...] = (
    Seat("root-rw", "`USER` 不写 ＋ 根文件系统可写", "root", "rw"),
    Seat("app-rw", "写了 `USER app` ＋ 根文件系统可写", "app", "rw"),
    Seat("app-ro", "写了 `USER app` ＋ 根文件系统**只读**（不挂任何可写路径）", "app", "ro"),
    Seat("app-ro-mount", "同上，但显式挂出那两处真正需要写的路径", "app", "ro",
         writable=("/tmp", "/app/.cache")),
)


#: 这个进程启动时**真的会写**的三处。注意第三处的性质：
#: `/app/logs` 是可选的（日志也能往标准输出走），前两处不行——
#: 临时目录与库的缓存是 import 期就会伸手要的。
NEEDS: tuple[tuple[str, str, bool], ...] = (
    ("/tmp", "临时目录（uvicorn 与多进程启动时要用）", True),
    ("/app/.cache", "库的缓存（嵌入与 tokenizer 会在这里写）", True),
    ("/app/logs", "应用日志目录（也可以只往标准输出写）", False),
)


@dataclass(frozen=True)
class Write:
    """一处写入需求与它在某种姿态下的结果。"""

    path: str
    why: str
    required: bool
    ok: bool
    note: str


def seat_writes(seat: Seat) -> list[Write]:
    """某种姿态下，三处写入各是什么结果。

    判定只有一条：**根文件系统可写，或者这个路径被显式挂出来了**。root 与否
    不改变「通不通」，但它改变「出事时那一段代码能做什么」——所以两者要分开报。
    """
    out: list[Write] = []
    for path, why, required in NEEDS:
        ok = seat.rootfs == "rw" or path in seat.writable
        if ok:
            note = ("以 root 写（没有人能拦住它写别的地方）" if seat.user == "root"
                    else "以普通用户写")
        else:
            note = ("**写不进去**：根文件系统只读，而这个路径没有挂出来" if required
                    else "写不进去（但这一处可以不写：日志还有标准输出这一条路）")
        out.append(Write(path=path, why=why, required=required, ok=ok, note=note))
    return out


def seat_tally(seat: Seat) -> dict:
    """一种姿态的三笔账：写得进去几处、**必须显式声明几处**、权限面有多大。"""
    writes = seat_writes(seat)
    return {
        "seat": seat.name,
        "label": seat.label,
        "ok": sum(1 for w in writes if w.ok),
        "total": len(writes),
        "required_ok": all(w.ok for w in writes if w.required),
        "declared": len(seat.writable),
        "root": seat.user == "root",
        "rootfs": seat.rootfs,
    }


def seat_table() -> list[dict]:
    """四种姿态各一行——**这一组的读数就是它**。"""
    return [dict(seat_tally(seat), writes=seat_writes(seat)) for seat in SEATS]
