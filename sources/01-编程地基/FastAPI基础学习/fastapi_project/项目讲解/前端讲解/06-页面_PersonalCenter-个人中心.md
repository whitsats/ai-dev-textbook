# 页面讲解：PersonalCenter 个人中心（我的文章/收藏/评论）

> 页面文件：`frontend/src/views/PersonalCenter.vue`

## 1. 页面职责
PersonalCenter 是登录用户的个人中心页面，提供三类数据视图：
- 我的文章（可切换：已发布 / 草稿）
- 我的收藏
- 我的评论

页面结构：
- 左侧：用户信息卡片 + Tab 导航
- 右侧：内容列表（文章列表或评论列表）

## 2. 路由入口
路由：`/personal` -> `PersonalCenter.vue`
- 该路由 `meta.requiresAuth: true`，必须登录

## 3. 依赖与引用
- `getMe`：`@/api/user.js`（拉取当前用户信息）
- `getPersonalCenter`：`@/api/personal.js`（拉取列表数据）
- 导航组件：`Header.vue`
- 路由：`useRouter`

## 4. 调用的后端接口
### 4.1 获取当前用户信息
`getMe()` -> `GET /api/user/me`
- 返回 user_id/username/nickname/picture/job

### 4.2 获取个人中心列表
`getPersonalCenter(typeName, drafted)` -> `GET /api/personal/`

请求参数：
- `type_name`：`article` / `favorite` / `comment`
- `drafted`：仅当 type_name=article 时有效
  - 1：已发布
  - 0：草稿

返回数据形态：
- type_name=comment：返回评论数组（包含 article_title、floor_number 等）
- type_name=article/favorite：返回文章数组

## 5. 页面状态设计
核心状态：
- `activeTab`：当前 tab（article/favorite/comment）
- `articleStatus`：文章子 tab（1=已发布，0=草稿）
- `loading`
- `articles`：文章列表（用于 article/favorite）
- `comments`：评论列表（用于 comment）
- `user`：用户信息

## 6. 核心交互流程

### 6.1 初始化
`onMounted()` 调用 `fetchData()`：
1. 拉取 getMe 填充 user 卡片
2. 拉取 getPersonalCenter 填充列表

### 6.2 切换 tab（我的文章/收藏/评论）
点击左侧 tab：`switchTab(key)`
- activeTab = key
- 如果切到非 article：articleStatus 重置为 1
- 调用 fetchData 重新拉取对应列表

### 6.3 切换文章状态（已发布/草稿）
仅当 activeTab=article 显示子 tab：
- `setArticleStatus(v)` 更新 articleStatus 并 fetchData

### 6.4 跳转文章详情
- 在文章列表或评论列表点击条目：
  - `router.push('/article/detail/<id>')`

## 7. UI 展示规则
- 左侧用户头像：`/images/headers/<picture>`
- 右侧列表：
  - article/favorite：显示头图、标题、浏览量、创建时间等
  - comment：显示文章标题、楼层号、评论内容、时间

## 8. 常见问题
- 为什么个人中心每次切换 tab 都会重新请求 getMe？
  - fetchData 同时拉取用户信息与列表，简单直观。若要优化可把 user 信息缓存起来。
- 个人中心的数据从哪里来？
  - 后端在 `/api/personal/` 按 type_name 路由到不同 service，并通过 DAO 组装数据。
