<template>
  <div class="tool-page">
    <div class="page-header">
      <span class="page-icon">📝</span>
      <div>
        <h3 class="page-title">历史记录</h3>
        <p class="page-desc">所有已完成任务的保存90天，超时自动删除，请及时下载到本地</p>
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
            <div class="history-item-title-row">
              <div class="history-item-title">{{ task.title || '未命名任务' }}</div>
              <span v-if="isAdmin && (task.username || task.phone)" class="user-badge">
                <el-icon><User /></el-icon>
                {{ task.phone || task.username }}
              </span>
              <span v-if="task.deducted_zs > 0" class="zs-badge" title="实际扣除ZS币">
                ZS -{{ task.deducted_zs }}
              </span>
            </div>
            <div class="history-item-meta">
              <span class="small muted stats-label">{{ formatTime(task.created_at) }}</span>
              <span class="meta-actions">
                <el-tooltip content="复制文案" placement="top" :show-after="300">
                  <el-button
                    text
                    size="small"
                    type="warning"
                    class="action-btn"
                    @click.stop="handleCopyPrompt(task)"
                  >
                    <el-icon><CopyDocument /></el-icon>
                  </el-button>
                </el-tooltip>
                <el-tooltip content="下载视频" placement="top" :show-after="300">
                  <el-button
                    text
                    size="small"
                    type="primary"
                    class="action-btn"
                    @click.stop="handleDownload(task)"
                  >
                    <el-icon><Download /></el-icon>
                  </el-button>
                </el-tooltip>
                <el-tooltip content="删除此记录" placement="top" :show-after="300">
                  <el-button
                    text
                    size="small"
                    type="danger"
                    class="action-btn"
                    @click.stop="handleDelete(task)"
                  >
                    <el-icon><Delete /></el-icon>
                  </el-button>
                </el-tooltip>
                <el-tooltip content="复制文案" placement="top" :show-after="300">
                  <el-button
                    size="small"
                    type="warning"
                    class="action-btn"
                    @click.stop="openVideoEditor(task)"
                  >
                  <el-icon><Edit /></el-icon>编辑视频
                  </el-button>
                </el-tooltip>
              </span>
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
    <el-dialog v-model="detailVisible" title="任务详情" :close-on-click-modal="false" top="5vh" class="detail-dialog">
      <div v-if="detailLoading" style="text-align:center;padding:30px;">
        <el-icon class="is-loading" style="font-size:24px;"><Loading /></el-icon>
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

    <!-- 视频后处理编辑弹窗 -->
    <el-dialog v-model="editVideoDialogVisible" title="🎬 视频后处理编辑" :close-on-click-modal="false" top="6vh" width="65%" class="video-edit-dialog" destroy-on-close>
      <VideoPostProcessEditor
        v-if="editTaskData"
        :task-video-url="editTaskVideoUrl"
        :task-video-path="editTaskVideoPath"
        :task-text="editTaskText"
        :task-id="editTaskData.task_id"
      />
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { loadTaskHistory, deleteTaskHistory, getTaskHistoryDetail } from '../api'
import { ElMessageBox } from 'element-plus'
import { Edit, User, CopyDocument, Download, Delete } from '@element-plus/icons-vue'
import { useAuth } from '../composables/useAuth'
import VideoPostProcessEditor from '../components/VideoPostProcessEditor.vue'

const { isAdmin } = useAuth()

const loading = ref(false)
const tasks = ref<any[]>([])
const currentPage = ref(1)
const pageSize = ref(10)
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

// Video post-process editor dialog
const editVideoDialogVisible = ref(false)
const editTaskData = ref<any>(null)
const editTaskVideoUrl = ref('')
const editTaskVideoPath = ref('')
const editTaskText = ref('')

async function openVideoEditor(task: any) {
  // 从列表中已有的字段提取文案
  let content = task.goods_text || ''
  if (!content && task.input) {
    let input: any = task.input
    if (typeof input === 'string') {
      try { input = JSON.parse(input) } catch { /* ignore */ }
    }
    content = input.goods_text || input.prompt || input.text || ''
  }
  // 如果列表数据没有文案，则调用详情接口获取完整 input
  if (!content && task.task_id) {
    try {
      const data = await getTaskHistoryDetail(task.task_id)
      const meta = data?.metadata || data
      const input = meta.input
      if (input) {
        let obj: any = input
        if (typeof obj === 'string') {
          try { obj = JSON.parse(obj) } catch { /* ignore */ }
        }
        content = obj.goods_text || obj.prompt || obj.text || ''
      }
    } catch { /* ignore */ }
  }
  editTaskData.value = task
  editTaskVideoPath.value = task.video_path || ''
  editTaskVideoUrl.value = task.video_path ? previewUrl(task.video_path) : ''
  editTaskText.value = content
  editVideoDialogVisible.value = true
}

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
    const data = await getTaskHistoryDetail(task.task_id)
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

async function handleCopyPrompt(task: any) {
  // 尝试从列表中已有的字段提取文案
  let content = task.goods_text || ''
  if (!content && task.input) {
    let input: any = task.input
    if (typeof input === 'string') {
      try { input = JSON.parse(input) } catch { /* ignore */ }
    }
    content = input.goods_text || input.prompt || input.text || ''
  }
  // 如果列表数据没有，则调用详情接口获取完整 input
  if (!content && task.task_id) {
    try {
      const data = await getTaskHistoryDetail(task.task_id)
      const meta = data?.metadata || data
      const input = meta.input
      if (input) {
        let obj: any = input
        if (typeof obj === 'string') {
          try { obj = JSON.parse(obj) } catch { /* ignore */ }
        }
        content = obj.goods_text || obj.prompt || obj.text || ''
      }
    } catch { /* ignore */ }
  }
  if (!content) {
    ElMessage.warning('该任务无可用文案')
    return
  }
  try {
    await navigator.clipboard.writeText(content)
    ElMessage.success('文案已复制到剪贴板')
  } catch {
    // Fallback
    const textarea = document.createElement('textarea')
    textarea.value = content
    textarea.style.position = 'fixed'
    textarea.style.left = '-9999px'
    document.body.appendChild(textarea)
    textarea.select()
    document.execCommand('copy')
    document.body.removeChild(textarea)
    ElMessage.success('文案已复制到剪贴板')
  }
}

async function handleDownload(task: any) {
  if (!task.video_path) {
    ElMessage.warning('该任务无可下载的视频')
    return
  }
  const url = previewUrl(task.video_path)
  const a = document.createElement('a')
  a.href = url
  a.download = task.title || `task_${task.task_id}`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
}

async function handleDelete(task: any) {
  if (!task.task_id) return
  try {
    await ElMessageBox.confirm(
      `确定要永久删除任务「${task.title || '未命名任务'}」？\n所有相关文件（视频、帧、元数据）将被清除。`,
      '删除确认',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning', confirmButtonClass: 'el-button--danger' }
    )
    await deleteTaskHistory(task.task_id)
    ElMessage.success('任务已删除')
    // Remove from local list without re-fetch for instant feedback
    tasks.value = tasks.value.filter((t: any) => t.task_id !== task.task_id)
    // Reload to update pagination and stats
    loadData()
  } catch (e: any) {
    if (e === 'cancel') return // User cancelled
    const msg = typeof e === 'string' ? e : e?.message || '删除失败'
    ElMessage.error(`删除失败：${msg}`)
  }
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
.user-badge {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 12px;
  color: var(--primary, #6366f1);
  background: rgba(99, 102, 241, 0.1);
  padding: 1px 8px;
  border-radius: 10px;
  white-space: nowrap;
}
.admin-hint {
  font-size: 12px;
  color: var(--muted);
  margin-left: auto;
  opacity: 0.7;
}
.zs-badge {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  font-size: 12px;
  font-weight: 700;
  color: #f59e0b;
  background: rgba(110, 110, 110, 0.301);
  padding: 1px 7px;
  border-radius: 10px;
  white-space: nowrap;
}
.zs-icon-img {
  width: 18px;
  height: 18px;
  vertical-align: middle;
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
.history-item-preview video:fullscreen,
.history-item-preview video:-webkit-full-screen {
  object-fit: contain !important;
  background: #000;
}
.detail-video:fullscreen,
.detail-video:-webkit-full-screen {
  object-fit: contain !important;
  background: #000;
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
  position: relative;
}
.history-item-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.history-item-title {
  font-weight: 700;
  font-size: 14px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
  min-width: 0;
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
  object-fit: contain;
  background: #000;
}

.history-item-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 4px;
}
.meta-actions {
  display: inline-flex;
  gap: 2px;
  align-items: center;
  margin-left: auto;
  flex-shrink: 0;
}
.action-btn {
  opacity: 0.5;
  transition: opacity 0.15s;
  padding: 4px 5px !important;
  min-width: unset !important;
  min-height: unset !important;
}
.history-item:hover .action-btn {
  opacity: 1;
}

.page-content {
  max-width: 100%;
  width: 100%;
}

/* ── 移动端适配 ── */
@media (max-width: 640px) {
  .history-item {
    padding: 10px;
  }
  .history-list {
    grid-template-columns: 1fr;
    gap: 10px;
  }
  .stats-row {
    grid-template-columns: repeat(2, 1fr);
    gap: 8px;
  }
  .stats-card {
    padding: 12px 10px;
  }
  .stats-value {
    font-size: 20px;
  }
  .meta-actions {
    margin-left: 0;
  }
  .action-btn {
    opacity: 1;
    font-size: 13px;
  }
}
</style>

<style>
/* 全局 dialog 宽度控制 */
.detail-dialog {
  width: 700px;
  max-width: 92vw;
}
.detail-dialog .el-dialog__body {
  padding: 16px;
  overflow-x: hidden;
}

/* 桌面端：固定宽度 700px */
@media (min-width: 641px) {
  .detail-dialog {
    width: 700px !important;
  }
}

/* 移动端：自适应宽度 */
@media (max-width: 640px) {
  .detail-dialog {
    width: 92vw !important;
    max-width: 92vw !important;
    min-width: 0 !important;
  }
  .detail-dialog .el-dialog__body {
    padding: 12px;
  }
}

/* 视频编辑弹窗：宽屏大弹窗 */
.video-edit-dialog {
  max-width: 95vw !important;
}
.video-edit-dialog .el-dialog__body {
  padding: 16px;
  padding-top: 8px;
  overflow-x: hidden;
}
@media (max-width: 1024px) {
  .video-edit-dialog {
    width: 100vw !important;
    max-width: 100vw !important;
  }
  .video-edit-dialog .el-dialog__body {
    padding: 12px;
  }
}
</style>