<template>
  <div class="register-page">
    <div class="register-card">
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

      <h1 class="title">创建账号</h1>
      <p class="subtitle">加入我们，开始分享您的故事</p>

      <form @submit.prevent="handleRegister" class="form">
        <div class="field">
          <label>邮箱</label>
          <div class="input-wrap">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="4" width="20" height="16" rx="3"/><path d="M2 8l10 7 10-7"/></svg>
            <input v-model="form.username" placeholder="请输入邮箱" type="email" />
          </div>
        </div>

        <div class="field">
          <label>密码</label>
          <div class="input-wrap">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
            <input v-model="form.password" type="password" placeholder="请输入密码（至少6位）" />
          </div>
        </div>

        <div class="field">
          <label>确认密码</label>
          <div class="input-wrap">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
            <input v-model="form.second_password" type="password" placeholder="请再次输入密码" />
          </div>
        </div>

        <div class="field">
          <label>邮箱验证码</label>
          <div class="ecode-row">
            <div class="input-wrap input-wrap--grow">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="3"/><path d="M8 12h8M12 8v8"/></svg>
              <input v-model="form.ecode" placeholder="请输入邮箱验证码" />
            </div>
            <button type="button" class="btn-send" @click="sendCode" :disabled="countdown > 0">
              {{ countdown > 0 ? `${countdown}s` : '发送验证码' }}
            </button>
          </div>
        </div>

        <div class="error-msg" v-if="error">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 8v4M12 16h.01"/></svg>
          {{ error }}
        </div>

        <div class="success-msg" v-if="successMsg">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M9 12l2 2 4-4"/></svg>
          {{ successMsg }}
        </div>

        <button type="submit" class="btn-primary" :disabled="loading">注册</button>
      </form>

      <div class="footer-links">
        <router-link to="/login">已有账号？<strong>去登录</strong></router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { sendEmailCode, register } from '@/api/user.js'
import { setToken } from '@/utils/auth.js'

const router = useRouter()
const form = ref({ username: '', password: '', second_password: '', ecode: '' })
const error = ref('')
const successMsg = ref('')
const loading = ref(false)
const countdown = ref(0)

async function sendCode() {
  if (!form.value.username) {
    error.value = '请先输入邮箱'
    return
  }
  error.value = ''
  successMsg.value = ''
  try {
    const res = await sendEmailCode({ email: form.value.username })
    if (res.code === 200) {
      successMsg.value = '验证码已发送，请查收'
      countdown.value = 60
      const timer = setInterval(() => {
        countdown.value--
        if (countdown.value <= 0) clearInterval(timer)
      }, 1000)
    } else {
      error.value = res.msg || '发送失败'
    }
  } catch (e) {
    error.value = '发送失败'
  }
}

async function handleRegister() {
  error.value = ''
  successMsg.value = ''
  if (!form.value.username || !form.value.password || !form.value.ecode) {
    error.value = '请填写完整信息'
    return
  }
  if (form.value.password !== form.value.second_password) {
    error.value = '两次密码不一致'
    return
  }
  loading.value = true
  try {
    const res = await register(form.value)
    if (res.code === 200) {
      successMsg.value = '注册成功，即将跳转登录...'
      setTimeout(() => router.push('/login'), 1500)
    } else {
      error.value = res.msg || '注册失败'
    }
  } catch (e) {
    error.value = e.message || '注册失败'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.register-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #F0FDF4 0%, #F8FAFC 50%, #EEF2FF 100%);
  padding: 24px;
}

.register-card {
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

.ecode-row {
  display: flex;
  gap: 10px;
  align-items: center;
}

.btn-send {
  padding: 11px 16px;
  background: var(--color-primary);
  color: #fff;
  border: none;
  border-radius: var(--radius-sm);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  white-space: nowrap;
  transition: var(--transition);
  flex-shrink: 0;
}

.btn-send:hover:not(:disabled) {
  background: var(--color-primary-dark);
}

.btn-send:disabled {
  background: var(--color-border);
  color: var(--color-text-muted);
  cursor: not-allowed;
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

.success-msg {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 14px;
  background: #F0FDF4;
  border: 1px solid #BBF7D0;
  border-radius: var(--radius-sm);
  color: #16A34A;
  font-size: 13px;
}

.btn-primary {
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

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.footer-links {
  margin-top: 24px;
  text-align: center;
  font-size: 14px;
  color: var(--color-text-secondary);
}

.footer-links strong {
  color: var(--color-primary);
}
</style>
