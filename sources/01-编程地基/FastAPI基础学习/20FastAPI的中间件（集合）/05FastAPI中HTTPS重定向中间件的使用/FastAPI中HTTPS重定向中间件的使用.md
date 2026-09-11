# FastAPI中HTTPS重定向中间件的使用

> **素材来源**：`raw/FastAPI基础学习文档/FastAPI基础学习文档\20FastAPI的中间件（集合）\05FastAPI中HTTPS重定向中间件的使用\FastAPI中HTTPS重定向中间件的使用.pdf`
> **页数**：4（其中无文本页 1 页，多为截图/图示）
> **正文规模**：约 2,224 字符，其中汉字 418 个
> **说明**：本文件由 `tools/extract_sources.py` 自动抽取，仅作写书素材，未做人工校订；引用时请以原文为准。

---
<!-- p.1 -->

FastAPI 中 HTTPS 重定向中间件的使用
本节介绍 HTTPS 重定向中间件，强制 HTTP 请求跳转到 HTTPS。
什么是 HTTPS 重定向？
自动将 HTTP 请求重定向到 HTTPS，确保数据传输加密。
基本使用
注意：此中间件本身不需要参数，直接添加即可。
测试
需要先配置 SSL 证书（仅测试用）：
重定向状态码
用户访问：http://example.com
↓
重定向 (307/308)
↓
用户访问：https://example.com
from fastapi import FastAPI
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
app = FastAPI()
# 添加 HTTPS 重定向中间件
app.add_middleware(HTTPSRedirectMiddleware)
# 生成自签名证书
openssl req -x509 -newkey rsa:2048 -keyout key.pem -out cert.pem -days 365 -
nodes
# 启动带 HTTPS 的服务
uvicorn main:app --ssl-keyfile key.pem --ssl-certfile cert.pem
# 测试 HTTP 请求
curl -I http://localhost:8000/
# 返回：307 Temporary Redirect
# Location: https://localhost:8000/

---

<!-- p.2 -->

状态码 名称 说明
307 临时重定向 保留原请求方法（POST 不会变成 GET）
308 永久重定向 保留原请求方法，浏览器会缓存
使用方式
方式 1：Nginx 层处理（推荐）
生产环境推荐在 Nginx 层处理，性能更好：
方式 2：应用层处理
当 Nginx 无法处理时使用：
方式 3：仅生产环境启用
# HTTP 监听（80 端口）
server {
listen 80;
server_name example.com;
# 重定向到 HTTPS
return 301 https://$server_name$request_uri;
}
# HTTPS 监听（443 端口）
server {
listen 443 ssl;
ssl_certificate /path/to/cert.pem;
ssl_certificate_key /path/to/key.pem;
location / {
proxy_pass http://127.0.0.1:8000;
}
}
from fastapi import FastAPI
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
app = FastAPI()
app.add_middleware(HTTPSRedirectMiddleware)
import os
from fastapi import FastAPI
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
app = FastAPI()
# 仅生产环境启用
if os.getenv("ENV") == "production":
app.add_middleware(HTTPSRedirectMiddleware)

---

<!-- p.3 -->

要点 说明
推荐方式 Nginx 层处理重定向
应用层 仅作为备选方案
避免循环 只配置一层重定向
WebSocket 客户端使用 wss:// 协议
常见问题
循环重定向
如果 Nginx 和应用层都配置了重定向，会导致无限循环：
解决方法：只在一层配置，推荐 Nginx 层。
WebSocket 支持
WebSocket 连接同样遵循重定向规则：
HTTPSRedirectMiddleware 仅处理 HTTP 协议的重定向，不会主动将 ws:// 重定向为 wss:// 。若
需保障 WebSocket 传输安全，需直接要求客户端使用 wss:// 协议连接，或在 Nginx 层配置 ws →
wss 的重定向。
总结
选择建议：
物理机/虚拟机部署 → Nginx 层
Docker 容器内 → 考虑应用层或 Entrypoint 脚本
已有 Nginx/Apache → Nginx 层
HTTP → HTTPS → HTTP → HTTPS → 死循环
from fastapi import FastAPI
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
app = FastAPI()
app.add_middleware(HTTPSRedirectMiddleware)
@app.websocket("/ws")
async def websocket_endpoint(websocket):
await websocket.accept()
await websocket.send_text("Hello")
