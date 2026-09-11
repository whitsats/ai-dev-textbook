# 02_FastAPI实例化参数_基础元数据配置

> **素材来源**：`raw/FastAPI基础学习文档/FastAPI基础学习文档\02FastAPI实例化app应用配置参数（集合）\02_FastAPI实例化参数_基础元数据配置.pdf`
> **页数**：6（其中无文本页 1 页，多为截图/图示）
> **正文规模**：约 3,301 字符，其中汉字 1,200 个
> **说明**：本文件由 `tools/extract_sources.py` 自动抽取，仅作写书素材，未做人工校订；引用时请以原文为准。

---
<!-- p.1 -->

FastAPI 实例化参数：基础元数据配置
本文档介绍 FastAPI 实例化时控制 API 文档信息的元数据参数，这些参数用于在 Swagger UI 和 Redoc
中展示 API 的描述性信息。
debug 参数
debug 参数控制调试模式开关，当设置为 True 时，FastAPI 会返回详细的错误堆栈信息，便于开发者
排查问题。
代码解释：
debug=True 开启调试模式
当代码发生错误时，FastAPI 会返回详细的错误堆栈信息
帮助开发者快速定位问题根源
生产环境务必将此参数设为 False ，否则会暴露敏感的服务器信息
如果已经自定义了全局异常处理器（ @app.exception_handler ），当 debug=True 且请求触发
未被捕获的异常时，FastAPI 内置的调试错误页面会优先显示，导致自定义异常处理器失效；仅当
debug=False 时，自定义全局异常处理器才会生效
title 参数
title 参数设置 API 文档的标题，会显示在 Swagger UI 和 Redoc 页面的顶部。
代码解释：
title 设置 API 文档的标题
标题会显示在 Swagger UI 和 Redoc 页面的顶部
默认为 "FastAPI"
建议设置为清晰的应用名称或业务名称
summary 参数
summary 参数提供 API 文档的简短摘要，位于标题下方。
app = FastAPI(debug=True)
app = FastAPI(title="用户管理系统 API")

---

<!-- p.2 -->

代码解释：
summary 提供一段简短的摘要文字
摘要位于标题下方，是对 API 功能的简洁描述
默认为 None
适用于补充 title 无法完全表达的信息
description 参数
description 参数提供 API 的详细描述，支持 Markdown 格式，可以包含多行文本和格式化内容。
代码解释：
description 提供详细的 API 描述
支持 Markdown 格式，可以写多行文本
可以包含标题（ ## ）、列表（ - ）、代码块等 Markdown 语法
默认为空字符串
常用于介绍项目背景、功能模块、技术栈等信息
会在 Swagger UI 和 Redoc 中以富文本形式展示
version 参数
version 参数声明当前 API 的版本号。
app = FastAPI(
title="用户管理系统 API",
summary="提供用户增删改查接口"
)
app = FastAPI(
title="用户管理系统 API",
summary="提供用户增删改查接口",
description="""
这是一个基于 FastAPI 开发的后端 API。
## 功能模块
- 用户管理
- 权限控制
## 技术栈
- FastAPI
- PostgreSQL
- Redis
"""
)

---

<!-- p.3 -->

代码解释：
version 声明当前 API 的版本号
默认为 "0.1.0"
建议遵循语义化版本规范（如 "1.0.0"、"2.1.3"）
版本号会显示在 API 文档中，方便使用者了解 API 的演进
terms_of_service 参数
terms_of_service 参数设置服务条款的 URL 链接，会在文档底部显示。
代码解释：
terms_of_service 设置服务条款的 URL 链接
默认为 None ，不显示服务条款
URL 链接会显示在 API 文档底部
适用于需要声明使用条款的应用场景
contact 参数
contact 参数用于展示联系人信息，支持 name （必填，联系人 / 团队名称）、 email （可选，联系邮
箱）、 url （可选，联系页面 URL）三个字段，传入字典时至少需包含 name 字段以保证展示有效性。
代码解释：
contact 字典用于展示联系人信息
name 字段指定联系人或团队的名称
email 字段指定联系邮箱地址
app = FastAPI(
title="用户管理系统 API",
version="1.0.0"
)
app = FastAPI(
title="用户管理系统 API",
terms_of_service="https://example.com/terms"
)
app = FastAPI(
title="用户管理系统 API",
contact={
"name": "技术支持团队",
"email": "support@example.com",
"url": "https://example.com/contact"
}
)

---

<!-- p.4 -->

url 字段指定联系页面的 URL
默认为 None ，不显示联系人信息
这些信息会显示在 API 文档中
license_info 参数
license_info 参数用于展示许可证信息，支持 name （必填，许可证名称）、 url （可选，许可证详
情 URL）两个字段，传入字典时至少需包含 name 字段。
代码解释：
license_info 字典用于展示许可证信息
name 字段指定许可证的名称（如 "MIT License"、"Apache 2.0"）
url 字段指定许可证的详细 URL
默认为 None ，不显示许可证信息
会在 API 文档中显示开源许可证信息
deprecated 参数
deprecated 参数用于标记整个 API 是否已废弃，设为 True 时会在文档中显示废弃提示。
代码解释：
deprecated 标记整个 API 是否已废弃
设为 True 时，文档中会显示废弃警告
默认为 False ，设为 True 时，API 文档中会显著标记该 API 已废弃（Swagger UI 会显示红色废
弃标签）
适用于需要下线但暂时保留的旧版 API
建议同时在 description 中说明新的替代 API
综合配置示例
app = FastAPI(
title="用户管理系统 API",
license_info={
"name": "MIT License",
"url": "https://opensource.org/licenses/MIT"
}
)
app = FastAPI(
title="旧版用户 API",
deprecated=True
)

---

<!-- p.5 -->

以下是一个完整的基础元数据配置示例：
代码解释：
title 设置 API 文档标题为"用户管理系统 API"
summary 提供简短摘要："提供用户增删改查接口"
description 使用 Markdown 格式描述功能模块
version 设置版本号为 "1.0.0"
terms_of_service 设置服务条款 URL
contact 字典包含三个键： name 是联系人名称， email 是邮箱， url 是联系页面
license_info 字典包含许可证名称和 URL
这些元数据都会显示在 Swagger UI 和 Redoc 文档中
app = FastAPI(
title="用户管理系统 API",
summary="提供用户增删改查接口",
description="""
这是一个基于 FastAPI 开发的后端 API。
## 功能模块
- 用户管理
- 权限控制
""",
version="1.0.0",
terms_of_service="https://example.com/terms",
contact={
"name": "技术支持",
"email": "support@example.com",
"url": "https://example.com"
},
license_info={
"name": "MIT License",
"url": "https://opensource.org/licenses/MIT"
}
)
