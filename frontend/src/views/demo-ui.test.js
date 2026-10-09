import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import { flushPromises, mount } from '@vue/test-utils'
import ChatView from './ChatView.vue'
import App from '../App.vue'
import appRouter from '../router'
import GroupRoomCreator from '../components/GroupRoomCreator.vue'
import PrivateRoomCreator from '../components/PrivateRoomCreator.vue'
import { useAuthStore } from '../stores/auth'
import { DEMO_ACTIVE_KEY, readDemo, resetDemo } from '../lib/demo'
import http from '../lib/http'
import { useRoomStore } from '../stores/room'
import { useMessageStore } from '../stores/message'

const wrappers = []
beforeEach(() => {
  localStorage.clear(); sessionStorage.clear(); sessionStorage.setItem(DEMO_ACTIVE_KEY, 'true'); resetDemo()
  vi.stubGlobal('matchMedia', () => ({ matches: false }))
  HTMLElement.prototype.scrollTo = vi.fn()
  HTMLElement.prototype.scrollIntoView = vi.fn()
})
afterEach(() => { wrappers.splice(0).forEach((wrapper) => wrapper.unmount()); document.body.innerHTML = ''; vi.unstubAllGlobals() })
const render = (component, options = {}) => { const wrapper = mount(component, { attachTo: document.body, ...options }); wrappers.push(wrapper); return wrapper }

describe('演示用户流程', () => {
  it('已登录账号直接进入/demo会卸载旧连接、清除真实缓存，退出仍保留真实凭据', async () => {
    sessionStorage.removeItem(DEMO_ACTIVE_KEY)
    const pinia = createPinia(); setActivePinia(pinia)
    const auth = useAuthStore()
    auth.setAuth('real-token', { id: 8, username: '真实用户' }); auth.initialized = true
    const connections = []
    vi.stubGlobal('WebSocket', class { constructor() { this.close = vi.fn(); connections.push(this) } })
    const get = vi.spyOn(http, 'get').mockImplementation(async (url) => ({ data: url === '/rooms/mine' ? [{ id: 99, type: 'private', display_name: '真实私人会话', member_count: 2, my_role: 'member' }] : [{ id: 99, room_id: 99, sender_id: 8, content: '真实私密正文', message_type: 'text', created_at: new Date().toISOString() }] }))
    vi.spyOn(http, 'post').mockResolvedValue({ data: {} })
    await appRouter.push('/chat'); await appRouter.isReady()
    const wrapper = render(App, { global: { plugins: [pinia, appRouter] } })
    await flushPromises()
    expect(wrapper.text()).toContain('真实私密正文')
    const realRequests = get.mock.calls.length
    await appRouter.push('/demo'); await flushPromises()
    expect(wrapper.text()).toContain('演示空间')
    expect(wrapper.text()).not.toContain('真实私密正文')
    expect(useRoomStore().rooms.some((room) => room.id === 99)).toBe(false)
    expect(useMessageStore().roomMessages[99]).toBeUndefined()
    expect(connections.length).toBeGreaterThan(0)
    connections.forEach((connection) => expect(connection.close).toHaveBeenCalled())
    expect(get.mock.calls.length).toBe(realRequests)
    auth.logout()
    expect(auth.token).toBe('real-token')
    expect(auth.user.username).toBe('真实用户')
    expect(useMessageStore().roomMessages).toEqual({})
  })
  it('群聊对话框可搜索、选人、创建，并能用Escape退出及返回原焦点', async () => {
    const wrapper = render(GroupRoomCreator)
    const trigger = wrapper.get('[aria-label="新建群聊"]')
    trigger.element.focus()
    await trigger.trigger('click')
    await flushPromises()
    expect(document.querySelector('[role="dialog"]').getAttribute('aria-modal')).toBe('true')
    expect(document.activeElement.id).toBe('group-name')
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))
    await flushPromises()
    expect(document.querySelector('[role="dialog"]')).toBeNull()
    expect(document.activeElement).toBe(trigger.element)
    await trigger.trigger('click')
    const name = document.getElementById('group-name')
    name.value = '读书会'; name.dispatchEvent(new Event('input'))
    const search = document.querySelector('[aria-label="搜索群成员"]')
    search.value = '陈予'; search.dispatchEvent(new Event('input'))
    document.querySelector('.search-btn').click()
    await flushPromises()
    document.querySelector('.result-item').click()
    await flushPromises()
    expect(document.querySelector('.create-group-submit').disabled).toBe(false)
    document.querySelector('.create-group-submit').click()
    await flushPromises()
    expect(wrapper.emitted('room-created')[0][0]).toBeGreaterThan(4)
    expect(document.querySelector('[role="dialog"]')).toBeNull()
    expect(readDemo().rooms.at(-1).display_name).toBe('读书会')
  })
  it('私聊创建复用已有会话并正常关闭对话框', async () => {
    const wrapper = render(PrivateRoomCreator)
    await wrapper.get('[aria-label="新建私聊"]').trigger('click')
    const search = document.querySelector('[aria-label="搜索用户"]')
    search.value = '陈予'; search.dispatchEvent(new Event('input'))
    document.querySelector('.search-btn').click()
    await flushPromises()
    document.querySelector('.result-item').click()
    await flushPromises()
    expect(wrapper.emitted('room-created')[0][0]).toBe(2)
    expect(document.querySelector('[role="dialog"]')).toBeNull()
  })
  it('共用聊天页面发送、回复、撤回、切换会话，全过程没有真实HTTP或WebSocket', async () => {
    const pinia = createPinia(); setActivePinia(pinia)
    useAuthStore().enterDemo()
    const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/demo', component: ChatView }] })
    await router.push('/demo'); await router.isReady()
    const get = vi.spyOn(http, 'get'); const post = vi.spyOn(http, 'post')
    const ws = vi.fn(); vi.stubGlobal('WebSocket', ws)
    const wrapper = render(ChatView, { global: { plugins: [pinia, router] } })
    await flushPromises()
    expect(wrapper.text()).toContain('演示空间')
    expect(wrapper.text()).toContain('Mango 工作室')
    const input = wrapper.get('[aria-label="消息内容"]')
    await input.setValue('很高兴见到大家')
    await input.trigger('keydown', { key: 'Enter', isComposing: true })
    expect(readDemo().messages.at(-1).content).not.toBe('很高兴见到大家')
    await wrapper.get('[aria-label="发送消息"]').trigger('click')
    await flushPromises()
    expect(readDemo().messages.at(-1).content).toBe('很高兴见到大家')
    const id = readDemo().messages.at(-1).id
    await wrapper.get(`[data-message-id="${id}"] .reply-btn`).trigger('click')
    await input.setValue('补充一句：下午见')
    await wrapper.get('[aria-label="发送消息"]').trigger('click')
    await flushPromises()
    expect(readDemo().messages.at(-1).reply_to_message_id).toBe(id)
    await wrapper.get(`[data-message-id="${id}"] .recall-btn`).trigger('click')
    await flushPromises()
    expect(wrapper.get(`[data-message-id="${id}"]`).text()).toContain('该消息已被撤回')
    await wrapper.findAll('.room-item').find((room) => room.text().includes('周末去走走')).trigger('click')
    await flushPromises()
    expect(wrapper.find('.image-attachment-preview').exists()).toBe(true)
    expect(get).not.toHaveBeenCalled(); expect(post).not.toHaveBeenCalled(); expect(ws).not.toHaveBeenCalled()
  })
})
