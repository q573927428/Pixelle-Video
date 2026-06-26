import { createRouter, createWebHistory } from 'vue-router'
import { getAuth } from '@/composables/useAuth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'home',
      component: () => import('@/views/HomePage.vue'),
    },
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
    },
    {
      path: '/register',
      name: 'register',
      component: () => import('@/views/LoginView.vue'),
    },
    {
      path: '/create',
      name: 'digital_human',
      component: () => import('@/views/DigitalHumanView.vue'),
    },
    {
      path: '/tasks',
      name: 'tasks',
      component: () => import('@/views/TaskCenterView.vue'),
    },
    {
      path: '/history',
      name: 'history',
      component: () => import('@/views/TaskHistoryView.vue'),
    },
    {
      path: '/account',
      name: 'account',
      component: () => import('@/views/AccountDetailView.vue'),
    },
    {
      path: '/settings',
      name: 'settings',
      component: () => import('@/views/SettingsView.vue'),
    },
    {
      path: '/admin',
      name: 'admin',
      component: () => import('@/views/AdminView.vue'),
    },
  ],
})

/** 需要侧边栏布局的路由 (route name) */
export const appRoutes = ['digital_human', 'tasks', 'history', 'account', 'settings', 'admin']

router.beforeEach((to, _from) => {
  const auth = getAuth()
  const isLoggedIn = auth.isLoggedIn.value

  // 未登录访问 app 页面，重定向到登录
  if (appRoutes.includes(to.name as string) && !isLoggedIn) {
    return '/login'
  }

  // 已登录访问 /login 或 /register，重定向到 /create
  if ((to.path === '/login' || to.path === '/register') && isLoggedIn) {
    return '/create'
  }

  // 已登录访问 /，重定向到 /create
  if (to.path === '/' && isLoggedIn) {
    return '/create'
  }
})

export default router