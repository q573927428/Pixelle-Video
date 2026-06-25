<template>
  <section>
    <div class="card">
      <div class="card-header">
        <h3 class="card-title">📊 任务中心</h3>
        <div class="card-header-tools">
          <el-select v-model="filterStatus" placeholder="状态筛选" size="small" clearable @change="onFilterChange" style="width:110px;margin-right:8px">
            <el-option label="全部" value="" />
            <el-option label="待处理" value="pending" />
            <el-option label="进行中" value="running" />
            <el-option label="待确认" value="pending_confirmation" />
            <el-option label="已完成" value="completed" />
            <el-option label="失败" value="failed" />
            <el-option label="已取消" value="cancelled" />
          </el-select>
          <el-button @click="loadTasks" :disabled="loadingTasks" :loading="loadingTasks">刷新</el-button>
        </div>
      </div>
      <div class="card-body task-center-grid">
        <div v-if="!pagedTasks.length" class="empty-preview">暂无任务</div>
        <div v-for="task in pagedTasks" :key="task.task_id" class="task-card">
          <div class="task-card-header">
            <span class="task-card-id mono">{{ shortId(task.task_id) }}</span>
            <div class="task-card-header-actions">
              <span v-if="taskElapsedTimes[task.task_id]" style="font-weight:500;font-size:12px;margin-right:8px;white-space:nowrap;" :style="{ color: task.status === 'running' ? 'var(--el-color-warning)' : 'var(--el-color-success)' }">⏱ {{ taskElapsedTimes[task.task_id] }}</span>
              <el-tag :type="tagType(task.status)" effect="dark" size="small">{{ statusLabel(task.status) }}</el-tag>
              <el-button
                v-if="canCancel(task.status)"
                size="small"
                type="danger"
                text
                :loading="cancellingId === task.task_id"
                @click="handleCancelTask(task.task_id)"
              >取消</el-button>
              <el-button
                v-if="!canCancel(task.status)"
                size="small"
                type="danger"
                text
                :loading="deletingId === task.task_id"
                @click="handleDeleteTask(task.task_id)"
              >
              <el-icon><svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg></el-icon>
              </el-button>
            </div>
          </div>

          <!-- 左图右文布局 -->
          <div class="task-card-main">
            <!-- 左侧：预览图 -->
            <div class="task-card-thumbs" v-if="hasPreviews(task)">
              <div class="task-thumb" v-if="getCharacterImage(task)" :style="{ backgroundImage: `url(${getCharacterImage(task)})` }">
                <span class="thumb-label">角色</span>
              </div>
              <div class="task-thumb" v-if="getGoodsImage(task)" :style="{ backgroundImage: `url(${getGoodsImage(task)})` }">
                <span class="thumb-label">商品</span>
              </div>
            </div>
            <div class="task-card-thumbs task-card-thumbs-empty" v-else>
              <div class="task-thumb task-thumb-placeholder">📷</div>
            </div>

            <!-- 右侧：信息 -->
            <div class="task-card-info">
              <div class="info-row">
                <span class="info-label">用户</span>
                <span class="info-value">{{ getUserDisplay(task) }}</span>
              </div>
              <div class="info-row">
                <span class="info-label">类型</span>
                <span class="info-value">{{ taskTypeLabel(task.task_type) }}</span>
              </div>
              <div class="info-row">
                <span class="info-label">创建</span>
                <span class="info-value">{{ formatTime(task.created_at) }}</span>
              </div>
              <div class="info-row" v-if="task.completed_at">
                <span class="info-label">完成</span>
                <span class="info-value">{{ formatTime(task.completed_at) }}</span>
              </div>
              <div class="info-row" v-if="task.error">
                <span class="info-label">错误</span>
                <span class="info-value error-text">{{ task.error }}</span>
              </div>
              <div class="info-row" v-if="task.warnings?.length">
                <span class="info-label">警告</span>
                <span class="info-value warn-text">{{ task.warnings.join('; ') }}</span>
              </div>
            </div>
          </div>

          <!-- 顶部：RunningHub 任务 ID -->
          <div class="task-card-footer" v-if="getRunninghubId(task)">
            <span class="footer-label">Task ID</span>
            <span class="footer-text mono">{{ getRunninghubId(task) }}</span>
          </div>

          <!-- 底部：文案 -->
          <div class="task-card-footer" v-if="getText(task)">
            <span class="footer-label">文案</span>
            <span class="footer-text">{{ getText(task) }}</span>
          </div>
        </div>
        <div class="pagination-wrapper" v-if="filteredTasks.length > pageSize">
          <el-pagination
            v-model:current-page="currentPage"
            v-model:page-size="pageSize"
            :total="filteredTasks.length"
            :page-sizes="[10, 20, 50, 100]"
            layout="total, sizes, prev, pager, next"
            @current-change="onPageChange"
            @size-change="onPageChange"
            background
          />
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { loadTasks as apiLoadTasks, cancelTask as apiCancelTask, deleteTaskHistory, filePreviewUrl } from '../api'
import { useResources } from '../composables/useResources'
import { getAuth } from '../composables/useAuth'


const loadingTasks = ref(false)
const cancellingId = ref('')
const deletingId = ref('')
const filterStatus = ref('')
const { tasks } = useResources()
const { isAdmin } = getAuth()

const currentPage = ref(1)
const pageSize = ref(16)

const filteredTasks = computed(() => {
  if (!filterStatus.value) return tasks.value
  return tasks.value.filter((t: any) => t.status === filterStatus.value)
})

const pagedTasks = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  return filteredTasks.value.slice(start, start + pageSize.value)
})

const taskElapsedTimes = ref<Record<string, string>>({})
let elapsedTimer: ReturnType<typeof setInterval> | null = null

function formatElapsed(seconds: number): string {
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = seconds % 60
  if (h > 0) return `${h}时${m}分${s}秒`
  if (m > 0) return `${m}分${s}秒`
  return `${s}秒`
}

function getTaskElapsed(task: any): string {
  if (!task.created_at) return ''
  const created = new Date(task.created_at).getTime()
  let end: number
  if (['completed', 'failed', 'cancelled'].includes(task.status)) {
    end = task.completed_at ? new Date(task.completed_at).getTime() : Date.now()
  } else if (task.status === 'running') {
    end = Date.now()
  } else {
    return ''
  }
  const elapsed = Math.floor((end - created) / 1000)
  if (elapsed <= 0) return ''
  return formatElapsed(elapsed)
}

function getStatusText(task: any): string {
  const labels: Record<string, string> = {
    pending: '待处理',
    running: '进行中',
    pending_confirmation: '待确认',
    completed: '已完成',
    failed: '失败',
    cancelled: '已取消',
  }
  return labels[task.status] || task.status
}

function updateElapsedTimes() {
  const times: Record<string, string> = {}
  for (const task of tasks.value) {
    const elapsed = getTaskElapsed(task)
    if (elapsed) times[task.task_id] = elapsed
  }
  taskElapsedTimes.value = times
}

function startElapsedTimer() {
  stopElapsedTimer()
  updateElapsedTimes()
  elapsedTimer = setInterval(updateElapsedTimes, 1000)
}

function stopElapsedTimer() {
  if (elapsedTimer) {
    clearInterval(elapsedTimer)
    elapsedTimer = null
  }
}

onMounted(() => {
  loadTasks()
  startElapsedTimer()
  startTaskPolling()
})

onUnmounted(() => {
  stopElapsedTimer()
  stopTaskPolling()
})

async function loadTasks() {
  loadingTasks.value = true
  try { tasks.value = await apiLoadTasks(100, filterStatus.value || undefined) }
  catch { tasks.value = [] }
  finally {
    loadingTasks.value = false
    updateElapsedTimes()
  }
}

let pollTimer: ReturnType<typeof setInterval> | null = null

function startTaskPolling() {
  stopTaskPolling()
  // 每 10 秒轮询一次任务状态，确保状态变化时 UI 自动更新
  // 组件销毁时 stopTaskPolling 会清除定时器，防止内存泄漏
  pollTimer = setInterval(() => {
    apiLoadTasks(100, filterStatus.value || undefined)
      .then((newTasks) => {
        tasks.value = newTasks
        updateElapsedTimes()
      })
      .catch(() => { /* 静默处理轮询失败 */ })
  }, 10000)
}

function stopTaskPolling() {
  if (pollTimer !== null) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

function onFilterChange() {
  currentPage.value = 1
  loadTasks()
}

function onPageChange() {
  // el-pagination 已通过 v-model 绑定 currentPage / pageSize
}

watch(pageSize, () => {
  currentPage.value = 1
})

function tagType(status: string): string {
  return { completed: 'success', running: 'warning', pending: 'info', failed: 'danger', cancelled: 'info' }[status] || 'info'
}

function shortId(id: string): string {
  return id.length > 20 ? id.slice(0, 20) + '...' : id
}

function statusLabel(status: string): string {
  const labels: Record<string, string> = {
    pending: '待处理',
    running: '进行中',
    pending_confirmation: '待确认',
    completed: '已完成',
    failed: '失败',
    cancelled: '已取消',
  }
  return labels[status] || status
}

function taskTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    video_generation: '视频生成',
  }
  return labels[type] || type
}

function formatTime(iso: string): string {
  if (!iso) return ''
  try {
    const d = new Date(iso)
    const pad = (n: number) => String(n).padStart(2, '0')
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
  } catch {
    return iso
  }
}

function canCancel(status: string): boolean {
  return ['pending', 'running', 'pending_confirmation'].includes(status)
}

async function handleDeleteTask(taskId: string) {
  try {
    await ElMessageBox.confirm('确定删除该任务？删除后不可恢复。', '确认删除', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch {
    return
  }
  deletingId.value = taskId
  try {
    await deleteTaskHistory(taskId)
  } catch (e: any) {
    // 404 means the task exists in memory but not persisted to filesystem yet.
    // The request() API throws new Error(detail), so e.message contains "not found in history"
    const msg = typeof e === 'string' ? e : (e?.message || '')
    if (!msg.includes('not found in history') && !msg.includes('404')) {
      ElMessage.error(`删除失败：${msg}`)
      deletingId.value = ''
      return
    }
  }
  tasks.value = tasks.value.filter((t: any) => t.task_id !== taskId)
  ElMessage.success('已删除任务')
  deletingId.value = ''
}

async function handleCancelTask(taskId: string) {
  cancellingId.value = taskId
  try {
    const resp: any = await apiCancelTask(taskId)
    const task = tasks.value.find((t: any) => t.task_id === taskId)
    if (task) {
      task.status = 'cancelled'
      task.completed_at = new Date().toISOString()
    }
    ElMessage.success(resp?.message || '已取消任务')
    // Refresh after a short delay to reflect server-side status
    setTimeout(() => { loadTasks() }, 800)
  } catch (e: any) {
    console.error('Cancel task error:', e)
    const msg = typeof e === 'string' ? e : (e?.message || '取消失败')
    ElMessage.error(`取消失败：${msg}`)
  } finally {
    cancellingId.value = ''
  }
}


function hasPreviews(task: any): boolean {
  return !!getCharacterImage(task) || !!getGoodsImage(task)
}

function getCharacterImage(task: any): string {
  const params = task.request_params
  if (!params) return ''
  const assets = params.character_assets || []
  if (assets.length > 0) return filePreviewUrl(assets[0])
  return ''
}

function getGoodsImage(task: any): string {
  const params = task.request_params
  if (!params) return ''
  const assets = params.goods_assets || []
  if (assets.length > 0) return filePreviewUrl(assets[0])
  return ''
}

function getRunninghubId(task: any): string {
  const params = task.request_params
  if (!params) return ''
  return params._runninghub_task_id || ''
}

function getText(task: any): string {
  const params = task.request_params
  if (!params) return ''
  return params.goods_text || params.goods_title || ''
}

function getUserDisplay(task: any): string {
  return task.phone || task.username || '-'
}
</script>
