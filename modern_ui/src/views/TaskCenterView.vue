<template>
  <section>
    <div class="card">
      <div class="card-header">
        <h3 class="card-title">📊 任务中心</h3>
        <div class="card-header-tools">
          <el-select v-model="filterStatus" placeholder="状态筛选" size="small" clearable @change="loadTasks" style="width:110px;margin-right:8px">
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
        <div v-if="!filteredTasks.length" class="empty-preview">暂无任务</div>
        <div v-for="task in filteredTasks" :key="task.task_id" class="task-card">
          <div class="task-card-header">
            <span class="task-card-id mono">{{ shortId(task.task_id) }}</span>
            <div class="task-card-header-actions">
              <el-tag :type="tagType(task.status)" effect="dark" size="small">{{ statusLabel(task.status) }}</el-tag>
              <el-button
                v-if="canCancel(task.status)"
                size="small"
                type="danger"
                text
                :loading="cancellingId === task.task_id"
                @click="handleCancelTask(task.task_id)"
              >取消</el-button>
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
            <span class="footer-label">RunningHub ID</span>
            <span class="footer-text mono">{{ getRunninghubId(task) }}</span>
          </div>

          <!-- 底部：文案 -->
          <div class="task-card-footer" v-if="getText(task)">
            <span class="footer-label">文案</span>
            <span class="footer-text">{{ getText(task) }}</span>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { loadTasks as apiLoadTasks, cancelTask as apiCancelTask, filePreviewUrl } from '../api'
import { useResources } from '../composables/useResources'
import { getAuth } from '../composables/useAuth'


const loadingTasks = ref(false)
const cancellingId = ref('')
const filterStatus = ref('')
const { tasks } = useResources()
const { isAdmin } = getAuth()

const filteredTasks = computed(() => {
  if (!filterStatus.value) return tasks.value
  return tasks.value.filter((t: any) => t.status === filterStatus.value)
})

onMounted(() => {
  loadTasks()
})

async function loadTasks() {
  loadingTasks.value = true
  try { tasks.value = await apiLoadTasks(100, filterStatus.value || undefined) }
  catch { tasks.value = [] }
  finally { loadingTasks.value = false }
}

function tagType(status: string): string {
  return { completed: 'success', running: 'warning', pending: 'info', failed: 'danger', cancelled: 'info' }[status] || 'info'
}

function shortId(id: string): string {
  return id.length > 12 ? id.slice(0, 12) + '...' : id
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
</script>