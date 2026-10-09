export function mergeMessages(current, incoming) {
  const items = new Map(current.map((message) => [message.id, message]))
  for (const message of incoming) {
    const previous = items.get(message.id)
    const merged = { ...previous, ...message }
    if (previous?.is_recalled) merged.is_recalled = true
    if (merged.is_recalled) { merged.content = ''; merged.attachments = [] }
    items.set(message.id, merged)
  }
  return [...items.values()].sort((a, b) => a.id - b.id).map((message) => {
    const target = items.get(message.reply_to_message_id)
    if (target?.is_recalled) return { ...message, replied_message: { ...target, content: '', attachments: [] } }
    return message
  })
}

export const roleLabel = (role) => ({ owner: '群主', admin: '管理员', member: '成员', user: '成员' }[role] || '成员')
export function previewText(message) {
  if (!message) return '开始新的对话'
  if (message.is_recalled) return '消息已撤回'
  if (message.message_type === 'image') return message.content || '[图片]'
  if (message.message_type === 'file') return message.content || `[文件] ${message.attachments?.[0]?.original_name || ''}`
  return message.content || '新消息'
}

export function shouldSendOnEnter(event) {
  return event.key === 'Enter' && !event.shiftKey && !event.isComposing && event.keyCode !== 229 && !event.repeat
}
