# Service 层讲解（业务编排与校验）

> 目录：`fastapi_project/backend/app/services/`

## 1. Service 层的职责
Service 层是后端业务的“核心编排层”，主要负责：
- 业务规则校验（长度、必填、草稿/发布规则、状态规则）
- 权限/归属校验（是否本人操作）
- 组装 DAO 的查询结果（把多表数据拼成前端需要的结构）
- 做轻量的数据格式化（如图片 URL 归一、标签展示格式）

它不直接关心 HTTP（交给 API 层），也尽量不写复杂 SQL（交给 DAO 层）。

## 2. 依赖注入如何拿到 Service
依赖组装分两层：
- `dependencies/api_dp/*`：FastAPI Depends 的入口（注入 db，再调用 service_dp）
- `dependencies/service_dp/*`：手动把 DAO 实例注入到 Service 构造函数

例：文章 Service
- `dependencies/api_dp/article_dp.py` -> `get_article_service(db)`
- `dependencies/service_dp/article_dp.py` -> `ArticleService(db, ArticleDao(db), UserDao(db), CommentDao(db), FavoriteDao(db))`

好处：
- 结构清晰：service 的依赖一眼可见
- 后续若替换 DAO 或增加缓存组件，改动集中

## 3. ArticleService（文章业务）
文件：`backend/app/services/article_service.py`

### 3.1 列表与搜索：get_list
- 输入：page, article_type, keyword(可选)
- DAO：
  - keyword 存在：`ArticleDao.search_article`
  - 否则：`ArticleDao.find_article`
- 输出：list[dict]

附带处理：
- `article_image` 归一成对外 URL
  - 兼容旧数据：数据库可能只存 `article_001.jpg`，会补成 `article/header/article_001.jpg`
  - 再拼接前缀 `/images/`
- `article_tag` 展示格式：把 `,` 替换成 ` · `

### 3.2 详情：get_detail
- DAO：`ArticleDao.get_article_detail`（注意：会把 browse_num +1 并 commit）
- 追加信息：
  - 作者昵称：`UserDao.find_by_userid`
  - 评论列表与评论数：`CommentDao.get_comment_user_list`、`get_article_comment_count`
  - 是否收藏：若 current_user 存在则调用 `FavoriteDao.user_if_favorite`
- 返回结构：符合前端文章详情页展示需求

### 3.3 新建页数据：get_new_page_data
- 返回草稿列表 + label_types/article_types/article_tags

### 3.4 保存文章：save_article
这是文章发布/存草稿的核心逻辑：
- 先做归属校验 `_check_ownership(article_id, user_id)`：
  - `article_id <= -1` 视为新建，不校验
  - 否则从 DAO 查 owner_id，必须等于当前 user_id
- 再做发布/草稿校验：
  - 发布 drafted=1：标题与内容必须有
  - 草稿 drafted=0：标题或内容至少一个存在
- 再过滤 article_image：
  - 仅允许相对路径（过滤 `blob:`、http、// 等）
- 最终落库：
  - `article_id == -1`：insert
  - `article_id > -1`：update

### 3.5 上传头图：upload_header_image
- 仍然先做归属校验
- DAO 更新 `article_image` 字段为相对路径
- 返回给前端的 url 用 `/images/<rel_path>`

## 4. CommentService（评论/回复业务）
文件：`backend/app/services/comment_service.py`

核心规则：
- 评论/回复内容长度：5 ~ 1000
- 入库交给 DAO：
  - 一级评论：`CommentDao.insert_comment`（负责 floor_number 递增）
  - 回复：`CommentDao.insert_reply`

返回风格：
- 成功返回 code=200
- 异常返回 code=500 + 错误信息

## 5. UserService（注册/登录/邮箱验证码/JWT）
文件：`backend/app/services/user_service.py`

### 5.1 邮箱验证码：send_email_code
- 校验邮箱格式
- 生成 code 并写入 Redis：key=`email:code:<email>`，过期 300s
- 当前实现“开发模式”：直接把 code 返回给前端（方便测试）
  - 生产环境可替换为调用 `send_email(email, code)`

### 5.2 注册：register
- 校验：邮箱格式、密码长度、两次密码一致
- 从 Redis 校验邮箱验证码
- 检查用户名是否已存在
- bcrypt hash 密码
- 生成默认昵称（邮箱 @ 前部分）
- 随机分配头像图片 `1~539.jpg`
- DAO 创建用户，返回用户信息

### 5.3 登录：login
- 查询用户
- bcrypt 校验密码
- 创建 JWT：payload `{"sub": "<user_id>"}`
- 返回 user 信息 + token（并移除 password 字段）

说明：
- JWT encode/decode 在 `backend/app/core/security.py`

## 6. FavoriteService（收藏/取消收藏）
文件：`backend/app/services/favorite_service.py`
- update_status：调用 DAO 更新 canceled
- canceled=0 返回“收藏成功”，canceled=1 返回“取消收藏成功”

## 7. PersonalService（个人中心）
文件：`backend/app/services/personal_service.py`

提供三类列表：
- 我的文章：`get_article_list(user_id, drafted)`
- 我的收藏：`get_favorite_list(user_id)`
- 我的评论：`get_comment_list(user_id)`

要点：
- 文章/收藏列表共用 `_enrich_articles`：把 ORM 转 dict，并把 article_image 归一为 `/images/...`
- 我的评论列表：
  - 先从 CommentDao 查用户评论
  - 再通过 ArticleDao 根据 article_id 查标题
  - 返回结构包含 article_title，便于前端展示

## 8. Service 层常见问题
- 为什么有的业务复用 ArticleService？
  - `index_api` 通过 `IndexArticleServiceDep` 注入的也是 `ArticleService`，用于首页列表。
- 为什么要做“图片路径归一化”？
  - 兼容旧数据（只存文件名）与新数据（存相对路径），并统一对外输出 `/images/...`。
- 为什么归属校验抛 PermissionError？
  - 这样 API 层可以统一捕获并返回 403。

下一篇文档会专门讲 DAO 层：每个 DAO 怎么查询、有哪些关键 SQL/过滤条件、以及与表结构的对应关系。
