<template>
  <div class="page">
    <Header />

    <div class="detail-wrap">
      <div v-if="loading" class="loading-state">
        <div class="skeleton-content">
          <div class="skeleton-line skeleton-h1"></div>
          <div class="skeleton-meta"></div>
          <div class="skeleton-body">
            <div class="skeleton-line" v-for="n in 8" :key="n"></div>
          </div>
        </div>
      </div>

      <div v-else-if="article" class="content-card">
        <div class="article-header">
          <div class="breadcrumb">
            <router-link to="/">首页</router-link>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 18l6-6-6-6"/></svg>
            <span>文章详情</span>
          </div>
          <h1 class="article-title">{{ article.title }}</h1>
          <div class="article-meta-bar">
            <div class="author-info">
              <img :src="'/images/headers/' + (author.picture || '1.jpg')" class="author-avatar" @error="handleAvatarError" />
              <div class="author-detail">
                <span class="author-name">{{ author.nickname }}</span>
                <span class="publish-time">{{ article.create_time }}</span>
              </div>
            </div>
            <div class="meta-right">
              <span class="meta-item">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                {{ article.browse_num }}
              </span>
              <span class="meta-item">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
                {{ commentCount }}
              </span>
            </div>
          </div>
          <div class="tags-row" v-if="tagList.length">
            <span class="tag" v-for="tag in tagList" :key="tag">{{ tag }}</span>
          </div>
        </div>

        <div class="article-body" v-html="article.article_content"></div>

        <div class="article-footer">
          <div class="action-bar">
            <button
              class="action-btn"
              :class="{ active: isFavorite === 0 }"
              @click="toggleFavorite"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" :fill="isFavorite === 0 ? 'currentColor' : 'none'" stroke="currentColor" stroke-width="2"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/></svg>
              {{ isFavorite === 0 ? '已收藏' : '收藏' }}
            </button>
            <router-link
              :to="`/article/edit?article_id=${article.id}`"
              v-if="isOwner"
              class="action-btn"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
              编辑文章
            </router-link>
          </div>
        </div>

        <div class="comments-section">
          <h3 class="section-title">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
            评论 <span class="count">{{ commentCount }}</span>
          </h3>

          <div v-if="isLogin" class="comment-form">
            <img :src="'/images/headers/' + (currentUser?.picture || '1.jpg')" class="form-avatar" />
            <div class="form-body">
              <textarea v-model="commentContent" placeholder="写下你的评论...（至少5个字）" rows="3"></textarea>
              <button class="btn-submit" @click="submitComment" :disabled="!commentContent.trim() || commentContent.trim().length < 5">
                发表回复
              </button>
            </div>
          </div>
          <div v-else class="login-tip">
            <router-link to="/login" class="login-link">登录</router-link>后发表评论
          </div>

          <div class="comment-list" v-if="commentList.length">
            <div v-for="item in commentList" :key="item.id" class="comment-item">
              <div class="comment-main">
                <img :src="item.picture ? '/images/headers/' + item.picture : '/images/headers/1.jpg'" class="comment-avatar" />
                <div class="comment-content-wrap">
                  <div class="comment-header">
                    <span class="nickname">{{ item.nickname }}</span>
                    <span class="floor">#{{ item.floor_number }}楼</span>
                    <span class="time">{{ item.create_time }}</span>
                  </div>
                  <div class="comment-text" v-html="item.content"></div>
                  <button v-if="isLogin" class="reply-btn" @click="showReplyForm(item)">
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
                    回复
                  </button>

                  <div v-if="replyingTo === item.id" class="reply-form">
                    <textarea v-model="replyContent" placeholder="写下你的回复...（至少5个字）" rows="2"></textarea>
                    <div class="reply-actions">
                      <button class="btn-reply" @click="submitReply(item)" :disabled="!replyContent.trim() || replyContent.trim().length < 5">发送</button>
                      <button class="btn-cancel" @click="cancelReply">取消</button>
                    </div>
                  </div>

                  <div class="reply-list" v-if="item.reply_list && item.reply_list.length">
                    <div v-for="reply in item.reply_list" :key="reply.content.id" class="reply-item">
                      <div class="reply-main">
                        <img :src="reply.from_user.picture ? '/images/headers/' + reply.from_user.picture : '/images/headers/1.jpg'" class="reply-avatar" />
                        <div class="reply-body">
                          <span class="nickname from">{{ reply.from_user.nickname }}</span>
                          <span class="reply-action-text">回复</span>
                          <span class="nickname to">{{ reply.to_user.nickname }}</span>
                          <span class="reply-text">：</span>
                          <span class="reply-content-text" v-html="reply.content.content"></span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
          <div v-else class="no-comments">
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
            <p>暂无评论，快来抢沙发</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getArticleDetail } from '@/api/article.js'
import { updateFavoriteStatus } from '@/api/favorite.js'
import { addComment, replyComment } from '@/api/comment.js'
import { isLoggedIn, getUserInfo } from '@/utils/auth.js'
import Header from '@/components/Header.vue'

const route = useRoute()
const router = useRouter()
const article = ref(null)
const author = ref({})
const commentList = ref([])
const commentCount = ref(0)
const isFavorite = ref(1)
const tagList = ref([])
const loading = ref(false)
const commentContent = ref('')
const replyContent = ref('')
const replyingTo = ref(null)
const currentUser = ref(null)

const isLogin = computed(() => isLoggedIn())

// 只有登录用户且是文章作者才显示编辑按钮
const isOwner = computed(() => {
  const user = getUserInfo()
  return user && article.value && user.user_id === article.value.user_id
})

watch(() => route.fullPath, () => {
  if (isLoggedIn()) {
    currentUser.value = JSON.parse(localStorage.getItem('user_info') || 'null')
  }
}, { immediate: true })

async function fetchDetail() {
  const articleId = route.params.id
  if (!articleId) return
  loading.value = true
  try {
    const res = await getArticleDetail(articleId)
    if (res.code === 200) {
      const data = res.data
      article.value = data
      author.value = data.author || {}
      commentList.value = data.comment_list || []
      commentCount.value = data.comment_count || 0
      isFavorite.value = data.is_favorite || 1
      tagList.value = data.tag_list || []
    }
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

async function toggleFavorite() {
  const newCanceled = isFavorite.value === 0 ? 1 : 0
  try {
    await updateFavoriteStatus({ article_id: article.value.id, canceled: newCanceled })
    isFavorite.value = newCanceled
  } catch (e) {
    alert('操作失败：' + (e.message || '请先登录'))
  }
}

async function submitComment() {
  if (commentContent.value.trim().length < 5) {
    alert('评论至少需要5个字')
    return
  }
  try {
    await addComment({ article_id: article.value.id, content: commentContent.value })
    commentContent.value = ''
    fetchDetail()
  } catch (e) {
    alert('发表评论失败：' + (e.message || '请先登录'))
  }
}

function showReplyForm(item) {
  replyingTo.value = item.id
}

function cancelReply() {
  replyingTo.value = null
  replyContent.value = ''
}

async function submitReply(item) {
  if (replyContent.value.trim().length < 5) {
    alert('回复至少需要5个字')
    return
  }
  try {
    await replyComment({
      article_id: article.value.id,
      content: replyContent.value,
      reply_id: item.id,
      base_reply_id: item.id,
    })
    replyContent.value = ''
    replyingTo.value = null
    fetchDetail()
  } catch (e) {
    alert('回复失败：' + (e.message || '请先登录'))
  }
}

watch(
  () => route.params.id,
  (id) => { if (id) fetchDetail() },
  { immediate: true }
)
</script>

<style scoped>
.page {
  min-height: 100vh;
  background: var(--color-bg);
}

.detail-wrap {
  max-width: 860px;
  margin: 0 auto;
  padding: 28px 24px;
}

.loading-state {
  background: var(--color-surface);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
  padding: 32px;
}

.skeleton-content { display: flex; flex-direction: column; gap: 16px; }
.skeleton-h1 { height: 32px; width: 70%; }
.skeleton-meta { height: 16px; width: 40%; }
.skeleton-body { display: flex; flex-direction: column; gap: 10px; margin-top: 16px; }
.skeleton-line { height: 14px; background: var(--color-border); border-radius: 4px; }
.skeleton-line:nth-child(odd) { width: 100%; }
.skeleton-line:nth-child(even) { width: 85%; }
@keyframes shimmer {
  0% { opacity: 0.5; }
  50% { opacity: 1; }
  100% { opacity: 0.5; }
}
.skeleton-h1, .skeleton-meta, .skeleton-line { animation: shimmer 1.5s infinite; }

.content-card {
  background: var(--color-surface);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
  overflow: hidden;
}

.article-header {
  padding: 32px 40px 24px;
  border-bottom: 1px solid var(--color-border);
}

.breadcrumb {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--color-text-muted);
  margin-bottom: 16px;
}

.breadcrumb a {
  color: var(--color-primary);
}

.breadcrumb a:hover { text-decoration: underline; }

.article-title {
  font-size: 28px;
  font-weight: 700;
  color: var(--color-text-primary);
  line-height: 1.4;
  margin-bottom: 20px;
}

.article-meta-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.author-info {
  display: flex;
  align-items: center;
  gap: 10px;
}

.author-avatar {
  width: 38px;
  height: 38px;
  border-radius: 50%;
  object-fit: cover;
}

.author-detail {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.author-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.publish-time {
  font-size: 12px;
  color: var(--color-text-muted);
}

.meta-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 13px;
  color: var(--color-text-muted);
}

.tags-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.tag {
  padding: 3px 10px;
  background: rgba(79, 70, 229, 0.06);
  color: var(--color-primary-light);
  border-radius: 20px;
  font-size: 12px;
  font-weight: 500;
}

.article-body {
  padding: 32px 40px;
  line-height: 1.85;
  font-size: 16px;
  color: var(--color-text-primary);
}

.article-footer {
  padding: 0 40px 24px;
}

.action-bar {
  display: flex;
  gap: 12px;
  padding-top: 20px;
  border-top: 1px solid var(--color-border);
}

.action-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 9px 20px;
  background: var(--color-bg);
  color: var(--color-text-secondary);
  border: 1.5px solid var(--color-border);
  border-radius: 20px;
  font-size: 14px;
  cursor: pointer;
  transition: var(--transition);
  text-decoration: none;
}

.action-btn:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
  background: rgba(79, 70, 229, 0.04);
}

.action-btn.active {
  background: rgba(79, 70, 229, 0.08);
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.comments-section {
  padding: 24px 40px 40px;
  border-top: 1px solid var(--color-border);
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 18px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin-bottom: 24px;
}

.section-title .count {
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text-muted);
  background: var(--color-bg);
  padding: 2px 8px;
  border-radius: 10px;
}

.comment-form {
  display: flex;
  gap: 14px;
  margin-bottom: 28px;
}

.form-avatar {
  width: 38px;
  height: 38px;
  border-radius: 50%;
  object-fit: cover;
  flex-shrink: 0;
}

.form-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 10px;
  align-items: flex-end;
}

.form-body textarea {
  width: 100%;
  padding: 12px;
  border: 1.5px solid var(--color-border);
  border-radius: var(--radius-sm);
  font-size: 14px;
  resize: vertical;
  transition: var(--transition);
  background: var(--color-bg);
  color: var(--color-text-primary);
  line-height: 1.6;
}

.form-body textarea:focus {
  border-color: var(--color-primary);
  background: #fff;
  outline: none;
}

.btn-submit {
  padding: 8px 20px;
  background: var(--color-primary);
  color: #fff;
  border: none;
  border-radius: 20px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: var(--transition);
}

.btn-submit:hover:not(:disabled) {
  background: var(--color-primary-dark);
}

.btn-submit:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.login-tip {
  padding: 20px;
  background: var(--color-bg);
  border-radius: var(--radius-sm);
  text-align: center;
  font-size: 14px;
  color: var(--color-text-secondary);
  margin-bottom: 28px;
}

.login-link {
  color: var(--color-primary);
  font-weight: 600;
}

.comment-list {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.comment-item {
  padding-bottom: 24px;
  border-bottom: 1px solid var(--color-border);
}

.comment-item:last-child {
  border-bottom: none;
}

.comment-main {
  display: flex;
  gap: 14px;
}

.comment-avatar {
  width: 38px;
  height: 38px;
  border-radius: 50%;
  object-fit: cover;
  flex-shrink: 0;
}

.comment-content-wrap {
  flex: 1;
  min-width: 0;
}

.comment-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
  flex-wrap: wrap;
}

.nickname {
  font-weight: 600;
  font-size: 14px;
  color: var(--color-text-primary);
}

.floor {
  font-size: 12px;
  color: var(--color-primary);
  background: rgba(79, 70, 229, 0.06);
  padding: 1px 6px;
  border-radius: 4px;
}

.time {
  font-size: 12px;
  color: var(--color-text-muted);
}

.comment-text {
  font-size: 15px;
  line-height: 1.7;
  color: var(--color-text-primary);
  margin-bottom: 8px;
}

.reply-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--color-text-muted);
  background: none;
  border: none;
  cursor: pointer;
  padding: 0;
  transition: var(--transition);
}

.reply-btn:hover {
  color: var(--color-primary);
}

.reply-form {
  margin-top: 12px;
}

.reply-form textarea {
  width: 100%;
  padding: 10px;
  border: 1.5px solid var(--color-border);
  border-radius: var(--radius-sm);
  font-size: 14px;
  resize: vertical;
  background: var(--color-bg);
  transition: var(--transition);
  color: var(--color-text-primary);
  line-height: 1.6;
}

.reply-form textarea:focus {
  border-color: var(--color-primary);
  background: #fff;
  outline: none;
}

.reply-actions {
  display: flex;
  gap: 8px;
  margin-top: 8px;
}

.btn-reply {
  padding: 6px 14px;
  background: var(--color-primary);
  color: #fff;
  border: none;
  border-radius: var(--radius-sm);
  font-size: 12px;
  cursor: pointer;
  transition: var(--transition);
}

.btn-reply:hover:not(:disabled) {
  background: var(--color-primary-dark);
}

.btn-reply:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.btn-cancel {
  padding: 6px 14px;
  background: var(--color-bg);
  color: var(--color-text-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  font-size: 12px;
  cursor: pointer;
  transition: var(--transition);
}

.btn-cancel:hover {
  background: var(--color-border);
}

.reply-list {
  margin-top: 12px;
  border-radius: var(--radius-sm);
  overflow: hidden;
}

.reply-item {
  padding: 10px 14px;
  background: var(--color-bg);
  border-radius: var(--radius-sm);
  margin-bottom: 6px;
}

.reply-item:last-child {
  margin-bottom: 0;
}

.reply-main {
  display: flex;
  gap: 10px;
  align-items: flex-start;
}

.reply-avatar {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  object-fit: cover;
  flex-shrink: 0;
}

.reply-body {
  flex: 1;
  font-size: 14px;
  line-height: 1.6;
}

.nickname.from { color: var(--color-primary); }
.nickname.to { color: var(--color-primary); }
.reply-action-text, .reply-text { color: var(--color-text-secondary); }

.no-comments {
  text-align: center;
  padding: 40px;
  color: var(--color-text-muted);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}

.no-comments svg { opacity: 0.3; }
.no-comments p { font-size: 14px; }
</style>
