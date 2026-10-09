import { defineStore } from 'pinia'
import http, { TOKEN_KEY, USER_KEY } from '../lib/http'
import { DEMO_ACTIVE_KEY, DEMO_USER, isDemoActive, readDemo } from '../lib/demo'
import { useRoomStore } from './room'
import { useMessageStore } from './message'
const initializationTasks = new WeakMap()

function readStoredUser() {
  const raw = localStorage.getItem(USER_KEY)

  if (!raw) {
    return null
  }

  try {
    return JSON.parse(raw)
  } catch {
    localStorage.removeItem(USER_KEY)
    return null
  }
}

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem(TOKEN_KEY) || '',
    user: isDemoActive() ? { ...DEMO_USER } : readStoredUser(),
    demoMode: isDemoActive(),
    loading: false,
    bootstrapping: false,
    initialized: false,
  }),

  getters: {
    isLoggedIn: (state) => state.demoMode || (!!state.token && !!state.user),
  },

  actions: {
    enterDemo() {
      sessionStorage.setItem(DEMO_ACTIVE_KEY, 'true')
      readDemo()
      this.demoMode = true
      this.user = { ...DEMO_USER }
      this.initialized = true
      useRoomStore().clearRooms()
      useMessageStore().clearMessages()
    },
    setAuth(token, user) {
      this.token = token
      this.user = user

      localStorage.setItem(TOKEN_KEY, token)
      localStorage.setItem(USER_KEY, JSON.stringify(user))
    },

    setUser(user) {
      this.user = user
      localStorage.setItem(USER_KEY, JSON.stringify(user))
    },

    clearAuth() {
      this.token = ''
      this.user = null

      localStorage.removeItem(TOKEN_KEY)
      localStorage.removeItem(USER_KEY)
    },

    async login(identifier, password) {
      this.loading = true

      try {
        const response = await http.post('/auth/login', {
          identifier,
          password,
        })

        const data = response.data
        this.setAuth(data.access_token, data.user)

        return data
      } finally {
        this.loading = false
      }
    },

    async fetchMe() {
      if (this.demoMode) return this.user
      const response = await http.get('/users/me')
      this.setUser(response.data)
      return response.data
    },

    async initializeAuth() {
      if (this.initialized) return
      if (initializationTasks.has(this)) return initializationTasks.get(this)
      this.bootstrapping = true
      const task = Promise.resolve().then(async () => {
        try {
          if (this.demoMode) return
          if (!this.token) { this.clearAuth(); return }
          await this.fetchMe()
        } catch (error) {
          if ([401, 403].includes(error?.response?.status)) this.clearAuth()
        } finally {
          this.bootstrapping = false
          this.initialized = true
          initializationTasks.delete(this)
        }
      })
      initializationTasks.set(this, task)
      return task
    },

    logout() {
      useRoomStore().clearRooms()
      useMessageStore().clearMessages()
      if (this.demoMode) {
        sessionStorage.removeItem(DEMO_ACTIVE_KEY)
        this.demoMode = false
        this.token = localStorage.getItem(TOKEN_KEY) || ''
        this.user = readStoredUser()
      } else this.clearAuth()
    },
  },
})
