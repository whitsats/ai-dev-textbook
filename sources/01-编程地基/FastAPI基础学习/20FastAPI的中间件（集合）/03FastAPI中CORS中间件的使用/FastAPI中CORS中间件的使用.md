# FastAPI中CORS中间件的使用

> **素材来源**：`raw/FastAPI基础学习文档/FastAPI基础学习文档\20FastAPI的中间件（集合）\03FastAPI中CORS中间件的使用\FastAPI中CORS中间件的使用.pdf`
> **页数**：4（其中无文本页 1 页，多为截图/图示）
> **正文规模**：约 2,390 字符，其中汉字 400 个
> **说明**：本文件由 `tools/extract_sources.py` 自动抽取，仅作写书素材，未做人工校订；引用时请以原文为准。

---
<!-- p.1 -->

前端地址 API 地址
是否
同源
原因
http://localhost:3000 http://localhost:3000/api
✅ 同
源
协议、域名、端口
都相同
http://localhost:3000 http://localhost:8000/api
❌ 跨
域
端口不同
http://example.com https://example.com/api
❌ 跨
域
协议不同
http://a.example.com http://b.example.com/api
❌ 跨
域
子域名不同
参数 说明 常用值
allow_origins 允许的域名列表 ["*"] 或具体域名
allow_methods 允许的 HTTP 方法 ["*"] 或 ["GET", "POST"]
allow_headers 允许的请求头 ["*"] 或 ["Authorization"]
allow_credentials 是否允许发送 Cookie True / False
max_age 预检请求缓存时间（秒） 默认 600
FastAPI 中 CORS 中间件的使用
本节介绍 CORS（跨域资源共享）中间件，解决前后端分离时的跨域访问问题。
什么是跨域？
浏览器出于安全考虑，限制不同源之间的请求。
什么是"同源"？ 三要素完全相同才算同源：
基本使用
参数说明：
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
app = FastAPI()
app.add_middleware(
CORSMiddleware,
allow_origins=["*"], # 允许所有来源
allow_methods=["*"], # 允许所有方法
allow_headers=["*"], # 允许所有请求头
)

---

<!-- p.2 -->

预检请求（OPTIONS）
浏览器发送复杂请求（PUT、DELETE、有自定义头等）前，会先发一个 OPTIONS 预检请求：
CORS 中间件会自动处理 OPTIONS 请求。
常见问题
问题 1：allow_credentials=True 时不能用 *
问题 2：Authorization 头被拦截
前端发送 Token 时，需要在 allow_headers 中允许：
生产环境配置
浏览器 → OPTIONS /api/users → 检查服务器是否允许
↓
允许 → 发送实际请求
不允许 → 被拦截
# ❌ 错误
app.add_middleware(
CORSMiddleware,
allow_origins=["*"], # 通配符
allow_credentials=True, # 允许 Cookie
)
# ✅ 正确：必须指定具体域名
app.add_middleware(
CORSMiddleware,
allow_origins=["http://localhost:3000", "https://example.com"],
allow_credentials=True,
allow_methods=["*"],
allow_headers=["*"],
)
app.add_middleware(
CORSMiddleware,
allow_origins=["http://localhost:3000"],
allow_methods=["*"],
allow_headers=["*"], # 或明确列出 ["Authorization", "Content-Type"]
)
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
app = FastAPI()
# 根据环境配置不同的域名

---

<!-- p.3 -->

要点 说明
allow_origins=["*"] 开发环境可用，生产环境要指定域名
allow_credentials=True 允许 Cookie，但 origins 不能用 *
预检请求 OPTIONS 方法会被自动处理
常用头 Authorization （Token）、 Content-Type （JSON）
前端配合
fetch 请求
axios 请求
总结
生产环境建议：明确列出允许的域名和方法，不要使用 * 。
env = os.getenv("ENV", "development")
if env == "production":
origins = ["https://example.com", "https://www.example.com"]
else:
origins = ["http://localhost:3000", "http://localhost:8080"]
app.add_middleware(
CORSMiddleware,
allow_origins=origins,
allow_credentials=True,
allow_methods=["GET", "POST", "PUT", "DELETE"],
allow_headers=["Authorization", "Content-Type"],
)
fetch('http://localhost:8000/api', {
credentials: 'include' // 携带 Cookie
})
axios.get('http://localhost:8000/api', {
withCredentials: true // 携带 Cookie
})
