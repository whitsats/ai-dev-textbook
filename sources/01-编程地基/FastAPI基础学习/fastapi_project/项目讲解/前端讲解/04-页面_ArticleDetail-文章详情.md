# 页面讲解：ArticleDetail 文章详情（收藏/评论/回复）

> 页面文件：`frontend/src/views/ArticleDetail.vue`

## 1. 页面职责
ArticleDetail 页面负责展示一篇文章的完整信息，并提供互动能力：
- 文章标题、作者、发布时间、浏览量、标签
- 文章正文（v-html 渲染 HTML 富文本）
- 收藏/取消收藏
- 评论列表（一级评论 + 回复列表）
- 发表评论、回复评论
- 若当前用户是作者：显示“编辑文章”入口

## 2. 路由入口与参数
路由：`/article/detail/:id`
- `id` 来自 `route.params.id`，代表文章 ID

当 id 变化时：
- watch 监听 `route.params.id`，自动重新拉取文章详情

## 3. 依赖与引用
- `getArticleDetail`：`@/api/article.js`
- `updateFavoriteStatus`：`@/api/favorite.js`
- `addComment/replyComment`：`@/api/comment.js`
- 登录态：`isLoggedIn/getUserInfo`：`@/utils/auth.js`
- 导航：`Header.vue`

## 4. 调用的后端接口
### 4.1 拉取文章详情
`getArticleDetail(articleId)` -> `GET /api/article/detail?article_id=<id>`

页面使用返回字段：
- `data.title/article_content/browse_num/create_time/...`
- `data.author`（作者信息）
- `data.comment_list`（一级评论列表，每条含 reply_list）
- `data.comment_count`
- `data.is_favorite`（收藏状态）
- `data.tag_list`

说明：
- 后端在 DAO 层会把 browse_num +1，因此每次拉取详情浏览量会递增

### 4.2 收藏/取消收藏
`updateFavoriteStatus({ article_id, canceled })` -> `POST /api/favorite/update_status`

约定：
- canceled=0：收藏
- canceled=1：取消收藏

页面状态：
- `isFavorite` 用 canceled 值来表示（0=已收藏，1=未收藏）

### 4.3 发表评论
`addComment({ article_id, content })` -> `POST /api/comment/add`

### 4.4 回复评论
`replyComment({ article_id, content, reply_id, base_reply_id })` -> `POST /api/comment/reply`

页面实现中：
- reply_id = 当前一级评论 id
- base_reply_id = 当前一级评论 id

## 5. 页面状态设计
核心状态：
- `article`：文章对象
- `author`：作者对象
- `commentList/commentCount`
- `isFavorite`：收藏状态
- `tagList`：标签数组
- `loading`

评论输入状态：
- `commentContent`：评论输入
- `replyingTo`：当前正在回复的一级评论 id
- `replyContent`：回复输入

登录相关：
- `isLogin = isLoggedIn()`
- `currentUser`：从 localStorage 的 user_info 读取

权限相关（作者判断）：
- `isOwner`：通常根据 currentUser.user_id 与 article.user_id 对比（页面里会计算/判断）

## 6. 核心交互流程

### 6.1 进入页面 / 切换文章
- watch(route.params.id) -> fetchDetail()
- fetchDetail：
  - loading=true
  - 调用 getArticleDetail
  - 填充 article/author/commentList/commentCount/isFavorite/tagList
  - loading=false

### 6.2 收藏/取消收藏
- 点击收藏按钮 -> toggleFavorite()
- 计算 newCanceled：
  - 当前 isFavorite=0（已收藏） -> newCanceled=1
  - 当前 isFavorite=1（未收藏） -> newCanceled=0
- 调用 updateFavoriteStatus 成功后更新 isFavorite
- 如果未登录：axios 拦截器会跳转登录；页面也会 alert 提示

### 6.3 发表评论
- 输入 commentContent（至少 5 个字）
- submitComment 调用 addComment
- 成功后清空输入并 fetchDetail() 刷新评论区

### 6.4 回复一级评论
- 点击“回复” -> showReplyForm(item) 设置 replyingTo
- 输入 replyContent（至少 5 个字）
- submitReply 调用 replyComment
- 成功后清空输入、关闭回复框并 fetchDetail() 刷新

## 7. UI 与渲染注意点
- `article.article_content` 使用 `v-html` 渲染富文本：
  - 依赖后端存储的 HTML 内容
  - 若未来要增强安全性，需要注意 XSS 过滤（当前文档仅说明，不改代码）

## 8. 常见问题
- 未登录时点击收藏/评论？
  - 请求会返回 401（业务 code 或 HTTP 401），axios 拦截器会清 token 并跳转登录。
- 为什么评论刷新会重新增加浏览量？
  - fetchDetail() 会再次调用文章详情接口，而后端详情接口会 browse_num +1。
  - 若希望“刷新评论不增浏览”，可拆分后端接口：文章详情与评论列表分开。
