# FastAPI的文件处理

> **素材来源**：`raw/FastAPI基础学习文档/FastAPI基础学习文档\12FastAPI的文件处理\FastAPI的文件处理.pdf`
> **页数**：13（其中无文本页 1 页，多为截图/图示）
> **正文规模**：约 12,152 字符，其中汉字 1,415 个
> **说明**：本文件由 `tools/extract_sources.py` 自动抽取，仅作写书素材，未做人工校订；引用时请以原文为准。

---
<!-- p.1 -->

依赖 用途
python-multipart multipart/form-data 编码（文件上传必需）
aiofiles 异步文件读写（大文件必备）
pillow 图片缩略图处理
属性/方法 说明
file.filename 上传时的原始文件名
file.content_type MIME 类型，如 image/png
file.size
文件大小（字节），FastAPI 中该属性通常为 None，需通过读取内容或
文件系统获取实际大小。
await
file.read(size)
读取内容，不指定 size 则读全部
await
file.write(data)
写入内容
await
file.seek(offset)
移动指针（ read() 后需 seek(0) 重置）
await
file.close()
关闭文件（FastAPI 请求结束后自动关闭）
FastAPI 文件处理
FastAPI 提供了完整的文件处理能力，支持文件上传、下载、分块传输、断点续传、静态文件服务等。
本指南覆盖从基础到生产级别的全部场景。
环境准备
核心概念：UploadFile
UploadFile 是 FastAPI 对上传文件的封装类型，内部基于 SpooledTemporaryFile （内存与磁盘自
动切换的临时文件），支持流式读写，不会一次性将整个文件加载到内存。
UploadFile 常用属性和方法：
第一部分：文件上传
pip install python-multipart aiofiles pillow

---

<!-- p.2 -->

单文件上传（推荐方式）
请求示例
响应示例
关于 File(...) 装饰器：单个 UploadFile 参数时 File(...) 可省略，但建议始终加上以保
持代码一致性。多文件场景下 List[UploadFile] = File(...) 则是必需的。
三种保存方式对比
实际开发中有三种保存方式，根据场景选择：
from fastapi import FastAPI, UploadFile, File
import aiofiles
import uuid
from pathlib import Path
app = FastAPI()
UPLOAD_DIR = Path("./uploads")
UPLOAD_DIR.mkdir(exist_ok=True)
@app.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
file_ext = Path(file.filename).suffix or ".bin"
saved_name = f"{uuid.uuid4().hex}{file_ext}"
file_path = UPLOAD_DIR / saved_name
content = await file.read()
async with aiofiles.open(file_path, "wb") as buffer:
await buffer.write(content)
return {
"filename": saved_name,
"original": file.filename,
"size": len(content)
}
curl -X POST "http://127.0.0.1:8000/upload/" -F "file=@example.txt"
{
"filename": "a1b2c3d4e5f6.txt",
"original": "example.txt",
"size": 1024
}
# 方式一：一次性读取写入（简单但占用内存高）
content = await file.read()
with open(file_path, "wb") as f:
f.write(content)

---

<!-- p.3 -->

方式 内存占用 适用场景 推荐程度
一次性读写 高（全量加载） < 10MB 小文件 仅简单场景
aiofiles 异步写入 中（全量加载后异步写入） 一般生产环境 推荐
分块流式写入 极低（始终 1 个 chunk） GB 级超大文件 超大文件专用
多文件上传
请求示例
# 方式二：aiofiles 异步写入（全量读取后异步写入，推荐并发场景，避免阻塞事件循环）
content = await file.read()
async with aiofiles.open(file_path, "wb") as buffer:
await buffer.write(content)
# 方式三：分块流式写入（适合 GB 级超大文件）
CHUNK_SIZE = 1024 * 1024 # 1MB
async with aiofiles.open(file_path, "wb") as buffer:
while chunk := await file.read(CHUNK_SIZE):
await buffer.write(chunk)
from fastapi import FastAPI, File, UploadFile
from typing import List
app = FastAPI()
@app.post("/upload-multiple/")
async def upload_multiple(files: List[UploadFile] = File(...)):
results = []
for file in files:
content = await file.read()
results.append({
"filename": file.filename,
"content_type": file.content_type,
"size": len(content)
})
return {"files": results, "total": len(files)}
curl -X POST "http://127.0.0.1:8000/upload-multiple/" \
-F "files=@file1.txt" \
-F "files=@file2.txt" \
-F "files=@file3.pdf"

---

<!-- p.4 -->

文件验证（类型与大小）
注意： seek(0) 非常重要。 await file.read() 会移动文件指针到末尾，如果后续还需要读取
（如保存到磁盘），必须先 seek(0) 重置。
表单 + 文件混合上传
from fastapi import FastAPI, UploadFile, File, HTTPException
from pathlib import Path
app = FastAPI()
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/gif", "application/pdf",
"text/plain"}
MAX_FILE_SIZE = 10 * 1024 * 1024 # 10MB
@app.post("/upload-validated/")
async def upload_validated(file: UploadFile = File(...)):
if file.content_type not in ALLOWED_TYPES:
raise HTTPException(
status_code=400,
detail=f"不支持的类型: {file.content_type}"
)
content = await file.read()
if len(content) > MAX_FILE_SIZE:
raise HTTPException(
status_code=400,
detail=f"文件超过限制: {len(content)}/{MAX_FILE_SIZE} bytes"
)
await file.seek(0) # read() 后指针移至末尾，需重置才能再次使用
return {"filename": file.filename, "size": len(content)}
from fastapi import FastAPI, Form, File, UploadFile
from typing import List
app = FastAPI()
@app.post("/article/publish/")
async def publish_article(
title: str = Form(...),
author: str = Form(...),
tags: str = Form("general"),
is_public: bool = Form(True),
files: List[UploadFile] = File(default=[])
):
return {
"title": title,
"author": author,
"tags": tags,

---

<!-- p.5 -->

请求示例
第二部分：文件下载
FileResponse （小文件）
FileResponse 直接返回静态文件，自动设置 Content-Type 、 Content-Length 、 Content-
Disposition ：
请求示例
"is_public": is_public,
"files": [{"name": f.filename, "type": f.content_type} for f in files]
}
curl -X POST "http://127.0.0.1:8000/article/publish/" \
-F "title=FastAPI 教程" \
-F "author=张三" \
-F "tags=tutorial,python" \
-F "is_public=true" \
-F "files=@readme.txt" \
-F "files=@diagram.png"
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path
app = FastAPI()
UPLOAD_DIR = Path("./uploads")
@app.get("/download/{filename}")
async def download_file(filename: str):
file_path = UPLOAD_DIR / filename
if not file_path.exists():
raise HTTPException(status_code=404, detail="文件不存在")
return FileResponse(
path=file_path,
filename=filename,
media_type="application/octet-stream"
)
curl -O "http://127.0.0.1:8000/download/example.txt"

---

<!-- p.6 -->

StreamingResponse （大文件）
StreamingResponse 以流式方式返回，边读边发，内存占用极低：
while chunk := await f.read(...) 是 walrus 运算符（海象运算符），在循环中同时完成赋
值和判断，Python 3.8+ 支持。
断点续传（Range 请求）
实现完整的断点续传，支持客户端从中断位置恢复下载：
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
import aiofiles
from pathlib import Path
app = FastAPI()
UPLOAD_DIR = Path("./uploads")
@app.get("/download-large/{filename}")
async def download_large(filename: str):
file_path = UPLOAD_DIR / filename
if not file_path.exists():
raise HTTPException(status_code=404, detail="文件不存在")
async def file_iterator():
async with aiofiles.open(file_path, mode="rb") as f:
while chunk := await f.read(1024 * 1024): # 每次 1MB
yield chunk
return StreamingResponse(
file_iterator(),
media_type="application/octet-stream",
headers={"Content-Disposition": f"attachment; filename={filename}"}
)
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse
import aiofiles
from pathlib import Path
app = FastAPI()
UPLOAD_DIR = Path("./uploads")
UPLOAD_DIR.mkdir(exist_ok=True)
@app.get("/download-resumable/{filename}")
async def download_resumable(request: Request, filename: str):
file_path = UPLOAD_DIR / filename
if not file_path.exists():

---

<!-- p.7 -->

raise HTTPException(status_code=404, detail="文件不存在")
file_size = file_path.stat().st_size
async def range_iterator(start: int = 0, end: int = file_size - 1):
try:
async with aiofiles.open(file_path, mode="rb") as f:
# 边界校验：起始位置超出文件大小则直接返回空
if start >= file_size:
yield b""
return
# 修正end的边界（防止end超过文件大小）
end = min(end, file_size - 1)
await f.seek(start)
remaining = end - start + 1
while remaining > 0:
chunk = await f.read(min(1024 * 1024, remaining))
if not chunk:
break
yield chunk
remaining -= len(chunk)
except Exception as e:
raise HTTPException(status_code=500, detail=f"文件读取失败: {str(e)}")
range_header = request.headers.get("Range")
if range_header:
try:
_, spec = range_header.split("=")
start_str, end_str = spec.split("-")
start = int(start_str) if start_str.strip() else 0
end = min(int(end_str) if end_str.strip() else file_size - 1,
file_size - 1)
except (ValueError, IndexError):
raise HTTPException(status_code=416, detail="Range 无效")
resp = StreamingResponse(
range_iterator(start, end),
status_code=206,
media_type="application/octet-stream"
)
resp.headers["Content-Range"] = f"bytes {start}-{end}/{file_size}"
resp.headers["Content-Length"] = str(end - start + 1)
else:
resp = StreamingResponse(
range_iterator(),
status_code=200,
media_type="application/octet-stream"
)
resp.headers["Content-Length"] = str(file_size)
resp.headers["Accept-Ranges"] = "bytes"
return resp

---

<!-- p.8 -->

场景 状态码 Content-Range Content-Length
完整下载 200 无 文件总大小
部分下载 206 bytes 1048576-2097151/5242880 1048576
无效 Range 416 — —
完整下载
断点续传（从第 1MB 处开始）
响应头对比
第三部分：静态文件挂载
通过 app.mount() 将目录直接挂载为静态文件服务，无需手动编写每个文件的下载接口：
适合 100MB 以下的图片、CSS、JS 等静态资源；100MB 以上大文件推荐 StreamingResponse
（支持分块下载、断点续传，内存占用更低）。
第四部分：图片预览
上传图片并生成缩略图
curl -X GET "http://127.0.0.1:8000/download-resumable/large_file.zip" -o
large_file.zip
curl -X GET "http://127.0.0.1:8000/download-resumable/large_file.zip" \
-H "Range: bytes=1048576-" -o part2.zip
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
app = FastAPI()
# 访问 /static/filename.txt -> 返回 ./uploads/filename.txt
app.mount("/static", StaticFiles(directory="./uploads"), name="uploads")
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
import io
import uuid
import aiofiles
from PIL import Image
from pathlib import Path
app = FastAPI()
UPLOAD_DIR = Path("./uploads")

---

<!-- p.9 -->

请求示例
UPLOAD_DIR.mkdir(exist_ok=True)
@app.post("/upload-image/")
async def upload_image(file: UploadFile = File(...)):
if not file.content_type.startswith("image/"):
raise HTTPException(status_code=400, detail="只支持图片文件")
file_ext = Path(file.filename).suffix or ".png"
saved_name = f"{uuid.uuid4().hex}{file_ext}"
file_path = UPLOAD_DIR / saved_name
content = await file.read()
async with aiofiles.open(file_path, "wb") as buffer:
await buffer.write(content)
return {
"filename": saved_name,
"preview_url": f"/preview/{saved_name}",
"download_url": f"/download/{saved_name}"
}
@app.get("/preview/{filename}")
async def preview_image(filename: str, width: int = 200, height: int = 200):
file_path = UPLOAD_DIR / filename
if not file_path.exists():
raise HTTPException(status_code=404, detail="图片不存在")
try:
with Image.open(file_path) as img: # 上下文管理器自动关闭
img.thumbnail((width, height))
buffer = io.BytesIO()
img.save(buffer, format=img.format or "PNG")
buffer.seek(0)
return StreamingResponse(
buffer,
media_type=f"image/{img.format.lower()}" if img.format else
"image/png",
headers={"Cache-Control": "public, max-age=86400"}
)
except Exception as e:
raise HTTPException(status_code=500, detail=f"图片处理失败: {str(e)}")
# 上传图片
curl -X POST "http://127.0.0.1:8000/upload-image/" -F "file=@photo.jpg"
# 预览缩略图（默认 200x200）
curl "http://127.0.0.1:8000/preview/a1b2c3d4.jpg"
# 自定义尺寸
curl "http://127.0.0.1:8000/preview/a1b2c3d4.jpg?width=400&height=300"

---

<!-- p.10 -->

PIL.Image.thumbnail() 保持宽高比缩放，不会拉伸变形。 Cache-Control: public, max-
age=86400 设置 24 小时缓存，减少重复计算。
第五部分：安全与最佳实践
路径穿越防护
用户上传的文件名可能包含 ../ 等路径遍历序列，直接拼接会导致目录穿越漏洞：
防护分三层：① Path().name 去除目录遍历；② 正则过滤非法字符；③ is_relative_to() 二次验
证。
资源管理
UploadFile 和 aiofiles 的文件句柄会在请求处理完毕后自动关闭，无需手动 close() （手动关闭
反而可能在后续使用时出错）：
from fastapi import FastAPI, HTTPException, UploadFile, File
from pathlib import Path
import re
app = FastAPI()
UPLOAD_DIR = Path("./uploads").resolve()
def safe_filename(filename: str) -> str:
name = Path(filename).name # 提取文件名，去除所有目录层级
name = re.sub(r"[^\w\-.]", "_", name) # 仅保留安全字符
return name or "unnamed"
@app.post("/upload-safe/")
async def upload_safe(file: UploadFile = File(...)):
safe_name = safe_filename(file.filename)
file_path = UPLOAD_DIR / safe_name
# 二次验证：resolve 后检查是否仍在允许目录内
if not file_path.resolve().is_relative_to(UPLOAD_DIR):
raise HTTPException(status_code=400, detail="非法文件路径")
content = await file.read()
async with aiofiles.open(file_path, "wb") as buffer:
await buffer.write(content)
return {"filename": safe_name}
# 推荐：让 FastAPI 自动管理生命周期
@app.post("/upload/")
async def upload(file: UploadFile = File(...)):
content = await file.read()

---

<!-- p.11 -->

方式 适用场景 内存占用 注意
bytes = File(...) < 10MB 临时测试 高 整个文件读入内存
UploadFile 所有场景 低（流式） 推荐优先使用
List[UploadFile] 多文件上传 低 List[...] = File(...)
文件清理策略
生产环境建议使用定时任务（APScheduler / cron）而非 HTTP 接口触发清理。
用法对比速查表
上传方式
# 直接使用，无需手动 close()
return {"size": len(content)}
# 如果需要手动管理资源，使用上下文管理器
from contextlib import asynccontextmanager
@asynccontextmanager
async def managed_file(file: UploadFile):
try:
yield await file.read()
finally:
await file.close() # 仅在需要提前关闭时才手动处理
from fastapi import FastAPI
from pathlib import Path
import time
app = FastAPI()
UPLOAD_DIR = Path("./uploads")
MAX_AGE_HOURS = 24
@app.get("/cleanup/")
async def cleanup_files():
now = time.time()
deleted = 0
for fp in UPLOAD_DIR.iterdir():
if fp.is_file() and (now - fp.stat().st_mtime) / 3600 > MAX_AGE_HOURS:
fp.unlink()
deleted += 1
return {"deleted": deleted}

---

<!-- p.12 -->

方式 适用场景 内存占用 断点续传
FileResponse < 100MB 静态文件 低 否
StreamingResponse 大文件/GB 级 极低（分块） 支持（需手动实现 Range）
下载方式
总结
1. 上传优先用 UploadFile ： bytes 方式仅适合简单测试，大文件必须用流式方式
2. 保存用 aiofiles ：异步写入不阻塞事件循环，超大文件用分块流式写入
3. 始终验证：文件类型白名单 + 大小限制，防止恶意上传和内存溢出
4. seek(0) 别忘了：每次 read() 后指针移到末尾，需要重置才能再次使用
5. 下载大文件用 StreamingResponse ： FileResponse 适合小文件，大文件分块下载内存友好
6. 断点续传：解析 Range 请求头，返回 206 + Content-Range 响应头
7. 安全防护：始终对文件名做 safe_filename() 处理，防止路径穿越
