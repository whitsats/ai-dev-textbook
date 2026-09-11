# FastAPI中数据库连接池中间件的使用

> **素材来源**：`raw/FastAPI基础学习文档/FastAPI基础学习文档\20FastAPI的中间件（集合）\09FastAPI中数据库连接池中间件的使用\FastAPI中数据库连接池中间件的使用.pdf`
> **页数**：6（其中无文本页 1 页，多为截图/图示）
> **正文规模**：约 4,561 字符，其中汉字 669 个
> **说明**：本文件由 `tools/extract_sources.py` 自动抽取，仅作写书素材，未做人工校订；引用时请以原文为准。

---
<!-- p.1 -->

FastAPI 中数据库连接池中间件的使用
本节介绍如何使用中间件管理数据库连接生命周期。
什么是数据库连接池？
预先创建一组数据库连接，使用时从池中获取，用完归还，而不是每次请求都创建新连接。
使用 lifespan 管理连接（推荐方式）
FastAPI 0.104+ 推荐使用 lifespan 管理应用生命周期：
没有连接池：
请求1 → 创建连接 → 查询 → 关闭连接
请求2 → 创建连接 → 查询 → 关闭连接
请求3 → 创建连接 → 查询 → 关闭连接
有连接池：
启动时 → 根据配置创建 N 个初始连接（示例：10 个） → 放入池中（可配置最小/最大连接数、空闲超时
等）
请求1 → 从池中获取连接 → 查询 → 归还连接
请求2 → 从池中获取连接 → 查询 → 归还连接
...（复用已有连接，避免频繁创建/销毁连接的性能开销，性能更高）
from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
DATABASE_URL = "sqlite+aiosqlite:///./test.db"
# 创建异步引擎（包含连接池）
engine = create_async_engine(DATABASE_URL, echo=False)
# 创建会话工厂
async_session = sessionmaker(
engine, class_=AsyncSession, expire_on_commit=False
)
@asynccontextmanager
async def lifespan(app: FastAPI):
# 启动时：创建表
# （这里简化处理，实际项目中表应该单独管理）
yield
# 关闭时：释放所有连接
await engine.dispose()
app = FastAPI(lifespan=lifespan)

---

<!-- p.2 -->

lifespan 流程：
在路由中使用数据库
方式一：依赖注入（推荐）
方式二：中间件传递
通过中间件将数据库会话存入 request.state ：
应用启动 → lifespan(yield之前) → 处理请求 → 应用关闭 → lifespan(yield之后)
↓ ↑
连接数据库 断开数据库
from fastapi import FastAPI, Depends
from sqlalchemy.ext.asyncio import AsyncSession
app = FastAPI()
async def get_db():
"""获取数据库会话，用完自动关闭"""
async with async_session() as session:
yield session
@app.get("/users")
async def list_users(db: AsyncSession = Depends(get_db)):
"""获取用户列表"""
from sqlalchemy import select
from models import User
result = await db.execute(select(User))
users = result.scalars().all()
return users
from fastapi import FastAPI, Request
app = FastAPI()
@app.middleware("http")
async def db_session_middleware(request: Request, call_next):
# 每个请求创建一个会话
async with async_session() as session:
request.state.db = session
response = await call_next(request)
return response
@app.get("/users")
async def list_users(request: Request):
"""通过 request.state 获取数据库会话"""

---

<!-- p.3 -->

推荐方式一（依赖注入），更符合 FastAPI 设计理念。此方式每个请求创建独立会话，但无法灵活控制
会话作用域（如多个依赖复用会话），且不符合 FastAPI 依赖注入的设计理念，仅推荐简单场景临时使
用。
完整示例
项目结构
database.py
models.py
from sqlalchemy import select
from models import User
result = await request.state.db.execute(select(User))
users = result.scalars().all()
return users
app/
├── main.py # 应用入口
├── models.py # SQLAlchemy 模型
├── schemas.py # Pydantic 模型
└── database.py # 数据库配置
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
DATABASE_URL = "sqlite+aiosqlite:///./test.db"
Base = declarative_base()
engine = create_async_engine(DATABASE_URL, echo=False)
async_session = sessionmaker(
engine, class_=AsyncSession, expire_on_commit=False
)
from sqlalchemy import Column, Integer, String
from database import Base
class User(Base):
__tablename__ = "users"
id = Column(Integer, primary_key=True, index=True)
username = Column(String, unique=True, index=True)
email = Column(String, unique=True, index=True)

---

<!-- p.4 -->

main.py
总结
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import engine, async_session
from models import User, Base
@asynccontextmanager
async def lifespan(app: FastAPI):
# 创建表（仅首次运行/需要重建表时执行，生产环境建议用 Alembic 管理迁移）
try:
async with engine.begin() as conn:
await conn.run_sync(Base.metadata.create_all)
except Exception as e:
print(f"创建表失败: {e}")
raise
yield
# 关闭连接池
await engine.dispose()
app = FastAPI(lifespan=lifespan)
async def get_db():
async with async_session() as session:
yield session
@app.get("/users", response_model=list[dict])
async def list_users(db: AsyncSession = Depends(get_db)):
result = await db.execute(select(User))
users = result.scalars().all()
return [{"id": u.id, "username": u.username, "email": u.email} for u in
users]
@app.post("/users", status_code=201)
async def create_user(
username: str,
email: str,
db: AsyncSession = Depends(get_db)
):
user = User(username=username, email=email)
db.add(user)
await db.commit()
await db.refresh(user)
return {"id": user.id, "username": user.username}

---

<!-- p.5 -->

方式 说明 选择建议
lifespan 管理应用生命周期，推荐
新项目使
用
@app.on_event
旧方式（通过
@app.on_event("startup")/@app.on_event("shutdown")

管理生命周期），0.104 版本后被 lifespan 替代，不推荐新代
码使用
兼容性需
求
中间件传递 通过 request.state 简单场景
数据库操作 方法
查询所有 db.execute(select(Model)).scalars().all()
查询单个 db.execute(select(Model).where(...)).scalar_one_or_none()
新增 db.add(obj); await db.commit(); await db.refresh(obj)
修改 修改属性后 await db.commit()
删除 await db.delete(obj); await db.commit()
最佳实践：
1. 使用 lifespan 管理连接生命周期
2. 使用 Depends(get_db) 依赖注入获取会话
3. 每个请求使用独立的数据库会话
4. 长时间任务避免持有数据库连接
