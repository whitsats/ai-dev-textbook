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
| 表单与文件混合上传（1.15 章） | FastAPI · Request Files and Form | https://fastapi.tiangolo.com/tutorial/request-forms-and-files/ |
| 静态文件挂载（1.15 章） | FastAPI · Static Files | https://fastapi.tiangolo.com/tutorial/static-files/ |
| 静态挂载实现与目录校验（1.15 章） | Starlette · Static Files | https://starlette.dev/staticfiles/ |
| 异步路由与阻塞调用（1.7、1.15 章） | FastAPI · Concurrency and async / await | https://fastapi.tiangolo.com/async/ |
| 文件名唯一化（1.15 章） | Python 3 · uuid | https://docs.python.org/3/library/uuid.html |
| 内存/磁盘自动切换的临时文件（1.15 章） | Python 3 · tempfile | https://docs.python.org/3/library/tempfile.html |
| 图片缩放与格式转换（1.15 章） | Pillow · Image 模块 | https://pillow.readthedocs.io/en/stable/reference/Image.html |
| 响应模型与返回类型（1.9 章） | FastAPI · Response Model - Return Type | https://fastapi.tiangolo.com/tutorial/response-model/ |
| 响应状态码（1.9 章） | FastAPI · Response Status Code | https://fastapi.tiangolo.com/tutorial/response-status-code/ |
| 自定义响应类（1.9、1.14 章） | FastAPI · Custom Response | https://fastapi.tiangolo.com/advanced/custom-response/ |
| 错误处理与异常处理器（1.14 章） | FastAPI · Handling Errors | https://fastapi.tiangolo.com/tutorial/handling-errors/ |
| 应用生命周期与 `lifespan`（1.12、1.14 章） | FastAPI · Lifespan Events | https://fastapi.tiangolo.com/advanced/events/ |
| `TestClient` 与 `raise_server_exceptions`（1.14 章） | FastAPI · Testing | https://fastapi.tiangolo.com/tutorial/testing/ |
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
| JWT 生成与口令哈希（1.13 章） | FastAPI · OAuth2 with JWT | https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/ |
| 作用域与权限声明（1.13 章） | FastAPI · OAuth2 scopes | https://fastapi.tiangolo.com/advanced/security/oauth2-scopes/ |
| `get_current_user` 依赖写法（1.13 章） | FastAPI · Get Current User | https://fastapi.tiangolo.com/tutorial/security/get-current-user/ |
| 表单登录与 `OAuth2PasswordRequestForm`（1.13 章） | FastAPI · Simple OAuth2 | https://fastapi.tiangolo.com/tutorial/security/simple-oauth2/ |
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
| fixture 与作用域（1.14 章） | pytest · Fixtures | https://docs.pytest.org/en/stable/how-to/fixtures.html |
| 标准库测试框架（1.14 章） | Python 3 · unittest | https://docs.python.org/3/library/unittest.html |
| 替身与 `assert_not_called`（1.14 章） | Python 3 · unittest.mock | https://docs.python.org/3/library/unittest.mock.html |
| 日志轮转 handler（1.14 章） | Python 3 · logging.handlers | https://docs.python.org/3/library/logging.handlers.html |
| 用配置管理日志（1.14 章） | Python 3 · logging.config | https://docs.python.org/3/library/logging.config.html |
| 依赖与虚拟环境（1.1 章） | uv 官方文档 | https://docs.astral.sh/uv/ |
| 版本控制（1.1 章） | Git 官方文档 | https://git-scm.com/doc |
| 工作树并行隔离（2.2 章） | Git · git-worktree | https://git-scm.com/docs/git-worktree |
| 补丁应用与退出码语义（2.3 章） | Git · git-apply | https://git-scm.com/docs/git-apply |
| HTTP 语义（1.8 章） | RFC 9110 · HTTP Semantics | https://www.rfc-editor.org/rfc/rfc9110.html |
| JWT 规范（1.13 章） | RFC 7519 · JWT | https://www.rfc-editor.org/rfc/rfc7519.html |
| OAuth 2.0 规范（1.13 章） | RFC 6749 · OAuth 2.0 | https://www.rfc-editor.org/rfc/rfc6749.html |
| Bearer 令牌用法与 401/403 语义（1.13 章） | RFC 6750 · Bearer Token Usage | https://www.rfc-editor.org/rfc/rfc6750.html |
| HMAC 密钥最短长度（1.13 章） | RFC 7518 · JSON Web Algorithms | https://www.rfc-editor.org/rfc/rfc7518.html |
| 刷新令牌轮换与重放处置（1.13 章） | RFC 9700 · OAuth 2.0 Security BCP | https://www.rfc-editor.org/rfc/rfc9700.html |
| 口令存储与工作因子（1.13 章） | OWASP · Password Storage Cheat Sheet | https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html |
| 用户认证与错误文案（1.13 章） | OWASP · Authentication Cheat Sheet | https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html |
| 对象级授权与越权（1.13 章） | OWASP · Authorization Cheat Sheet | https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html |
| JWT 库（1.13 章） | PyJWT · Usage | https://pyjwt.readthedocs.io/en/stable/usage.html |
| 库版本行为变化与安全修复（1.13 章） | PyJWT · Changelog | https://pyjwt.readthedocs.io/en/stable/changelog.html |
| bcrypt 行为变更（1.13 章） | bcrypt · CHANGELOG | https://github.com/pyca/bcrypt/blob/main/CHANGELOG.rst |
| 异步任务与队列（1.7 章） | Celery 官方文档 | https://docs.celeryq.dev/ |

### 第 2 篇 · AI 时代的开发方式

| 用途 | 官方出处 | 链接 |
| --- | --- | --- |
| Claude Code 使用与工程化（2.2、2.5 章） | Claude Code 官方文档 | https://code.claude.com/docs |
| 代理循环、内置工具与执行环境（2.2 章） | Claude Code · How Claude Code works | https://code.claude.com/docs/en/how-claude-code-works |
| 权限模式全集与各模式免询问范围（2.2 章） | Claude Code · Choose a permission mode | https://code.claude.com/docs/en/permission-modes |
| Allow/Ask/Deny 规则与优先级（2.2 章） | Claude Code · Configure permissions | https://code.claude.com/docs/en/permissions |
| 沙箱 Bash 的平台要求与设置（2.2 章） | Claude Code · Configure the sandboxed Bash tool | https://code.claude.com/docs/en/sandboxing |
| 命令面与标志（2.2 章） | Claude Code · CLI reference | https://code.claude.com/docs/en/cli-reference |
| 会话恢复、命名与「不还原的配置」（2.2 章） | Claude Code · Manage sessions | https://code.claude.com/docs/en/sessions |
| 上下文窗口与 prompt caching（2.2、2.5 章） | Claude Code · Prompt caching | https://code.claude.com/docs/en/prompt-caching |
| CLAUDE.md 与自动记忆（2.2、2.5 章） | Claude Code · How Claude remembers your project | https://code.claude.com/docs/en/memory |
| 「什么时候该加什么机制」的触发表与扩展机制对照（2.5 章） | Claude Code · Extend Claude Code | https://code.claude.com/docs/en/features-overview |
| `.claude` 目录逐文件说明（何时读、是否提交）（2.5 章） | Claude Code · Explore the .claude directory | https://code.claude.com/docs/en/claude-directory |
| 技能正文按需加载、支持文件与动态上下文注入（2.5 章） | Claude Code · Extend Claude with skills | https://code.claude.com/docs/en/skills |
| Hooks 事件全表、三种节奏与处理器类型（2.5 章） | Claude Code · Hooks reference | https://code.claude.com/docs/en/hooks |
| MCP 接入信号、三种传输与 `.mcp.json` 的 `type` 陷阱（2.5 章） | Claude Code · Connect Claude Code to tools via MCP | https://code.claude.com/docs/en/mcp |
| 常见工作流与最佳实践（2.2 章） | Claude Code · Common workflows ／ Best practices | https://code.claude.com/docs/en/common-workflows |
| 会话隔离到 git worktree（2.2 章） | Claude Code · Run parallel sessions with worktrees | https://code.claude.com/docs/en/worktrees |
| 平台与入口对照（2.2 章） | Claude Code · Platforms and integrations | https://code.claude.com/docs/en/platforms |
| Hooks 的触发时机与进出参（2.2、2.5 章） | Claude Code · Automate actions with hooks | https://code.claude.com/docs/en/hooks-guide |
| 子代理、Hooks、权限、Skills | Claude Code · Agent SDK 概览 | https://code.claude.com/docs/en/agent-sdk/overview |
| 用代码驱动 Agent（2.6 章） | Claude Agent SDK · Python 参考 | https://code.claude.com/docs/en/agent-sdk/python |
| Claude API 与 Messages 格式 | Claude 平台文档 | https://platform.claude.com/docs/en/home |
| API 鉴权、限流、SDK（2.1 章） | Claude · API 概览 | https://platform.claude.com/docs/en/api/overview |
| 工具调用与函数编排 | Claude · Tool use | https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview |
| Codex 的沙箱与审批两层控制（2.3 章） | OpenAI · Agent approvals & security | https://learn.chatgpt.com/docs/agent-approvals-security |
| 沙箱模式与平台前置依赖（2.3 章） | OpenAI · Sandbox | https://learn.chatgpt.com/docs/sandboxing |
| Codex CLI 安装与用法（2.3 章） | OpenAI · Codex CLI | https://learn.chatgpt.com/docs/codex/cli |
| 命令与斜杠命令参考（2.3 章） | OpenAI · Command line options | https://learn.chatgpt.com/docs/developer-commands |
| 非交互运行与脚本化（2.3 章） | OpenAI · Non-interactive mode | https://learn.chatgpt.com/docs/non-interactive-mode |
| 云端任务、两阶段运行与环境（2.3 章） | OpenAI · Codex cloud | https://learn.chatgpt.com/docs/cloud |
| 云端联网控制（2.3 章） | OpenAI · Agent internet access | https://learn.chatgpt.com/docs/cloud/internet-access |
| 代码审查（2.3 章） | OpenAI · Code review | https://learn.chatgpt.com/docs/code-review |
| 自动审批复核（2.3 章） | OpenAI · Automatic approval review | https://learn.chatgpt.com/docs/sandboxing/auto-review |
| 自动复核的实现与默认策略（开源仓库，2.3 章） | Codex · guardian | https://github.com/openai/codex/tree/main/codex-rs/core/src/guardian |
| 原生 Windows 沙箱（2.3 章） | OpenAI · Windows sandbox | https://learn.chatgpt.com/docs/windows/windows-sandbox |
| AGENTS.md 项目说明（2.3、2.5 章） | OpenAI · Custom instructions with AGENTS.md | https://learn.chatgpt.com/docs/agent-configuration/agents-md |
| 命令规则 `prefix_rule`、三种决策与复合命令判定（2.5 章） | OpenAI · Rules | https://learn.chatgpt.com/docs/agent-configuration/rules |
| 技能目录/加载位置与初始列表的上下文预算（2.5 章） | OpenAI · Build skills | https://learn.chatgpt.com/docs/build-skills |
| 定时任务与事件触发的可用面（2.5 章） | OpenAI · Automations | https://learn.chatgpt.com/docs/automations |
| 本地配置入门与参考（2.3、2.5 章） | OpenAI · Config basics ／ Configuration reference | https://learn.chatgpt.com/docs/config-file/config-basic |
| OpenAI 侧能力与 Responses API | OpenAI API 文档 | https://developers.openai.com/api/docs |
| Assistants → Responses 迁移 | OpenAI · 迁移指南 | https://developers.openai.com/api/docs/guides/migrate-to-responses |
| 版本变更追踪（2.1 章） | OpenAI · Changelog | https://developers.openai.com/api/docs/changelog |
| MCP 协议与服务器（2.5 章） | MCP 官方文档 | https://modelcontextprotocol.io/ |
| MCP 入门 | MCP · Getting Started | https://modelcontextprotocol.io/docs/2026-07-28/getting-started/intro |
| MCP 规范与授权模型 | MCP · Specification | https://modelcontextprotocol.io/specification/ |
| MCP 官方 SDK | MCP · SDKs | https://modelcontextprotocol.io/docs/2026-07-28/sdk |
| GitHub Copilot 对照（2.3 章） | GitHub · Copilot 文档 | https://docs.github.com/en/copilot |
| 规则文件与 `@` 引用（2.4 章） | Cursor · Rules | https://cursor.com/docs/rules |
| 补全的多行编辑与跳转预测（2.4 章） | Cursor · Tab | https://cursor.com/help/ai-features/tab |
| 仓库级 / 路径级自定义指令（2.4 章） | GitHub · Adding repository custom instructions | https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/add-custom-instructions/add-repository-instructions |
| 斜杠命令、聊天变量与参与者（2.4 章） | GitHub · Copilot Chat cheat sheet | https://docs.github.com/en/copilot/reference/chat-cheat-sheet |
| Agent / Plan / Ask 三种模式（2.4 章） | GitHub · Asking Copilot questions in your IDE | https://docs.github.com/en/copilot/how-tos/chat-with-copilot/chat-in-ide |
| 预设命令清单与「可用命令随环境变化」（2.4 章） | Cursor · Slash commands | https://cursor.com/docs/cli/reference/slash-commands |
| 自定义命令已并入 Skills（2.4、2.5 章） | Claude Code · Extend Claude with skills | https://code.claude.com/docs/en/slash-commands |
| Vue - Official 取代 Vetur、在 Vue 3 里须禁用 Vetur（2.4 章） | Vue · Using Vue with TypeScript | https://vuejs.org/guide/typescript/overview |
| Network 面板记录什么与 Initiator（2.4 章） | Chrome DevTools · Inspect network activity | https://developer.chrome.com/docs/devtools/network/ |
| 跨域：简单请求、预检与凭证限制（2.4 章） | MDN · Cross-Origin Resource Sharing | https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/CORS |
| CORS 中间件的凭证与反射行为（2.4 章） | Starlette · Middleware | https://starlette.dev/middleware/ |
| 前端环境变量与构建模式（2.4 章） | Vite · Env Variables and Modes | https://vite.dev/guide/env-and-mode |
| 构建与产物预览（2.4 章） | Vite · Building for Production | https://vite.dev/guide/build |
| `create-vue` 脚手架与项目结构（2.4 章） | Vue · Quick Start | https://vuejs.org/guide/quick-start |
| 本机与私有网地址判定（2.3、2.4 章） | Python · ipaddress | https://docs.python.org/3/library/ipaddress.html |
| Vibe Coding 的定义与事件索引（2.4 章） | Wikipedia · Vibe coding | https://en.wikipedia.org/wiki/Vibe_coding |
| AI 生成代码的安全通过率与测试方法（2.4 章） | Veracode · 2025 GenAI Code Security Report | https://www.veracode.com/resources/analyst-reports/2025-genai-code-security-report/ |
| 语法与安全通过率的长期对比（2.4 章） | Veracode · Spring 2026 GenAI Code Security Update | https://www.veracode.com/blog/spring-2026-genai-code-security/ |
| AI 与人类 PR 的缺陷对比（2.4 章） | CodeRabbit · State of AI vs Human Code Generation | https://www.coderabbit.ai/blog/state-of-ai-vs-human-code-generation-report |
| 重构比例与重复代码（2.4 章） | GitClear · AI Assistant Code Quality Research 2025 | https://www.gitclear.com/ai_assistant_code_quality_2025_research |
| rsync 争议的维护者说明（2.4 章） | LWN · Tridgell: rsync and outrage | https://lwn.net/Articles/1076040/ |
| 开发者生产力的对照实验（2.1 章） | METR · 2025 AI 与开源开发者生产力实验 | https://metr.org/blog/2025-07-10-early-2025-ai-experienced-os-dev-study/ |
| 同一实验的 2026 更新（选择效应与重设计） | METR · 实验设计变更说明 | https://metr.org/blog/2026-02-24-uplift-update/ |
| AI 采用率、信任与交付稳定性（2.1 章） | DORA · State of AI-assisted Software Development 2025 | https://dora.dev/dora-report-2025/ |
| 上表关键数字的官方公告（2.1 章） | Google Cloud · 2025 DORA 报告发布 | https://cloud.google.com/blog/products/ai-machine-learning/announcing-the-2025-dora-report |
| 风险分类与治理口径（2.1、3.8 章） | OWASP · GenAI LLM Top 10 2026 | https://genai.owasp.org/llm-top-10/ |

| Claude Code 在 GitHub Actions 里的两种模式、App 权限与触发检查（2.6 章） | Claude Code · GitHub Actions | https://code.claude.com/docs/en/github-actions |
| Codex 的 PR 审查、`## Code Review Rules` 与 Security Review（2.6 章） | OpenAI · Review GitHub pull requests with Codex | https://learn.chatgpt.com/docs/third-party/github |
| `/review` 的四种范围与行级反馈（2.6 章） | OpenAI · Code review | https://learn.chatgpt.com/docs/code-review |
| 必需状态检查接受的状态、job 名重名与 strict/loose 口径（2.6 章） | GitHub · About protected branches | https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches |
| 「跳过但必需」的四种情形与修法（path 过滤 / 条件跳过 / 依赖失败 / merge_group）（2.6 章） | GitHub · Troubleshooting required status checks | https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/troubleshooting-required-status-checks |
| 分支保护规则的开关位置与所需权限（2.6 章） | GitHub · Managing a branch protection rule | https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/managing-a-branch-protection-rule |

### 第 3 篇 · 大模型与 Agent 原理

| 用途 | 官方出处 | 链接 |
| --- | --- | --- |
| 模型能力边界、上下文长度、定价（3.1 章） | Claude · Models 概览 | https://platform.claude.com/docs/en/about-claude/models/overview |
| 上下文窗口的构成、上下文腐烂、KV 缓存与前缀缓存的经济账（3.1 章） | Claude · Context windows | https://platform.claude.com/docs/en/build-with-claude/context-windows |
| `count_tokens` 接口、估算性质、新分词器约 +30% 词元（3.1 章） | Claude · Token counting | https://platform.claude.com/docs/en/build-with-claude/token-counting |
| 前缀缓存的命中规则、TTL 与读写价格倍数、最小可缓存长度 1,024–4,096 词元（3.1、3.3 章） | Claude · Prompt caching | https://platform.claude.com/docs/en/build-with-claude/prompt-caching |
| 采样参数在新一代模型上的取舍与 400 错误（3.1 章） | Claude · Using the Messages API | https://platform.claude.com/docs/en/build-with-claude/working-with-messages |
| `max_tokens`、`cache_control` 与取样参数的第一手定义（3.1 章） | Claude · Create a Message | https://platform.claude.com/docs/en/api/messages/create |
| 编码器对照、中日英切分差异、单 token 解码的有损性（3.1 章） | OpenAI · 使用 Tiktoken 计数 | https://developers.openai.com/cookbook/examples/how_to_count_tokens_with_tiktoken |
| 输出的非确定性、固定模型快照与建评测的建议（3.1 章） | OpenAI · Text generation | https://developers.openai.com/api/docs/guides/text |
| 金律、给动机、示例三要求与 3–5 条、XML 标签、角色、长上下文摆放、输出格式控制、提示链与自我纠错链、过度提示（3.2 章） | Claude · Prompting best practices | https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices |
| 提示工程的三件前置：成功标准、实测方式、一份初稿（3.2 章） | Claude · Prompt engineering overview | https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/overview |
| `output_config.format`、严格工具调用、受约束解码的三条保证、支持清单与 schema 限制（3.2、3.4、3.5 章） | Claude · Structured outputs | https://platform.claude.com/docs/en/build-with-claude/structured-outputs |
| 思考块的结构与 `signature`、回传的是摘要而非原始推理链、按输出计费与占用 `max_tokens`、自适应思考与 `effort`（3.2 章） | Claude · Thinking | https://platform.claude.com/docs/en/build-with-claude/thinking |
| 工作流与 Agent 的分界线、增强型大语言模型、五种工作流（含编排者–工作者与评估者–优化者）、自主 Agent 的适用判据、三条设计原则与 ACI（3.3–3.5 章） | Anthropic · Building effective agents | https://www.anthropic.com/engineering/building-effective-agents |
| 运行时原语（Agent / 交接 / 护栏 / 会话 / 追踪记录）、内置循环、护栏与人类在环（3.3、3.5 章） | OpenAI · Agents SDK 概览 | https://openai.github.io/openai-agents-python/ |
| 长期记忆的实现形态：客户端执行的记忆目录、即时检索、路径遍历防护（3.3、3.6 章） | Claude · Memory tool | https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool |
| 即时检索、上下文预算、长任务的三套手法（上下文压缩 / 结构化笔记 / 子代理）与压缩该保留什么（3.3、3.4、3.6 章） | Anthropic · Effective context engineering for AI agents | https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents |
| 三套手法的作用域（清理工具结果 / 压缩 / 结构化笔记）、`clear_tool_uses` 的 `keep` 与 `clear_at_least`、压缩的默认阈值与保留清单、上下文腐烂（3.6 章） | Claude · Context engineering: memory, compaction, and tool clearing | https://platform.claude.com/cookbook/tool-use-context-engineering-context-engineering-tools |
| 记忆存储作为托管能力：跨会话的用户偏好、项目约定与历史错误（3.6 章） | Claude · Using agent memory（Memory stores） | https://platform.claude.com/docs/en/managed-agents/memory |
| 会话的两种保存方式：`previous_response_id` 与服务端存储的边界（3.6 章） | OpenAI · Conversation state | https://developers.openai.com/api/docs/guides/conversation-state |
| SQLite `ALTER TABLE` 的能力边界（只支持重命名与增删列、加 `NOT NULL` 需默认值）（3.6 章） | SQLite · ALTER TABLE | https://www.sqlite.org/lang_altertable.html |
| 在 SQLite 上改列约束的推荐做法（批处理模式与 `render_as_batch`）（3.6 章） | Alembic · Batch mode | https://alembic.sqlalchemy.org/en/latest/batch.html |
| 编排者–工作者结构、投入档位（1 个 / 2–4 个 / >10 个子代理）、交接四件（目标 / 输出格式 / 工具与来源 / 边界）、质量提升 90.2% 与约 4×、约 15× 的词元量级、广度优先 vs 依赖中间结果（3.7 章） | Anthropic · How we built our multi-agent research system | https://www.anthropic.com/engineering/multi-agent-research-system |
| A2A 规范：Agent Card、Task 生命周期、Message/Part/Artifact、不透明执行（按声明能力协作，不访问对方内部状态、记忆与工具）（3.7 章） | A2A Protocol · Specification（v1.0.0） | https://a2a-protocol.org/latest/specification/ |
| A2A 与 MCP 的分工：前者管代理之间的协作，后者为代理提供工具与上下文（3.7 章） | Google · Announcing the Agent2Agent Protocol (A2A) | https://developers.googleblog.com/en/a2a-a-new-era-of-agent-interoperability/ |
| `json_schema` + `strict: true`、`additionalProperties: false`、首次使用 schema 的额外延迟（3.2 章） | OpenAI · Structured model outputs | https://developers.openai.com/api/docs/guides/structured-outputs |
| 结构化输出与工具调用（3.5 章） | OpenAI · API 文档 | https://developers.openai.com/api/docs |
| 工具调用协议（3.5 章） | Claude · Tool use | https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview |
| 工具定义的三个字段、`tool_choice` 的三种取值、工具结果如何回填（3.5 章） | Claude · Implementing tool use | https://platform.claude.com/docs/en/agents-and-tools/tool-use/implement-tool-use |
| 一次响应里的多个调用：默认开启、`disable_parallel_tool_use` 与何时该关掉（3.5 章） | Claude · Parallel tool use | https://platform.claude.com/docs/en/agents-and-tools/tool-use/parallel-tool-use |
| 工具执行失败的回填（`is_error`）、超长结果与不可重试错误（3.5 章） | Claude · Handling tool calls | https://platform.claude.com/docs/en/agents-and-tools/tool-use/handle-tool-calls |
| `tools` / `tool_choice` / `parallel_tool_calls` 三个参数与严格模式的字段要求（3.5 章） | OpenAI · Function calling | https://developers.openai.com/api/docs/guides/function-calling |
| 两类威胁模型（越狱 / 直接注入 = 用户是对手；间接注入 = 用户可信而内容不可信）、不可信内容的四条处理纪律（只进工具结果 / 标注来源 / 系统提示里声明策略 / JSON 编码）、注入检测的三种粒度、以及「红队自己的代理」（3.8 章） | Claude · Mitigate jailbreaks and prompt injections | https://platform.claude.com/docs/en/test-and-evaluate/strengthen-guardrails/mitigate-jailbreaks |
| Agents Rule of Two：三条属性（[A] 处理不可信输入 / [B] 访问敏感系统或私有数据 / [C] 改状态或对外通信）在同一会话里**最多同时具备两条**；三条齐备时不得自主运行，至少要有监督（人类在环），或在干净的上下文里新开会话（3.8 章） | Meta · Agents Rule of Two: A Practical Approach to AI Agent Security | https://ai.meta.com/blog/practical-ai-agent-security/ |
| 风险分类与治理口径（2.1、3.8 章）；本章点到 LLM01 提示注入 / LLM02 敏感信息泄露 / LLM06 过度代理（Excessive Agency）/ LLM10 不当输出处理（Improper Output Handling）四条 | OWASP · GenAI LLM Top 10 2026 | https://genai.owasp.org/llm-top-10/ |
| 提示注入与防护（3.8 章） | OWASP · LLM Top 10 | https://genai.owasp.org/llm-top-10/ |
| 风险治理框架（3.8 章） | NIST · AI Risk Management Framework | https://www.nist.gov/itl/ai-risk-management-framework |
| 可观测性的定义与三支柱（指标 / 日志 / 追踪各自回答什么）、与「多打日志」的分界、黑盒与白盒监控、四类黄金信号（延迟 / 流量 / 错误 / 饱和度）（3.9.1–3.9.2） | Google · SRE Book, Chapter 6: Monitoring Distributed Systems | https://sre.google/sre-book/monitoring-distributed-systems/ |
| GenAI 语义约定总站：`gen_ai.*` 属性、模型调用与工具执行的 span、词元用量的口径（含缓存词元与「按计费口径报」）、采样要用的属性（3.9.2–3.9.5） | OpenTelemetry · Semantic conventions for GenAI | https://opentelemetry.io/docs/specs/semconv/gen-ai/ |
| span 覆盖「含全部重试」的一次逻辑操作、span 名 `{操作} {模型}`、`invoke_agent` / `execute_tool` 等操作名、内容类属性（输入/输出消息、系统提示、工具定义）逐项 `Opt-In` 且带敏感数据警告、语义约定状态为 Development（3.9.3、3.9.5） | OpenTelemetry · GenAI client spans（语义约定源文件） | https://raw.githubusercontent.com/open-telemetry/semantic-conventions-genai/main/docs/gen-ai/gen-ai-spans.md |
| Agent 与工具 span 的操作名与层级、工具 span 的属性（3.9.3） | OpenTelemetry · GenAI agent spans | https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/gen-ai-agent-spans.md |
| 评测的结构（task / trial / grader / transcript / outcome / harness / suite）、三类 grader 的强弱点、判产出不判路径、能力评估与回归评估及毕业机制、pass@k 与 pass^k、起步 20–50 条真实失败题、隔离每次试验、跟踪四类指标（3.9.6–3.9.8） | Anthropic · Demystifying evals for AI agents | https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents |
| 评测的两阶段（先代码评分、后人工评分）与题面质量的三条要求、0% 通过率先怀疑题、参考解（3.9.6–3.9.7） | Claude · Create strong empirical evaluations | https://platform.claude.com/docs/en/test-and-evaluate/develop-tests |
| 评测的统计五条建议：报标准误（SEM）与 95% 置信区间、聚类标准误（实测可大到 3 倍以上）、题目内多采样降方差、配对差（相关系数 0.3–0.7）、功效分析（3.9.7） | Anthropic · A statistical approach to model evaluations | https://www.anthropic.com/research/statistical-approach-to-model-evals |
| 可观测性平台侧与数据模型（7.2 章；3.9 章不引平台） | Langfuse 官方文档 | https://langfuse.com/docs |
| 评估方法与指标（3.9 章备查；本章不用） | Ragas 官方文档 | https://docs.ragas.io/en/stable/ |
| `TestClient` 与端到端验收的官方写法（3.10.4–3.10.5） | FastAPI · Testing | https://fastapi.tiangolo.com/tutorial/testing/ |
| 依赖覆盖 `app.dependency_overrides`：只换依赖、不换应用（3.10.4） | FastAPI · Testing Dependencies with Overrides | https://fastapi.tiangolo.com/advanced/testing-dependencies/ |
| 架构图与时序图的语法（3.10.1、`zhizhou-v3/docs/architecture.md`） | Mermaid 官方文档 | https://mermaid.js.org/ |

### 第 4 篇 · AI 应用开发框架

| 用途 | 官方出处 | 链接 |
| --- | --- | --- |
| 文档总站（全篇） | LangChain 官方文档 | https://docs.langchain.com/ |
| LangChain Python 概览（4.1 章） | LangChain · Overview | https://docs.langchain.com/oss/python/langchain/overview |
| **v1 命名空间变更（必读）** | LangChain v1 新特性 | https://docs.langchain.com/oss/python/releases/langchain-v1 |
| 消息类型与 `trim_messages`（4.1 章） | LangChain · Messages | https://docs.langchain.com/oss/python/langchain/messages |
| `init_chat_model` 与模型参数（4.1 章） | LangChain · Models | https://docs.langchain.com/oss/python/langchain/models |
| 结构化输出的两种策略与错误重试（4.2 章） | LangChain · Structured output | https://docs.langchain.com/oss/python/langchain/structured-output |
| 提示模板族与 `MessagesPlaceholder`（4.2 章） | LangChain · Reference: prompts 参考 | https://reference.langchain.com/python/langchain-core/prompts |
| 解析器族的分工与官方定位（4.2 章） | LangChain · Reference: output_parsers 参考 | https://reference.langchain.com/python/langchain-core/output_parsers |
| `with_structured_output` 与 `include_raw` 的三字段（4.2 章） | LangChain · Reference: with_structured_output | https://reference.langchain.com/python/langchain-core/language_models/chat_models/BaseChatModel/with_structured_output |
| Agent = Model + Harness、中间件分类（4.3 章） | LangChain · Agents | https://docs.langchain.com/oss/python/langchain/agents |
| `@tool` 的三种 schema 来源与保留参数名（4.3 章） | LangChain · Tools | https://docs.langchain.com/oss/python/langchain/tools |
| 四种审批决策与 `when` 谓词的版本要求（4.3 章） | LangChain · Human-in-the-loop | https://docs.langchain.com/oss/python/langchain/human-in-the-loop |
| 本章四个中间件的签名与默认值（4.3 章） | LangChain · Reference: middleware 参考 | https://reference.langchain.com/python/langchain/middleware |
| 默认异常处理器的规则（4.3 章） | LangGraph · Reference: agents / ToolNode | https://reference.langchain.com/python/langgraph/agents |
| 下游兜底超时与重试常量（4.1 章） | OpenAI · Python SDK | https://github.com/openai/openai-python |
| 集成与模型提供方（4.2 章） | LangChain · Integrations | https://docs.langchain.com/oss/python/integrations/providers/overview |
| LangGraph 与状态编排（4.4 章） | LangGraph · Overview | https://docs.langchain.com/oss/python/langgraph/overview |
| 图 API（节点/边/状态）（4.4 章） | LangGraph · Graph API | https://docs.langchain.com/oss/python/langgraph/graph-api |
| 图 API 用法：reducer、输入/输出 schema、私有通道（4.4 章） | LangGraph · Use the graph API | https://docs.langchain.com/oss/python/langgraph/use-graph-api |
| 检查点与线程（中断的前提）（4.4 章） | LangGraph · Persistence | https://docs.langchain.com/oss/python/langgraph/persistence |
| `interrupt` 的两半：它需要什么、恢复时重跑什么（4.4 章） | LangGraph · Interrupts | https://docs.langchain.com/oss/python/langgraph/interrupts |
| `stream_mode` 四种模式与 `output_keys`（4.4 章） | LangGraph · Streaming | https://docs.langchain.com/oss/python/langgraph/streaming |
| `StateGraph` 的参数（state / input_schema / output_schema）（4.4 章） | LangGraph · Reference: StateGraph | https://reference.langchain.com/python/langgraph/graph/state/StateGraph |
| 时间旅行：读历史、从旧快照分支、`as_node` 那条限定（4.5 章） | LangGraph · Use time travel | https://docs.langchain.com/oss/python/langgraph/use-time-travel |
| 自定义检查点后端：五个方法的签名与负索引约定（4.5 章） | LangGraph · Reference: BaseCheckpointSaver | https://reference.langchain.com/python/langgraph/checkpoint/base/BaseCheckpointSaver |
| 多智能体：Supervisor 拓扑与子代理（4.5 章） | LangChain · Multi-agent | https://docs.langchain.com/oss/python/langchain/multi-agent |
| 交接的两种实现：单代理 ＋ 中间件 / 多份子图（4.5 章） | LangChain · Handoffs | https://docs.langchain.com/oss/python/langchain/multi-agent/handoffs |
| `Command(goto=...)` / `resume` / `update` 三个参数的语义（4.5 章） | LangGraph · Reference: Command | https://reference.langchain.com/python/langgraph/types/Command |
| 跨线程记忆：为什么长期记忆不放在检查点里（4.5 章） | LangGraph · Persistence › Memory store | https://docs.langchain.com/oss/python/langgraph/persistence#memory-store |
| API 参考（全篇） | LangChain / LangGraph Reference | https://reference.langchain.com/python/ |

### 第 5 篇 · RAG 与生产级系统

| 用途 | 官方出处 | 链接 |
| --- | --- | --- |
| 检索在框架侧的抽象：retriever / vector store / text splitter 三件套（5.1、5.3 章） | LangChain · Retrieval | https://docs.langchain.com/oss/python/langchain/retrieval |
| **为什么切分会决定召回上限**：给每一片补上它在原文里的上下文（5.2 章） | Anthropic · Introducing Contextual Retrieval | https://www.anthropic.com/news/contextual-retrieval |
| 工程视角的流程综述与四阶段的另一种画法（5.1 章，仅作对照） | MongoDB · What is RAG? | https://www.mongodb.com/resources/basics/artificial-intelligence/retrieval-augmented-generation |
| 向量数据库（5.3、5.7 章） | Milvus 官方文档 | https://milvus.io/docs |
| Milvus 快速开始 | Milvus · Quickstart | https://milvus.io/docs/quickstart.md |
| Milvus 多租户与库表设计（5.7 章） | Milvus · Database | https://milvus.io/docs/manage_databases.md |
| 评估框架与指标（5.6 章） | Ragas 官方文档 | https://docs.ragas.io/en/stable/ |
| 忠实度的官方算法：回答拆成断言、逐条判断能否从检索上下文推出，且**只量事实一致性、不量完整性**（5.6 章） | Ragas · Faithfulness | https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/faithfulness/ |
| 回答相关度的官方算法：由回答反推 N 个问题（默认 3）、与原问题算嵌入余弦取平均；文档明说**它不保证落在 0–1**（5.6 章） | Ragas · Answer Relevancy | https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/answer_relevance/ |
| 上下文精度的官方公式，以及那个说明排序敏感性的例子：不相关的片排第 2 位不影响、排第 1 位减半（5.6 章） | Ragas · Context Precision | https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/context_precision/ |
| 上下文召回需要参考答案（reference）——本章唯一明确不具备的那个输入（5.6 章） | Ragas · Context Recall | https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/context_recall/ |
| 评测集的四条要求，含「样本数要足够得出统计显著的结论」（5.6 章的 `1/n` 是它的可计算形式） | Ragas · Testset Generation | https://docs.ragas.io/en/stable/concepts/test_data_generation/ |
| 这套指标的原始出处，出发点是「不依赖人工标注」（5.6 章） | Ragas · Automated Evaluation of RAG (2023) | https://arxiv.org/abs/2309.15217 |
| 评估入门实操 | Ragas · Evaluate a simple LLM app | https://docs.ragas.io/en/latest/getstarted/evals/ |
| 向量化与嵌入模型 | Hugging Face · Sentence Transformers | https://sbert.net/ |
| 检索评测基准（5.6 章） | BEIR 基准 | https://github.com/beir-cellar/beir |
| **片长到底该定多少**：小片适合事实型问答、大片适合宽上下文，且不同嵌入模型敏感度不同（5.2 章） | Rethinking Chunk Size For Long-Document Retrieval (2025) | https://arxiv.org/abs/2505.21700 |
| 高级切法的对照实验（5.2 章，仅作对照） | Comparative Evaluation of Advanced Chunking for RAG (2025) | https://pmc.ncbi.nlm.nih.gov/articles/PMC12649634/ |
| 框架侧「加载 → 切分 → 嵌入 → 存储」那条链（5.2 章） | LangChain · Knowledge base | https://docs.langchain.com/oss/python/langchain/knowledge-base |
| 切分器的概念与「按语义层级级联」（5.2 章） | LangChain · Text splitters | https://python.langchain.com/docs/concepts/text_splitters/ |
| `RecursiveCharacterTextSplitter` 参数与语言感知分隔符（5.2 章） | LangChain · Recursive text splitter | https://python.langchain.com/docs/how_to/recursive_text_splitter/ |
| 父子片的官方实现（5.2 章） | LangChain · Parent Document Retriever | https://python.langchain.com/docs/how_to/parent_document_retriever/ |
| 按嵌入相似度找断点的官方实现（5.2 章） | LangChain · Semantic chunker | https://python.langchain.com/docs/how_to/semantic-chunker/ |
| 工程侧对「按标题／元素／token」几种切法的分类（5.2 章） | Unstructured · Chunking | https://docs.unstructured.io/open-source/core-functionality/chunking |
| `get_text()` 的抽取模式与加密件的 `authenticate`（5.2 章） | PyMuPDF 文档 | https://pymupdf.readthedocs.io/en/latest/ |
| Word 解析与标题样式（5.2 章） | python-docx 文档 | https://python-docx.readthedocs.io/en/latest/ |
| PPT 解析（5.2 章） | python-pptx 文档 | https://python-pptx.readthedocs.io/en/latest/ |
| 魔数检测与 libmagic（5.2 章） | file(1) 与 libmagic 源码 | https://github.com/file/file |
| 编码检测（5.2 章） | chardet 文档 | https://chardet.readthedocs.io/en/latest/ |
| NFKC 规范化与 Unicode 类别（清洗那一步的依据）（5.2 章） | Python 标准库 · unicodedata | https://docs.python.org/3/library/unicodedata.html |
| 中文 OCR 引擎（5.2 章） | PaddleOCR 官方文档 | https://www.paddleocr.ai/latest/en/index.html |
| 备选 OCR 引擎（5.2 章） | Tesseract OCR | https://tesseract-ocr.github.io/ |
| **归一化后内积 == 余弦**；`metric_type` 的 COSINE／IP／L2 三种取法（5.3 章） | Milvus · Similarity Metrics | https://milvus.io/docs/metric.md |
| 索引族的选型入口；**`IVF_FLAT` 不做压缩**、索引文件与原始向量大小相当（5.3 章） | Milvus · In-memory Index | https://milvus.io/docs/index.md |
| 索引的内部结构由近似最近邻算法决定（5.3 章） | Milvus · Index Explained | https://milvus.io/docs/index-explained.md |
| `nlist` / `nprobe` 的官方定义与适用规模（5.3 章） | Milvus · IVF_FLAT | https://milvus.io/docs/ivf-flat.md |
| 量化索引族（`IVF_PQ`）的官方说明（5.3 章） | Milvus · IVF_PQ | https://milvus.io/docs/ivf-pq.md |
| 图索引的 `M` / `efConstruction` / `ef`（5.3 章，**本章未实现**） | Milvus · HNSW | https://milvus.io/docs/hnsw.md |
| BGE 模型族与 v1.5 的变化（5.3 章） | BGE 官方文档 · BGE v1 & v1.5 | https://bge-model.com/bge/bge_v1_v1.5.html |
| **bge-large-zh-v1.5 是 1024 维**的权威出处（5.3 章） | Hugging Face · BAAI/bge-large-zh-v1.5 | https://huggingface.co/BAAI/bge-large-zh-v1.5 |
| 官方用法与批大小／FP16 等运维旋钮（5.3 章） | FlagEmbedding 仓库 | https://github.com/FlagOpen/FlagEmbedding |
| 中文嵌入模型的能力边界与评测口径（5.3 章） | BGE 技术报告 · C-Pack | https://arxiv.org/abs/2309.07597 |
| **倒数排名融合的原始论文**，也是 `k=60` 的出处（5.4 章） | Cormack、Clarke、Buettcher · SIGIR 2009 | https://cormack.uwaterloo.ca/cormacksigir09-rrf.pdf |
| 官方把重排分成两档的入口页；加权那一档流程里有**分数归一化**这一步（5.4 章） | Milvus · Reranking | https://milvus.io/docs/reranking.md |
| 官方对 RRF 的定位：「不给显式权重、把多条路平等地合起来」时用它（5.4 章） | Milvus · RRF Ranker | https://milvus.io/docs/rrf-ranker.md |
| 加权那一档的取分与归一化流程（5.4 章） | Milvus · Weighted Ranker | https://milvus.io/docs/weighted-ranker.md |
| 多路检索与重排策略在引擎侧的接线方式（5.4 章） | Milvus · Multi-Vector Hybrid Search | https://milvus.io/docs/multi-vector-search.md |
| 框架侧的混合检索实现：**带权重的倒数排名融合**，权重默认等权（5.4 章） | LangChain · `EnsembleRetriever` | https://reference.langchain.com/python/langchain-classic/retrievers/ensemble/EnsembleRetriever |
| 交叉编码器的官方用法（`CrossEncoder.predict([(query, doc)])`）（5.4 章） | Sentence Transformers · Cross-Encoder 用法 | https://www.sbert.net/docs/cross_encoder/usage/usage.html |
| 可直接取用的重排模型清单（5.4 章） | Sentence Transformers · 预训练交叉编码器 | https://www.sbert.net/docs/cross_encoder/pretrained_models.html |
| **「交叉编码器被广泛用于对其他模型召回的 top-k 文档重排」**的官方出处（5.4 章） | BAAI · `bge-reranker-large` | https://huggingface.co/BAAI/bge-reranker-large |
| 生产配置里常点名的那一个重排模型（5.4 章） | BAAI · `bge-reranker-v2-m3` | https://huggingface.co/BAAI/bge-reranker-v2-m3 |
| 托管重排 API 的产品视角（接口与计费口径）（5.4 章） | Cohere · Rerank | https://docs.cohere.com/docs/rerank-overview |
| HyDE：先编一段假设答案再检索（5.4 章，**本章未实现**） | Gao 等 · Precise Zero-Shot Dense Retrieval without Relevance Labels (2022) | https://arxiv.org/abs/2212.10496 |
| 「密集／稀疏／混合三条路各有赢面」的评测依据（5.4 章，仅作口径对照） | BEIR 论文 | https://arxiv.org/abs/2104.08663 |
| **引用可以是一等能力**：模型输出带结构化出处、可被下游核验（5.5 章） | Anthropic · Citations | https://platform.claude.com/docs/en/build-with-claude/citations |
| 框架侧的 CRAG 参考实现：评估—分档—三支动作（含「网络搜索」那一支）（5.5 章） | LangGraph · Corrective RAG 教程 | https://langchain-ai.github.io/langgraph/tutorials/rag/langgraph_crag/ |
| 框架内置的中心化判分器接口（把「评估器」做成可替换的一层）（5.5 章，仅作契约对照） | LangChain · Retrieval 里的 document graders | https://docs.langchain.com/oss/python/langchain/retrieval |
| 「拒答」是 RAG 的一等输出、不是失败（5.5 章） | Anthropic · Reducing hallucinations | https://platform.claude.com/docs/en/test-and-evaluate/strengthen-guardrails/reduce-hallucinations |
| **事件流的四个字段与三条语法细节**：空行结束一帧、冒号开头是注释、`retry` 必须为整数；浏览器端的连接上限与重连默认行为（5.7 章） | MDN · Using server-sent events | https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events |
| 心跳在主流实现里的落地：`ping` 默认 15 秒、行分隔符默认 `\r\n`、`send_timeout` 与优雅退出的先后（5.7 章，仅作对照；**本树不引这个库**） | sse-starlette | https://github.com/sysid/sse-starlette |
| **每个键值组合都是一条新的时间序列**：指标名与标签的命名规则、单位写进名字、不允许无界取值的标签（5.7 章的高基数护栏出自这里） | Prometheus · Metric and label naming | https://prometheus.io/docs/practices/naming/ |
| TTL 会被 `DEL`／`SET`／`GETSET` 这类覆盖键内容的命令清掉；`EXPIRE` 收相对时长而 `PEXPIREAT` 收绝对时刻（5.7 章的写入与设期不可分） | Redis · EXPIRE | https://redis.io/docs/latest/commands/expire/ |
| 线程池默认上限 `min(32, os.cpu_count() + 4)`（5.7 章报的 20 是它在本机的值） | Python · concurrent.futures | https://docs.python.org/3/library/concurrent.futures.html |
| 同步阻塞调用要用 `to_thread`（5.7 章 490.0ms 对 60.7ms 那一组的依据） | Python · Coroutines and Tasks（含 `asyncio.to_thread`） | https://docs.python.org/3/library/asyncio-task.html |
| 一次生成请求的字段形状（已在 3.9 落地，5.7 章只把它接到常驻服务上） | OpenTelemetry · GenAI semantic conventions | https://opentelemetry.io/docs/specs/semconv/gen-ai/ |
| CSV 的定义方式：按分隔符切、按引号转义的行序列——5.8 章「不能只看有没有逗号」那条判据的依据 | Python · csv | https://docs.python.org/3/library/csv.html |
| 只用标准库取 HTML 文本（5.8 章 `.html` 那一档不引 BeautifulSoup 的官方依据） | Python · html.parser | https://docs.python.org/3/library/html.parser.html |
| `.docx`／`.pptx`／`.xlsx` 都是 ZIP 容器，所以只能靠包内路径分（5.8 章的 `_ZIP_KIND`） | Python · zipfile | https://docs.python.org/3/library/zipfile.html |
| `rglob`／`relative_to`／`suffix` 的语义，以及「发现阶段」的排序与文档名折算（5.8 章） | Python · pathlib | https://docs.python.org/3/library/pathlib.html |
| 内容戳用的 SHA-256 前 12 位（5.8 章的 `content_stamp` 由它实现，**不是加密用途**） | Python · hashlib | https://docs.python.org/3/library/hashlib.html |
| **内容寻址**的经典出处：对象名由「内容 ＋ 类型 ＋ 长度」的哈希算，而不是由文件名——5.8 章的「内容哈希即身份」同一条思路 | Git · Git Internals · Git Objects | https://git-scm.com/book/en/v2/Git-Internals-Git-Objects |
| 按魔数识别文件类型的最小实现规范（5.8 章的 `MAGIC` 表是它的子集：只看开头几个字节）。`magic(5)` 不属于 man-pages 计划，`man7.org` 上没有这一页（实测 404），故登记发行版的官方镜像页 | file(1) · magic(5) | https://manpages.ubuntu.com/manpages/jammy/man5/magic.5.html |
| 官方媒体类型注册表：「类型是注册的、后缀只是建议的」（5.8 章「格式按内容判」的权威表述） | IANA · Media Types | https://www.iana.org/assignments/media-types/media-types.xhtml |
| Python 标准编码表里 `gb18030` 的位置（5.8 章的 `parse_text` 先试 UTF-8、失败再按它解码） | Python · codecs · Standard Encodings | https://docs.python.org/3/library/codecs.html#standard-encodings |
| 架构图的官方语法（`flowchart LR` / `flowchart TD`）；**图是文本**，所以能进版本库、能被 diff（5.9 章的两张图据此写成） | Mermaid · Flowchart | https://mermaid.js.org/syntax/flowchart.html |
| 时序图的官方语法（5.9 章在线侧用的是流程图而非时序图，理由写在 5.9.2：这里要回答「谁调谁、留下什么产物」） | Mermaid · Sequence diagram | https://mermaid.js.org/syntax/sequenceDiagram.html |
| **决策记录（ADR）的原始出处**：一条决定记成「背景—决定—后果」，出发点是让后来的人知道当时的处境（5.9 章的六字段由它扩展而来） | Michael Nygard · Documenting Architecture Decisions (2011) | https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions |
| 决策记录模板的社区索引与「编号 ＋ 状态」这两个约定（5.9 章只借这两个约定，不引其模板） | adr.github.io · Architecture Decision Records | https://adr.github.io/ |
| 「按读者分层画图」（上下文／容器／组件／代码）的通用提法（5.9 章的「两张图 ＋ 图外表」是它在一次小项目上的落地） | C4 model | https://c4model.com/ |

### 第 6 篇 · 模型接入与成本工程（新增篇）

| 用途 | 官方出处 | 链接 |
| --- | --- | --- |
| 多厂商统一调用（6.2、6.3 章） | LiteLLM 官方文档 | https://docs.litellm.ai/ |
| Claude API 与定价（6.1 章） | Claude · API 概览 | https://platform.claude.com/docs/en/api/overview |
| **登记表的四个价与两处加成**：缓存写 1.25×（5 分钟）／2×（1 小时）、缓存读 0.1×（Fable 5.1 与 Mythos 5.1 是 0.025× 的例外）、批量 50%、驻留 1.1×、工具使用的系统提示词词元数（6.1 章） | Claude · Pricing | https://platform.claude.com/docs/en/about-claude/pricing |
| **「短档/长档」两套价的分界与缓存写 1.25×**（6.1 章） | OpenAI · Pricing | https://developers.openai.com/api/docs/pricing |
| 逐个模型的窗口、最大输出与知识截止（6.1 章） | OpenAI · Models | https://developers.openai.com/api/docs/models |
| **「>272K 输入按 2× 输入、1.5× 输出，且作用于整单（for the full request）」那句话的出处**（6.1 章） | OpenAI · GPT-5.6 Terra | https://developers.openai.com/api/docs/models/gpt-5.6-terra |
| OpenAI Responses API（6.2 章） | OpenAI · API 文档 | https://developers.openai.com/api/docs |
| **Messages 的形状条款**：`system` 顶层字段、`max_tokens` 必填、`tool_use` / `tool_result` 的块形态与 `stop_reason`（6.2 章） | Claude · Messages API | https://platform.claude.com/docs/en/api/messages |
| **命名事件、`ping`、`input_json_delta` 的参数分片、流里的错误事件**（6.2 章） | Claude · Streaming | https://platform.claude.com/docs/en/build-with-claude/streaming |
| `input_schema`、`tool_choice` 与「工具结果放在 user 消息里」（6.2 章） | Claude · Tool use | https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview |
| **Messages 与 Items 的区别**、`instructions`、`text.format`、`store` 默认存（6.2 章） | OpenAI · 迁移到 Responses | https://developers.openai.com/api/docs/guides/migrate-to-responses |
| **`arguments` 是 JSON 字符串**、`role="tool"` 的结果消息、兼容层与 Responses 的工具能力差别（6.2 章） | OpenAI · 函数调用 | https://developers.openai.com/api/docs/guides/function-calling |
| `status: incomplete` 与 `incomplete_details.reason` 的两个取值（6.2 章） | OpenAI · 推理模型 | https://developers.openai.com/api/docs/guides/reasoning |
| 数据留存与隐私（6.4 章） | OpenAI · 数据控制 | https://developers.openai.com/api/docs/guides/your-data |
| **批量通道的两条口径**：**50% off** 与 **24 小时完成窗口**、`.jsonl` 的提交形状、以及「批量有自己的一份限流配额」（6.4 章） | OpenAI · Batch API | https://developers.openai.com/api/docs/guides/batch |
| **同一个 50%、同一个 up to 24 hours**：这是本章少数能当断言用的共同点之一（两家在这一点上完全一致），以及批量的结果形状与「结束后取回」（6.4 章） | Claude · Message Batches | https://platform.claude.com/docs/en/build-with-claude/batch-processing |
| **错误分档表里 Messages 那一列**：11 个状态码、`request_id`、「SDKs automatically retry transient failures with exponential backoff, twice by default, honoring the retry-after header」、以及流式错误不走标准机制（6.3 章） | Claude · Errors | https://platform.claude.com/docs/en/api/errors |
| **错误分档表里另两家那两列**：`rate_limit_error` / `slow_down` / `server_is_overloaded` 的取值，以及那句最常用的判据「Retrying billing, spend, or quota errors won't restore API access」（6.3 章） | OpenAI · Error codes | https://developers.openai.com/api/docs/guides/error-codes |
| **降级的三种写法与冷却**：`fallbacks` / `context_window_fallbacks` / `content_policy_fallbacks`、`num_retries` × `request_timeout` × `allowed_fails` / `cooldown_time`、in-order 语义与 `attempted_fallbacks` 这条可观测性字段（6.3 章） | LiteLLM · Fallbacks（Provider Failover） | https://docs.litellm.ai/docs/proxy/reliability |
| **路由策略与超窗预检**：simple-shuffle / latency-based / lowest-cost，以及「没有 `enable_pre_call_checks`，超窗的请求照样发出去」（6.3 章） | LiteLLM · Router（Load Balancing） | https://docs.litellm.ai/docs/routing |
| 自建推理服务（6.3 章） | vLLM 官方文档 | https://docs.vllm.ai/ |
| 本地模型运行（6.3 章） | Ollama 官方 | https://ollama.com/ |

### 第 7 篇 · AI 应用工程化（新增篇）

| 用途 | 官方出处 | 链接 |
| --- | --- | --- |
| 评测流水线与回归（7.1 章） | Ragas 官方文档 | https://docs.ragas.io/en/stable/ |
| **实验的四条原则（含 `Isolate changes`）与四步流程**：Setup → Run → Evaluate → Store；结果按时间戳落盘、命名要带「改了什么＋版本＋日期」、元数据建议（`git_commit` / `environment` / `model_version` / `total_tokens` / `response_time_ms`）、出错保留部分结果（7.1 章） | Ragas · Experimentation | https://docs.ragas.io/en/stable/concepts/experimentation/ |
| **评测集里的查询类型**（单跳／多跳、具体／抽象）与「样本数要足够得出统计显著的结论」（7.1 章的 `1/n` 是它的可计算形式） | Ragas · Testset Generation for RAG | https://docs.ragas.io/en/stable/concepts/test_data_generation/rag/ |
| **退出码表**：`0` 全过、`1` 有失败、`2` 被用户中断、`3` 内部错、`4` 用法错、`5` **没有收集到测试**（非零）、`6` 警告超限——「没跑」与「跑了且全过」是两件事（7.1 章） | pytest · Exit codes | https://docs.pytest.org/en/stable/reference/exit-codes.html |
| 追踪与成本看板（7.2 章） | Langfuse 官方文档 | https://langfuse.com/docs |
| **数据模型**：观测按 `trace_id` 归组、trace 级属性（`user_id`／`session_id`／`tags`／`metadata`）复制到每一行观测、会话把多条 trace 串起来、内置在 OpenTelemetry 之上、**后台批量导出与短进程退出前必须 `flush()`**（7.2 章） | Langfuse · Observability Data Model | https://langfuse.com/docs/observability/data-model |
| **一条好 trace 长什么样**：trace 的粒度（一轮对话／一次 agent 运行／一次管线执行）与 session、嵌套（工具调用别挂在根上）、**不要用一根 generation 包住整个循环**、**命名是接口**（动态值不进名字、低基数、不要拿模型名当名字）、算成本要的三件套（模型名 ＋ usage ＋ 可选的 cost 覆盖）、标签在创建时定死而事后判定用 score（7.2 章） | Langfuse · What does a good trace look like? | https://langfuse.com/docs/observability/best-practices |
| **GenAI client span 的语义约定**：span 名 `{gen_ai.operation.name} {gen_ai.request.model}`、span kind 取 `CLIENT`、属性三档（Required `gen_ai.operation.name`／`gen_ai.provider.name`；Conditionally Required `error.type`／`gen_ai.request.model`；Recommended 包括 `gen_ai.usage.input_tokens`／`output_tokens`／`cache_read.input_tokens`／`cache_write.input_tokens`「适用时才有」）、**被自动重试的请求由一根 span 覆盖含全部重试的逻辑操作**、内容类属性默认不记（7.2 章） | OpenTelemetry · GenAI client spans（语义约定源文件） | https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/gen-ai-spans.md |
| **GenAI 观测的一趟实操**：`invoke_agent` → `chat` / `execute_tool` 的 span 树、两条直方图指标 `gen_ai.client.operation.duration` 与（按 `gen_ai.token.usage` 分输入输出的）`gen_ai.client.token.usage`、**默认不采集提示与工具参数**（敏感数据）（7.2 章） | OpenTelemetry · Inside the LLM Call: GenAI Observability with OpenTelemetry | https://opentelemetry.io/blog/2026/genai-observability/ |
| 追踪标准与埋点（7.2 章） | OpenTelemetry · GenAI 语义约定 | https://opentelemetry.io/docs/specs/semconv/gen-ai/ |
| 提示与配置的版本化、灰度与 A/B（7.3 章） | Langfuse · Prompt CI/CD | https://langfuse.com/resources/engineering/prompt-cicd |
| **把提示词改动当一次发布的六个阶段**：版本 → 验证 → 门 → 放量 → 观测 → 回滚，每一段各自防一种失效（不知道改了什么／修好一处弄坏十处／未检查的改动进生产／离线过了上线炸了／只有真流量才看得出的回归／坏改动留在线上）；**一张「哪些自带、哪些要自己拼」的表**是本章分工的出处——不可变版本与 diff、标签发布、数据集验证、CI 回归门、按版本的生产指标与告警都是自带，而**权重分流（90/10 的百分比住在你的代码里）、「一键选出赢家」、多步审批 要自己拼**；按版本聚合的指标是 median latency ／ median input・output tokens ／ median cost ／ generation count ／ median evaluation score；**SDK 把提示词缓存在进程里、默认 TTL 60 秒并后台重新校验**，所以「挪标签」到「现场真的换了」最坏差一个 TTL（7.3.7 的「回滚是两项之和」） |
| **一次 prompt 版本化的最小形态**：每次保存产生一个**不可变版本**（带版本号与 diff），部署由**标签**控制、一个标签指向恰好一个版本；标签的三类用法（环境 `staging`／`production`、租户 `tenant-1`、实验 `prod-a`／`prod-b`）；`latest` 自动维护、取提示词时不带标签则默认取 `production`；**回滚 ＝ 把 `production` 挪回旧版本**（不用重新部署）；**受保护标签**：成员与查看者不能改也不能删（管理员与所有者可以），连带着那一版也不能被删；企业版另有**审计日志**（谁改了哪个标签、改前改后）；提示词作用域是项目（7.3.2／7.3.7） |
| 提示与配置的版本化、灰度与 A/B（7.3 章） | Langfuse · Prompt Version Control | https://langfuse.com/docs/prompt-management/features/prompt-version-control |
| 分桶与实验分流（7.3 章） | GrowthBook · SDK 规范 | https://docs.growthbook.io/lib/build-your-own |
| **哈希分桶的逐字规范**：`hash(seed, value, version)` 用 32 位 FNV-1a，**v2** 是 `fnv32a(str(fnv32a(seed + value))) % 10000 / 10000`（10,000 个桶）、**v1** 是 `fnv32a(value + seed) % 1000 / 1000`（1,000 个桶，**官方标明「v1 在并行实验下会有偏差」**——它把 seed 拼在后面）；实现必须逐字节一致，另有一套**400 多条跨语言测试**要求所有 SDK 100% 通过；`inRange` 是**左闭右开**（`n >= start && n < end`）；`getBucketRanges` 把**覆盖度乘进每一段**（`(2, 0.5, [0.4, 0.6]) → [[0, 0.2], [0.4, 0.7]]`）、权重和不为 1 就退回等分；**命名空间**（同一命名空间里两段不重叠即互斥）与**过滤器**（默认 `hashVersion` 2）是两种隔离手段；粘性分桶用 `bucketVersion` 强制重新分桶（7.3.4） |
| **偷看与序贯检验**：频繁检验（偷看）会把假阳率抬到名义值之上，而序贯检验是它的频派解法——「随便看多少次」仍把假阳率压在α以内；代价写得很清楚：**序贯置信区间一致地比固定样本区间更宽**，而多宽取决于调参 `N*`（默认 5,000，应设成「你通常会做决定时的样本量」，**开跑后不能改**）；实现取 Asymptotic Confidence Sequences（Waudby-Smith 等 2023），α 默认 0.05（7.3.6） |
| 提示与配置的版本化、灰度与 A/B（7.3 章） | GrowthBook · Sequential Testing | https://docs.growthbook.io/statistics/sequential |
| 实验的统计与早期决策（7.3 章） | Statsig · 序贯检验 | https://docs.statsig.com/stats-engine/sequential-testing |
| **mSPRT 做法与它对「早决定」的告诐**：逐次调整 p 值与区间（区间随数据积累变窄），于是「结果页上可以随时读」；两条适用场景是「发现意外回归」与「机会成本高」，并限定「只在少数关键指标上这么做」；最有价值的一句是**「早做的决定往往给出功效不足的提升估计」**——要准确的效应量就等满功效（它还引 Kohavi 等关于事后功效计算不可靠的那一节）（7.3.6） |
| 配置与代码的边界（7.3 章） | 十二要素应用 · III. Config | https://12factor.net/config |
| **配置的判据**：配置是「在部署之间会变的一切」，它必须与代码**严格分开**（检验标准：代码库能不能在任何时候开源而不泄露凭据）；不推荐「不入版本控制的配置文件」（容易被误提交、散在各处、与语言绑定）；也不用**按环境分组**——环境名会长成组合爆炸，而要「逐项正交、各自独立」（7.3.1 与提示词三件套的边界） |
| 内容寻址与不可变（7.3 章） | Git · What is Git? | https://git-scm.com/book/en/v2/Getting-Started-What-is-Git%3F |
| **内容戳那条性质的出处**：「Git 里一切都被校验和标记过，所以任何内容的改动 Git 都不会不知道」；它**按内容的哈希存储而不是按文件名存储**；Git 基本只增不删（所以「回到旧内容」是一次新提交）（7.3.2） |
| 安全落地的风险清单（7.4 章） | OWASP · LLM Top 10（2025） | https://genai.owasp.org/llm-top-10/ |
| **那十条的名字与编号（本章映射表的原始清单）**：`LLM01` 提示注入、`LLM02` 敏感信息泄露、`LLM03` 供应链、`LLM04` 数据与模型投毒、`LLM05` 不当输出处理、`LLM06` 过度代理、`LLM07` 系统提示泄露、`LLM08` 向量与嵌入弱点、`LLM09` 误信息、`LLM10` 无界消耗——本章逐条落到本项目的某一层，三栏计数 **5 ／ 4 ／ 1**（分母 10），「不适用」那一栏写了理由（本章是 `LLM04`：不训练也不微调）（7.4.1） | OWASP GenAI Security Project · 2025 十大风险与缓解 | https://genai.owasp.org/llm-top-10/ |
| 工具权限与授权（7.4 章） | MCP · 授权规范 | https://modelcontextprotocol.io/specification/2025-06-18/basic/authorization |
| **三道关那三样的出处**：服务端作为 **OAuth 2.1 资源服务器**、令牌的受众用 `resource` 参数表达（资源指示）、`401` 与 `403` 的分工（未提供凭证与凭证不足是两件事）、以及**令牌不得出现在查询串里**——本章的三道关（令牌／scope／参数）把这段规范落成一次判定，而 scope 细到资源实例那一条（安全上的考量）来自它的受众约束（7.4.4） | MCP · 授权（`2025-06-18` 版） | https://modelcontextprotocol.io/specification/2025-06-18/basic/authorization |
| 数据合规与留存（7.5 章） | OpenAI · 数据控制 | https://developers.openai.com/api/docs/guides/your-data |
| **本章从它取的那一条**：API 数据的**留存**与「不用于训练」是两件各自可设置的事（不是一个开关）——本章把这一条落成两列（`privacy.RETENTION` 的 `days` 与 `enforced`），而不是写成一句承诺；这也是「合规章的产物是一张表和一个比例」那条判据的出处之一（7.5.1–7.5.2） | OpenAI · 数据控制与留存 | https://developers.openai.com/api/docs/guides/your-data |
| 内部威胁与治理框架（7.4 章） | NIST · AI RMF | https://www.nist.gov/itl/ai-risk-management-framework |
| **四个动作的名字与次序**：`GOVERN` ／ `MAP` ／ `MEASURE` ／ `MANAGE`——本章的三张表（留存、删除范围、审计自查）是**「度量」那一步**的落地，而 7.4 那张 OWASP 映射表是「映射」那一步（7.5.1 与 7.5.7） | NIST · AI 风险治理（AI RMF 1.0） | https://www.nist.gov/itl/ai-risk-management-framework |
| **四个动作的名字与次序**：`GOVERN` ／ `MAP` ／ `MEASURE` ／ `MANAGE`——本章那张 OWASP 映射表就是**「映射」这一步**的一次落地（把风险清单对到本项目的那一层），而本章的「拦截率与误杀率一起报」是「度量」那一步的最小形态（7.4.1 与本章小结第 1 条） | NIST · AI 风险管理框架（AI RMF 1.0 ＋ 生成式 AI 档案） | https://www.nist.gov/itl/ai-risk-management-framework |

### 第 8 篇 · 交付与产品化（新增篇）

| 用途 | 官方出处 | 链接 |
| --- | --- | --- |
| 容器化与部署（8.1 章） | Docker 官方文档 | https://docs.docker.com/ |
| **每一层是一组文件系统变化、且一旦创建就不可变**（本章 8.1.1 的层账与浪费账都建在这一句上；层复用为什么省带宽也在这里） | Docker · Understanding the image layers | https://docs.docker.com/get-started/docker-concepts/building-images/understanding-image-layers/ |
| **构建缓存的总口径**：一旦某层失效，**它之后的所有层都要重跑**（「即使它们本来会打出一样的结果」），所以要把变化频繁的指令往后放（8.1.2 那张表的出处） | Docker · Docker build cache | https://docs.docker.com/build/cache/ |
| **失效的四条细则**：逐行比对；`COPY`/`ADD` 按**文件元数据**算校验和而 **mtime 不算**；`RUN` 那一层**不会自动失效**（重建一周后还是同一批包）；secret 的内容不参与校验而 `--build-arg` 参与——8.1.2 那五行读数逐条对着它 | Docker · Build cache invalidation | https://docs.docker.com/build/cache/invalidation/ |
| **多阶段构建**：每个 `FROM` 开一段、`COPY --from` 只带走产物、`AS <NAME>` 命名与 `--target` 停在某一段——8.1.3 第四招的出处 | Docker · Multi-stage builds | https://docs.docker.com/build/building/multi-stage/ |
| **上下文与 `.dockerignore`**：指定本地目录时**所有子目录都被包含**、`.dockerignore` 在**发送前**把路径移掉、否定匹配的次序——8.1.4 那一组数的出处 | Docker · Build context 与 .dockerignore | https://docs.docker.com/build/concepts/context/ |
| **构建密钥**：`ENV`/`ARG` 不适合传密钥（「因为它们会留在最终镜像里」）、secret mount 与 SSH mount 的用法、`--mount=type=secret` 的三种挂法——8.1.6 那三档的出处 | Docker · Build secrets | https://docs.docker.com/build/building/secrets/ |
| **Compose 的起序**：启动时**不等到就绪、只等到在跑**、`condition` 的三种取值（`service_started`／`service_healthy`／`service_completed_successfully`）、`healthcheck` 的四个参数与 `restart: true`——8.1.5 整节的出处 | Docker · Control startup and shutdown order in Compose | https://docs.docker.com/compose/how-tos/startup-order/ |
| **常见指令与那条最佳实践**：`FROM`／`WORKDIR`／`COPY`／`RUN`／`ENV`／`EXPOSE`／`USER`／`CMD` 各自管什么，以及那句「建一个应用用户，别用 root 跑」——8.1.6 第一件的出处 | Docker · Writing a Dockerfile | https://docs.docker.com/get-started/docker-concepts/building-images/writing-a-dockerfile/ |
| **只读根文件系统与挂卷**：把容器的根文件系统当「金镜像」、需要写的地方显式挂出来（`--read-only`）——8.1.6 第三、四行的出处 | OWASP · Docker Security Cheat Sheet | https://cheatsheetseries.owasp.org/cheatsheets/Docker_Security_Cheat_Sheet.html |
| CI/CD 与发布（8.2 章） | GitHub Actions 官方文档 | https://docs.github.com/actions |
| **官方那套查找顺序与四条限制**：`key` 精确 → `key` 的部分匹配 → `restore-keys`（按写的顺序，各按前缀找）→ **默认分支上把这几步再来一遍**；**缓存的内容不可改**（只能换 key）；作用域**单向**（当前分支 ＋ 默认分支，看不见子分支与兄弟分支、也看不见别的标签）；**7 天没访问被清、仓库上限 10 GiB、超限时按最后访问从旧往新清**——8.2.3 那六行读数与两组清理账逐条对着它 | GitHub · Dependency caching reference | https://docs.github.com/en/actions/reference/dependency-caching-reference |
| **低信任触发器与缓存的边界**（同一页下半部）：只有 `push`／`workflow_dispatch`／`schedule` 等少数触发器能在默认分支作用域**写**缓存，`pull_request_target`／`issue_comment`／`workflow_run` 只有**读**权；而只读的那一次想存时「**保存失败，但 step 与 job 都不失败**」（日志里一句 warning）——8.2.3 那条「校验不通过时它挡住什么」的出处 | GitHub · Dependency caching reference（缓存访问限制与污染） | https://docs.github.com/en/actions/reference/dependency-caching-reference |
| **产物的四条规矩**：依赖别的 job 产物的 job 必须等它**成功**完成（`needs`）；上传返回一个 SHA256 **摘要**、下载时自动比对而**不一致只显示警告**；v4 起**产物不可变**（同名重传要换名字）；`retention-days` 不能超过仓库上限——8.2.3 产物那一组四行的出处 | GitHub · Store and share data with workflow artifacts | https://docs.github.com/en/actions/tutorials/store-and-share-data |
| **那句最要紧的话**：被跳过的 job **会把状态报成 Success**，而且「**即使它是必需检查，它也不会阻止 PR 合并**」——8.2.5 第一种形状（绿而没验）的出处 | GitHub · Using conditions to control job execution | https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-jobs-with-conditions |
| **另一句相反的话**：「如果工作流因**路径过滤、分支过滤或提交信息**被跳过，与它相关的检查会**停留在 Pending**，要求这些检查通过的 PR **会被挡住合并**」；同页给出五个跳过字符串（`[skip ci]`／`[ci skip]`／`[no ci]`／`[skip actions]`／`[actions skip]`）与 `skip-checks:true`，并写明这一招**只对 `push`／`pull_request` 生效**——8.2.1 与 8.2.5 的出处 | GitHub · Skipping workflow runs | https://docs.github.com/en/actions/how-tos/manage-workflow-runs/skip-workflow-runs |
| **必需检查的三种合格状态**：`successful`／`skipped`／`neutral`——8.2.5 里「`cancelled` 不在其中」这条判断的出处（同页还有严格与宽松两种必需检查） | GitHub · About protected branches | https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches |
| **权限与 unpinned 的引用**：任何有写权限的人都能读全部密钥；`GITHUB_TOKEN` 的默认应当收成只读、再按 job 提权；`pull_request_target`／`workflow_run` 是**特权**触发器（共享 main 的缓存、可能有写 token 与密钥），「必须不显式 checkout 不受信任的代码」；**钉到完整 SHA 是目前唯一把 action 当作不可变版本的方式**（标签可以被移动、也可以被删除）——8.2.4 那两组的出处 | GitHub · Secure use reference | https://docs.github.com/en/actions/reference/security/secure-use |
| **fork 与密钥**：「除 `GITHUB_TOKEN` 外，**fork 触发的工作流拿不到密钥**」；密钥未设置时表达式取到的是**空字符串**；环境密钥在审阅人批准前拿不到——8.2.4 第二、三组的出处 | GitHub · Using secrets in GitHub Actions | https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets |
| **OIDC**：不用把云凭证复制一份到仓库，换来的令牌**只对一个 job 有效**、之后自己过期（官方示例里 `exp − iat ＝ 300` 秒）——8.2.4 第四组那两栏的出处 | GitHub · OpenID Connect | https://docs.github.com/en/actions/concepts/security/openid-connect |
| 镜像与编排排错 | Docker · Compose | https://docs.docker.com/compose/ |
| CI/CD 与发布（8.2 章） | GitHub Actions 文档 | https://docs.github.com/en/actions |
| **数据流协议的底层就是 SSE**：官方原文说它「用 SSE 格式，为的是更统一的约定、通过 ping 保活、重连能力，以及更好的缓存处理」；事件类型表（`text-delta`／`reasoning-*`／`tool-input-*`／`tool-output-*`／`source-*`／`error`／`finish`／`abort`）；收尾的 `data: [DONE]` 与 `x-vercel-ai-ui-message-stream: v1`；**`reset-step`「重试时先让失败那一次的局部输出失效」**——8.3.6 那张对照表的出处，也是 8.3.5 里「重试没清 partial」在框架侧的解法 | Vercel AI SDK · Stream Protocols | https://ai-sdk.dev/docs/ai-sdk-ui/stream-protocol |
| **框架知道什么、不知道什么**：`status` 的四个值（`submitted`／`streaming`／`ready`／`error`）、`stop()` 与 `regenerate()`（前者会 abort 掉那次 fetch 并把状态复位）、`onFinish` 回调里的 `isAbort`／`isDisconnect`／`isError`、以及 `throttle` 节流——8.3.6 里「断线重连与去重仍然是你的账」这一条的出处 | Vercel AI SDK · Chatbot（`useChat`） | https://ai-sdk.dev/docs/ai-sdk-ui/chatbot |
| **`EventSource` 的两条硬边界**：非 HTTP/2 时**每浏览器＋每域名 6 条连接**（HTTP/2 默认 100）、`readyState` 的三个值与 `close()`——8.3.1 那张协议对照表最后一列的出处 | MDN · EventSource | https://developer.mozilla.org/en-US/docs/Web/API/EventSource |
| **代理为什么要单独说一句**：`proxy_buffering` 的默认值是 **`on`**；关掉时响应**同步、收到即转发**；而它**可由响应头 `X-Accel-Buffering: yes/no` 单独开关**——8.3.2 里「同一份代码两种命」那一组的出处（`proxy_read_timeout` 默认 **60 秒**也在同一页，8.3.3 的心跳档位按它建模） | Nginx · ngx_http_proxy_module | https://nginx.org/en/docs/http/ngx_http_proxy_module.html |
| 前端流式对话（8.3 章） | Vercel AI SDK 文档 | https://ai-sdk.dev/docs/introduction |
| 前端框架（8.3 章） | Next.js 官方文档 | https://nextjs.org/docs |
| 鉴权与多租户（8.4 章） | FastAPI · Security | https://fastapi.tiangolo.com/tutorial/security/ |
| **OpenAPI 有哪几种安全方案、FastAPI 为什么照它们实现**：`apiKey`（query／header／cookie）、`http` 里的 `bearer`（`Authorization: Bearer <token>`）、`oauth2` 的四种 flow、`openIdConnect`；以及 `fastapi.security` 这一个模块就提供这些工具（8.4.1 「谁在说话」那一步的出处——**认人不认租户，租户是从认出来的那个人身上查出来的**） | FastAPI · Security | https://fastapi.tiangolo.com/tutorial/security/ |
| **作用域（scopes）与「该调用方能做什么」**：`Security(..., scopes=[...])` 把权限声明式地挂在依赖上、依赖里能读出这个 key 被授予了哪些 scope，OpenAPI 里也能看到——8.4.4 分层配额里「key 这一层还带能力标签」那一格的出处 | FastAPI · OAuth2 scopes | https://fastapi.tiangolo.com/advanced/security/oauth2-scopes/ |
| **行了级隔离的默认方向是「拒绝」**：`ALTER TABLE ... ENABLE ROW LEVEL SECURITY` 之后，所有正常访问都**必须被策略允许**，而「如果表上没有任何策略，则用默认拒绝——没有任何行可见、也不可修改」；多条 permissive 之间按 **OR** 合并、restrictive 之间按 **AND**；**表属主默认绕过**（除非 `FORCE ROW LEVEL SECURITY`），超级用户与 `BYPASSRLS` 角色也绕过；而 `TRUNCATE`／`REFERENCES` 这类整表操作**不受行安全约束**——8.4.2 里「忘了带 `tenant_id` 的查询由谁拦住」那三行的出处 | PostgreSQL · Row Security Policies | https://www.postgresql.org/docs/current/ddl-rowsecurity.html |
| **向量库的四级隔离与它们各自的天花板**：数据组织是 **Database → Collection → Partition/Partition Key** 三层；库级隔离最好而**不活跃的租户白占资源**；集合级两种做法（全租户一集合＋按字段过滤，租户一多就撞性能；一租户一集合，受集合上限）；分区级两种（一租户一分区，受**分区数上限**；partition key，最可扩展**但不支持批量写入**）——8.4.2 那张「同一件事在向量库里的等价物」的出处 | Zilliz · Designing Multi-Tenancy RAG with Milvus | https://zilliz.com/blog/build-multi-tenancy-rag-with-milvus-best-practices-part-one |
| **429 与 `Retry-After`**：这个状态码的意思是「客户端在给定时间里发了太多请求」；`Retry-After` 用的单位是秒（例子里 `Retry-After: 3600`）；限流可以是**全站**的也可以是**按资源**的，而「通常按 IP，但认证过之后可以按用户或按已授权的应用」——8.4.4 里「超限的三种回答」那张表的出处（RFC 6585 §4） | MDN · 429 Too Many Requests | https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Status/429 |
| **限流器与负载卸载是两件事**：限流器按**用户**决策（「如果你能接受用户改变请求节奏，限流器就合适」），负载卸载按**系统整体状态**决策（事故中保住核心请求）；Stripe 生产在跑四种：请求速率限制器（最要紧的那个）、**并发请求限制器**（「同一时刻最多 20 条在进行中」——它管的是 CPU 密集型端点的资源争抢，且「调紧一点、拒得比速率限制器更频繁是完全合理的」）、fleet 预留卸载器（给关键方法留 20%，超过的部分回 503）、worker 利用率卸载器（四级优先级、**来回放量要慢，否则会 flapping**）；另一句要点：**测试模式与生产模式用同一条限流** | Stripe · Scaling your API with rate limiters | https://stripe.com/blog/rate-limiters |
| **「缺上限」本身就是一类 API 风险**：资源消费不受限被列为 API 风险的第四位，判据是**缺任一条上限即脆弱**——执行超时、可分配内存、文件描述符数、进程数、上传体积、单请求里的操作数（如批处理）、单页返回条数、**第三方服务商的预算上限**；两个场景直接可用：SMS 那条 0.05 美元一次的调用被脚本刷到「几分钟损失几千美元」、GraphQL 批处理**绕过按请求数的限流**（一次 HTTP 请求装 999 个 mutation）——8.4.3 「按请求数是最容易被绕开的一种」那两行的出处 | OWASP · API4:2023 Unrestricted Resource Consumption | https://owasp.org/API-Security/editions/2023/en/0xa4-unrestricted-resource-consumption/ |
| **计费侧的三个现成名词**：按用量计费靠**上报用量**（meter events）累计、**额度**（credits）用于预付与促销、以及**用量阈值告警**（「客户超过某个用量线时告警」）——8.4.5 的预扣／额度、8.4.6 的余额线与对账，出处都在这一页的三条入口上 | Stripe · Basic usage-based billing | https://docs.stripe.com/billing/subscriptions/usage-based |
| 可观测性与告警（8.5 章） | OpenTelemetry 官方文档 | https://opentelemetry.io/docs/ |
| **SLI 与 SLO 的定义**：SLI 是「对服务行为的度量」，而「**好的 SLI 从用户的视角量你的服务**」；SLO 是把一个或多个 SLI 接上业务价值来沟通可靠性；以及那句判据句——「一个系统可以 100% 可用，而用户点「加入购物车」时那双黑色的鞋没被加进去，那它仍然不可靠」（8.5.1 那张表与「四层叠起来才是『用户没事』」的出处） | OpenTelemetry · Observability primer | https://opentelemetry.io/docs/concepts/observability-primer/ |
| **四类信号各自是什么**：traces（请求在应用里的路径）、metrics（运行时的一次度量）、logs（一次事件的记录）、baggage（信号之间传递的上下文）；另有一句「可观测性让你从外部提问，而不用先知道它的内部构造」（8.5.1 「SLI 是从那些信号里挑出来的一个数」的出处） | OpenTelemetry · Signals | https://opentelemetry.io/docs/concepts/signals/ |
| **燃尽率的算法与窗口的形状**：燃尽率 ＝ 观测错误率 ÷ 理想错误率（理想错误率就是 1 − SLO）；14.4 那一档配的是「过去 1 小时 / 过去 5 分钟」与 30 天目标；**短窗取长窗的 1/12**（这一条在三个档位上都能对上：1 小时/5 分钟、6 小时/30 分钟、3 天/6 小时）；以及那条天花板——**最大燃尽率 ＝ 1/(1 − SLO)**，SLO 越低能设的阈值越小（8.5.3 那张三档表与「同一个错误率在新 SLO 下更不严重」这条判据的出处） | Datadog · Burn rate alerts（转引 SRE Workbook） | https://docs.datadoghq.com/service_level_objectives/burn_rate/ |
| **燃尽率与多窗口多燃尽率那套工作法的出处**：那一章给的三档建议是 2%／5%／10% 的预算，对应 14.4／6／1 三个燃尽率与三种处置（立刻叫醒／开单／进排期）；注：**这一页在当前网络下 TLS 校验不通过**，本章的窗口与百分比经上面那一页转引核对 | Google SRE Workbook · Alerting on SLOs | https://sre.google/workbook/alerting-on-slos/ |
| **告警该改什么**：按**症状**告警而不是按原因（「按与用户痛点相关的症状告警，而不是试图抓每一种可能的成因」）；「**避免那些无事可做的告警**」；容量类要人介入（它不造成即时影响，但不处理就是一次将到的故障）；批任务的阈值取两轮；以及元监控（监控自己也要有告警）——8.5.3 那一整节与噪声账的出处 | Prometheus · Alerting practices | https://prometheus.io/docs/practices/alerting/ |
| **容量与主动故障的预算**：一段应用「不要因为主动驱逐而把服务容量降掉超过 10%」（例子里就是 `minAvailable: 90%`）；百分比**向上取整**；而最要紧的是那句边界——「**预算只能防主动驱逐，防不了所有不可用的成因**」（节点挂了、或预算正在最小尺寸时出事，照样掉下去）；一行 `maxUnavailable: 0%` 等于要求零驱逐——8.5.4 与 8.5.6 「挂一台之后还剩多少」那一栏的出处 | Kubernetes · Specifying a disruption budget | https://kubernetes.io/docs/tasks/run-application/configure-pdb/ |
| **演练的四步与六条原则**：先定义**稳态**（可量的输出，不是内部属性）、再假设稳态会在对照组与实验组里继续、再引入**真实世界的事件**、最后试图**推翻**假设；原则里的三条直接可用：**在生产上做**（系统的行为随环境与流量而变，只有真实流量能追出请求路径）、**缩小影响面**、**自动化并持续跑**——8.5.5 四种演练的判据与「判据是发现了什么」的出处 | Principles of Chaos Engineering | https://principlesofchaos.org/ |
| **演练单的三件东西**：一次实验有**动作**（对资源做什么、持续多久）、**目标**（对哪一批资源做）、**停止条件**（越线自动停，就是护栏）；以及那句要紧的提醒——「它对真实资源做真实操作，所以在生产上跑之前**先做规划阶段、并在预发环境跑一遍**」——8.5.5 那张演练单与「先预发再生产」的出处 | AWS · Fault Injection Service | https://docs.aws.amazon.com/fis/latest/userguide/what-is.html |
| **可用性要能被测量、能被算**：这份白皮书把「可用性」当成一个可以用数学证明的东西，「最好的设计配上良好的意愿也可能达不到预期，所以你需要测量它的机制」——8.5.1 「四个数是算出来的」与 8.5.2「两个数一起报」的出处 | AWS · Availability and Beyond（白皮书） | https://docs.aws.amazon.com/whitepapers/latest/availability-and-beyond-improving-resilience/availability-and-beyond-improving-resilience.html |
| **队列与利用率的非线性**：积压随利用率逼近上限而**加速**增长（同一个排队模型在 50% 与 90% 上是两条曲线），以及「重试本身也是一种队列」——8.5.6 那张利用率表与「按均值买机器」那一段的定性依据（本章的 `1/(1−ρ)` 是单服务台近似的写法，具体数由脚本算出） | AWS Builders' Library · Avoiding insurmountable queue backlogs | https://aws.amazon.com/builders-library/avoiding-insurmountable-queue-backlogs/ |

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
| **同一套工作法的官方入口**（页面里 Leadership Principles → Behavioral-based questions → The STAR method 四个相邻小节；另：技术岗约一半时间在技术评估、另一半在行为面） | Amazon · Interview Loop | https://amazon.jobs/content/en/how-we-hire/interview-loop |
| **「六秒」与「七点四秒」的来处**：一份眼动研究——招聘者平均只在一份简历上停 **7.4 秒**，而「赢得注意力的那几份有一个共同点：简单版面」（2018 年那次跟踪的结论，2012 那一版给的是 **6 秒**）；注：**原文与转载页在当前网络下 403**，本章那句时长经这份被波士顿大学托管的报告 PDF 核对 | TheLadders · Eye-Tracking Study | https://www.bu.edu/com/files/2018/10/TheLadders-EyeTracking-StudyC2.pdf |
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
| 训练算力最优配比（3.1 章） | Training Compute-Optimal Large Language Models (Chinchilla, 2022) | https://arxiv.org/abs/2203.15556 |
| 涌现能力（3.1 章） | Emergent Abilities of Large Language Models (2022) | https://arxiv.org/abs/2206.07682 |
| 涌现能力的替代解释（3.1 章） | Are Emergent Abilities of Large Language Models a Mirage? (2023) | https://arxiv.org/abs/2304.15004 |
| 旋转位置编码（3.1 章） | RoFormer: Enhanced Transformer with Rotary Position Embedding (RoPE, 2021) | https://arxiv.org/abs/2104.09864 |
| KV 缓存管理与服务吞吐（3.1 章） | Efficient Memory Management for LLM Serving with PagedAttention (vLLM, SOSP 2023) | https://arxiv.org/abs/2309.06180 |
| 思维链（3.2 章） | Chain-of-Thought Prompting Elicits Reasoning in LLMs (2022) | https://arxiv.org/abs/2201.11903 |
| 零样本思维链（3.2 章） | Large Language Models are Zero-Shot Reasoners (2022) | https://arxiv.org/abs/2205.11916 |
| 自一致性：采样多条路径后边际化投票（3.2 章） | Self-Consistency Improves Chain of Thought Reasoning in Language Models (2022) | https://arxiv.org/abs/2203.11171 |
| 思维树：在思想单元上生成、评估与搜索（3.2 章） | Tree of Thoughts: Deliberate Problem Solving with LLMs (2023) | https://arxiv.org/abs/2305.10601 |
| 无外部信号的自我纠错不可靠（3.2 章） | Large Language Models Cannot Self-Correct Reasoning Yet (2023) | https://arxiv.org/abs/2310.01798 |
| 思维链解释可能与真实原因不符（3.2 章） | Language Models Don't Always Say What They Think (2023) | https://arxiv.org/abs/2305.04388 |
| 提示格式敏感度：仅改格式造成 76 个准确率点差距（3.2 章） | Quantifying Language Models' Sensitivity to Spurious Features in Prompt Design (2023) | https://arxiv.org/abs/2310.11324 |
| ReAct：推理与行动交替、ALFWorld +34% 与 WebShop +10%（3.3–3.5 章） | ReAct: Synergizing Reasoning and Acting in Language Models (2022) | https://arxiv.org/abs/2210.03629 |
| 工具学习（3.5 章） | Toolformer (2023) | https://arxiv.org/abs/2302.04761 |
| 检索增强的 API 调用；幻觉参数是主要失败模式（3.5 章） | Gorilla: Large Language Model Connected with Massive APIs (2023) | https://arxiv.org/abs/2305.15334 |
| 自我反思与迭代（3.4 章） | Reflexion: Language Agents with Verbal Reinforcement Learning (2023) | https://arxiv.org/abs/2303.11366 |
| 先制定计划再解题的提示写法（3.4 章） | Plan-and-Solve Prompting: Improving Zero-Shot Chain-of-Thought Reasoning (2023) | https://arxiv.org/abs/2305.04091 |
| LLM Agent 规划的五个方向：任务分解 / 计划选择 / 外部模块 / 反思 / 记忆（3.4 章） | Understanding the planning of LLM agents: A survey (2024) | https://arxiv.org/abs/2402.02716 |
| 经典规划任务上 LLM 的规划能力仍差得远；常识任务上难以区分「在规划」与「在检索」（3.4 章） | PlanBench: An Extensible Benchmark for Evaluating LLMs on Planning and Reasoning about Change (NeurIPS 2023) | https://arxiv.org/abs/2206.10498 |
| RAG 原始论文（5.1 章） | Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks (2020) | https://arxiv.org/abs/2005.11401 |
| 长上下文与位置敏感（2.1、3.6、5.2、5.4 章） | Lost in the Middle (2023) | https://arxiv.org/abs/2307.03172 |
| 上下文分层管理的早期系统化尝试：分页、换入换出（3.6 章） | MemGPT: Towards LLMs as Operating Systems (2023) | https://arxiv.org/abs/2310.08560 |
| 记忆流 + 重要性打分 + 定期反思的写入侧设计（3.6 章） | Generative Agents: Interactive Simulacra of Human Behavior (2023) | https://arxiv.org/abs/2304.03442 |
| 大模型多代理系统的结构、协作与评估综述；三类结构分类的另一种口径（3.7 章） | Large Language Model based Multi-Agents: A Survey of Progress and Challenges (2024) | https://arxiv.org/abs/2402.01680 |
| 间接注入的系统性演示：攻击者不直接对模型说话，而是把指令写进模型**会读到**的内容里（3.8 章） | Not what you've signed up for: Compromising Real-World LLM-Integrated Applications with Indirect Prompt Injection (2023) | https://arxiv.org/abs/2302.12173 |
| 包幻觉与仿冒投递（2.1、7.4 章） | We Have a Package for You! A Comprehensive Analysis of Package Hallucinations by Code Generating LLMs (USENIX Security 2025) | https://arxiv.org/abs/2406.10279 |
| AI 助手与不安全代码（2.1、7.4 章） | Do Users Write More Insecure Code with AI Assistants? (CCS 2023) | https://arxiv.org/abs/2211.03622 |
| 生成式 AI 与批判性思考（2.1 章） | The Impact of Generative AI on Critical Thinking (CHI 2025) | https://www.microsoft.com/en-us/research/publication/the-impact-of-generative-ai-on-critical-thinking-self-reported-reductions-in-cognitive-effort-and-confidence-effects-from-a-survey-of-knowledge-workers/ |
| **反思令牌**：`Retrieve`／`IsREL`／`IsSUP`／`IsUSE` 四个令牌与它们的取值空间（5.5 章） | Self-RAG: Learning to Retrieve, Generate and Critique through Self-Reflection (2023) | https://arxiv.org/abs/2310.11511 |
| **评估—分档—动作三步，以及「有一片够高就是 Correct」这条汇总写法**（5.5 章） | Corrective Retrieval Augmented Generation (CRAG, 2024) | https://arxiv.org/abs/2401.15884 |
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
