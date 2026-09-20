"""构建缓存：命中的判据是**这一层之前的输入**，不是「文件内容变没变」。

这一块回答的是同一件事的另一面：上一块量「打出来的东西有多重」，这一块量
**「改一行要重打多重、打多久」**。两者共用一个前提——每一行是一层，而层与层之间
只有一条单向的依赖：**前面任何一层失效，它后面全部重跑**。

三条官方口径，各自都反直觉：

1. **一旦某层失效，它之后的所有层都要重跑**（「即使它们本来会打出一样的结果」）——
   所以优化缓存的唯一办法是**把变化频繁的往后放、把不常变的往前放**；
2. `COPY` / `ADD` 的缓存校验和按**文件元数据**算，而**文件修改时间（mtime）不算**——
   所以「碰一下文件」不会让缓存失效，「改一个字」才会；
3. `RUN` 那一层**不会自动失效**。官方原话：`RUN apt-get update` 之后过一周重新构建，
   拿到的还是同一批包——**「上游有没有新版本」不在这一层的输入里**。
   要它重跑得给一个显式动作（`--no-cache`、`--no-cache-filter`、或让前面某一层变一变）。

这一块因此不量「构建有多快」（那要看机器），只量**哪些层重跑、以及重跑那几层
按剧本要花多久**——后者是写死的每层耗时，所以它查的是顺序的性质，不是机器的性能。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Instr:
    """一行指令。`files` 是它的缓存校验要看的**上下文文件**（COPY/ADD 才有）。

    注意这里没有 mtime 这个位置——**它不是漏了，是有意的**：官方明确说 mtime
    不参与校验和，所以模型里根本没有它可放的地方。
    """

    text: str
    files: tuple[str, ...] = ()
    seconds: int = 0
    label: str = ""


@dataclass(frozen=True)
class CacheRun:
    """一次构建的缓存结果：逐层命中情况。"""

    hits: tuple[bool, ...]

    @property
    def reused(self) -> int:
        return sum(1 for h in self.hits if h)

    @property
    def rebuilt(self) -> int:
        return len(self.hits) - self.reused

    @property
    def first_miss(self) -> int | None:
        for i, hit in enumerate(self.hits):
            if not hit:
                return i
        return None

    def seconds(self, instrs: tuple[Instr, ...]) -> int:
        """这一次构建要花多久：**只有重跑的那几层算**（脚本化的每层耗时）。"""
        return sum(ins.seconds for hit, ins in zip(self.hits, instrs) if not hit)


def cache_run(instrs: tuple[Instr, ...], *, changed: tuple[str, ...] = (),
              touched: tuple[str, ...] = (), edited: tuple[int, ...] = ()) -> CacheRun:
    """走一遍缓存查找。三个入参对应三种变化，**后两种的对照就是这一块的重点**：

    · `changed`：这几个文件的**内容**变了（让含它们的 COPY/ADD 失效）；
    · `touched`：这几个文件只是**时间戳**变了（官方：不影响缓存）；
    · `edited`：第几行指令的**文本**改了（那一层及之后重跑）。

    规则与官方一致：逐行比对，**第一处不命中之后，后面全部重跑**。
    """
    hits: list[bool] = []
    broken = False
    for i, ins in enumerate(instrs):
        hit = not broken
        if hit and i in edited:
            hit = False
        if hit and ins.files and any(f in changed for f in ins.files):
            hit = False
        hits.append(hit)
        if not hit:
            broken = True
    return CacheRun(tuple(hits))


#: 同一件事的两种写法。**它们的区别只有一处：`COPY` 放在依赖之前还是之后。**
#: 而这一处决定了「改一行源码」的代价差 36 倍。
UNSORTED: tuple[Instr, ...] = (
    Instr("COPY . /app", files=("requirements.txt", "app/main.py", "app/rag.py",
                                "tests/test_api.py", "data/corpus.jsonl", "README.md"),
          seconds=4, label="整个上下文一次拷进来"),
    Instr("RUN pip install -r requirements.txt", seconds=48, label="装依赖"),
    Instr("RUN apt-get update && apt-get install -y build-essential", seconds=95,
          label="装工具链"),
)

#: 顺序版：先拷依赖清单与装依赖，**源码放在最后**。
SORTED: tuple[Instr, ...] = (
    Instr("COPY requirements.txt .", files=("requirements.txt",), seconds=2, label="只拷依赖清单"),
    Instr("RUN pip install -r requirements.txt", seconds=48, label="装依赖"),
    Instr("COPY app ./app", files=("app/main.py", "app/rag.py"), seconds=4, label="拷源码"),
)

#: 这两种最常见的改动**不在同一个位置**：源码在最后、依赖清单在最前。
#: 所以「改一行」这句话必须带上是哪一个文件，否则答案在 4 秒与 147 秒之间。
SRC_FILE = "app/main.py"
DEP_FILE = "requirements.txt"


def variants(out_days: int = 0) -> list[dict]:
    """四种改动 × 两种顺序的对照表。**每一格都是跑出来的**。

    `out_days` 只用来给「缓存没过期」那一行起个名字——**它对结果没有任何影响**，
    而这一点正是第四行要证明的事。
    """
    cases: tuple[tuple[str, dict], ...] = (
        ("改一行源码", {"changed": (SRC_FILE,)}),
        ("改依赖清单", {"changed": (DEP_FILE,)}),
        ("只碰一下时间戳（内容没变）", {"touched": (SRC_FILE,)}),
        (f"什么都没改，隔 {out_days or 90} 天再构建一次", {}),
        ("把装依赖那一行的文本改一下", {"edited": (1,)}),
    )
    rows: list[dict] = []
    for label, kw in cases:
        row: dict = {"case": label}
        for name, instrs in (("unsorted", UNSORTED), ("sorted", SORTED)):
            run = cache_run(instrs, **kw)
            row[name] = {
                "rebuilt": run.rebuilt,
                "reused": run.reused,
                "seconds": run.seconds(instrs),
                "first_miss": run.first_miss,
            }
        rows.append(row)
    return rows
