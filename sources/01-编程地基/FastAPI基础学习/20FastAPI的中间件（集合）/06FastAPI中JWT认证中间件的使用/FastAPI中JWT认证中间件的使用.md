# FastAPI中JWT认证中间件的使用

> **素材来源**：`raw/FastAPI基础学习文档/FastAPI基础学习文档\20FastAPI的中间件（集合）\06FastAPI中JWT认证中间件的使用\FastAPI中JWT认证中间件的使用.pdf`
> **页数**：6（其中无文本页 1 页，多为截图/图示）
> **正文规模**：约 4,602 字符，其中汉字 651 个
> **说明**：本文件由 `tools/extract_sources.py` 自动抽取，仅作写书素材，未做人工校订；引用时请以原文为准。

---
<!-- p.1 -->

FastAPI 中 JWT 认证中间件的使用
本节介绍如何使用中间件实现全局 JWT 认证。
什么是 JWT？
JWT（JSON Web Token）是一种基于令牌的身份验证方式，流程如下：
Token 包含用户信息（Base64 编码，可解码），通过数字签名防篡改，需保证密钥安全才能防止伪
造。
安装依赖
基本使用
1. 定义 JWT 配置
2. 登录接口（签发 Token）
用户登录 → 服务器签发 Token（包含用户信息 + 数字签名） → 用户携带 Token 访问 → 服务器验证签
名（确认未篡改）
pip install fastapi-jwt-auth python-jose passlib
from datetime import timedelta
from fastapi import FastAPI, HTTPException, Depends
from fastapi_jwt_auth import AuthJWT
from pydantic import BaseModel
app = FastAPI()
class Settings(BaseModel):
authjwt_secret_key: str = "your-secret-key-change-in-production"
authjwt_algorithm: str = "HS256"
authjwt_access_token_expires: timedelta = timedelta(minutes=30)
settings = Settings()
@AuthJWT.load_config
def get_config():
return settings

---

<!-- p.2 -->

3. 受保护接口（验证 Token）
全局中间件方式
使用中间件实现全局认证，所有请求都会验证 Token：
from pydantic import BaseModel
# 定义登录请求模型
class LoginRequest(BaseModel):
username: str
password: str
@app.post("/login")
async def login(request: LoginRequest, Authorize: AuthJWT = Depends()):
if request.username != "admin" or request.password != "admin123":
raise HTTPException(status_code=401, detail="用户名或密码错误")
access_token = Authorize.create_access_token(subject=request.username)
return {"access_token": access_token, "token_type": "bearer"}
@app.get("/protected")
async def protected(Authorize: AuthJWT = Depends()):
# 验证令牌，无效则抛出异常
Authorize.jwt_required()
# 获取用户名
current_user = Authorize.get_jwt_subject()
return {"user": current_user}
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi_jwt_auth import AuthJWT
from fastapi_jwt_auth.exceptions import AuthJWTException
app = FastAPI()
# 先定义配置（需保留之前的 Settings 和 get_config）
class Settings(BaseModel):
authjwt_secret_key: str = "your-secret-key-change-in-production"
authjwt_algorithm: str = "HS256"
authjwt_access_token_expires: timedelta = timedelta(minutes=30)
@AuthJWT.load_config
def get_config():
return Settings()
@app.middleware("http")
async def jwt_middleware(request: Request, call_next):
# 排除白名单
if request.url.path in ["/login", "/docs", "/openapi.json", "/redoc"]:
return await call_next(request)
# 正确获取带请求上下文的 AuthJWT 实例
try:
authorize = AuthJWT(request) # 绑定 request 上下文

---

<!-- p.3 -->

路径 说明
/login 登录接口
/docs Swagger 文档
/openapi.json OpenAPI schema
/redoc ReDoc 文档
白名单路径：
测试
1. 登录获取 Token
返回：
2. 携带 Token 访问
返回：
3. 无 Token 访问
返回 401：
错误处理
authorize.jwt_required()
except AuthJWTException as e:
raise HTTPException(status_code=401, detail=str(e))
response = await call_next(request)
return response
curl -X POST "http://localhost:8000/login" \
-H "Content-Type: application/json" \
-d '{"username":"admin","password":"admin123"}'
{"access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...", "token_type":
"bearer"}
curl -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
http://localhost:8000/protected
{"user": "admin"}
curl http://localhost:8000/protected
{"detail": "未授权"}

---

<!-- p.4 -->

方式 说明 选择建议
中间
件
一次配置，全局生
效
全局认证场景（所有接口均需认证），但灵活性差（无法局部调
整）
依赖
注入
每个路由单独使
用，更灵活
推荐，更符合 FastAPI 依赖注入设计理念，支持局部认证、多层
依赖、更易测试和扩展
区分不同错误类型：
中间件 vs 依赖注入
依赖注入方式（推荐）：
生产环境建议
from fastapi_jwt_auth.exceptions import (
AuthJWTException,
TokenExpiredError, # Token 过期
MissingTokenError, # 缺少 Token
InvalidHeaderError, # Token 格式错误
)
@app.middleware("http")
async def jwt_middleware(request: Request, call_next):
if request.url.path in ["/login", "/docs", "/openapi.json"]:
return await call_next(request)
try:
AuthJWT().jwt_required()
except TokenExpiredError:
raise HTTPException(status_code=401, detail="Token 已过期")
except MissingTokenError:
raise HTTPException(status_code=401, detail="缺少 Token")
except InvalidHeaderError:
raise HTTPException(status_code=401, detail="无效的 Token")
except AuthJWTException:
raise HTTPException(status_code=401, detail="未授权")
return await call_next(request)
async def get_current_user(Authorize: AuthJWT = Depends()) -> str:
"""验证 Token 并返回当前用户"""
Authorize.jwt_required()
return Authorize.get_jwt_subject()
@app.get("/protected")
async def protected(user: str = Depends(get_current_user)):
return {"user": user}

---

<!-- p.5 -->

功能 方法 说明
创建 Token create_access_token() 登录时调用
验证 Token jwt_required() 验证有效性
获取用户 get_jwt_subject() 从 Token 获取用户信息
要点 说明
生产密钥 使用环境变量，不要硬编码
白名单路径 登录、文档等不需要认证
推荐方式 依赖注入而非全局中间件
过期时间 访问令牌 15-30 分钟
生产环境部署时，必须通过 export JWT_SECRET_KEY=xxx 手动设置密钥，禁止依赖代码中的默认随机
值（避免重启服务后密钥变化导致 Token 失效）。
安全建议：
密钥使用环境变量，不要硬编码
Token 过期时间：访问令牌 15-30 分钟
生产环境使用强密钥（至少 32 位随机字符串）
总结
import os
import secrets
from pydantic import BaseModel
class Settings(BaseModel):
# 生产环境必须通过环境变量设置密钥，禁止使用默认值
authjwt_secret_key: str = os.getenv(
"JWT_SECRET_KEY",
# 仅开发环境临时使用，生产环境必须手动配置环境变量
secrets.token_urlsafe(32)
)
authjwt_algorithm: str = "HS256"
