import { ref, computed, reactive } from 'vue'
import { request } from '../api'

export interface UserInfo {
  id: number
  username: string
  email: string | null
  role: 'vip' | 'normal' | 'admin'
  daily_limit: number
  vip_expires_at: string | null
  created_at: string
}

export interface UserDailyUsage {
  used_today: number
  remaining: number
  is_unlimited: boolean
}

const TOKEN_KEY = 'pixelle_auth_token'
const USER_KEY = 'pixelle_auth_user'

// Reactive state
const token = ref<string | null>(localStorage.getItem(TOKEN_KEY))
const currentUser = ref<UserInfo | null>(_loadUser())

function _loadUser(): UserInfo | null {
  try {
    const raw = localStorage.getItem(USER_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

function _saveUser(user: UserInfo | null) {
  if (user) {
    localStorage.setItem(USER_KEY, JSON.stringify(user))
  } else {
    localStorage.removeItem(USER_KEY)
  }
  currentUser.value = user
}

export function useAuth() {
  const isLoggedIn = computed(() => !!token.value && !!currentUser.value)
  const isAdmin = computed(() => currentUser.value?.role === 'admin')
  const isVip = computed(() => currentUser.value?.role === 'vip')
  const roleLabel = computed(() => {
    const role = currentUser.value?.role
    if (role === 'admin') return '管理员'
    if (role === 'vip') return 'VIP 会员'
    return '普通用户'
  })

  async function login(username: string, password: string): Promise<UserInfo> {
    const res = await request<{ access_token: string; user: UserInfo }>('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    })
    token.value = res.access_token
    localStorage.setItem(TOKEN_KEY, res.access_token)
    _saveUser(res.user)
    return res.user
  }

  async function register(username: string, password: string, email?: string): Promise<UserInfo> {
    const res = await request<{ access_token: string; user: UserInfo }>('/api/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password, email }),
    })
    token.value = res.access_token
    localStorage.setItem(TOKEN_KEY, res.access_token)
    _saveUser(res.user)
    return res.user
  }

  function logout() {
    token.value = null
    localStorage.removeItem(TOKEN_KEY)
    _saveUser(null)
  }

  async function fetchMe(): Promise<UserInfo> {
    const user = await request<UserInfo>('/api/auth/me', {
      headers: _authHeaders(),
    })
    _saveUser(user)
    return user
  }

  async function fetchUsage(): Promise<UserDailyUsage> {
    return request<UserDailyUsage>('/api/auth/usage', {
      headers: _authHeaders(),
    })
  }

  function _authHeaders(): Record<string, string> {
    const t = token.value
    return t ? { Authorization: `Bearer ${t}` } : {}
  }

  return {
    token,
    currentUser,
    isLoggedIn,
    isAdmin,
    isVip,
    roleLabel,
    login,
    register,
    logout,
    fetchMe,
    fetchUsage,
    _authHeaders,
  }
}

// Singleton instance for global use
let _authInstance: ReturnType<typeof useAuth> | null = null

export function getAuth(): ReturnType<typeof useAuth> {
  if (!_authInstance) {
    _authInstance = useAuth()
  }
  return _authInstance
}
