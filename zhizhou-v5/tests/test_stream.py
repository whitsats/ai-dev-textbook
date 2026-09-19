# tests/test_stream.py —— 不需要密钥、不需要网络：SSE 契约与三条坏形态
"""这一份测的是 5.7 的流式那一半。九组断言：

1. **编解码往返**：`encode` → `parse` 之后的字段一个不差；
2. **多行载荷**：带换行的 JSON 必须被拆成多行 `data:`，而客户端拼回来是**同一段**；
3. **心跳是注释行**：`parse` 认它是 comment，`check` 不把它算成事件；
4. **心跳不占编号**：发若干心跳之后 `next_id` 一动不动——
   这是全章最容易写错的一处（做成 `event: ping` 就会让续传补错位置）；
5. **编号严格递增**：`check` 对乱序与重复都要报；
6. **`retry` 必须是整数**：传 `1500.0` 出去要写成 `retry: 1500`——
   规范里「非整数则忽略」，而「忽略了」与「没写」在客户端完全一样；
7. **断线续传不重不漏**：`resume(last_id)` 补出来的帧拼在已收内容之后**恰好等于全文**；
8. **三条坏形态的夹具**：乱序、重复、缺 `done`——`check` 三条都必须抓到
   （这是「服务端自己也要能解自己的流」的全部理由）；
9. **发布顺序**：来源在正文之前、`done` 在最后。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.stream import (HEARTBEAT, Frame, StreamLog, StreamWriter,      # noqa: E402
                        check, comment, encode, parse, publish, sse_frame)


def test_编解码往返() -> None:
    frame = Frame("event", event="token", data='{"content":"知舟"}', id=7, retry=1500)
    text = encode(frame)
    assert text.endswith("\n\n")
    got = parse(text)
    assert len(got) == 1
    assert (got[0].kind, got[0].event, got[0].data, got[0].id) == \
        ("event", "token", '{"content":"知舟"}', 7)
    assert got[0].retry is None or got[0].retry == 1500


def test_多行载荷拆成多行data() -> None:
    payload = "第一行\n第二行"
    text = encode(Frame("event", event="note", data=payload, id=1))
    assert text.count("data: ") == 2, text
    assert parse(text)[0].data == payload, "客户端拼回来必须与原文一字不差"


def test_心跳是注释行且不带编号() -> None:
    writer = StreamWriter()
    before = writer.next_id
    beats = [writer.heartbeat() for _ in range(3)]
    assert all(b.strip().startswith(":") for b in beats)
    assert HEARTBEAT.startswith(":")
    assert writer.next_id == before, "心跳**不能**推进编号"
    assert all(f.kind == "comment" for f in parse("".join(beats)))
    # 夹着心跳的一整条流必须照样通过：心跳既不算事件、也不占编号
    text = publish(writer, sources=["发布规范#0"], segments=["甲", "乙"], beats=1)
    assert any(f.kind == "comment" for f in parse(text)), "beats=1 应当插进心跳"
    assert check(text) == ()
    # 而只有心跳的流必须被后一条抓到：心跳再多也构不成「生成完了」
    assert check("".join(beats)) == ("流没有以 done 结尾",)
    assert comment("ping") == ": ping\n\n"


def test_编号严格递增() -> None:
    writer = StreamWriter()
    text = writer.open() + writer.event("sources", []) + writer.event("token", {"c": "a"}) \
        + writer.event("done", {})
    assert check(text) == ()
    ids = [f.id for f in parse(text) if f.kind == "event" and f.event != "open"]
    assert ids == sorted(set(ids)) and len(ids) == len(set(ids))


def test_retry必须是整数() -> None:
    text = encode(Frame("event", event="open", data="{}", retry=1500.0))
    assert "retry: 1500\n" in text, "写成 1500.0 会被客户端整条忽略"
    assert "retry: 1500.0" not in text


def test_断线续传不重不漏() -> None:
    writer = StreamWriter()
    segments = ["知舟的", "发布说明", "必须包含", "四段"]
    sent = writer.open() + "".join(writer.event("token", {"content": s}) for s in segments) \
        + writer.event("done", {"segments": len(segments)})
    # 客户端在收到第 2 段之后断了：它手上是 open + 前两段（第一段是 sources）
    received = writer.open() + encode(writer.log.frames[0]) + encode(writer.log.frames[1])
    last_id = parse(received)[-1].id
    assert last_id == 2
    tail = "".join(writer.resume(last_id))
    assert tail, "必须能补出后续帧"
    whole = received + tail
    assert check(whole) == (), check(whole)
    tokens = [f.data for f in parse(whole) if f.event == "token"]
    assert tokens == [json.dumps({"content": s}, ensure_ascii=False) for s in segments], tokens
    assert [f.event for f in parse(whole) if f.kind == "event"][-1] == "done"
    # 缓存的窗口有限：超出窗口的老帧补不回来，这一点要能被读出来
    small = StreamLog(max_items=2)
    w2 = StreamWriter(log=small)
    w2.open()
    for s in segments:
        w2.event("token", {"content": s})
    assert len(small.replay(0)) == 2, "窗口只留 2 帧——续传的上限由它决定"


def test_三条坏形态都必须被check抓到() -> None:
    good = (sse_frame("sources", [], id=1) + sse_frame("token", {"content": "甲"}, id=2)
            + sse_frame("token", {"content": "乙"}, id=3) + sse_frame("done", {"n": 2}, id=4))
    assert check(good) == ()
    # ① 乱序：编号倒退
    out_of_order = (sse_frame("sources", [], id=1) + sse_frame("token", {"content": "甲"}, id=3)
                    + sse_frame("token", {"content": "乙"}, id=2)
                    + sse_frame("done", {}, id=4))
    issues = check(out_of_order)
    assert any("严格递增" in i for i in issues), issues
    # ② 重复：同一编号发了两次（补发重复）
    duplicated = (sse_frame("sources", [], id=1) + sse_frame("token", {"content": "甲"}, id=2)
                  + sse_frame("token", {"content": "甲"}, id=2) + sse_frame("done", {}, id=3))
    issues = check(duplicated)
    assert any("出现了多次" in i for i in issues), issues
    # ③ 缺 done：客户端分不清「生成完了」与「连接断了」
    no_done = sse_frame("sources", [], id=1) + sse_frame("token", {"content": "甲"}, id=2)
    assert "流没有以 done 结尾" in check(no_done)


def test_发布顺序来源在前done在后() -> None:
    writer = StreamWriter()
    text = publish(writer, sources=["发布规范#0", "调用预算#0"], segments=["甲", "乙"])
    events = [f.event for f in parse(text) if f.kind == "event"]
    assert events == ["open", "sources", "token", "token", "done"], events
    assert check(text) == ()


def run() -> int:
    """不依赖 pytest 的跑法：`python tests/test_stream.py`。"""
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
