# Fast API的介绍和环境准备

> **素材来源**：`raw/FastAPI基础学习文档/FastAPI基础学习文档\01Fast API的介绍和环境准备\Fast API的介绍和环境准备.pdf`
> **页数**：13（其中无文本页 1 页，多为截图/图示）
> **正文规模**：约 9,042 字符，其中汉字 2,115 个
> **说明**：本文件由 `tools/extract_sources.py` 自动抽取，仅作写书素材，未做人工校订；引用时请以原文为准。

---
<!-- p.1 -->

特点 说明
高性能 可与 NodeJS 和 Go 比肩（归功于 Starlette 和 Pydantic）
高效编码 通过自动数据验证、交互式文档生成和直观的 API 设计，大幅提升开发效率
更少 Bug
依托 Pydantic 的运行时验证和强类型系统，有效减少因数据类型错误导致的运行
时异常
类型提示 利用 Python 的类型提示，提供严格的输入验证
自动文档 自动生成 Swagger UI 和 ReDoc 交互式文档
异步支持 支持异步请求处理，高效处理 IO 密集型任务
数据验证 使用 Pydantic 进行数据验证和序列化
依赖注入 内置依赖注入系统，代码更模块化
WebSocket 原生支持 WebSocket，适用于实时通信
认证支持 内置 OAuth2 和 JWT 认证支持
中间件 支持 CORS、GZip、静态文件等中间件
框架 特点 适用场景
FastAPI 高性能、自动文档、类型提示 API 微服务、高并发场景、数据验证
Flask 轻量、灵活、扩展丰富 简单应用、原型开发、微型服务
FastAPI 的介绍和环境准备
FastAPI 介绍
FastAPI 是一个用于构建 API 的现代、快速（高性能）web 框架，专为在 Python 中构建 RESTful API 而
设计。
FastAPI 已在许多应用程序和系统的生产环境中使用，测试覆盖率保持 100%。框架仍在快速迭代中，定
期添加新功能和修复问题。
版本提示：FastAPI 发展迅速，建议查看官方仓库了解最新的 Python 版本要求和功能更新。
FastAPI 特点
FastAPI 适用场景
API 后端：构建 RESTful API，支持前后端分离
微服务：作为微服务后端框架，支持快速开发和部署
数据处理：处理和返回 JSON 数据
实时通信：WebSocket 支持实时应用
FastAPI vs Flask vs Django

---

<!-- p.2 -->

框架 特点 适用场景
Django 全功能、管理后台、内置 ORM 复杂应用、网站、后台管理系统
层级 技术 说明
展示层 Jinja2、API 交互 模板渲染和 API 请求
框架层 Starlette Web 服务核心
数据层 Pydantic 数据模型、验证、序列化
ORM 层 SQLAlchemy、Tortoise 数据库交互
运行层 Uvicorn ASGI 服务器
部署层 Docker 容器化部署
资源 链接
官方文档 https://fastapi.tiangolo.com/
GitHub 仓库 https://github.com/fastapi/fastapi
中文社区 https://fastapi.tiangolo.com/zh/
技术栈架构
FastAPI 基于以下核心技术构建：
学习资源
环境准备
Python 版本要求
FastAPI 依赖 Python 3.8 及更高版本，具体版本要求请查看官方仓库。
安装 FastAPI
推荐安装方式：
# 检查 Python 版本
python --version
# 安装 FastAPI 标准版（推荐）
pip install "fastapi[standard]"
# 安装所有可选依赖
pip install "fastapi[all]"

---

<!-- p.3 -->

安装 ASGI 服务器
FastAPI 本身不包含 Web 服务器，需要安装 ASGI 服务器：
虚拟环境管理
使用 venv（推荐）
使用 Conda
# 推荐使用 Uvicorn
pip install "uvicorn[standard]"
# 或使用 Hypercorn
pip install hypercorn
# 创建虚拟环境
python -m venv .venv
# 激活虚拟环境
# Windows
.venv\Scripts\activate
# Linux/Mac
source .venv/bin/activate
# 安装依赖
pip install "fastapi[standard]" "uvicorn[standard]"
# 创建 conda 环境
conda create --name fastapi-env python=3.11
# 激活环境
conda activate fastapi-env
# 安装依赖
pip install "fastapi[standard]" "uvicorn[standard]"

---

<!-- p.4 -->

使用 uv（推荐，现代化工具）
第一个 FastAPI 应用
创建项目
项目结构：
创建 requirements.txt ：
安装依赖：
编写代码
创建 main.py ：
# 安装 uv
pip install uv
# 创建项目
uv init myproject
cd myproject
# 添加依赖
uv add fastapi uvicorn
# 运行
uv run uvicorn main:app --reload
fastapi-project/
├── main.py
└── requirements.txt
fastapi
uvicorn
# 安装所有依赖
pip install -r requirements.txt
# 或分别安装
pip install fastapi uvicorn
from fastapi import FastAPI
app = FastAPI()
@app.get("/")
def read_root():
return {"Hello": "World"}

---

<!-- p.5 -->

参数 说明 示例
--reload 文件变化时自动重载 uvicorn main:app --reload
--host 绑定主机地址 uvicorn main:app --host 0.0.0.0
--port 监听端口 uvicorn main:app --port 8000
--workers 工作进程数 uvicorn main:app --workers 4
运行应用
方式一：命令行运行
方式二：在代码中启动
常用 Uvicorn 参数：
启动成功后会看到：
注意： --workers 不能与 --reload 同时使用。
访问应用
首页： http://127.0.0.1:8000/
Swagger UI： http://127.0.0.1:8000/docs
ReDoc： http://127.0.0.1:8000/redoc
OpenAPI JSON： http://127.0.0.1:8000/openapi.json
uvicorn main:app --reload
from fastapi import FastAPI
import uvicorn
app = FastAPI()
@app.get("/hi")
def greet():
return "Hello, World!"
if __name__ == "__main__":
uvicorn.run("main:app", reload=True)
INFO: Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO: Started reloader process [xxxxx] using StatReload
INFO: Started server process [xxxxx]
INFO: Waiting for application startup.
INFO: Application startup complete.

---

<!-- p.6 -->

代码 说明
from fastapi import FastAPI 导入 FastAPI 类
app = FastAPI() 创建 FastAPI 应用实例
@app.get("/") 定义 GET 请求路由
def greet() 路由处理函数
return {"Hello": "World"} 返回 JSON 响应
代码解析
路径参数和查询参数
路径参数
路径参数是 URL 的一部分，用 {} 包裹，FastAPI 会自动提取并做类型校验：
访问 /items/5 返回 {"item_id": 5}
FastAPI 会自动将 item_id 转换为 int 类型；如果传入 /items/foo ，会返回清晰的 422 错误，
而不是崩溃
查询参数
查询参数是 URL 中 ? 后面的键值对，没有 {} 包裹，通过函数参数直接定义：
访问 /items/?skip=20&limit=50 返回 {"skip": 20, "limit": 50}
带默认值的参数为可选，不带默认值则为必填
FastAPI 同样会对查询参数进行类型校验和转换
from fastapi import FastAPI
app = FastAPI()
@app.get("/items/{item_id}")
def read_item(item_id: int):
return {"item_id": item_id}
from fastapi import FastAPI
app = FastAPI()
@app.get("/items/")
def read_items(skip: int = 0, limit: int = 10):
return {"skip": skip, "limit": limit}

---

<!-- p.7 -->

混合使用
路径参数和查询参数可以同时使用：
访问 /items/5?q=test 返回 {"item_id": 5, "q": "test"}
访问 /items/5 返回 {"item_id": 5, "q": null} （查询参数为 None ，返回 JSON 时表现为
null ）
完整示例
下面是一个包含多种请求方式的综合示例，涵盖 GET、POST、路径参数、查询参数、请求体和异常处
理：
from fastapi import FastAPI
app = FastAPI()
@app.get("/items/{item_id}")
def read_item(item_id: int, q: str | None = None):
return {"item_id": item_id, "q": q}
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
# 创建 FastAPI 应用，并配置文档页面标题和版本
app = FastAPI(
title="商品管理 API",
description="一个完整的 FastAPI 示例应用",
version="1.0.0"
)
# 定义 Pydantic 模型，用于验证请求体（POST /items/ 时接收的 JSON）
class Item(BaseModel):
name: str # 必填字段
description: Optional[str] = None # 可选字段，默认 None
price: float # 必填字段
tax: Optional[float] = None # 可选字段，默认 None
# 模拟数据库：用字典存储商品数据（实际项目中替换为真实数据库）
items_db = {}
# GET / - 根路径
@app.get("/")
def root():
return {"message": "Hello World"}
# GET /items/{item_id} - 获取单个商品
@app.get("/items/{item_id}")
def read_item(item_id: int, q: Optional[str] = None):
# FastAPI 自动校验 item_id 必须为整数，否则返回 422
if item_id not in items_db:

---

<!-- p.8 -->

Pydantic 版本注意：本示例使用 model_dump() （Pydantic v2）。如果使用 Pydantic v1，请将
item.model_dump() 替换为 item.dict() 。
项目最佳实践
推荐项目结构
# 商品不存在时抛出 404 异常
raise HTTPException(status_code=404, detail="商品不存在")
# 合并返回 item_id、数据库中的商品信息，以及可选的查询参数 q
return {"item_id": item_id, **items_db[item_id], "q": q}
# POST /items/ - 创建新商品
@app.post("/items/")
def create_item(item: Item):
# FastAPI 根据 Pydantic 模型自动校验请求体，格式不对直接返回 422
item_id = len(items_db) + 1
# model_dump() 将 Pydantic 模型转为普通字典（v2 API，v1 用 .dict()）
items_db[item_id] = item.model_dump()
return {"item_id": item_id, **items_db[item_id]}
# GET /users/{user_id}/items/{item_id} - 获取指定用户的商品
@app.get("/users/{user_id}/items/{item_id}")
def read_user_item(
user_id: int,
item_id: int,
q: Optional[str] = None,
short: bool = False
):
item = {"item_id": item_id, "owner_id": user_id}
if q:
item["q"] = q
if not short:
item["description"] = "这是一个示例商品"
return item
fastapi-project/
├── app/
│ ├── __init__.py
│ ├── main.py # 应用入口
│ ├── config.py # 配置管理
│ ├── database.py # 数据库连接
│ ├── dependencies.py # 依赖注入
│ ├── models/ # 数据库模型
│ │ ├── __init__.py
│ │ ├── item.py
│ │ └── user.py
│ ├── schemas/ # Pydantic 模型
│ │ ├── __init__.py
│ │ ├── item.py
│ │ └── user.py
│ └── routers/ # 路由模块
│ ├── __init__.py

---

<!-- p.9 -->

方式 说明 资源消耗
多进程 每个请求一个进程，隔离性强，但开销大 高
多线程 每个请求一个线程，GIL 限制 CPU 密集型任务 中等
开发工作流
1. 创建并激活虚拟环境
2. 安装依赖
3. 生成依赖文件
注意： pip freeze 会锁定所有已安装的包（包括传递依赖），实际项目中建议使用 pip-tools
或 pipreqs 只记录直接依赖，避免依赖膨胀。
4. 运行开发服务器
注意： main:app 表示从 main.py 文件中导入名为 app 的 FastAPI 实例。
5. 访问文档
打开浏览器访问 http://localhost:8000/docs 测试 API。
FastAPI 为什么这么快？
并发模型对比
│ ├── items.py
│ └── users.py
├── tests/ # 测试文件
│ ├── __init__.py
│ ├── test_items.py
│ └── test_users.py
├── requirements.txt
├── .env # 环境变量
└── .gitignore
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/Mac
source .venv/bin/activate
pip install "fastapi[standard]" "uvicorn[standard]"
pip freeze > requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000

---

<!-- p.10 -->

方式 说明 资源消耗
协程（async/await） 单线程内通过事件循环切换任务，轻量高效 低
概念 说明
协程（Coroutine） 可暂停和恢复的函数，用 async def 定义，核心是 await
异步（Async） 基于协程的非阻塞编程模式，通过事件循环调度多个协程
用途 依赖包 安装命令 说明
数据库
ORM
SQLAlchemy
（异步）
pip install
sqlalchemy[asyncio]
推荐用于 FastAPI 异步项
目
Tortoise ORM pip install tortoise-orm 纯异步 ORM，内置分页
数据库驱
动
asyncpg pip install asyncpg PostgreSQL 异步驱动
aiomysql pip install aiomysql MySQL 异步驱动
数据库迁
移
Alembic pip install alembic
SQLAlchemy 数据库版本
管理
FastAPI 默认使用协程模型，在处理大量 IO 密集型请求（如数据库查询、HTTP 调用）时表现优
异。
什么是协程？
协程是一种可以暂停执行、稍后恢复的特殊函数。与普通函数不同，协程在遇到 IO 操作时会让出执行
权，允许其他任务继续运行，从而在单线程内实现并发。
协程与异步的关系：
基本语法
常用依赖推荐
import asyncio
async def fetch_data():
# 模拟 IO 操作（如网络请求），await 会让出执行权
await asyncio.sleep(1)
return {"data": "result"}
async def main():
result = await fetch_data()
print(result)
asyncio.run(main())

---

<!-- p.11 -->

用途 依赖包 安装命令 说明
认证 passlib
pip install
passlib[bcrypt]
密码哈希（推荐替代
bcrypt）
PyJWT pip install pyjwt JWT 令牌生成与验证
环境变量
pydantic-
settings
pip install pydantic-
settings
Pydantic v2 原生配置管
理
异步 HTTP
客户端
httpx pip install httpx
支持同步/异步请求，测
试客户端
aiohttp pip install aiohttp 纯异步 HTTP 客户端
缓存 redis
pip install
redis[hiredis]
Redis 异步客户端，
hiredis 提升性能
邮件 aiosmtplib pip install aiosmtplib 异步 SMTP，发送邮件
模板渲染 jinja2 pip install jinja2
模板引擎（可选，非 API
必选）
CORS 内置 无需安装
FastAPI 已内置 CORS 中
间件
测试 pytest
pip install pytest
pytest-asyncio
单元测试框架
httpx pip install httpx ASGI 测试客户端
分页 内置 无需安装 FastAPI 支持内置分页
API 文档
增强
favicon 无需安装
自动从 /favicon.ico
读取
序号 内容 关键命令
1 环境准备 安装 Python 3.8+，使用 venv / conda / uv 管理虚拟环境
2 安装 FastAPI pip install "fastapi[standard]" "uvicorn[standard]"
3 创建应用 在 main.py 中实例化 FastAPI() ，用装饰器定义路由
4 运行服务 uvicorn main:app --reload
5 访问文档 打开 http://localhost:8000/docs 使用 Swagger UI
提示：实际项目中按需安装，不必全部引入。使用 uv add <package> 或 pip install
<package> 逐个添加。
总结
核心要点

---

<!-- p.12 -->

序号 内容 关键命令
6 参数处理 路径参数用 {} ，查询参数直接作为函数参数，请求体用 Pydantic 模型
7 项目结构 采用 app/routers 、 app/models 、 app/schemas 模块化分层
8 性能优势 基于 Starlette + Pydantic，默认协程模型，支持高并发 IO 场景
后续学习方向
请求体与数据验证：深入学习 Pydantic 模型、嵌套字段、字段校验
数据库集成：SQLAlchemy + Alembic 数据库迁移
认证授权：JWT + OAuth2 实现登录和权限控制
依赖注入：使用 Depends() 提取复用逻辑
部署上线：Docker 容器化 + Nginx 反向代理 + Gunicorn/Uvicorn 多进程
