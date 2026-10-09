import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { mount } from '@vue/test-utils'
import { useRoomSocket } from './useRoomSocket'

let wrapper
let instances
class FakeSocket {
  static OPEN = 1
  constructor(url) { this.url = url; this.readyState = 0; this.send = vi.fn(); instances.push(this) }
  open() { this.readyState = 1; this.onopen?.() }
  close() { this.readyState = 3; this.onclose?.({ code: 1000 }) }
}
beforeEach(() => { vi.useFakeTimers(); instances = []; vi.stubGlobal('WebSocket', FakeSocket) })
afterEach(() => { wrapper?.unmount(); vi.useRealTimers(); vi.unstubAllGlobals() })
function setup(options = {}) {
  let socket
  wrapper = mount(defineComponent({ setup() { socket = useRoomSocket({ token: () => 'token', onMessage: vi.fn(), onConnected: vi.fn(), ...options }); return () => h('div') } }))
  return socket
}
describe('实时连接恢复', () => {
  it('快速切换房间后旧连接的打开、消息和关闭事件全部失效', () => {
    const onMessage = vi.fn(); const onConnected = vi.fn()
    const socket = setup({ onMessage, onConnected })
    socket.connect(1); const old = instances[0]
    socket.connect(2); const current = instances[1]
    old.open(); old.onmessage({ data: JSON.stringify({ event: 'new_message', data: { id: 9 } }) }); old.onclose({ code: 1006 })
    expect(socket.wsStatus.value).toBe('connecting')
    expect(onMessage).not.toHaveBeenCalled(); expect(onConnected).not.toHaveBeenCalled()
    current.open()
    expect(onConnected.mock.calls[0][0]).toBe(2)
    expect(socket.wsStatus.value).toBe('connected')
    vi.advanceTimersByTime(1000)
    expect(instances).toHaveLength(2)
  })
  it('打开连接前已捕获恢复游标，断开后自动退避重连', () => {
    let cursor = 50
    const onConnected = vi.fn()
    const socket = setup({ onConnecting: () => ({ cursor }), onConnected })
    socket.connect(1)
    cursor = 99
    instances[0].open()
    expect(onConnected.mock.calls[0][1].cursor).toBe(50)
    instances[0].onclose({ code: 1006 })
    vi.advanceTimersByTime(999); expect(instances).toHaveLength(1)
    vi.advanceTimersByTime(1); expect(instances).toHaveLength(2)
    expect(instances[1].url).toContain('/ws/rooms/1')
  })
  it('心跳发送ping，未收到pong会重新建立连接；卸载会清除定时器', () => {
    const socket = setup()
    socket.connect(1); instances[0].open()
    vi.advanceTimersByTime(20000)
    expect(instances[0].send).toHaveBeenCalledWith(JSON.stringify({ action: 'ping' }))
    vi.advanceTimersByTime(60000)
    expect(socket.wsStatus.value).toBe('closed')
    vi.advanceTimersByTime(1000)
    expect(instances).toHaveLength(2)
    wrapper.unmount(); wrapper = null
    vi.advanceTimersByTime(120000)
    expect(instances).toHaveLength(2)
  })
})
