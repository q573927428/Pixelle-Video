<template>
  <div class="tool-page">
    <div class="page-header">
      <span class="page-icon">📋</span>
      <div>
        <h3 class="page-title">历史记录</h3>
        <p class="page-desc">所有已完成任务的持久化记录，重启服务器后依然保留</p>
      </div>
    </div>

    <div class="page-content">
      <!-- 统计卡片 -->
      <div class="stats-row">
        <div class="stats-card">
          <div class="stats-value">{{ stats.total_tasks }}</div>
          <div class="stats-label">总任务数</div>
        </div>
        <div class="stats-card success">
          <div class="stats-value">{{ stats.completed }}</div>
          <div class="stats-label">已完成</div>
        </div>
        <div class="stats-card danger">
          <div class="stats-value">{{ stats.failed }}</div>
          <div class="stats-label">已失败</div>
        </div>
        <div class="stats-card">
          <div class="stats-value">{{ formatDuration(stats.total_duration) }}</div>
          <div class="stats-label">总时长</div>
        </div>
      </div>

      <!-- 筛选和刷新 -->
      <div class="history-toolbar">
        <el-select v-model="filterStatus" placeholder="筛选状态" clearable style="width:140px;" @change="loadData">
          <el-option label="全部" value="" />
          <el-option label="已完成" value="completed" />
          <el-option label="失败" value="failed" />
        </el-select>
        <el-button @click="loadData" :loading="loading">刷新</el-button>
      </div>

      <!-- 任务列表 -->
      <div v-if="!loading && !tasks.length" class="empty-preview">
        <div><div style="font-size:38px;margin-bottom:10px;">📂</div><div>暂无历史任务记录</div></div>
      </div>

      <div v-loading="loading" class="history-list">
        <div v-for="task in tasks" :key="task.task_id" class="history-item" @click="showDetail(task)">
          <div class="history-item-preview" @click.stop>
            <video
              v-if="task.video_path"
              :src="previewUrl(task.video_path)"
              muted
              controls
              playsinline
              preload="metadata"
            />
            <div v-else class="history-item-placeholder">🎬</div>
            <span v-if="task.duration" class="duration-badge">{{ task.duration.toFixed(1) }}s</span>
          </div>
          <div class="history-item-info">
            <div class="history-item-title">{{ task.title || '未命名任务' }}</div>
            <div class="history-item-meta">
              <el-tag :type="task.status === 'completed' ? 'success' : 'danger'" effect="dark" size="small">
                {{ task.status === 'completed' ? '已完成' : '失败' }}
              </el-tag>
              <span class="small muted">{{ formatTime(task.created_at) }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 分页 -->
      <div v-if="totalPages > 1" class="pagination-wrap">
        <el-pagination
          v-model:current-page="currentPage"
          :page-size="pageSize"
          :total="total"
          layout="prev, pager, next"
          @current-change="onPageChange"
        />
      </div>
    </div>

    <!-- 详情对话框 -->
    <el-dialog v-model="detailVisible" title="任务详情" width="700px" :close-on-click-modal="false" top="5vh">
      <div v-if="detailLoading" style="text-align:center;padding:30px;">
        <el-icon class="is-loading" style="font-size:24px;"><svg viewBox="0 0 1024 1024"><path fill="currentColor" d="M512 64a32 32 0 0 1 32 32v192a32 32 0 0 1-64 0V96a32 32 0 0 1 32-32z"/><path fill="currentColor" d="M512 736a32 32 0 0 1 32 32v192a32 32 0 0 1-64 0V768a32 32 0 0 1 32-32z"/></svg></el-icon>
        <div class="small muted" style="margin-top:12px;">加载中...</div>
      </div>
      <template v-else-if="detailData">
        <div class="detail-section">
          <div class="detail-label">任务 ID</div>
          <div class="detail-value mono">{{ detailData.metadata.task_id }}</div>
        </div>
        <div class="detail-section">
          <div class="detail-label">状态</div>
          <div class="detail-value">
            <el-tag :type="detailData.metadata.status === 'completed' ? 'success' : 'danger'" effect="dark">
              {{ detailData.metadata.status === 'completed' ? '已完成' : '失败' }}
            </el-tag>
          </div>
        </div>
        <div class="detail-section">
          <div class="detail-label">创建时间</div>
          <div class="detail-value">{{ detailData.metadata.created_at }}</div>
        </div>
        <div class="detail-section" v-if="detailData.metadata.completed_at">
          <div class="detail-label">完成时间</div>
          <div class="detail-value">{{ detailData.metadata.completed_at }}</div>
        </div>
        <div class="detail-section" v-if="detailData.metadata.result?.duration">
          <div class="detail-label">视频时长</div>
          <div class="detail-value">{{ detailData.metadata.result.duration.toFixed(1) }} 秒</div>
        </div>
        <div class="detail-section" v-if="detailData.metadata.result?.file_size">
          <div class="detail-label">文件大小</div>
          <div class="detail-value">{{ formatSize(detailData.metadata.result.file_size) }}</div>
        </div>
        <div class="detail-section" v-if="detailData.metadata.input">
          <div class="detail-label">输入参数</div>
          <pre class="detail-json">{{ JSON.stringify(detailData.metadata.input, null, 2) }}</pre>
        </div>
        <div class="detail-section" v-if="detailData.metadata.error">
          <div class="detail-label">错误信息</div>
          <div class="detail-value" style="color:var(--danger);">{{ detailData.metadata.error }}</div>
        </div>
        <div class="detail-section" v-if="detailData.metadata.result?.video_path">
          <div class="detail-label">视频预览</div>
          <video class="detail-video" controls :src="previewUrl(detailData.metadata.result.video_path)" />
        </div>
      </template>
      <div v-else class="empty-preview">未找到任务详情</div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { loadTaskHistory } from '../api'

const loading = ref(false)
const tasks = ref<any[]>([])
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)
const totalPages = ref(0)
const filterStatus = ref('')

const stats = ref({
  total_tasks: 0,
  completed: 0,
  failed: 0,
  total_duration: 0,
  total_size: 0,
})

// Detail dialog
const detailVisible = ref(false)
const detailLoading = ref(false)
const detailData = ref<any>(null)

onMounted(() => {
  loadData()
})

async function loadData() {
  loading.value = true
  try {
    const result = await loadTaskHistory(currentPage.value, pageSize.value, filterStatus.value || undefined)
    tasks.value = result.tasks || []
    total.value = result.total || 0
    totalPages.value = result.total_pages || 0

    // Extract stats from response
    if (result.tasks) {
      stats.value = {
        total_tasks: result.total || result.tasks.length,
        completed: result.tasks.filter((t: any) => t.status === 'completed').length,
        failed: result.tasks.filter((t: any) => t.status === 'failed').length,
        total_duration: result.tasks.reduce((sum: number, t: any) => sum + (t.duration || 0), 0),
        total_size: 0,
      }
    }
  } catch (e: any) {
    const msg = typeof e === 'string' ? e : e?.message || '请求失败'
    ElMessage.error(`加载历史记录失败：${msg}`)
    tasks.value = []
  } finally {
    loading.value = false
  }
}

function onPageChange(page: number) {
  currentPage.value = page
  loadData()
}

async function showDetail(task: any) {
  if (!task.task_id) return
  detailVisible.value = true
  detailLoading.value = true
  detailData.value = null
  try {
    const response = await fetch(`/api/tasks/history/${task.task_id}`)
    if (!response.ok) {
      const text = await response.text()
      let detail: any
      try { detail = JSON.parse(text) } catch { detail = { detail: text } }
      throw new Error(detail.detail || response.statusText)
    }
    const data = await response.json()
    detailData.value = data
  } catch (e: any) {
    const msg = typeof e === 'string' ? e : e?.message || '请求失败'
    ElMessage.error(`加载详情失败：${msg}`)
  } finally {
    detailLoading.value = false
  }
}

function previewUrl(path: string): string {
  if (!path) return ''
  const normalized = path.replace(/\\\\/g, '/').replace(/\\/g, '/')
  const idx = normalized.indexOf('output/')
  if (idx >= 0) return `/api/files/${normalized.slice(idx)}`
  return `/api/files/${encodeURIComponent(normalized)}`
}

function formatTime(iso: string) {
  if (!iso) return ''
  try {
    const d = new Date(iso)
    return d.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
  } catch {
    return iso
  }
}

function formatDuration(seconds: number): string {
  if (!seconds) return '0s'
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = Math.floor(seconds % 60)
  if (h > 0) return `${h}h ${m}m`
  if (m > 0) return `${m}m ${s}s`
  return `${s}s`
}

function formatSize(bytes: number): string {
  if (!bytes) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  let i = 0
  let size = bytes
  while (size >= 1024 && i < units.length - 1) {
    size /= 1024
    i++
  }
  return `${size.toFixed(1)} ${units[i]}`
}

function playHover(e: Event) {
  const video = (e.currentTarget as HTMLElement).querySelector('video')
  if (video) video.play().catch(() => {})
}

function stopHover(e: Event) {
  const video = (e.currentTarget as HTMLElement).querySelector('video')
  if (video) { video.pause(); video.currentTime = 0 }
}
</script>

<style scoped>
.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}
.stats-card {
  background: rgba(2, 6, 23, 0.4);
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 18px 16px;
  text-align: center;
}
.stats-card.success { border-color: rgba(52, 199, 89, 0.4); }
.stats-card.danger { border-color: rgba(255, 69, 58, 0.4); }
.stats-value {
  font-size: 24px;
  font-weight: 800;
  margin-bottom: 4px;
}
.stats-label {
  font-size: 12px;
  color: var(--muted);
}

.history-toolbar {
  display: flex;
  gap: 10px;
  margin-bottom: 14px;
  align-items: center;
}

.history-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 14px;
}
.history-item {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 12px;
  border: 1px solid var(--line);
  border-radius: 14px;
  background: rgba(2, 6, 23, 0.28);
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s, transform 0.15s;
}
.history-item:hover {
  background: rgba(30, 41, 59, 0.5);
  border-color: rgba(99, 102, 241, 0.4);
  transform: translateY(-2px);
}
.history-item-preview {
  position: relative;
  width: 100%;
  aspect-ratio: 9 / 16;
  flex-shrink: 0;
  border-radius: 10px;
  overflow: hidden;
  background: rgba(15, 23, 42, 0.5);
  display: grid;
  place-items: center;
}
.history-item-preview video {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.history-item-placeholder {
  font-size: 42px;
}
.duration-badge {
  position: absolute;
  bottom: 6px;
  right: 6px;
  background: rgba(0, 0, 0, 0.75);
  color: #fff;
  font-size: 12px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 6px;
  backdrop-filter: blur(4px);
  letter-spacing: 0.3px;
}
.history-item-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.history-item-title {
  font-weight: 700;
  font-size: 14px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.history-item-meta {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
}

.pagination-wrap {
  display: flex;
  justify-content: center;
  margin-top: 20px;
}

/* Detail dialog */
.detail-section {
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--line);
}
.detail-label {
  font-size: 12px;
  color: var(--muted);
  margin-bottom: 4px;
}
.detail-value {
  font-size: 14px;
  font-weight: 600;
}
.detail-json {
  background: rgba(15, 23, 42, 0.6);
  border-radius: 10px;
  padding: 12px;
  font-size: 12px;
  max-height: 300px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-all;
}
.detail-video {
  width: 100%;
  max-height: 400px;
  border-radius: 10px;
}

.page-content {
  max-width: 100%;
  width: 100%;
}
</style>