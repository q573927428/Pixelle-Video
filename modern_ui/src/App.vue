<template>
  <div class="shell">
    <aside class="sidebar">
      <div class="brand">
        <div class="brand-logo">🎬</div>
        <div>
          <h1 class="brand-title">Pixelle Studio</h1>
          <p class="brand-subtitle">Full Modern UI</p>
        </div>
      </div>

      <div class="nav-title">工作台</div>
      <button
        v-for="item in navItems"
        :key="item.key"
        class="nav-item"
        :class="{ active: activeView === item.key }"
        @click="switchView(item.key)"
      >
        <span class="nav-icon">{{ item.icon }}</span>
        <span>{{ item.label }}</span>
      </button>
    </aside>

    <main class="main">
      <QuickCreateView v-if="activeView === 'quick_create'" />
      <AssetBasedView v-if="activeView === 'custom_media'" />
      <DigitalHumanView v-if="activeView === 'digital_human'" />
      <I2vView v-if="activeView === 'image_to_video'" />
      <ActionTransferView v-if="activeView === 'action_transfer'" />

      <!-- ====== 📋 历史记录 ====== -->
      <TaskHistoryView v-if="activeView === 'history'" />

      <!-- ====== ⚙️ 系统配置 ====== -->
      <SettingsView v-if="activeView === 'settings'" />

      <!-- ====== 📤 上传中心 ====== -->
      <section v-if="activeView === 'assets'">
        <div class="grid grid-2">
          <div class="card">
            <div class="card-header"><h3 class="card-title">📤 上传中心</h3><el-tag effect="dark">temp/uploads</el-tag></div>
            <div class="card-body">
              <el-tabs v-model="uploadCategory">
                <el-tab-pane label="图片素材" name="image" />
                <el-tab-pane label="视频素材" name="video" />
                <el-tab-pane label="参考音频" name="ref_audio" />
                <el-tab-pane label="数字人角色" name="character_image" />
                <el-tab-pane label="商品图" name="goods_image" />
              </el-tabs>
              <UploadBox :category="uploadCategory" :accept="uploadAccept" @upload="handleUpload" @select-history="openHistory" />
              <UploadList :uploads="uploads" />
            </div>
          </div>
          <div class="card">
            <div class="card-header"><h3 class="card-title">🧭 使用说明</h3></div>
            <div class="card-body">
              <el-timeline>
                <el-timeline-item timestamp="1. 上传素材" type="primary">上传后的绝对路径会自动加入对应工具表单。</el-timeline-item>
                <el-timeline-item timestamp="2. 选择工作流" type="success">图生视频使用 i2v_ 工作流，动作迁移使用 af_ 工作流。</el-timeline-item>
                <el-timeline-item timestamp="3. 提交任务" type="warning">所有工具统一进入任务中心，可轮询状态并预览结果。</el-timeline-item>
              </el-timeline>
            </div>
          </div>
        </div>
      </section>

      <!-- ====== 📊 任务中心 ====== -->
      <section v-if="activeView === 'tasks'">
        <div class="card">
          <div class="card-header"><h3 class="card-title">📊 任务中心</h3><el-button @click="loadTasks">刷新</el-button></div>
          <div class="card-body">
            <div v-if="!tasks.length" class="empty-preview">暂无任务</div>
            <div v-for="task in tasks" :key="task.task_id" class="task-item">
              <div class="task-top"><span class="mono">{{ task.task_id }}</span><el-tag :type="tagType(task.status)" effect="dark">{{ task.status }}</el-tag></div>
              <el-progress :percentage="task.progress?.percentage ?? 0" />
              <div class="small muted">{{ task.progress?.message || task.message || `状态：${task.status}` }}</div>
            </div>
          </div>
        </div>
      </section>

      <!-- ====== 🧩 资源管理 ====== -->
      <section v-if="activeView === 'resources'">
        <div class="grid grid-3">
          <ResourceCard title="🖼️ 模板" :items="templates" label-key="display_name" tag-key="size" />
          <ResourceCard title="🧩 媒体工作流" :items="mediaWorkflows" label-key="display_name" tag-key="source" />
          <ResourceCard title="🎵 BGM / TTS" :items="[...bgmFiles, ...ttsWorkflows]" label-key="display_name" fallback-label-key="name" tag-key="source" />
        </div>
      </section>
    </main>

    <HistoryDialog v-model="historyVisible" :loading="historyLoading" :records="historyRecords" :filter-category="historyFilterCategory" @select="onHistorySelect" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import type { NavItem } from './types'
import { uploadFile as apiUpload, saveToLocalHistory, loadLocalHistory, loadTasks as apiLoadTasks } from './api'
import { useResources } from './composables/useResources'
import UploadBox from './components/UploadBox.vue'
import UploadList from './components/UploadList.vue'
import ResourceCard from './components/ResourceCard.vue'
import HistoryDialog from './components/HistoryDialog.vue'
import QuickCreateView from './views/QuickCreateView.vue'
import AssetBasedView from './views/AssetBasedView.vue'
import DigitalHumanView from './views/DigitalHumanView.vue'
import I2vView from './views/I2vView.vue'
import ActionTransferView from './views/ActionTransferView.vue'
import TaskHistoryView from './views/TaskHistoryView.vue'
import SettingsView from './views/SettingsView.vue'

const activeView = ref('digital_human')
const uploadCategory = ref('image')

const uploadAccept = computed(() => {
  const acceptMap: Record<string, string> = {
    image: 'image/*',
    video: 'video/*',
    ref_audio: 'audio/*',
    character_image: 'image/*',
    goods_image: 'image/*',
  }
  return acceptMap[uploadCategory.value] || undefined
})

const { templates, mediaWorkflows, ttsWorkflows, bgmFiles, tasks, uploads, loadAll } = useResources()

const historyVisible = ref(false)
const historyLoading = ref(false)
const historyRecords = ref<any[]>([])
const historyFilterCategory = ref<string | undefined>(undefined)

const navItems: NavItem[] = [
  { key: 'digital_human', icon: '🤖', label: '数字人' },
  { key: 'quick_create', icon: '⚡', label: '快速创作' },
  { key: 'custom_media', icon: '🎨', label: '素材创作' },
  { key: 'image_to_video', icon: '🎥', label: '图生视频' },
  { key: 'action_transfer', icon: '💃', label: '动作迁移' },
  { key: 'assets', icon: '📤', label: '上传中心' },
  { key: 'tasks', icon: '📊', label: '任务中心' },
  { key: 'history', icon: '📋', label: '历史记录' },
  { key: 'resources', icon: '🧩', label: '资源管理' },
  { key: 'settings', icon: '⚙️', label: '系统配置' },
]

onMounted(() => {
  loadAll()
})

function switchView(key: string) {
  activeView.value = key
}


async function loadTasks() {
  try { tasks.value = await apiLoadTasks() }
  catch { tasks.value = [] }
}

async function handleUpload(rawFile: File, category: string) {
  if (!rawFile) return
  try {
    const data = await apiUpload(rawFile, category)
    uploads.value.unshift(data)
    saveToLocalHistory(data, category)
    ElMessage.success(`${data.filename} 上传成功`)
  } catch (e: any) {
    ElMessage.error(`上传失败：${e.message}`)
  }
}

function openHistory(category: string) {
  const localHistory = loadLocalHistory()
  historyRecords.value = localHistory.slice(0, 50)
  historyFilterCategory.value = category
  historyVisible.value = true
}

function onHistorySelect(record: any) {
  historyVisible.value = false
  historyFilterCategory.value = undefined
  ElMessage.success(`已选择：${record.name}`)
}

function tagType(status: string): string {
  return { completed: 'success', running: 'warning', pending: 'info', failed: 'danger', cancelled: 'info' }[status] || 'info'
}
</script>