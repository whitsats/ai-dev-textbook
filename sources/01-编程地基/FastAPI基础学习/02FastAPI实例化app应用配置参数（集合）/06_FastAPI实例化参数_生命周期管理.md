# 06_FastAPI实例化参数_生命周期管理

> **素材来源**：`raw/FastAPI基础学习文档/FastAPI基础学习文档\02FastAPI实例化app应用配置参数（集合）\06_FastAPI实例化参数_生命周期管理.pdf`
> **页数**：4（其中无文本页 1 页，多为截图/图示）
> **正文规模**：约 2,841 字符，其中汉字 392 个
> **说明**：本文件由 `tools/extract_sources.py` 自动抽取，仅作写书素材，未做人工校订；引用时请以原文为准。

---
<!-- p.1 -->

参数名 类型 默认值 说明
on_startup Sequence[Callable] None 已废弃，推荐用 lifespan
on_shutdown Sequence[Callable] None 已废弃，推荐用 lifespan
lifespan
Union[Callable[[FastAPI],

AsyncContextManager],

LifespanProtocol]
None 应用生命周期管理函数
FastAPI 实例化参数：生命周期管理
本文档介绍 FastAPI 实例化时通过 lifespan 管理应用启动与关闭的参数。
参数说明
lifespan 是官方推荐的应用生命周期管理方式，替代已废弃的 on_startup 和 on_shutdown 。
基本用法
from contextlib import asynccontextmanager
from fastapi import FastAPI
import asyncio
# 补充缺失的函数定义（占位/示例逻辑）
async def init_database():
"""初始化数据库连接/表结构等"""
await asyncio.sleep(0.1) # 模拟异步操作
print("数据库初始化完成")
async def load_cache():
"""加载缓存配置/预热缓存等"""
await asyncio.sleep(0.1)
print("缓存加载完成")
async def close_database():
"""关闭数据库连接"""
await asyncio.sleep(0.1)
print("数据库连接关闭")
async def save_cache():
"""保存缓存数据到持久化存储"""
await asyncio.sleep(0.1)
print("缓存数据已保存")
@asynccontextmanager
async def lifespan(app: FastAPI):
print("应用启动中...")
await init_database()
await load_cache()

---

<!-- p.2 -->

数据库连接池管理
yield
print("应用关闭中...")
await close_database()
await save_cache()
app = FastAPI(lifespan=lifespan)
@app.get("/")
def root():
return {"message": "Hello World"}
from contextlib import asynccontextmanager
from fastapi import FastAPI
import asyncpg
from collections.abc import AsyncGenerator
db_pool: asyncpg.Pool | None = None
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
global db_pool
try: # 新增异常捕获，确保启动失败也能执行关闭逻辑
print("正在创建数据库连接池...")
db_pool = await asyncpg.create_pool(
host="localhost",
port=5432,
user="user",
password="password",
database="mydb",
min_size=5,
max_size=20
)
print("数据库连接池创建成功")
yield
finally: # 改用 finally 确保关闭逻辑必执行
print("正在关闭数据库连接池...")
if db_pool:
await db_pool.close()
print("数据库连接池已关闭")
app = FastAPI(lifespan=lifespan)
@app.get("/users/{user_id}")
async def get_user(user_id: int):
async with db_pool.acquire() as conn:
row = await conn.fetchrow("SELECT * FROM users WHERE id = $1", user_id)
return dict(row) if row else {"error": "用户不存在"}

---

<!-- p.3 -->

Redis 缓存管理
最佳实践
始终使用 lifespan ：避免使用已废弃的 on_startup 和 on_shutdown
不要在 lifespan 中执行耗时过长的同步操作：会阻塞事件循环，影响启动速度
资源释放要确保执行：即使启动失败，关闭逻辑也应尽量执行
多数据库场景：可在一个 lifespan 中管理多个资源的初始化与销毁
from contextlib import asynccontextmanager
from fastapi import FastAPI
import redis.asyncio as redis
redis_client: redis.Redis | None = None
@asynccontextmanager
async def lifespan(app: FastAPI):
global redis_client
redis_client = await redis.from_url(
"redis://localhost:6379",
encoding="utf-8",
decode_responses=True
)
await redis_client.ping()
print("Redis 连接成功")
yield
if redis_client:
await redis_client.close()
print("Redis 连接已关闭")
app = FastAPI(lifespan=lifespan)
@app.get("/cache/{key}")
async def get_cache(key: str):
value = await redis_client.get(key)
return {"key": key, "value": value}
@app.post("/cache/{key}/{value}")
async def set_cache(key: str, value: str):
await redis_client.set(key, value)
return {"message": "设置成功"}
