import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import api, { errorText } from '../lib/api'
import http from '../lib/http'
import { resetDemo } from '../lib/demo'
import { previewText, roleLabel, shouldSendOnEnter } from '../lib/messages'
import { useAuthStore } from '../stores/auth'
import { useRoomStore } from '../stores/room'
import { useMessageStore } from '../stores/message'
import { useComposer } from './useComposer'
import { useRoomSocket } from './useRoomSocket'

export function useChat() {
  const router = useRouter()
  const authStore = useAuthStore()
  const roomStore = useRoomStore()
  const messageStore = useMessageStore()
  const messageScrollRef = ref(null)
  const fileInputRef = ref(null)
  const sidebarOpen = ref(false)
  const recallingMessageId = ref(null)
  const activeJumpMessageId = ref(null)
  const isNearBottom = ref(true)
  const showScrollToBottom = ref(false)
  const hasUnreadIncoming = ref(false)
  const resettingDemo = ref(false)
  let jumpTimer
  let roomGeneration = 0
  let stopped = false
  const readThrough = new Map()
  const currentMessages = computed(() => messageStore.getMessagesByRoom(roomStore.selectedRoomId))
  const isCurrentRoomLoading = computed(() => messageStore.isRoomLoading(roomStore.selectedRoomId))
  const currentRoomError = computed(() => messageStore.errors[roomStore.selectedRoomId] || '')
  const userInitial = computed(() => (authStore.user?.username || 'M').charAt(0).toUpperCase())
  const composer = useComposer({ roomStore, messageStore, onSent: async () => { await scrollMessagesToBottom('smooth'); markRead() } })
  const { draftMessage, replyDraft, sendError, sending, uploading, canSend, clearReplyDraft, handleSendMessage, handleUploadAndSendAttachment } = composer
  const isMine = (message) => message.sender_id === authStore.user?.id
  const getSenderLabel = (message) => isMine(message) ? '我' : (message.sender_username || '成员')
  const getRoomInitial = (room) => (room.display_name || 'M').charAt(0)
  const canRecallMessage = (message) => !!message && !message.is_recalled && isMine(message)
  const canReplyMessage = (message) => !!message && !message.is_recalled
  const getMessageAttachments = (message) => Array.isArray(message?.attachments) ? message.attachments : []
  const getImageAttachments = (message) => getMessageAttachments(message).filter((item) => item.attachment_type === 'image')
  const getFileAttachments = (message) => getMessageAttachments(message).filter((item) => item.attachment_type === 'file')
  const getReplyTargetMessage = (message) => currentMessages.value.find((item) => item.id === message.reply_to_message_id) || message.replied_message || null
  const getReplyPreviewTitle = (message) => { const target = getReplyTargetMessage(message); return target ? `回复 ${getSenderLabel(target)}` : '回复消息' }
  const getReplyPreviewContent = (message) => previewText(getReplyTargetMessage(message))
  const composerPlaceholder = computed(() => '输入消息…')
  const socket = useRoomSocket({ token: () => authStore.demoMode ? '' : authStore.token, onConnecting: (roomId) => {
    const loaded = messageStore.getMessagesByRoom(roomId)
    return { afterId: loaded.at(-1)?.id, ids: loaded.map((message) => message.id), stick: isNearBottom.value }
  }, onConnected: async (roomId, recovery) => {
    const generation = roomGeneration
    try {
      await messageStore.syncAfter(roomId, recovery.afterId)
      await messageStore.reconcileLoaded(roomId, recovery.ids)
      if (generation === roomGeneration && roomId === roomStore.selectedRoomId) {
        if (recovery.stick) { await scrollMessagesToBottom(); markRead() }
        else { showScrollToBottom.value = true; hasUnreadIncoming.value = true }
      }
    } catch { /* The message pane exposes a retry action. */ }
  }, onMessage: handleRoomEvent, onUnauthorized: async () => {
    try { await api.get('/users/me'); await roomStore.fetchMyRooms() } catch { /* HTTP authentication handler handles expired sessions. */ }
  } })
  const userSocket = useRoomSocket({ token: () => authStore.demoMode ? '' : authStore.token, path: () => '/ws/users', onUnauthorized: () => api.get('/users/me').catch(() => {}), onConnected: () => handleRefreshRooms(), onMessage: async (payload) => {
    if (payload.event === 'room_created') { await handleRefreshRooms(); return }
    if (payload.event === 'room_updated') {
      const message = payload.data?.message
      if (message) roomStore.updateActivity(message, message.room_id !== roomStore.selectedRoomId && !isMine(message))
      if (!roomStore.rooms.some((room) => room.id === payload.data?.room_id)) await handleRefreshRooms()
    }
  } })
  const wsStatus = computed(() => authStore.demoMode ? 'connected' : socket.wsStatus.value)
  const wsStatusText = computed(() => authStore.demoMode ? '演示空间' : ({ connecting: '正在连接', connected: '实时连接', error: '正在恢复连接', closed: '正在恢复连接', idle: '连接未建立' }[wsStatus.value]))
  const wsStatusClass = computed(() => wsStatus.value)

  function markRead() {
    const roomId = roomStore.selectedRoomId
    const messageId = currentMessages.value.at(-1)?.id
    if (!messageId || (readThrough.get(roomId) || 0) >= messageId) return
    readThrough.set(roomId, messageId)
    roomStore.markRead(roomId, messageId).catch(() => { if (readThrough.get(roomId) === messageId) readThrough.delete(roomId) })
  }
  function updateScrollState() {
    const element = messageScrollRef.value
    isNearBottom.value = !element || element.scrollHeight - element.scrollTop - element.clientHeight < 80
    showScrollToBottom.value = !isNearBottom.value
    if (isNearBottom.value) { hasUnreadIncoming.value = false; markRead() }
  }
  async function scrollMessagesToBottom(behavior = 'auto') {
    await nextTick()
    messageScrollRef.value?.scrollTo({ top: messageScrollRef.value.scrollHeight, behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : behavior })
    isNearBottom.value = true; showScrollToBottom.value = false; hasUnreadIncoming.value = false
  }
  function handleMessageScroll() { updateScrollState() }
  function handleScrollToBottom() { scrollMessagesToBottom('smooth') }
  async function handleLoadOlder() {
    const roomId = roomStore.selectedRoomId
    const element = messageScrollRef.value
    const height = element?.scrollHeight || 0
    const top = element?.scrollTop || 0
    try {
      await messageStore.fetchOlder(roomId)
      await nextTick()
      if (roomId === roomStore.selectedRoomId && element) element.scrollTop = top + element.scrollHeight - height
    } catch { /* The history retry button stays available. */ }
  }
  function handleReplyMessage(message) {
    if (canReplyMessage(message)) replyDraft.value = { messageId: message.id, senderLabel: getSenderLabel(message), previewText: previewText(message) }
  }
  async function handleReplyPreviewClick(message) {
    const roomId = roomStore.selectedRoomId
    try {
      if (!currentMessages.value.some((item) => item.id === message.reply_to_message_id)) await messageStore.fetchContext(roomId, message.reply_to_message_id)
      if (roomId !== roomStore.selectedRoomId) return
      await nextTick()
      const target = messageScrollRef.value?.querySelector(`[data-message-id="${message.reply_to_message_id}"]`)
      if (target) {
        target.scrollIntoView({ block: 'center', behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' })
        clearTimeout(jumpTimer); activeJumpMessageId.value = message.reply_to_message_id
        jumpTimer = setTimeout(() => { activeJumpMessageId.value = null }, 1800)
      }
    } catch (error) { sendError.value = errorText(error, '原消息加载失败，请重试') }
  }
  async function handleRoomEvent(payload, roomId) {
    if (roomId !== roomStore.selectedRoomId) return
    if (payload.event === 'new_message' || payload.event === 'message_recalled') {
      const message = payload.data
      if (!message?.id) return
      const stick = isNearBottom.value || isMine(message)
      messageStore.appendOrUpdateMessage(roomId, message)
      roomStore.updateActivity(message)
      if (replyDraft.value?.messageId === message.id && message.is_recalled) clearReplyDraft()
      await nextTick()
      if (roomId !== roomStore.selectedRoomId) return
      if (stick) { await scrollMessagesToBottom(); markRead() }
      else { hasUnreadIncoming.value = true; showScrollToBottom.value = true }
    }
    if (payload.event === 'error') sendError.value = payload.data?.message || '连接出现问题，请重试'
  }
  async function loadCurrentRoomMessages() {
    const roomId = roomStore.selectedRoomId
    const generation = roomGeneration
    if (!roomId) return
    try {
      await messageStore.fetchRoomMessages(roomId)
      if (generation === roomGeneration && roomId === roomStore.selectedRoomId) { await scrollMessagesToBottom(); markRead() }
    } catch { /* Error is displayed by the message pane. */ }
  }
  async function handleRefreshRooms() { try { await roomStore.fetchMyRooms() } catch { /* The sidebar exposes retry. */ } }
  async function handleRoomCreated(roomId) { await handleRefreshRooms(); roomStore.selectRoom(roomId); sidebarOpen.value = false }
  function handleSelectRoom(roomId) { roomStore.selectRoom(roomId) }
  async function handleLogout() {
    socket.disconnect(); userSocket.disconnect(); roomGeneration++
    if (!authStore.demoMode) { try { await http.post('/auth/logout') } catch { /* Always allow local sign-out. */ } }
    roomStore.clearRooms(); messageStore.clearMessages(); authStore.logout(); router.push('/login')
  }
  function handleComposerKeydown(event) { if (shouldSendOnEnter(event)) { event.preventDefault(); handleSendMessage() } }
  function handleReconnect() { if (!authStore.demoMode) { socket.connect(roomStore.selectedRoomId); userSocket.connect('users') } }
  function handlePickFile() { if (!sending.value && !uploading.value && roomStore.selectedRoomId) fileInputRef.value?.click() }
  async function handleFileChange(event) {
    const file = event.target.files?.[0]
    if (!file) return
    try { await handleUploadAndSendAttachment(file) } finally { event.target.value = '' }
  }
  async function handleRecallMessage(message) {
    if (!canRecallMessage(message) || recallingMessageId.value) return
    recallingMessageId.value = message.id; sendError.value = ''
    try {
      const response = await api.post(`/messages/${message.id}/recall`)
      const returned = response.data.data || response.data
      const recalled = { ...message, ...returned, id: message.id, room_id: message.room_id, is_recalled: true, content: '', attachments: [] }
      messageStore.appendOrUpdateMessage(message.room_id, recalled)
      roomStore.updateActivity(recalled)
      if (replyDraft.value?.messageId === message.id) clearReplyDraft()
    } catch (error) { sendError.value = errorText(error, '撤回失败，请重试') }
    finally { recallingMessageId.value = null }
  }
  const refreshedImages = new WeakSet()
  async function refreshAttachment(attachment) {
    const response = await api.get(`/uploads/${attachment.upload_id}/access`)
    attachment.file_url = (response.data.data || response.data).file_url
    return attachment.file_url
  }
  async function handleImageError(attachment) {
    if (!attachment.upload_id || refreshedImages.has(attachment)) return
    refreshedImages.add(attachment)
    try { await refreshAttachment(attachment) } catch { sendError.value = '图片加载失败，请刷新消息' }
  }
  function handleImageLoad() { if (isNearBottom.value) scrollMessagesToBottom() }
  async function openAttachment(attachment) {
    const tab = window.open('about:blank', '_blank')
    if (tab) tab.opener = null
    try {
      const url = attachment.upload_id ? await refreshAttachment(attachment) : attachment.file_url
      if (url.startsWith('data:')) {
        tab?.close()
        const link = document.createElement('a'); link.href = url; link.download = attachment.original_name; link.click()
      } else if (tab) tab.location.href = url
      else { const link = document.createElement('a'); link.href = url; link.target = '_blank'; link.rel = 'noopener noreferrer'; link.click() }
    } catch (error) { tab?.close(); sendError.value = errorText(error, '附件打开失败，请重试') }
  }
  async function handleResetDemo() {
    resettingDemo.value = true
    readThrough.clear()
    resetDemo(); roomStore.clearRooms(); messageStore.clearMessages()
    await handleRefreshRooms()
    resettingDemo.value = false
  }
  function formatTime(isoString) {
    if (!isoString) return ''
    const date = new Date(isoString.endsWith('Z') || /[+-]\d\d:\d\d$/.test(isoString) ? isoString : `${isoString}Z`)
    return Number.isNaN(date.getTime()) ? '' : date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', hour12: false })
  }
  function formatFileSize(size) {
    const bytes = Number(size) || 0
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 ** 2) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / 1024 ** 2).toFixed(1)} MB`
  }
  watch(() => roomStore.selectedRoomId, (roomId) => {
    roomGeneration++; socket.disconnect(); activeJumpMessageId.value = null; clearTimeout(jumpTimer)
    isNearBottom.value = true; showScrollToBottom.value = false; hasUnreadIncoming.value = false
    if (roomId && !stopped) { loadCurrentRoomMessages(); if (!authStore.demoMode) socket.connect(roomId) }
  }, { flush: 'sync', immediate: true })
  onMounted(async () => { await handleRefreshRooms(); if (!authStore.demoMode && !stopped) userSocket.connect('users') })
  onBeforeUnmount(() => { stopped = true; roomGeneration++; clearTimeout(jumpTimer) })
  return { authStore, roomStore, messageStore, messageScrollRef, fileInputRef, sidebarOpen, recallingMessageId, activeJumpMessageId, currentMessages, isCurrentRoomLoading, currentRoomError, userInitial, wsStatus, wsStatusText, wsStatusClass, composerPlaceholder, showScrollToBottom, hasUnreadIncoming, resettingDemo, ...composer, roleLabel, previewText, getRoomInitial, isMine, getSenderLabel, canReplyMessage, canRecallMessage, getReplyTargetMessage, getReplyPreviewTitle, getReplyPreviewContent, getMessageAttachments, getImageAttachments, getFileAttachments, handleReplyMessage, handleReplyPreviewClick, handleMessageScroll, handleScrollToBottom, handleLoadOlder, loadCurrentRoomMessages, handleRefreshRooms, handlePrivateRoomCreated: handleRoomCreated, handleGroupRoomCreated: handleRoomCreated, handleSelectRoom, handleLogout, handleComposerKeydown, handleReconnect, handlePickFile, handleFileChange, handleRecallMessage, handleResetDemo, handleImageError, handleImageLoad, openAttachment, formatTime, formatFileSize }
}
