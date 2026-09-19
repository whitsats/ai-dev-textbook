#!/usr/bin/env python
"""一键验收：起服务 → 三条路径走 HTTP → 打印读数。

    python scripts/acceptance.py --offline    # 不需要密钥：进程内起应用，HTTP 面是真的
    python scripts/acceptance.py              # 需要密钥：真起 uvicorn，走真端口
    python scripts/acceptance.py --port 8011  # 指定端口（默认自动挑一个空闲端口）

**离线那一路为什么不造假 HTTP**：它用 `TestClient`，请求真的穿过 ASGI——路由、
依赖注入、pydantic 校验、统一外壳都在链路上，假的只有**模型传输**（换成剧本）。
所以这一路足够确定性，可以当门（`tools/check_runnable.py` 跑的就是同一批用例，
它们和本脚本共用 `tests/test_acceptance.py` 里的三个 `path*()`）。

真机那一路只报读数、不断言行为：模型怎么答不是这份脚本能规定的，
唯一钉死的是**外壳与 HTTP 状态码**——那是服务端的承诺，与模型无关。
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))          # 复用机检的那三个 path*()


def free_port() -> int:
    """让操作系统挑一个空闲端口：写死 8000 会撞上别人正在跑的服务。"""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def brief(r: dict, keys: tuple[str, ...] = ("steps", "calls", "tokens", "reason")) -> str:
    d = r.get("data") or {}
    return "｜".join(f"{k} {d.get(k)}" for k in keys)


def tools_of(r: dict) -> list[str]:
    """轨迹里真正调过的工具。最后一条是收口（`action` 为空），不给它留个 `None`。"""
    return [e["action"] for e in (r.get("data") or {}).get("trace", []) if e["action"]]


def offline() -> int:
    import test_acceptance as acc                   # noqa: PLC0415 —— 只有这一路才需要它

    print("== 一键验收（离线：真实 HTTP 面 ＋ 剧本模型）==")
    qa = acc.path1_qa()
    draft, env = acc.path2_draft()
    resumed, first = acc.path3_memory()

    print(f"① 问答（只读）      {brief(qa)}")
    print(f"   工具：{tools_of(qa)}")
    print(f"② 草稿（写）        {brief(draft)}｜环境终态 {env['draft']}")
    print(f"   工具：{tools_of(draft)}")
    print(f"③ 跨会话续跑        新会话 {resumed['data']['session_id']}"
          f"（上一个 {first['data']['session_id']}）｜"
          f"历史 {resumed['data']['memory']['history_messages']} 条｜"
          f"召回 {resumed['data']['memory']['recalled']}")
    print(f"   答案：{resumed['data']['answer']}")

    failed = []
    if env["draft"] != "draft":
        failed.append("② 的发布没有被拦住")
    if resumed["data"]["memory"]["history_messages"] != 0:
        failed.append("③ 的新会话不该带历史")
    if "草稿" not in resumed["data"]["answer"]:
        failed.append("③ 的偏好没有影响回答")
    print("✔ 三条路径全通" if not failed else f"✖ {failed}")
    return 0 if not failed else 1


def real(port: int, timeout: float = 20.0) -> int:
    import httpx                                    # noqa: PLC0415 —— 真机那一路才需要

    base = f"http://127.0.0.1:{port}"
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    proc = subprocess.Popen(                                     # noqa: S603
        [sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(port), "--log-level", "warning"],
        cwd=ROOT, env=env)
    try:
        deadline = time.time() + timeout
        while True:                                             # 等服务真的起来，而不是 sleep 一个猜的数
            if time.time() > deadline:
                print(f"✖ {timeout:.0f}s 内没等到 /healthz（服务是否起得来？）")
                return 1
            try:
                if httpx.get(f"{base}/healthz", timeout=1.0).json().get("ok"):
                    break
            except Exception:                                   # noqa: BLE001 —— 起来之前连不上是正常的
                time.sleep(0.3)
        print(f"== 一键验收（真机：{base}，模型 {os.environ.get('LLM_MODEL', '(未设置)')}）==")

        def post(path: str, body: dict) -> dict:
            resp = httpx.post(f"{base}{path}", json=body, timeout=180.0)
            assert resp.status_code == 200, f"{path} → {resp.status_code} {resp.text[:200]}"
            return resp.json()

        qa = post("/api/v1/agent/chat", {"task": "读 42 号文章的正文，用一句话说它讲了什么。"})
        draft = post("/api/v1/agent/chat", {"task": "给 42 号文章起草一版并发布。", "allow_write": True})
        first = post("/api/v1/agent/session/chat", {"task": "记住：以后发布一律先给我看草稿。"})
        resumed = post("/api/v1/agent/session/chat",
                       {"task": "把 42 号文章发布上线。", "allow_write": True})
        metrics = httpx.get(f"{base}/api/v1/agent/metrics", params={"window": 4}).json()

        print(f"① 问答（只读）      {brief(qa)}")
        print(f"   工具：{tools_of(qa)}")
        print(f"② 草稿（写）        {brief(draft)}")
        print(f"   工具：{tools_of(draft)}"
              "  ← 发布有没有被拦，看上一次工具是不是 publish_article")
        print(f"③ 跨会话续跑        历史 {resumed['data']['memory']['history_messages']} 条｜"
              f"召回 {resumed['data']['memory']['recalled']}")
        print(f"   答案：{resumed['data']['answer']}")
        print(f"指标：{json.dumps({k: metrics['data'][k] for k in ('runs', 'success_rate')}, ensure_ascii=False)}"
              f"｜失败分布 {metrics['data']['failure_distribution']}")
        print("说明：真机读数只报不当门——同一份代码在两次运行里可以给出不同的轨迹，"
              "而门要的是确定性（见 3.9）。")
        return 0
    finally:
        proc.terminate()                                        # 无论成败都收掉这个进程
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true", help="不用密钥：剧本模型 + 真实 HTTP 面")
    ap.add_argument("--port", type=int, default=0, help="默认自动挑一个空闲端口")
    args = ap.parse_args()
    return offline() if args.offline else real(args.port or free_port())


if __name__ == "__main__":
    raise SystemExit(main())
