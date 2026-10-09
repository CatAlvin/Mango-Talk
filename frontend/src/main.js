import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'
import { useAuthStore } from './stores/auth'
import './style.css'

async function bootstrap() {
  const app = createApp(App)
  const pinia = createPinia()

  app.use(pinia)
  app.use(router)
  await router.isReady()

  const authStore = useAuthStore(pinia)
  window.addEventListener('mango:unauthorized', () => {
    if (authStore.demoMode) return
    authStore.logout()
    router.replace('/login')
  })
  await authStore.initializeAuth()

  app.mount('#app')
}

bootstrap()
