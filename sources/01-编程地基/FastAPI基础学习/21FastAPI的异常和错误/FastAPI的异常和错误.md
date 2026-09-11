# FastAPI的异常和错误

> **素材来源**：`raw/FastAPI基础学习文档/FastAPI基础学习文档\21FastAPI的异常和错误\FastAPI的异常和错误.pdf`
> **页数**：8（其中无文本页 1 页，多为截图/图示）
> **正文规模**：约 7,179 字符，其中汉字 990 个
> **说明**：本文件由 `tools/extract_sources.py` 自动抽取，仅作写书素材，未做人工校订；引用时请以原文为准。

---
<!-- p.1 -->

参数 作用
status_code HTTP 状态码（400、401、404 等）
detail 错误信息，返回给客户端
headers 自定义响应头
FastAPI 异常处理与错误捕获
什么是异常处理？
异常就是程序运行中的"意外"。比如用户访问不存在的资源、输入了无效数据、数据库连接失败等。
FastAPI 提供了完善的异常处理机制，让我们能优雅地应对这些情况。
常用异常类型
HTTPException
最常用的异常类型，用于返回 HTTP 错误响应：
from fastapi import FastAPI, HTTPException, Path
app = FastAPI()
FAKE_USERS = {1: {"id": 1, "username": "alice"}, 2: {"id": 2, "username":
"bob"}}
@app.get("/users/{user_id}")
async def get_user(user_id: int = Path(..., gt=0)):
user = FAKE_USERS.get(user_id)
if user is None:
raise HTTPException(status_code=404, detail=f"用户 {user_id} 不存在")
return user
@app.get("/protected")
async def get_protected():
raise HTTPException(
status_code=401,
detail="需要认证",
headers={"WWW-Authenticate": "Bearer"}
)

---

<!-- p.2 -->

验证失败场景 示例 返回
路径参数类型不匹配 /items/abc （期望 int） 422
请求体格式错误 {"username":} 422
Pydantic 验证失败 email: "not-email" 422
必填参数缺失 期望 ?name= 但未传 422
RequestValidationError
FastAPI 底层会将参数验证失败（如路径参数类型不匹配、Pydantic 模型验证失败等）转换为
RequestValidationError 异常，并自动返回 422 响应。若需自定义验证失败的响应格式，可捕获该异常
（或其底层的 ValidationError）并重新处理。
全局异常处理器
对于业务代码中未被局部捕获的异常（如数据库连接错误、代码逻辑 bug 等），可注册针对 Exception
基类的全局异常处理器作为兜底方案。FastAPI 会优先匹配最具体的异常类型处理器，再匹配基类处理
器，因此兜底处理器需确保最后注册（或明确其优先级），避免覆盖特定异常的自定义处理逻辑。
基本用法
from pydantic import BaseModel, EmailStr
class UserCreate(BaseModel):
username: str
email: EmailStr
age: int
@app.post("/users")
async def create_user(user: UserCreate):
return {"username": user.username}
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import logging
app = FastAPI()
logger = logging.getLogger(__name__)
@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
logger.error(f"发生错误: {exc}")
return JSONResponse(
status_code=500,
content={"error": "服务器内部错误", "message": "发生了意外错误"}
)

---

<!-- p.3 -->

处理特定异常
最佳实践：
异常处理器注册顺序：需先注册具体异常类型的处理器（如 ValidationError 、
InsufficientFundsError ），再注册基类异常（如 Exception ）的兜底处理器，确保具体异常
优先匹配自定义逻辑，避免被基类处理器覆盖。
自定义业务异常
定义异常类
from pydantic import ValidationError
@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
errors = []
for error in exc.errors():
errors.append({
"field": ".".join(str(x) for x in error["loc"]),
"message": error["msg"]
})
return JSONResponse(status_code=422, content={"error": "验证错误", "details":
errors})
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
app = FastAPI()
# 自定义异常类
class InsufficientFundsError(Exception):
def __init__(self, account_id: str, balance: float, required: float):
self.account_id = account_id
self.balance = balance
self.required = required
super().__init__(f"账户 {account_id} 余额不足")
# 注册异常处理器
@app.exception_handler(InsufficientFundsError)
async def insufficient_funds_handler(request: Request, exc:
InsufficientFundsError):
return JSONResponse(
status_code=402,
content={
"error": "余额不足",
"account_id": exc.account_id,
"current_balance": exc.balance,
"required_amount": exc.required
}
)

---

<!-- p.4 -->

执行流程
统一错误响应格式
定义标准的错误格式，让客户端可以统一处理：
# 在业务代码中直接抛出
@app.post("/transfer")
async def transfer(from_account: str, to_account: str, amount: float):
# 模拟从数据库/缓存查询账户余额（更贴近真实业务）
account_balances = {"acc_001": 1000.0, "acc_002": 5000.0}
if from_account not in account_balances:
raise HTTPException(status_code=404, detail=f"账户 {from_account} 不存在")
balance = account_balances[from_account]
if amount <= 0:
raise HTTPException(status_code=400, detail="转账金额必须大于0")
if balance < amount:
raise InsufficientFundsError(account_id=from_account, balance=balance,
required=amount)
# 模拟转账逻辑
account_balances[from_account] -= amount
account_balances[to_account] = account_balances.get(to_account, 0.0) +
amount
return {"status": "转账成功", "from_account": from_account, "to_account":
to_account, "amount": amount}
请求 → 业务逻辑 → raise 自定义异常
↓
全局异常处理器捕获
↓
返回 JSON 响应
from pydantic import BaseModel
from typing import List, Optional
class ErrorDetail(BaseModel):
field: str
message: str
type: str
class ErrorResponse(BaseModel):
error: str
message: str
details: Optional[List[ErrorDetail]] = None
code: Optional[str] = None
@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
error_details = []
for error in exc.errors():

---

<!-- p.5 -->

响应示例：
在依赖注入中处理异常
抛出 HTTPException
抛出自定义异常
error_details.append(ErrorDetail(
field=".".join(str(x) for x in error["loc"]),
message=error["msg"],
type=error["type"]
))
# 使用统一错误响应模型构建响应
error_response = ErrorResponse(
error="Validation Error",
message="输入数据验证失败",
details=error_details,
code="VAL_001"
)
# 转换为字典返回（确保格式统一）
return JSONResponse(status_code=422, content=error_response.model_dump())
{
"error": "Validation Error",
"message": "输入数据无效",
"details": [
{"field": "email", "message": "邮箱格式不正确", "type": "value_error"}
],
"code": "VAL_001"
}
from fastapi import FastAPI, Depends, HTTPException, Header
from typing import Annotated
app = FastAPI()
def verify_api_key(x_api_key: Annotated[str, Header()]):
if x_api_key != "secret-key":
raise HTTPException(status_code=401, detail="无效的 API Key")
return x_api_key
@app.get("/data")
async def get_data(api_key: Annotated[str, Depends(verify_api_key)]):
return {"data": "secret data"}
from fastapi import FastAPI, Request, Depends, Header
from fastapi.responses import JSONResponse
from typing import Annotated
class AuthError(Exception):

---

<!-- p.6 -->

层级 做法 示例
业务层 抛出具体异常 raise InsufficientFundsError(...)
API 层 转换为 HTTP 响应 @app.exception_handler(...)
全局层 兜底处理 @app.exception_handler(Exception)
注意：依赖中抛出非 HTTPException 的异常，必须配合全局处理器才能正常返回响应。
异常处理最佳实践
分层处理
环境区分
def __init__(self, reason: str):
self.reason = reason
super().__init__(reason)
@app.exception_handler(AuthError)
async def auth_error_handler(request: Request, exc: AuthError):
return JSONResponse(status_code=403, content={"error": "认证失败", "reason":
exc.reason})
def get_current_user(authorization: Annotated[str | None, Header()] = None):
if not authorization:
raise AuthError(reason="请求头缺少 Authorization Token")
token = authorization.split(" ")[-1] if " " in authorization else
authorization
if token != "valid_token_123":
raise AuthError(reason="Token 无效或已过期")
# 模拟返回当前用户信息
return {"id": 1, "username": "test_user"}
@app.get("/profile")
async def get_profile(user: Annotated[dict, Depends(get_current_user)]):
return {"user": user}
import os
import traceback
ENV = os.getenv("ENV", "development")
@app.exception_handler(Exception)
async def exception_handler(request: Request, exc: Exception):
if ENV == "production":
return JSONResponse(status_code=500, content={"error": "Internal Server
Error"})
else:

---

<!-- p.7 -->

状态
码
含义 使用场景
400 Bad Request 请求参数不合法
401
Unauthorized（未授
权）
缺少认证凭证（如 Token）、凭证无效 / 过期，需先完成认证
403
Forbidden（禁止访
问）
已完成认证，但用户无权限执行该操作（如普通用户访问管理
员接口）
404 Not Found 资源不存在
422 Unprocessable Entity 参数验证失败
429 Too Many Requests 请求过于频繁
500 Internal Server Error 服务器内部错误（兜底）
503 Service Unavailable 服务不可用
生产环境：不暴露堆栈信息
开发环境：返回详细信息便于调试
HTTP 状态码速查
总结
return JSONResponse(
status_code=500,
content={"error": type(exc).__name__, "message": str(exc), "trace":
traceback.format_exc()}
)
FastAPI 异常处理要点：
抛出异常 → HTTPException(status_code, detail)
→ raise 自定义异常类
全局处理 → @app.exception_handler(异常类型)
→ 返回 JSONResponse
统一格式 → 定义 ErrorResponse 模型
→ 所有响应格式一致
最佳实践 → 业务层抛异常，API 层转换
→ 全局兜底，区分生产/开发环境
→ 记录日志，不泄露敏感信息
