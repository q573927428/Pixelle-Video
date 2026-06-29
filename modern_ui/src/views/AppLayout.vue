<template>
  <div class="shell">
    <!-- Desktop sidebar -->
    <aside class="sidebar" :class="{ collapsed: !sidebarOpen }">
      <div class="brand">
        <div class="brand-logo">🎬</div>
        <div class="brand-text">
          <h1 class="brand-title">ZuoSuo AI</h1>
          <p class="brand-subtitle">创作之所 作为之所在</p>
        </div>
      </div>

      <div class="sidebar-nav-wrapper">
        <div class="nav-title">工作台</div>
        <button
          v-for="item in navItems"
          :key="item.key"
          class="nav-item"
          :class="{ active: currentRoute === item.key }"
          @click="switchView(item.key)"
        >
          <span class="nav-icon">{{ item.icon }}</span>
          <span>{{ item.label }}</span>
        </button>

        <!-- Spacer + User Menu at bottom -->
        <div style="flex:1"></div>

        <UserMenu @show-login="handleLogout" />
      </div>
    </aside>

    <!-- Mobile top header (always visible) -->
    <header class="mobile-header">
      <div class="mobile-header-inner">
        <div class="brand">
          <div class="brand-logo">🎬</div>
          <div class="brand-text">
            <h1 class="brand-title">ZuoSuo AI</h1>
            <p class="brand-subtitle">创作之所 作为之所在</p>
          </div>
        </div>
        <button class="sidebar-toggle" @click="sidebarOpen = !sidebarOpen" aria-label="切换菜单">
          <span class="toggle-bar" :class="{ open: sidebarOpen }"></span>
          <span class="toggle-bar" :class="{ open: sidebarOpen }"></span>
          <span class="toggle-bar" :class="{ open: sidebarOpen }"></span>
        </button>
      </div>
    </header>

    <!-- Mobile overlay + drawer navigation -->
    <div v-if="sidebarOpen" class="mobile-overlay" @click="sidebarOpen = false" />

    <aside class="mobile-drawer" :class="{ open: sidebarOpen }">
      <div class="sidebar-nav-wrapper">
        <button
          v-for="item in navItems"
          :key="item.key"
          class="nav-item"
          :class="{ active: currentRoute === item.key }"
          @click="switchView(item.key); sidebarOpen = false"
        >
          <span class="nav-icon">{{ item.icon }}</span>
          <span>{{ item.label }}</span>
        </button>

        <div style="flex:1"></div>

        <UserMenu @show-login="handleLogout" />
      </div>
    </aside>

    <main class="main">
      <slot />
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import type { NavItem } from '@/types'
import { useResources } from '@/composables/useResources'
import { getAuth } from '@/composables/useAuth'
import UserMenu from '@/components/UserMenu.vue'

const router = useRouter()
const route = useRoute()
const auth = getAuth()
const { loadAll } = useResources()

const sidebarOpen = ref(window.innerWidth > 768)

function onResize() {
  if (window.innerWidth > 768) {
    sidebarOpen.value = true
  } else {
    sidebarOpen.value = false
  }
}

const baseNavItems: NavItem[] = [
  { key: 'create', icon: '🤖', label: '数字人' },
  { key: 'tasks', icon: '🗓️', label: '任务中心' },
  { key: 'history', icon: '📝', label: '历史记录' },
  { key: 'account', icon: '💰', label: '账户明细' },
]

const currentRoute = computed(() => {
  const name = (route.name as string) || ''
  // 路由名 digital_human 对应导航 key create
  if (name === 'digital_human') return 'create'
  return name
})

const navItems = computed(() => {
  const items = [...baseNavItems]
  if (auth.isAdmin.value) {
    items.push({ key: 'settings', icon: '⚙️', label: '系统配置' })
    items.push({ key: 'instances', icon: '🖥️', label: '实例管理' })
    items.push({ key: 'admin', icon: '🔐', label: '用户管理' })
  }
  return items
})

onMounted(() => {
  loadAll()
  window.addEventListener('resize', onResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
})

function switchView(key: string) {
  router.push(`/${key}`)
}

function handleLogout() {
  router.push('/login')
}
</script>

<style scoped>
.shell {
  display: flex;
  height: 100vh;
  background: #0f0f1a;
  color: #e0e0e0;
}

.sidebar {
  width: 260px;
  min-width: 260px;
  background: rgba(255, 255, 255, 0.03);
  border-right: 1px solid rgba(255, 255, 255, 0.06);
  display: flex;
  flex-direction: column;
  transition: width 0.3s, min-width 0.3s;
  overflow: hidden;
}

.sidebar.collapsed {
  width: 0;
  min-width: 0;
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 20px 20px 16px;
  position: relative;
}

.brand-logo {
  width: 46px;
  height: 46px;
  display: grid;
  place-items: center;
  border-radius: 16px;
  background: linear-gradient(135deg, var(--brand), var(--brand-2));
  box-shadow: 0 18px 45px #7c3aed59;
  font-size: 24px;
}

.brand-text {
  flex: 1;
  min-width: 0;
}

.brand-title {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
  color: #fff;
  line-height: 1.2;
}

.brand-subtitle {
  margin: 3px 0 0;
  color: var(--muted);
  font-size: 12px;
}

.sidebar-toggle {
  display: none;
  position: absolute;
  right: 8px;
  top: 50%;
  transform: translateY(-50%);
  background: none;
  border: none;
  cursor: pointer;
  padding: 8px;
  flex-direction: column;
  gap: 4px;
}

.toggle-bar {
  display: block;
  width: 20px;
  height: 2px;
  background: rgba(255, 255, 255, 0.6);
  border-radius: 2px;
  transition: transform 0.3s, opacity 0.3s;
}

.toggle-bar.open:nth-child(1) {
  transform: rotate(45deg) translate(4px, 4px);
}

.toggle-bar.open:nth-child(2) {
  opacity: 0;
}

.toggle-bar.open:nth-child(3) {
  transform: rotate(-45deg) translate(4px, -4px);
}

.sidebar-nav-wrapper {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 8px 12px 16px;
  overflow-y: auto;
}

.nav-title {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: rgba(255, 255, 255, 0.3);
  padding: 8px 12px;
  margin-bottom: 4px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border: 1px solid transparent;
  border-radius: 16px;
  background: transparent;
  color: #fff;
  font-size: 14px;
  cursor: pointer;
  transition: background 0.15s, color 0.15s, border-color 0.15s;
  text-align: left;
  width: 100%;
}

.nav-item:hover,
.nav-item.active {
  background: linear-gradient(135deg, #7c3aed40, #06b6d421);
  border-color: #7dd3fc3d;
  color: #fff;
}

.nav-icon {
  font-size: 18px;
  width: 24px;
  text-align: center;
  flex-shrink: 0;
}

.main {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  min-width: 0;
  background: radial-gradient(circle at 10% 10%, rgba(124, 58, 237, .32), transparent 34%), radial-gradient(circle at 88% 12%, rgba(6, 182, 212, .24), transparent 32%), linear-gradient(135deg, #07111f, #0c1222 48%, #101827);
}

/* Mobile header */
.mobile-header {
  display: none;
}

.mobile-overlay {
  display: none;
}

.mobile-drawer {
  display: none;
}

/* Desktop: hide desktop sidebar brand toggle button */
.sidebar .sidebar-toggle {
  display: none;
}

@media (max-width: 768px) {
  .sidebar {
    display: none;
  }

  .shell {
    flex-direction: column;
  }

  .mobile-header {
    display: flex;
    align-items: center;
    height: 74px;
    background: #1a1a2e;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    flex-shrink: 0;
    position: sticky;
    top: 0;
    z-index: 90;
  }

  .mobile-header-inner {
    display: flex;
    align-items: center;
    width: 100%;
    padding: 0 16px;
    position: relative;
  }

  .mobile-header-inner .brand {
    padding: 0;
  }

  .mobile-header .sidebar-toggle {
    display: flex;
    position: relative;
    right: auto;
    top: auto;
    transform: none;
    margin-left: auto;
  }

  .mobile-overlay {
    display: block;
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.5);
    z-index: 95;
  }

  .mobile-drawer {
    display: flex;
    flex-direction: column;
    position: fixed;
    left: 0;
    top: 64px;
    bottom: 0;
    width: 260px;
    background: #0f0f1a;
    border-right: 1px solid rgba(255, 255, 255, 0.06);
    z-index: 96;
    transform: translateX(-100%);
    transition: transform 0.3s ease;
  }

  .mobile-drawer.open {
    transform: translateX(0);
  }

  .main {
    padding: 16px;
    padding-top: 0;
  }
}
</style>
