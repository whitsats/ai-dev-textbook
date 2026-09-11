<template>
  <div class="page">
    <Header />

    <div class="edit-wrap">
      <div class="edit-card">
        <div class="card-header">
          <h2 class="page-title">{{ isEdit ? '编辑文章' : '写文章' }}</h2>
          <div class="draft-select" v-if="draftList.length">
            <span class="draft-label">草稿</span>
            <select v-model="selectedDraft" @change="loadDraft">
              <option value="">请选择草稿</option>
              <option v-for="d in draftList" :key="d.id" :value="d.id">{{ d.title || '无标题草稿' }}</option>
            </select>
          </div>
        </div>

        <div class="form">
          <div class="title-area">
            <input
              v-model="form.title"
              class="title-input"
              :class="{ invalid: errors.title }"
              placeholder="输入文章标题..."
              @blur="validateField('title')"
              @input="clearError('title')"
            />
            <div v-if="errors.title" class="field-error">{{ errors.title }}</div>
          </div>

          <div class="form-row">
            <div class="field">
              <label>栏目</label>
              <select v-model="form.label_name">
                <option
                  v-for="(item, key) in labelTypes"
                  v-show="key !== 'recommend'"
                  :key="key"
                  :value="key"
                >
                  {{ item.name }}
                </option>
              </select>
            </div>
            <div class="field">
              <label>类型</label>
              <select v-model="form.article_type">
                <option
                  v-for="(item, key) in articleTypes"
                  v-show="key !== 'recommend'"
                  :key="key"
                  :value="key"
                >
                  {{ item.name }}
                </option>
              </select>
            </div>
          </div>

          <div class="form-row tags-row">
            <label class="field-label">标签</label>
            <div class="tag-list">
              <label v-for="tag in articleTags" :key="tag" class="tag-chip" :class="{ selected: selectedTags.includes(tag) }">
                <input type="checkbox" :value="tag" v-model="selectedTags" />
                {{ tag }}
              </label>
            </div>
          </div>

          <div class="image-area">
            <button type="button" class="btn-upload" @click="triggerUpload">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="3"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>
              上传头图
            </button>
            <input type="file" ref="fileInput" @change="handleUpload" style="display:none" accept="image/*" />

            <img
              v-if="form.article_image"
              class="image-preview"
              :src="displayImage(form.article_image)"
              alt="头图预览"
            />
          </div>

          <div class="content-area">
            <textarea
              v-model="form.article_content"
              class="content-input"
              :class="{ invalid: errors.article_content }"
              placeholder="在此输入文章内容..."
              @blur="validateField('article_content')"
              @input="clearError('article_content')"
            ></textarea>
            <div v-if="errors.article_content" class="field-error">{{ errors.article_content }}</div>
          </div>

          <div class="action-bar">
            <button v-if="form.drafted === 0" class="btn-draft" @click="saveDraft">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg>
              保存草稿
            </button>
            <button class="btn-publish" @click="publish">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
              {{ isEdit && form.drafted === 1 ? '重新发布' : '发布文章' }}
            </button>
          </div>

          <div v-if="verifyVisible" class="verify-panel">
            <div class="verify-title">落库校验（保存后从后端再读一次）</div>
            <div v-if="verifying" class="verify-loading">校验中...</div>
            <div v-else-if="verifyError" class="verify-error">{{ verifyError }}</div>
            <div v-else-if="lastSaved" class="verify-body">
              <div class="verify-row">
                <div class="verify-label">后端返回：</div>
                <pre class="verify-pre">{{ JSON.stringify(lastSaved.article, null, 2) }}</pre>
              </div>
              <div class="verify-row">
                <div class="verify-label">本地提交：</div>
                <pre class="verify-pre">{{ JSON.stringify(lastSaved.local, null, 2) }}</pre>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  getNewPageData,
  saveArticle,
  uploadHeaderImage,
  getArticleDetail,
} from '@/api/article.js'
import Header from '@/components/Header.vue'

const route = useRoute()
const router = useRouter()
const labelTypes = ref({})
const articleTypes = ref({})
const articleTags = ref([])
const draftList = ref([])
const selectedDraft = ref('')
const fileInput = ref(null)

const form = ref({
  article_id: -1,
  title: '',
  article_content: '',
  drafted: 0,
  label_name: '',
  article_tag: '',
  article_type: '',
  article_image: '',
})

const selectedTags = ref([])
const isEdit = ref(false)

const lastSaved = ref(null)
const verifyVisible = ref(false)
const verifying = ref(false)
const verifyError = ref('')

const errors = ref({
  title: '',
  article_content: '',
})

// form.article_image 存相对路径（article/header/xxx.jpg）
// displayImage 展示时拼完整 URL
function displayImage(relPath) {
  if (!relPath) return ''
  if (relPath.startsWith('blob:') || relPath.startsWith('http')) return relPath
  return `/images/${relPath}`
}

function clearError(field) {
  if (errors.value[field]) errors.value[field] = ''
}

function validateField(field) {
  if (field === 'title') {
    const ok = !!form.value.title?.trim()
    errors.value.title = ok ? '' : '标题为必填项'
    return ok
  }
  if (field === 'article_content') {
    const ok = !!form.value.article_content?.trim()
    errors.value.article_content = ok ? '' : '内容为必填项'
    return ok
  }
  return true
}

function validateForm() {
  const okTitle = validateField('title')
  const okContent = validateField('article_content')
  return okTitle && okContent
}

function pick(obj, keys) {
  const out = {}
  keys.forEach((k) => {
    out[k] = obj?.[k]
  })
  return out
}

async function verifyPersisted(articleId) {
  verifyVisible.value = true
  verifying.value = true
  verifyError.value = ''
  try {
    const res = await getArticleDetail(articleId)
    if (res.code !== 200) {
      verifyError.value = res.msg || '拉取文章详情失败'
      lastSaved.value = null
      return
    }
    const d = res.data || {}
    const article = {
      id: d.id,
      title: d.title,
      article_content: d.article_content,
      browse_num: d.browse_num,
      tag_list: d.tag_list,
    }
    lastSaved.value = {
      article,
      local: pick(form.value, [
        'article_id',
        'title',
        'article_content',
        'drafted',
        'label_name',
        'article_tag',
        'article_type',
        'article_image',
      ]),
    }
  } catch (e) {
    verifyError.value = e?.message || '拉取文章详情异常'
    lastSaved.value = null
  } finally {
    verifying.value = false
  }
}

async function fetchNewPage() {
  const res = await getNewPageData()
  if (res.code === 200) {
    labelTypes.value = res.data.label_types || {}
    articleTypes.value = res.data.article_types || {}
    articleTags.value = res.data.article_tags || []
    draftList.value = res.data.drafted_list || []

    // 默认选中第一个栏目（跳过 recommend 占位项）
    if (!form.value.label_name) {
      const firstLabelKey = Object.keys(labelTypes.value || {}).find((k) => k !== 'recommend')
      if (firstLabelKey) form.value.label_name = firstLabelKey
    }

    // 默认选中第一个类型（跳过 recommend 占位项）
    if (!form.value.article_type) {
      const firstTypeKey = Object.keys(articleTypes.value || {}).find((k) => k !== 'recommend')
      if (firstTypeKey) form.value.article_type = firstTypeKey
    }
  }
}

async function loadArticleForEdit(articleId) {
  const res = await getArticleDetail(articleId)
  if (res.code !== 200) {
    errors.value.title = res.msg || '拉取文章详情失败'
    return
  }
  const d = res.data || {}

  form.value.article_id = d.id
  form.value.title = d.title || ''
  form.value.article_content = d.article_content || ''
  form.value.drafted = typeof d.drafted === 'number' ? d.drafted : form.value.drafted
  form.value.label_name = d.label_name || form.value.label_name
  form.value.article_type = d.article_type || form.value.article_type

  // 后端 detail 已经返回完整 URL（/images/...），展示时由 displayImage 处理
  // form.article_image 统一存相对路径，方便 save 时直接使用
  const rawImg = d.article_image || ''
  form.value.article_image = rawImg.startsWith('/images/')
    ? rawImg.replace('/images/', '')
    : rawImg

  if (Array.isArray(d.tag_list)) {
    selectedTags.value = d.tag_list.filter(Boolean)
  } else if (typeof d.article_tag === 'string' && d.article_tag) {
    selectedTags.value = d.article_tag.split(',').map(s => s.trim()).filter(Boolean)
  } else {
    selectedTags.value = []
  }

  isEdit.value = true
  selectedDraft.value = ''
}

function loadDraft() {
  if (!selectedDraft.value) return
  const draft = draftList.value.find(d => d.id == selectedDraft.value)
  if (draft) {
    form.value.article_id = draft.id
    form.value.title = draft.title || ''
    form.value.article_content = draft.article_content || ''
    // 同理：统一存相对路径
    const rawImg = draft.article_image || ''
    form.value.article_image = rawImg.startsWith('/images/')
      ? rawImg.replace('/images/', '')
      : rawImg
  }
}

function triggerUpload() {
  fileInput.value.click()
}

async function handleUpload(e) {
  const file = e.target.files[0]
  if (!file) return
  e.target.value = ''

  try {
    // 新建文章：先保存草稿拿到 article_id（此时无图片）
    if (form.value.article_id === -1) {
      form.value.article_tag = selectedTags.value.join(',')
      const res = await saveArticle({ ...form.value, drafted: 0, article_image: '' })
      if (res.code === 200) {
        form.value.article_id = res.data.article_id
      } else {
        errors.value.title = res.msg || '请先保存草稿后再上传头图'
        return
      }
    }

    // 上传图片到后端
    const fd = new FormData()
    fd.append('article_id', form.value.article_id)
    fd.append('file', file)

    const res = await uploadHeaderImage(fd)
    const payload = res?.data || res
    if (payload?.state === 'SUCCESS') {
      // relPath 是 article/header/xxx.jpg，直接用来展示
      const relPath = payload.original || payload.title || ''
      form.value.article_image = relPath
    }
  } catch (err) {
    console.error(err)
  }
}

async function saveDraft() {
  form.value.article_tag = selectedTags.value.join(',')

  const hasAnyContent =
    !!form.value.title?.trim() ||
    !!form.value.article_content?.trim() ||
    !!form.value.article_image ||
    (selectedTags.value && selectedTags.value.length > 0)

  // 什么都没填：不请求后端，直接红色提示
  if (!hasAnyContent) {
    errors.value.title = '请至少填写标题或内容后再保存草稿'
    errors.value.article_content = '请至少填写标题或内容后再保存草稿'
    return
  }

  const res = await saveArticle({ ...form.value, drafted: 0 })
  if (res.code === 200) {
    form.value.article_id = res.data.article_id
    // 草稿保存不弹窗
    await verifyPersisted(res.data.article_id)
  } else {
    // 草稿保存失败也不弹窗，走红字提示
    const msg = res.msg || '草稿保存失败'
    errors.value.title = msg
  }
}

async function publish() {
  if (!validateForm()) {
    return
  }
  form.value.article_tag = selectedTags.value.join(',')

  const res = await saveArticle({ ...form.value, drafted: 1 })
  if (res.code === 200) {
    await verifyPersisted(res.data.article_id)
    router.push(`/article/detail/${res.data.article_id}`)
  } else {
    // 不弹窗：把后端错误映射到表单红字提示
    const msg = res.msg || '发布失败'
    if (msg.includes('标题')) {
      errors.value.title = msg
    } else if (msg.includes('内容')) {
      errors.value.article_content = msg
    }
  }
}

onMounted(async () => {
  await fetchNewPage()

  const qid = route.query.article_id
  const articleId = qid ? Number(qid) : NaN
  if (!Number.isNaN(articleId) && articleId > 0) {
    await loadArticleForEdit(articleId)
  }
})
</script>

<style scoped>
.page {
  min-height: 100vh;
  background: var(--color-bg);
}

.edit-wrap {
  max-width: 860px;
  margin: 0 auto;
  padding: 28px 24px;
}

.edit-card {
  background: var(--color-surface);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
  overflow: hidden;
}

.card-header {
  padding: 20px 28px;
  border-bottom: 1px solid var(--color-border);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.page-title {
  font-size: 18px;
  font-weight: 700;
  color: var(--color-text-primary);
}

.draft-select {
  display: flex;
  align-items: center;
  gap: 8px;
}

.draft-label {
  font-size: 13px;
  color: var(--color-text-secondary);
}

.draft-select select {
  padding: 6px 10px;
  border: 1.5px solid var(--color-border);
  border-radius: var(--radius-sm);
  font-size: 13px;
  background: var(--color-bg);
  color: var(--color-text-primary);
  cursor: pointer;
  transition: var(--transition);
}

.draft-select select:focus {
  border-color: var(--color-primary);
  outline: none;
}

.form {
  padding: 24px 28px 28px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.title-area {
  border-bottom: 2px solid var(--color-border);
  padding-bottom: 16px;
}

.title-input {
  width: 100%;
  border: none;
  font-size: 22px;
  font-weight: 700;
  color: var(--color-text-primary);
  background: transparent;
  outline: none;
}

.title-input.invalid {
  border-radius: var(--radius-sm);
  outline: 2px solid rgba(239, 68, 68, 0.45);
  outline-offset: 6px;
}

.field-error {
  margin-top: 10px;
  font-size: 12px;
  line-height: 1.2;
  color: #ef4444;
}

.title-input::placeholder {
  color: var(--color-text-muted);
  font-weight: 400;
}

.form-row {
  display: flex;
  gap: 16px;
  align-items: flex-start;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex: 1;
}

.field label, .field-label {
  font-size: 13px;
  font-weight: 500;
  color: var(--color-text-secondary);
}

.field select {
  padding: 9px 12px;
  border: 1.5px solid var(--color-border);
  border-radius: var(--radius-sm);
  font-size: 14px;
  background: var(--color-bg);
  color: var(--color-text-primary);
  cursor: pointer;
  transition: var(--transition);
}

.field select:focus {
  border-color: var(--color-primary);
  background: #fff;
  outline: none;
}

.tags-row {
  align-items: flex-start;
}

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  flex: 1;
}

.tag-chip {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 12px;
  background: var(--color-bg);
  border: 1.5px solid var(--color-border);
  border-radius: 20px;
  font-size: 13px;
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: var(--transition);
}

.tag-chip input {
  display: none;
}

.tag-chip:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.tag-chip.selected {
  background: rgba(79, 70, 229, 0.08);
  border-color: var(--color-primary);
  color: var(--color-primary);
  font-weight: 500;
}

.image-area {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.btn-upload {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: var(--color-bg);
  border: 1.5px solid var(--color-border);
  border-radius: var(--radius-sm);
  font-size: 13px;
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: var(--transition);
}

.btn-upload:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
  background: rgba(79, 70, 229, 0.04);
}

.image-name {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  color: #16A34A;
  background: #F0FDF4;
  padding: 4px 10px;
  border-radius: 20px;
}

.image-preview {
  width: 92px;
  height: 52px;
  object-fit: cover;
  border-radius: 10px;
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-xs);
}

.content-area {
  border: 1.5px solid var(--color-border);
  border-radius: var(--radius-sm);
  overflow: hidden;
  transition: var(--transition);
}

.content-area:has(.content-input.invalid) {
  border-color: rgba(239, 68, 68, 0.55);
}

.content-area:focus-within {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.08);
}

.content-area:has(.content-input.invalid):focus-within {
  border-color: rgba(239, 68, 68, 0.65);
  box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.12);
}

.content-input {
  width: 100%;
  padding: 14px 16px;
  border: none;
  font-size: 15px;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  line-height: 1.8;
  color: var(--color-text-primary);
  resize: vertical;
  background: var(--color-bg);
  outline: none;
  min-height: 300px;
}

.content-input.invalid {
  outline: 2px solid rgba(239, 68, 68, 0.45);
  outline-offset: -2px;
}

.content-input::placeholder {
  color: var(--color-text-muted);
}

.action-bar {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding-top: 8px;
  border-top: 1px solid var(--color-border);
}

.btn-draft, .btn-publish {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 22px;
  border: none;
  border-radius: 20px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: var(--transition);
}

.btn-draft {
  background: var(--color-bg);
  color: var(--color-text-secondary);
  border: 1.5px solid var(--color-border);
}

.btn-draft:hover {
  border-color: var(--color-text-secondary);
  color: var(--color-text-primary);
}

.btn-publish {
  background: var(--color-primary);
  color: #fff;
}

.btn-publish:hover {
  background: var(--color-primary-dark);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(79, 70, 229, 0.3);
}

.verify-panel {
  margin-top: 16px;
  padding: 14px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg);
}

.verify-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin-bottom: 10px;
}

.verify-loading {
  font-size: 13px;
  color: var(--color-text-secondary);
}

.verify-error {
  font-size: 13px;
  color: #DC2626;
}

.verify-row {
  display: grid;
  grid-template-columns: 80px 1fr;
  gap: 10px;
  align-items: start;
  margin-top: 10px;
}

.verify-label {
  font-size: 12px;
  color: var(--color-text-secondary);
  padding-top: 6px;
}

.verify-pre {
  margin: 0;
  padding: 10px;
  background: #0b1020;
  color: #E5E7EB;
  border-radius: 10px;
  font-size: 12px;
  line-height: 1.4;
  overflow: auto;
  max-height: 220px;
}

</style>
