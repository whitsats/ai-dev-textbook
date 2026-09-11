# FastAPI的依赖注入

> **素材来源**：`raw/FastAPI基础学习文档/FastAPI基础学习文档\16FastAPI的依赖注入\FastAPI的依赖注入.pdf`
> **页数**：10（其中无文本页 1 页，多为截图/图示）
> **正文规模**：约 7,963 字符，其中汉字 1,138 个
> **说明**：本文件由 `tools/extract_sources.py` 自动抽取，仅作写书素材，未做人工校订；引用时请以原文为准。

---
<!-- p.1 -->

角色 / 动作 编程概念
你（需要依赖的对象） 路由函数
拿铁（依赖的接口） 依赖项函数
服务员（创建并组装依赖） FastAPI 注入器
"递给你" 动作 Depends()
FastAPI 的依赖注入
依赖注入（Dependency Injection，DI）的核心思想：不要在路由函数 / 依赖函数内部自行创建所需的
资源 / 数据（如数据库连接、用户信息），而是通过参数声明依赖，由 FastAPI 从外部创建并注入这些
资源 / 数据。
优势：代码更模块化、更易于测试、更易于维护。FastAPI 和 Spring/Java 的 DI 思想一致——都是控制
反转（IoC）。
工作原理
路由函数通过参数和 Depends 声明它需要什么，FastAPI 自动完成：
1. 查看声明（ Depends(get_user) ）
2. 执行依赖函数
3. 将返回值注入到路由参数
from fastapi import FastAPI, Depends
app = FastAPI()
def get_db():
db = "MockDB_Session"
try:
yield db # 注入 db，请求期间 db 可用
finally:
print("数据库会话已关闭") # 请求结束后自动清理
def get_current_user(db: str = Depends(get_db), token: str = "valid_token"):
if token != "valid_token":
raise HTTPException(status_code=401, detail="无效 Token")
return {"id": 1, "username": "alice", "db_session": db}
@app.get("/users/me")
def read_user_me(current_user: dict = Depends(get_current_user)):
return {"username": current_user["username"], "email": "alice@example.com"}

---

<!-- p.2 -->

执行流程：
基础用法
简单依赖
访问 GET /items 返回 {"q": "default_value"} 。
带 yield 的依赖：资源清理
执行顺序：初始化 → yield（注入到路由，暂停执行）→ 路由函数执行 → yield 之后的代码（路由执行
完后）→ finally（最终清理）。
请求 GET /users/me
→ get_db() 执行到 yield db，暂停
→ get_current_user(db="MockDB_Session") 执行，返回用户字典
→ 执行路由函数 read_user_me
→ 请求结束后：打印 "数据库会话已关闭"
from fastapi import FastAPI, Depends
app = FastAPI()
def get_query_param():
return "default_value"
@app.get("/items")
def read_items(q: str = Depends(get_query_param)):
return {"q": q}
def get_db():
print("连接数据库...") # 初始化
db = "DB_Connection_Object"
try:
yield db # 注入 db 到路由函数
print("提交事务...") # 路由执行完毕后执行
finally:
print("关闭数据库连接...") # 始终执行
@app.get("/users")
def get_users(db: str = Depends(get_db)):
return {"users": ["Alice", "Bob"]}

---

<!-- p.3 -->

带参数的依赖
FastAPI 自动将 URL 查询参数映射到依赖项的同名参数：
链式依赖
FastAPI 先解析 get_current_user 的所有依赖项（ verify_token() 和 get_db() ，二者无固定执
行顺序），执行完所有依赖项后将结果注入 get_current_user ，再执行 get_current_user ，最后
将结果注入路由函数。
from fastapi import FastAPI, Depends, Query
app = FastAPI()
def get_pagination_params(skip: int = 0, limit: int = 10):
return {"skip": skip, "limit": limit}
@app.get("/items")
def list_items(params: dict = Depends(get_pagination_params)):
return {"params": params}
GET /items → {"params": {"skip": 0, "limit": 10}}
GET /items?skip=5 → {"params": {"skip": 5, "limit": 10}}
GET /items?limit=50 → {"params": {"skip": 0, "limit": 50}}
from fastapi import FastAPI, Depends, HTTPException
app = FastAPI()
def get_db():
return "DB_Connection"
def verify_token(token: str = "valid_token"):
if token != "valid_token":
raise HTTPException(status_code=401, detail="无效 Token")
return {"user_id": 1}
def get_current_user(
token: dict = Depends(verify_token),
db: str = Depends(get_db)
):
return {"user": token, "db": db}
@app.get("/profile")
def get_profile(user: dict = Depends(get_current_user)):
return user

---

<!-- p.4 -->

类作为依赖项
FastAPI 会自动实例化类：
Depends() 不传参数时，FastAPI 自动使用类本身作为依赖项并实例化。 Annotated[str,
Header()] 表示参数类型为 str ，值从请求头获取。
Annotated 推荐写法
from fastapi import FastAPI, Depends, Header
from typing import Annotated
app = FastAPI()
class PaginationParams:
def __init__(self, skip: int = 0, limit: int = 10):
self.skip = skip
self.limit = limit
class UserQuery:
def __init__(self, x_token: Annotated[str, Header()]):
self.token = x_token
@app.get("/items")
def list_items(p: PaginationParams = Depends()):
return {"skip": p.skip, "limit": p.limit}
@app.get("/query")
def user_query(q: UserQuery = Depends()):
return {"token": q.token}
from fastapi import FastAPI, Depends, Query
from typing import Annotated
app = FastAPI()
# 带参数的依赖 + Annotated 写法
def get_pagination(
skip: Annotated[int, Query(ge=0)],
limit: Annotated[int, Query(ge=1, le=100)]
):
return {"skip": skip, "limit": limit}
# Annotated 声明依赖，同时保留参数校验
PaginationDep = Annotated[dict, Depends(get_pagination)]
@app.get("/items")
def list_items(params: PaginationDep):
return {"params": params}

---

<!-- p.5 -->

Annotated[str, Depends(get_db)] 含义：参数类型为 str ，其值由 Depends(get_db) 提供。相
比 str = Depends(get_db) ，Annotated 写法将类型信息和依赖来源分离，IDE 提示更友好。
执行顺序与生命周期
多依赖项的执行顺序
控制台输出顺序：
from fastapi import FastAPI, Depends
app = FastAPI()
def get_db():
print("1. [DB] Setup: 创建数据库连接")
db = "DB_Session"
try:
yield db
print("9. [DB] Yield-after: 提交事务")
finally:
print("10. [DB] Teardown: 关闭数据库连接")
def get_cache():
print("2. [Cache] Setup: 连接缓存服务器")
cache = "Cache_Connection"
try:
yield cache
print("7. [Cache] Yield-after: 同步缓存")
finally:
print("8. [Cache] Teardown: 断开缓存连接")
def get_current_user(
db: str = Depends(get_db),
cache: str = Depends(get_cache)
):
print("3. [User] Setup: 验证用户")
try:
yield f"User_Data (using {db} & {cache})"
print("5. [User] Yield-after: 更新用户活跃时间")
finally:
print("6. [User] Teardown: 清理用户资源")
@app.get("/profile")
def user_profile(user: str = Depends(get_current_user)):
print("4. [Route] 路由主逻辑执行中...")
return {"profile": user}

---

<!-- p.6 -->

Setup 阶段（自上而下，深入依赖树）：
Teardown 阶段（自下而上，栈式清理）：
最后 setup 的，最先 teardown。 即「后进先出」的栈式清理。
异常情况下的保证
即使路由函数抛出异常， finally 块也会保证执行——清理顺序与正常情况完全一致。
高级用法
可选依赖项
1. [DB] Setup: 创建数据库连接
2. [Cache] Setup: 连接缓存服务器
3. [User] Setup: 验证用户
4. [Route] 路由主逻辑执行中...
5. [User] Yield-after: 更新用户活跃时间
6. [User] Teardown: 清理用户资源
7. [Cache] Yield-after: 同步缓存
8. [Cache] Teardown: 断开缓存连接
9. [DB] Yield-after: 提交事务
10. [DB] Teardown: 关闭数据库连接
请求到达 /profile
│
▼
get_current_user(db=get_db, cache=get_cache)
│ 需要 db 和 cache
▼
get_db ──── yield ──── 暂停
get_cache ──── yield ──── 暂停
回到 get_current_user ──── yield ──── 暂停
▼
执行路由函数
路由执行完毕
▼
get_current_user: yield之后 → finally
▼
get_cache: yield之后 → finally
▼
get_db: yield之后 → finally
from fastapi import FastAPI, Depends
app = FastAPI()
def get_optional_db():
return "DB_Connection"

---

<!-- p.7 -->

特性 中间件 dependencies
生效范
围
默认全局，可通过路由匹配局部生
效
精准指定单个 / 多个路由生效
执行顺
序
按中间件添加顺序（请求先经过） 按依赖声明顺序（路由执行前）
错误处
理
需手动捕获异常并格式化响应
可直接抛出 HTTPException，FastAPI 自动格
式化
参数类型声明为 str | None ，不传参数时 db=None 。
全局依赖项：批量认证
dependencies=[Depends(...)] 在指定路由上批量添加认证检查。
依赖项中的状态共享
@app.get("/items")
def list_items(db: str | None = Depends(get_optional_db)):
if db:
return {"db": db, "source": "database"}
return {"source": "mock"}
from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPBearer
app = FastAPI()
security = HTTPBearer()
def verify_api_key(x_api_key: str = Depends(security)):
if x_api_key != "my-secret-key":
raise HTTPException(status_code=403, detail="无效的 API Key")
@app.get("/items", dependencies=[Depends(verify_api_key)])
def read_items():
return ["item1", "item2"]
@app.get("/users", dependencies=[Depends(verify_api_key)])
def read_users():
return ["alice", "bob"]
from fastapi import FastAPI, Depends, Request
app = FastAPI()

---

<!-- p.8 -->

通过 request.app.state 共享应用级别的状态。每次请求 req_id 自动递增。
多个 Depends
先验证登录（401），通过后才验证管理员（403）。适用于 RBAC 场景。
带缓存的依赖项
同一个请求中，若多次引用无参数 / 参数完全相同的同一个依赖项，FastAPI 会自动缓存依赖项的执行结
果（仅执行一次），避免重复计算 / 创建资源。
def get_request_id(request: Request):
if "request_id" not in request.app.state.__dict__:
request.app.state.request_id = 0
request.app.state.request_id += 1
return request.app.state.request_id
@app.get("/")
def get_id(req_id: int = Depends(get_request_id)):
return {"request_id": req_id}
from fastapi import FastAPI, Depends, HTTPException
app = FastAPI()
def verify_admin(token: str = "admin_token"):
if token != "admin_token":
raise HTTPException(status_code=403, detail="非管理员")
return {"role": "admin"}
def verify_login(token: str = "valid_token"):
if token != "valid_token":
raise HTTPException(status_code=401, detail="未登录")
return {"user_id": 1}
@app.get("/admin/panel")
def admin_panel(
admin=Depends(verify_admin),
user=Depends(verify_login)
):
return {"admin": admin, "user": user}
from fastapi import FastAPI, Depends
app = FastAPI()
def heavy_computation():
print("执行了 heavy_computation") # 只打印一次
return {"result": "expensive_result"}

---

<!-- p.9 -->

错误 原因 解决
TypeError: ... is not
a callable
Depends() 里传了值
而不是函数
传入函数： Depends(get_db) 而非
Depends(get_db())
yield 后代码没执行 依赖项没有 yield 需要清理资源必须加 yield
依赖项没被调用 参数没有 Depends 需注入的参数必须用 Depends()
result1 和 result2 得到的是同一个返回值。
常见错误
@app.get("/items")
def list_items(
result1=Depends(heavy_computation),
result2=Depends(heavy_computation),
):
return {"r1": result1, "r2": result2}
