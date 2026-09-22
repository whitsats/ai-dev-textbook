<!-- 由 `tools/appendix.py` 生成：重生成 `python tools/appendix.py --sync`，
     对账 `python tools/appendix.py --check`（提交门 4h/5 与 CI 各跑一次）。**不要手改。** -->

# 附录

> 这一份只回答读者最先遇到的三件事：**跑哪一条命令**（附录 A）｜**每支门脚本管什么**
> （附录 B）｜**书里那些数从哪儿来**（附录 C）。
>
> 它是**生成物**：每一格都从盘上读出来——六棵树的目录与入口脚本的 docstring、每个脚本的
> `--offline`、`.githooks/pre-commit` 的阶段名、各树的 `requirements.txt`。
> 所以「书改了而附录没重生」不是笔误，是一处会被拦下的不一致。
>
> 一个提醒：附录 A 的入口命令**一律不要密钥、不要网络**；去掉 `--offline` 才是真机那一趟
> （那几趟要 API key，正文在对应的章里写了各自要什么）。

## 附录 A　六棵可运行树：先跑哪一条命令

六棵树都是**自包含**的：进它的目录、按最后一列装依赖、跑该章的离线入口即可。
「测试用例」是静态读数（数 `def test_`），与正文里的「全树 N 条」同一个数。

| 篇 | 树 | 章 | `app/` 模块 | 测试模块 | 测试用例 | 依赖 |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| 第 3 篇 大模型与Agent原理 | `zhizhou-v3/` | 10 | 21 | 11 | 150 | 8 个：`httpx`、`pydantic`、`sqlalchemy`、`alembic`、`tiktoken`、`fastapi`、`uvicorn`、`pytest` |
| 第 4 篇 AI应用开发框架 | `zhizhou-v4/` | 5 | 13 | 5 | 84 | 5 个：`langchain`、`langchain-openai`、`langgraph`、`openai`、`pytest` |
| 第 5 篇 RAG与生产级系统 | `zhizhou-v5/` | 9 | 20 | 12 | 178 | 8 个：`langchain`、`langchain-openai`、`pymupdf`、`pillow`、`python-docx`、`python-pptx`、`pytesseract`、`pytest` |
| 第 6 篇 模型接入与成本工程 | `zhizhou-v6/` | 4 | 7 | 7 | 87 | 零依赖（标准库：dataclasses、hashlib、json、math、pathlib、random、sys） |
| 第 7 篇 AI应用工程化 | `zhizhou-v7/` | 5 | 10 | 10 | 185 | 零依赖（标准库：base64、collections、dataclasses、difflib、hashlib、json、math、pathlib、random、re、statistics、sys、typing、unicodedata） |
| 第 8 篇 交付与产品化 | `zhizhou-v8/` | 5 | 19 | 19 | 343 | 零依赖（标准库：dataclasses、fnmatch、math、pathlib、random、sys） |

（依赖那一列是各树 `requirements.txt` 的全部声明，**含只在跑测试时需要**的那些；写成「零依赖」的树一个第三方包都不装。）

### A.1 第 3 篇 · `zhizhou-v3/`（10 章 ｜ 150 条用例）

在该目录下跑；跑对了会看到 `离线自检通过`（去掉 `--offline` 是真机那一趟）。

| 入口 | 这个脚本干什么 |
| --- | --- |
| `python demo.py --offline` | 知舟 Agent 版的七条演示路径。默认**真的调用模型**；`--offline` 用假策略跑同一套骨架。 |
| `python scripts/acceptance.py --offline` | 一键验收：起服务 → 三条路径走 HTTP → 打印读数。 |

### A.2 第 4 篇 · `zhizhou-v4/`（5 章 ｜ 84 条用例）

在该目录下跑；跑对了会看到 `离线自检通过`（去掉 `--offline` 是真机那一趟）。

| 入口 | 这个脚本干什么 |
| --- | --- |
| `python scripts/agent_tools.py --offline` | 4.3 的可运行脚本：工具、循环、护栏，四组读数。 |
| `python scripts/first_app.py --offline` | 第一个框架版应用：**多轮问答 ＋ 裁剪 ＋ 记账**。 |
| `python scripts/persistence_multiagent.py --offline` | 4.5 的可运行脚本：持久化与多智能体编排，五组读数。 |
| `python scripts/prompt_chain.py --offline` | 提示模板、解析器与 LCEL 编排：五段可验收的读数。 |
| `python scripts/state_graph.py --offline` | 4.4 的可运行脚本：图的机制读数，六组。 |

### A.3 第 5 篇 · `zhizhou-v5/`（9 章 ｜ 178 条用例）

在该目录下跑；跑对了会看到 `离线自检通过`（去掉 `--offline` 是真机那一趟）。

| 入口 | 这个脚本干什么 |
| --- | --- |
| `python scripts/acceptance.py --offline` | 5.8 的端到端验收：**一条命令回答「这一版知识库能不能上」。** |
| `python scripts/generate_reader.py --offline` | 5.5 的读数：**生成侧的四组账，外加真机上的一遍引用核对。** |
| `python scripts/recap.py --offline` | 5.9 的文档对账：**让手写的第二份清单自己对账。** |
| `python scripts/retrieve_reader.py --offline` | 5.4 读数：**三条路（字面／向量／融合）与两个后处理（改写／重排）各自改了什么。** |
| `python scripts/serve_reader.py --offline` | 5.7 的读数：**在线侧的六组账，外加一遍夹具自检。** |
| `python scripts/split_reader.py --offline` | 5.2 读数：**换切法到底换来了什么**。 |
| `python scripts/vector_reader.py --offline` | 5.3 读数：**向量到底比字面匹配多拿到了什么。** |
| `python scripts/why_rag.py --offline` | 5.1 读数：**同一句问题、同一个模型，只差「有没有资料」**。 |

### A.4 第 6 篇 · `zhizhou-v6/`（4 章 ｜ 87 条用例）

在该目录下跑；跑对了会看到 `离线自检通过`（去掉 `--offline` 是真机那一趟）。

| 入口 | 这个脚本干什么 |
| --- | --- |
| `python scripts/gateway_reader.py --offline` | 6.3 的读数脚本：把「出错之后怎么办」变成六组能复算的数。 |
| `python scripts/meter_reader.py --offline` | 6.4 的读数脚本：把「成本与性能」变成六组能复算的数。 |
| `python scripts/select_reader.py --offline` | 6.1 的读数脚本：把「选型」变成六组能复算的数。 |
| `python scripts/wire_reader.py --offline` | 6.2 的读数脚本：把「三家不一样」变成六组能复算的数。 |

### A.5 第 7 篇 · `zhizhou-v7/`（5 章 ｜ 185 条用例）

在该目录下跑；跑对了会看到 `离线自检通过`（去掉 `--offline` 是真机那一趟）。

| 入口 | 这个脚本干什么 |
| --- | --- |
| `python scripts/pipeline_reader.py --offline` | 7.1 的读数脚本：把「怎么知道它还行」变成六组能复算的数。 |
| `python scripts/privacy_reader.py --offline` | 7.5 的读数脚本：把「留存、隐私、审计」变成六组能复算的数。 |
| `python scripts/rollout_reader.py --offline` | 7.3 的读数脚本：把「改了哪一版、谁看到了它」变成六组能复算的数。 |
| `python scripts/security_reader.py --offline` | 7.4 的读数脚本：把「安全怎么落地」变成六组能复算的数。 |
| `python scripts/trace_reader.py --offline` | 7.2 的读数脚本：把「出了事怎么看见」变成六组能复算的数。 |

### A.6 第 8 篇 · `zhizhou-v8/`（5 章 ｜ 343 条用例）

在该目录下跑；跑对了会看到 `离线自检通过`（去掉 `--offline` 是真机那一趟）。

| 入口 | 这个脚本干什么 |
| --- | --- |
| `python scripts/ci_reader.py --offline` | 8.2 的读数脚本：把「有没有人去跑这一版」变成六组能复算的数。 |
| `python scripts/deploy_reader.py --offline` | 8.1 的读数脚本：把「交出去的那个东西」变成六组能复算的数。 |
| `python scripts/quota_reader.py --offline` | 8.4 的读数脚本：把「多租户、配额与计费」变成六组能复算的数。 |
| `python scripts/slo_reader.py --offline` | 8.5 的读数脚本：把「线上运维」变成六组能复算的数。 |
| `python scripts/stream_reader.py --offline` | 8.3 的读数脚本：把「一个字一个字地到达」变成六组能复算的数。 |

## 附录 B　门脚本速查

`tools/` 下每一支脚本：它管什么、怎么单独跑、跑在提交门的哪一关。
阶段号与说明照抄 `.githooks/pre-commit` 自己的那份（它才是事实来源）。

| 脚本 | 一句话 | 自己声明的开关 | 跑在提交门的哪一关 |
| --- | --- | --- | --- |
| `appendix.py` | 附录（`APPENDIX.md`）的生成器：**读者要跑什么、每支门脚本管什么、数从哪来。** | （无开关） | 1/5；4h/5 |
| `audit_coverage.py` | 素材覆盖度审计：逐章核算"可用素材汉字量"与"计划篇幅"的关系，用于校准 PLAN.md。 | `--md`／`--pool`／`--out`／`--check`／`--risk-table`／`--self-test` | 1/5；3/5 |
| `backend_index.py` | 10.5 的交付物：**把一份 Java 体系的后端题库，换成 Python／AI 岗位的视角。** | `--bank`／`--offline`／`--check`／`--self-test` | 1/5；4c/5 |
| `bank_index.py` | 第 10 篇的交付物：**把题库收敛成一份可核对的考点索引。** | `--bank`／`--offline`／`--counts`／`--check`／`--self-test` | 1/5；4b/5 |
| `check_refs.py` | 校验 REFERENCES.md 中的官方文档链接是否仍然有效。 | `--offline`／`--only-broken`／`--timeout`／`--workers`／`--file` | 5/5 |
| `check_runnable.py` | 可运行树的一致性门（`zhizhou-v3/` 手写版与 `zhizhou-v4/` 框架版）。 | `--self-test` | 1/5；4/5 |
| `extract_sources.py` | 把 raw/ 中的原始资料转换为 sources/ 下的纯文本素材库。 | `--report` | 素材：`--report` 把 `raw/` 转成 `sources/`，与书稿无关 |
| `index_book.py` | 全书索引（index_book.py） | `--sync`／`--check`／`--self-test` | 1/5；4f/5 |
| `install_hooks.py` | 安装提交前校验钩子（install_hooks.py） | `--uninstall`／`--status`／`--self-test` | 装机：`python tools/install_hooks.py` 装一次提交钩子 |
| `lint_book.py` | 正文一致性校验（lint_book.py） | `--only`／`--quiet`／`--self-test` | 1/5；2/5 |
| `mobile_index.py` | 10.6 的交付物：**两份移动端题库，拼成一份可核对的索引。** | `--offline`／`--check`／`--self-test` | 1/5；4d/5 |
| `mock_round.py` | 10.7 的交付物：**把一场 45 分钟的模拟面试，变成四组能复算的数。** | `--offline`／`--check`／`--self-test` | 1/5；4e/5 |
| `revisit.py` | 通读修订的候选生成器（跨篇的一致性、口径与重复）。 | `--check`／`--shapes`／`--dupes`／`--facts`／`--self-test` | 1/5；4g/5 |
| `style_claims.py` | 书侧手写数字的对账（style_claims.py） | （无开关） | 库：被四支工具的自检调用，自己没有入口 |
| `totals.py` | 全书汇总数字的**单一来源**：生成、对账、自检。 | `--check`／`--sync`／`--self-test`／`--sites` | 1/5；3b/5 |
| `trace_refs.py` | 改稿前的引用清单：给一个术语 / 数字 / 结论，列出全书哪些章节用到了它。 | `--from`／`--fuzzy`／`--threshold`／`--top`／`--scope`／`--context`／`--max-per-chapter`／`--md`／`--quiet`／`--self-test` | 不进提交门（读者手动跑） |

| 阶段 | 它在提交门里的原话 |
| --- | --- |
| 1/5 | 工具自检（字数口径 / 对账门 / 汇总数字） |
| 2/5 | 正文一致性校验 |
| 3/5 | 文档数字对账（PLAN / README / COVERAGE / LEDGER 逐节表与章标题字数 / PROJECT 字数 vs 实测；另报逐节表「事前估」列的欠账） |
| 3b/5 | 汇总数字对账（台账篇级进度 / PLAN 看板与文首 / README / COVERAGE） |
| 4/5 | 可运行树一致性（正文代码块 ↔ zhizhou-v3/ · v4/ · v5/） |
| 4b/5 | 题库索引对账（第 10 篇：专题／题数／考点数／归属） |
| 4c/5 | 后端题库的岗位视角索引（第 10 篇：板块／处置／难度／题面关键词） |
| 4d/5 | 移动端两份题库的索引（第 10 篇：地形图／处置／素材可用性／两列反向索引） |
| 4e/5 | 模拟面试与复盘（第 10 篇：时间账／追问穿透／评分／失败模式） |
| 4f/5 | 全书索引（术语 → 章节 / 树与门脚本 → 章节 / 小节目录） |
| 4g/5 | 通读普查（体例形状 / 常见坑条数，与 REVISIT.md 逐行比） |
| 4h/5 | 附录（六棵树速查 / 门脚本速查 / 总量与复算入口） |
| 5/5 | REFERENCES.md 有改动 → 联网校验全部链接／链接清单自检（离线） |

## 附录 C　全书的总量，与它们的复算入口

这一列不是「相信我们」，是**你自己能重算**：每条命令都会把那一行印出来。

| 量 | 值 | 怎么复算 |
| --- | --- | --- |
| 正文篇章 | 69 / 69 章（10 篇） | `python tools/totals.py --check`（那一行印的就是这个比值） |
| 正文有效字 | 852,559 | `python tools/totals.py --check`（同一行，`852,559 字`） |
| 可运行树 | 6 棵、1,027 条用例（v3 150 ／ v4 84 ／ v5 178 ／ v6 87 ／ v7 185 ／ v8 343） | `python tools/check_runnable.py` |
| 术语词条 | 365 条 | `python tools/index_book.py --check` |
| 练习 | 301 条（基础 113／进阶 105／挑战 83） | `python tools/appendix.py --check`（本附录自己算的，口径见 `STYLE`） |
| 常见坑 | 968 条（其中 2 章用表格） | 同上 |
| 素材站点 | 20 类、100 处 | `python tools/totals.py --check`（同一行） |
| 门脚本 | 15 支（其中 12 支跑在提交门里；另 1 支是零入口的库） | `python tools/appendix.py --check`（附录 B 就是那份表） |
