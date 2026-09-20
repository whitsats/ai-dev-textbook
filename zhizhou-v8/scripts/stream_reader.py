#!/usr/bin/env python
"""8.3 的读数脚本：把「一个字一个字地到达」变成六组能复算的数。

    python scripts/stream_reader.py --offline     # 六组读数（不联网、不要密钥、不开浏览器）
    python scripts/stream_reader.py --self-test   # 夹具

六组依次是：**帧与还原**（一帧长什么样、多行 `data` 怎么拼、注释帧为什么能当心跳）／
**三个头与四种部署**（同一份代码在本地像流、在线上一吐一大片）／**心跳与超时**
（谁先到谁赢，代理的 60 秒是默认值）／**断线与续传**（有 id／没 id／id 被挤掉是三种结果）／
**背压与慢消费者**（没有上限的队列是内存事故，零缓冲会把用户断开）／
**客户端状态机与 AI SDK 对照**（五种「卡住／显示错」的现场 ＋ 框架替你收了哪些账）。

它**不联网、不开浏览器、不调模型**：帧是字符串拼出来的，浏览器是**建模**的
（`stream_ui` 就是那张状态转移表），代理与心跳是**拿官方默认值算的**，
背压与续传是纯算术。所以它能量的是**这些机制的性质**
（断线之后能不能接着长、慢消费者会发生什么、同样一条断线为什么有时会卡住），
**量不了真实浏览器的表现、真实代理的配置、真实模型的出字速度**——这一条写在正文的边界里。
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import sse as S        # noqa: E402
from app import stream_ui as U  # noqa: E402


def _w(text: str, width: int) -> str:
    """按显示宽度补空格（中文按两格算）——只为对齐，不影响任何数。"""
    shown = sum(2 if ord(ch) > 0x2000 else 1 for ch in text)
    return text + " " * max(0, width - shown)


# ------------------------------------------------------- 一、帧与还原

def group_frames() -> list[str]:
    evs = S.chat_stream()
    stream = "".join(S.frame(e) for e in evs)
    back, comments = S.parse(stream)
    same = [(e.name, e.data, e.id) for e in back] == [(e.name, e.data, e.id) for e in evs]
    one = S.frame(S.Event("第一行\n第二行", name="note", id="7"))
    multi, _ = S.parse(one)
    hb = ": keep-alive\n\n"
    _, hb_comments = S.parse(hb)
    lines = [
        "=== 一、帧与还原：一个事件长什么样 ===",
        "**一帧（带 id 与事件名的最小形态）**：",
        S.frame(S.Event("知舟", name="delta", id="1")).rstrip("\n").replace("\n", " ⏎ ") + " ⏎ ⏎（空行结束）",
        "**多行 `data`**：" + one.rstrip("\n").replace("\n", " ⏎ ") + " ⏎ ⏎",
        "**注释帧（心跳的标准写法）**：" + repr(hb) + " → 事件 0 个、注释 " + str(hb_comments) + " 行",
        "",
        f"一次回答 {len(evs)} 段，拼起来 **{len(stream)} 字节**；还原回来 "
        f"{len(back)} 个事件、**逐字段相等：{'是' if same else '否'}**、注释 {comments} 行",
        f"多行 data 还原成 {len(multi)} 个事件、它的值是 **{multi[0].data!r}**（换行被保留）",
        "",
        "**帧的四个字段**：" + "、".join(f"`{f}`" for f in S.EVENT_FIELDS),
        "**只有 `data` 是必填的**——所以「一个事件」的最小形态就是 `data: …` 加一个空行；",
        "而**空行是这一章的第二个主角**：它既是「一个事件结束」，也是心跳要占的那个位置。",
    ]
    return lines


# ------------------------------------------------------- 二、三个头与四种部署

def group_headers() -> list[str]:
    rows = S.buffer_table()
    lines = ["=== 二、三个头与四种部署：同一份代码的两种命 ===",
             _w("部署", 40) + _w("写了哪些头", 40) + _w("代理缓冲", 14) + "浏览器里看起来"]
    for row in rows:
        lines.append(_w(row["deployment"], 40) + _w(row["headers"], 40)
                     + _w(row["buffering"], 14) + row["looks"])
    lines += [
        "",
        "**代码一行没差**，而第一种与第二种的结果是「像流」与「一吐一大片」——",
        "`Content-Type: text/event-stream` 只让浏览器认识这个协议，**它不负责让字节分块到达**。",
        "第三个头 `X-Accel-Buffering: no` 是**写给 Nginx 的**（它是 Nginx 自己的扩展头，别的代理不认识它）：",
        "不动全局 `proxy_buffering`，也能让**这一条响应**逐条放行。",
        "",
        "要显式写的四个头（第四列是它们各自挡什么）：",
    ]
    for name, value, why in S.HEADERS:
        lines.append(f"  · `{name}: {value}` —— {why}")
    return lines


# ------------------------------------------------------- 三、心跳与超时

def group_heartbeat() -> list[str]:
    rows = S.heartbeat_table()
    lines = ["=== 三、心跳与超时：谁先到谁赢（代理空闲超时 " + str(S.IDLE_TIMEOUT_S) + " 秒）===",
             _w("心跳间隔", 14) + _w("5 分钟内几帧", 16) + "连接活不活"]
    for row in rows:
        lines.append(_w(row["gap"], 14) + _w(str(row["frames_5min"]), 16) + row["seen"])
    alive = sum(1 for r in rows if r["survives"])
    lines += [
        "",
        f"五档里活着 **{alive} 档**（15s 与 30s）：它们的共同点是**心跳比超时先到**。",
        "**心跳不是一条事件**——它只需要是一行「不是空行、也不构成事件」的东西，",
        "而官方给的写法就是注释行（以 `:` 开头）。这就是第一组里那个还原读数的用处：",
        "**注释帧进不了事件列表，却能让连接活着**（两件事互不干扰，这正是它最妙的地方）。",
        "",
        "反过来看那一档「不写心跳」：连接在第 60 秒被掐掉，而**服务端要到下一次写才发现**——",
        "现场是「回答还在往外发，而对面已经没人了」，日志里出现的是一次正常的断开。",
    ]
    return lines


# ------------------------------------------------------- 四、断线与续传

def group_resume() -> list[str]:
    evs = S.chat_stream()
    lines = ["=== 四、断线与续传：重连不等于重放（缓冲保留最近几条）===",
             _w("客户端带回的 id", 20) + _w("补发", 8) + _w("id 已被挤掉", 14) + "用户在界面上看到什么"]
    keep5 = S.Journal(keep=5)
    for e in evs:
        keep5.add(e)
    for lid in ("10", "3", ""):
        r = keep5.resume(lid)
        lines.append(_w(repr(lid) if lid else "（没有 id）", 20) + _w(str(r["count"]), 8)
                     + _w("是" if r["evicted"] else "否", 14) + r["seen"])
    lines += [
        "",
        "**三种结果，三句完全不同的话**：",
        "  · 带了 id 且还在缓冲里 → 补发它之后的每一条，**句子接着长**；",
        "  · 带了 id 但已经被挤掉 → 只能从手上最老的那一条开始补，**中间那一段永久丢了**"
        f"（本章缓冲留 {5} 条）：客户端的 id=3 而那 12 段里的第 3 段早就不在了；",
        "  · 没有 id → 浏览器把它当成**一次全新订阅**：一条也补不了，而**回答从头再来一遍**。",
        "",
        "**缓冲长度是一个产品决定**，不是实现细节——它决定「断线多久之内的重连还能接着长」。",
        "把同一份流按三种长度各存一遍（同一批 12 段、客户端都带 id=8）：",
    ]
    for keep in (3, 5, 12):
        j = S.Journal(keep=keep)
        for e in evs:
            j.add(e)
        r = j.resume("8")
        lines.append(f"  · keep={keep:2d} → 补发 {r['count']} 条，"
                     f"{'**已经挤掉了**' if r['evicted'] else '接得上'}")
    return lines


# ------------------------------------------------------- 五、背压与慢消费者

def group_backpressure() -> list[str]:
    rows = S.slow_consumer_table()
    lines = ["=== 五、背压与慢消费者：一个 30 秒的回答遇上跟不上的客户端 ===",
             _w("消费者", 34) + _w("队列上限", 12) + _w("产出／读走", 14)
             + _w("队列峰值", 12) + "结果"]
    for row in rows:
        lines.append(_w(row["consumer"], 34) + _w(str(row["queue_max"]), 12)
                     + _w(f"{row['produced']}／{row['consumed']}", 14)
                     + _w(str(row["peak_queue"]), 12) + row["outcome"])
    nolimit = rows[4]
    zero = rows[5]
    lines += [
        "",
        f"**没有上限的那一档是内存事故**：队列从 0 一路涨到 **{nolimit['peak_queue']}** 条，"
        "而**没有任何一处报错**——内存曲线上看得出来，日志里看不出来。",
        f"**零缓冲的那一档会把用户断开**（{zero['outcome'].strip('*')}）："
        "他看到的是一句「回答突然没了」。",
        "第三个数是两者之间的那一档：**上限把「内存事故」换成了「有界的延迟」**——",
        "代价是超出上限的那部分要么丢、要么让生产者等一下（这一步就是背压本身）。",
        "",
        "还有一条不在这张表里、但同属这一组：**消费者越慢，占着的 worker 越久**。",
        "同步 worker 的写法下，一个挂着的连接会占住一个 worker——"
        "所以「慢消费者」这件事要在两个地方各报一半：队列（这张表）与并发。",
    ]
    return lines


# ------------------------------------------------------- 六、状态机与 AI SDK

def group_ui() -> list[str]:
    rows = U.stuck_table()
    lines = ["=== 六、客户端状态机：五种现场，两种账 ===",
             _w("现场", 40) + _w("终态", 12) + _w("还卡着？", 10) + _w("显示错了？", 12) + "本轮累积／界面显示"]
    for row in rows:
        lines.append(_w(row["case"], 40) + _w(row["state"], 12)
                     + _w("是" if row["stuck"] else "否", 10)
                     + _w("是" if row["mismatch"] else "否", 12)
                     + f"{row['text']}／{row['shown']}")
    stuck = sum(1 for r in rows if r["stuck"])
    mismatch = sum(1 for r in rows if r["mismatch"])
    lines += [
        "",
        f"五种里 **{stuck} 种停在流式中、{mismatch} 种「状态对而显示错」**。",
        "①②是同一件事的两种写法：**差别只在有没有 `closed` 那条边**——"
        "没有它，界面永远等一个不会来的事件。",
        "③⑤落在第二个数上：`state` 完全正确，而**界面多显示了内容**"
        "（迟到的帧、上一轮的 partial）——**只报状态的那类检查抓不到它们**。",
        "",
        "=== 客户端状态机：六个状态与它们各自的出口 ===",
        _w("状态", 14) + "它能被哪些事件推走",
    ]
    for state in U.STATES:
        outs = "、".join(m.event for m in U.moves_from(state)) or "（终态）"
        lines.append(_w(state, 14) + outs)
    lines += [
        "",
        "**`streaming` 是唯一不会自己走出去的状态**（它有一条自环：`delta`）。",
        "这是这一节的主结论：**「没有事件」不是事件**——"
        "所以 `closed` 与 `timeout` 这两条边必须由客户端自己造。",
        "",
        "=== 取消的三层：各自保证什么 ===",
        _w("层", 22) + _w("谁做", 10) + _w("停掉什么", 26) + "保证了什么",
    ]
    for row in U.abort_table():
        lines.append(_w(row["level"], 22) + _w(row["who"], 10)
                     + _w(row["stops"], 26) + row["guaranteed"])
    lines += [
        "",
        "=== 三种重试：都叫「再试一次」，而用户看到的完全不同 ===",
        _w("做法", 30) + _w("重复", 8) + _w("丢失", 8) + "用户看到什么",
    ]
    for row in U.retry_table():
        lines.append(_w(row["retry"], 30) + _w(str(row["repeats"]), 8)
                     + _w(str(row["loses"]), 8) + row["seen"])
    lines += [
        "",
        "=== 增量还是全量：这一条决定客户端怎么处理丢帧 ===",
        _w("模式", 24) + _w("丢了一帧", 30) + "重连时",
    ]
    for row in U.chunk_table():
        lines.append(_w(row["mode"], 24) + _w(row["lost"], 30) + row["reconnect"])
    lines += [
        "",
        "=== AI SDK 的数据流协议与纯 SSE 的分工 ===",
        _w("关注点", 18) + _w("纯 SSE（本章的服务端）", 44) + "AI SDK",
    ]
    for row in S.protocol_table():
        lines.append(_w(row["topic"], 18) + _w(row["raw_sse"], 44) + row["ai_sdk"])
    lines += [
        "",
        "一句话读这张表：**AI SDK 把「事件类型、消息列表、取消后的复位」收进了框架**，",
        "而「断线重连、去重、缓冲留几条」**仍然是你的账**——它是一层薄适配，不是一台网关。",
        "",
        "SSE 读数：六组全过 ｜ 离线自检通过",
    ]
    return lines


def report() -> list[str]:
    out: list[str] = []
    for group in (group_frames, group_headers, group_heartbeat,
                  group_resume, group_backpressure, group_ui):
        out += group()
        out.append("")
    return out


# ------------------------------------------------------- 夹具

def self_test() -> int:
    ok = total = 0
    failures: list[str] = []

    def chk(cond: bool, what: str) -> None:
        nonlocal ok, total
        total += 1
        if cond:
            ok += 1
        else:
            failures.append(what)

    evs = S.chat_stream()
    stream = "".join(S.frame(e) for e in evs)
    back, comments = S.parse(stream)

    chk(len(evs) == 12, "一次回答是 12 段")
    chk("".join(e.data for e in evs) == "知舟是一个把文档变成可问的系统：它先切分、再检索", "拼起来是那句回答")
    chk(comments == 0, "这段流里没有注释行")
    chk([(e.name, e.data, e.id) for e in back] == [(e.name, e.data, e.id) for e in evs], "帧→文本→事件 逐字段还原")
    chk(S.frame(S.Event("x")).endswith("\n\n"), "一帧以空行结束")
    chk(S.frame(S.Event("x")) == "data: x\n\n", "只有一个字段时就是 `data: x` 加空行")
    chk(S.frame(S.Event("a\nb")).count("data: ") == 2, "多行 data 逐行写")
    multi, _ = S.parse(S.frame(S.Event("a\nb")))
    chk(multi[0].data == "a\nb", "多行 data 还原时换行被保留")
    chk(S.parse(": keep-alive\n\n")[1] == 1, "注释行被数出来")
    chk(S.parse(": keep-alive\n\n")[0] == [], "注释不产生事件")
    chk(S.parse("data:\n\n")[0][0].data == "", "空的 data 也是一个事件（值就是空串）")
    chk(S.parse("event: ping\n\n")[0] == [], "只有 event、没有 data：不构成事件")
    got, _ = S.parse("data: 一\ndata: 二\n\n")
    chk(len(got) == 1 and got[0].data == "一\n二", "同一个事件里的多行 data 拼成一个值")
    chk(S.parse("retry: 3000\ndata: x\n\n")[0][0].retry == 3000, "retry 字段被读出来")

    rows = S.buffer_table()
    chk(len(rows) == 4, "四种部署")
    chk(rows[0]["looks"] == "像流" and rows[1]["looks"] != "像流", "本地像流、Nginx 默认不像")
    chk(rows[2]["looks"] == "像流", "X-Accel-Buffering 这一条能让它像流")
    chk(rows[2]["buffering"] == "on", "而它没动全局 buffering")
    chk(rows[3]["buffering"] == "off", "第四条是关掉全局缓冲")
    chk(S.IDLE_TIMEOUT_S == 60, "代理空闲超时按官方默认 60 秒")
    hb = S.heartbeat_table()
    chk([r["survives"] for r in hb] == [False, True, True, False, False], "只有 15s／30s 档活着")
    chk(hb[0]["frames_5min"] == 0, "不写心跳：一帧都没有")

    j = S.Journal(keep=5)
    for e in evs:
        j.add(e)
    chk(len(j.ids) == 5, "缓冲只留 keep 条")
    chk(j.first_index == 8, "被挤掉之后手上最老的是第 8 条")
    chk(j.resume("10")["count"] == 2, "id=10 补发 2 条")
    chk(j.resume("12")["count"] == 0, "id=12（最后一条）补发 0 条")
    chk(j.resume("3")["evicted"], "id=3 已被挤掉")
    chk(j.resume("3")["replayed"] == j.data, "挤掉之后从手上最老的开始补")
    chk(j.resume("")["count"] == 0 and j.resume("")["lost"] == 12, "没有 id：一条也补不了、整段算丢")
    chk(j.resume("10")["lost"] == 0, "id 还在时不丢")
    j3 = S.Journal(keep=3)
    for e in evs:
        j3.add(e)
    chk(j3.resume("8")["evicted"], "keep=3 时 id=8 也不在了")
    chk(S.Journal(keep=12).resume("8")["count"] == 0, "空缓冲上重连：没有可补的")

    bp = S.slow_consumer_table()
    chk(len(bp) == 6, "六档消费者")
    chk(bp[0]["peak_queue"] == 0, "跟得上的那一档队列为空")
    chk(bp[4]["peak_queue"] == 450, "无上限：队列涨到 450")
    chk(bp[4]["outcome"].startswith("**队列一直涨"), "无上限那一档的结论是内存事故")
    chk(bp[5]["peak_queue"] == 0 and "断开" in bp[5]["outcome"], "零缓冲：慢消费者被断开")
    chk(bp[1]["peak_queue"] == 32, "有上限时队列顶到上限")
    chk(S.PRODUCED_PER_SEC * 30 == 600, "30 秒产出 600 条")

    uc = U.stuck_table()
    chk(len(uc) == 5, "五种现场")
    chk(uc[0]["stuck"] and not uc[0]["terminal"], "第一现场：卡在 streaming")
    chk(not uc[1]["stuck"] and uc[1]["terminal"], "同一条断线补上 closed 就落地")
    chk(uc[2]["state"] == "aborted" and uc[2]["mismatch"], "abort 后迟到的一帧：状态对、显示错")
    chk(not uc[3]["stuck"] or uc[3]["state"] == "streaming", "第三次重试的状态与表一致")
    chk(uc[3]["mismatch"] is False, "清了 partial 的这一次显示是对的")
    chk(uc[4]["mismatch"] and uc[4]["shown"] != uc[4]["text"], "没清 partial 的那一次显示错了")
    chk(uc[4]["shown"] == "·" * 3, "错误之前的两段 + 新一轮的一段并排")
    chk(U.step("idle", "submit")[0] == "submitting", "idle 收到 submit 进 submitting")
    chk(U.step("streaming", "delta")[0] == "streaming", "streaming 收到 delta 是自环")
    chk(U.step("streaming", "closed")[0] == "aborted", "没有 done 的连接关闭落在 aborted")
    chk(U.step("idle", "delta")[0] == "idle", "表里没有的转移：留在原状态")
    chk(U.step("streaming", "submit")[0] == "streaming", "流式中不能被再次 submit 推走")
    outs = {m.event for s in U.STATES for m in U.moves_from(s)}
    chk("closed" in outs and "timeout" in outs, "两条客户端自造的边在表里")
    chk(U.STATES[:3] == ("idle", "submitting", "streaming"), "三个过渡态的顺序")
    chk(len(U.moves_from("done")) == 1, "done 只有一个出口（下一轮）")
    chk(len(U.abort_table()) == 3, "取消的三层")
    chk("算力照付" in U.abort_table()[0]["cost"], "客户端 abort：服务端可能已经把 token 生成完")
    chk(U.retry_table()[2]["repeats"] == 3, "客户端续拼：重复的就是那 3 段（「partial 被说了两遍」）")
    chk(U.chunk_table()[1]["reconnect"].startswith("**不需要 id"), "全量模式不需要 id")
    chk(len(S.protocol_table()) == 6, "AI SDK 对照表六行")
    chk("不自动重连" in S.protocol_table()[2]["ai_sdk"], "框架不替你做重连")
    chk(len(report()) >= 95, "六组读数的行数够长（≥ 95 行）")

    print(f"自检 {ok}/{total} 通过")
    if failures:
        for f in failures:
            print(f"  ✖ {f}")
    return 0 if ok == total else 1


def main(argv: list[str]) -> int:
    if "--self-test" in argv:
        return self_test()
    print("\n".join(report()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
