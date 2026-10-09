import { onBeforeUnmount, ref } from 'vue'

export function useRoomSocket({ token, onMessage, onConnected, onConnecting, onUnauthorized, path = (roomId) => `/ws/rooms/${roomId}` }) {
  const wsStatus = ref('idle')
  let ws
  let reconnectTimer
  let heartbeatTimer
  let generation = 0
  let retries = 0
  let disposed = false
  let selectedRoomId
  let lastPong = 0
  const current = (connection, attempt) => !disposed && ws === connection && generation === attempt
  function clearTimers() { clearTimeout(reconnectTimer); clearInterval(heartbeatTimer) }
  function disconnect() {
    generation++; clearTimers()
    const previous = ws; ws = null; previous?.close()
    wsStatus.value = 'idle'
  }
  function connect(roomId, retry = false) {
    if (disposed) return
    const attempt = ++generation
    clearTimers()
    const previous = ws; ws = null; previous?.close()
    selectedRoomId = roomId
    if (!retry) retries = 0
    if (!roomId || !token()) { wsStatus.value = 'idle'; return }
    const recovery = onConnecting?.(roomId)
    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const connection = new WebSocket(`${protocol}://${window.location.host}${path(roomId)}?token=${encodeURIComponent(token())}`)
    ws = connection; wsStatus.value = 'connecting'
    connection.onopen = () => {
      if (!current(connection, attempt)) return
      retries = 0; wsStatus.value = 'connected'; lastPong = Date.now()
      Promise.resolve(onConnected(roomId, recovery)).catch(() => {})
      heartbeatTimer = setInterval(() => {
        if (!current(connection, attempt)) return
        if (Date.now() - lastPong > 60000) { connection.close(); return }
        if (connection.readyState === WebSocket.OPEN) connection.send(JSON.stringify({ action: 'ping' }))
      }, 20000)
    }
    connection.onmessage = (event) => {
      if (!current(connection, attempt)) return
      try {
        const payload = JSON.parse(event.data)
        if (payload.event === 'pong') { lastPong = Date.now(); return }
        Promise.resolve(onMessage(payload, roomId)).catch(() => {})
      } catch { /* Ignore malformed events without interrupting recovery. */ }
    }
    connection.onerror = () => { if (current(connection, attempt)) wsStatus.value = 'error' }
    connection.onclose = (event) => {
      if (!current(connection, attempt)) return
      clearInterval(heartbeatTimer); ws = null
      if ([1008, 4401, 4403].includes(event.code)) { wsStatus.value = 'closed'; onUnauthorized?.(); return }
      wsStatus.value = 'closed'
      reconnectTimer = setTimeout(() => connect(selectedRoomId, true), Math.min(1000 * 2 ** retries++, 30000))
    }
  }
  function online() { if (selectedRoomId && wsStatus.value !== 'connected') connect(selectedRoomId) }
  window.addEventListener('online', online)
  onBeforeUnmount(() => { disposed = true; disconnect(); window.removeEventListener('online', online) })
  return { wsStatus, connect, disconnect }
}
