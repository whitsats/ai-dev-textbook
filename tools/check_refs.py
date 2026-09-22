#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
校验 REFERENCES.md 中的官方文档链接是否仍然有效。

为什么需要这个脚本
------------------
本教材的技术结论以官方文档为准，但文档会迁移、分支会重命名、API 会关停。
审计素材时就撞上过一批：Claude 文档从 docs.anthropic.com 迁到
platform.claude.com 与 code.claude.com，OpenAI 文档迁到 developers.openai.com，
LangChain 发布 v1 后旧命名空间被移出主线。人工检查几十个链接既慢又容易漏，
所以做成可复跑的脚本。

关注六种结果
------------
  OK      2xx/3xx 正常
  跳转    最终域名与请求域名不同 —— 文档搬家了，正文里的引用要跟着改
  失效    4xx —— 服务器明确说“没有”，链接已死，必须替换（会拦提交）
  暂不可用 5xx —— 服务器说“现在给不了”（重试过），**不是**“没有这个东西”：
          链接可能好好的，是对方维护／限流／上层代理出错。会打印并提醒
          人工看一眼，但不拦提交
  超时    瞬时连接失败（超时 / DNS 抖动 / 连接被重置）—— 重跑一次就好的事，
          **不当作失效**，也不拦提交，但会打印出来提醒
  超时    瞬时连接失败（超时 / DNS 抖动 / 连接被重置）—— 重跑一次就好的事，
          **不当作失效**，也不拦提交，但会打印出来提醒
  连接异常 非瞬时的连接层失败（如证书校验不通过）—— 必须人工确认：
          可能是站点换了域名，也可能是 TLS 配置本身有问题。同样不拦提交
  拦截    401/403/429 —— 站点拒绝脚本访问（含限流），人工确认即可（不算失效）

为何把「超时」单独列一档：早期实现把 status=0 一律归为「失效」，
结果是本地网络抖一下就提交不了。报警器一旦会因为无关原因响，就会被绕过——
所以只让服务器明确声明的死链拦提交。

为何把 5xx 从「失效」里拆出来（2026-09-22 补）：原来写的是「4xx/5xx 都算失效」，
而 CI 上 `manpages.ubuntu.com` 回了一个 503，于是那一笔提交被拦住——可是 503 恰恰
在说「我现在给不了」，不是在说「没有这一页」。**这与上面那句追问是同一个形状**：
把「查不出来」当成「查出来是坏的」，会让报警器在无关原因上响。重试之后仍然 5xx
的列为「暂不可用」：打印、提醒、人工看一眼，不拦提交。

为何还要把「连接异常」从「超时」里拆出来：`www.starlette.io` 的证书在本机
校验不通过，早期实现把它报成「超时（网络抖一下，忽略即可）」，于是整整一轮
没人去看它——而真实原因是 Starlette 的文档站迁到了 `starlette.dev`。
**把「重跑就好」和「必须查」混成一档，等于把后者藏起来。**

用法
----
    python tools/check_refs.py                 # 校验全部链接
    python tools/check_refs.py --only-broken   # 只打印要处理的（失效 / 暂不可用 / 跳转 / 连接异常）
    python tools/check_refs.py --offline       # 只解析链接清单，不发请求
    python tools/check_refs.py --workers 12 --timeout 12
"""

from __future__ import annotations

import argparse
import concurrent.futures as futures
import re
import socket
import ssl
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
REFS = ROOT / "REFERENCES.md"
URL_RE = re.compile(r"https?://[^\s|)\]}>,；，、]+")
UA = ("Mozilla/5.0 (compatible; freebuff-textbook-ref-check/1.0; "
      "+https://example.invalid/bot)")


def collect_urls(text: str) -> list[str]:
    """按出现顺序去重收集链接。"""
    seen: set[str] = set()
    out: list[str] = []
    for m in URL_RE.finditer(text):
        u = m.group(0).rstrip(".,;）)】").replace("&amp;", "&")
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def _probe(url: str, method: str, timeout: float) -> tuple[int, str]:
    req = urllib.request.Request(url, method=method, headers={
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    })
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
        return resp.status, resp.geturl()


def _attempt(url: str, timeout: float) -> dict:
    """单次尝试：先 HEAD；不少站点对 HEAD 返回 403/405，再退化为 GET。"""
    for method in ("HEAD", "GET"):
        try:
            status, final = _probe(url, method, timeout)
            return {"url": url, "status": status, "final": final, "error": ""}
        except urllib.error.HTTPError as e:
            if method == "HEAD" and e.code in (403, 405, 400, 501):
                continue
            return {"url": url, "status": e.code, "final": url, "error": f"HTTP {e.code}"}
        except urllib.error.URLError as e:
            if method == "HEAD":
                continue
            return {"url": url, "status": 0, "final": url,
                    "error": f"{type(e.reason).__name__}: {e.reason}"}
        except (socket.timeout, TimeoutError):
            if method == "HEAD":
                continue
            return {"url": url, "status": 0, "final": url, "error": "超时"}
        except Exception as e:  # noqa: BLE001
            if method == "HEAD":
                continue
            return {"url": url, "status": 0, "final": url, "error": type(e).__name__}
    return {"url": url, "status": 0, "final": url, "error": "无法连接"}


def _retryable(r: dict) -> bool:
    """值不值得重问一次：**连接层失败（status=0）与 5xx 都值得。**

    连接层失败多为瞬时的（限流、DNS、TLS 握手）；5xx 也是同一类东西——503 常带着
    `Retry-After`，最常见的成因是对方在维护或对脚本限流，而不是那一页没了。
    4xx 不重试：服务器已经明确答复，重问一次还是同一句话。
    """
    return r["status"] == 0 or r["status"] >= 500


def check(url: str, timeout: float, attempts: int = 2) -> dict:
    """带重试的探测（判据见 `_retryable`：连接层失败与 5xx 重试，4xx 不重试）。"""
    result = _attempt(url, timeout)
    for _ in range(attempts - 1):
        if not _retryable(result):
            break
        if result["status"] >= 500:
            time.sleep(1.5)          # 对方说「等会儿再来」，那就真的等一下
        result = _attempt(url, timeout)
    return result


# 连接层失败里，「重跑一次就好」的那些（异常类名）。
# 不在这里面的（例如证书校验失败）要人工确认，不能归为「网络抖动」。
TRANSIENT_ERRORS = {
    "超时", "TimeoutError", "gaierror", "ConnectionResetError",
    "ConnectionRefusedError", "ConnectionError", "RemoteDisconnected",
    "IncompleteRead", "IncompleteReadError", "CannotSendRequest",
}


def is_transient(error: str) -> bool:
    """判断连接层失败是否属于「重跑一次就好」的瞬时问题。"""
    return error.split(":", 1)[0].strip() in TRANSIENT_ERRORS


def verdict(r: dict) -> str:
    st = r["status"]
    if st == 0:
        # 连接层问题（重试已试过），不是链接失效，不拦提交；
        # 但要区分「瞬时」与「必须人工确认」。
        return "超时" if is_transient(r["error"]) else "连接异常"
    if st in (401, 403, 429):
        return "拦截"      # 反爬／限流，非链接失效
    if st >= 500:
        return "暂不可用"  # 服务器说「现在给不了」，**不是**「没有这个东西」
    if st >= 400:
        return "失效"
    a, b = urlparse(r["url"]).netloc, urlparse(r["final"]).netloc
    if a.replace("www.", "") != b.replace("www.", ""):
        return "跳转"      # 换域名了，引用需更新
    return "OK"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true", help="只解析链接，不发请求")
    ap.add_argument("--only-broken", action="store_true",
                    help="只打印需要处理的项（失效 / 暂不可用 / 跳转 / 连接异常）")
    ap.add_argument("--timeout", type=float, default=10.0)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--file", default=str(REFS), help="要校验的文件，默认 REFERENCES.md")
    args = ap.parse_args()

    path = Path(args.file)
    if not path.exists():
        print(f"找不到 {path}", file=sys.stderr)
        return 1
    urls = collect_urls(path.read_text("utf-8", errors="ignore"))
    print(f"从 {path.name} 解析出 {len(urls)} 个唯一链接\n")

    if args.offline:
        for u in urls:
            print(f"  {u}")
        return 0

    results: list[dict] = []
    with futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = {pool.submit(check, u, args.timeout): u for u in urls}
        for fut in futures.as_completed(futs):
            results.append(fut.result())

    order = {u: i for i, u in enumerate(urls)}
    results.sort(key=lambda r: order[r["url"]])

    counts: dict[str, int] = {}
    for r in results:
        v = verdict(r)
        counts[v] = counts.get(v, 0) + 1
        if args.only_broken and v not in ("失效", "暂不可用", "跳转", "连接异常"):
            continue
        tail = f"  → {r['final']}" if r["final"] != r["url"] else ""
        extra = f"  ({r['error']})" if r["error"] and v != "OK" else ""
        print(f"  [{v}] {r['status'] or '-'}  {r['url']}{tail}{extra}")

    print("\n汇总：" + " ｜ ".join(f"{k} {v}" for k, v in sorted(counts.items())))
    broken = counts.get("失效", 0)
    moved = counts.get("跳转", 0)
    timeouts = counts.get("超时", 0)
    unavailable = counts.get("暂不可用", 0)
    if broken or moved:
        print(f"\n需要处理：{broken} 个失效、{moved} 个跳转。"
              f"请更新 REFERENCES.md，再同步受影响章节。")
    if unavailable:
        print(f"\n提示：{unavailable} 个链接服务器回了 5xx（已重试）——这是「现在给不了」，"
              f"不是「没有这一页」：对方可能在维护，也可能在对脚本限流。不拦提交，"
              f"但建议过一会儿再跑一次确认；若几次都是它，就换一个出处。")
    if timeouts:
        print(f"\n提示：{timeouts} 个链接连接超时（已重试），多为本地网络或对方限流——"
              f"不算失效，建议稍后重跑确认。")
    conn_errors = counts.get("连接异常", 0)
    if conn_errors:
        print(f"\n⚠️ {conn_errors} 个链接出现**非瞬时**的连接失败（已重试）——"
              f"请人工确认：常见原因是文档站换了域名或证书有问题，"
              f"而不是网络抖动。用 `--only-broken` 或直接打开链接查看。")
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main())
