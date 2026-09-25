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
  连接异常 非瞬时的连接层失败（如证书校验不通过）—— 必须人工确认：
          可能是站点换了域名，也可能是 TLS 配置本身有问题。同样不拦提交
  拦截    401/403/429 —— 站点拒绝脚本访问（含限流），人工确认即可（不算失效）
  未查    **本次预算内没轮到它**（见下节的 `--max-seconds`）—— 既不算通过也不算
          失效，打印出来、不拦提交

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

为何会有「未查」这一档（2026-09-25 补）
--------------------------------------
上面两条讲的是**一档报错不该响**。这一条讲的是另一半：**一档检查不该跑不完**。

485 条链接 × 每条 HEAD→GET→整轮重试 × 5xx 还要退避 —— 这一趟没有上界，
实测在提交门里要跑几分钟到几十分钟。而 `SKIP_BOOK_CHECKS=1` 是在钩子**最顶上**
就退出的，它跳过的是**整条链**（十四个工具的夹具 ＋ 正文校验 ＋ 四道对账 ＋
可运行树 ＋ 四道索引），不是这一档。于是形状是：为了省一次联网校验，
把本地所有的门一起关掉。

**跑不完的报警器与会乱响的报警器一样会被绕过，而且它绕过的是整条链。**
所以本脚本改成三层：

  ① **离线解析永远有界**（`--offline`，0.15 秒）——提交门每次都跑它；
  ② **改动的提交只查这次 diff 新增的链接**（`--changed-only`，通常 1–5 条，
     几秒），且带 `--max-seconds` 硬预算与结果缓存；
  ③ **全量按时间守**：CI（`refs` job）与它的 `schedule` 跑全量——那里没有时限。

「链接腐坏」按时间发生，不按你改没改 REFERENCES.md 发生；把全量挂在「改动」
这个事件上，就会同时得到「越少动出处越晚发现死链」与「一动出处就被罚几分钟」。

用法
----
    python tools/check_refs.py                 # 校验全部链接
    python tools/check_refs.py --only-broken   # 只打印要处理的（失效 / 暂不可用 / 跳转 / 连接异常）
    python tools/check_refs.py --offline       # 只解析链接清单，不发请求
    python tools/check_refs.py --changed-only --cache --max-seconds 45
                                               # 只查相对 HEAD 新增的链接（提交门跑这一条）
    python tools/check_refs.py --workers 12 --timeout 12
    python tools/check_refs.py --self-test     # 夹具（diff 取链接 / 缓存 / 预算 / 判定极性）
"""

from __future__ import annotations

import argparse
import concurrent.futures as futures
import json
import re
import socket
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

# 本脚本会打印 ⚠️（非 BMP 之外的符号没问题，但 GBK 控制台编不出来）：
# 钩子那边有 PYTHONIOENCODING=utf-8 挡着，人直接跑没有——那样它会在**最后一行**
# 崩掉，而前面那些读数已经打印过。与 `bank_index.py` 等同一处理。
sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
REFS = ROOT / "REFERENCES.md"
URL_RE = re.compile(r"https?://[^\s|)\]}>,；，、]+")
UA = ("Mozilla/5.0 (compatible; freebuff-textbook-ref-check/1.0; "
      "+https://example.invalid/bot)")

#: 结果缓存。放 `.git/` 下有两个理由：它**永不进仓**（所以不会变成「手抄的第二份数」
#: 那种漂掉没人管的东西），而且它是一台机器的事实、不是全队的事实。
CACHE_PATH = ROOT / ".git" / "book-checks" / "refs-cache.json"
#: 缓存只记 OK，且只信一周。失效／跳转**不进缓存**——修好之后要立刻看得见。
CACHE_TTL_SECONDS = 7 * 24 * 3600


def collect_urls(text: str) -> list[str]:
    """按出现顺序去重收集链接。

    尾随的 `。` 也要剥掉：正文里「链接 + 句号」是常见写法（`book/` 下现搜有 5 行），
    不剥的话同一条链接在表格里和在散文里会被数成两条。本文件里的这份清单与
    `style_claims.inventory_facts` 那一条**是两份正则**（后者的字符类已经排除了 `。`、
    且还会剥尾随 `/`）；今天两处都数出 485，是因为盘上恰好没有会分歧的写法——
    **它们是可以分歧的，所以别把其中一份当另一份的证明。**
    """
    seen: set[str] = set()
    out: list[str] = []
    for m in URL_RE.finditer(text):
        u = m.group(0).rstrip(".,;）)】。").replace("&amp;", "&")
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def collect_added_urls(diff_text: str) -> list[str]:
    """从 `git diff` 的输出里取**新增行**上的链接。

    三处刻意的不取：`--- a/…` / `+++ b/…` 两个头（它们以 `-` / `+` 开头，
    但说的是文件名，不是内容）、被删掉的行（`-` 开头——删掉的链接不该再去问）、
    以及上下文行。取宽了会让这一档重新变成「查全量」，取窄了会静默什么都不查，
    所以两头都有夹具。
    """
    added = [ln[1:] for ln in diff_text.splitlines()
             if ln.startswith("+") and not ln.startswith("+++")]
    return collect_urls("\n".join(added))


def git_diff_of(path: Path) -> str | None:
    """该文件相对 HEAD 的 diff；取不到返回 None，由调用方兜底。

    **两份 diff 都要取并拼起来**，不是「哪一份都行」：`git diff HEAD` 看的是工作区，
    `git diff --cached` 看的是暂存区。提交那一刻两者一般一样，但**不是必然一样**
    （`git add -p` 分次暂存、或者被暂存后又在工作区改回去），而漏读一份的后果恰好是
    我们要防的那种：新增链接数成 0 条、输出写着「无事可做」。两份拼起来再交给
    `collect_added_urls` 去重，就没有这个缝。未出生的 HEAD（首次提交）那一侧会失败，
    两份都失败才返回 None。
    """
    rel = path.name if path.parent == ROOT else str(path)
    chunks: list[str] = []
    for rev in ("HEAD", "--cached"):
        try:
            proc = subprocess.run(["git", "diff", rev, "-U0", "--", rel], cwd=ROOT,
                                  capture_output=True, text=True,
                                  encoding="utf-8", errors="replace")
        except OSError:
            return None
        if proc.returncode == 0:
            chunks.append(proc.stdout)
    return "\n".join(chunks) if chunks else None


# ---------------------------------------------------------------- 缓存

def cache_load(path: Path) -> dict[str, dict]:
    """读缓存。读不出来（没有 / 半截 / 手改坏）就当空的——缓存是优化，不是事实。"""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def cache_save(path: Path, entries: dict[str, dict]) -> bool:
    """写回缓存。写不进去（只读目录 / `.git` 是文件）不算错，返回 False。"""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(entries, ensure_ascii=False, indent=1,
                                   sort_keys=True), encoding="utf-8")
        return True
    except OSError:
        return False


def cache_fresh(entry: dict, ttl_seconds: float, now: float) -> bool:
    """这条缓存还算不算数。"""
    try:
        return (now - float(entry["checked_at"])) < ttl_seconds
    except (KeyError, TypeError, ValueError):
        return False


def probe_plan(urls: list[str], cache: dict[str, dict], ttl_seconds: float,
               now: float) -> tuple[list[str], list[dict]]:
    """（要真去问的, 直接采信的）。

    采信的条件有三条：**记的是 OK**（失效／跳转从不入缓存）、**在一周之内**、
    而且**是同一个 URL**。三条缺一条就重新问——缓存省的是重复的网络往返，
    不是「把已知的坏消息盖住」。
    """
    todo: list[str] = []
    hits: list[dict] = []
    for u in urls:
        entry = cache.get(u)
        if (isinstance(entry, dict) and entry.get("verdict") == "OK"
                and cache_fresh(entry, ttl_seconds, now)):
            hits.append({**entry, "url": u, "cached": True})
        else:
            todo.append(u)
    return todo, hits


def probe(urls: list[str], timeout: float, workers: int,
          max_seconds: float) -> tuple[list[dict], bool]:
    """并发探测，返回（结果, 有没有被预算截断）。

    `max_seconds` 到点之后**不再等**在飞的那些任务，把它们标成「未查」。
    不用 `with ThreadPoolExecutor(...)`：它的 `__exit__` 是 `shutdown(wait=True)`，
    会把预算到期这件事**变成再等一整轮**（在飞的那次探测最长 `timeout` 秒）。
    """
    if not urls:
        return [], False
    results: list[dict] = []
    futs: dict[futures.Future, str] = {}
    pending: set[futures.Future] = set()
    pool = futures.ThreadPoolExecutor(max_workers=workers)
    truncated = False
    try:
        futs = {pool.submit(check, u, timeout): u for u in urls}
        pending = set(futs)
        budget = max_seconds if max_seconds > 0 else None
        for fut in futures.as_completed(futs, timeout=budget):
            results.append(fut.result())
            pending.discard(fut)
    except (TimeoutError, futures.TimeoutError):
        truncated = True
    finally:
        for fut in pending:
            results.append({"url": futs[fut], "status": 0, "final": futs[fut],
                            "error": "未查（预算用完）", "unchecked": True})
        pool.shutdown(wait=False, cancel_futures=True)
    order = {u: i for i, u in enumerate(urls)}
    results.sort(key=lambda r: order[r["url"]])
    return results, truncated


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


def result_verdict(r: dict) -> str:
    """这一条怎么记（`未查` 与 `*·缓存` 只在这里出现，不进 `verdict`）。"""
    if r.get("unchecked"):
        return "未查"
    return verdict(r)


def blocks(counts: dict[str, int]) -> bool:
    """拦提交的判据**只有一条**：服务器明确说了 4xx。

    `未查` 不在这条里——「没轮到它」既不是通过也不是坏消息，把它算成坏消息
    会让提交门重新变成「会因为无关原因响」。
    """
    return counts.get("失效", 0) > 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true", help="只解析链接，不发请求")
    ap.add_argument("--only-broken", action="store_true",
                    help="只打印需要处理的项（失效 / 暂不可用 / 跳转 / 连接异常 / 未查）")
    ap.add_argument("--changed-only", action="store_true",
                    help="只探测相对 HEAD 新增的链接（提交门跑这一条）")
    ap.add_argument("--cache", action="store_true",
                    help="采信并写回结果缓存（只记 OK，TTL 一周；文件在 .git/ 下）")
    ap.add_argument("--cache-ttl", type=float, default=CACHE_TTL_SECONDS / 3600,
                    help="缓存有效期（小时，默认 168）")
    ap.add_argument("--max-seconds", type=float, default=0.0,
                    help="联网探测的硬预算（秒，0＝不限）；到点没轮到的记「未查」，不拦提交")
    ap.add_argument("--timeout", type=float, default=10.0)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--file", default=str(REFS), help="要校验的文件，默认 REFERENCES.md")
    ap.add_argument("--self-test", action="store_true", help="用合成状态自检")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

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

    targets = urls
    if args.changed_only:
        diff = git_diff_of(path)
        if diff is None:
            # 兜底要说出来：**悄悄退化成查全量**与**悄悄什么都不查**一样坏，
            # 一个会说谎，一个会装死。
            print("⚠️ 取不到 git diff（首次提交 / 不在仓库内？）——改为探测全部链接，"
                  "并受 --max-seconds 限制。\n")
        else:
            targets = collect_added_urls(diff)
            if not targets:
                print("本次改动里没有新增链接（删除 / 改注 / 重排）——这一档无事可做。")
                print("\n汇总：0 条需要处理")
                return 0
            print(f"改动里新增 {len(targets)} 个链接（相对 HEAD）\n")

    now = time.time()
    cache = cache_load(CACHE_PATH) if args.cache else {}
    ttl = args.cache_ttl * 3600
    todo, hits = probe_plan(targets, cache, ttl, now)
    if args.cache:
        print(f"缓存：命中 {len(hits)} 条 / 待问 {len(todo)} 条"
              f"（TTL {args.cache_ttl:g} 小时，{CACHE_PATH.relative_to(ROOT)}）\n")

    results, truncated = probe(todo, args.timeout, args.workers, args.max_seconds)
    results = hits + results

    counts: dict[str, int] = {}
    for r in results:
        v = result_verdict(r)
        counts[v] = counts.get(v, 0) + 1
        if args.only_broken and v not in ("失效", "暂不可用", "跳转", "连接异常", "未查"):
            continue
        tag = f"{v}·缓存" if r.get("cached") and v == "OK" else v
        tail = f"  → {r['final']}" if r.get("final") and r["final"] != r["url"] else ""
        extra = f"  ({r['error']})" if r.get("error") and v != "OK" else ""
        print(f"  [{tag}] {r['status'] or '-'}  {r['url']}{tail}{extra}")

    if args.cache:
        changed = 0
        for r in results:
            if r.get("cached") or r.get("unchecked"):
                continue
            if verdict(r) == "OK":
                cache[r["url"]] = {"url": r["url"], "status": r["status"],
                                   "final": r["final"], "error": "",
                                   "verdict": "OK", "checked_at": now}
                changed += 1
        if changed and not cache_save(CACHE_PATH, cache):
            print("\n（注：这一趟查好的结果没能写进缓存，只影响下次的往返次数。）")

    print("\n汇总：" + " ｜ ".join(f"{k} {v}" for k, v in sorted(counts.items())))
    broken = counts.get("失效", 0)
    moved = counts.get("跳转", 0)
    timeouts = counts.get("超时", 0)
    unavailable = counts.get("暂不可用", 0)
    unchecked = counts.get("未查", 0)
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
    if unchecked:
        print(f"\n⚠️ 有 {unchecked} 个链接**没在预算内轮到**（--max-seconds "
              f"{args.max_seconds:g} 秒）——它们既不算通过、也不算失效，这一趟到此为止。"
              f"它们不是坏消息：要么把 `--max-seconds` 调大，要么让 CI 的全量那一趟去看。"
              if not args.changed_only else
              f"\n⚠️ 有 {unchecked} 个新增链接**没在预算内轮到**（--max-seconds "
              f"{args.max_seconds:g} 秒）。**它们这一趟没被判定**——提交门只对"
              f"「问到过、且服务器说 4xx」的那些报警，所以这一笔会在未判定处放行；"
              f"CI 的全量那一趟仍会看。若想在这里就问完，把 `--max-seconds` 调大重跑。")
    if truncated and not unchecked:
        print(f"\n（预算 {args.max_seconds:g} 秒用尽，但在飞的都收回来了。）")
    # 拦提交的判据只走这一个函数（它的夹具在下边）：**没轮到它不算坏消息**。
    return 1 if blocks(counts) else 0


# ---------------------------------------------------------------- 夹具

def self_test() -> int:
    """合成状态喂进去：这一档的**每一条判据**都要能响，且**不许在无关的地方响**。

    这一档最容易坏的地方不是网络，是「读窄了」：diff 取正则一旦配错，
    新增链接会数成 0 条，而输出上写着「无事可做」——**扫描退化成空与一切正常
    在输出上完全一样**（这本书里已经出现过好几次）。所以下面第一组夹具全部在钉
    「哪些行算新增」这一件事。
    """
    bad = 0
    total = 11

    def check_1(name: str, got, want) -> None:
        nonlocal bad
        if got != want:
            print(f"  ✖ 夹具「{name}」：期望 {want!r}，实得 {got!r}")
            bad += 1

    # ① 新增行取链接；`+++` 文件头不算
    diff = ("--- a/REFERENCES.md\n+++ b/REFERENCES.md\n"
            "@@ -1 +1,2 @@\n+新出处：https://docs.example.com/a\n"
            "+另一条：https://docs.example.com/b\n")
    check_1("新增行上的链接都取到", collect_added_urls(diff),
            ["https://docs.example.com/a", "https://docs.example.com/b"])

    # ② 删掉的行不算（删掉的链接不该再去问）
    check_1("被删行上的链接不取", collect_added_urls("--- a/x\n+++ b/x\n"
                                                "-https://gone.example.com/z\n"),
            [])

    # ③ 同一新增行里的重复只算一次，尾随标点剥掉
    check_1("同行的重复链接与尾随标点",
            collect_added_urls("+见 https://a.example.com/p、https://a.example.com/p。\n"),
            ["https://a.example.com/p"])

    # ④ 空 diff 就是 0 条（由调用方据此说「无事可做」，而不是假装查过）
    check_1("空 diff 不假装有事", collect_added_urls(""), [])

    # ⑤ 缓存往返
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        cpath = Path(td) / "deep" / "cache.json"
        entries = {"https://a.example.com/p": {"url": "https://a.example.com/p",
                                              "status": 200, "final": "", "error": "",
                                              "verdict": "OK", "checked_at": 1000.0}}
        check_1("缓存写得进、读得出", cache_save(cpath, entries) and cache_load(cpath) == entries, True)

        # ⑥ 缓存坏了当空的：它是优化，不是事实
        cpath.write_text("{ 半截", encoding="utf-8")
        check_1("坏缓存当空的", cache_load(cpath), {})

        # ⑦ TTL：一周之内采信、一周之外重问
        fresh = {"checked_at": 1_000_000.0, "verdict": "OK"}
        check_1("TTL 内采信", cache_fresh(fresh, CACHE_TTL_SECONDS, 1_000_000.0 + 60), True)
        check_1("TTL 外重问", cache_fresh(fresh, CACHE_TTL_SECONDS, 1_000_000.0 + CACHE_TTL_SECONDS + 1), False)

        # ⑧ 非 OK 不进缓存：只有记着 OK 的才算命中（否则坏消息会被缓存盖住）
        urls = ["https://ok.example.com/", "https://dead.example.com/"]
        cache = {"https://ok.example.com/": {"checked_at": 1_000_000.0, "verdict": "OK"},
                 "https://dead.example.com/": {"checked_at": 1_000_000.0, "verdict": "失效"}}
        todo, hits = probe_plan(urls, cache, CACHE_TTL_SECONDS, 1_000_000.0 + 60)
        check_1("只有 OK 被采信", (todo, [h["url"] for h in hits]),
                (["https://dead.example.com/"], ["https://ok.example.com/"]))

    # ⑨ 判定极性：只有 4xx 拦提交；「未查」与「超时」都不拦
    #    （把「没轮到它」当成坏消息，会让提交门重新变成会因为无关原因响）
    check_1("未查不拦提交", blocks({"未查": 3, "超时": 1}), False)
    check_1("失效拦提交", blocks({"失效": 1, "未查": 9}), True)

    print(f"链接校验自检：{total - bad}/{total} 通过"
          + ("" if not bad else "（见上）"))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
