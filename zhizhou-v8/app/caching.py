"""缓存与产物：**「命中」与「恢复了东西」不是一回事，而缓存与产物的作用域也不一样。**

这一块把两个很容易被当成一个的东西分开：

| | `actions/cache` | `upload-artifact` |
| --- | --- | --- |
| 它是什么 | 一份**跨 run 复用**的依赖目录 | 一次 run 的**产出**（报告、二进制、日志） |
| 谁看得见 | 有作用域：当前分支 ＋ 默认分支（单向） | 同一次 run 内的所有 job，但要 `needs:` |
| 能不能改 | **不能**——同 key 的内容一旦写下就不可变 | **不能**——v4 起 artifact 不可变，同名重传会失败 |
| 命中判据 | exact → partial → restore-keys（顺序查找） | `needs:` ＋ 名字；下载时自动比 SHA256 |
| 过期 | 7 天没访问被清；仓库上限 10 GB，超了按最后访问从旧往新清 | `retention-days`（且不能超过仓库上限） |

四条官方口径，各自都会让人写出一份「看着命中、其实在吃老本」的缓存：

1. **`cache-hit` 只在 exact 匹配时为真**。restore-key 的前缀命中会**真的把文件恢复出来**，
   而 `cache-hit` 是 `false`——所以「恢复了东西」与「命中」是两件事，
   拿 `cache-hit` 当「缓存有没有生效」的判据会得出相反结论；
2. **`key` 自己的部分匹配先于 `restore-keys`**。搜索顺序是
   当前分支上的 exact → 当前分支上的 partial → restore-keys（按顺序）→ 默认分支上再来一遍。
   所以「我写了 restore-keys 却拿到另一个版本」通常不是它没生效，是**它根本没轮到**；
3. **缓存不可改**。想更新只能换 key。于是**静态 key（不含指纹）的缓存是一份不再更新的缓存**：
   依赖变了、key 没变，保存那一步被跳过，而它看起来一直命中；
4. **缓存不签名、不校验；产物校验了也只报警告**。官方明说「能读缓存的人可以打开一个 PR 读到它」，
   低信任触发器在默认分支作用域只有读权；而它想写时**保存失败、step 与 job 都不失败**
   （日志里一句 warning）。产物那边同构：`download-artifact` 会自己算 SHA256 与上传时那一份比，
   **不一致只显示一句警告**，run 仍然是绿的。

这一块因此把「命中」拆成三个字段报：`matched`（命中哪一条）、`rule`（靠哪条规则命中的）、
`cache_hit`（官方那个布尔值）——**只报最后一个，前两个就会变成一句听起来对的话。**
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Entry:
    """一份缓存。`scope` 是它建在哪个 ref 上；`created` 是创建序号（越大越新）。"""

    key: str
    scope: str
    created: int
    accessed_day: int
    kb: int


#: 「今天」是第 45 天。`pip-3.9-aaaa` 与 `wheel-ubuntu-aaaa` 已经 40／25 天没被访问，
#: 而官方口径是**超过 7 天没访问就清掉**——它们其实早就不在了（`alive()` 会这么判），
#: 而这件事**不会出现在任何输出里**：它只让下一次构建慢一点。
NOW_DAY = 45
STALE_DAYS = 7

STORE: tuple[Entry, ...] = (
    Entry("pip-3.12-aaaa", "main", 1, 39, 180_000),
    Entry("pip-3.12-bbbb", "main", 4, 40, 182_000),
    Entry("pip-3.11-aaaa", "main", 2, 43, 175_000),
    Entry("pip-3.12-cccc", "feat/rag", 6, 41, 185_000),
    Entry("npm-aaaa", "main", 3, 39, 60_000),
    Entry("pip-3.9-aaaa", "main", 0, 5, 168_000),
    Entry("wheel-ubuntu-aaaa", "main", 5, 20, 90_000),
)

DEFAULT_BRANCH = "main"


def alive(entry: Entry, *, now: int = NOW_DAY) -> bool:
    """7 天没访问的那一条已经不在了——**这件事不影响「命中」的写法，只影响结果**。"""
    return now - entry.accessed_day <= STALE_DAYS


def restore(key: str, restore_keys: tuple[str, ...] = (), *,
            branch: str, store: tuple[Entry, ...] = STORE,
            default: str = DEFAULT_BRANCH) -> dict:
    """按官方那套顺序找回一份缓存，并说清**是哪一条规则让它命中的**。

    搜索顺序（官方原文的顺序，本项目把它逐条落成尝试记录）：

    ```
    当前分支上：key 精确 → key 的部分匹配 → restore-keys（按写的顺序，各按前缀找）
    默认分支上：同样的四步再来一遍
    ```

    「部分匹配」这一树按**前缀**读（与官方对 restore-keys 的读法同向：
    「以这个键开头的都会被匹配上」），并列时取**最新创建**的那一份。
    """
    tries: list[str] = []
    for scope in (branch, default):
        for rule, pattern in [("精确匹配 key", key)] + \
                [("key 的部分匹配", key)] + \
                [(f"restore-key：{rk}", rk) for rk in restore_keys]:
            pool = [e for e in store if e.scope == scope and alive(e)]
            if rule == "精确匹配 key":
                hits = [e for e in pool if e.key == pattern]
                label = f"{rule} @{scope}"
            elif rule == "key 的部分匹配":
                hits = [e for e in pool if e.key.startswith(pattern) and e.key != key]
                label = f"{rule} @{scope}"
            else:
                hits = [e for e in pool if e.key.startswith(pattern)]
                label = f"{rule} @{scope}"
            tries.append(label)
            if hits:
                best = max(hits, key=lambda e: e.created)
                return {
                    "key": key,
                    "branch": branch,
                    "matched": best.key,
                    "scope": best.scope,
                    "kb": best.kb,
                    "rule": label,
                    "cache_hit": best.key == key and best.scope == branch,
                    "tries": tuple(tries),
                }
    return {"key": key, "branch": branch, "matched": None, "scope": None, "kb": 0,
            "rule": "全都试过，没有", "cache_hit": False, "tries": tuple(tries)}


def save(key: str, kb: int, *, branch: str, store: tuple[Entry, ...] = STORE,
         extra: tuple[Entry, ...] = ()) -> dict:
    """保存一份缓存。**同 key 已存在时不能覆盖**（官方：缓存的内容不可改，只能换 key）。

    `extra` 是「这一次会话里已经存下去的」那一批（`save_sequence` 会往里放）——
    少了它，「静态 key 的第二次保存」会看起来成功，而真实行为是被跳过。
    """
    view = store + extra
    same = [e for e in view if e.scope == branch and e.key == key and alive(e)]
    if same:
        return {"saved": False, "kb": 0,
                "why": f"@{branch} 上已经有 {key}：内容不可改，只能换一个 key"}
    free, evicted = _evict(view, kb)
    return {"saved": True, "kb": kb, "evicted": evicted, "free_kb": free,
            "why": "新 key，存下去了"}


def save_sequence(saves: tuple[tuple[str, int], ...], *, branch: str = "main",
                  store: tuple[Entry, ...] = STORE) -> list[dict]:
    """连着存几次，看**缓存里留着的到底是哪一份**。

    这是「静态 key」那一行的现场：依赖改了三次、指纹没写进 key，于是三次保存
    里有两次被跳过，而每一次都**看起来命中**（因为那个 key 确实在）。
    """
    extra: list[Entry] = []
    held: dict[str, int] = {}          # 这个 key 上**真正留着的那一份**的体积
    rows: list[dict] = []
    for i, (key, kb) in enumerate(saves, start=1):
        res = save(key, kb, branch=branch, store=store, extra=tuple(extra))
        if res["saved"]:
            extra.append(Entry(key, branch, 100 + i, NOW_DAY, kb))
            held[key] = kb
        rows.append({"round": i, "key": key, "kb": kb, "saved": res["saved"],
                     "why": res["why"], "held_kb": held.get(key, 0)})
    return rows


#: 仓库上限（默认 10 GB，可上调；超出的用量计费）。清理按**最后访问时间从旧到新**。
LIMIT_KB = 10 * 1024 * 1024


def _evict(store: tuple[Entry, ...], add_kb: int, *, now: int = NOW_DAY) -> tuple[int, tuple[str, ...]]:
    """按官方的清理顺序腾地方：先按 7 天口径清，再按最后访问从旧到新清到限额以下。"""
    live = [e for e in store if alive(e, now=now)]
    total = sum(e.kb for e in live)
    evicted: list[str] = []
    for entry in sorted(live, key=lambda e: (e.accessed_day, e.key)):
        if total + add_kb <= LIMIT_KB:
            break
        total -= entry.kb
        evicted.append(entry.key)
    return LIMIT_KB - total - add_kb, tuple(evicted)


#: 一个「大仓库」的缓存账：总量 11.2 GB，**每一条都在 7 天内被访问过**，
#: 所以 7 天那条规则一条都清不掉——超限时起作用的是「最后访问从旧到新」。
MONOREPO: tuple[Entry, ...] = (
    Entry("torch-main", "main", 10, 45, 2_458_000),
    Entry("mypy-cache", "main", 9, 45, 1_843_000),
    Entry("uv-cache", "main", 8, 44, 1_536_000),
    Entry("pip-cache", "main", 7, 43, 1_229_000),
    Entry("huggingface", "main", 6, 42, 921_000),
    Entry("npm-cache", "main", 5, 41, 819_000),
    Entry("playwright", "main", 4, 40, 717_000),
    Entry("go-build", "main", 3, 39, 614_000),
    Entry("cargo-registry", "main", 2, 39, 512_000),
    Entry("gradle", "main", 1, 38, 410_000),
)


# ------------------------------------------------------- 产物

@dataclass(frozen=True)
class Artifact:
    """一次 run 的产出。`digest` 是上传时那份的 SHA256（官方 v4 起会返回它）。"""

    name: str
    job: str
    kb: int
    files: tuple[str, ...]
    digest: str


REPORT = Artifact("test-report", "test", 1_240,
                  ("report/junit.xml", "report/coverage.html", "report/summary.md"),
                  "sha256:9f2c…")


def fetch(art: Artifact, *, needs: tuple[str, ...]) -> dict:
    """另一个 job 来取这份产物。**`needs:` 是「拿得到」的判据**，不是顺序偏好。"""
    if art.job not in needs:
        return {"ok": False, "why": f"没有 `needs: {art.job}`——它不会等那个 job 跑完，也就取不到"}
    return {"ok": True, "kb": art.kb, "files": art.files, "dir": art.name}


def reupload(existing: tuple[str, ...], name: str) -> dict:
    """v4 起产物不可变：**同名重传会失败**（没有「覆盖」这个动作）。"""
    if name in existing:
        return {"saved": False, "why": f"`{name}` 已经存在：产物不可变，要换一个名字"}
    return {"saved": True, "why": "新名字"}


def verify(art: Artifact, *, tampered: tuple[str, ...] = ()) -> dict:
    """下载时自动比 SHA256。**不一致只报一句警告**——run 仍然是绿的。"""
    if not tampered:
        return {"match": True, "level": "—", "green": True}
    return {"match": False, "level": "warning",
            "green": True,
            "why": f"{len(tampered)} 个文件与上传时不一样，而这只记成一句警告"}
