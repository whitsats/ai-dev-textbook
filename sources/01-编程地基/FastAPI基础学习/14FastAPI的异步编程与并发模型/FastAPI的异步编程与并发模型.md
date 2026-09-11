# FastAPI的异步编程与并发模型

> **素材来源**：`raw/FastAPI基础学习文档/FastAPI基础学习文档\14FastAPI的异步编程与并发模型\FastAPI的异步编程与并发模型.pdf`
> **页数**：10（其中无文本页 1 页，多为截图/图示）
> **正文规模**：约 8,045 字符，其中汉字 1,301 个
> **说明**：本文件由 `tools/extract_sources.py` 自动抽取，仅作写书素材，未做人工校订；引用时请以原文为准。

---
<!-- p.1 -->

维度 同步 异步
执行方式 按顺序执行，等待时不做事 等待 IO 时可处理其他任务
资源占用 阻塞线程 不阻塞线程
适用场景 CPU 密集型任务 IO 密集型任务
代码复杂度 简单 需要理解事件循环
FastAPI 的异步编程与并发模型
FastAPI 基于 Python 的 async/await 语法提供原生异步支持，通过事件循环实现高并发。
同步 vs 异步
定义异步路径操作
async def ：异步函数，在事件循环中执行
def ：同步函数，FastAPI 会自动将其分配到线程池执行（默认 40 线程），避免直接阻塞事件循
环，但同步阻塞耗时仍会占用线程池资源，高并发下可能导致线程池耗尽。
混合使用示例
from fastapi import FastAPI
import asyncio
app = FastAPI()
@app.get("/async")
async def async_endpoint():
await asyncio.sleep(1) # 非阻塞等待，事件循环可处理其他请求
return {"message": "Hello from async endpoint"}
@app.get("/sync")
def sync_endpoint():
return {"message": "Hello from sync endpoint"}

---

<!-- p.2 -->

场景 方式 工具
数据库查询 async def + await asyncpg、databases
HTTP 请求 async def + await httpx（异步模式）
文件读写 async def + await aiofiles
CPU 密集型计算 def 同步函数 线程池/进程池
避免在异步函数中使用 time.sleep() ，会阻塞整个事件循环。
选择建议
事件循环原理
并发执行多个任务
@app.get("/async-task")
async def async_task():
await asyncio.sleep(1) # IO 密集型：数据库查询、HTTP 请求
return {"type": "async"}
@app.get("/sync-task")
def sync_task():
result = sum(i * i for i in range(10**7)) # CPU 密集型：纯计算
return {"type": "sync", "result": result}
import asyncio
async def task_a():
print("Task A: 开始")
await asyncio.sleep(1) # 暂停 1 秒
print("Task A: 完成")
async def task_b():
print("Task B: 开始")
await asyncio.sleep(0.5) # 暂停 0.5 秒
print("Task B: 完成")
async def main():
await asyncio.gather(task_a(), task_b())
asyncio.run(main())
# 输出：
# Task A: 开始
# Task B: 开始
# （0.5 秒后）

---

<!-- p.3 -->

特性 并发 并行
执行方
式
单线程 / 单进程内，利用 IO 等待间隙交替执行多个
任务
多 CPU 核心同时执行多个任
务
资源需
求
单 CPU 核心（可结合线程池） 多 CPU 核心
适用场
景
IO 密集型 CPU 密集型
实现方
式
事件循环（协程）+ 线程池 多进程/多线程（GIL 外)
asyncio.gather(*tasks) 并发执行所有协程，总耗时等于最慢任务的耗时。
时间轴可视化
并发与并行的区别
FastAPI 异步模型实现的是并发，CPU 密集型任务需要 ProcessPoolExecutor 实现并行。
异步工具详解
asyncio.gather ：并发等待多个任务
# Task B: 完成
# （再 0.5 秒后）
# Task A: 完成
# 总耗时约 1 秒（非串行的 1.5 秒）
Task1: [执行] → [await IO ] → [恢复] → [完成]
Task2: [执行] → [await IO] → [恢复] → [完成]
Task3: [执行] → [await IO] → [恢复] → [完成]
import asyncio
async def task(index: int):
await asyncio.sleep(index * 0.5)
return f"任务 {index} 完成"
async def main():
# 5 个任务并发执行，总耗时约 2.5 秒（最慢任务的耗时）
results = await asyncio.gather(
task(1), task(2), task(3), task(4), task(5)
)
print(results)
async def may_fail(index: int):

---

<!-- p.4 -->

asyncio.create_task ：后台任务（不等待）
create_task 将协程转为任务并立即提交给事件循环，与直接 await 的区别： await 会阻塞直到完
成， create_task 立即返回。
BackgroundTasks ：保证执行的后台任务
BackgroundTasks 与请求生命周期分离，客户端断开连接后任务仍会继续执行（与 create_task 的
关键区别）：
raise ValueError(f"任务 {index} 出错")
# return_exceptions=True：某个任务出错不影响其他任务
async def main_with_errors():
results = await asyncio.gather(
task(1),
may_fail(2), # 出错
task(3),
return_exceptions=True,
)
# ['任务 1 完成', ValueError('任务 2 出错'), '任务 3 完成']
import asyncio
async def slow_task():
await asyncio.sleep(3)
return "慢任务完成"
async def main():
task = asyncio.create_task(slow_task()) # 立即返回，不等待
print("任务已创建，不等待")
await asyncio.sleep(1)
print("已经过 1 秒")
result = await task # 等待任务完成
print(f"结果: {result}")
from fastapi import FastAPI, BackgroundTasks
import asyncio
app = FastAPI()
def sync_send_email(email: str):
import time
time.sleep(3) # 支持同步函数,但该同步阻塞会占用 FastAPI 线程池线程，高并发下可能导致线
程池耗尽。
print(f"邮件已发送给 {email}")

---

<!-- p.5 -->

特性 create_task BackgroundTasks
服务器关闭时 任务立即中断 等待任务执行完成（除非服务器被强制终止)
支持同步函数 不支持（需手动封装) 支持（自动分配到线程池)
错误处理 需自行捕获异常 框架自动捕获并记录异常（无返回给客户端)
run_in_executor ：在线程池/进程池中执行同步任务
CPU 密集型任务放在异步函数中直接调用会阻塞事件循环，应使用 run_in_executor ：
对于真正受 GIL 限制的 CPU 密集型任务，使用 ProcessPoolExecutor 分发到多进程，充分利用
多核。
async def async_notify(user_id: int):
await asyncio.sleep(2) # 也支持异步函数
print(f"用户 {user_id} 通知已发送")
@app.post("/register/")
async def register_user(username: str, background_tasks: BackgroundTasks):
background_tasks.add_task(sync_send_email, username)
return {"message": "注册成功"}
@app.post("/order/{order_id}")
async def create_order(order_id: int, background_tasks: BackgroundTasks):
background_tasks.add_task(async_notify, order_id)
return {"message": "订单创建成功"}
from fastapi import FastAPI
from concurrent.futures import ProcessPoolExecutor
import asyncio
app = FastAPI()
executor = ProcessPoolExecutor(max_workers=4)
def heavy_computation(n: int) -> int:
def fib(x):
return x if x < 2 else fib(x - 1) + fib(x - 2)
return fib(n)
@app.get("/compute/{n}")
async def compute_fibonacci(n: int):
loop = asyncio.get_event_loop()
# None = 默认线程池；传入 ProcessPoolExecutor 则用进程池
result = await loop.run_in_executor(None, heavy_computation, n)
return {"n": n, "fibonacci": result}

---

<!-- p.6 -->

asyncio.Semaphore ：控制并发数
asyncio.wait_for ：超时控制
实战示例
import asyncio
import httpx
semaphore = asyncio.Semaphore(5) # 最多 5 个并发
async def fetch_with_limit(url: str):
async with semaphore: # 获取许可，超出限制时等待
async with httpx.AsyncClient() as client:
response = await client.get(url)
return {"url": url, "status": response.status_code}
async def main():
urls = [f"https://httpbin.org/delay/1" for _ in range(20)]
# 20 个请求同时发起，但同时最多只有 5 个在执行
results = await asyncio.gather(*[fetch_with_limit(url) for url in urls])
print(f"完成 {len(results)} 个请求")
import asyncio
async def slow_operation():
await asyncio.sleep(10)
return "操作完成"
async def main():
try:
result = await asyncio.wait_for(slow_operation(), timeout=3.0)
print(result)
except asyncio.TimeoutError:
print("操作超时（超过 3 秒）")
# shield 保护任务不被取消
async def with_shield():
task = asyncio.create_task(slow_operation())
try:
result = await asyncio.wait_for(asyncio.shield(task), timeout=3.0)
except asyncio.TimeoutError:
print("等待超时，但任务仍在后台执行")
result = await task # 继续等待任务完成
print(f"任务最终结果: {result}")

---

<!-- p.7 -->

异步数据库操作
使用 lifespan 上下文管理器管理数据库连接生命周期：
from contextlib import asynccontextmanager
from fastapi import FastAPI
import databases
import sqlalchemy
DATABASE_URL = "sqlite:///./test.db"
database = databases.Database(DATABASE_URL, connect_args={"check_same_thread":
False})
engine = sqlalchemy.create_engine(DATABASE_URL)
metadata = sqlalchemy.MetaData()
users = sqlalchemy.Table(
"users", metadata,
sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
sqlalchemy.Column("name", sqlalchemy.String(50)),
sqlalchemy.Column("email", sqlalchemy.String(100)),
)
metadata.create_all(engine)
@asynccontextmanager
async def lifespan(app: FastAPI):
try:
await database.connect()
yield
except Exception as e:
print(f"数据库连接失败: {e}")
raise
finally:
if database.is_connected:
await database.disconnect()
app = FastAPI(lifespan=lifespan)
@app.post("/users/")
async def create_user(name: str, email: str):
query = users.insert().values(name=name, email=email)
last_id = await database.execute(query)
return {"id": last_id, "name": name, "email": email}
@app.get("/users/{user_id}")
async def read_user(user_id: int):
query = users.select().where(users.c.id == user_id)
user = await database.fetch_one(query)
if not user:
return {"error": "用户不存在"}
return dict(user)

---

<!-- p.8 -->

场景 同步处理 异步处理 性能提升
1000 并发 IO 请求 100s（串行） 1s（并发） ~99%
CPU 密集型任务 10s 10s（无差别） 0%（需多进程）
异步 HTTP 请求
性能对比
异步对 IO 密集型任务有巨大性能提升，对 CPU 密集型任务无效果。
最佳实践
@app.get("/users/")
async def list_users(skip: int = 0, limit: int = 10):
query = users.select().offset(skip).limit(limit)
result = await database.fetch_all(query)
return [dict(row) for row in result]
from fastapi import FastAPI
import asyncio
import httpx
app = FastAPI()
@app.get("/fetch-data")
async def fetch_data():
async with httpx.AsyncClient(timeout=10.0) as client:
response = await
client.get("https://jsonplaceholder.typicode.com/posts/1")
return response.json()
@app.get("/fetch-multiple")
async def fetch_multiple():
urls = [
"https://jsonplaceholder.typicode.com/posts/1",
"https://jsonplaceholder.typicode.com/posts/2",
"https://jsonplaceholder.typicode.com/users/1",
]
async with httpx.AsyncClient(timeout=30.0) as client:
tasks = [client.get(url) for url in urls]
responses = await asyncio.gather(*tasks)
return {"count": len(responses), "data": [r.json() for r in responses]}

---

<!-- p.9 -->

做法 说明
避免阻塞调用 异步函数中用 await asyncio.sleep() 而非 time.sleep()
CPU 密集型用线程池/进程池 放在事件循环外执行
错误处理 使用 try/except 捕获异步操作中的异常
资源管理 使用 async with 确保连接、文件句柄正确关闭
设置超时 所有 IO 操作都应设置合理的超时时间
工具 用途
async def / await 定义异步函数 / 等待异步操作
asyncio.gather 并发执行多个协程并等待结果
asyncio.create_task 创建后台任务（立即执行，不等待）
BackgroundTasks FastAPI 后台任务，保证执行
run_in_executor 在线程/进程池中执行同步任务
asyncio.Semaphore 控制并发数量
asyncio.wait_for 设置协程超时时间
lifespan 应用启动/关闭生命周期管理
核心工具速查
