# FastAPI中信任代理头部中间件的使用

> **素材来源**：`raw/FastAPI基础学习文档/FastAPI基础学习文档\20FastAPI的中间件（集合）\10FastAPI中信任代理头部中间件的使用\FastAPI中信任代理头部中间件的使用.pdf`
> **页数**：6（其中无文本页 1 页，多为截图/图示）
> **正文规模**：约 3,608 字符，其中汉字 581 个
> **说明**：本文件由 `tools/extract_sources.py` 自动抽取，仅作写书素材，未做人工校订；引用时请以原文为准。

---
<!-- p.1 -->

参数 类型 说明
allowed_hosts List[str] 允许的主机名列表
模式 匹配示例 不匹配示例
example.com example.com api.examp
*.example.com api.example.com 、 www.example.com 、 a.b.example.com example.c
["*"] 全部 无（不推荐
FastAPI 中信任代理头部中间件的使用
本节介绍如何使用 TrustedHostMiddleware 防止主机头攻击。
什么是主机头攻击？
攻击者通过伪造 Host 头部字段，诱导服务器访问恶意地址或执行恶意操作。
基本使用
参数说明：
allowed_hosts 配置
正常请求：
GET /admin HTTP/1.1
Host: example.com
↓
服务器访问 example.com
攻击请求：
GET /admin HTTP/1.1
Host: evil.com
↓
服务器可能被诱导访问 evil.com（DNS 重绑定攻击）
from fastapi import FastAPI
from fastapi.middleware.trustedhost import TrustedHostMiddleware
app = FastAPI()
app.add_middleware(
TrustedHostMiddleware,
allowed_hosts=["example.com", "*.example.com"]
)

---

<!-- p.2 -->

测试
允许的主机
不允许的主机
常见问题
本地开发环境
开发时使用 localhost ，需要添加到允许列表：
使用反向代理
使用 Nginx 反向代理时，若 Nginx 转发了 X-Forwarded-Host 头， TrustedHostMiddleware 默认仅
校验原始 Host 头（即 Nginx 向 FastAPI 发送的 Host 头）。若需校验客户端真实 Host （ X-
Forwarded-Host ），需先配置 FastAPI 信任代理，并自定义中间件处理：
curl -I -H "Host: example.com" http://localhost:8000/
# 返回：HTTP/1.1 200 OK
curl -I -H "Host: evil.com" http://localhost:8000/
# 返回：HTTP/1.1 400 Bad Request
# {"detail": "Invalid host header"}
app.add_middleware(
TrustedHostMiddleware,
allowed_hosts=["localhost", "127.0.0.1", "*.example.com"]
)
from fastapi import FastAPI, Request
from fastapi.middleware.trustedhost import TrustedHostMiddleware
app = FastAPI(proxy_headers=True) # 信任代理头
# 自定义中间件校验 X-Forwarded-Host
@app.middleware("http")
async def validate_forwarded_host(request: Request, call_next):
forwarded_host = request.headers.get("X-Forwarded-Host")
if forwarded_host and forwarded_host not in ["example.com",
"api.example.com"]:
return JSONResponse(status_code=400, content={"detail": "Invalid
forwarded host header"})
response = await call_next(request)
return response
# 保留原始 Host 头校验
app.add_middleware(
TrustedHostMiddleware,

---

<!-- p.3 -->

WebSocket 支持
WebSocket 连接同样会被验证：
不同环境配置
与其他中间件配合
中间件顺序
建议按以下顺序注册（注册顺序 = 执行顺序，先注册的中间件先处理请求）：
allowed_hosts=["localhost"] # Nginx 向 FastAPI 发送的 Host 通常为 localhost
)
app.add_middleware(
TrustedHostMiddleware,
allowed_hosts=["example.com"]
)
@app.websocket("/ws")
async def websocket_endpoint(websocket):
await websocket.accept()
await websocket.send_text("Hello")
import os
from fastapi import FastAPI
from fastapi.middleware.trustedhost import TrustedHostMiddleware
app = FastAPI()
env = os.getenv("ENV", "development")
if env == "production":
# 生产环境：只允许正式域名
allowed_hosts = ["example.com", "www.example.com", "api.example.com"]
else:
# 开发环境：允许本地访问
allowed_hosts = ["localhost", "127.0.0.1", "0.0.0.0"]
app.add_middleware(
TrustedHostMiddleware,
allowed_hosts=allowed_hosts
)
from fastapi import FastAPI
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.cors import CORSMiddleware
app = FastAPI()
# 1. 先验证主机（最外层: 请求最先经过）

---

<!-- p.4 -->

建议 说明
不使用 * 生产环境绝对不要用通配符
明确列出域名 列出所有允许的域名
添加本地访问 开发环境添加 localhost
配合反向代理 使用 Nginx 时考虑多层防护
攻击类型 说明
DNS 重绑定 攻击者注册域名，通过 DNS 指向不同 IP
密码重置钓鱼 利用 Host 头进行钓鱼攻击
缓存污染 利用 Host 头污染 CDN/WAF 缓存
与 HTTPS 重定向配合
安全建议
常见攻击类型：
总结
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["example.com"])
# 2. 再处理 CORS（主机验证通过后才执行）
app.add_middleware(
CORSMiddleware,
allow_origins=["https://example.com"]
)
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
app = FastAPI()
# 1. HTTPS 重定向
app.add_middleware(HTTPSRedirectMiddleware)
# 2. 主机验证
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["example.com"])

---

<!-- p.5 -->

功能 说明
TrustedHostMiddleware 主机头验证中间件
allowed_hosts 允许的主机名列表
*.example.com 通配符匹配子域名
400 Bad Request 不允许的主机返回此错误
最佳实践：
1. 生产环境不使用 *
2. 开发环境添加 localhost
3. 配合反向代理时考虑多层防护
4. 与其他安全中间件配合使用
