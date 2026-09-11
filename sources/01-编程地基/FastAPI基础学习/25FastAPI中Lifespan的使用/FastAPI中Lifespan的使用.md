# FastAPI中Lifespan的使用

> **素材来源**：`raw/FastAPI基础学习文档/FastAPI基础学习文档\25FastAPI中Lifespan的使用\FastAPI中Lifespan的使用.pdf`
> **页数**：8（其中无文本页 1 页，多为截图/图示）
> **正文规模**：约 8,042 字符，其中汉字 887 个
> **说明**：本文件由 `tools/extract_sources.py` 自动抽取，仅作写书素材，未做人工校订；引用时请以原文为准。

---
<!-- p.1 -->

FastAPI 中 Lifespan 的使用
Lifespan 是 FastAPI 0.104+ 引入的应用生命周期管理机制，用于替代旧版的
@app.on_event("startup") 与 @app.on_event("shutdown") 装饰器（旧方式仍兼容，但官方推荐
使用 Lifespan）。用于在应用启动时初始化资源、在应用关闭时清理资源。
核心思想：通过 @asynccontextmanager 装饰的异步函数（或 @contextmanager 装饰的同步函数）
作为异步上下文管理器， yield 之前是应用启动阶段（初始化资源）， yield 之后是应用关闭阶段
（清理资源）。FastAPI 优先推荐异步实现。
基本用法
核心组件：
应用启动
↓
yield 之前（startup）—— 初始化资源：连接数据库、加载配置、建立连接池
↓
处理请求 ←———————————— 路由正常工作
↓
yield 之后（shutdown）—— 释放资源：关闭连接池、保存缓存、关闭客户端
↓
应用退出
from fastapi import FastAPI
from contextlib import asynccontextmanager
from datetime import datetime
@asynccontextmanager
async def lifespan(app: FastAPI):
# —— Startup 阶段（yield 之前）——
app.state.startup_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S") # 存
入 app.state，全局可访问
app.state.counter = 0 # 请求计数器
yield # ← 分界线
# —— Shutdown 阶段（yield 之后）——
print(f"共处理 {app.state.counter} 个请求")
app = FastAPI(lifespan=lifespan)
@app.get("/")
async def root():
app.state.counter += 1
return {"message": "Hello World", "startup_time": app.state.startup_time}

---

<!-- p.2 -->

组件 作用
@asynccontextmanager 将函数转为异步上下文管理器，支持 async with 语法
yield 分界线：之前是 startup，之后是 shutdown
app.state.xxx
应用级状态存储，生命周期内全局共享。
⚠️ 仅存储「全局资源」（如引擎、连接池），不存储请求级 / 临时
数据，避免线程安全问题
注意： yield 之后（shutdown）的代码在应用正常关闭时必定会执行（如优雅退出、Ctrl+C）；
若应用被强制终止（如 kill -9），则无法执行。
场景一：数据库连接池 + Redis
首先创建ORM。
在 startup 阶段初始化数据库和 Redis，存入 app.state 供路由使用；在 shutdown 阶段逆序关闭
（后初始化的资源先关闭，避免依赖资源已释放导致错误）。
# models.py
from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()
class Item(Base):
__tablename__ = "items"
id = Column(Integer, primary_key=True, index=True)
name = Column(String, index=True)
description = Column(String, nullable=True)
from fastapi import FastAPI, Depends, HTTPException
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession,
async_sessionmaker
from sqlalchemy import select
from pydantic import BaseModel
import redis.asyncio as redis
from models import Item
DATABASE_URL = "sqlite+aiosqlite:///./test.db"
@asynccontextmanager
async def lifespan(app: FastAPI):
# 初始化资源时捕获异常
try:
# —— Startup：初始化资源 ——
app.state.engine = create_async_engine(DATABASE_URL, echo=False)
app.state.async_session = async_sessionmaker(
app.state.engine, class_=AsyncSession, expire_on_commit=False

---

<!-- p.3 -->

)
async with app.state.engine.begin() as conn:
await conn.run_sync(Base.metadata.create_all)
app.state.redis = await redis.from_url("redis://localhost",
decode_responses=True)
except Exception as e:
print(f"启动阶段初始化资源失败：{e}")
raise # 抛出异常，终止应用启动（避免启动后资源缺失）
yield
# —— Shutdown：逆序关闭（先检查资源是否存在）——
if hasattr(app.state, "redis"):
try:
await app.state.redis.close()
except Exception as e:
print(f"关闭 Redis 失败：{e}")
if hasattr(app.state, "engine"):
try:
await app.state.engine.dispose()
except Exception as e:
print(f"关闭数据库引擎失败：{e}")
app = FastAPI(lifespan=lifespan)
# 每次请求创建新会话
async def get_db():
async with app.state.async_session() as session:
yield session
# —— 模型 ——
class ItemCreate(BaseModel):
name: str
description: str = ""
class ItemResponse(BaseModel):
id: int
name: str
description: str
class Config:
from_attributes = True
# —— 路由 ——
@app.post("/items", response_model=ItemResponse, status_code=201)
async def create_item(item: ItemCreate, db: AsyncSession = Depends(get_db)):
db_item = Item(name=item.name, description=item.description)
db.add(db_item)
await db.commit()
await db.refresh(db_item)

---

<!-- p.4 -->

资源管理流程：
场景二：在 Lifespan 中使用配置
将配置加载和资源初始化放在一起：
return db_item
@app.get("/items/{item_id}", response_model=ItemResponse)
async def get_item(item_id: int, db: AsyncSession = Depends(get_db)):
result = await db.execute(select(Item).where(Item.id == item_id))
item = result.scalar_one_or_none()
if not item:
raise HTTPException(status_code=404, detail="Item not found")
return item
# —— Redis 缓存 ——
@app.post("/cache/{key}")
async def set_cache(key: str, value: str):
await app.state.redis.set(key, value)
return {"key": key, "value": value}
@app.get("/cache/{key}")
async def get_cache(key: str):
value = await app.state.redis.get(key)
return {"key": key, "value": value}
startup 阶段
├─ create_async_engine() → 存入 app.state.engine
├─ async_sessionmaker() → 存入 app.state.async_session
└─ redis.from_url() → 存入 app.state.redis
↓
请求进来 → get_db() → async_session() → 得到 session
↓
shutdown 阶段（逆序）
├─ app.state.redis.close()
└─ app.state.engine.dispose()
# main.py
from fastapi import FastAPI
from contextlib import asynccontextmanager
from pydantic_settings import BaseSettings
import redis.asyncio as redis
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker,
AsyncSession
class Settings(BaseSettings):
database_url: str = "sqlite+aiosqlite:///./test.db"
redis_url: str = "redis://localhost"
debug: bool = False

---

<!-- p.5 -->

版本注意： pydantic >= 2.0 使用 from pydantic_settings import BaseSettings 。
场景三：多个资源的管理
多个资源在一个 Lifespan 中顺序初始化，关闭时逆序清理：
model_config = {"env_file": ".env"}
@asynccontextmanager
async def lifespan(app: FastAPI):
# 加载配置
settings = Settings()
# 初始化资源（使用配置）
app.state.engine = create_async_engine(settings.database_url,
echo=settings.debug)
app.state.redis = await redis.from_url(settings.redis_url,
decode_responses=True)
app.state.settings = settings # 也可以把配置存入 app.state
yield
# 关闭资源
await app.state.redis.close()
await app.state.engine.dispose()
app = FastAPI(lifespan=lifespan)
@app.get("/debug")
async def debug_mode():
# 从 app.state 读取配置
return {"debug": app.state.settings.debug}
from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import create_async_engine
import redis.asyncio as redis
async def create_db_pool():
"""模拟数据库连接池创建"""
engine = create_async_engine("sqlite+aiosqlite:///./test.db", echo=False)
return engine
async def create_redis_pool():
"""模拟Redis连接池创建"""
return await redis.from_url("redis://localhost", decode_responses=True)
async def create_message_queue():
"""模拟消息队列初始化（示例用简单对象）"""
class MockMQ:
async def close(self):
print("消息队列已关闭")

---

<!-- p.6 -->

原则：启动时按「依赖顺序」初始化（如先数据库、后依赖数据库的缓存），关闭时按「逆依赖顺序」
清理（先关缓存、后关数据库）；无依赖的资源可按任意顺序关闭。
测试 Lifespan
TestClient 会自动触发 lifespan，无需额外配置：
return MockMQ()
@asynccontextmanager
async def lifespan(app: FastAPI):
# 1. 连接数据库
app.state.db = await create_db_pool()
# 2. 连接 Redis
app.state.redis = await create_redis_pool()
# 3. 初始化消息队列
app.state.mq = await create_message_queue()
yield
# 逆序关闭：后启动的先关
await app.state.mq.close() # 先关消息队列
await app.state.redis.close() # 再关 Redis
await app.state.db.dispose() # 最后关数据库
# tests/test_lifespan.py
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from contextlib import asynccontextmanager
startup_calls = []
shutdown_calls = []
@asynccontextmanager
async def lifespan(app: FastAPI):
startup_calls.append("startup")
yield
shutdown_calls.append("shutdown")
@pytest.fixture
def client():
app = FastAPI(lifespan=lifespan)
@app.get("/")
async def root():
return {"status": "ok"}
with TestClient(app) as c:
yield c

---

<!-- p.7 -->

执行时机：
总结
完整生命周期：
def test_lifespan(client):
"""验证 startup 已执行"""
assert startup_calls == ["startup"]
response = client.get("/")
assert response.status_code == 200
with TestClient(app) as client:
↓
执行 lifespan yield 之前的代码（startup）
↓
client 可以发送请求
↓
退出 with 块
↓
执行 lifespan yield 之后的代码（shutdown）
Lifespan 核心要点：
定义方式 → @asynccontextmanager + yield 划分 startup/shutdown
资源存储 → app.state 用于全局共享（引擎、连接池、缓存）
会话注入 → Depends(get_db) 从 app.state 取会话工厂
关闭顺序 → shutdown 阶段逆序关闭
测试 → TestClient 自动触发 lifespan
┌──────────────────────────────────────────────────────────────┐
│ 应用启动 │
├──────────────────────────────────────────────────────────────┤
│ lifespan startup（yield 之前） │
│ 1. 创建数据库引擎 → app.state.engine │
│ 2. 创建会话工厂 → app.state.async_session │
│ 3. 创建 Redis 客户端 → app.state.redis │
├──────────────────────────────────────────────────────────────┤
│ 应用运行中（处理请求） │
│ 请求 → Depends(get_db) → async_session() → Session │
├──────────────────────────────────────────────────────────────┤
│ lifespan shutdown（yield 之后，逆序） │
│ 1. app.state.redis.close() │
│ 2. app.state.engine.dispose() │
└──────────────────────────────────────────────────────────────┘
