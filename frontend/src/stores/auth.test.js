import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useAuthStore } from './auth'
import http, { TOKEN_KEY, USER_KEY } from '../lib/http'
import { DEMO_ACTIVE_KEY } from '../lib/demo'
import { useRoomStore } from './room'
import { useMessageStore } from './message'

beforeEach(() => { localStorage.clear(); sessionStorage.clear(); setActivePinia(createPinia()) })
describe('身份恢复', () => {
  it('启动器和路由同时初始化身份时只请求一次', async () => {
    const store = useAuthStore()
    store.setAuth('token', { id: 8, username: '用户' })
    let resolve
    const get = vi.spyOn(http, 'get').mockImplementation(() => new Promise((done) => { resolve = done }))
    const first = store.initializeAuth()
    const second = store.initializeAuth()
    await Promise.resolve()
    expect(get).toHaveBeenCalledTimes(1)
    resolve({ data: { id: 8, username: '用户' } })
    await Promise.all([first, second])
    expect(store.initialized).toBe(true)
  })
  it('网络故障保留已有身份，身份到期则清除', async () => {
    const store = useAuthStore()
    store.setAuth('token', { id: 8, username: '用户' })
    const get = vi.spyOn(http, 'get').mockRejectedValueOnce(new Error('Network Error'))
    await store.initializeAuth()
    expect(store.token).toBe('token')
    store.initialized = false
    get.mockRejectedValueOnce({ response: { status: 401 } })
    await store.initializeAuth()
    expect(store.token).toBe('')
  })
  it('演示进入、刷新和退出不会覆盖真实认证数据', async () => {
    const store = useAuthStore()
    store.setAuth('real-token', { id: 8, username: '原用户' })
    useRoomStore().rooms = [{ id: 99, display_name: '真实私人会话' }]
    useMessageStore().appendOrUpdateMessage(99, { id: 99, content: '真实私密正文' })
    store.enterDemo()
    expect(useRoomStore().rooms).toEqual([])
    expect(useMessageStore().roomMessages).toEqual({})
    expect(sessionStorage.getItem(DEMO_ACTIVE_KEY)).toBe('true')
    expect(localStorage.getItem(TOKEN_KEY)).toBe('real-token')
    expect(localStorage.getItem(USER_KEY)).toContain('原用户')
    store.initialized = false
    const get = vi.spyOn(http, 'get')
    await store.initializeAuth()
    expect(get).not.toHaveBeenCalled()
    store.logout()
    expect(store.user.username).toBe('原用户')
    expect(store.demoMode).toBe(false)
    expect(useRoomStore().rooms).toEqual([])
    expect(useMessageStore().roomMessages).toEqual({})
  })
})
