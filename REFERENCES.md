# 官方文档出处（REFERENCES.md）

> 本教材的结论以**官方文档**为准，素材库只作参考与经验来源。
> 全部链接可通过 `python tools/check_refs.py` 批量校验。
> **访问日期：2026-09-11**（链接会迁移，正文引用时必须写明版本与访问日期）

---

## 一、引用规范

1. **优先级**：官方文档 ＞ 规范/RFC ＞ 同行评议论文（arXiv）＞ 厂商博客 ＞ 社区文章。
   社区文章（含素材库里的 PDF）只能作为"经验与踩坑"来源，**不得作为技术结论的依据**。
2. **必须可校验**：正文「延伸阅读」列出的每个链接都要能通过 `tools/check_refs.py`。
3. **必须带版本**：涉及 API 的段落要写明所用版本，例如
   `Python 3.11+`、`FastAPI 0.x`、`LangChain v1`、`MCP 规范 2026-07-28`。
4. **不得引用无法追溯的材料**：素材库中部分资料自带"仅供购买者学习、禁止传播"声明，
   只能在正文里转述其**经验性结论**，且不得复制原文。
5. **链接失效的处理**：发现 404 或跳转到新域名时，先更新本文件，再同步受影响章节。

### 「延伸阅读」小节的固定格式

```markdown
## 延伸阅读

**官方文档**（本章结论的权威依据）
- FastAPI · Dependencies — https://fastapi.tiangolo.com/tutorial/dependencies/ ｜ 本章依赖注入部分据此重写
- Pydantic · Models — https://pydantic.dev/docs/validation/latest/concepts/models/ ｜ 校验器与嵌套模型

**规范 / 论文**（有则写，无则省略）
- ReAct: Synergizing Reasoning and Acting in Language Models — https://arxiv.org/abs/2210.03629

**素材溯源**（保留可追溯性，便于回查原始资料）
- `sources/01-编程地基/FastAPI基础学习/16FastAPI的依赖注入/FastAPI的依赖注入.md`
```

---

## 二、时效警告：为什么必须以官方文档为准

审计素材时发现，几处关键技术在近两年发生了**破坏性变更**，素材里教的写法已经过时：

| 主题 | 素材里的写法 | 现状 | 权威出处 |
| --- | --- | --- | --- |
| LangChain | 旧版链式 API（`LLMChain` 等） | **LangChain v1** 重构了 `langchain` 命名空间，只保留 Agent 基础构件，旧功能移到 `langchain-classic` | [LangChain v1 新特性](https://docs.langchain.com/oss/python/releases/langchain-v1) |
| OpenAI | Assistants API | **Assistants API 已于 2026-08-26 关停**，迁移到 Responses API + Conversations API | [迁移指南](https://developers.openai.com/api/docs/guides/migrate-to-responses) |
| Claude | `docs.anthropic.com` | 文档已迁至 `platform.claude.com`（API）与 `code.claude.com`（Claude Code） | [Claude 平台文档](https://platform.claude.com/docs/en/home) |
| Claude Code SDK | `Claude Code SDK` | 已更名为 **Claude Agent SDK**，Python/TypeScript 双支持 | [Agent SDK 概览](https://code.claude.com/docs/en/agent-sdk/overview) |
| MCP | 通用描述 | 规范**按日期版本化**（如 `2026-07-28`），能力与授权模型逐版演进 | [MCP 规范](https://modelcontextprotocol.io/specification/) |
| AI 前端 | 手写 fetch + SSE | Vercel **AI SDK 7**（2026-06）提供了 Agent 运行时与 UI 层 | [AI SDK 文档](https://ai-sdk.dev/docs/introduction) |
| Pydantic 文档域 | `docs.pydantic.dev` | 已迁至 **`pydantic.dev/docs`**，且校验库拆出独立文档树 | [Pydantic 文档](https://pydantic.dev/docs/) |
| Starlette 文档域 | `www.starlette.io` | 已迁至 **`starlette.dev`**（旧域在当前网络下 TLS 校验不通过） | [Starlette Responses](https://starlette.dev/responses/) |

> 这六条正是"为什么不能直接整理素材"的最硬理由。正文每章都要回到官方文档核对。

---

## 三、按篇的官方出处

### 第 0 篇 · 导论

| 用途 | 官方出处 | 链接 |
| --- | --- | --- |
| 岗位职责与能力要求（0.1 章） | Anthropic · Careers | https://www.anthropic.com/careers |
| 模型能力边界（0.1 章） | Claude · Models 概览 | https://platform.claude.com/docs/en/about-claude/models/overview |
| 作品展示与仓库规范（0.1、0.2 章） | GitHub 文档 | https://docs.github.com/ |
| Python 学习边界（0.2 章） | Python 3 官方教程 | https://docs.python.org/3/tutorial/ |
| FastAPI 学习边界（0.2 章） | FastAPI · Tutorial | https://fastapi.tiangolo.com/tutorial/ |
| 虚拟环境（0.3 章） | Python 3 · venv | https://docs.python.org/3/library/venv.html |
| 依赖管理（0.3 章） | Astral · uv | https://docs.astral.sh/uv/ |
| API Key 与首次调用（0.3 章） | Claude · API 概览 ／ OpenAI · API 文档 | https://platform.claude.com/docs/en/api/overview |

### 第 1 篇 · 编程地基（Python 与 FastAPI 后端工程）

| 用途 | 官方出处 | 链接 |
| --- | --- | --- |
| Python 语法、标准库、类型注解 | Python 3 官方文档 | https://docs.python.org/3/ |
| 语法学习边界（1.2 章） | Python 3 · 官方教程 | https://docs.python.org/3/tutorial/ |
| 内置类型与字符串方法（1.2、1.3 章） | Python 3 · 内置类型 | https://docs.python.org/3/library/stdtypes.html |
| 内置函数（1.2、1.3 章） | Python 3 · 内置函数 | https://docs.python.org/3/library/functions.html |
| 数据结构与推导式（1.3 章） | Python 3 · 教程 · 数据结构 | https://docs.python.org/3/tutorial/datastructures.html |
| 函数定义与参数规则（1.4 章） | Python 3 · 教程 · 函数定义 | https://docs.python.org/3/tutorial/controlflow.html |
| 装饰器与 `wraps` / `lru_cache`（1.4 章） | Python 3 · functools 模块 | https://docs.python.org/3/library/functools.html |
| 迭代器协议与生成器（1.4、5.4 章）；魔术方法全表（1.5.11 章） | Python 3 · 数据模型 | https://docs.python.org/3/reference/datamodel.html |
| 类、继承与方法查找（1.5 章） | Python 3 · 教程 · 类 | https://docs.python.org/3/tutorial/classes.html |
| 抽象基类（1.5 章） | Python 3 · abc 模块 | https://docs.python.org/3/library/abc.html |
| 数据类（1.5、1.5.12 章） | Python 3 · dataclasses 模块 | https://docs.python.org/3/library/dataclasses.html |
| 结构化类型 Protocol（1.5 章） | Python 3 · typing 模块 | https://docs.python.org/3/library/typing.html |
| 错误与异常（1.6 章） | Python 3 · 教程 · 错误和异常 | https://docs.python.org/3/tutorial/errors.html |
| 文件读写（1.6 章） | Python 3 · 教程 · 输入与输出 | https://docs.python.org/3/tutorial/inputoutput.html |
| 日志（1.6、7.2 章） | Python 3 · logging 模块 | https://docs.python.org/3/library/logging.html |
| 日志最佳实践（1.6 章） | Python 3 · Logging HOWTO | https://docs.python.org/3/howto/logging.html |
| JSON 读写（1.6 章） | Python 3 · json 模块 | https://docs.python.org/3/library/json.html |
| 路径与文件系统（1.6 章） | Python 3 · pathlib 模块 | https://docs.python.org/3/library/pathlib.html |
| 导入机制（1.6 章） | Python 3 · import 系统 | https://docs.python.org/3/reference/import.html |
| 线程与锁（1.7 章） | Python 3 · threading 模块 | https://docs.python.org/3/library/threading.html |
| 进程与多核（1.7 章） | Python 3 · multiprocessing 模块 | https://docs.python.org/3/library/multiprocessing.html |
| 线程池与进程池（1.7 章） | Python 3 · concurrent.futures | https://docs.python.org/3/library/concurrent.futures.html |
| 协程与任务（1.7、5.7 章） | Python 3 · asyncio 任务与协程 | https://docs.python.org/3/library/asyncio-task.html |
| GIL 定义（1.7 章） | Python 3 · 术语表 · GIL | https://docs.python.org/3/glossary.html |
| 异步路由与并发模型（1.7、1.9 章） | FastAPI · Concurrency and async | https://fastapi.tiangolo.com/async/ |
| 后台任务（1.7 章） | FastAPI · Background Tasks | https://fastapi.tiangolo.com/tutorial/background-tasks/ |
| Counter / defaultdict（1.3、7.2 章） | Python 3 · collections 模块 | https://docs.python.org/3/library/collections.html |
| 异步编程（1.7 章） | Python 官方文档 · asyncio | https://docs.python.org/3/library/asyncio.html |
| 代码风格（全篇） | PEP 8 | https://peps.python.org/pep-0008/ |
| Web 框架（1.9–1.15 章） | FastAPI 官方文档 | https://fastapi.tiangolo.com/ |
| 应用元数据与文档地址（1.9 章） | FastAPI · Metadata and Docs URLs | https://fastapi.tiangolo.com/tutorial/metadata/ |
| 参数声明与 `Annotated`（1.9 章） | FastAPI · Path Parameters | https://fastapi.tiangolo.com/tutorial/path-params/ |
| 路径参数与数值约束（1.9 章） | FastAPI · Path Parameters and Numeric Validations | https://fastapi.tiangolo.com/tutorial/path-params-numeric-validations/ |
| 查询参数与字符串约束（1.9 章） | FastAPI · Query Parameters and String Validations | https://fastapi.tiangolo.com/tutorial/query-params-str-validations/ |
| 请求体基础（1.9 章） | FastAPI · Request Body | https://fastapi.tiangolo.com/tutorial/body/ |
| 请求体多参数与 `embed`（1.9 章） | FastAPI · Body - Multiple Parameters | https://fastapi.tiangolo.com/tutorial/body-multiple-params/ |
| 请求头参数（1.9 章） | FastAPI · Header Parameters | https://fastapi.tiangolo.com/tutorial/header-params/ |
| Cookie 参数（1.9 章） | FastAPI · Cookie Parameters | https://fastapi.tiangolo.com/tutorial/cookie-params/ |
| 表单数据（1.15 章） | FastAPI · Form Data | https://fastapi.tiangolo.com/tutorial/request-forms/ |
| 文件上传（1.15 章） | FastAPI · Request Files | https://fastapi.tiangolo.com/tutorial/request-files/ |
| 响应模型与返回类型（1.9 章） | FastAPI · Response Model - Return Type | https://fastapi.tiangolo.com/tutorial/response-model/ |
| 响应状态码（1.9 章） | FastAPI · Response Status Code | https://fastapi.tiangolo.com/tutorial/response-status-code/ |
| 自定义响应类（1.9、1.14 章） | FastAPI · Custom Response | https://fastapi.tiangolo.com/advanced/custom-response/ |
| 错误处理与异常处理器（1.14 章） | FastAPI · Handling Errors | https://fastapi.tiangolo.com/tutorial/handling-errors/ |
| 多文件应用与 `APIRouter`（1.9、1.15 章） | FastAPI · Bigger Applications | https://fastapi.tiangolo.com/tutorial/bigger-applications/ |
| 配置与环境变量（1.9 章） | FastAPI · Settings and Environment Variables | https://fastapi.tiangolo.com/advanced/settings/ |
| `BaseSettings` 与 `.env`（1.9 章） | Pydantic · Settings 管理 | https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/ |
| `UploadFile` 与 `FileResponse`（1.9、1.15 章） | Starlette · Responses | https://starlette.dev/responses/ |
| HTTP 概览、方法、状态码（1.8 章） | MDN · HTTP | https://developer.mozilla.org/en-US/docs/Web/HTTP |
| HTTP 语义规范（1.8 章） | RFC 9110 · HTTP Semantics | https://www.rfc-editor.org/rfc/rfc9110.html |
| Cookie 与 Session（1.8、1.13 章） | MDN · HTTP Cookies | https://developer.mozilla.org/en-US/docs/Web/HTTP/Cookies |
| 跨域与 CORS（1.8、8.3 章） | MDN · CORS | https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS |
| TLS 与证书（1.8 章） | MDN · Transport Layer Security | https://developer.mozilla.org/en-US/docs/Web/Security/Transport_Layer_Security |
| 最小 HTTP 服务端示例（1.8 章） | Python 3 · http.server | https://docs.python.org/3/library/http.server.html |
| 版本要求与最新变更（1.1 章） | FastAPI · GitHub 仓库 | https://github.com/fastapi/fastapi |
| 依赖注入基础（1.11 章） | FastAPI · Dependencies | https://fastapi.tiangolo.com/tutorial/dependencies/ |
| `yield` 依赖与资源清理（1.11 章） | FastAPI · Dependencies with yield | https://fastapi.tiangolo.com/tutorial/dependencies/dependencies-with-yield/ |
| 测试与依赖覆盖（1.11 章） | FastAPI · Testing Dependencies with Overrides | https://fastapi.tiangolo.com/advanced/testing-dependencies/ |
| 中间件与执行顺序（1.11 章） | FastAPI · Middleware | https://fastapi.tiangolo.com/tutorial/middleware/ |
| 高级中间件与纯 ASGI 写法（1.11 章） | FastAPI · Advanced Middleware | https://fastapi.tiangolo.com/advanced/middleware/ |
| CORS 中间件配置（1.8、1.11 章） | FastAPI · CORS | https://fastapi.tiangolo.com/tutorial/cors/ |
| 内置中间件与已知限制（1.11 章） | Starlette · Middleware | https://starlette.dev/middleware/ |
| `request.state` 与 `app.state`（1.11 章） | Starlette · Requests | https://starlette.dev/requests/ |
| 安全与 JWT（1.13 章） | FastAPI · Security | https://fastapi.tiangolo.com/tutorial/security/ |
| 数据校验（1.10 章） | Pydantic 官方文档 | https://pydantic.dev/docs/ |
| Pydantic 模型与校验器 | Pydantic · Models | https://pydantic.dev/docs/validation/latest/concepts/models/ |
| 字段约束与 `default_factory`（1.10 章） | Pydantic · Fields | https://pydantic.dev/docs/validation/latest/concepts/fields/ |
| 校验器与 `mode` 语义（1.10 章） | Pydantic · Validators | https://pydantic.dev/docs/validation/latest/concepts/validators/ |
| `ConfigDict` 配置项与继承（1.10 章） | Pydantic · Configuration | https://pydantic.dev/docs/validation/latest/concepts/config/ |
| 序列化与 `field_serializer`（1.10 章） | Pydantic · Serialization | https://pydantic.dev/docs/validation/latest/concepts/serialization/ |
| 别名三级开关（1.10 章） | Pydantic · Aliases | https://pydantic.dev/docs/validation/latest/concepts/alias/ |
| 常用类型与 `EmailStr` 依赖（1.10 章） | Pydantic · Types | https://pydantic.dev/docs/validation/latest/concepts/types/ |
| 可辨识联合（1.10 章） | Pydantic · Unions | https://pydantic.dev/docs/validation/latest/concepts/unions/ |
| 计算字段（1.10 章） | Pydantic · Computed Fields | https://pydantic.dev/docs/validation/latest/concepts/computed_fields/ |
| 模型与 OpenAPI 契约（1.10 章） | Pydantic · JSON Schema | https://pydantic.dev/docs/validation/latest/concepts/json_schema/ |
| ORM 模型定义（1.12 章） | SQLAlchemy · ORM Quick Start | https://docs.sqlalchemy.org/en/20/orm/quickstart.html |
| 异步引擎与会话（1.12 章） | SQLAlchemy · Asyncio Extension | https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html |
| 会话与事务边界（1.12 章） | SQLAlchemy · Session Basics | https://docs.sqlalchemy.org/en/20/orm/session_basics.html |
| `expire_on_commit` 参数（1.12 章） | SQLAlchemy · Session API | https://docs.sqlalchemy.org/en/20/orm/session_api.html |
| 查询与结果提取（1.12 章） | SQLAlchemy · Querying Guide | https://docs.sqlalchemy.org/en/20/orm/queryguide/index.html |
| N+1 与预加载（1.12 章） | SQLAlchemy · Relationship Loading | https://docs.sqlalchemy.org/en/20/orm/queryguide/relationships.html |
| 连接池参数（1.12 章） | SQLAlchemy · Connection Pooling | https://docs.sqlalchemy.org/en/20/core/pooling.html |
| 数据库迁移（1.12 章） | Alembic · Tutorial | https://alembic.sqlalchemy.org/en/latest/tutorial.html |
| FastAPI 与 SQLAlchemy 集成（1.12 章） | FastAPI · SQL Databases | https://fastapi.tiangolo.com/tutorial/sql-databases/ |
| Redis 异步客户端（1.12 章） | Redis · Python client | https://redis.io/docs/latest/develop/clients/redis-py/ |
| Redis 数据结构（1.12 章） | Redis · Data types | https://redis.io/docs/latest/develop/data-types/ |
| Redis 过期与淘汰（1.12 章） | Redis · EXPIRE 命令 | https://redis.io/docs/latest/commands/expire/ |
| 单元测试（1.14 章） | pytest 官方文档 | https://docs.pytest.org/ |
| 依赖与虚拟环境（1.1 章） | uv 官方文档 | https://docs.astral.sh/uv/ |
| 版本控制（1.1 章） | Git 官方文档 | https://git-scm.com/doc |
| HTTP 语义（1.8 章） | RFC 9110 · HTTP Semantics | https://www.rfc-editor.org/rfc/rfc9110.html |
| JWT 规范（1.13 章） | RFC 7519 · JWT | https://www.rfc-editor.org/rfc/rfc7519.html |
| OAuth 2.0 规范（1.13 章） | RFC 6749 · OAuth 2.0 | https://www.rfc-editor.org/rfc/rfc6749.html |
| 异步任务与队列（1.7 章） | Celery 官方文档 | https://docs.celeryq.dev/ |

### 第 2 篇 · AI 时代的开发方式

| 用途 | 官方出处 | 链接 |
| --- | --- | --- |
| Claude Code 使用与工程化（2.2、2.5 章） | Claude Code 官方文档 | https://code.claude.com/docs |
| 子代理、Hooks、权限、Skills | Claude Code · Agent SDK 概览 | https://code.claude.com/docs/en/agent-sdk/overview |
| 用代码驱动 Agent（2.6 章） | Claude Agent SDK · Python 参考 | https://code.claude.com/docs/en/agent-sdk/python |
| Claude API 与 Messages 格式 | Claude 平台文档 | https://platform.claude.com/docs/en/home |
| API 鉴权、限流、SDK（2.1 章） | Claude · API 概览 | https://platform.claude.com/docs/en/api/overview |
| 工具调用与函数编排 | Claude · Tool use | https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview |
| OpenAI 侧能力与 Responses API | OpenAI API 文档 | https://developers.openai.com/api/docs |
| Assistants → Responses 迁移 | OpenAI · 迁移指南 | https://developers.openai.com/api/docs/guides/migrate-to-responses |
| 版本变更追踪（2.1 章） | OpenAI · Changelog | https://developers.openai.com/api/docs/changelog |
| MCP 协议与服务器（2.5 章） | MCP 官方文档 | https://modelcontextprotocol.io/ |
| MCP 入门 | MCP · Getting Started | https://modelcontextprotocol.io/docs/2026-07-28/getting-started/intro |
| MCP 规范与授权模型 | MCP · Specification | https://modelcontextprotocol.io/specification/ |
| MCP 官方 SDK | MCP · SDKs | https://modelcontextprotocol.io/docs/2026-07-28/sdk |
| GitHub Copilot 对照（2.3 章） | GitHub · Copilot 文档 | https://docs.github.com/en/copilot |

### 第 3 篇 · 大模型与 Agent 原理

| 用途 | 官方出处 | 链接 |
| --- | --- | --- |
| 模型能力边界、上下文长度、定价（3.1 章） | Claude · Models 概览 | https://platform.claude.com/docs/en/about-claude/models/overview |
| 结构化输出与工具调用（3.5 章） | OpenAI · API 文档 | https://developers.openai.com/api/docs |
| 工具调用协议（3.5 章） | Claude · Tool use | https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview |
| 提示注入与防护（3.8 章） | OWASP · LLM Top 10 | https://genai.owasp.org/llm-top-10/ |
| 风险治理框架（3.8 章） | NIST · AI Risk Management Framework | https://www.nist.gov/itl/ai-risk-management-framework |
| 追踪与指标（3.9 章） | OpenTelemetry 官方文档 | https://opentelemetry.io/docs/ |
| LLM 应用可观测性（3.9 章） | Langfuse 官方文档 | https://langfuse.com/docs |
| 评估方法与指标（3.9 章） | Ragas 官方文档 | https://docs.ragas.io/en/stable/ |

### 第 4 篇 · AI 应用开发框架

| 用途 | 官方出处 | 链接 |
| --- | --- | --- |
| 文档总站（全篇） | LangChain 官方文档 | https://docs.langchain.com/ |
| LangChain Python 概览（4.1 章） | LangChain · Overview | https://docs.langchain.com/oss/python/langchain/overview |
| **v1 命名空间变更（必读）** | LangChain v1 新特性 | https://docs.langchain.com/oss/python/releases/langchain-v1 |
| 集成与模型提供方（4.2 章） | LangChain · Integrations | https://docs.langchain.com/oss/python/integrations/providers/overview |
| LangGraph 与状态编排（4.4 章） | LangGraph · Overview | https://docs.langchain.com/oss/python/langgraph/overview |
| 图 API（节点/边/状态）（4.4 章） | LangGraph · Graph API | https://docs.langchain.com/oss/python/langgraph/graph-api |
| API 参考（全篇） | LangChain / LangGraph Reference | https://reference.langchain.com/python/ |

### 第 5 篇 · RAG 与生产级系统

| 用途 | 官方出处 | 链接 |
| --- | --- | --- |
| 向量数据库（5.3、5.7 章） | Milvus 官方文档 | https://milvus.io/docs |
| Milvus 快速开始 | Milvus · Quickstart | https://milvus.io/docs/quickstart.md |
| Milvus 多租户与库表设计（5.7 章） | Milvus · Database | https://milvus.io/docs/manage_databases.md |
| 评估框架与指标（5.6 章） | Ragas 官方文档 | https://docs.ragas.io/en/stable/ |
| 评估入门实操 | Ragas · Evaluate a simple LLM app | https://docs.ragas.io/en/latest/getstarted/evals/ |
| 向量化与嵌入模型 | Hugging Face · Sentence Transformers | https://sbert.net/ |
| 检索评测基准（5.6 章） | BEIR 基准 | https://github.com/beir-cellar/beir |

### 第 6 篇 · 模型接入与成本工程（新增篇）

| 用途 | 官方出处 | 链接 |
| --- | --- | --- |
| 多厂商统一调用（6.2、6.3 章） | LiteLLM 官方文档 | https://docs.litellm.ai/ |
| Claude API 与定价（6.1 章） | Claude · API 概览 | https://platform.claude.com/docs/en/api/overview |
| OpenAI Responses API（6.2 章） | OpenAI · API 文档 | https://developers.openai.com/api/docs |
| 数据留存与隐私（6.4 章） | OpenAI · 数据控制 | https://developers.openai.com/api/docs/guides/your-data |
| 自建推理服务（6.3 章） | vLLM 官方文档 | https://docs.vllm.ai/ |
| 本地模型运行（6.3 章） | Ollama 官方 | https://ollama.com/ |

### 第 7 篇 · AI 应用工程化（新增篇）

| 用途 | 官方出处 | 链接 |
| --- | --- | --- |
| 评测流水线与回归（7.1 章） | Ragas 官方文档 | https://docs.ragas.io/en/stable/ |
| 追踪与成本看板（7.2 章） | Langfuse 官方文档 | https://langfuse.com/docs |
| 追踪标准与埋点（7.2 章） | OpenTelemetry · GenAI 语义约定 | https://opentelemetry.io/docs/specs/semconv/gen-ai/ |
| 提示注入与不安全的输出处理（7.4 章） | OWASP · LLM Top 10 | https://genai.owasp.org/llm-top-10/ |
| 工具权限与授权（7.4 章） | MCP · 授权规范 | https://modelcontextprotocol.io/specification/ |
| 数据合规与留存（7.5 章） | OpenAI · 数据控制 | https://developers.openai.com/api/docs/guides/your-data |
| 内部威胁与红队测试（7.4 章） | NIST · AI RMF | https://www.nist.gov/itl/ai-risk-management-framework |

### 第 8 篇 · 交付与产品化（新增篇）

| 用途 | 官方出处 | 链接 |
| --- | --- | --- |
| 容器化与部署（8.1 章） | Docker 官方文档 | https://docs.docker.com/ |
| 镜像与编排排错 | Docker · Compose | https://docs.docker.com/compose/ |
| CI/CD 与发布（8.2 章） | GitHub Actions 文档 | https://docs.github.com/en/actions |
| 前端流式对话（8.3 章） | Vercel AI SDK 文档 | https://ai-sdk.dev/docs/introduction |
| 前端框架（8.3 章） | Next.js 官方文档 | https://nextjs.org/docs |
| 鉴权与多租户（8.4 章） | FastAPI · Security | https://fastapi.tiangolo.com/tutorial/security/ |
| 可观测性与告警（8.5 章） | OpenTelemetry 官方文档 | https://opentelemetry.io/docs/ |

### 第 9 篇 · 进阶方向（新增篇，可选）

| 用途 | 官方出处 | 链接 |
| --- | --- | --- |
| 本地与批量推理（9.1 章） | vLLM 官方文档 | https://docs.vllm.ai/ |
| 本地模型与量化（9.1 章） | Ollama 官方 | https://ollama.com/ |
| LoRA/QLoRA 微调（9.2 章） | Hugging Face PEFT | https://huggingface.co/docs/peft |
| SFT / DPO 训练（9.2 章） | Hugging Face TRL | https://huggingface.co/docs/trl |
| 数据集与模型托管（9.2 章） | Hugging Face 文档 | https://huggingface.co/docs |
| 语音与实时对话（9.3 章） | OpenAI · API 文档 | https://developers.openai.com/api/docs |

### 第 10 篇 · 求职冲刺

| 用途 | 官方出处 | 链接 |
| --- | --- | --- |
| 岗位能力要求与 JD 对照（10.1 章） | 各公司招聘页与 JD（引用时逐个标注） | https://www.anthropic.com/careers |
| 项目演示与开源仓库规范（10.2 章） | GitHub 文档 | https://docs.github.com/ |
| 系统设计与上下文管理（10.3 章） | Claude · 平台文档 | https://platform.claude.com/docs/en/home |
| 可观测性与成本追问（10.3 章） | OpenTelemetry 官方文档 | https://opentelemetry.io/docs/ |

---

## 四、经典论文（理论依据）

原理篇不能只引文档，关键机制要回到原始论文。

| 主题 | 论文 | 链接 |
| --- | --- | --- |
| 大模型架构基础（3.1 章） | Attention Is All You Need (2017) | https://arxiv.org/abs/1706.03762 |
| 指令微调与对齐（3.1 章） | Training language models to follow instructions (InstructGPT, 2022) | https://arxiv.org/abs/2203.02155 |
| 思维链（3.2 章） | Chain-of-Thought Prompting Elicits Reasoning in LLMs (2022) | https://arxiv.org/abs/2201.11903 |
| ReAct：推理与行动交替（3.4、3.5 章） | ReAct: Synergizing Reasoning and Acting in Language Models (2022) | https://arxiv.org/abs/2210.03629 |
| 工具学习（3.5 章） | Toolformer (2023) | https://arxiv.org/abs/2302.04761 |
| 自我反思与迭代（3.4 章） | Reflexion: Language Agents with Verbal Reinforcement Learning (2023) | https://arxiv.org/abs/2303.11366 |
| RAG 原始论文（5.1 章） | Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks (2020) | https://arxiv.org/abs/2005.11401 |
| 长上下文与位置敏感（5.2、5.4 章） | Lost in the Middle (2023) | https://arxiv.org/abs/2307.03172 |
| 自反思检索（5.4 章） | Self-RAG (2023) | https://arxiv.org/abs/2310.11511 |
| RAG 自动评估（5.6 章） | Ragas: Automated Evaluation of Retrieval Augmented Generation (2023) | https://arxiv.org/abs/2309.15217 |
| LoRA 低秩微调（9.2 章） | LoRA: Low-Rank Adaptation of Large Language Models (2021) | https://arxiv.org/abs/2106.09685 |
| 量化微调（9.2 章） | QLoRA: Efficient Finetuning of Quantized LLMs (2023) | https://arxiv.org/abs/2305.14314 |
| 偏好对齐（9.2 章） | Direct Preference Optimization (2023) | https://arxiv.org/abs/2305.18290 |

---

## 五、维护方式

```bash
# 校验全部链接（并发 HEAD 请求，报告失效与跳转）
python tools/check_refs.py

# 只看失效项
python tools/check_refs.py --only-broken

# 离线：只解析出链接清单，不发请求
python tools/check_refs.py --offline
```

链接大面积失效（或报告域名跳转）时，先更新本文件，再据此修订受影响章节——
本文件是全书技术准确性的**单一事实来源**。
