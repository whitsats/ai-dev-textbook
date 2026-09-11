<template>
  <div class="login-page">
    <div class="login-card">
      <div class="card-header">
        <router-link to="/" class="back-home">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 12H5M12 5l-7 7 7 7"/></svg>
        </router-link>
        <div class="brand">
          <svg width="36" height="36" viewBox="0 0 28 28" fill="none">
            <rect width="28" height="28" rx="7" fill="#4F46E5"/>
            <path d="M8 20V10L14 7L20 10V20L14 23L8 20Z" fill="white" fill-opacity="0.9"/>
            <path d="M14 12V19M11 14L14 12L17 14" stroke="#4F46E5" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          <span>FastAPI</span>
        </div>
      </div>

      <h1 class="title">欢迎回来</h1>
      <p class="subtitle">登录您的账号，继续探索</p>

      <form @submit.prevent="handleLogin" class="form">
        <div class="field">
          <label>用户名 / 邮箱</label>
          <div class="input-wrap">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="8" r="4"/><path d="M4 20c0-4 3.6-7 8-7s8 3 8 7"/></svg>
            <input v-model="form.username" placeholder="请输入用户名（邮箱）" autocomplete="username" />
          </div>
        </div>

        <div class="field">
          <label>密码</label>
          <div class="input-wrap">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
            <input v-model="form.password" type="password" placeholder="请输入密码" autocomplete="current-password" />
          </div>
        </div>

        <div class="field">
          <label>验证码</label>
          <div class="vcode-row">
            <div class="input-wrap input-wrap--grow">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="3"/><path d="M8 12h8M12 8v8"/></svg>
              <input v-model="form.vcode" placeholder="请输入验证码" />
            </div>
            <img :src="vcodeUrl" @click="refreshVcode" class="vcode-img" alt="验证码" />
          </div>
        </div>

        <div class="error-msg" v-if="error">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 8v4M12 16h.01"/></svg>
          {{ error }}
        </div>

        <button type="submit" class="btn-primary" :disabled="loading">
          <span v-if="loading" class="spinner"></span>
          {{ loading ? '登录中...' : '登录' }}
        </button>
      </form>

      <div class="footer-links">
        <router-link to="/register">还没有账号？<strong>去注册</strong></router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { login } from '@/api/user.js'
import { setToken } from '@/utils/auth.js'
import { getVcodeUrl } from '@/api/user.js'

const router = useRouter()
const form = ref({ username: '', password: '', vcode: '' })
const error = ref('')
const loading = ref(false)
const vcodeUrl = ref('')

function refreshVcode() {
  vcodeUrl.value = getVcodeUrl()
}

async function handleLogin() {
  error.value = ''
  if (!form.value.username || !form.value.password || !form.value.vcode) {
    error.value = '请填写完整信息'
    return
  }
  loading.value = true
  try {
    const res = await login(form.value)
    if (res.code === 200) {
      setToken(res.data.token)
      localStorage.setItem('user_info', JSON.stringify({
        user_id: res.data.user_id,
        username: res.data.username,
        nickname: res.data.nickname,
        picture: res.data.picture,
      }))
      router.push('/')
    } else {
      error.value = res.msg || '登录失败'
      refreshVcode()
    }
  } catch (e) {
    error.value = e.message || '登录失败'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  refreshVcode()
})
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #EEF2FF 0%, #F8FAFC 50%, #FDF4FF 100%);
  padding: 24px;
}

.login-card {
  background: var(--color-surface);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  padding: 40px;
  width: 100%;
  max-width: 420px;
  border: 1px solid rgba(0,0,0,0.04);
}

.card-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 32px;
}

.back-home {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: var(--radius-sm);
  color: var(--color-text-secondary);
  transition: var(--transition);
}

.back-home:hover {
  background: var(--color-bg);
  color: var(--color-primary);
}

.brand {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 18px;
  font-weight: 700;
  color: var(--color-text-primary);
}

.title {
  font-size: 26px;
  font-weight: 700;
  color: var(--color-text-primary);
  margin-bottom: 6px;
}

.subtitle {
  font-size: 14px;
  color: var(--color-text-secondary);
  margin-bottom: 32px;
}

.form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field label {
  font-size: 13px;
  font-weight: 500;
  color: var(--color-text-secondary);
}

.input-wrap {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 11px 14px;
  background: var(--color-bg);
  border: 1.5px solid var(--color-border);
  border-radius: var(--radius-sm);
  transition: var(--transition);
}

.input-wrap:focus-within {
  border-color: var(--color-primary);
  background: #fff;
  box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.1);
}

.input-wrap svg {
  color: var(--color-text-muted);
  flex-shrink: 0;
}

.input-wrap input {
  flex: 1;
  border: none;
  background: transparent;
  font-size: 14px;
  color: var(--color-text-primary);
}

.input-wrap input::placeholder {
  color: var(--color-text-muted);
}

.input-wrap--grow {
  flex: 1;
}

.vcode-row {
  display: flex;
  gap: 10px;
  align-items: center;
}

.vcode-img {
  width: 100px;
  height: 42px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  border: 1px solid var(--color-border);
  transition: var(--transition);
  flex-shrink: 0;
}

.vcode-img:hover {
  opacity: 0.8;
}

.error-msg {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 14px;
  background: #FEF2F2;
  border: 1px solid #FECACA;
  border-radius: var(--radius-sm);
  color: #DC2626;
  font-size: 13px;
}

.btn-primary {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  width: 100%;
  padding: 13px;
  background: var(--color-primary);
  color: #fff;
  border: none;
  border-radius: var(--radius-sm);
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: var(--transition);
}

.btn-primary:hover:not(:disabled) {
  background: var(--color-primary-dark);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(79, 70, 229, 0.3);
}

.btn-primary:active:not(:disabled) {
  transform: translateY(0);
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.footer-links {
  margin-top: 24px;
  text-align: center;
  font-size: 14px;
  color: var(--color-text-secondary);
}

.footer-links a strong {
  color: var(--color-primary);
}
</style>
