# tests/agent/test_memory.py —— 不需要密钥：装配的账、重放的合法性、长期记忆的三个闸
"""这一份测的是 3.6 的契约，不是实现细节。四组：

1. **装配**：三套手法都省词元，但「换掉了什么」必须能算出来，且降幅不能是假的；
2. **合法化**：库里存下来的东西装回上下文时，请求必须合法（工具往返成对）；
3. **长期记忆**：同键覆盖、过期不召回、可删、只从用户的话里抽；
4. **跨会话**：新会话历史为空，偏好只能从长期记忆来。

计数用注入的「按字符数」替身：**测试不该依赖编码器版本**，而 `count` 本来就是注入点。
"""
from app.agent import memory as mem
from app.agent.memory import (InMemoryStore, MemoryItem, MemoryWriter, Message, assemble,
                              clean_tool_results, note_tail, render_memory, sanitize, to_openai)
from app.llm.client import Config, RawChat, ToolCall, chat
from app.services.agent_service import AgentService

count = lambda s: len(s)                                # noqa: E731 —— 确定性替身：按字符计


def call(i: str, name: str = "read_article") -> Message:
    return Message("assistant", "", tool_calls=(mem.ToolCall(i, name, '{"article_id": 42}'),))


def history(n_tool: int = 3, pad: int = 200) -> list[Message]:
    """n_tool 轮「声明 → 工具结果」，外加几条对话。工具结果刻意很长。"""
    out: list[Message] = [Message("user", "先找一篇讲刷新令牌的文章")]
    for i in range(n_tool):
        out.append(call(f"c{i}"))
        out.append(Message("tool", "命中一篇——《JWT 刷新令牌怎么做》" * pad, tool_call_id=f"c{i}"))
        out.append(Message("assistant", f"读了第 {i + 1} 篇。"))
    out.append(Message("user", "作者是谁"))
    return out


# ------------------------------------------------------------------ 1. 装配的账

def test_三套手法省下的量与换掉的东西() -> None:
    hist = history()
    full = assemble(hist, policy="full", count=count)
    clean = assemble(hist, policy="clean", count=count)
    note = assemble(hist, policy="note", count=count)

    assert full.saved == 0 and full.dropped_tool_results == 0
    # 三套手法的省下比例必须严格递增，而且账与实际消息数对得上
    assert 0 < clean.saved < note.saved <= 1
    assert clean.dropped_tool_results == 1 and clean.dropped_messages == 0
    assert note.dropped_messages > 0 and clean.dropped_tool_results == 1
    # 「省了」与「丢了」是同一次装配的两个面：省下最多的一定也压掉了最多
    assert note.input_tokens < clean.input_tokens < full.input_tokens


def test_基线取同一窗口下的全量降幅才不会虚高() -> None:
    """窗口截断本身就让请求变小：把它算进「清理的功劳」里，得出的降幅是假的。"""
    hist = history()
    a = assemble(hist, policy="clean", max_messages=6, count=count)
    window = hist[-6:]
    from app.agent.memory import count_messages

    assert a.baseline_tokens == count_messages(sanitize(window)[0], count)
    assert a.baseline_tokens < count_messages(sanitize(hist)[0], count)   # 不是原始历史的全量


def test_策略名不认识就报错而不是静默按全量走() -> None:
    try:
        assemble(history(), policy="auto", count=count)
    except ValueError as exc:
        assert "auto" in str(exc)
    else:
        raise AssertionError("未知策略必须报错")


# ------------------------------------------------------------------ 2. 重放的合法性

def test_孤儿工具结果被丢掉而不是发出去() -> None:
    msgs, dropped = sanitize([Message("tool", "命中 3 条……", tool_call_id="c1")])
    assert msgs == [] and dropped == 1


def test_半截声明会被删掉() -> None:
    """历史停在「assistant 宣布调用、结果还没回来」这一刻：留着它请求同样非法。"""
    hist = [Message("user", "读一下"), call("c9")]
    msgs, dropped = sanitize(hist)
    assert dropped == 1 and [m.role for m in msgs] == ["user"]


def test_笔记折成user而不是发明一个角色() -> None:
    msgs, _ = sanitize([Message("note", "早前对话的笔记：……")])
    assert [m.role for m in msgs] == ["user"]


def test_成对的历史装得出合法请求且tool前面必有声明() -> None:
    hist = history()
    msgs = to_openai(assemble(hist, policy="full", count=count).messages)
    assert [m["role"] for m in msgs[:3]] == ["user", "assistant", "tool"]
    assert msgs[1]["tool_calls"][0]["id"] == "c0"
    assert msgs[1]["tool_calls"][0]["function"]["name"] == "read_article"

    # 一个最小的「服务商校验器」：它只认这三条，而这三条就是 400 的成因。
    open_calls: set[str] = set()
    for m in msgs:
        assert m["role"] in ("user", "assistant", "tool"), m["role"]
        if m["role"] == "assistant":
            for c in m.get("tool_calls", []):
                assert c["id"] not in open_calls
                open_calls.add(c["id"])
        elif m["role"] == "tool":
            assert m["tool_call_id"] in open_calls, "tool 结果没有配对声明"
            open_calls.discard(m["tool_call_id"])
    assert open_calls == set(), "有声明没有结果"


def test_只存结果的写法装不出合法请求() -> None:
    """把「删掉声明、只留结果」当成优化，下一次会话就会在服务商那里 400。"""
    only_results = [Message("user", "读一下"), Message("tool", "正文……", tool_call_id="c1")]
    msgs, dropped = sanitize(only_results)
    assert dropped == 1 and to_openai(msgs) == [{"role": "user", "content": "读一下"}]


def test_压缩笔记优先用模型给的版本() -> None:
    hist = history()
    msgs, cut = note_tail(hist, keep_recent_turns=2, summary="模型压缩出来的三行笔记")
    assert cut == len(hist) - 2 and "模型压缩出来的三行笔记" in msgs[0].content


# ------------------------------------------------------------------ 3. 长期记忆

def test_同键覆盖而不是追加() -> None:
    store = InMemoryStore()
    sid = store.open_session(7, title="t")
    w = MemoryWriter()
    for _ in range(3):
        for item in w.from_turn("以后发布一律先给我看草稿", session_id=sid):
            store.remember(7, item)
    assert [i.key for i in store.recall(7)] == ["pref.publish"]


def test_过期不再召回但没被删掉() -> None:
    store = InMemoryStore()
    w = MemoryWriter()
    fresh = w.from_turn("记住我的语气别太正式")[0]
    store.remember(7, fresh)
    stale = MemoryItem("pref.tone", "旧的", expires_at=fresh.updated_at.replace(year=2000))
    store.remember(7, stale)                    # 同键覆盖：新值反而是过期的那个
    assert store.recall(7) == []
    assert store.forget(7, "pref.tone") == 1    # 还在库里，删得掉
    assert store.forget(7, "pref.tone") == 0


def test_只从用户的话里抽偏好没有线索就不写() -> None:
    w = MemoryWriter()
    assert w.from_turn("今天天气不错，帮我看看 42 号文章") == []
    assert w.from_turn("以后发布一律先给我看草稿")[0].key == "pref.publish"
    assert w.from_turn("记住，标签最多三个")[0].key == "pref.tags"


def test_一轮最多写两条且值被截断() -> None:
    w = MemoryWriter()
    got = w.from_turn("以后发布先给我看草稿。记住我的语气别太正式。标签最多三个。")
    assert len(got) <= w.max_items == 2
    long_text = "以后发布" + "啰" * 999          # 值被截到 max_value，不是整个句子进库
    assert len(w.from_turn(long_text)[0].value) <= w.max_value


def test_任务痕迹活得比偏好短() -> None:
    w = MemoryWriter()
    task = w.from_task("把 42 号文章发布上线", "等待人工确认")
    pref = w.from_turn("以后发布一律先给我看草稿")[0]
    assert pref.expires_at > task.expires_at, "偏好比一次任务痕迹活得久"
    assert "等待人工确认" in task.value


def test_记忆进提示且为空时不占词元() -> None:
    assert render_memory([]) == ""
    text = render_memory([MemoryItem("pref.publish", "先给我看草稿")])
    assert "pref.publish" in text and "冲突时以本次为准" in text


# ------------------------------------------------------------------ 4. 存储、会话与跨会话

def test_会话写回读取与不存在的会话() -> None:
    store = InMemoryStore()
    sid = store.open_session(7, title="刷新令牌")
    store.append(sid, Message("user", "你好"))
    store.append(sid, Message("assistant", "在的"))
    assert [m.role for m in store.history(sid)] == ["user", "assistant"]
    assert len(store.history(sid, limit=1)) == 1
    got = store.transcript(sid)
    assert got["title"] == "刷新令牌" and len(got["messages"]) == 2
    assert got["messages"][0]["content"] == "你好"          # 正文在库里，不在的只是哈希
    try:
        store.transcript(999)
    except KeyError:
        pass
    else:
        raise AssertionError("不存在的会话必须报错")


def scripted(replies):
    """剧本式传输层：让会话链在无凭据时也能端到端跑。`sends` 记下每次发出去几条消息。"""
    seq = list(replies)
    sends: list[int] = []

    def transport(messages, cfg, **kw):
        sends.append(len(messages))
        got = seq.pop(0) if len(seq) > 1 else seq[0]
        if isinstance(got, str):
            return RawChat(got, [], 5)
        return RawChat("", [got], 5) if isinstance(got, ToolCall) else got

    def chat_fn(messages, **kw):
        return chat(messages, transport=transport, **kw)
    chat_fn.sends = sends
    return chat_fn


def service(replies, **kw) -> AgentService:
    chat_fn = scripted(replies)
    svc = AgentService(Config(api_key="x"), sessions=InMemoryStore(), chat_fn=chat_fn, **kw)
    svc.sends = chat_fn.sends          # 只读的观测点：诊断不该让它多一条
    return svc


def test_新会话的历史为空偏好只能来自长期记忆() -> None:
    svc = service([ToolCall("c0", "read_article", '{"article_id": 42}'), "按你之前说的，发布要先看草稿"])
    first = svc.session_chat("记住：以后发布一律先给我看草稿。")
    second = svc.session_chat("把 42 号文章发布上线。", allow_write=True)
    assert second["session_id"] != first["session_id"]
    assert second["memory"]["history_messages"] == 0                 # 新会话一无所知
    assert "pref.publish" in second["memory"]["recalled"]            # 但它记得
    assert "草稿" in second["answer"]


def test_用户这一轮在调模型之前就落库() -> None:
    """写前落库：模型那条路炸了，用户说过的话不能跟着一起丢。"""
    def boom(messages, **kw):
        raise RuntimeError("模型侧炸了")

    svc = AgentService(Config(api_key="x"), sessions=InMemoryStore(), chat_fn=boom)
    sid = svc.open_session("会炸的会话")
    try:
        svc.session_chat("这句必须留下", session_id=sid)
    except RuntimeError:
        pass
    else:
        raise AssertionError("异常必须向上抛，不能吞")
    assert [m.role for m in svc.sessions.history(sid)] == ["user"]


def test_拼错的会话id不会开出假历史() -> None:
    """空历史与「这段会话不存在」是两件事：前者是合法的首轮，后者是一次 bug。"""
    store = InMemoryStore()
    try:
        store.history(999)
    except KeyError as exc:
        assert "999" in str(exc)
    else:
        raise AssertionError("不存在的会话必须报错，而不是返回空数组")

    svc = service([ToolCall("c0", "read_article", '{"article_id": 42}'), "好"])
    try:
        svc.session_chat("这句不该落库", session_id=999)
    except KeyError:
        pass
    else:
        raise AssertionError("端点声称的 404 必须真的会发生")
    assert svc.sessions.recall(7) == []               # 报错前没回写过任何东西
    assert svc.sends == []                            # 也没调过模型：失败在写之前就发生了


def test_跑完的会话能装回合法请求() -> None:
    svc = service([ToolCall("c0", "read_article", '{"article_id": 42}'), "读完了"])
    payload = svc.session_chat("读 42 号文章")
    rows = svc.sessions.history(payload["session_id"])
    assert [m.role for m in rows] == ["user", "assistant", "tool", "assistant"]
    msgs = to_openai(assemble(rows, policy="note", count=count).messages)
    open_calls = {c["id"] for m in msgs if m["role"] == "assistant" for c in m.get("tool_calls", [])}
    assert {m["tool_call_id"] for m in msgs if m["role"] == "tool"} == open_calls
    assert msgs[-1]["role"] == "assistant" and msgs[-1]["content"] == "读完了"


def test_装配诊断不写库也不调模型() -> None:
    svc = service([ToolCall("c0", "read_article", '{"article_id": 42}'), "读完了"])
    payload = svc.session_chat("读 42 号文章")
    sid = payload["session_id"]
    before = len(svc.sessions.history(sid))
    sent = len(svc.sends)
    diag = svc.memory_of(sid, policy="full")
    assert diag["policy"] == "full" and diag["messages"] > 0
    assert diag["saved"] == 0 and len(svc.sessions.history(sid)) == before
    assert len(svc.sends) == sent, "只读诊断不能调模型"


def test_长期记忆可以按用户删掉() -> None:
    svc = service([ToolCall("c0", "read_article", '{"article_id": 42}'), "好"])
    payload = svc.session_chat("记住：以后发布一律先给我看草稿。")
    assert "pref.publish" in payload["memory"]["remembered"]
    assert svc.forget("pref.publish") == 1
    assert "pref.publish" not in svc.memory_of(payload["session_id"])["long_term"]
    assert svc.system_prompt().count("长期记忆") <= 1


def test_清理只换内容不拆配对() -> None:
    """清理「工具结果」而不是「工具往返」：换掉的是正文，声明与 id 原地不动。

    这一点很容易做错：如果清理时把早前的 tool 消息整条删掉，只留最近一条，
    请求就又多出一堆无配对的结果——省下的词元得在 400 里加倍还回去。
    """
    hist = history(n_tool=4)
    msgs, replaced = clean_tool_results(hist, keep_recent=1)
    assert replaced == 3
    cleaned, dropped = sanitize(msgs)
    assert dropped == 0 and len(cleaned) == len(hist)
    tools = [m for m in cleaned if m.is_tool()]
    assert len(tools) == 4 and all(m.tool_call_id for m in tools)
    assert tools[0].content.startswith("[工具结果已清理")
    assert tools[-1].content.startswith("命中一篇")
