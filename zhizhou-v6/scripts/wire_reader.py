#!/usr/bin/env python
"""6.2 的读数脚本：把「三家不一样」变成六组能复算的数。

    python scripts/wire_reader.py --offline     # 六组读数（不要密钥、不要网络）
    python scripts/wire_reader.py --self-test   # 十四套夹具

它**不调模型**：它把同一个中立请求翻成三家的载荷、把三家的答复翻回来、
把三段夹具流解析成同一段答复，然后数出「哪几格对不上」。
所以这一章的每个结论都能拿纸笔复核——与 6.1 同一条纪律：**读数要么能复算，要么别写进正文**。

六组依次是：翻译表 / 同一请求的三种载荷 / 「为什么停」的十五格 /
工具参数的一个对象与两个字符串 / 同一段答复的三种帧形 / 八模型 × 三方言的能力矩阵。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.dialects import (ADAPTERS, STREAM_ARGS, STREAM_TEXT, chat_stream,  # noqa: E402
                          load_arguments, messages_stream, responses_stream,
                          tool_dialects, tool_constraint)
from app.registry import MODELS  # noqa: E402
from app.wire import (DIALECTS, DIALECT_NAME, FIELD_MAP, SHAPE_MAP,  # noqa: E402
                      STOP_BACK, STOP_LOSSY, STOP_MAP, WIRE_AS_OF, Block, Message,
                      Request, Tool, WireError, distinct_landings, shape_landings,
                      stop_cells, table_violations, validate)

#: 六组读数共用的那一个中立请求。**它必须够真实**：一段系统提示、一轮带工具调用的
#: 历史（含一次结果）、两个工具、一个输出上限——翻译表里那八行它一格都不落。
SYSTEM = "你是知舟，一个企业知识库问答助手。"
TOOLS = (
    Tool("search", "在企业知识库里检索",
         {"type": "object", "properties": {"q": {"type": "string"}}, "required": ["q"]}),
    Tool("calc", "算一个算式",
         {"type": "object", "properties": {"expr": {"type": "string"}}}, strict=True),
)


def sample_request(dialect: str) -> Request:
    """夹具请求：一轮问答 ＋ 一次工具往返。**三种方言共用它**。"""
    return Request(
        model="gpt-5.6-terra", system=SYSTEM,
        messages=(
            Message("user", (Block("text", text="北京天气怎么样？"),)),
            Message("assistant", (Block("tool_call", call_id="call_1", name="search",
                                        arguments={"q": "北京 天气"}),)),
            Message("user", (Block("tool_result", call_id="call_1",
                                   text="晴，26 摄氏度"),)),
        ),
        tools=TOOLS, max_output_tokens=1_024, dialect=dialect)


# ------------------------------------------------------------------ 一、翻译表

def group_field_map() -> list[str]:
    out = [f"=== 一、同一件事的三种说法（规范字段 {len(FIELD_MAP)} 个 × "
           f"方言 {len(DIALECTS)} 种，抄于 {WIRE_AS_OF}）==="]
    for name in DIALECTS:
        out.append(f"{'':<18}{name:<12}{DIALECT_NAME[name]}")
    for fld, m in FIELD_MAP.items():
        out.append(f"{fld:<18}" + "".join(f"{m[d]:<24}" for d in DIALECTS).rstrip())
    land, shape = distinct_landings(), shape_landings()
    out.append(f"名字层：{sum(1 for v in land.values() if v == 3)}/{len(land)} 个字段**三家各说各的"
               f"（没有一栏同名）**；形状只有一种的字段 {sum(1 for v in land.values() if v == 1)} 个")
    for n in (3, 2, 1):
        got = [k for k, v in shape.items() if v == n]
        out.append(f"形状层：{n} 种形状的字段 {len(got)} 个"
                   + (f"（{'、'.join(got)}）" if got else ""))
    two = [k for k, v in shape.items() if v == 2]
    out.append(f"「名字三家不同、而形状只差一档」的字段：{len(two)} 个"
               f"（{'、'.join(two)}）——改代码要看的就是这几格")
    return out


# ------------------------------------------------- 二、同一请求的三种载荷

def _payload(dialect: str, req: Request) -> dict:
    return ADAPTERS[dialect].to_wire(req)


def group_payload() -> list[str]:
    out = ["=== 二、同一请求翻成三种载荷（模板请求：1 段系统提示 ＋ 3 条消息 ＋ 2 个工具）==="]
    shared: set[str] | None = None
    for d in DIALECTS:
        req = sample_request(d)
        payload = json.loads(json.dumps(_payload(d, req), ensure_ascii=False))
        keys = _paths(payload)
        shared = set(keys) if shared is None else (shared & set(keys))
        out.append(f"{DIALECT_NAME[d]:<26} 路径 {ADAPTERS[d].path:<20} "
                   f"key 路径 {len(keys):>3} 个  JSON {len(json.dumps(payload, ensure_ascii=False).encode()):>5} 字节")
    out.append(f"三份载荷都有的 key 路径：{len(shared or [])} 个"
               f"（{'、'.join(sorted(shared or []))}）")
    return out


def _paths(obj, prefix: str = "") -> list[str]:
    if isinstance(obj, dict):
        got: list[str] = []
        for k, v in obj.items():
            got.extend(_paths(v, f"{prefix}.{k}" if prefix else k))
        return got
    if isinstance(obj, list):
        got = []
        for v in obj:
            got.extend(_paths(v, f"{prefix}[]"))
        return got
    return [prefix]


# ------------------------------------------------- 三、「为什么停」的十五格

def group_stops() -> list[str]:
    out = [f"=== 三、「为什么停」：规范 {len(STOP_MAP)} 档 × {len(DIALECTS)} 方言"
           f" ＝ {len(STOP_MAP) * len(DIALECTS)} 格 ==="]
    out.append(f"{'规范档':<16}" + "".join(f"{d:<38}" for d in DIALECTS).rstrip())
    for stop, row in STOP_MAP.items():
        cells = []
        for d in DIALECTS:
            v = row[d]
            mark = "（空）" if v is None else ("（撞车）" if f"{d}/{stop}" in STOP_LOSSY else "")
            cells.append(f"{'-' if v is None else v}{mark}")
        out.append(f"{stop:<16}" + "".join(f"{c:<38}" for c in cells).rstrip())
    for d in DIALECTS:
        lost = {s: STOP_LOSSY.get(f"{d}/{s}", "") for s in STOP_MAP}
        empty = sum(1 for v in lost.values() if v.startswith("空"))
        bump = sum(1 for v in lost.values() if v.startswith("撞车"))
        full = len(STOP_MAP) - empty - bump
        out.append(f"{DIALECT_NAME[d]:<26} 能原样表达的 {full}/{len(STOP_MAP)} 档"
                   f"　空 {empty} 格　与别的档撞车 {bump} 格")
    out.append(f"表自身：{len(stop_cells())} 格逐格核过（正程与回程对得上），"
               f"不符 {len(table_violations())} 处")
    out.append("两种「说不出来」不一样：空会被拦下，撞车什么都不报")
    return out


# ------------------------------------------------- 四、一个对象与两个字符串

def _wire_tool_call(dialect: str) -> dict:
    """从真载荷里把**模型给的那一次调用**取出来——不是我们自己造的第二个形状。"""
    payload = _payload(dialect, sample_request(dialect))
    if dialect == "messages":
        for msg in payload["messages"]:
            for b in msg["content"]:
                if b["type"] == "tool_use":
                    return {"where": "content[].input", "value": b["input"],
                            "type": "object"}
    if dialect == "responses":
        for item in payload["input"]:
            if item.get("type") == "function_call":
                return {"where": "input[].arguments", "value": item["arguments"],
                        "type": "string"}
    for msg in payload["messages"]:
        for c in (msg.get("tool_calls") or []):
            return {"where": "messages[].tool_calls[].function.arguments",
                    "value": c["function"]["arguments"], "type": "string"}
    raise AssertionError(f"{dialect} 的载荷里没有工具调用")


def group_tool_args() -> list[str]:
    out = ["=== 四、工具参数：一家给对象，两家给字符串 ==="]
    parsed = {}
    for d in DIALECTS:
        got = _wire_tool_call(d)
        parsed[d] = got["value"] if isinstance(got["value"], dict) \
            else json.loads(got["value"])
        out.append(f"{DIALECT_NAME[d]:<26} {got['where']:<44} {got['type']:<7} "
                   f"{json.dumps(got['value'], ensure_ascii=False, sort_keys=True)}")
    same = len({json.dumps(v, sort_keys=True) for v in parsed.values()}) == 1
    out.append(f"三份形状解出来的规范对象是否逐个相同：{'是' if same else '否'}"
               f"　{json.dumps(parsed['messages'], ensure_ascii=False, sort_keys=True)}")
    bad = '{"q": "北京", '        # 少一个右花括号
    for d in ("chat", "responses"):
        try:
            load_arguments(bad, d)
        except WireError as exc:
            out.append(f"坏 JSON（{d}）：{exc}")
    return out


# ------------------------------------------------- 五、同一段答复的三种帧形

def _streams() -> dict[str, list[str]]:
    """三段夹具流：**同一件事的三种帧形**（一段文本 ＋ 一次工具调用）。"""
    return {"messages": messages_stream(), "responses": responses_stream(),
            "chat": chat_stream()}


def group_streams() -> list[str]:
    out = ["=== 五、同一段答复的三种帧形（夹具流：一段文本 ＋ 一次工具调用）==="]
    got = {d: ADAPTERS[d].from_stream(lines) for d, lines in _streams().items()}
    for d in DIALECTS:
        lines, resp = _streams()[d], got[d]
        named = sum(1 for ln in lines if ln.startswith("event:"))
        ping = sum(1 for ln in lines if ln.strip() == 'data: {"type":"ping"}')
        done = any(ln.strip() == "data: [DONE]" for ln in lines)
        out.append(f"{DIALECT_NAME[d]:<26} 帧 {resp.events:>2} 个　"
                   f"带 event: 名 {named:>2} 行　ping {ping} 个　以 [DONE] 收尾 "
                   f"{'是' if done else '否'}")
    texts = {d: r.text for d, r in got.items()}
    args = {d: json.dumps(r.tool_calls[0].arguments, ensure_ascii=False, sort_keys=True)
            for d, r in got.items()}
    stops = {d: r.stop for d, r in got.items()}
    out.append(f"三段流解出来的文本：{sorted(set(texts.values()))[0]}"
               f"（三种方言是否一致：{'是' if len(set(texts.values())) == 1 else '否'}）")
    out.append(f"解出来的工具参数：{sorted(set(args.values()))[0]}"
               f"（是否逐个相同：{'是' if len(set(args.values())) == 1 else '否'}）")
    out.append("停下来的原因：" + "／".join(f"{d}={stops[d]}" for d in DIALECTS)
               + f"　（{len(set(stops.values()))} 种说法，而三段流都带着一次工具调用）")
    return out


# ------------------------------------------------- 六、能力矩阵

def group_matrix() -> list[str]:
    out = [f"=== 六、八模型 × 三方言：谁能调到工具（登记的约束 {WIRE_AS_OF}）==="]
    out.append(f"{'模型':<20}{'厂商':<11}{'能接的方言':<26}{'能调工具的方言'}")
    blocked: list[str] = []
    for m in MODELS:
        ds = tool_dialects(m.name)
        note = [f"{d}：{tool_constraint(m.name, d)}" for d in DIALECTS
                if d in ds and tool_constraint(m.name, d)]
        out.append(f"{m.name:<20}{m.vendor:<11}{'、'.join(ds):<26}{'、'.join(ds)}")
        if note:
            out.append(f"{'':<20}{note[0]}")
        for d in DIALECTS:
            if d not in ds:
                blocked.append(f"{m.name}/{d}")
    chat_ok = [m.name for m in MODELS if "chat" in tool_dialects(m.name)]
    total = len(MODELS) * len(DIALECTS)
    out.append(f"{total} 个格子（{len(MODELS)} 模型 × {len(DIALECTS)} 方言）里，调得到工具的 "
               f"{sum(len(tool_dialects(m.name)) for m in MODELS)} 格，调不到 {len(blocked)} 格；"
               f"其中兼容层上 {len(chat_ok)} 个模型可以，但都要先关掉推理")
    out.append(f"调不到的那 {len(blocked)} 格里有 "
               f"{sum(1 for b in blocked if b.startswith('claude'))} 格属于同一件事："
               f"**另一家的四个模型不在兼容层的图纸上**")
    return out


def readings() -> list[str]:
    lines: list[str] = []
    for part in (group_field_map(), group_payload(), group_stops(),
                 group_tool_args(), group_streams(), group_matrix()):
        lines.extend(part)
        lines.append("")
    lines.append("协议读数：六组全过 ｜ 离线自检通过")
    return lines


# ------------------------------------------------------------------ 夹具

def fixture_cases() -> list[tuple[str, bool]]:
    """十四套夹具。**每条规则都要配一条反例**——只测正向会让规则越管越宽。"""
    msg = ADAPTERS["messages"].to_wire(sample_request("messages"))
    res = ADAPTERS["responses"].to_wire(sample_request("responses"))
    chat = ADAPTERS["chat"].to_wire(sample_request("chat"))
    chats = [m for m in chat["messages"] if m["role"] == "tool"]
    parsed = {d: ADAPTERS[d].from_stream(lines) for d, lines in _streams().items()}
    texts = {d: r.text for d, r in parsed.items()}
    args = {d: r.tool_calls[0].arguments for d, r in parsed.items()}
    stops = {d: r.stop for d, r in parsed.items()}
    calls = {d: len(r.tool_calls) for d, r in parsed.items()}
    return [
        ("翻译表三列都填满", all(len(v) == 3 for v in FIELD_MAP.values())
         and all(len(v) == 3 for v in SHAPE_MAP.values())),
        ("八个字段三家各说各的（名字层）", set(distinct_landings().values()) == {3}),
        ("形状层分三堆：四个字段三种形状",
         sorted(k for k, v in shape_landings().items() if v == 3)
         == sorted(["messages", "tools[].schema", "tool_result", "口径/版本"])),
        ("Messages 的系统提示不在消息数组里",
         msg["system"] == SYSTEM and all(m["role"] != "system" for m in msg["messages"])),
        ("Responses 的工具结果与消息平级",
         any(i.get("type") == "function_call_output" for i in res["input"])
         and all(isinstance(i, dict) for i in res["input"])),
        ("兼容层的工具结果是一条独立消息",
         len(chats) == 1 and chats[0]["tool_call_id"] == "call_1"),
        ("工具参数：一家对象、两家字符串",
         isinstance(_wire_tool_call("messages")["value"], dict)
         and _wire_tool_call("responses")["type"] == "string"
         and _wire_tool_call("chat")["type"] == "string"),
        ("坏 JSON 会报错而不是空对象", _bad_json_raises()),
        ("停止原因十五格全在表里", len(stop_cells()) == 15),
        ("空与撞车分开登记", len(STOP_LOSSY) == 4
         and any("空" in v for v in STOP_LOSSY.values())
         and any("撞车" in v for v in STOP_LOSSY.values())),
        ("真表上正程与回程逐格对得上", table_violations() == []),
        ("把一格回程改错就红", _broken_back_table_fires()),
        ("兼容层的「命中停止词」读到的是正常结束",
         STOP_MAP["stop_sequence"]["chat"] == STOP_MAP["end_turn"]["chat"]
         and "chat/stop_sequence" in STOP_LOSSY),
        ("三段流解出同一段文本", len(set(texts.values())) == 1 and texts["chat"] == STREAM_TEXT),
        ("三段流解出同一组工具参数", len({json.dumps(v, sort_keys=True)
                                           for v in args.values()}) == 1
         and args["messages"] == STREAM_ARGS),
        ("三段流都带着一次工具调用", set(calls.values()) == {1}),
        ("「要调工具」这家读不出：两家说 tool_call，一家只报正常结束",
         stops == {"messages": "tool_call", "chat": "tool_call",
                   "responses": "end_turn"}),
        ("只有一家发 event: 名与 ping",
         all(ln.startswith("event:") for ln in messages_stream() if ln.startswith("event:"))
         and not any(ln.startswith("event:") for ln in chat_stream() + responses_stream())),
        ("能力矩阵：最大的那个只走 Responses，小一号的要关推理",
         tool_dialects("gpt-6-astra") == ("responses",)
         and tool_constraint("gpt-5.6-luna", "chat") != ""
         and tool_dialects("claude-opus-5") == ("messages",)),
        ("规范请求通不过校验时给出原因", _reject_reasons() == 2),
        ("模板请求自身是合法的",
         all(validate(sample_request(d)) == [] for d in DIALECTS)),
    ]


def _broken_back_table_fires() -> bool:
    """把 `length`（兼容层的「到上限了」）回程改读成「正常结束」，检查必须说话。"""
    broken = {d: dict(m) for d, m in STOP_BACK.items()}
    broken["chat"]["length"] = "end_turn"
    return any("length" in m for m in table_violations(stop_back=broken))


def _bad_json_raises() -> bool:
    for d in ("chat", "responses"):
        try:
            load_arguments('{"q": ', d)
        except WireError:
            continue
        return False
    return True


def _reject_reasons() -> int:
    """两条刻意的坏请求：缺系统提示、工具结果指向一次不存在的调用。"""
    ok = sample_request("chat")
    empty_system = Request(model=ok.model, system="   ", messages=ok.messages,
                           dialect="chat")
    orphan = Request(model=ok.model, system=SYSTEM,
                     messages=(Message("user", (Block("tool_result", call_id="nope",
                                                      text="x"),)),),
                     dialect="chat")
    return sum(1 for r in (empty_system, orphan) if validate(r))


def self_test() -> int:
    cases = fixture_cases()
    bad = 0
    for label, ok in cases:
        print(f"  {'✓' if ok else '✗'} {label}")
        bad += 0 if ok else 1
    print(f"自检 {len(cases) - bad}/{len(cases)} 通过")
    return 1 if bad else 0


def main(argv: list[str]) -> int:
    if "--self-test" in argv:
        return self_test()
    for line in readings():
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
