# 07_FastAPI实例化参数_中间件与依赖注入

> **素材来源**：`raw/FastAPI基础学习文档/FastAPI基础学习文档\02FastAPI实例化app应用配置参数（集合）\07_FastAPI实例化参数_中间件与依赖注入.pdf`
> **页数**：4（其中无文本页 1 页，多为截图/图示）
> **正文规模**：约 2,179 字符，其中汉字 493 个
> **说明**：本文件由 `tools/extract_sources.py` 自动抽取，仅作写书素材，未做人工校订；引用时请以原文为准。

---
<!-- p.1 -->

参数名 类型 默认值 说明
dependencies Sequence[Depends] [] 全局依赖项（所有接口都会执行）
middleware Sequence[Middleware] None 全局中间件列表
FastAPI 实例化参数：中间件与依赖注入
本文档介绍 FastAPI 实例化时配置全局中间件和依赖注入的参数。
参数说明
全局中间件
CORS 中间件配置
多个中间件组合
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
app = FastAPI()
app.add_middleware(
CORSMiddleware,
allow_origins=["http://localhost:3000"],
allow_credentials=True,
allow_methods=["*"],
allow_headers=["*"],
)
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from starlette.middleware.sessions import SessionMiddleware
import secrets
app = FastAPI()
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
CORSMiddleware,
allow_origins=["https://example.com"],
allow_credentials=True,

---

<!-- p.2 -->

特性 中间件 ( middleware ) 依赖注入 ( dependencies )
执行时机 请求/响应的处理管道中 路由处理函数调用前
获取请求对象 通过 request 参数 通过 Depends 注入
注册方式 app.add_middleware() FastAPI(dependencies=[...])
适用场景 CORS、GZip、Session 等 认证、验证、日志等
中间件按照添加顺序形成嵌套结构，先添加的在外层、后添加的在内层；请求处理时先执行外层中
间件（先添加的），再执行内层；响应返回时先执行内层中间件（后添加的），再执行外层。
全局依赖注入
使用 dependencies 为所有路由添加全局依赖：
中间件与依赖注入对比
allow_methods=["GET", "POST"],
allow_headers=["Authorization"],
)
app.add_middleware(SessionMiddleware, secret_key=secrets.token_hex(32))
from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPBearer
security = HTTPBearer()
async def verify_token(authorization: str = Depends(security)):
# 先判断 Token 是否存在，避免 AttributeError
if not authorization:
raise HTTPException(status_code=401, detail="未提供 Token")
if authorization.credentials != "valid-token":
raise HTTPException(status_code=401, detail="无效的 Token")
return authorization.credentials
app = FastAPI(dependencies=[Depends(verify_token)])
@app.get("/items")
def get_items():
return [{"id": 1}, {"id": 2}]
@app.get("/users")
def get_users():
return [{"id": 1}, {"id": 2}]

---

<!-- p.3 -->

最佳实践
中间件顺序很重要：先添加的在外层（请求阶段先执行）、后添加的在内层（请求阶段后执行），
CORS 通常放最外层（确保跨域校验优先执行）
谨慎使用全局依赖：全局依赖会影响所有路由，可能造成性能开销，必要时用路由级别的 Depends
敏感操作谨慎放中间件：中间件对所有请求可见，且无法精准关联路由上下文，认证、权限校验等
核心敏感操作建议用依赖注入（依赖注入可精准绑定路由、支持更灵活的异常处理和依赖复用）；
仅无路由上下文依赖的敏感操作（如全局请求日志审计）可考虑中间件
GZip 压缩阈值：根据实际响应大小调整 minimum_size ，避免小文件压缩反而增加开销
