const TOKEN_KEY = 'fastapi_token'

export function getToken() {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token)
}

export function removeToken() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem('user_info')
}

export function getUserInfo() {
  return JSON.parse(localStorage.getItem('user_info') || 'null')
}

export function isLoggedIn() {
  return !!getToken()
}
