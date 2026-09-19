"""实验一：三套上下文手法的账——省了多少、以及**丢掉了什么**。

三种装配方式都只改「送进模型之前的那一段」，模型与任务完全相同：
  A 全量        ：历史一字不动。
  B 清理工具结果：只留最近 2 条工具结果的全文，更早的换成一行摘要（不动用户与助手的话）。
  C 清理＋笔记  ：在 B 之上，把最近 6 条之前的部分压成逐条笔记（每条截到 50 字符）。

**词元用本地编码器数**（`tiktoken`），所以这一段不需要凭据、每次跑都是同一组数。

「事实存活率」是这里真正的一列：任务依赖 6 条事实，分别落在工具结果内部、早期长句的
第 50 字之后、最近几轮。省下的词元如果换成了答不出来，那不叫省，
那叫**把问题挪到下一轮再炸**。
"""
from __future__ import annotations

import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import tiktoken  # noqa: E402

ENC = tiktoken.get_encoding("o200k_base")
count = lambda s: len(ENC.encode(s))                     # noqa: E731


def width(s: str) -> int:
    """按终端显示宽度排表：汉字与全角标点算两格，其余算一格。"""
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in s)


def pad(s: str, n: int) -> str:
    return s + " " * max(0, n - width(s))


SECTIONS = [
    "刷新令牌要解决的问题是：访问令牌必须短期有效，但用户不想每次过期都重新登录。",
    "做法一，滑动过期：每次换新令牌时把刷新令牌也一起换掉，旧的那枚立刻作废；"
    "并发刷新会互相踢掉，工程上常给旧令牌留一个很短的宽限窗口。",
    "做法二，黑名单：刷新令牌长期有效，退出或检测到异常时把它的 jti 写进 Redis，"
    "TTL 设为令牌剩余寿命即可；代价是每次刷新多一次查询。",
    "做法三，版本号：用户表上存 token_version，签发时写进声明，校验时比对；"
    "改密码或强制下线就把版本号加一，该用户所有旧令牌立刻失效。",
    "三种做法可以叠用：滑动过期覆盖常态，版本号覆盖一键下线，"
    "黑名单只留给需要精确到单枚令牌的场景。",
]

# 五条工具结果各不相同：这样「只留最近 2 条」才会真的丢掉更早的信息。
TOOL_SEARCH = ("命中 3 条：《JWT 刷新令牌怎么做》(id 42)、《FastAPI 依赖注入》(id 17)、"
               "《Redis 位图》(id 88)")
TOOL_BODY_1 = ("《JWT 刷新令牌怎么做》正文（第 1–3 段，回给模型时截到 2,000 字符）：\n\n"
               + "\n\n".join(SECTIONS[0:3]))
TOOL_BODY_2 = ("《JWT 刷新令牌怎么做》正文（第 4–6 段）：\n\n"
               + "\n\n".join([SECTIONS[4], SECTIONS[3]]))    # 版本号放在深处：摘要那 40 字符吃不到它
TOOL_BODY_3 = ("《JWT 刷新令牌怎么做》正文（第 7–8 段）：\n\n"
               + "\n\n".join([SECTIONS[0], SECTIONS[4]]))
TOOL_TAGS = '["安全", "后端", "JWT", "部署"]'
TOOL_COUNT = "128"

# 6 条事实，按「被谁丢掉」分布：
#   早期工具结果内部（B 就丢）／早期长句第 50 字之后（只有 C 丢）／最近几轮（都留得住）
FACTS = [
    ("文章 id 是 42", "早期短句，第 25 字"),
    ("宽限窗口", "早期工具结果内部"),
    ("token_version", "早期工具结果内部"),
    ("幂等键 run-7f3a", "早期长句，第 60 字之后"),
    ("发布需要人工确认", "最近一轮"),
    ("最多三个", "最近一轮"),
]

LONG_EARLY_TURN = (
    "起草这一步我按三种做法的顺序排了一遍，并在每段后面标了一行代价与来源，方便你逐段删改；"
    "另外顺带说明一句，这一版用的幂等键 run-7f3a 由循环生成，重跑只会写一次，不会有第二份草稿。"
)

TURNS = [
    ("user", "帮我找一篇讲刷新令牌的文章"),
    ("tool", TOOL_SEARCH),
    ("assistant", "找到了：《JWT 刷新令牌怎么做》（文章 id 是 42）。要读正文吗？"),
    ("user", "读一下，顺便记一下它讲了几种做法，等会儿要按它的口径改稿"),
    ("tool", TOOL_BODY_1),
    ("user", "继续，把后面几段也读出来"),
    ("tool", TOOL_BODY_2),
    ("assistant", "读完了，正文一共八段，可以按它逐段改。"),
    ("user", "还有两段没读"),
    ("tool", TOOL_BODY_3),
    ("user", "作者是谁"),
    ("assistant", "作者的用户 id 是 7，所以你有权限改。"),
    ("user", "给它起草一版，注意不要重复写"),
    ("assistant", LONG_EARLY_TURN),
    ("user", "标签有哪些"),
    ("tool", TOOL_TAGS),
    ("assistant", "标签从「安全 / 后端 / JWT / 部署」里选，最多三个。"),
    ("user", "直接发布吧"),
    ("assistant", "发布需要人工确认，我先停在这里。"),
    ("user", "正文有多长"),
    ("assistant", "正文超过两千字会被截断，回给模型的是前 2,000 字符。"),
    ("user", "帮我数一下总共有多少篇"),
    ("tool", TOOL_COUNT),
    ("user", "好，就这样"),
]

KEEP_TOOL = 2          # B：留最近几条工具结果
KEEP_TURNS = 6         # C：最近几条不压
NOTE_CHARS = 50        # C：笔记每条截多少字符


def clean_tool_results(history, keep_recent: int = KEEP_TOOL):
    """把更早的工具结果换成一行摘要：**只动工具结果**，用户与助手的话不动。"""
    seen = 0
    out = []
    for role, text in reversed(history):
        if role != "tool":
            out.append((role, text))
            continue
        seen += 1
        out.append((role, text) if seen <= keep_recent
                   else ("tool", f"[工具结果已清理：{len(text)} 字符 → {text[:40]}……]"))
    return list(reversed(out))


def note_tail(history, keep_recent_turns: int = KEEP_TURNS):
    """把更早的对话压成逐条笔记：**不调模型**，所以这一步可复现（有损的压缩在 3.6.5）。"""
    if len(history) <= keep_recent_turns:
        return history
    head, tail = history[:-keep_recent_turns], history[-keep_recent_turns:]
    notes = [f"- [{role}] {text[:NOTE_CHARS]}" for role, text in head if role != "tool"]
    return [("note", "早前对话的笔记：\n" + "\n".join(notes))] + tail


def assembled(policy: str):
    if policy == "A 全量":
        return TURNS
    if policy == "B 清理工具结果":
        return clean_tool_results(TURNS)
    return note_tail(clean_tool_results(TURNS))


def render(msgs) -> str:
    return "\n".join(f"{r}: {t}" for r, t in msgs)


def main() -> None:
    n_tool = sum(1 for r, _ in TURNS if r == "tool")
    print(f"== 历史 {len(TURNS)} 条，其中工具结果 {n_tool} 条；任务依赖 {len(FACTS)} 条事实 ==")
    print()
    cols = [("策略", 16), ("最终上下文", 12), ("累计计费输入", 14), ("峰值", 10), ("事实存活", 10)]
    print("".join(pad(t, w) for t, w in cols) + "丢了哪几条")
    for policy in ("A 全量", "B 清理工具结果", "C 清理＋笔记"):
        msgs = assembled(policy)
        total = peak = 0
        for i in range(1, len(msgs) + 1):
            n = count(render(msgs[:i]))
            total += n
            peak = max(peak, n)
        final = render(msgs)
        lost = [f for f, _ in FACTS if f not in final]
        cells = [policy, f"{count(final):,}", f"{total:,}", f"{peak:,}",
                 f"{len(FACTS) - len(lost)}/{len(FACTS)}"]
        print("".join(pad(c, w) for c, (_, w) in zip(cells, cols))
              + ("；".join(lost) if lost else "—"))

    base_msgs = assembled("A 全量")
    base_final = count(render(base_msgs))
    base_peak = max(count(render(base_msgs[:i])) for i in range(1, len(base_msgs) + 1))
    print()
    print(f"相对 A 全量（最终 {base_final:,}／峰值 {base_peak:,}）：")
    for policy in ("B 清理工具结果", "C 清理＋笔记"):
        msgs = assembled(policy)
        final = count(render(msgs))
        peak = max(count(render(msgs[:i])) for i in range(1, len(msgs) + 1))
        print(f"  {policy}：最终 {final:,}（{final / base_final - 1:+.0%}）；"
              f"峰值 {peak:,}（{peak / base_peak - 1:+.0%}）")


if __name__ == "__main__":
    main()
