import { computed, onBeforeUnmount, ref, watch } from 'vue'
import api, { errorText } from '../lib/api'

export function useComposer({ roomStore, messageStore, onSent = () => {} }) {
  const draftMessage = ref('')
  const replyDraft = ref(null)
  const sendError = ref('')
  const sending = ref(false)
  const uploading = ref(false)
  const uploadProgress = ref(0)
  const failedTask = ref(null)
  const drafts = new Map()
  const failures = new Map()
  let uploadController
  let epoch = 0
  let disposed = false
  const canSend = computed(() => !!roomStore.selectedRoomId && !!draftMessage.value.trim() && !sending.value && !uploading.value)
  const clearReplyDraft = () => { replyDraft.value = null }

  watch(() => roomStore.selectedRoomId, (roomId, previousId) => {
    epoch++
    uploadController?.abort()
    uploadController = null
    if (previousId) drafts.set(previousId, { content: draftMessage.value, reply: replyDraft.value })
    const draft = drafts.get(roomId)
    draftMessage.value = draft?.content || ''
    replyDraft.value = draft?.reply || null
    failedTask.value = failures.get(roomId) || null
    sending.value = false; uploading.value = false; sendError.value = failedTask.value ? '消息发送失败，请重试' : ''
  }, { flush: 'sync' })

  function createTask(attachments = [], roomId = roomStore.selectedRoomId) {
    return { client_message_id: crypto.randomUUID(), room_id: roomId, content: draftMessage.value.trim(), message_type: attachments.length ? attachments[0].attachment_type : 'text', reply_to_message_id: replyDraft.value?.messageId || null, attachments: attachments.map((item) => ({ upload_id: item.upload_id })), snapshot: draftMessage.value, replySnapshot: replyDraft.value?.messageId || null }
  }

  async function sendTask(task, taskEpoch = epoch) {
    if (sending.value || disposed || task.room_id !== roomStore.selectedRoomId || taskEpoch !== epoch) return
    const dataGeneration = messageStore.generation
    sending.value = true; sendError.value = ''
    try {
      const { snapshot, replySnapshot, ...body } = task
      const response = await api.post('/messages', body)
      if (disposed || dataGeneration !== messageStore.generation) return
      const message = response.data.data || response.data
      messageStore.appendOrUpdateMessage(task.room_id, message)
      roomStore.updateActivity(message)
      failures.delete(task.room_id)
      if (taskEpoch === epoch) {
        failedTask.value = null
        if (draftMessage.value === snapshot) draftMessage.value = ''
        if (replyDraft.value?.messageId === replySnapshot) clearReplyDraft()
        await onSent(message)
      } else {
        const draft = drafts.get(task.room_id)
        if (draft?.content === snapshot) draft.content = ''
        if (draft?.reply?.messageId === replySnapshot) draft.reply = null
      }
    } catch (error) {
      if (disposed || dataGeneration !== messageStore.generation) return
      failures.set(task.room_id, task)
      if (taskEpoch === epoch) {
        failedTask.value = task
        sendError.value = errorText(error, '消息发送失败，请重试')
      }
    } finally { if (!disposed && taskEpoch === epoch) sending.value = false }
  }

  async function handleSendMessage() {
    if (!canSend.value) return
    const task = failedTask.value
    if (task && task.snapshot === draftMessage.value && task.replySnapshot === (replyDraft.value?.messageId || null) && !task.attachments.length) await sendTask(task)
    else await sendTask(createTask())
  }
  async function retryFailedMessage() { if (failedTask.value && !sending.value && !uploading.value) await sendTask(failedTask.value) }
  function discardFailedMessage() { failures.delete(roomStore.selectedRoomId); failedTask.value = null; sendError.value = '' }

  async function handleUploadAndSendAttachment(file) {
    if (sending.value || uploading.value || !roomStore.selectedRoomId) return
    if (!file.size) { sendError.value = '请选择有内容的文件'; return }
    if (file.size > 50 * 1024 * 1024) { sendError.value = '文件大小不能超过 50 MB'; return }
    const task = createTask()
    const taskEpoch = epoch
    const controller = new AbortController()
    uploadController = controller
    uploading.value = true; uploadProgress.value = 0; sendError.value = ''
    try {
      const formData = new FormData()
      formData.append('file', file)
      const response = await api.post('/uploads', formData, { timeout: 120000, signal: controller.signal, onUploadProgress: (event) => { if (event.total && taskEpoch === epoch) uploadProgress.value = Math.round(event.loaded / event.total * 100) } })
      if (controller.signal.aborted || disposed || taskEpoch !== epoch || task.room_id !== roomStore.selectedRoomId) return
      const attachment = response.data.data || response.data
      task.attachments = [{ upload_id: attachment.upload_id }]
      task.message_type = attachment.attachment_type
      uploading.value = false
      await sendTask(task, taskEpoch)
    } catch (error) {
      if (!controller.signal.aborted && taskEpoch === epoch && !disposed) sendError.value = errorText(error, '文件上传失败，请重新选择文件')
    } finally {
      if (taskEpoch === epoch && !disposed) { uploading.value = false; uploadController = null }
    }
  }
  onBeforeUnmount(() => { disposed = true; epoch++; uploadController?.abort() })
  return { draftMessage, replyDraft, sendError, sending, uploading, uploadProgress, failedTask, canSend, clearReplyDraft, handleSendMessage, retryFailedMessage, discardFailedMessage, handleUploadAndSendAttachment }
}
