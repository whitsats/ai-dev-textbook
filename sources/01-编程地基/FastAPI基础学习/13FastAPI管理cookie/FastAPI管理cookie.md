# FastAPI管理cookie

> **素材来源**：`raw/FastAPI基础学习文档/FastAPI基础学习文档\13FastAPI管理cookie\FastAPI管理cookie.pdf`
> **页数**：10（其中无文本页 1 页，多为截图/图示）
> **正文规模**：约 8,331 字符，其中汉字 950 个
> **说明**：本文件由 `tools/extract_sources.py` 自动抽取，仅作写书素材，未做人工校订；引用时请以原文为准。

---
<!-- p.1 -->

属性 说明
key Cookie 名称
value Cookie 值
max_age 过期时间（秒），与 expires 同时设置时优先生效
expires 过期时间点（UTC datetime），与 max_age 二选一
path 有效路径，默认为 /
domain 有效域名
secure 仅 HTTPS 传输
httponly 禁止 JavaScript 访问（防 XSS）
samesite CSRF 防护策略（ strict / lax / none ）
FastAPI 管理 Cookie
Cookie 是服务器发给浏览器并保存在本地的一小块数据，浏览器后续请求时会自动携带。FastAPI 通过
Cookie 参数和 Response.set_cookie() 提供完整的 Cookie 操作能力。
Cookie 工作原理
Cookie 常用属性：
基本操作
读取 Cookie
方式一： Cookie 参数（推荐，单个 Cookie）
方式二： request.cookies 字典（读取多个 Cookie）
首次请求 → 服务器 Set-Cookie 响应头 → 浏览器保存
后续请求 → 浏览器自动携带 Cookie 头 → 服务器读取验证
from fastapi import FastAPI, Cookie
from typing import Optional
app = FastAPI()
@app.get("/read_cookie")
def read_cookie(ads_id: Optional[str] = Cookie(None, alias="ads-id")):
return {"ads_id": ads_id}

---

<!-- p.2 -->

请求示例
响应示例
Cookie 参数的 alias 用于处理请求中 Cookie 名与函数参数名不一致的情况（如 ads-id vs
ads_id ）。
设置 Cookie
响应头
过期时间两种写法
from fastapi import FastAPI, Request
app = FastAPI()
@app.get("/read_cookies")
def read_cookies(request: Request):
return {
"username": request.cookies.get("username"),
"session_id": request.cookies.get("session_id")
}
curl -X GET "http://127.0.0.1:8000/read_cookies" \
-H "Cookie: username=admin; session_id=sess_abc123"
{"username": "admin", "session_id": "sess_abc123"}
from fastapi import FastAPI, Response
app = FastAPI()
@app.get("/set_cookie")
def set_cookie(response: Response):
response.set_cookie(
key="username",
value="admin",
max_age=3600,
httponly=True,
secure=True,
samesite="lax"
)
return {"message": "Cookie 已设置"}
set-cookie: username=admin; Max-Age=3600; HttpOnly; Secure; SameSite=Lax

---

<!-- p.3 -->

datetime.utcnow() 已在 Python 3.12 弃用，必须使用 datetime.now(timezone.utc) 。
删除 Cookie
响应头
删除 Cookie 本质上是设置一个过期时间为过去的同名 Cookie。注意：如果设置时指定了
path/domain ，删除时也需传入相同的 path/domain 。
Cookie 参数高级特性
Cookie(...) 支持 Pydantic 风格的验证和元数据：
# 方式一：max_age，指定秒数（推荐）
response.set_cookie(key="token", value="abc", max_age=86400) # 24小时
# 方式二：expires，指定 UTC 时间点
from datetime import datetime, timedelta, timezone
expires = datetime.now(timezone.utc) + timedelta(days=7)
response.set_cookie(key="token", value="abc", expires=expires)
from fastapi import FastAPI, Response
app = FastAPI()
@app.post("/logout")
def logout(response: Response):
response.delete_cookie(key="session_id")
return {"message": "已登出"}
set-cookie: session_id=; Expires=Thu, 01 Jan 1970 00:00:00 GMT; Max-Age=0
from fastapi import FastAPI, Cookie
app = FastAPI()
@app.get("/advanced_cookie")
def advanced_cookie(
user_id: str = Cookie(
..., # 必填，不传返回 422
alias="user-id", # 映射请求中的 Cookie 名
min_length=32,
max_length=32,
pattern=r"^[a-zA-Z0-9]{32}$",
description="登录后返回的 32 位用户 ID",
)
):
return {"user_id": user_id}

---

<!-- p.4 -->

参数 说明
... （Ellipsis） 必填，不传返回 422
alias 映射不同的 Cookie 名称
min_length / max_length 值的长度限制
pattern 正则表达式验证
title / description OpenAPI 文档元数据
请求示例
验证失败响应（422）
中间件统一验证 Cookie
方式一： @app.middleware （推荐）
curl -X GET "http://127.0.0.1:8000/advanced_cookie" \
-H "Cookie: user-id=abcdef1234567890abcdef1234567890"
{"detail": [{"loc": ["cookie", "user-id"], "msg": "String should match pattern",
"type": "string_pattern_mismatch"}]}
from fastapi import FastAPI, Request, HTTPException
from starlette.responses import JSONResponse
app = FastAPI()
valid_sessions = {}
EXEMPT_PATHS = {"/login", "/docs", "/openapi.json"}
@app.middleware("http")
async def cookie_auth_middleware(request: Request, call_next):
if request.url.path in EXEMPT_PATHS:
return await call_next(request)
session_id = request.cookies.get("session_id")
if not session_id or session_id not in valid_sessions:
return JSONResponse(
status_code=401,
content={"detail": "请先登录"}
)
request.state.username = valid_sessions[session_id]
return await call_next(request)

---

<!-- p.5 -->

特性 @app.middleware BaseHTTPMiddleware
代码量 更少 需要定义类
可复用性 函数直接定义 类可继承复用
适用场景 简单拦截逻辑 复杂配置、多次实例化
方式二： BaseHTTPMiddleware 类
完整示例：用户登录认证
from fastapi import FastAPI, Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
app = FastAPI()
valid_sessions = {}
class CookieAuthMiddleware(BaseHTTPMiddleware):
EXEMPT_PATHS = {"/login", "/docs", "/openapi.json"}
async def dispatch(self, request: Request, call_next):
if request.url.path in self.EXEMPT_PATHS:
return await call_next(request)
session_id = request.cookies.get("session_id")
if not session_id or session_id not in valid_sessions:
return JSONResponse(
status_code=401,
content={"detail": "请先登录"}
)
request.state.username = valid_sessions[session_id]
return await call_next(request)
app.add_middleware(CookieAuthMiddleware)
from fastapi import FastAPI, Response, Request, HTTPException
from pydantic import BaseModel
from datetime import datetime, timedelta, timezone
import uuid
import os
is_prod = os.getenv("ENV") == "production"
app = FastAPI()

---

<!-- p.6 -->

请求流程
fake_users_db = {
"admin": {"username": "admin", "password": "123456"},
"user01": {"username": "user01", "password": "password"}
}
sessions = {}
class LoginRequest(BaseModel):
username: str
password: str
@app.post("/login")
def login(response: Response, login_data: LoginRequest):
user = fake_users_db.get(login_data.username)
if not user or user["password"] != login_data.password:
raise HTTPException(status_code=401, detail="用户名或密码错误")
session_id = str(uuid.uuid4())
sessions[session_id] = {
"username": login_data.username,
"login_time": datetime.now(timezone.utc).isoformat()
}
response.set_cookie(
key="session_id",
value=session_id,
httponly=True,
secure=is_prod,
samesite="lax",
max_age=86400
)
return {"message": "登录成功"}
@app.get("/protected")
def protected(request: Request):
session_id = request.cookies.get("session_id")
if not session_id or session_id not in sessions:
raise HTTPException(status_code=401, detail="请先登录")
return {"message": f"欢迎回来，{sessions[session_id]['username']}！"}
@app.post("/logout")
def logout(response: Response):
response.delete_cookie(key="session_id")
return {"message": "已登出"}
# 登录
curl -X POST "http://127.0.0.1:8000/login" \
-H "Content-Type: application/json" \
-d '{"username": "admin", "password": "123456"}'

---

<!-- p.7 -->

特性 Cookie（客户端存储） Session（服务端存储）
存储位置 浏览器本地 服务器内存 / Redis / 数据库
数据安全 暴露在客户端，敏感信息需加密 服务端相对安全
传输量 每次请求都携带，增加体积 仅传递 session_id（轻量）
容量限制 单个 4KB，总数 20-50 个 可存储大量数据
Cookie 与 Session 对比
推荐做法：将 session_id 存入 Cookie（设置 httponly 防 XSS），实际用户数据存服务器端
（Redis / 数据库）。
安全设置详解
Secure：仅 HTTPS 传输
生产环境必须启用，HTTP 下 Cookie 会被窃听。
HttpOnly：禁止 JavaScript 访问
设置后 document.cookie 无法读取，防止 XSS 攻击窃取 Cookie。
SameSite：CSRF 防护
# 响应头: Set-Cookie: session_id=<uuid>; Max-Age=86400; HttpOnly; Secure;
SameSite=Lax
# 访问受保护接口
curl -X GET "http://127.0.0.1:8000/protected" \
-H "Cookie: session_id=<登录时获取的session_id>"
# 响应: {"message": "欢迎回来，admin！"}
# 登出
curl -X POST "http://127.0.0.1:8000/logout" \
-H "Cookie: session_id=<session_id>"
response.set_cookie(key="token", value="xyz", secure=True)
response.set_cookie(key="token", value="xyz", httponly=True)
response.set_cookie(key="token", value="xyz", samesite="strict") # 严格：仅同站请
求携带
response.set_cookie(key="token", value="xyz", samesite="lax") # 宽松：允许跨站
GET（默认）
response.set_cookie(key="token", value="xyz", samesite="none", secure=True) # 无
限制

---

<!-- p.8 -->

模式 同站请求 跨站 GET 跨站 POST
strict 携带 不携带 不携带
lax 携带 携带 不携带
none 携带 携带 携带（需 secure=True ）
生产环境推荐配置
常见问题
Cookie 设置成功但读取不到？
path 不一致：设置时 path="/api/" ，读取时默认从 path="/" 读取，会读取不到
secure 与协议不匹配：开发环境 HTTP 下设置 secure=True 不会保存
domain 不一致：跨域场景下 Cookie 共享有限制
Cookie 大小限制？
单个 Cookie ≤ 4KB
单域名下总数限制约 20-50 个
大量数据仅存 ID，实际数据存服务端
测试中验证 Cookie
response.set_cookie(
key="session_id",
value=session_id,
httponly=True, # 防 XSS
secure=True, # 仅 HTTPS
samesite="lax", # CSRF 防护
max_age=86400, # 24小时
path="/"
)
from fastapi.testclient import TestClient
client = TestClient(app)
response = client.post("/login", json={"username": "admin", "password":
"123456"})
assert response.cookies.get("session_id") is not None
response = client.get("/protected", cookies={"session_id": "xxx"})
assert response.status_code == 200

---

<!-- p.9 -->

操作 方法
读取（单个） Cookie(...) 参数
读取（多个） request.cookies.get()
设置 response.set_cookie()
删除 response.delete_cookie()
前端操作 Cookie
总结
最佳实践
1. 生产环境必开安全三件套： httponly=True + secure=True + samesite="lax"
2. 敏感信息存服务端：Cookie 仅存 session_id，实际数据放 Redis / 数据库
3. 注意 path 一致性：设置和删除时确保 path 相同
4. 合理设置过期时间：根据业务需求选择 max_age 或 expires
5. 定期清理会话：实现过期机制，防止会话积压
// 读取（httponly 的 Cookie 无法通过 JS 读取）
const cookie = document.cookie;
// 设置
document.cookie = "theme=dark; path=/; max-age=86400";
// 删除
document.cookie = "theme=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT";
