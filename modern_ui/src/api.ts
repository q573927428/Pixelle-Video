const BASE = ''

export async function request<T = any>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(BASE + url, options)
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

export async function loadTasks(limit = 30) {
  return request<any[]>(`/api/tasks?limit=${limit}`)
}

export async function loadTaskHistory(page = 1, pageSize = 20, status?: string) {
  const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) })
  if (status) params.set('status', status)
  return request<{ tasks: any[]; total: number; page: number; page_size: number; total_pages: number }>(`/api/tasks/history?${params}`)
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
  if (outputIndex >= 0) return `/api/files/${normalized.slice(outputIndex)}`
  if (uploadIndex >= 0) return `/api/files/${normalized.slice(uploadIndex)}`
  if (apiResultIndex >= 0) return `/api/files/${normalized.slice(apiResultIndex)}`
  return `/api/files/${encodeURIComponent(normalized)}`
}

export function makePreviewUrl(rec: { url?: string; relative_path?: string; path?: string }): string {
  if (rec.url) return rec.url
  if (rec.relative_path) return `/api/files/${rec.relative_path}`
  const parts = (rec.path || '').replace(/\\\\/g, '/').replace(/\\/g, '/').split('/')
  const idx = parts.indexOf('temp')
  if (idx >= 0) return '/api/files/' + parts.slice(idx).join('/')
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

// ====== Config API ======

export interface LLMConfig {
  api_key: string
  base_url: string
  model: string
}

export interface ComfyUIConfig {
  comfyui_url: string
  comfyui_api_key: string
  runninghub_api_key: string
  runninghub_concurrent_limit: number
  runninghub_instance_type: string
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
