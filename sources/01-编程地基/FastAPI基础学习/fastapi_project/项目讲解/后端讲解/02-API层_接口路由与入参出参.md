# API 层讲解（api 路由与请求响应）

> 目录：`fastapi_project/backend/app/api/`

## 1. API 层的职责
API 层主要负责：
- 定义路由（URL、HTTP 方法）
- 解析参数（Query/Form/Body）
- 注入依赖（如：DB Session、Service、current_user）
- 把 Service 层返回的结果包装为统一响应 `Result`

API 层尽量不写复杂业务逻辑，把业务规则下沉到 Service。

## 2. 总路由聚合
总路由：`backend/app/api/router.py`
- 把各子路由 include 进来

路由模块：
- `user_api.py`：用户
- `article_api.py`：文章
- `comment_api.py`：评论
- `favorite_api.py`：收藏
- `personal_api.py`：个人中心
- `index_api.py`：首页

## 3. 统一响应 Result
统一响应模型：`backend/app/common/result.py`

API 层常见写法：
- service 返回 dict：`{"code":..., "msg":..., "data":...}`
- API 层：`return Result(code=r["code"], msg=r["msg"], data=r.get("data"))`

## 4. 鉴权依赖在 API 层的使用
鉴权依赖：`backend/app/dependencies/current_user.py`

两种常用注入方式：
- 强制登录：`Depends(get_current_user)`
- 可选登录：`Depends(get_current_user_optional)`

说明：
- 未登录会抛 `HTTPException(401, ...)`
- 可选登录会捕获异常并返回 None

## 5. 各模块接口清单（按文件）

### 5.1 首页（index_api）
文件：`backend/app/api/index_api.py`
- `GET /api/`
  - Query：`page`（默认 1）、`article_type`（默认 recommend）、`keyword`（可选）
  - 返回：文章列表 + 栏目列表（label_types）

对应 service：复用 `ArticleService.get_list()`

### 5.2 用户（user_api）
文件：`backend/app/api/user_api.py`
- `GET /api/user/vcode`
  - 返回图片验证码（jpeg bytes）
  - 并通过 `Set-Cookie` 写入 cookie `vcode`（有效期 300s）
- `POST /api/user/ecode`
  - Body：邮箱
  - 返回：邮箱验证码（当前实现开发环境直接返回 code；可扩展为真实邮件发送）
- `POST /api/user/reg`
  - Body：username/password/second_password/ecode
  - 返回：注册结果
- `POST /api/user/login`
  - Body：username/password/vcode
  - 校验通过后：把 service 返回的 token 写入 cookie `token`
- `POST /api/user/logout`
  - 删除 cookie `token`
- `GET /api/user/me`
  - 需要 Authorization Bearer token
  - 返回当前用户信息

### 5.3 文章（article_api）
文件：`backend/app/api/article_api.py`
- `GET /api/article/detail`
  - Query：`article_id`
  - 可选登录：如果登录则额外返回 `is_favorite`（是否收藏）
- `GET /api/article/new-page`
  - 需要登录
  - 返回：草稿列表 + label_types/article_types/article_tags
- `POST /api/article/drafted`
  - 需要登录
  - Body：草稿 id
  - 返回草稿详情
- `POST /api/article/save`
  - 需要登录
  - Body：文章保存请求（含 drafted、标签、类型、头图相对路径等）
  - 由 service 完成“发布/草稿校验 + 归属校验 + insert/update”
- `POST /api/article/upload`
  - 需要登录
  - Form：`article_id` + File：`file`
  - 保存到 `settings.upload_dir_abs`，压缩为 jpg
  - 数据库存相对路径 `article/header/<name>.jpg`
  - 返回对外 url：`/images/article/header/<name>.jpg`

### 5.4 评论（comment_api）
文件：`backend/app/api/comment_api.py`
- `GET|POST /api/comment/ueditor`
  - `GET ?action=config`：返回评论编辑器配置 `settings.comment_ueditor_config`
  - `POST action=image`：上传图片（目前路径写入 `resource/upload`，并返回 `/upload/<name>`）
- `POST /api/comment/add`
  - 需要登录
  - Body：article_id/content
  - 自动读取客户端 IP：`request.client.host`
- `POST /api/comment/reply`
  - 需要登录
  - Body：article_id/content/reply_id/base_reply_id
  - 自动读取 IP

说明：评论/回复内容长度在 Service 层统一校验。

### 5.5 收藏（favorite_api）
文件：`backend/app/api/favorite_api.py`
- `POST /api/favorite/update_status`
  - 需要登录
  - Body：article_id + canceled（0=收藏，1=取消）

### 5.6 个人中心（personal_api）
文件：`backend/app/api/personal_api.py`
- `GET /api/personal/`
  - 需要登录
  - Query：
    - `type_name`：article / favorite / comment
    - `drafted`：仅当 type_name=article 时有效（1=已发布，0=草稿）
  - 返回：对应列表

## 6. API 层常见约定与注意点
- 认证 token：
  - `current_user.py` 从 `Authorization: Bearer <token>` 读取
  - `user_api.login` 目前把 token 写入 cookie（但其它接口依赖的是 Authorization 头）
  - 前端调用时需确保带 Authorization，否则会 401
- 文件上传：
  - 文章头图上传统一存到 `resource/images/article/header` 下
  - 图片对外访问统一 `/images/...`（由 main.py 静态挂载）

下一篇文档会从 Service 角度解释每个接口背后的业务校验、权限校验与数据编排。
