# 页面讲解：Home 首页（文章列表/搜索/栏目/分页）

> 页面文件：`frontend/src/views/Home.vue`

## 1. 页面职责
Home 是站点的入口页，负责：
- 拉取文章列表并展示卡片列表
- 展示“栏目分类”（由后端返回 label_types）并支持切换筛选
- 支持关键字搜索
- 支持分页（上一页/下一页）
- 作为全站布局容器之一，顶部使用 `Header` 导航

## 2. 路由入口
路由配置：`frontend/src/router/index.js`
- `path: '/'`
- `name: 'Home'`
- `component: Home.vue`

## 3. 依赖与引用
页面脚本中主要引用：
- `getArticleList`：`@/api/article.js`
- `Header`：`@/components/Header.vue`
- `isLoggedIn/removeToken`：`@/utils/auth.js`
- `logout`：`@/api/user.js`（页面内也有退出逻辑；Header 里也有退出按钮）

## 4. 调用的后端接口
`getArticleList(params)` -> `GET /api/`（因为 axios baseURL 是 `/api`）

请求参数：
- `page`：当前页（从 1 开始）
- `article_type`：栏目 key（默认 recommend 表示全部）
- `keyword`：可选，搜索关键字

返回使用字段：
- `data.list`：文章列表
- `data.label_types`：栏目字典（key -> {name, selected}）
- `data.total_page`：总页数（如果后端未返回则前端默认 1）

## 5. 页面状态设计
核心响应式状态：
- `articles`: 文章列表
- `labelTypes`: 栏目类型
- `loading`: 列表加载态
- `page/totalPages`: 分页
- `currentType`: 当前栏目
- `keyword`: 搜索关键字

派生状态：
- `isLogin`: 是否登录（用于 Header/按钮显示）

## 6. 核心交互流程

### 6.1 首次进入页面
- `onMounted` 触发 `fetchArticles()`
- 进入 loading
- 请求 `/api/`
- 成功后赋值 articles/labelTypes/totalPages

### 6.2 切换栏目
- 点击左侧栏目，调用 `switchType(key)`：
  - currentType = key
  - page 重置为 1
  - keyword 清空
  - 再次 fetchArticles

### 6.3 搜索
- 输入框回车或点击“搜索”：
  - page 重置为 1
  - fetchArticles（带 keyword）

### 6.4 分页
- 上一页：page-- 后 fetchArticles
- 下一页：page++ 后 fetchArticles

### 6.5 进入文章详情
- 点击文章卡片：`router.push('/article/detail/<id>')`

## 7. UI 约定与图片展示
文章列表卡片使用：
- `item.article_image` 作为头图
- 若为空则兜底：`/images/article/header/article_001.jpg`

说明：
- `/images` 指向后端静态挂载目录（后端会把 `resource/images` 映射到 `/images`）

## 8. 常见问题
- 为什么 `totalPages` 可能始终是 1？
  - Home.vue 依赖 `res.data.total_page` 字段，如果后端未返回该字段，会保持默认值。
- 退出逻辑在哪里？
  - Header 组件中有退出按钮与流程；Home 页面内部也实现了 `handleLogout`（主要用于兼容不同入口）。
