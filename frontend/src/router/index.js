import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

import LoginView from '../views/LoginView.vue'
import ChatView from '../views/ChatView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      redirect: '/login',
    },
    {
      path: '/login',
      name: 'login',
      component: LoginView,
    },
    {
      path: '/demo',
      name: 'demo',
      component: ChatView,
      meta: { demo: true },
    },
    {
      path: '/chat',
      name: 'chat',
      component: ChatView,
      meta: {
        requiresAuth: true,
      },
    },
  ],
})

router.beforeEach(async (to) => {
  const authStore = useAuthStore()

  if (to.meta.demo) {
    if (!authStore.demoMode) authStore.enterDemo()
    return
  }

  if (!authStore.initialized) {
    await authStore.initializeAuth()
  }

  if (to.meta.requiresAuth && !authStore.isLoggedIn) {
    return '/login'
  }

  if (to.path === '/chat' && authStore.demoMode) return '/demo'

  if (to.path === '/login' && authStore.isLoggedIn) {
    return authStore.demoMode ? '/demo' : '/chat'
  }
})

export default router
