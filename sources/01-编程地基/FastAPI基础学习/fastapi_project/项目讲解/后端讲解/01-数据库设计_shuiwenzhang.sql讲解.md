# 数据库设计（shuiwenzhang.sql）讲解

> SQL 文件：`fastapi_project/backend/shuiwenzhang.sql`

## 1. 数据库初始化方式
SQL 脚本开头会：
- 删除旧库：`DROP DATABASE IF EXISTS shuiwenzhang;`
- 创建新库并选择：`CREATE DATABASE ...; USE shuiwenzhang;`

字符集：`utf8mb4`，适合存储中文与 emoji，推荐配置。

## 2. 表清单与业务含义
本项目核心四表：
- `user`：用户
- `article`：文章（含草稿/已发布）
- `comment`：评论与回复（同表存储）
- `favorite`：收藏（软删除 canceled）

## 3. user 表（用户表）
表结构要点：
- 主键：`user_id` 自增
- `username`：邮箱格式用户名，唯一约束
- `password`：bcrypt 哈希后的密码
- `nickname/picture/job`：展示字段
- `create_time/update_time`：时间戳

与后端代码对应：
- ORM：`backend/app/models/user.py`
- DAO：`backend/app/dao/user_dao.py`
- Service：`backend/app/services/user_service.py`

常见业务：
- 注册：检查邮箱格式、密码长度、二次密码一致、邮箱验证码
- 登录：校验密码后签发 JWT（token 放在返回 data 中，并在 API 层写入 cookie）

## 4. article 表（文章主表）
表结构要点：
- 主键：`id` 自增
- `title/article_content`：标题与正文（HTML 富文本）
- `drafted`：0=草稿，1=已发布
- `label_name`：栏目 key（如 `python`/`auto_test`），用于首页筛选
- `article_tag`：标签（逗号分隔），展示时会替换成 ` · `
- `browse_num`：浏览量（详情接口会 +1）
- `article_image`：文章头图（本项目有兼容逻辑，既支持只存文件名，也支持存相对路径）

索引：
- `idx_user_id`：按作者查
- `idx_label_name`：按栏目筛选
- `idx_drafted`：按草稿/发布筛选

与后端代码对应：
- ORM：`backend/app/models/article.py`
- DAO：`backend/app/dao/article_dao.py`
- Service：`backend/app/services/article_service.py`

关键业务规则：
- 发布（drafted=1）必须有标题与内容
- 草稿（drafted=0）至少要有标题或内容
- `article_id > 0` 更新文章时要做“归属校验”（必须是本人文章）

## 5. comment 表（评论/回复表）
表结构要点：
- 主键：`id`
- `article_id`：被评论文章
- `user_id`：评论人
- `content`：评论内容（HTML）
- `ipaddr`：评论人 IP（由后端从 request.client.host 获取）
- `reply_id`：回复目标评论 id
  - 一级评论：`reply_id = 0`
- `base_reply_id`：所属一级评论 id
  - 一级评论：`base_reply_id = 0`
- `floor_number`：楼层号（按文章维度递增）
  - 只对一级评论有意义

评论/回复如何落库：
- 新增一级评论：
  - 先查询该文章已存在评论的 `max(floor_number)`
  - 新评论 floor_number = max + 1
  - 写入时：reply_id=0, base_reply_id=0
- 新增回复：
  - 直接插入，设置 reply_id 与 base_reply_id

与后端代码对应：
- ORM：`backend/app/models/comment.py`
- DAO：`backend/app/dao/comment_dao.py`
- Service：`backend/app/services/comment_service.py`

查询返回结构（用于文章详情页评论展示）：
- 一级评论列表 + 每条评论的 reply_list
- reply_list 的每条包含：from_user / to_user / content

## 6. favorite 表（收藏表）
表结构要点：
- 主键：`id`
- `user_id`：收藏者
- `article_id`：文章
- `canceled`：软删除标记
  - 0=收藏中
  - 1=已取消收藏

与后端代码对应：
- ORM：`backend/app/models/favorite.py`
- DAO：`backend/app/dao/favorite_dao.py`
- Service：`backend/app/services/favorite_service.py`

更新策略：
- 若记录不存在：insert 一条
- 若记录存在：更新 canceled

## 7. 表关系（逻辑关系）
> SQL 中未显式创建外键，但逻辑上存在关联。

- `article.user_id` -> `user.user_id`
- `comment.user_id` -> `user.user_id`
- `comment.article_id` -> `article.id`
- `favorite.user_id` -> `user.user_id`
- `favorite.article_id` -> `article.id`

建议理解为：
- 一个人可以写多篇文章
- 一篇文章有多条评论；评论又可以有多层回复（通过 base_reply_id 归属到一级评论）
- 一个人可以收藏多篇文章

## 8. 示例数据说明
SQL 文件中带了示例数据，方便本地跑起来就能看到：
- user 三条测试用户
- article 多篇文章，其中包含一条 `drafted=0` 的草稿
- comment 多条评论与回复（可用于验证楼层号、回复关系）
- favorite 多条收藏记录（包含 canceled=1 的取消收藏记录）

## 9. 与图片资源路径的约定
- SQL 示例中 `article.article_image` 多为 `article_001.jpg` 这种“纯文件名”
- 后端会兼容处理：如果发现数据库里不含 `/`，会自动补成 `article/header/<filename>`
- 最终对外访问 URL 统一为：`/images/article/header/<filename>`

对应逻辑：
- `backend/app/services/article_service.py` 的 `_normalize_article_image`
- 静态挂载：`backend/app/main.py` 挂载 `/images -> resource/images`
