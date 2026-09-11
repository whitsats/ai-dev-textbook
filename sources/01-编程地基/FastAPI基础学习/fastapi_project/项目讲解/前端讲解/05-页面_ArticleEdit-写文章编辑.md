# 页面讲解：ArticleEdit 写文章/编辑文章（草稿/发布/上传头图）

> 页面文件：`frontend/src/views/ArticleEdit.vue`

## 1. 页面职责
ArticleEdit 页面是“内容生产后台”，负责：
- 新建文章（默认草稿 drafted=0）
- 从草稿列表加载草稿继续编辑
- 编辑已发布文章（通过 query 参数 article_id 进入编辑模式）
- 上传文章头图（上传前必要时先创建草稿拿到 article_id）
- 保存草稿、发布文章
- 发布/保存后进行“落库校验”：再从后端读取一次文章详情并对比展示

## 2. 路由入口与参数
路由：`/article/edit`
- 该路由 `meta.requiresAuth: true`，必须登录才能访问

编辑模式参数：
- query：`article_id`
- 当存在且 >0 时，会拉取文章详情并回填表单

## 3. 依赖与引用
- API：
  - `getNewPageData`（新建页数据：栏目/类型/标签/草稿列表）
  - `saveArticle`（草稿/发布统一保存）
  - `uploadHeaderImage`（上传头图）
  - `getArticleDetail`（用于编辑回填、落库校验）
- 导航组件：`Header.vue`
- 路由：`useRoute/useRouter`

## 4. 调用的后端接口
### 4.1 新建页初始化数据
`getNewPageData()` -> `GET /api/article/new-page`

返回使用字段：
- `label_types`：栏目
- `article_types`：类型
- `article_tags`：标签列表
- `drafted_list`：草稿列表

### 4.2 保存草稿 / 发布文章（统一接口）
`saveArticle(data)` -> `POST /api/article/save`

关键字段：
- `article_id`：
  - -1 表示新建
  - >0 表示更新
- `drafted`：
  - 0 保存草稿
  - 1 发布
- 其它：title/content/label_name/article_tag/article_type/article_image

### 4.3 上传头图
`uploadHeaderImage(formData)` -> `POST /api/article/upload`

formData：
- `article_id`
- `file`

返回：
- payload.state === 'SUCCESS'
- payload.original/title 通常为相对路径 `article/header/<filename>.jpg`

### 4.4 编辑回填 / 落库校验
`getArticleDetail(articleId)` -> `GET /api/article/detail`
用途：
- 编辑模式加载文章详情
- 发布/保存后 verifyPersisted：再次拉取详情，并在页面下方展示“后端返回 vs 本地提交”

## 5. 页面状态设计
核心表单：
- `form`：
  - `article_id`（默认 -1）
  - `title/article_content`
  - `drafted`（默认 0）
  - `label_name/article_tag/article_type/article_image`

辅助状态：
- `labelTypes/articleTypes/articleTags`
- `draftList/selectedDraft`
- `selectedTags`：多选标签数组，保存时 join(',') 写入 form.article_tag
- `errors`：表单红字提示

校验面板：
- `verifyVisible/verifying/verifyError/lastSaved`

## 6. 关键流程（建议按下面顺序理解代码）

### 6.1 页面初始化
`onMounted`：
1. `fetchNewPage()` 拉取栏目/类型/标签/草稿列表
2. 读取 `route.query.article_id`：
   - 若存在且 >0：`loadArticleForEdit(articleId)` 进入编辑模式

### 6.2 草稿选择与加载
- UI 上方有草稿下拉框（来自 drafted_list）
- `loadDraft()`：
  - 根据 selectedDraft 找到草稿对象
  - 回填 title/content/article_image

### 6.3 图片路径处理（displayImage）
- 表单内 `form.article_image` 统一存“相对路径”如：`article/header/xxx.jpg`
- 展示时 `displayImage(relPath)` 统一拼成 `/images/<relPath>`
- 如果是 blob/http（例如预览临时 URL），直接返回原值

### 6.4 上传头图（handleUpload）
上传前的关键处理：
- 如果是新建文章（article_id == -1）：
  - 先调用 `saveArticle({...form, drafted:0, article_image:''})` 创建草稿
  - 成功后拿到后端返回的 `article_id`
- 再正式上传：
  - `FormData.append('article_id', form.article_id)`
  - `FormData.append('file', file)`
  - 调用 uploadHeaderImage
  - 成功后把相对路径写入 `form.article_image`

### 6.5 保存草稿（saveDraft）
- 保存前会判断“是否填写了任何内容”：
  - title/content/article_image/selectedTags 任何一个有值即可
- 若完全空：给 title/content 设置红字提示，不请求后端
- 调用 saveArticle(drafted=0)
- 成功后调用 `verifyPersisted(article_id)` 进行落库校验展示

### 6.6 发布文章（publish）
- 先 `validateForm()`：标题与内容必填
- `form.article_tag = selectedTags.join(',')`
- 调用 saveArticle(drafted=1)
- 成功：
  - verifyPersisted
  - 跳转到文章详情页 `/article/detail/<id>`
- 失败：
  - 把后端 msg 映射到 title/content 的红字提示

## 7. 常见问题
- 为什么上传头图前要先保存草稿？
  - 后端上传接口需要 article_id，用于做归属校验并把图片路径写回 article 表。
- 为什么保存/发布后还要“落库校验”？
  - 用于开发调试：直观看到“后端最终存储内容”和“本地提交内容”的差异。
