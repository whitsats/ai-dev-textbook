# DAO 层讲解（数据访问与查询逻辑）

> 目录：`fastapi_project/backend/app/dao/`

## 1. DAO 层的职责
DAO（Data Access Object）层只做“数据读写”，特点：
- 输入是业务所需的最小参数（如 user_id/article_id/page 等）
- 输出是 ORM 实体或简单的 dict/list
- 不处理 HTTP、不处理权限（权限在 Service 做）

本项目 DAO 基于 SQLAlchemy ORM 查询。

## 2. 统一的 model_to_dict
多个 DAO 都有类似 `model_to_dict`：
- 遍历 ORM 对象的 `__dict__`
- 过滤私有字段 `_sa_instance_state`
- datetime 格式化为字符串

优点：快速把 ORM 转成前端可用的数据结构。
注意：这种方式会把所有字段都带出来，若包含敏感字段（如 user.password），需要再做过滤（项目里 CommentDao 做了 sanitize）。

## 3. ArticleDao（文章相关查询）
文件：`backend/app/dao/article_dao.py`

### 3.1 首页/列表：find_article
- join `User` 拿作者昵称
- 仅查已发布：`Article.drafted == 1`
- 支持栏目筛选：`label_name`
- 排序：`browse_num desc`
- limit：`page * 10`

### 3.2 搜索：search_article
- 条件：title like 或 content like
- 同样只查已发布 drafted=1
- 排序 browse_num desc，limit `page * 10`

### 3.3 详情：get_article_detail
- 按 id 查文章
- 若存在：
  - `browse_num += 1`
  - `commit + refresh`

说明：浏览量自增放在 DAO 里实现，Service 调用时即产生副作用。

### 3.4 草稿相关
- `get_all_article_drafted(user_id)`：查 drafted=0
- `get_one_article_drafted(article_id)`：查某篇草稿

### 3.5 个人中心相关
- `get_article_by_userid(user_id, drafted)`：查我的文章（草稿/发布）
- `get_favorite_article_by_userid(user_id)`：join favorite 表按收藏时间倒序
- `get_comment_article_by_userid(user_id)`：
  - 先 distinct 出评论过的 article_id
  - 再用 in_ 查询 article 列表

### 3.6 写入/更新
- `insert_article(...)`：insert 后 commit + refresh
- `update_article(...)`：按 id 查 row，更新字段后 commit
- `update_article_header_image(...)`：仅更新 article_image

归属校验并不在 DAO 做：Service 会通过 `get_article_owner_id` 查询 owner_id 再判断。

## 4. CommentDao（评论/回复）
文件：`backend/app/dao/comment_dao.py`

### 4.1 评论树组装：get_comment_user_list(article_id)
返回的数据结构用于文章详情页：
- 先查一级评论：
  - 条件：reply_id=0 且 base_reply_id=0
  - 按 id desc
- 对每条一级评论：
  - 查评论用户（User）
  - 查所有回复：`base_reply_id = 一级评论.id`
  - 对每条回复：
    - from_user：回复用户
    - to_user：通过 reply_id 找到“被回复的评论”，再找到对应用户
    - content：回复内容（comment 表的一条记录）
- 对 user dict 做脱敏：去掉 password

### 4.2 楼层号：insert_comment
- 先查该文章下评论的 max(floor_number)
- next_floor = max + 1
- 插入 comment：reply_id=0, base_reply_id=0

### 4.3 回复：insert_reply
- 直接插入一条 comment 记录：
  - reply_id：回复目标评论 id
  - base_reply_id：所属一级评论 id

### 4.4 统计：get_article_comment_count
- 只统计一级评论数量（reply_id=0 & base_reply_id=0）

## 5. FavoriteDao（收藏）
文件：`backend/app/dao/favorite_dao.py`

实现特点：
- `update_status(article_id, user_id, canceled)`：
  - 若不存在记录则 insert
  - 若存在则更新 canceled
  - commit
- `user_if_favorite(user_id, article_id)`：
  - 查询 canceled 字段
  - 若无记录返回 1（表示“未收藏/默认状态”）

说明：这里用 canceled 作为软删除标记，避免频繁 delete。

## 6. UserDao（用户）
文件：`backend/app/dao/user_dao.py`
- `find_by_username`：按 username 查（返回列表）
- `find_by_userid`：按 user_id 查
- `create_user`：插入用户
- `model_to_dict`：ORM 转 dict

注意：UserDao 不负责密码 hash/校验，相关逻辑在 `UserService` + `core/security.py`。

## 7. DAO 层与表结构的对应关系
- `models/user.py` <-> `user` 表
- `models/article.py` <-> `article` 表
- `models/comment.py` <-> `comment` 表
- `models/favorite.py` <-> `favorite` 表

SQL 设计与示例数据详见上一份文档：`01-数据库设计_shuiwenzhang.sql讲解.md`。

## 8. 常见扩展建议
- 如果未来要做分页，建议 DAO 返回 limit/offset，避免 `page * 10` 的“伪分页”。
- 如果要保证数据一致性，建议补上外键与级联策略，或在 DAO 层加存在性校验。
- 评论树查询目前是 N+1 查询（每条评论/回复都单独查 user），数据量大时可考虑 join 一次查全。
