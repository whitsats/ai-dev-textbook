# tests/test_acceptance.py —— 端到端验收：不换应用，只把模型换成剧本
"""这一份测的是**服务**，不是零件：路由、依赖注入、请求校验、统一外壳、
会话、指标，六样一起过。

三条路径对应 [`PROJECT.md`](../../PROJECT.md) 的验收标准——问答（只读）／
草稿（写，且发布停在人工确认）／跨会话续跑（新会话历史为零，但召回了偏好）。
唯一的替身是**模型传输**（`chat()` 的 `transport=` 参数），所以剩下的每一层都是真的：
路由、pydantic 校验、依赖装配、注册表、循环、追踪器、会话存储。

**为什么用 `dependency_overrides`，而不是另起一个 `FastAPI()`**：
「一个依赖要密钥、另一个不要」本身就是这一章要验的接线；另建一个应用就把它绕过去了。
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.agent.memory import InMemoryStore
from app.agent.trace import Tracer
from app.api.agent import get_agent_service, get_memory_service
from app.llm.client import Config, RawChat, ToolCall, chat
from app.main import app
from app.services.agent_service import AgentService


def scripted(*replies):
    """剧本传输层：按序吐出响应，用完后重复最后一条（与 `tests/test_wiring.py` 同一口径）。"""
    seq = list(replies)

    def transport(messages, cfg, **kw):
        got = seq.pop(0) if len(seq) > 1 else seq[0]
        return RawChat(got, [], 6) if isinstance(got, str) else got

    def chat_fn(messages, **kw):
        return chat(messages, transport=transport, **kw)

    return chat_fn


def tool(name: str, arg: str) -> RawChat:
    """造一个「模型这次要调工具」的响应。"""
    return RawChat("", [ToolCall("c0", name, arg)])


def client(*replies, allow_approve: bool = False, sessions=None, tracer=None):
    """真实应用 ＋ 剧本模型。返回 `(客户端, 服务实例)`：服务实例用来读环境终态。"""
    svc = AgentService(
        Config(api_key="test"),
        sessions=sessions if sessions is not None else InMemoryStore(),
        tracer=tracer if tracer is not None else Tracer(),
        chat_fn=scripted(*replies),
        approve=(lambda name, args: True) if allow_approve else (lambda name, args: False),
    )
    # 两个依赖都要换。只换 `get_agent_service` 的话，会话与指标端点会走回真装配
    # （它要从环境变量读密钥），现象是一个 500——而报错与路由本身毫无关系。
    app.dependency_overrides[get_agent_service] = lambda: svc
    app.dependency_overrides[get_memory_service] = lambda: svc
    return TestClient(app), svc


def _post(c: TestClient, path: str, body: dict) -> dict:
    """一次 POST，并顺带把「HTTP 层必须是 200」这条钉死：外壳内部才谈 code。"""
    resp = c.post(path, json=body)
    assert resp.status_code == 200, f"{path} → {resp.status_code} {resp.text[:200]}"
    return resp.json()


def path1_qa() -> dict:
    """① 问答：只读会话里，模型自己决定读哪一篇、什么时候收口。"""
    c, _ = client(tool("read_article", '{"article_id": 42}'),
                  "这篇讲的是刷新令牌的三种做法与三条边界。")
    return _post(c, "/api/v1/agent/chat",
                 {"task": "读 42 号文章的正文，用一句话说它讲了什么。"})


def path2_draft(*, allow_approve: bool = False) -> tuple[dict, dict]:
    """② 草稿：起草真的执行了，发布停在人工确认（默认不批）。返回 `(响应, 环境终态)`。"""
    c, svc = client(tool("create_draft", '{"article_id": 42, "body": "草稿正文"}'),
                    tool("publish_article", '{"article_id": 42}'),
                    "草稿已写好，请确认是否发布。",
                    allow_approve=allow_approve)
    r = _post(c, "/api/v1/agent/chat",
              {"task": "给 42 号文章起草一版并发布。", "allow_write": True})
    return r, {"draft": svc.store.get("draft", {}).get("status")}


def path3_memory() -> tuple[dict, dict]:
    """③ 跨会话续跑：会话 A 定下偏好，新开的会话 B 直接要求发布。返回 `(B 的响应, A 的响应)`。"""
    c, _ = client("好，以后发布我先给你看草稿。",
                  "必须先给你看草稿才能发布。")
    a = _post(c, "/api/v1/agent/session/chat",
              {"task": "记住：以后发布一律先给我看草稿。"})
    b = _post(c, "/api/v1/agent/session/chat",
              {"task": "把 42 号文章发布上线。", "allow_write": True})
    return b, a


# ---------------------------------------------------------------- 三条路径

def test_路径一_问答只读且真的读了文章() -> None:
    data = path1_qa()["data"]
    assert data["reason"] == "模型给出最终答案"
    assert data["trace"][0]["action"] == "read_article"
    assert "刷新令牌" in data["trace"][0]["observation_head"]      # 工具真的执行过
    assert data["steps"] == 2 and data["calls"] == 2


def test_路径二_起草执行而发布停在人工确认() -> None:
    r, env = path2_draft()
    assert env["draft"] == "draft"                                 # 草稿写进去了
    assert [e["action"] for e in r["data"]["trace"]][:2] == ["create_draft", "publish_article"]
    assert "等待人工确认" in r["data"]["trace"][1]["observation_head"]
    assert r["data"]["answer"].endswith("请确认是否发布。")


def test_路径二_审批放行时发布真的会执行() -> None:
    """反向守：上面那条断言不能因为「发布这条路根本走不通」而通过。"""
    _, env = path2_draft(allow_approve=True)
    assert env["draft"] == "published"


def test_路径三_新会话历史为零但召回了偏好() -> None:
    b, a = path3_memory()
    assert a["data"]["session_id"] != b["data"]["session_id"]      # 必须是新开的会话
    assert b["data"]["memory"]["history_messages"] == 0            # 它没有上一轮的历史
    assert "pref.publish" in b["data"]["memory"]["recalled"]       # 靠的是长期记忆
    assert "草稿" in b["data"]["answer"]                            # 偏好真的进了提示
    assert "pref.publish" in a["data"]["memory"]["remembered"]


# ---------------------------------------------------------------- 外壳与边界

def test_健康检查与统一外壳() -> None:
    c, _ = client("兜底答案")
    assert c.get("/healthz").json()["ok"] is True
    r = _post(c, "/api/v1/agent/chat", {"task": "随便问一句。"})
    assert r["code"] == 0 and r["msg"] == "ok"
    assert set(r) == {"code", "msg", "data"}                       # 外壳不许长出新字段
    assert r["data"]["answer"] == "兜底答案"


def test_可回放会话与删除一条记忆() -> None:
    c, _ = client("好，以后发布我先给你看草稿。")
    sid = _post(c, "/api/v1/agent/session/chat",
                {"task": "记住：以后发布一律先给我看草稿。"})["data"]["session_id"]
    got = c.get(f"/api/v1/agent/session/{sid}").json()
    assert got["code"] == 0 and got["data"]["messages"][0]["role"] == "user"
    ctx = c.get(f"/api/v1/agent/session/{sid}/context").json()
    assert ctx["data"]["long_term"] and ctx["data"]["input_tokens"] > 0
    assert c.delete("/api/v1/agent/memory/pref.publish").json()["data"]["deleted"] == 1
    assert "pref.publish" not in c.get(f"/api/v1/agent/session/{sid}/context"
                                       ).json()["data"]["long_term"]


def test_指标端点不要求密钥且窗口有界() -> None:
    c, _ = client("答案")
    for task in ("第一件事。", "第二件事。", "第三件事。"):
        _post(c, "/api/v1/agent/chat", {"task": task})
    m = c.get("/api/v1/agent/metrics", params={"window": 2}).json()
    assert m["code"] == 0
    assert m["data"]["runs"] == 2                                  # 窗口是最近的 N 次，不是“从启动至今”
    assert m["data"]["failure_distribution"] == {"成功": 2}         # 所以分布也只有两个样本（有限档，不是原话）
    assert m["data"]["cost"] is None                               # 没配单价就不编一个价


def test_参数越界与不存在的资源走HTTP语义() -> None:
    """两条边界要分清：**请求本身不合法**（422）与**请求合法但对象不存在**（404），
    都不该伪装成一个 `code != 0` 的正常响应——那会让调用方只能靠读文案来判断。"""
    c, _ = client("答案")
    assert c.post("/api/v1/agent/chat", json={"task": "x", "max_steps": 99}).status_code == 422
    assert c.get("/api/v1/agent/session/999999").status_code == 404
