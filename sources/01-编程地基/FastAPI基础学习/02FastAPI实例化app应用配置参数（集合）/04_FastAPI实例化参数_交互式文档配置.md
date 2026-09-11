# 04_FastAPI实例化参数_交互式文档配置

> **素材来源**：`raw/FastAPI基础学习文档/FastAPI基础学习文档\02FastAPI实例化app应用配置参数（集合）\04_FastAPI实例化参数_交互式文档配置.pdf`
> **页数**：7（其中无文本页 1 页，多为截图/图示）
> **正文规模**：约 5,010 字符，其中汉字 1,566 个
> **说明**：本文件由 `tools/extract_sources.py` 自动抽取，仅作写书素材，未做人工校订；引用时请以原文为准。

---
<!-- p.1 -->

FastAPI 实例化参数：交互式文档配置
本文档介绍 FastAPI 实例化时配置 OpenAPI 文档与交互界面的参数。FastAPI 会自动为每个 API 生成交
互式文档，包括 Swagger UI、Redoc 和 OpenAPI Schema，这些文档的访问路径和显示内容都可以通
过参数定制。
openapi_url 参数
openapi_url 参数设置 OpenAPI Schema 文件的访问路径。这个 JSON 文件包含了 API 的完整结构定
义，其他工具可以据此生成客户端代码。设为 None 可以完全关闭 OpenAPI Schema 的生成。
修改 openapi_url 路径后，Swagger UI 和 Redoc 会自动读取新路径的 Schema 文件，无需额外配
置。
代码解释：
openapi_url="/openapi.json" 设置 OpenAPI Schema 文件的访问路径
默认为 "/openapi.json"
设为 None 可以完全关闭 OpenAPI Schema 的生成
关闭后，默认配置下 Swagger UI 和 Redoc 会因无法读取 Schema 而无法正常工作（若通过外部
挂载已生成的 Schema 文件，仍可展示文档）。
这个 JSON 文件包含了 API 的完整结构定义
其他工具（如代码生成器）可以据此生成客户端 SDK
openapi_tags 参数
openapi_tags 参数用于在文档中定义分组标签，可以对 API 端点进行分类展示，使文档更加清晰有
序。
代码解释：
openapi_tags 定义分组标签列表
每个标签是一个字典，包含 name 和可选的 description
app = FastAPI(openapi_url="/openapi.json")
app = FastAPI(
openapi_tags=[
{"name": "用户", "description": "用户相关操作"},
{"name": "商品", "description": "商品相关操作"},
{"name": "订单", "description": "订单相关操作"}
]
)

---

<!-- p.2 -->

name 是标签的名称，用于在文档中显示
description 是标签的描述，说明该组包含哪些操作
使用时可在路由装饰器中通过 tags 参数指定标签名称，若标签名称已在 openapi_tags 中定
义，文档会显示对应的描述；若未定义，标签仍会显示但无描述信息
例如： @app.get("/users", tags=["用户"])
docs_url 参数
docs_url 参数控制 Swagger UI 文档的访问路径。Swagger UI 提供了交互式的 API 文档界面，可以在
页面上直接测试 API 调用。
代码解释：
docs_url="/docs" 设置 Swagger UI 的访问路径
默认为 "/docs"
设为 None 可以关闭 Swagger UI
关闭后，访问 /docs 会返回 404
Swagger UI 提供了交互式的文档界面
用户可以在页面上直接填写参数并发送请求测试 API
redoc_url 参数
redoc_url 参数控制 Redoc 文档的访问路径。Redoc 是另一种 API 文档界面，风格更加简洁美观。
代码解释：
redoc_url="/redoc" 设置 Redoc 的访问路径
默认为 "/redoc"
设为 None 可以关闭 Redoc
Redoc 提供了另一种风格的文档界面
与 Swagger UI 不同，Redoc 更侧重于文档展示而非交互测试
swagger_ui_parameters 参数
swagger_ui_parameters 参数允许自定义 Swagger UI 的显示参数和行为配置。
app = FastAPI(docs_url="/docs")
app = FastAPI(redoc_url="/redoc")

---

<!-- p.3 -->

代码解释：
swagger_ui_parameters 是一个字典，用于自定义 Swagger UI 的行为
deepLinking: True 开启深度链接，URL 会反映当前展开的端点
displayOperationId: True 在文档中显示每个端点的操作 ID
defaultModelsExpandDepth: 2 默认展开的模型层级深度
persistAuthorization: True 刷新页面后保留授权信息
filter: True 显示过滤框，可以快速搜索端点
这些参数直接传递给 Swagger UI 的配置选项
servers 参数
servers 参数定义多个服务端点，文档右上角会显示一个下拉菜单，方便开发者在不同环境之间切换。
代码解释：
servers 列表定义多个服务端点
每个服务端点是一个字典，包含 url 和可选的 description
url 是服务的基本地址
description 是对该环境的描述
文档右上角会显示下拉菜单，可以在不同环境之间切换
方便开发者（前端 / 后端 / 测试）针对不同环境快速切换并测试 API
注意：FastAPI 仅在文档界面展示这些服务端点选项，不会自动修改 API 请求的实际访问地址，开
发者 / 测试人员需手动确保请求地址与选中的环境匹配，或在代码中自行实现环境路由逻辑。
关闭交互式文档
app = FastAPI(
swagger_ui_parameters={
"deepLinking": True, # 开启深度链接，URL 会反映当前展开的端点
"displayOperationId": True, # 在文档中显示每个端点的操作 ID
"defaultModelsExpandDepth": 2, # 默认展开的模型层级深度
"persistAuthorization": True, # 刷新页面后保留授权信息
"filter": True # 显示过滤框，可以快速搜索端点
}
)
app = FastAPI(
servers=[
{"url": "http://localhost:8000", "description": "本地开发环境"},
{"url": "https://api.example.com", "description": "生产环境"}
]
)

---

<!-- p.4 -->

在生产环境中，建议根据安全要求关闭 API 文档（或通过权限控制限制文档访问），避免未授权人员获
取 API 结构信息。若需保留代码生成能力，可在部署前生成 OpenAPI Schema 文件并保存到本地，关闭
openapi_url 后仍可手动使用该文件
代码解释：
docs_url=None 禁用了 Swagger UI，访问 /docs 会返回 404
redoc_url=None 禁用了 Redoc，访问 /redoc 会返回 404
openapi_url=None 禁用了 OpenAPI Schema 文件的生成
这三个参数分别控制三种文档资源的访问
对于安全要求较高的生产环境是推荐的做法
环境变量动态控制
通过环境变量动态控制文档开关，可以在开发和生产环境中使用同一套代码。
代码解释：
使用三元表达式判断环境变量 ENVIRONMENT 的值
当环境为 production 时，三个文档路径都设为 None 关闭文档
其他环境（如 development 、 staging ）则正常开启文档
这样在开发和生产环境中不需要手动修改代码
os.getenv("ENVIRONMENT") 读取系统环境变量（若未设置该变量，返回 None ，此时文档会默
认开启，生产环境需确保显式设置 ENVIRONMENT=production ）
适用于开发和生产环境共用同一套代码的场景
完整配置示例
以下是一个综合展示所有文档配置参数的完整示例：
app = FastAPI(
docs_url=None, # 关闭 Swagger UI 文档
redoc_url=None, # 关闭 Redoc 文档
openapi_url=None # 关闭 OpenAPI Schema 文件
)
import os
from fastapi import FastAPI
# 显式设置默认值为非生产环境，生产环境必须显式指定 ENVIRONMENT=production
env = os.getenv("ENVIRONMENT", "development")
app = FastAPI(
docs_url="/docs" if env != "production" else None,
redoc_url="/redoc" if env != "production" else None,
openapi_url="/openapi.json" if env != "production" else None
)

---

<!-- p.5 -->

代码解释：
title 设置 API 文档的标题为"我的 API 文档"
description 使用 Markdown 格式描述 API 的功能特性
version 设置版本号为 "1.0.0"
docs_url="/docs" 设置 Swagger UI 的访问路径
redoc_url="/redoc" 设置 Redoc 的访问路径
openapi_url="/openapi.json" 设置 OpenAPI Schema 的访问路径
terms_of_service 设置服务条款 URL
contact 字典包含联系人名称和邮箱
from fastapi import FastAPI
app = FastAPI(
title="我的 API 文档",
description="""
这是一个基于 FastAPI 的 API 文档示例。
## 功能特性
- 用户管理
- 订单处理
""",
version="1.0.0",
docs_url="/docs",
redoc_url="/redoc",
openapi_url="/openapi.json",
terms_of_service="https://example.com/terms",
contact={
"name": "技术支持",
"email": "support@example.com"
},
license_info={
"name": "MIT License",
"url": "https://opensource.org/licenses/MIT"
},
servers=[
{"url": "http://localhost:8000", "description": "本地开发环境"},
{"url": "https://api.example.com", "description": "生产环境"}
],
openapi_tags=[
{"name": "用户", "description": "用户相关操作"},
{"name": "商品", "description": "商品相关操作"}
],
swagger_ui_parameters={
"deepLinking": True,
"displayOperationId": True,
"defaultModelsExpandDepth": 2,
"persistAuthorization": True
}
)
@app.get("/")
def root():
return {"message": "Hello World"}

---

<!-- p.6 -->

license_info 字典包含许可证名称和 URL
servers 列表定义本地和生产两个服务端点
openapi_tags 定义"用户"和"商品"两个分组标签
swagger_ui_parameters 自定义 Swagger UI 的显示参数
@app.get("/") 定义一个简单的路由用于测试
