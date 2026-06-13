<template>
  <!-- Login Page -->
  <LoginView v-if="showLogin" @login-success="handleLoginSuccess" />

  <!-- Main App -->
  <div class="shell" v-else>
    <aside class="sidebar" :class="{ collapsed: !sidebarOpen }">
      <div class="brand">
        <div class="brand-logo">🎬</div>
        <div class="brand-text">
          <h1 class="brand-title">Pixelle Studio</h1>
          <p class="brand-subtitle">Full Modern UI</p>
        </div>
        <!-- Mobile toggle button -->
        <button class="sidebar-toggle" @click="sidebarOpen = !sidebarOpen" aria-label="切换菜单">
          <span class="toggle-bar" :class="{ open: sidebarOpen }"></span>
          <span class="toggle-bar" :class="{ open: sidebarOpen }"></span>
          <span class="toggle-bar" :class="{ open: sidebarOpen }"></span>
        </button>
      </div>

      <div class="sidebar-nav-wrapper" :class="{ collapsed: !sidebarOpen }">
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

        <!-- Spacer + User Menu at bottom -->
        <div style="flex:1"></div>

        <UserMenu @show-login="showLogin = true" @go-admin="switchView('admin')" />
      </div>
    </aside>

    <main class="main">
      <QuickCreateView v-if="activeView === 'quick_create'" />
      <!-- <AssetBasedView v-if="activeView === 'custom_media'" /> -->
      <DigitalHumanView v-if="activeView === 'digital_human'" />
      <!-- <I2vView v-if="activeView === 'image_to_video'" /> -->
      <!-- <ActionTransferView v-if="activeView === 'action_transfer'" /> -->

      <!-- ====== 📋 历史记录 ====== -->
      <TaskHistoryView v-if="activeView === 'history'" />

      <!-- ====== ⚙️ 系统配置 ====== -->
      <SettingsView v-if="activeView === 'settings'" />

      <!-- ====== 🔐 用户管理 (Admin) ====== -->
      <AdminView v-if="activeView === 'admin'" />

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

    </main>

  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import type { NavItem } from './types'
import { loadTasks as apiLoadTasks } from './api'
import { useResources } from './composables/useResources'
import { getAuth } from './composables/useAuth'
import QuickCreateView from './views/QuickCreateView.vue'
import AssetBasedView from './views/AssetBasedView.vue'
import DigitalHumanView from './views/DigitalHumanView.vue'
import I2vView from './views/I2vView.vue'
import ActionTransferView from './views/ActionTransferView.vue'
import TaskHistoryView from './views/TaskHistoryView.vue'
import SettingsView from './views/SettingsView.vue'
import LoginView from './views/LoginView.vue'
import AdminView from './views/AdminView.vue'
import UserMenu from './components/UserMenu.vue'

const auth = getAuth()
const activeView = ref('digital_human')
const showLogin = ref(!auth.isLoggedIn.value)
const sidebarOpen = ref(false)

const { tasks, loadAll } = useResources()

const baseNavItems: NavItem[] = [
  { key: 'digital_human', icon: '🤖', label: '数字人' },
  { key: 'quick_create', icon: '⚡', label: '快速创作' },
  // { key: 'custom_media', icon: '🎨', label: '素材创作' },
  // { key: 'image_to_video', icon: '🎥', label: '图生视频' },
  // { key: 'action_transfer', icon: '💃', label: '动作迁移' },
  { key: 'tasks', icon: '📊', label: '任务中心' },
  { key: 'history', icon: '📋', label: '历史记录' },
]

const navItems = computed(() => {
  const items = [...baseNavItems]
  if (auth.isAdmin.value) {
    items.push({ key: 'settings', icon: '⚙️', label: '系统配置' })
  }
  return items
})

onMounted(() => {
  if (auth.isLoggedIn.value) {
    loadAll()
  }
})

function switchView(key: string) {
  activeView.value = key
  sidebarOpen.value = false
}

function handleLoginSuccess() {
  showLogin.value = false
  loadAll()
}

async function loadTasks() {
  try { tasks.value = await apiLoadTasks() }
  catch { tasks.value = [] }
}

function tagType(status: string): string {
  return { completed: 'success', running: 'warning', pending: 'info', failed: 'danger', cancelled: 'info' }[status] || 'info'
}
</script>
