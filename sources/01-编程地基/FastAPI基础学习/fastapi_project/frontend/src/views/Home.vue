<template>
  <div class="page">
    <Header />

    <div class="home-wrap">
      <div class="home-layout">
        <aside class="sidebar">
          <div class="search-card">
            <div class="search-input-wrap">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
              <input v-model="keyword" @keyup.enter="handleSearch" placeholder="搜索文章..." />
            </div>
            <button class="btn-search" @click="handleSearch">搜索</button>
          </div>

          <div class="category-card">
            <h3 class="section-title">栏目分类</h3>
            <div class="category-list">
              <div
                v-for="(item, key) in labelTypes"
                :key="key"
                class="category-item"
                :class="{ active: currentType === key }"
                @click="switchType(key)"
              >
                <span class="cat-dot"></span>
                {{ item.name }}
              </div>
            </div>
          </div>
        </aside>

        <main class="main">
          <div class="articles-card">
            <div v-if="loading" class="loading-state">
              <div class="skeleton-list">
                <div class="skeleton-item" v-for="n in 4" :key="n">
                  <div class="skeleton-thumb"></div>
                  <div class="skeleton-info">
                    <div class="skeleton-line skeleton-title"></div>
                    <div class="skeleton-line skeleton-meta"></div>
                  </div>
                </div>
              </div>
            </div>
            <div v-else-if="articles.length === 0" class="empty-state">
              <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M9 12h6M9 16h6M7 4H4a1 1 0 0 0-1 1v14a1 1 0 0 0 1 1h16a1 1 0 0 0 1-1V9l-5-5z"/><path d="M14 4v5h5"/></svg>
              <p>暂无文章</p>
            </div>
            <div v-else class="article-items">
              <div
                v-for="item in articles"
                :key="item.id"
                class="article-card"
                @click="goDetail(item.id)"
              >
                <img
                  :src="item.article_image || '/images/article/header/article_001.jpg'"
                  class="article-thumb"
                />
                <div class="article-body">
                  <h3 class="article-title">{{ item.title }}</h3>
                  <div class="article-tags">
                    <span v-if="item.article_tag" class="tag" v-for="tag in item.article_tag.split(',')" :key="tag">{{ tag }}</span>
                  </div>
                  <div class="article-meta">
                    <div class="meta-left">
                      <span class="author">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="8" r="4"/><path d="M4 20c0-4 3.6-7 8-7s8 3 8 7"/></svg>
                        {{ item.nickname }}
                      </span>
                      <span class="views">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                        {{ item.browse_num }}
                      </span>
                    </div>
                    <span class="read-more">阅读全文 →</span>
                  </div>
                </div>
              </div>
            </div>

            <div class="pagination" v-if="articles.length > 0">
              <button @click="prevPage" :disabled="page <= 1" class="page-btn">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M15 18l-6-6 6-6"/></svg>
                上一页
              </button>
              <div class="page-info">
                <span class="current">{{ page }}</span>
                <span class="sep">/</span>
                <span class="total">{{ totalPages || 1 }}</span>
              </div>
              <button @click="nextPage" :disabled="page >= totalPages" class="page-btn">
                下一页
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 18l6-6-6-6"/></svg>
              </button>
            </div>
          </div>
        </main>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { getArticleList } from '@/api/article.js'
import { logout } from '@/api/user.js'
import { isLoggedIn, removeToken } from '@/utils/auth.js'
import Header from '@/components/Header.vue'

const router = useRouter()
const articles = ref([])
const labelTypes = ref({})
const loading = ref(false)
const page = ref(1)
const totalPages = ref(1)
const currentType = ref('recommend')
const keyword = ref('')

const isLogin = computed(() => isLoggedIn())

async function fetchArticles() {
  loading.value = true
  try {
    const params = { page: page.value, article_type: currentType.value }
    if (keyword.value) params.keyword = keyword.value
    const res = await getArticleList(params)
    if (res.code === 200) {
      articles.value = res.data?.list || []
      labelTypes.value = res.data?.label_types || {}
      totalPages.value = res.data?.total_page || 1
    }
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

function switchType(type) {
  currentType.value = type
  page.value = 1
  keyword.value = ''
  fetchArticles()
}

function handleSearch() {
  page.value = 1
  fetchArticles()
}

function prevPage() {
  if (page.value > 1) {
    page.value--
    fetchArticles()
  }
}

function nextPage() {
  if (page.value < totalPages.value) {
    page.value++
    fetchArticles()
  }
}

function goDetail(id) {
  router.push(`/article/detail/${id}`)
}

async function handleLogout() {
  try { await logout() } catch (e) {}
  removeToken()
  router.push('/')
  location.reload()
}

onMounted(() => {
  fetchArticles()
})
</script>

<style scoped>
.page {
  min-height: 100vh;
  background: var(--color-bg);
}

.home-wrap {
  max-width: 1200px;
  margin: 0 auto;
  padding: 28px 24px;
}

.home-layout {
  display: flex;
  gap: 24px;
  align-items: flex-start;
}

.sidebar {
  width: 240px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
  position: sticky;
  top: 84px;
}

.search-card {
  background: var(--color-surface);
  border-radius: var(--radius-md);
  padding: 16px;
  box-shadow: var(--shadow-sm);
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.search-input-wrap {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 12px;
  background: var(--color-bg);
  border: 1.5px solid var(--color-border);
  border-radius: var(--radius-sm);
  transition: var(--transition);
}

.search-input-wrap:focus-within {
  border-color: var(--color-primary);
  background: #fff;
}

.search-input-wrap svg {
  color: var(--color-text-muted);
  flex-shrink: 0;
}

.search-input-wrap input {
  flex: 1;
  border: none;
  background: transparent;
  font-size: 14px;
  color: var(--color-text-primary);
}

.search-input-wrap input::placeholder {
  color: var(--color-text-muted);
}

.btn-search {
  width: 100%;
  padding: 9px;
  background: var(--color-primary);
  color: #fff;
  border: none;
  border-radius: var(--radius-sm);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: var(--transition);
}

.btn-search:hover {
  background: var(--color-primary-dark);
}

.category-card {
  background: var(--color-surface);
  border-radius: var(--radius-md);
  padding: 16px 20px;
  box-shadow: var(--shadow-sm);
}

.section-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 12px;
}

.category-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.category-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 12px;
  border-radius: var(--radius-sm);
  font-size: 14px;
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: var(--transition);
}

.cat-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--color-border);
  transition: var(--transition);
}

.category-item:hover {
  background: rgba(79, 70, 229, 0.05);
  color: var(--color-primary);
}

.category-item:hover .cat-dot {
  background: var(--color-primary-light);
}

.category-item.active {
  background: rgba(79, 70, 229, 0.08);
  color: var(--color-primary);
  font-weight: 600;
}

.category-item.active .cat-dot {
  background: var(--color-primary);
}

.main {
  flex: 1;
  min-width: 0;
}

.articles-card {
  background: var(--color-surface);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
  overflow: hidden;
}

.loading-state {
  padding: 24px;
}

.skeleton-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.skeleton-item {
  display: flex;
  gap: 16px;
  padding: 16px;
  background: var(--color-bg);
  border-radius: var(--radius-sm);
}

.skeleton-thumb {
  width: 140px;
  height: 96px;
  background: var(--color-border);
  border-radius: var(--radius-sm);
  animation: shimmer 1.5s infinite;
}

.skeleton-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 10px;
}

.skeleton-line {
  background: var(--color-border);
  border-radius: 4px;
  animation: shimmer 1.5s infinite;
}

.skeleton-title { height: 20px; width: 70%; }
.skeleton-meta { height: 14px; width: 50%; }

@keyframes shimmer {
  0% { opacity: 0.6; }
  50% { opacity: 1; }
  100% { opacity: 0.6; }
}

.empty-state {
  padding: 80px 24px;
  text-align: center;
  color: var(--color-text-muted);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.empty-state svg {
  opacity: 0.4;
}

.empty-state p {
  font-size: 15px;
}

.article-items {
  display: flex;
  flex-direction: column;
}

.article-card {
  display: flex;
  gap: 20px;
  padding: 24px;
  border-bottom: 1px solid var(--color-border);
  cursor: pointer;
  transition: var(--transition);
}

.article-card:last-child {
  border-bottom: none;
}

.article-card:hover {
  background: rgba(79, 70, 229, 0.02);
}

.article-thumb {
  width: 180px;
  height: 120px;
  object-fit: cover;
  border-radius: var(--radius-sm);
  flex-shrink: 0;
  background: var(--color-bg);
}

.article-body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.article-title {
  font-size: 17px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin-bottom: 8px;
  line-height: 1.5;
  transition: var(--transition);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.article-card:hover .article-title {
  color: var(--color-primary);
}

.article-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 12px;
}

.tag {
  padding: 2px 8px;
  background: rgba(79, 70, 229, 0.06);
  color: var(--color-primary-light);
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
}

.article-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.meta-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.author, .views {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 13px;
  color: var(--color-text-muted);
}

.read-more {
  font-size: 13px;
  color: var(--color-primary);
  font-weight: 500;
  opacity: 0;
  transform: translateX(-4px);
  transition: var(--transition);
}

.article-card:hover .read-more {
  opacity: 1;
  transform: translateX(0);
}

.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 20px;
  border-top: 1px solid var(--color-border);
}

.page-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 8px 16px;
  background: var(--color-bg);
  color: var(--color-text-secondary);
  border: 1.5px solid var(--color-border);
  border-radius: var(--radius-sm);
  font-size: 14px;
  cursor: pointer;
  transition: var(--transition);
}

.page-btn:hover:not(:disabled) {
  border-color: var(--color-primary);
  color: var(--color-primary);
  background: rgba(79, 70, 229, 0.04);
}

.page-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.page-info {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 14px;
  color: var(--color-text-secondary);
}

.page-info .current {
  font-weight: 700;
  color: var(--color-primary);
}

.page-info .sep {
  color: var(--color-text-muted);
}
</style>
