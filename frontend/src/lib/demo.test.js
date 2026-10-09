import { beforeEach, describe, expect, it, vi } from 'vitest'
import api from './api'
import http, { TOKEN_KEY, USER_KEY } from './http'
import { DEMO_ACTIVE_KEY, DEMO_DATA_KEY, resetDemo, readDemo, demoRequest } from './demo'

beforeEach(() => { localStorage.clear(); sessionStorage.clear(); sessionStorage.setItem(DEMO_ACTIVE_KEY, 'true'); resetDemo() })

describe('演示空间', () => {
  it('创建、发送、撤回和未知请求均不会触及真实服务或认证数据', async () => {
    localStorage.setItem(TOKEN_KEY, 'real-account-token')
    localStorage.setItem(USER_KEY, '{"id":99,"username":"真实用户"}')
    const get = vi.spyOn(http, 'get')
    const post = vi.spyOn(http, 'post')
    const created = await api.post('/rooms/group', { name: '读书会', member_user_ids: [2], description: '每周一本书' })
    const roomId = created.data.room.id
    const response = await api.post('/messages', { room_id: roomId, content: '晚上好', message_type: 'text', client_message_id: crypto.randomUUID(), attachments: [] })
    await api.post(`/messages/${response.data.id}/recall`)
    await expect(api.get('/unknown')).rejects.toThrow()
    expect(get).not.toHaveBeenCalled(); expect(post).not.toHaveBeenCalled()
    expect(localStorage.getItem(TOKEN_KEY)).toBe('real-account-token')
    expect(localStorage.getItem(USER_KEY)).toContain('真实用户')
    expect(readDemo().messages.at(-1)).toMatchObject({ is_recalled: true, content: '', attachments: [] })
  })
  it('最新页、较早页与增量页按游标连续返回，重复发送幂等', async () => {
    const latest = (await api.get('/messages/room/1', { params: { limit: 50 } })).data
    const older = (await api.get('/messages/room/1', { params: { before_id: latest[0].id, limit: 50 } })).data
    expect(latest).toHaveLength(50)
    const ids = [...older, ...latest].map((message) => message.id)
    expect(new Set(ids).size).toBe(readDemo().messages.filter((message) => message.room_id === 1).length)
    expect(ids).toEqual([...ids].sort((a, b) => a - b))
    const task = { room_id: 1, content: '明天见', message_type: 'text', client_message_id: crypto.randomUUID(), attachments: [] }
    const first = (await api.post('/messages', task)).data
    const retry = (await api.post('/messages', task)).data
    expect(retry.id).toBe(first.id)
    expect((await api.get('/messages/room/1', { params: { after_id: latest.at(-1).id } })).data).toHaveLength(1)
  })
  it('回复摘要跟随原消息撤回，并保存用户的操作', async () => {
    const original = readDemo().messages.find((message) => message.room_id === 1 && message.sender_id === 1)
    const reply = (await demoRequest('post', '/messages', { room_id: 1, content: '回复', message_type: 'text', client_message_id: crypto.randomUUID(), reply_to_message_id: original.id, attachments: [] })).data
    await api.post(`/messages/${original.id}/recall`)
    const messages = (await api.get('/messages/room/1', { params: { limit: 100 } })).data
    expect(messages.find((message) => message.id === reply.id).replied_message).toMatchObject({ content: '', is_recalled: true, attachments: [] })
    expect(JSON.parse(localStorage.getItem(DEMO_DATA_KEY)).messages.at(-1).id).toBe(reply.id)
    resetDemo()
    expect(readDemo().messages.some((message) => message.client_message_id === reply.client_message_id)).toBe(false)
  })
})
