# FastAPI中请求限流中间件的使用

> **素材来源**：`raw/FastAPI基础学习文档/FastAPI基础学习文档\20FastAPI的中间件（集合）\07FastAPI中请求限流中间件的使用\FastAPI中请求限流中间件的使用.pdf`
> **页数**：6（其中无文本页 2 页，多为截图/图示）
> **正文规模**：约 3,333 字符，其中汉字 657 个
> **说明**：本文件由 `tools/extract_sources.py` 自动抽取，仅作写书素材，未做人工校订；引用时请以原文为准。

---
<!-- p.1 -->

FastAPI 中请求限流中间件的使用
本节介绍如何使用限流中间件，防止暴力攻击和 DDoS。
什么是请求限流？
限制客户端在单位时间内的请求次数，超过则拒绝访问。
安装依赖
基本使用
1. 创建限流器
2. 添加限流中间件
限制：5 次/分钟
第1次请求 → ✅ 通过
第2次请求 → ✅ 通过
第3次请求 → ✅ 通过
第4次请求 → ✅ 通过
第5次请求 → ✅ 通过
第6次请求 → ❌ 429 Too Many Requests
pip install slowapi
from fastapi import FastAPI, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
app = FastAPI()
# 创建限流器（按 IP 限流）
limiter = Limiter(key_func=get_remote_address)
# 将限流器存入 app 状态
app.state.limiter = limiter
# 正确写法（无需手动封装 Middleware 类，直接传入中间件对象）
from slowapi.middleware import SlowAPIMiddleware
app.add_middleware(SlowAPIMiddleware)

---

<!-- p.2 -->

配置 说明
"5/minute" 每分钟 5 次
"100/hour" 每小时 100 次
"1000/day" 每天 1000 次
"10/second" 每秒 10 次
3. 使用限流装饰器
限流配置速查
不同接口不同限制
测试限流
超过限制时返回：
@app.get("/api")
@limiter.limit("5/minute")
async def api_endpoint(request: Request):
return {"message": "Hello"}
# 登录接口：严格限制（防止暴力破解）
@app.post("/login")
@limiter.limit("5/minute")
async def login(request: Request):
return {"message": "login"}
# 公开接口：宽松限制
@app.get("/public/data")
@limiter.limit("100/minute")
async def public_data(request: Request):
return {"data": "public"}
# 普通 API：正常限制
@app.get("/items")
@limiter.limit("60/minute")
async def list_items(request: Request):
return {"items": []}
# 连续请求 10 次
for i in {1..10}; do curl -I http://localhost:8000/api; done
HTTP/1.1 429 Too Many Requests
Retry-After: 60
content-type: application/json
{"detail": "请求过多，请稍后再试"}

---

<!-- p.3 -->

自定义限流 key
除了按 IP 限流，还可以按用户限流：
按 Token 限流时，需先验证 Token 合法性，建议使用解析后的用户 ID 作为限流 key（而非原始
Token），避免 Token 泄露导致的限流失效；Token 无效时降级为 IP 限流。
自定义限流响应
修改被限流后的返回内容：
分布式限流（多实例部署）
单机部署用内存存储，多实例部署必须用 Redis：
from fastapi import HTTPException
def get_user_id(request: Request) -> str:
"""基于用户的限流（需先验证 Token 合法性）"""
auth_header = request.headers.get("Authorization", "")
if auth_header.startswith("Bearer "):
token = auth_header[7:]
# 补充：实际场景需先验证 Token 有效性（如解析 JWT）
try:
# 示例：解析 Token 获取用户 ID（替换为实际业务逻辑）
user_id = parse_jwt_token(token) # 需实现 parse_jwt_token 函数
return user_id # 用用户 ID 而非 Token 本身（更安全，避免 Token 泄露）
except Exception:
# Token 无效时，降级为按 IP 限流
return get_remote_address(request)
return get_remote_address(request)
# 使用自定义 key 函数
limiter = Limiter(key_func=get_user_id)
from slowapi.errors import RateLimitExceeded
from fastapi.responses import JSONResponse
@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
retry_after = exc.retry_after or 60 # 使用异常自带的重试时间，兜底 60 秒
return JSONResponse(
status_code=429,
content={
"error": "请求过于频繁",
"detail": str(exc.detail),
"retry_after": retry_after
},
headers={"Retry-After": str(retry_after)} # 需转为字符串，符合 HTTP 规范
)

---

<!-- p.4 -->

场景 推荐阈值 原因
登录接口 5-10/分钟 防止暴力破解
普通 API 60-100/分钟 正常用户使用
公开数据 200-500/分钟 适当放宽
管理接口 10-30/小时 严格限制
功能 方法
限流装饰器 @limiter.limit("数量/时间")
按 IP 限流 get_remote_address
按用户限流 自定义 key 函数
限流异常 RateLimitExceeded
分布式存储 RedisStorage
限流策略建议
总结
最佳实践：
1. 公开接口使用宽松限制
2. 敏感接口使用严格限制
3. 多实例部署时使用 Redis 存储
4. 返回友好的错误信息
pip install redis slowapi
import redis
from slowapi import Limiter
from slowapi.storage.redis_storage import RedisStorage
# 显式指定 decode_responses（避免 bytes 类型问题），并兼容 Redis 连接配置
redis_client = redis.Redis(
host="localhost",
port=6379,
db=0,
decode_responses=True, # 新增：确保返回字符串而非 bytes
password=None, # 补充：生产环境建议添加密码
socket_timeout=5
)
limiter = Limiter(
key_func=get_remote_address,
storage=RedisStorage(redis_client)
)

---

<!-- p.5 -->

5. 记录限流日志便于监控
