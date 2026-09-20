"""镜像与层：把「这一叠层一共多重、删了为什么不变小」变成一张能复算的账。

这一章接的是 1.1（本地环境）与 5.7（把服务装成常驻进程）留下的那句话的反面：
**它在你这台机器上跑得起来，不等于它能被交出去。** 六件事里这一件是地基——
「交出去的那个东西」到底是什么、有多重、改一行要重打多重。

三条判据，各自对应一个不会报错的错觉：

**① 每一行 `RUN` 都是一层，而层是只加的。** 在**后面一层**里删掉前面一层加进来的
文件，只会再加一层「白障」把那些文件遮住——**看得见的那一份变小了，而镜像没有**。
所以「镜像多大」与「占用多大」是两个数，本模块把两个都算出来（`image_kb` / `visible_kb`），
它们的差就是**交付了却没人能用上**的那部分（`wasted_kb`）。

**② `RUN` 那一层的缓存不会自己过期。** 官方写得很直白：`RUN apt-get update` 之后
隔一周重新构建，**拿到的还是同一批包**——缓存命中的判据是「这一层的输入有没有变」，
而「上游仓库里有没有新版本」不在它的输入里。所以「永远最新」需要一个显式的动作
（`--no-cache` / `--pull` / 一个会变的参数），不是一个期望。

**③ 密钥写进 `ENV` 会留在镜像配置里，和后来删没删那行无关。** 官方把 `ENV` 与
`ARG` 一起点名（「它们会留在最终镜像里」），区别只在**留在哪里**：`ENV` 留在
镜像配置（任何人 pull 下来就能读），`ARG` 不留在配置里但**参与缓存校验**、
且被 `RUN` 写进文件的那一份留在层里。真正不进任何一处的是 `--mount=type=secret`
——官方原话：**secret 的内容不参与构建缓存的校验**。

依据是 Docker 官方文档的五处：镜像层（每层是只加的文件系统变化）、构建缓存
（一旦某层失效，它之后的所有层都要重跑）、缓存失效（`COPY`/`ADD` 按文件元数据算校验和、
**mtime 不算**）、多阶段构建（`COPY --from` 只带走产物）、构建密钥（`ENV`/`ARG`
不适合传密钥，因为它们留在镜像里）。
"""

from __future__ import annotations

from dataclasses import dataclass, field

# --------------------------------------------------------------- 一、层的模型

#: 每删掉一个路径，那一层里会留下一个「白障」条目把它遮住。它很小，但**不为零**——
#: 这一点在下面的账里是故意的：`rm` 那一层不是「没有大小」，它是「大小约等于 0
#: 而遮住的那部分仍然在盘上」。
WHITEOUT_KB = 1


@dataclass(frozen=True)
class Change:
    """一次文件系统变化：加进来的（路径, KB），与删掉的路径。"""

    add: tuple[tuple[str, int], ...] = ()
    remove: tuple[str, ...] = ()


@dataclass(frozen=True)
class Step:
    """一行指令。`change` 是它对文件系统做了什么，`seconds` 是重建它要多久（脚本化的）。"""

    instruction: str
    change: Change = Change()
    note: str = ""
    seconds: int = 0


@dataclass(frozen=True)
class Layer:
    """一层：它有多大、遮了几个路径、重建要几秒、以及**它按内容算出来的是哪一层**。

    `digest` 不是哈希函数算的，而是把这一层的文件系统变化**写成一句可读的指纹**
    （`+a,b -c`）——层是内容寻址的，所以「同一层」就是「同一句指纹」。
    它存在的理由只有一个：**推送与拉取是逐层比指纹的，不是整份换的**。
    """

    index: int
    instruction: str
    size_kb: int
    whiteouts: int
    seconds: int
    digest: str = ""


@dataclass(frozen=True)
class Script:
    """一份 Dockerfile 的文件系统剧本（含基础镜像那一叠自己也算进来）。"""

    name: str
    label: str
    base: str
    base_kb: int
    steps: tuple[Step, ...]
    note: str = ""


@dataclass(frozen=True)
class Build:
    """一次构建的结果。**四个数里最要紧的是 `wasted_kb`**（见模块开头 ①）。"""

    script: Script
    layers: tuple[Layer, ...]
    live: dict[str, int] = field(default_factory=dict)

    @property
    def layer_kb(self) -> int:
        """这一份 Dockerfile 自己产生的那些层加起来（不含基础镜像）。"""
        return sum(layer.size_kb for layer in self.layers)

    @property
    def image_kb(self) -> int:
        """镜像一共多重：基础镜像 ＋ 每一行产生的层（**层是只加的**）。"""
        return self.script.base_kb + self.layer_kb

    @property
    def visible_kb(self) -> int:
        """最终那个联合文件系统里还看得见多少（把白障遮住的那些减掉）。"""
        return sum(self.live.values())

    @property
    def wasted_kb(self) -> int:
        """**交付了、却没人能用上**的那部分：层账减去可见账。"""
        return self.layer_kb - self.visible_kb

    @property
    def squashed_kb(self) -> int:
        """如果把它压成一层（只有可见的那部分），本该有多重。"""
        return self.script.base_kb + self.visible_kb

    @property
    def seconds(self) -> int:
        return sum(layer.seconds for layer in self.layers)

    def layers_of(self, keywords: str) -> tuple[Layer, ...]:
        """按关键字挑层（读数与夹具都靠它指到具体那一层）。"""
        return tuple(layer for layer in self.layers
                     if layer.instruction.split(" ", 1)[0] == keywords)


def run(script: Script) -> Build:
    """把一份剧本走一遍，得到层账与可见账。

    两条规则就是官方的两条：**每一行产生一层，层里的内容是「加进来的文件 ＋
    被删路径的白障」**——而删掉的那些字节仍然算在前面某一层的账上。
    """
    layers: list[Layer] = []
    live: dict[str, int] = {}
    for index, step in enumerate(script.steps, 1):
        for path, kb in step.change.add:
            live[path] = kb
        for path in step.change.remove:
            live.pop(path, None)
        size = sum(kb for _, kb in step.change.add) + WHITEOUT_KB * len(step.change.remove)
        #: 指纹里**必须带上体积**（层的内容就是「哪些文件、各多少字节」）——
        #: 只写路径的话，「改了一行源码」会被判成「没变」（本节的自检里有一条就是它）。
        digest = "+" + ",".join(f"{p}:{kb}" for p, kb in sorted(step.change.add)) + \
                 " -" + ",".join(sorted(step.change.remove))
        layers.append(Layer(index=index, instruction=step.instruction, size_kb=size,
                            whiteouts=len(step.change.remove), seconds=step.seconds,
                            digest=digest))
    return Build(script=script, layers=tuple(layers), live=live)


# --------------------------------------------------------------- 二、六份剧本

#: 上下文里有什么。**它是三份剧本共用的那一份**——`.dockerignore` 那一招改的
#: 不是 Dockerfile，而是这个集合。
CONTEXT: tuple[tuple[str, int], ...] = (
    ("/app/requirements.txt", 2),
    ("/app/app", 1_200),
    ("/app/tests", 1_800),
    ("/app/data/corpus", 9_000),
    ("/app/README.md", 40),
    ("/app/.venv", 15_000),
    ("/app/.git", 26_000),
)

#: 一份普通的 Python 应用装完之后的两笔固定开销：依赖本身，与**装它时顺手留下的缓存**。
SITE_PACKAGES_KB = 210_000
PIP_CACHE_KB = 62_000
#: 编译工具链与它的包索引。工具链只有在**装依赖那一刻**需要，之后全程用不到；
#: 索引文件在装完之后也没有任何用处。
TOOLCHAIN_KB = 220_000
APT_LISTS_KB = 30_000

BASE_PYTHON = ("python:3.12", 1_020_000)
BASE_SLIM = ("python:3.12-slim", 130_000)


def _ctx(*paths: str) -> Change:
    """从上下文里挑几个路径加进来（顺序按 `CONTEXT` 走，便于逐项对账）。"""
    kept = set(paths)
    return Change(add=tuple((p, kb) for p, kb in CONTEXT if p in kept))


#: ① 朴素版：`COPY . .` 一把梭 ＋ 装完再删缓存。
NAIVE = Script(
    name="naive",
    label="① 朴素版（`COPY . .` ＋ 装完再删缓存）",
    base=BASE_PYTHON[0], base_kb=BASE_PYTHON[1],
    steps=(
        Step("COPY . /app", _ctx(*(p for p, _ in CONTEXT)),
             "整个上下文都进来了：版本历史、测试、语料、本地虚拟环境", seconds=4),
        Step("RUN pip install -r requirements.txt",
             Change(add=(("/usr/local/lib/python3.12/site-packages", SITE_PACKAGES_KB),
                         ("/root/.cache/pip", PIP_CACHE_KB))),
             f"依赖 {SITE_PACKAGES_KB // 1000} MB，**装它时留下的缓存另外 {(PIP_CACHE_KB) // 1000} MB**",
             seconds=48),
        Step("RUN apt-get update && apt-get install -y build-essential",
             Change(add=(("/usr/lib/gcc", TOOLCHAIN_KB), ("/var/lib/apt/lists", APT_LISTS_KB))),
             "工具链与包索引都留在了这一层", seconds=95),
        Step("RUN rm -rf /root/.cache/pip /var/lib/apt/lists /app/.venv",
             Change(remove=("/root/.cache/pip", "/var/lib/apt/lists", "/app/.venv")),
             "**这一行只让看得见的那一份变小**", seconds=2),
        Step("USER app"),
        Step('CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]'),
    ),
    note="基线：每一件事都做了，只是顺序与位置不对",
)

#: ② 合并 `RUN`：让那两笔开销**根本不产生**（而不是产生完再删）。
MERGED = Script(
    name="merged",
    label="② 合并 `RUN`（`--no-cache-dir` ＋ 索引随装随删）",
    base=BASE_PYTHON[0], base_kb=BASE_PYTHON[1],
    steps=(
        Step("COPY . /app", _ctx(*(p for p, _ in CONTEXT)),
             "上下文没动（这一招只管装的那一层）", seconds=4),
        Step("RUN pip install --no-cache-dir -r requirements.txt",
             Change(add=(("/usr/local/lib/python3.12/site-packages", SITE_PACKAGES_KB),)),
             "缓存不落盘：`--no-cache-dir`", seconds=46),
        Step("RUN apt-get update && apt-get install -y --no-install-recommends build-essential"
             " && rm -rf /var/lib/apt/lists/*",
             Change(add=(("/usr/lib/gcc", TOOLCHAIN_KB),)),
             "索引在同一层里就删掉——它从来没有变成过一层", seconds=95),
        Step("USER app"),
        Step('CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]'),
    ),
    note="省下的是「装完再删」那一步删不掉的字节",
)

#: ③ `.dockerignore`：让不该进上下文的东西**根本没进来**。
IGNORED = Script(
    name="ignored",
    label="③ `.dockerignore`（把版本历史、测试、语料、本地虚拟环境挡在上下文外）",
    base=BASE_PYTHON[0], base_kb=BASE_PYTHON[1],
    steps=(
        Step("COPY . /app",
             _ctx("/app/requirements.txt", "/app/app", "/app/data/corpus", "/app/README.md"),
             "`CONTEXT` 里那四项，其余三项被 `.dockerignore` 挡在门外", seconds=2),
        Step("RUN pip install -r requirements.txt",
             Change(add=(("/usr/local/lib/python3.12/site-packages", SITE_PACKAGES_KB),
                         ("/root/.cache/pip", PIP_CACHE_KB))),
             "这一招不管装的那一层", seconds=48),
        Step("RUN apt-get update && apt-get install -y build-essential",
             Change(add=(("/usr/lib/gcc", TOOLCHAIN_KB), ("/var/lib/apt/lists", APT_LISTS_KB))),
             "同上", seconds=95),
        Step("RUN rm -rf /root/.cache/pip /var/lib/apt/lists /app/.venv",
             Change(remove=("/root/.cache/pip", "/var/lib/apt/lists", "/app/.venv")),
             "被挡在外面的路径，这一行仍然为它留一个白障（**白障不因为路径不在而免费**）",
             seconds=2),
        Step("USER app"),
        Step('CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]'),
    ),
    note="这一招与另外三招有一个本质区别：**它减掉的东西从来没有进过镜像**",
)

#: ④ 多阶段：编译那一套留在 builder 里，最终阶段只带走产物。
MULTISTAGE = Script(
    name="multistage",
    label="④ 多阶段构建（`COPY --from=build` 只带走 `site-packages` 与源码）",
    base=BASE_PYTHON[0], base_kb=BASE_PYTHON[1],
    steps=(
        Step("COPY --from=build /usr/local/lib/python3.12/site-packages /usr/local/lib/...",
             Change(add=(("/usr/local/lib/python3.12/site-packages", SITE_PACKAGES_KB),)),
             "只把**装好的依赖**带过来，装它的过程与工具链留在 builder", seconds=6),
        Step("COPY --from=build /app/app /app/app", Change(add=(("/app/app", 1_200),)),
             "源码", seconds=1),
        Step("COPY --from=build /app/README.md /app/README.md",
             Change(add=(("/app/README.md", 40),)), "附属文件", seconds=1),
        Step("USER app"),
        Step('CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]'),
    ),
    note="唯一一招能把「浪费」归零：**没有被带过来的东西，不在最终镜像里**",
)

#: ⑤ 换基础镜像：`python:3.12` → `python:3.12-slim`。**它是四招里省得最多的一招**，
#: 也是唯一一招会**带走能力**的（slim 里没有编译器，所以它与 ④ 配套才有意义）。
SLIM_BASE = Script(
    name="slim-base",
    label="⑤ 换基础镜像（`python:3.12` → `python:3.12-slim`）",
    base=BASE_SLIM[0], base_kb=BASE_SLIM[1],
    steps=NAIVE.steps,
    note="与 ① 只差基础镜像那一叠——**其余一个字都没改**",
)

#: ⑥ 四招一起：这一章交付的那份 Dockerfile。
FINAL = Script(
    name="final",
    label="⑥ 四招一起（`.dockerignore` ＋ slim 基础镜像 ＋ 合并 `RUN` ＋ 多阶段）",
    base=BASE_SLIM[0], base_kb=BASE_SLIM[1],
    steps=(
        Step("COPY --from=build /usr/local/lib/python3.12/site-packages /usr/local/lib/...",
             Change(add=(("/usr/local/lib/python3.12/site-packages", SITE_PACKAGES_KB),)),             " builder 用 slim（它有编译器吗？——没有，所以 builder 是 `build-stage`"
             "：`RUN apt-get install --no-install-recommends build-essential && pip install"
             " --no-cache-dir` 之后再 `COPY --from`）", seconds=6),
        Step("COPY --from=build /app/app /app/app", Change(add=(("/app/app", 1_200),)),
             "源码", seconds=1),
        Step("COPY --from=build /app/README.md /app/README.md",
             Change(add=(("/app/README.md", 40),)), "附属文件", seconds=1),
        Step("USER app"),
        Step('CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]'),
    ),
    note="这就是 8.1 交付的那份 Dockerfile",
)

SCRIPTS: tuple[Script, ...] = (NAIVE, MERGED, IGNORED, MULTISTAGE, SLIM_BASE, FINAL)


def build_of(name: str) -> Build:
    for script in SCRIPTS:
        if script.name == name:
            return run(script)
    raise KeyError(name)


def slimming_table() -> list[dict]:
    """瘦身四招的账：**四招各与基线单独比，不叠加**（叠加要重新算一遍，见最后一行）。

    为什么必须单算：四招动的是同一个数（层账）的不同部分，两两之间会互相吃掉
    ——比如「合并 `RUN`」省下的那 92 MB 里，有一部分本来就会被「多阶段」一起带走。
    一张把四招加起来等于最终值的表，是一张**每一项都不可信**的表。
    """
    base = build_of("naive")
    rows: list[dict] = []
    for script in (MERGED, IGNORED, MULTISTAGE, SLIM_BASE, FINAL):
        build = run(script)
        rows.append({
            "name": script.name,
            "label": script.label,
            "image_kb": build.image_kb,
            "saved_kb": base.image_kb - build.image_kb,
            "wasted_kb": build.wasted_kb,
            "note": script.note,
        })
    return rows


# --------------------------------------------------------------- 三、改一处要重发多少

#: 假装的那条链路：25 MB/s（脚本化的，所以「拉一次要多久」这个数能拿纸笔复算）。
LINK_MBPS = 25


def restamped(script: Script, *, path: str, kb: int) -> Script:
    """同一个剧本、**只把一个文件的体积改一下**——用来算「改一处要重发多少」。

    为什么用「改体积」而不是「改内容」：层是内容寻址的，两者对**层指纹**的影响
    完全一样（指纹变了），而用体积能让对账落在一个手算得出来的数上。
    """
    steps: list[Step] = []
    for step in script.steps:
        change = Change(
            add=tuple((p, kb if p == path else size) for p, size in step.change.add),
            remove=step.change.remove,
        )
        steps.append(Step(step.instruction, change, step.note, step.seconds))
    return Script(name=script.name + "-restamped", label=script.label + "（改一处之后）",
                  base=script.base, base_kb=script.base_kb, steps=tuple(steps),
                  note=script.note)


def pull_seconds(kb: int, *, mbps: int = LINK_MBPS) -> float:
    """把这些 KB 拉下来要多久（**不算解压与启动**，那两段与字节数无关）。"""
    return kb / (mbps * 1000)


def transfer_report(a: Build, b: Build) -> dict:
    """两份构建之间：**哪几层要重发、一共多少字节**。

    这就是「镜像小 ≠ 拉取小」的可算形式：层是内容寻址的，两份镜像共有 99% 的层时，
    推拉只走那一层变了的——而**前面所有层失效并不等于它们的内容都变了**
    （重建出来的层如果内容一样，指纹也一样，不会被重发）。
    """
    by_index = {layer.index: layer for layer in a.layers}
    changed = [layer for layer in b.layers
               if by_index.get(layer.index) is None
               or by_index[layer.index].digest != layer.digest]
    return {
        "layers": len(b.layers),
        "same": len(b.layers) - len(changed),
        "changed": len(changed),
        "changed_kb": sum(layer.size_kb for layer in changed),
        "total_kb": b.image_kb,
        "changed_instructions": tuple(layer.instruction for layer in changed),
    }


# --------------------------------------------------------------- 四、密钥三档

#: 同一个密钥的三种递法。四个布尔值回答同一句话：**它留在了谁看得见的地方。**
#: `config`＝镜像配置（`docker inspect` 就有）；`layer`＝某一层里（层是可以被 pull 下来的）；
#: `cache`＝构建缓存的校验输入（换了值就换一层，缓存因此能被当成侧信道）。
SECRET_RUNGS: tuple[dict, ...] = (
    {"rung": "env", "label": "`ENV API_KEY=…`",
     "decl": "ENV API_KEY=sk-…",
     "config": True, "layer": True, "cache": True,
     "how": "写在镜像配置里：**任何人 pull 下来 `docker inspect` 就能读**，"
            "而后来把这一行删掉，已经构建出来的那一版仍然带着它"},
    {"rung": "arg", "label": "`ARG` ＋ `RUN echo $API_KEY > /tmp/k`",
     "decl": 'ARG API_KEY\nRUN echo "$API_KEY" > /tmp/k',
     "config": False, "layer": True, "cache": True,
     "how": "值不在配置里，但**写进文件的那一份留在层里**，而且它参与缓存校验"
            "（官方：换了 `--build-arg` 的值，那一层就会重建）"},
    {"rung": "secret", "label": "`RUN --mount=type=secret,id=key`",
     "decl": "RUN --mount=type=secret,id=key sh -c 'cat /run/secrets/key > /dev/null'",
     "config": False, "layer": False, "cache": False,
     "how": "挂在构建容器里的临时文件，只在那一条指令的执行期间存在；"
            "官方原话：**secret 的内容不参与构建缓存的校验**"},
)


def secret_ladder() -> list[dict]:
    """三档各一行，附上「它留在哪几处」的个数——**这就是这一组的读数**。"""
    return [dict(row, leaks=sum(bool(row[k]) for k in ("config", "layer", "cache")))
            for row in SECRET_RUNGS]


def secret_visible_to(rung: str) -> tuple[str, ...]:
    """这个递法把密钥**交给了几种人**（用来把「三档」说成一句人话）。"""
    row = next(r for r in SECRET_RUNGS if r["rung"] == rung)
    who: list[str] = []
    if row["config"]:
        who.append("任何拿到这个镜像的人")
    if row["layer"]:
        who.append("任何一个拉过这个镜像的机器（包括 CI 的缓存）")
    if row["cache"]:
        who.append("任何一个能读构建缓存的人")
    return tuple(who)


# --------------------------------------------------------------- 五、读数的标记

def kb(n: int) -> str:
    """把 KB 读成人看的单位——**读数里两个单位都要给**（MB 便于比，GB 便于直觉）。"""
    return f"{n / 1000:.0f} MB" if n < 1_000_000 else f"{n / 1_000_000:.2f} GB"
