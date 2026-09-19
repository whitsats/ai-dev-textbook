# 知舟 v4 · 框架版参考实现

这是**第 4 篇正文里每一段代码的真身**，与 [`zhizhou-v3/`](../zhizhou-v3/) 并列存在。
两棵树做的是**同一件事**：同一个知舟、同一套工具契约、同一批验收标准；
区别只有一个——v3 是手写的，v4 用 LangChain / LangGraph。

所以这一棵树的用途不是「替代」，而是**对照**：第 4 篇每一章都会把同一件能力的两份实现摆在一起，
回答「框架替你做了什么、把什么藏起来了、藏起来的那部分什么时候会回来找你」。

它与正文的关系由机器保证，不靠自律：

```bash
python tools/check_runnable.py     # 在仓库根目录跑：两棵树都会被校验
```

## 当前进度（按章累加）

| 章 | 交付的零件 | 顶掉 v3 的哪一块 |
| --- | --- | --- |
| 4.1 | `app/config.py`（42 行）、`app/llm.py`（78 行，模型出口与默认值诊断）、`app/history.py`（108 行，消息与裁剪与用量）、`scripts/first_app.py`（98 行）、`tests/test_first_app.py`（119 行） | `app/llm/client.py`（468 行）的传输、超时、重试；`app/agent/memory.py` 的消息与裁剪部分 |
| 4.2 | `app/prompts.py`（65 行，三个提示模板）、`app/schemas.py`（52 行，结构化输出契约）、`app/chains.py`（147 行，LCEL 链）、`scripts/prompt_chain.py`（196 行）、`tests/test_prompt_chain.py`（166 行） | `app/llm/prompts/article_summary.md` ＋ 手拼的 `render()`；`app/llm/schemas.py` 的 `json_schema_strict()` 与 `validate()` |

| 4.3 | `app/tools.py`（六份 `@tool` 定义与体积上限）、`app/middleware.py`（四条护栏）、`app/agent.py`（`create_agent` 装配 ＋ 手写循环对照）、`app/scripted.py`（能发工具调用的剧本模型）、`scripts/agent_tools.py`、`tests/test_agent_tools.py` | `app/agent/tools/zhizhou.py` 的手写 schema；`app/agent/loop.py` 的循环与审批回调；`app/agent/guardrails.py` 的四条规则 |
| 4.4 | `app/graph.py`（`PipelineState` 与归约器、三个节点、子图、`interrupt` 审批、两套 schema）、`scripts/state_graph.py`（六组机制读数 ＋ 流水线两路）、`tests/test_state_graph.py`（20 条） | `app/agent/orchestrator.py`（交接契约、预算按份切）与 `app/agent/loop.py` 里的 `while` 与终止条件 |
| 4.5 | `app/checkpoint.py`（跨进程的检查点后端、`at_checkpoint`、`history`）、`app/supervisor.py`（Supervisor ＋ 三个角色 ＋ 两种交接载体）、`scripts/persistence_multiagent.py`（五组读数）、`tests/test_persistence.py`（18 条） | 4.4 的 `InMemorySaver` 只活在进程里；本章把「停在哪一步」变成**换一个进程读得回来**的事实，并把工序链换成一个团队 |

第 4 篇到此收口：这棵树里现在有**五个离线入口**（一章一个）与 **84 条离线测试**，
全部由 `tools/check_runnable.py` 守着（正文里标了路径的每个代码块都要在这棵树里找得到）。

## 三条命令

```bash
# 1. 离线：不需要密钥、不需要网络。剧本模型替代真实服务商，**这一路是门**
python scripts/first_app.py --offline     # 4.1：模型出口、消息、裁剪、用量
python scripts/prompt_chain.py --offline   # 4.2：模板契约、链的形状、解析失败
python scripts/agent_tools.py --offline    # 4.3：工具定义、两条路径、审批两法
python scripts/state_graph.py --offline    # 4.4：归约器、上限、并行、流、schema、中断
python scripts/persistence_multiagent.py --offline   # 4.5：快照、跨进程、时间旅行、交接限额、团队

# 2. 真机：读与 v3 完全同一份 .env，所以两个版本的行为可以直接对照
set -a; source ../zhizhou-v3/.env; set +a
python scripts/first_app.py                # 四轮问答的账
python scripts/prompt_chain.py             # 四条链的词元（含并行那一条）
python scripts/state_graph.py --real       # 4.4：同一张图换成真实服务商
python scripts/persistence_multiagent.py --real      # 4.5：模型调度者（会绕圈的那一次）
```

测试用 `pytest`（本书的验收不依赖它；本机没装 pytest 时 `python tools/check_runnable.py`
会用同一批测试函数自己驱动）：

```bash
pytest -q
```

## 与 v3 共用同一套配置

`.env.example` 里的三个变量名与 v3 一字不差（`LLM_API_KEY` / `LLM_BASE_URL` / `LLM_MODEL`）。
这不是巧合，是**对照条件**：如果连配置方式都换了，比出来的差异里就混进了无关变量。

## 4.5 那一批里最值得看的两处

1. **`SqliteCheckpointer` 是手写的，而且只为实现五个方法。**
   它存在的理由就一句话：同一份 `.sqlite` 文件，**另一个进程读得回来**
   （`InMemorySaver` 读不到——`scripts/persistence_multiagent.py --offline` 的第 ② 组用真子进程量）。
   三处最贵的坑都在注释里：序列化器返回的是**二元组**、空写入会让 `commit` 抛
   「no transaction is active」、同一连接跨线程会报 `sqlite3.OperationalError: not an error`
   （而且第一次运行往往正常）。
2. **`build_team()` 里没有 `max_handoffs` 参数。** 交接限额住在**状态**里：
   它是「这一次运行」的输入，不是「这张图」的属性——同一张图才能跑两种预算的对照。
   真机上那条读数很值：模型调度者看到「要点不够」就连派了**五次**同一个角色，
   最后是限额把它按停的。

## 4.2 那一批里最值得看的两处

1. **`json_mode` 不能用来拿固定字段。** 同一句提示、同一个模型，默认策略 /
   `json_schema` / `function_calling` 都返回了校验过的 `ArticleSummary`；
   而 `json_mode` 返回了一份**完全合法但完全用不了**的 JSON（键名是中文「摘要」「标签」，
   标签从一个变四个）。它只向服务端要「合法 JSON」，不要「你要的字段名」。
2. **`include_raw=True` 把解析失败从异常变成三个字段**（`raw` / `parsed` / `parsing_error`），
   于是「模型今天把格式写坏了」能进失败分布——会抛的那种只适合当离线夹具，不适合上生产。

## 4.1 那一批里最值得看的两处

1. **`describe_defaults()` 报的是「你没写时它会是多少」**。
   `init_chat_model` 不传 `timeout` 时，框架层是 `None`，**实际生效**的是下游 `openai` SDK 的
   600 秒读超时与 2 次重试（本机实测 `openai` 2.36.0）。所以这一棵树显式把边界改成
   30 秒 / 2 次，并把两个形态并列打印出来——**框架有默认值，不等于你有边界**。
2. **`ChatHistory._kept()` 是纯函数**。
   `dropped` 与 `to_messages()` 都走它；如果计数写在它里面，那么「打印一次读数」就会改变读数。

## 与 `zhizhou-v3/` 的分界

- 第 3 篇的正文与树**不出现任何框架依赖**（`PROJECT.md` 第一节的硬约定）；本树反过来，
  不依赖 v3 的内部实现，只共用 `.env` 与工具契约；
- 两棵树都受 `tools/check_runnable.py` 约束，但**各自的离线入口不同**
  （v3 是 `demo.py --offline`，本树是 `scripts/first_app.py --offline`），
  这一点写在工具的 `SPECS` 表里，不靠读者记；
- v3 是**完整服务**（有 FastAPI 端点、数据库迁移、护栏与观测）；本树当前只有模型出口与消息层，
  端点与装配要等第 4 篇后几章跟进——**不要拿现在的 v4 去比「功能完整性」，它比的是同一件事的写法**。
