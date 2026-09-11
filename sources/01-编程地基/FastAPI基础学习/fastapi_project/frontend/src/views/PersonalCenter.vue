<template>
  <div class="page">
    <Header />

    <div class="personal-wrap">
      <div class="personal-layout">
        <aside class="sidebar">
          <div class="user-card">
            <img :src="'/images/headers/' + (user.picture || '1.jpg')" class="avatar" />
            <h3 class="nickname">{{ user.nickname || '未知用户' }}</h3>
            <p class="job">{{ user.job || '暂无职位' }}</p>
          </div>

          <nav class="tab-nav">
            <div
              v-for="item in tabs"
              :key="item.key"
              class="tab-item"
              :class="{ active: activeTab === item.key }"
              @click="switchTab(item.key)"
            >
              <svg v-if="item.key === 'article'" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
              <svg v-if="item.key === 'favorite'" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/></svg>
              <svg v-if="item.key === 'comment'" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
              {{ item.label }}
            </div>
          </nav>
        </aside>

        <main class="main">
          <div class="content-card">
            <div class="card-header-bar">
              <h2 class="card-title">{{ currentTabLabel }}</h2>

              <div v-if="activeTab === 'article'" class="subtabs">
                <button type="button" class="subtab" :class="{ active: articleStatus === 1 }" @click="setArticleStatus(1)">已发布</button>
                <button type="button" class="subtab" :class="{ active: articleStatus === 0 }" @click="setArticleStatus(0)">草稿</button>
              </div>
            </div>

            <div v-if="loading" class="loading-state">
              <div class="skeleton-item" v-for="n in 3" :key="n">
                <div class="skeleton-thumb"></div>
                <div class="skeleton-info">
                  <div class="skeleton-line"></div>
                  <div class="skeleton-line skeleton-line-sm"></div>
                </div>
              </div>
            </div>

            <div v-else-if="activeTab === 'comment' && comments.length === 0" class="empty-state">
              <svg width="56" height="56" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="3" y="3" width="18" height="18" rx="3"/><path d="M8 12h8M12 8v8"/></svg>
              <p>暂无评论</p>
            </div>

            <div v-else-if="activeTab === 'comment'" class="comment-list">
              <div v-for="item in comments" :key="item.id" class="comment-item" @click="goDetail(item.article_id)">
                <div class="comment-article-title">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
                  {{ item.article_title }}
                </div>
                <div class="comment-body">
                  <span class="comment-floor">#{{ item.floor_number }}</span>
                  <span class="comment-text">{{ item.content }}</span>
                </div>
                <div class="comment-meta">
                  <span>{{ item.create_time }}</span>
                </div>
              </div>
            </div>

            <div v-else-if="articles.length === 0" class="empty-state">
              <svg width="56" height="56" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="3" y="3" width="18" height="18" rx="3"/><path d="M8 12h8M12 8v8"/></svg>
              <p>暂无内容</p>
            </div>

            <div v-else class="article-list">
              <div v-for="item in articles" :key="item.id" class="article-item" @click="goDetail(item.id)">
                <img :src="item.article_image" class="thumb" />
                <div class="info">
                  <h3>{{ item.title }}</h3>
                  <div class="meta">
                    <span>
                      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                      {{ item.browse_num }}
                    </span>
                    <span>
                      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/></svg>
                      {{ item.create_time }}
                    </span>
                  </div>
                </div>
              </div>
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
import { getMe } from '@/api/user.js'
import { getPersonalCenter } from '@/api/personal.js'
import Header from '@/components/Header.vue'

const router = useRouter()
const activeTab = ref('article')
const articleStatus = ref(1)
const loading = ref(false)
const articles = ref([])
const comments = ref([])
const user = ref({})

const tabs = [
  { key: 'article', label: '我的文章' },
  { key: 'favorite', label: '我的收藏' },
  { key: 'comment', label: '我的评论' },
]

const currentTabLabel = computed(() => {
  return tabs.find(t => t.key === activeTab.value)?.label || ''
})

async function fetchData() {
  loading.value = true
  try {
    const res = await getMe()
    if (res.code === 200) {
      user.value = res.data || {}
    }

    const listRes = await getPersonalCenter(activeTab.value, activeTab.value === 'article' ? articleStatus.value : 1)
    if (listRes.code === 200) {
      if (activeTab.value === 'comment') {
        comments.value = Array.isArray(listRes.data) ? listRes.data : []
      } else {
        articles.value = Array.isArray(listRes.data) ? listRes.data : []
      }
    } else {
      console.warn('personal list failed:', listRes)
      if (activeTab.value === 'comment') {
        comments.value = []
      } else {
        articles.value = []
      }
    }
  } catch (e) {
    console.error(e)
    if (activeTab.value === 'comment') {
      comments.value = []
    } else {
      articles.value = []
    }
  } finally {
    loading.value = false
  }
}

function switchTab(key) {
  activeTab.value = key
  if (key !== 'article') {
    articleStatus.value = 1
  }
  fetchData()
}

function setArticleStatus(v) {
  if (articleStatus.value === v) return
  articleStatus.value = v
  fetchData()
}

function goDetail(id) {
  router.push(`/article/detail/${id}`)
}

onMounted(() => {
  fetchData()
})
</script>

<style scoped>
.page {
  min-height: 100vh;
  background: var(--color-bg);
}

.personal-wrap {
  max-width: 1100px;
  margin: 0 auto;
  padding: 28px 24px;
}

.personal-layout {
  display: flex;
  gap: 24px;
  align-items: flex-start;
}

.sidebar {
  width: 220px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
  position: sticky;
  top: 84px;
}

.user-card {
  background: var(--color-surface);
  border-radius: var(--radius-md);
  padding: 28px 20px;
  box-shadow: var(--shadow-sm);
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.avatar {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  object-fit: cover;
  border: 3px solid var(--color-border);
}

.nickname {
  font-size: 17px;
  font-weight: 700;
  color: var(--color-text-primary);
}

.job {
  font-size: 13px;
  color: var(--color-text-muted);
}

.tab-nav {
  background: var(--color-surface);
  border-radius: var(--radius-md);
  padding: 8px;
  box-shadow: var(--shadow-sm);
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.tab-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 11px 14px;
  border-radius: var(--radius-sm);
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: var(--transition);
}

.tab-item:hover {
  background: rgba(79, 70, 229, 0.05);
  color: var(--color-primary);
}

.tab-item.active {
  background: rgba(79, 70, 229, 0.08);
  color: var(--color-primary);
  font-weight: 600;
}

.tab-item svg {
  flex-shrink: 0;
}

.main {
  flex: 1;
  min-width: 0;
}

.content-card {
  background: var(--color-surface);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
  overflow: hidden;
}

.card-header-bar {
  padding: 20px 24px;
  border-bottom: 1px solid var(--color-border);
}

.card-title {
  font-size: 17px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.loading-state {
  padding: 24px;
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
  width: 100px;
  height: 70px;
  background: var(--color-border);
  border-radius: var(--radius-sm);
  animation: shimmer 1.5s infinite;
  flex-shrink: 0;
}

.skeleton-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 8px;
}

.skeleton-line {
  height: 16px;
  background: var(--color-border);
  border-radius: 4px;
  animation: shimmer 1.5s infinite;
  width: 60%;
}

.skeleton-line-sm {
  height: 12px;
  width: 35%;
}

@keyframes shimmer {
  0% { opacity: 0.5; }
  50% { opacity: 1; }
  100% { opacity: 0.5; }
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

.empty-state svg { opacity: 0.3; }
.empty-state p { font-size: 15px; }

.subtabs {
  display: flex;
  gap: 8px;
}

.subtab {
  border: 1px solid var(--color-border);
  background: transparent;
  color: var(--color-text-secondary);
  padding: 6px 10px;
  border-radius: 999px;
  font-size: 13px;
  cursor: pointer;
  transition: var(--transition);
}

.subtab:hover {
  border-color: rgba(79, 70, 229, 0.4);
  color: var(--color-primary);
}

.subtab.active {
  background: rgba(79, 70, 229, 0.10);
  border-color: rgba(79, 70, 229, 0.30);
  color: var(--color-primary);
}

.article-list {
  display: flex;
  flex-direction: column;
}

.article-item {
  display: flex;
  gap: 16px;
  padding: 20px 24px;
  border-bottom: 1px solid var(--color-border);
  cursor: pointer;
  transition: var(--transition);
}

.article-item:last-child {
  border-bottom: none;
}

.article-item:hover {
  background: rgba(79, 70, 229, 0.02);
}

.thumb {
  width: 120px;
  height: 76px;
  object-fit: cover;
  border-radius: var(--radius-sm);
  flex-shrink: 0;
}

.info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 8px;
}

.info h3 {
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text-primary);
  transition: var(--transition);
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.article-item:hover .info h3 {
  color: var(--color-primary);
}

.meta {
  display: flex;
  gap: 16px;
  font-size: 12px;
  color: var(--color-text-muted);
}

.meta span {
  display: flex;
  align-items: center;
  gap: 4px;
}

.comment-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.comment-item {
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: 14px 16px;
  cursor: pointer;
  transition: var(--transition);
}

.comment-item:hover {
  border-color: var(--color-primary);
  box-shadow: var(--shadow-sm);
}

.comment-article-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--color-text-muted);
  margin-bottom: 8px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.comment-body {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin-bottom: 8px;
}

.comment-floor {
  font-size: 13px;
  color: var(--color-primary);
  font-weight: 600;
  flex-shrink: 0;
}

.comment-text {
  font-size: 14px;
  color: var(--color-text-primary);
  line-height: 1.6;
  word-break: break-all;
}

.comment-meta {
  font-size: 12px;
  color: var(--color-text-muted);
}
</style>
