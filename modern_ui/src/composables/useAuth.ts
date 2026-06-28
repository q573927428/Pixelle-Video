import { ref, computed, reactive } from 'vue'
import { request } from '../api'

export interface UserInfo {
  id: number
  username: string
  email: string | null
  phone: string | null
  role: 'vip' | 'svip' | 'normal' | 'admin'
  daily_limit: number
  vip_expires_at: string | null
  zs_balance: number
  invite_code: string | null
  status: number
  created_at: string
}

export interface UserDailyUsage {
  used_today: number
  remaining: number
  is_unlimited: boolean
}

const TOKEN_KEY = 'pixelle_auth_token'
const REFRESH_TOKEN_KEY = 'pixelle_refresh_token'
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
  const isSvip = computed(() => currentUser.value?.role === 'svip')
  const roleLabel = computed(() => {
    const role = currentUser.value?.role
    if (role === 'admin') return '管理员'
    if (role === 'svip') return 'SVIP 会员'
    if (role === 'vip') return 'VIP 会员'
    return '普通用户'
  })
  const zsBalance = computed(() => currentUser.value?.zs_balance ?? 0)
  const vipExpiresAt = computed(() => currentUser.value?.vip_expires_at ?? null)
  
  // VIP是否有效（角色为vip/svip且未过期）
  const isVipEffective = computed(() => {
    const role = currentUser.value?.role
    if (role !== 'vip' && role !== 'svip') return false
    if (!currentUser.value?.vip_expires_at) return false
    return new Date(currentUser.value.vip_expires_at) > new Date()
  })
  
  // 是否为会员（VIP或SVIP）
  const isMember = computed(() => isVipEffective.value)
  
  // 用户折扣率（100=无折扣, 90=9折, 80=8折）
  const userDiscount = computed(() => {
    const role = currentUser.value?.role
    if (role === 'svip') return 80
    if (role === 'vip') return 90
    return 100
  })
  
  // 用户队列优先级
  const userQueuePriority = computed(() => {
    const role = currentUser.value?.role
    if (role === 'svip') return 2
    if (role === 'vip') return 1
    return 0
  })

  async function login(username: string, password: string): Promise<UserInfo> {
    const res = await request<{ access_token: string; refresh_token: string; user: UserInfo }>('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    })
    token.value = res.access_token
    localStorage.setItem(TOKEN_KEY, res.access_token)
    localStorage.setItem(REFRESH_TOKEN_KEY, res.refresh_token)
    _saveUser(res.user)
    return res.user
  }

  async function loginByPhone(phone: string, password: string): Promise<UserInfo> {
    const res = await request<{ access_token: string; refresh_token: string; user: UserInfo }>('/api/auth/login-by-phone', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ phone, password }),
    })
    token.value = res.access_token
    localStorage.setItem(TOKEN_KEY, res.access_token)
    localStorage.setItem(REFRESH_TOKEN_KEY, res.refresh_token)
    _saveUser(res.user)
    return res.user
  }

  async function register(username: string, password: string, email?: string, inviteCode?: string): Promise<UserInfo> {
    const body: Record<string, any> = { username, password }
    if (email) body.email = email
    if (inviteCode) body.invite_code = inviteCode
    const res = await request<{ access_token: string; refresh_token: string; user: UserInfo }>('/api/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(REFRESH_TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
    token.value = null
    currentUser.value = null
    token.value = res.access_token
    localStorage.setItem(TOKEN_KEY, res.access_token)
    localStorage.setItem(REFRESH_TOKEN_KEY, res.refresh_token)
    _saveUser(res.user)
    return res.user
  }

  async function sendSmsCode(phone: string): Promise<void> {
    await request('/api/auth/send-sms-code', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ phone }),
    })
  }

  async function registerByPhone(phone: string, code: string, password: string, inviteCode?: string): Promise<UserInfo> {
    const body: Record<string, any> = { phone, code, password }
    if (inviteCode) body.invite_code = inviteCode
    const res = await request<{ access_token: string; refresh_token: string; user: UserInfo }>('/api/auth/register-by-phone', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(REFRESH_TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
    token.value = null
    currentUser.value = null
    token.value = res.access_token
    localStorage.setItem(TOKEN_KEY, res.access_token)
    localStorage.setItem(REFRESH_TOKEN_KEY, res.refresh_token)
    _saveUser(res.user)
    return res.user
  }

  async function bindPhone(phone: string, code: string): Promise<UserInfo> {
    const user = await request<UserInfo>('/api/auth/bind-phone', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ..._authHeaders() },
      body: JSON.stringify({ phone, code }),
    })
    _saveUser(user)
    return user
  }

  function logout() {
    token.value = null
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(REFRESH_TOKEN_KEY)
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
    isSvip,
    roleLabel,
    zsBalance,
    vipExpiresAt,
    isVipEffective,
    isMember,
    userDiscount,
    userQueuePriority,
    login,
    loginByPhone,
    register,
    sendSmsCode,
    registerByPhone,
    bindPhone,
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