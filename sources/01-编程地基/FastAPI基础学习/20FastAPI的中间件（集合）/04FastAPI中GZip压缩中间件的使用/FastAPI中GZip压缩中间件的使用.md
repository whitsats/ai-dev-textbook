# FastAPI中GZip压缩中间件的使用

> **素材来源**：`raw/FastAPI基础学习文档/FastAPI基础学习文档\20FastAPI的中间件（集合）\04FastAPI中GZip压缩中间件的使用\FastAPI中GZip压缩中间件的使用.pdf`
> **页数**：4（其中无文本页 1 页，多为截图/图示）
> **正文规模**：约 2,014 字符，其中汉字 512 个
> **说明**：本文件由 `tools/extract_sources.py` 自动抽取，仅作写书素材，未做人工校订；引用时请以原文为准。

---
<!-- p.1 -->

参数 类型 默认值 说明
minimum_size int 500 响应体大于此值才压缩（字节）
条件 说明
客户端发送 Accept-Encoding: gzip 浏览器支持才压缩
响应体大于 minimum_size 小数据不压缩
文本类型响应 JSON、HTML、XML 等会压缩
图片/视频 已是压缩格式，不处理
FastAPI 中 GZip 压缩中间件的使用
本节介绍 GZip 压缩中间件，用于减少网络传输量，提升响应速度。
什么是 GZip 压缩？
GZip 压缩将响应体从大变小，节省带宽。浏览器会自动解压缩，对开发者透明。
基本使用
参数说明：
压缩条件
中间件会自动判断是否需要压缩：
测试
如果返回头包含 Content-Encoding: gzip ，说明已启用压缩：
原始数据：100KB JSON
↓ GZip 压缩
压缩后：10KB
↓ 浏览器自动解压缩
显示：100KB JSON
from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware
app = FastAPI()
app.add_middleware(GZipMiddleware, minimum_size=1000)
# 查看响应头是否包含压缩标识
curl -I -H "Accept-Encoding: gzip" http://localhost:8000/

---

<!-- p.2 -->

场景 推荐值 原因
API 接口 1000-2000 大数据才压缩，节省 CPU
网站/博客 500-1000 更积极压缩，提升用户体验
实时数据 关闭或 5000+ 频繁小数据，不值得压缩
示例
minimum_size 设置建议
与 CDN 配合
如果使用 CDN，通常只在一层启用压缩：
HTTP/1.1 200 OK
Content-Encoding: gzip
from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware
app = FastAPI()
# 大于 1000 字节才压缩
app.add_middleware(GZipMiddleware, minimum_size=1000)
@app.get("/small")
async def small_data():
# 小数据，不压缩
return {"status": "ok"}
@app.get("/large")
async def large_data():
# 大数据，会被压缩
data = {"items": [{"id": i, "name": f"item_{i}"} for i in range(1000)]}
return data
应用层启用压缩 + CDN 层启用压缩 = 浪费 CPU
应用层禁用 + CDN 层启用 = 推荐
# 方案 1：应用层启用，CDN 禁用（明确说明）
app.add_middleware(GZipMiddleware, minimum_size=1000)
# 方案 2：应用层完全禁用，CDN 启用（推荐）
# 不添加 GZipMiddleware 即可完全禁用，而非设置超大值
# 错误示例（不推荐）：app.add_middleware(GZipMiddleware, minimum_size=100000)
# 正确示例：无需添加该中间件

---

<!-- p.3 -->

特性 GZip Brotli
压缩率 较好 更好（高 15-25%）
浏览器支持 所有 现代浏览器
性能 较快 略慢
要点 说明
minimum_size 根据场景调整，API 偏大，网站偏小
浏览器自动解压缩 开发者无需处理
与 CDN 配合 只用一层压缩即可
Brotli 需要 pip install brotli
GZip vs Brotli
Brotli 需要安装库（Starlette 会自动使用）：
总结
建议：
API 接口： minimum_size=1000-2000
网站/博客： minimum_size=500
使用 CDN 时：考虑只在 CDN 层启用
pip install brotli
# 启用 Brotli 压缩（需先 pip install brotli）
from starlette.middleware.compression import CompressionMiddleware
app = FastAPI()
# CompressionMiddleware 会自动检测 brotli 并优先使用，同时兼容 gzip
app.add_middleware(CompressionMiddleware, minimum_size=1000)
