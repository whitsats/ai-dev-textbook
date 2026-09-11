# 08_FastAPI实例化参数_生产环境最佳实践

> **素材来源**：`raw/FastAPI基础学习文档/FastAPI基础学习文档\02FastAPI实例化app应用配置参数（集合）\08_FastAPI实例化参数_生产环境最佳实践.pdf`
> **页数**：3（其中无文本页 1 页，多为截图/图示）
> **正文规模**：约 1,128 字符，其中汉字 394 个
> **说明**：本文件由 `tools/extract_sources.py` 自动抽取，仅作写书素材，未做人工校订；引用时请以原文为准。

---
<!-- p.1 -->

FastAPI 实例化参数：生产环境最佳实践
本文档介绍 FastAPI 实例化参数在生产环境中的安全与优化配置。
Debug 模式
注意事项
开启后会显示详细的错误堆栈信息，便于排查问题
生产环境必须关闭（FastAPI 中 debug 参数默认值为 False ，建议显式设置 debug=False 以增
强代码可读性）
如果定义了全局异常处理器，不建议同时开启 Debug 模式（开启后，未被捕获的异常会返回
FastAPI 内置的详细堆栈信息，而非自定义异常处理器的响应，导致异常处理逻辑失效）
文档访问控制
环境变量动态控制
推荐通过环境变量动态控制文档访问：
完全关闭文档
from fastapi import FastAPI
app = FastAPI(debug=True)
@app.get("/")
def index():
return {"message": "欢迎学习 FastAPI"}
import os
from fastapi import FastAPI
# 先标准化环境变量值，默认设为非生产
env = os.getenv("ENVIRONMENT", "").strip().lower()
app = FastAPI(
docs_url="/docs" if env != "production" else None,
redoc_url="/redoc" if env != "production" else None,
openapi_url="/openapi.json" if env != "production" else None
)

---

<!-- p.2 -->

检查项 推荐配置
Debug 模式 debug=False 或不设置
Swagger UI 生产环境设为 None
Redoc 生产环境设为 None
OpenAPI Schema 生产环境设为 None
CORS 配置具体的允许域名，不使用 ["*"]
异常处理 确保全局异常处理器不泄露敏感信息
生产环境安全检查清单
最佳实践
生产环境务必关闭 Debug 模式：避免敏感信息泄露
使用环境变量区分环境：如 ENVIRONMENT=production ，不要硬编码
CORS 不要使用通配符： allow_origins=["*"] 会带来安全风险
文档页面仅在开发环境开启：生产环境关闭以减少攻击面
异常信息脱敏处理：自定义异常处理器中避免返回原始堆栈或配置信息
from fastapi import FastAPI
app = FastAPI(
docs_url=None,
redoc_url=None,
openapi_url=None
)
