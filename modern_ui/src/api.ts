const BASE = ''

// 防止多个请求同时刷新令牌
let isRefreshing = false
let refreshPromise: Promise<any> | null = null

// 刷新令牌
async function refreshToken(): Promise<any> {
  if (isRefreshing) {
    return refreshPromise
  }
  
  isRefreshing = true
  refreshPromise = (async () => {
    try {
      const refreshToken = localStorage.getItem('pixelle_refresh_token')
      if (!refreshToken) {
        throw new Error('No refresh token')
      }
      
      const response = await fetch(BASE + '/api/auth/refresh-token', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ refresh_token: refreshToken }),
      })
      
      if (!response.ok) {
        throw new Error('Refresh token failed')
      }
      
      const data = await response.json()
      localStorage.setItem('pixelle_auth_token', data.access_token)
      localStorage.setItem('pixelle_refresh_token', data.refresh_token)
      return data
    } catch (e) {
      // 刷新失败，清除token并回到首页（状态驱动显示登录页）
      localStorage.removeItem('pixelle_auth_token')
      localStorage.removeItem('pixelle_refresh_token')
      window.location.href = '/'
      throw e
    } finally {
      isRefreshing = false
      refreshPromise = null
    }
  })()
  
  return refreshPromise
}

export async function request<T = any>(url: string, options?: RequestInit, isRetry = false): Promise<T> {
  // 自动注入 Authorization header
  const headers: Record<string, string> = {
    ...(options?.headers as Record<string, string>),
    ..._getAuthHeaders(),
  }
  const response = await fetch(BASE + url, { ...options, headers })
  
  // 处理401未授权
  if (response.status === 401 && !isRetry && url !== '/api/auth/login' && url !== '/api/auth/register' && url !== '/api/auth/login-by-phone' && url !== '/api/auth/refresh-token') {
    try {
      await refreshToken()
      // 刷新成功后重试原请求
      return request(url, options, true)
    } catch (e) {
      // 刷新失败，抛出错误
      let detail = '登录已过期，请重新登录'
      try {
        const data = await response.json()
        detail = data.detail || data.message || detail
      } catch (_) {}
      throw new Error(detail)
    }
  }
  
  if (!response.ok) {
    let detail = response.statusText
    try {
      const data = await response.json()
      detail = data.detail || data.message || JSON.stringify(data)
    } catch (_) {}
    throw new Error(detail)
  }
  return response.json()
}

export async function uploadFile(rawFile: File, category: string) {
  const formData = new FormData()
  formData.append('file', rawFile)
  formData.append('category', category)
  return request('/api/files/upload', { method: 'POST', body: formData })
}

export async function loadResources() {
  const [templates, media, tts, bgm, voices] = await Promise.all([
    request<{ templates: any[] }>('/api/resources/templates'),
    request<{ workflows: any[] }>('/api/resources/workflows/media'),
    request<{ workflows: any[] }>('/api/resources/workflows/tts'),
    request<{ bgm_files: any[] }>('/api/resources/bgm'),
    request<{ voices: any[] }>('/api/resources/tts-voices').catch(() => ({ voices: [] })),
  ])
  return {
    templates: templates.templates || [],
    mediaWorkflows: media.workflows || [],
    ttsWorkflows: tts.workflows || [],
    bgmFiles: bgm.bgm_files || [],
    ttsVoices: voices.voices || [],
  }
}

export async function loadTasks(limit = 30, status?: string) {
  const params = new URLSearchParams({ limit: String(limit) })
  if (status) params.set('status', status)
  return request<any[]>(`/api/tasks?${params}`)
}

export async function loadTaskHistory(page = 1, pageSize = 20, status?: string) {
  const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) })
  if (status) params.set('status', status)
  return request<{ tasks: any[]; total: number; page: number; page_size: number; total_pages: number }>(`/api/tasks/history?${params}`)
}

export async function getTaskHistoryDetail(taskId: string) {
  return request<any>(`/api/tasks/history/${encodeURIComponent(taskId)}`)
}

export async function cancelTask(taskId: string): Promise<{ success: boolean; message: string }> {
  return request(`/api/tasks/${encodeURIComponent(taskId)}`, { method: 'DELETE' })
}

export async function deleteTaskHistory(taskId: string): Promise<{ success: boolean; message: string }> {
  return request(`/api/tasks/history/${encodeURIComponent(taskId)}`, { method: 'DELETE' })
}

export async function checkHealth() {
  try {
    await request('/health')
    return true
  } catch {
    return false
  }
}

export function filePreviewUrl(path: string): string {
  if (!path) return ''
  // 兼容 Windows 双反斜杠和单反斜杠路径，全部转为正斜杠
  const normalized = path.replace(/\\\\/g, '/').replace(/\\/g, '/')
  const outputIndex = normalized.indexOf('output/')
  const uploadIndex = normalized.indexOf('temp/uploads/')
  const apiResultIndex = normalized.indexOf('pixelle_video/services/code/result/')
  if (outputIndex >= 0) return `/api/files/${_encodePath(normalized.slice(outputIndex))}`
  if (uploadIndex >= 0) return `/api/files/${_encodePath(normalized.slice(uploadIndex))}`
  if (apiResultIndex >= 0) return `/api/files/${_encodePath(normalized.slice(apiResultIndex))}`
  return `/api/files/${encodeURIComponent(normalized)}`
}

/** 对路径中每一段做 URL 编码（兼容中文文件名） */
function _encodePath(p: string): string {
  return p.split('/').map(seg => encodeURIComponent(seg)).join('/')
}

export function makePreviewUrl(rec: { url?: string; relative_path?: string; path?: string }): string {
  if (rec.url) return rec.url
  if (rec.relative_path) return `/api/files/${_encodePath(rec.relative_path)}`
  const parts = (rec.path || '').replace(/\\\\/g, '/').replace(/\\/g, '/').split('/')
  const idx = parts.indexOf('temp')
  if (idx >= 0) return '/api/files/' + parts.slice(idx).map(seg => encodeURIComponent(seg)).join('/')
  return filePreviewUrl(rec.path || '')
}

export function saveToLocalHistory(data: any, category: string) {
  try {
    const key = 'pixelle_upload_history'
    let history: any[] = JSON.parse(localStorage.getItem(key) || '[]')
    const record = {
      id: data.stored_name || Date.now().toString(),
      category: category || data.category || 'misc',
      name: data.filename || 'unknown',
      path: data.path,
      url: data.url || '',
    }
    history.unshift(record)
    if (history.length > 100) history = history.slice(0, 100)
    localStorage.setItem(key, JSON.stringify(history))
  } catch (_) {}
}

export function loadLocalHistory(): any[] {
  try {
    const key = 'pixelle_upload_history'
    return JSON.parse(localStorage.getItem(key) || '[]')
  } catch (_) {
    return []
  }
}

export function deleteFromLocalHistory(id: string): any[] {
  try {
    const key = 'pixelle_upload_history'
    let history: any[] = JSON.parse(localStorage.getItem(key) || '[]')
    history = history.filter((r: any) => r.id !== id)
    localStorage.setItem(key, JSON.stringify(history))
    return history
  } catch (_) {
    return []
  }
}

// ====== User File API (per-user isolation) ======

export async function getUserUploads(category = ''): Promise<{ success: boolean; records: any[] }> {
  const params = category ? `?category=${encodeURIComponent(category)}` : ''
  return request(`/api/files/user/list${params}`)
}

export async function getUserStorageUsage(): Promise<{
  success: boolean
  used_bytes: number
  limit_bytes: number
  used_display: string
  limit_display: string
  is_unlimited: boolean
  usage_percent: number
}> {
  return request('/api/files/user/usage')
}

export async function deleteUserUpload(fileId: number): Promise<{ success: boolean; message: string }> {
  return request(`/api/files/user/delete/${fileId}`, { method: 'DELETE' })
}

// ====== Config API ======

export interface LLMConfig {
  api_key: string
  base_url: string
  model: string
}

export interface RemoteComfyConfig {
  enabled: boolean
  base_url: string
  image_workflow_id: string
  video_workflow_id: string
  customize_workflow_id: string
  tts_workflow_id: string
}

export interface ComfyUIConfig {
  comfyui_url: string
  comfyui_api_key: string
  runninghub_api_key: string
  runninghub_concurrent_limit: number
  runninghub_instance_type: string
  autodl_api_key: string
  remote_comfy: RemoteComfyConfig
}

export interface FullConfig {
  llm: LLMConfig
  comfyui: ComfyUIConfig
  api_providers: Record<string, any>
  presets: string[]
}

function _getAuthHeaders(): Record<string, string> {
  try {
    const token = localStorage.getItem('pixelle_auth_token')
    return token ? { Authorization: `Bearer ${token}` } : {}
  } catch {
    return {}
  }
}

export async function getConfig(): Promise<FullConfig> {
  return request<FullConfig>('/api/config', {
    headers: _getAuthHeaders(),
  })
}

export async function saveConfig(config: {
  llm: LLMConfig
  comfyui: ComfyUIConfig
  api_providers: Record<string, any>
}): Promise<{ success: boolean; message: string }> {
  return request('/api/config', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', ..._getAuthHeaders() },
    body: JSON.stringify(config),
  })
}

export async function loadLLMModels(apiKey: string, baseUrl: string): Promise<string[]> {
  const res = await request<{ models: string[] }>('/api/config/llm/load-models', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ..._getAuthHeaders() },
    body: JSON.stringify({ api_key: apiKey, base_url: baseUrl }),
  })
  return res.models
}

export async function testLLMConnection(apiKey: string, baseUrl: string): Promise<{ success: boolean; message: string; model_count: number }> {
  return request('/api/config/llm/test-connection', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ..._getAuthHeaders() },
    body: JSON.stringify({ api_key: apiKey, base_url: baseUrl }),
  })
}

export async function testComfyUIConnection(url: string): Promise<boolean> {
  try {
    const res = await fetch(`${url}/system_stats`, { method: 'GET', signal: AbortSignal.timeout(5000) })
    return res.status === 200
  } catch {
    return false
  }
}

// ====== Remote ComfyUI (zealman mirror) API ======

export async function testRemoteComfyConnection(baseUrl: string): Promise<{ success: boolean; message: string }> {
  return request('/api/config/remote-comfy/test', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ..._getAuthHeaders() },
    body: JSON.stringify({ base_url: baseUrl }),
  })
}

export async function listRemoteWorkflows(baseUrl: string): Promise<{ success: boolean; workflows: any[]; message: string }> {
  return request('/api/config/remote-comfy/list-workflows', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ..._getAuthHeaders() },
    body: JSON.stringify({ base_url: baseUrl }),
  })
}

export async function resetConfig(): Promise<{ success: boolean; message: string }> {
  return request('/api/config/reset', {
    method: 'POST',
    headers: _getAuthHeaders(),
  })
}

export async function detectPreset(): Promise<string> {
  const res = await request<{ preset: string }>('/api/config/llm/detect-preset', {
    headers: _getAuthHeaders(),
  })
  return res.preset
}

export async function getPresetConfig(name: string): Promise<Record<string, any>> {
  return request(`/api/config/preset/${encodeURIComponent(name)}`, {
    headers: _getAuthHeaders(),
  })
}

// ====== Instance Management API (AutoDL 实例管理) ======

export async function listInstances(token: string, pageIndex = 1, pageSize = 50) {
  return request('/api/instances/list', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ..._getAuthHeaders() },
    body: JSON.stringify({ token, page_index: pageIndex, page_size: pageSize }),
  })
}

export async function getInstanceStatus(token: string, instanceUuid: string) {
  return request('/api/instances/status', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ..._getAuthHeaders() },
    body: JSON.stringify({ token, instance_uuid: instanceUuid }),
  })
}

export async function getInstanceSnapshot(token: string, instanceUuid: string) {
  return request(`/api/instances/snapshot?token=${encodeURIComponent(token)}&instance_uuid=${encodeURIComponent(instanceUuid)}`, {
    headers: _getAuthHeaders(),
  })
}

export async function powerOnInstance(token: string, instanceUuid: string) {
  return request('/api/instances/power-on', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ..._getAuthHeaders() },
    body: JSON.stringify({ token, instance_uuid: instanceUuid }),
  })
}

export async function powerOffInstance(token: string, instanceUuid: string) {
  return request('/api/instances/power-off', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ..._getAuthHeaders() },
    body: JSON.stringify({ token, instance_uuid: instanceUuid }),
  })
}

export async function releaseInstance(token: string, instanceUuid: string) {
  return request('/api/instances/release', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ..._getAuthHeaders() },
    body: JSON.stringify({ token, instance_uuid: instanceUuid }),
  })
}

export async function createInstance(token: string, gpuSpecUuid: string, instanceName = '并发生成-镜像机', reqGpuAmount = 1) {
  return request('/api/instances/create', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ..._getAuthHeaders() },
    body: JSON.stringify({ token, gpu_spec_uuid: gpuSpecUuid, instance_name: instanceName, req_gpu_amount: reqGpuAmount }),
  })
}

// ====== Mirror ComfyUI Control API ======

export async function mirrorStartComfyui(mirrorUrl: string) {
  return request('/api/instances/mirror/start', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ..._getAuthHeaders() },
    body: JSON.stringify({ mirror_url: mirrorUrl }),
  })
}

export async function mirrorStopComfyui(mirrorUrl: string) {
  return request('/api/instances/mirror/stop', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ..._getAuthHeaders() },
    body: JSON.stringify({ mirror_url: mirrorUrl }),
  })
}

export async function mirrorComfyStatus(mirrorUrl: string) {
  return request(`/api/instances/mirror/comfy-status?mirror_url=${encodeURIComponent(mirrorUrl)}`, {
    headers: _getAuthHeaders(),
  })
}

export async function mirrorInterrupt(mirrorUrl: string) {
  return request('/api/instances/mirror/interrupt', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ..._getAuthHeaders() },
    body: JSON.stringify({ mirror_url: mirrorUrl }),
  })
}

export async function mirrorFreeMemory(mirrorUrl: string) {
  return request('/api/instances/mirror/free', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ..._getAuthHeaders() },
    body: JSON.stringify({ mirror_url: mirrorUrl }),
  })
}

export async function mirrorVersions(mirrorUrl: string) {
  return request(`/api/instances/mirror/versions?mirror_url=${encodeURIComponent(mirrorUrl)}`, {
    headers: _getAuthHeaders(),
  })
}

export async function mirrorSwitchVersion(mirrorUrl: string, version: string) {
  return request('/api/instances/mirror/switch-version', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ..._getAuthHeaders() },
    body: JSON.stringify({ mirror_url: mirrorUrl, version }),
  })
}

export async function mirrorProbe(mirrorUrl: string) {
  return request(`/api/instances/mirror/probe?mirror_url=${encodeURIComponent(mirrorUrl)}`, {
    headers: _getAuthHeaders(),
  })
}

// ====== Auto-Scaling API (自动扩缩容) ======

export async function startAutoScaling(idleShutdownMinutes = 10, idleReleaseDays = 7, token = '') {
  return request('/api/instances/auto-scaling/start', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ..._getAuthHeaders() },
    body: JSON.stringify({ idle_shutdown_minutes: idleShutdownMinutes, idle_release_days: idleReleaseDays, token }),
  })
}

export async function stopAutoScaling() {
  return request('/api/instances/auto-scaling/stop', {
    method: 'POST',
    headers: _getAuthHeaders(),
  })
}

export async function getAutoScalingStatus() {
  return request('/api/instances/auto-scaling/status', {
    headers: _getAuthHeaders(),
  })
}

export async function ensureReadyInstance(token = '') {
  const params = token ? `?token=${encodeURIComponent(token)}` : ''
  return request(`/api/instances/auto-scaling/ensure-ready${params}`, {
    method: 'POST',
    headers: _getAuthHeaders(),
  })
}

// ====== Content Generation API (标题/话题生成) ======

export async function generateTitle(text: string, style?: string): Promise<{ success: boolean; title: string }> {
  return request('/api/content/title', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, style }),
  })
}

export async function generateTopics(text: string, count = 5): Promise<{ success: boolean; topics: string[] }> {
  return request('/api/content/topics', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, count }),
  })
}

export async function generatePublishPrepare(text: string): Promise<{ success: boolean; title: string; topics: string[] }> {
  return request('/api/content/publish-prepare', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
  })
}

// ====== Publishing API (短视频平台自动发布) ======

export interface PublishStartRequest {
  platform: string
  video_path: string
  title: string
  text: string
  topics: string[]
  portrait_cover?: string
  landscape_cover?: string
}

export interface PublishStartResponse {
  success: boolean
  session_id: string
  status: string
  message: string
}

export async function startPublish(data: PublishStartRequest): Promise<PublishStartResponse> {
  return request('/api/publish/start', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
}

export interface PublishStatusResponse {
  success: boolean
  session_id: string
  status: string
  current_step: string
  progress: number
  message: string
  platform_url: string
  error: string
  pending_qrcode?: string
}

export async function getPublishStatus(sessionId: string): Promise<PublishStatusResponse> {
  return request(`/api/publish/status/${encodeURIComponent(sessionId)}`)
}

export interface AccountInfo {
  id: number
  platform: string
  account_name: string
  status: string
  last_used_at: string | null
  expires_at: string | null
}

export async function listPublishAccounts(): Promise<{ success: boolean; accounts: AccountInfo[] }> {
  return request('/api/publish/accounts')
}

export async function deletePublishAccount(accountId: number): Promise<{ success: boolean; message: string }> {
  return request(`/api/publish/account/${accountId}`, { method: 'DELETE' })
}

export interface PublishLoginRequest {
  platform: string
}

export interface PublishLoginResponse {
  success: boolean
  session_id: string
  status: string
  message: string
}

export async function startPublishLogin(data: PublishLoginRequest): Promise<PublishLoginResponse> {
  return request('/api/publish/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
}

export async function savePublishCookie(data: {
  platform: string
  cookies: any[]
  account_name: string
  expires_at?: string
}): Promise<{ success: boolean; message: string }> {
  return request('/api/publish/cookie', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
}

/**
 * 创建 WebSocket 连接以接收发布实时状态
 */
export function createPublishWS(sessionId: string): WebSocket {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const wsUrl = `${protocol}//${window.location.host}/api/publish/ws/${encodeURIComponent(sessionId)}`
  return new WebSocket(wsUrl)
}
