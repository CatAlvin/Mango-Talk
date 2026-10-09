import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import api from '../lib/api'
import { useMessageStore } from './message'
import { mergeMessages, shouldSendOnEnter } from '../lib/messages'

beforeEach(() => { setActivePinia(createPinia()); sessionStorage.clear() })

describe('消息一致性', () => {
  it('历史请求返回时保留已先收到的实时消息，按ID去重排序', async () => {
    let resolve
    vi.spyOn(api, 'get').mockImplementation(() => new Promise((done) => { resolve = done }))
    const store = useMessageStore()
    const loading = store.fetchRoomMessages(3)
    store.appendOrUpdateMessage(3, { id: 62, content: '实时消息' })
    resolve({ data: [{ id: 60 }, { id: 61 }] })
    await loading
    store.appendOrUpdateMessage(3, { id: 61, content: '更新' })
    expect(store.getMessagesByRoom(3).map((message) => message.id)).toEqual([60, 61, 62])
  })
  it('退出后迟到的历史请求不会恢复前一个用户的数据', async () => {
    let resolve
    vi.spyOn(api, 'get').mockImplementation(() => new Promise((done) => { resolve = done }))
    const store = useMessageStore()
    const loading = store.fetchRoomMessages(1)
    store.clearMessages()
    resolve({ data: [{ id: 1, content: '私密消息' }] })
    await loading
    expect(store.roomMessages).toEqual({})
  })
  it('重连分批补齐超过100条消息', async () => {
    const get = vi.spyOn(api, 'get')
    get.mockResolvedValueOnce({ data: Array.from({ length: 100 }, (_, i) => ({ id: i + 2 })) })
    get.mockResolvedValueOnce({ data: [{ id: 102 }] })
    const store = useMessageStore()
    store.appendOrUpdateMessage(1, { id: 1 })
    await store.syncAfter(1)
    expect(store.getMessagesByRoom(1)).toHaveLength(102)
    expect(get.mock.calls[1][1].params.after_id).toBe(101)
  })
  it('连接前的恢复游标不受先到达的新实时消息影响', async () => {
    const get = vi.spyOn(api, 'get').mockResolvedValue({ data: [{ id: 2 }, { id: 3 }, { id: 4 }] })
    const store = useMessageStore()
    store.appendOrUpdateMessage(1, { id: 1 })
    const recoveryCursor = 1
    store.appendOrUpdateMessage(1, { id: 4 })
    await store.syncAfter(1, recoveryCursor)
    expect(get.mock.calls[0][1].params.after_id).toBe(1)
    expect(store.getMessagesByRoom(1).map((message) => message.id)).toEqual([1, 2, 3, 4])
  })
  it('原消息定位补齐较早窗口和现有窗口之间的空档', async () => {
    const get = vi.spyOn(api, 'get')
    get.mockResolvedValueOnce({ data: Array.from({ length: 50 }, (_, i) => ({ id: i + 1 })) })
    get.mockResolvedValueOnce({ data: Array.from({ length: 100 }, (_, i) => ({ id: i + 51 })) })
    get.mockResolvedValueOnce({ data: Array.from({ length: 100 }, (_, i) => ({ id: i + 151 })) })
    const store = useMessageStore()
    store.merge(1, Array.from({ length: 50 }, (_, i) => ({ id: i + 201 })))
    await store.fetchContext(1, 25)
    expect(store.getMessagesByRoom(1).map((message) => message.id)).toEqual(Array.from({ length: 250 }, (_, i) => i + 1))
  })
  it('离线撤回刷新全部已加载ID，旧快照无法恢复撤回正文', async () => {
    const post = vi.spyOn(api, 'post').mockImplementation(async (_url, body) => ({ data: body.ids.map((id) => ({ id, is_recalled: id === 1 })) }))
    const store = useMessageStore()
    store.merge(1, Array.from({ length: 250 }, (_, i) => ({ id: i + 1, content: '正文', attachments: [] })))
    await store.reconcileLoaded(1, store.getMessagesByRoom(1).map((message) => message.id))
    expect(post.mock.calls.map((call) => call[1].ids.length)).toEqual([200, 50])
    store.merge(1, [{ id: 1, is_recalled: false, content: '迟到的旧正文' }])
    expect(store.getMessagesByRoom(1)[0]).toMatchObject({ is_recalled: true, content: '', attachments: [] })
  })
  it('撤回清理正文附件与已有回复摘要', () => {
    const messages = mergeMessages([{ id: 1, content: '原文', attachments: [{ file_url: 'private' }] }, { id: 2, reply_to_message_id: 1, replied_message: { id: 1, content: '原文' } }], [{ id: 1, is_recalled: true }])
    expect(messages[0].content).toBe(''); expect(messages[0].attachments).toEqual([])
    expect(messages[1].replied_message.is_recalled).toBe(true); expect(messages[1].replied_message.content).toBe('')
  })
  it('输入法确认、长按与换行不会发送', () => {
    expect(shouldSendOnEnter({ key: 'Enter', isComposing: true })).toBe(false)
    expect(shouldSendOnEnter({ key: 'Enter', keyCode: 229 })).toBe(false)
    expect(shouldSendOnEnter({ key: 'Enter', repeat: true })).toBe(false)
    expect(shouldSendOnEnter({ key: 'Enter', shiftKey: true })).toBe(false)
    expect(shouldSendOnEnter({ key: 'Enter' })).toBe(true)
  })
})
