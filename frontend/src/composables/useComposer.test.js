import { afterEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h, reactive } from 'vue'
import { mount } from '@vue/test-utils'
import api from '../lib/api'
import { useComposer } from './useComposer'

const wrappers = []
function setup() {
  const roomStore = reactive({ selectedRoomId: 1, updateActivity: vi.fn() })
  const messageStore = { appendOrUpdateMessage: vi.fn() }
  let composer
  wrappers.push(mount(defineComponent({ setup() { composer = useComposer({ roomStore, messageStore }); return () => h('div') } })))
  return { composer, roomStore, messageStore }
}
afterEach(() => { wrappers.splice(0).forEach((wrapper) => wrapper.unmount()) })

describe('发送任务', () => {
  it('连续发送仅提交一次，确认保留用户刚输入的下一条草稿', async () => {
    let resolve
    const post = vi.spyOn(api, 'post').mockImplementation(() => new Promise((done) => { resolve = done }))
    const { composer } = setup()
    composer.draftMessage.value = '第一条'
    const sending = composer.handleSendMessage()
    await composer.handleSendMessage()
    expect(post).toHaveBeenCalledTimes(1)
    composer.draftMessage.value = '第二条'
    resolve({ data: { data: { id: 1, room_id: 1, content: '第一条' } } })
    await sending
    expect(composer.draftMessage.value).toBe('第二条')
    expect(composer.sending.value).toBe(false)
  })
  it('失败重试使用同一client_message_id', async () => {
    const post = vi.spyOn(api, 'post').mockRejectedValueOnce(new Error('Network Error')).mockResolvedValueOnce({ data: { data: { id: 1, room_id: 1 } } })
    const { composer } = setup()
    composer.draftMessage.value = '同一条消息'
    await composer.handleSendMessage()
    expect(composer.failedTask.value).toBeTruthy()
    await composer.retryFailedMessage()
    expect(post.mock.calls[0][1].client_message_id).toBe(post.mock.calls[1][1].client_message_id)
    expect(composer.failedTask.value).toBeNull()
  })
  it('切换房间立即取消上传，即使返回成功也不会发送至任何房间', async () => {
    let resolve
    const post = vi.spyOn(api, 'post').mockImplementation(() => new Promise((done) => { resolve = done }))
    const { composer, roomStore } = setup()
    const upload = composer.handleUploadAndSendAttachment(new File(['hello'], 'hello.txt', { type: 'text/plain' }))
    const signal = post.mock.calls[0][2].signal
    roomStore.selectedRoomId = 2
    expect(signal.aborted).toBe(true)
    resolve({ data: { data: { upload_id: 'upload1', attachment_type: 'file' } } })
    await upload
    expect(post).toHaveBeenCalledTimes(1)
    expect(composer.uploading.value).toBe(false)
  })
  it('发送期间换房间时，结果仅写入原房间并保留新房间草稿', async () => {
    let resolve
    vi.spyOn(api, 'post').mockImplementation(() => new Promise((done) => { resolve = done }))
    const { composer, roomStore, messageStore } = setup()
    composer.draftMessage.value = '发给房间一'
    const sent = composer.handleSendMessage()
    roomStore.selectedRoomId = 2
    composer.draftMessage.value = '房间二草稿'
    resolve({ data: { data: { id: 3, room_id: 1 } } })
    await sent
    expect(messageStore.appendOrUpdateMessage.mock.calls[0][0]).toBe(1)
    expect(composer.draftMessage.value).toBe('房间二草稿')
    roomStore.selectedRoomId = 1
    expect(composer.draftMessage.value).toBe('')
  })
  it('认证或演示模式切换清空store后，迟到发送结果不能恢复真实缓存', async () => {
    let resolve
    vi.spyOn(api, 'post').mockImplementation(() => new Promise((done) => { resolve = done }))
    const { composer, messageStore } = setup()
    messageStore.generation = 1
    composer.draftMessage.value = '真实消息'
    const sent = composer.handleSendMessage()
    messageStore.generation++
    resolve({ data: { data: { id: 3, room_id: 1 } } })
    await sent
    expect(messageStore.appendOrUpdateMessage).not.toHaveBeenCalled()
  })
})
