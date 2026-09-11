<template>
  <header class="app-header">
    <div class="header-inner">
      <router-link to="/" class="logo">
        <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
          <rect width="28" height="28" rx="7" fill="#4F46E5"/>
          <path d="M8 20V10L14 7L20 10V20L14 23L8 20Z" fill="white" fill-opacity="0.9"/>
          <path d="M14 12V19M11 14L14 12L17 14" stroke="#4F46E5" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        <span>FastAPI</span>
      </router-link>
      <nav class="nav">
        <router-link to="/" class="nav-link">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/></svg>
          首页
        </router-link>
        <router-link to="/article/edit" v-if="isLogin" class="nav-link nav-link--primary">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M5 12h14"/></svg>
          写文章
        </router-link>
        <router-link to="/personal" v-if="isLogin" class="nav-link">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="8" r="4"/><path d="M4 20c0-4 3.6-7 8-7s8 3 8 7"/></svg>
          个人中心
        </router-link>
        <router-link to="/login" v-if="!isLogin" class="nav-link nav-link--outline">登录</router-link>
        <a href="#" v-if="isLogin" @click.prevent="handleLogout" class="nav-link nav-link--muted">退出</a>
      </nav>
    </div>
  </header>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { isLoggedIn, removeToken } from '@/utils/auth.js'
import { logout } from '@/api/user.js'

const router = useRouter()
const isLogin = computed(() => isLoggedIn())

async function handleLogout() {
  try { await logout() } catch (e) {}
  removeToken()
  router.push('/')
  location.reload()
}
</script>

<style scoped>
.app-header {
  position: sticky;
  top: 0;
  z-index: 100;
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--color-border);
  box-shadow: 0 1px 0 rgba(0,0,0,0.03);
}

.header-inner {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 24px;
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.logo {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 18px;
  font-weight: 700;
  color: var(--color-text-primary);
  transition: var(--transition);
}

.logo:hover {
  opacity: 0.8;
}

.nav {
  display: flex;
  align-items: center;
  gap: 4px;
}

.nav-link {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 7px 14px;
  border-radius: var(--radius-sm);
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text-secondary);
  transition: var(--transition);
}

.nav-link:hover {
  color: var(--color-primary);
  background: rgba(79, 70, 229, 0.06);
}

.nav-link.router-link-active {
  color: var(--color-primary);
  background: rgba(79, 70, 229, 0.08);
}

.nav-link--primary {
  background: var(--color-primary);
  color: #fff !important;
}

.nav-link--primary:hover {
  background: var(--color-primary-dark);
  opacity: 1 !important;
}

.nav-link--outline {
  background: transparent;
  border: 1.5px solid var(--color-primary);
  color: var(--color-primary) !important;
}

.nav-link--outline:hover {
  background: var(--color-primary);
  color: #fff !important;
}

.nav-link--muted {
  color: var(--color-text-muted);
}

.nav-link--muted:hover {
  color: var(--color-text-secondary);
  background: rgba(0,0,0,0.04);
}
</style>
