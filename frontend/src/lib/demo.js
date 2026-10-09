export const DEMO_ACTIVE_KEY = 'mango_talk_demo_active'
export const DEMO_DATA_KEY = 'mango_talk_demo_v1'
export const DEMO_USER = { id: 1, username: '林间', role: 'user' }

const people = [DEMO_USER, { id: 2, username: '陈予', phone: '138****0521' }, { id: 3, username: '许知夏', phone: '139****0718' }, { id: 4, username: '周舟', phone: '136****1130' }, { id: 5, username: '宋青', phone: '137****0916' }]
const clone = (value) => JSON.parse(JSON.stringify(value))
export const isDemoActive = () => sessionStorage.getItem(DEMO_ACTIVE_KEY) === 'true'
let memory = null

function seed() {
  const rooms = [
    { id: 1, type: 'group', display_name: 'Mango 工作室', name: 'Mango 工作室', description: '秋日市集筹备小组', member_count: 5, my_role: 'owner', member_ids: [1, 2, 3, 4, 5], unread_count: 0 },
    { id: 2, type: 'private', display_name: '陈予', member_count: 2, my_role: 'member', member_ids: [1, 2], unread_count: 2 },
    { id: 3, type: 'group', display_name: '周末去走走', name: '周末去走走', description: '山野、海风和好天气', member_count: 3, my_role: 'member', member_ids: [1, 3, 4], unread_count: 1 },
    { id: 4, type: 'private', display_name: '许知夏', member_count: 2, my_role: 'member', member_ids: [1, 3], unread_count: 1 },
  ]
  const messages = []
  const base = new Date(Date.now() - 80 * 180000)
  rooms.forEach((room) => { room.created_at = new Date(base.getTime() - 48 * 3600000).toISOString() })
  function add(roomId, senderId, content, extras = {}) {
    const message = { id: messages.length + 1, room_id: roomId, sender_id: senderId, sender_username: people.find((person) => person.id === senderId).username, message_type: 'text', content, attachments: [], is_recalled: false, created_at: new Date(base.getTime() + messages.length * 180000).toISOString(), ...extras }
    if (message.reply_to_message_id) message.replied_message = clone(messages.find((item) => item.id === message.reply_to_message_id))
    messages.push(message)
    return message.id
  }
  const history = [
    [2, '秋日市集的摊位确定了，我们在靠银杏树的那一排。'],
    [3, '那个位置不错，下午光线应该很好。'],
    [1, '我周三去看场地，顺便量一下桌子的尺寸。'],
    [4, '主办方给的是两张一米二的桌子，可以拼起来。'],
    [5, '我想带几束干花，放在价目牌旁边。'],
    [2, '好，桌布用米白色吧，和橙色的海报也搭。'],
    [3, '海报上的手绘小芒果已经画好了，今晚发给大家。'],
    [1, '先留一个角放店名，别被桌上的东西挡住。'],
    [4, '摊位背面有挂钩，可以挂一张竖版。'],
    [5, '那我准备两根细木杆，挂起来不容易卷边。'],
    [2, '咖啡店那边同意借我们一个保温桶。'],
    [1, '太好了，热饮的事有着落了。'],
    [3, '菜单暂定芒果气泡水和桂花拿铁，大家觉得呢？'],
    [4, '两种就够了，现场做起来也方便。'],
    [5, '桂花可以分装成小袋，免得临时找量勺。'],
    [2, '我问了印刷店，海报要周四中午前给文件。'],
    [3, '收到，我周三晚上把两版都整理好。'],
    [1, '纸张选厚一点的，户外放一天不会太软。'],
    [4, '主办方说不能打钉子，记得带无痕胶。'],
    [5, '我有一卷，连剪刀一起带过去。'],
    [2, '杯子到了，试了一下，装热饮握着也不烫。'],
    [1, '杯盖能扣紧吗？路过的人可能会拿着走。'],
    [2, '可以，我装水摇过了，没有漏。'],
    [3, '贴纸印五百张是不是有点多？'],
    [4, '三百张差不多，多的下次也能用。'],
    [5, '想留几张贴在包装袋上，别全送光了。'],
    [1, '那就三百张，打包用和赠送用各留一些。'],
    [2, '周三拍菜单照片，咖啡店早上十点开门。'],
    [3, '我十点半到，带相机和那块木色背景板。'],
    [4, '我去买新鲜芒果，挑熟一点的。'],
    [5, '需要冰块吗？楼下便利店有卖。'],
    [1, '需要两袋，拍气泡水的时候再拆。'],
    [3, '今天窗边的光很软，正好不用补光灯。'],
    [2, '我把桌上的杯子和托盘擦好了。'],
    [4, '芒果买到了，还有一小袋桂花。'],
    [5, '十分钟后到，我顺路买了几块可颂。'],
    [1, '别忘了先吃点东西，我们可能要拍到一点。'],
    [3, '照片拍完了，有一张气泡冒起来的特别好看。'],
    [2, '那张可以做菜单封面，颜色很干净。'],
    [4, '剩下的果汁已经被我们喝完了，味道通过。'],
    [5, '桂花拿铁也好喝，周末应该会受欢迎。'],
    [1, '场地看过了，插座在右侧柱子上。'],
    [4, '我带一个五米的插线板，够用了。'],
    [2, '周六八点半可以进场，十点正式开始。'],
    [3, '我坐地铁，八点二十能到入口。'],
    [5, '我和周舟开车过去，把重的东西放我们车上。'],
    [1, '好，大家在北门集合，我拿着摊位证。'],
    [2, '物料清单已经核过一遍，今晚再看看海报。'],
  ]
  history.forEach(([senderId, content], index) => add(1, senderId, content, { created_at: new Date(base.getTime() - (48 - index) * 3600000).toISOString() }))
  add(1, 2, '印刷店确认收到文件了，周五下午可以取。')
  const question = add(1, 3, '海报标题用“把秋天装进杯子”，下面配那张桂花拿铁的照片，怎么样？')
  add(1, 1, '我喜欢这句，读起来很有画面。照片也用那张吧。', { reply_to_message_id: question })
  add(1, 4, '周五下午三点一起清点物料，大家有空吗？')
  add(1, 5, '有空，我把桌布和干花一起带过去。')
  add(1, 2, '整理好的物料和时间表在这里，看看有没有漏的。', { message_type: 'file', attachments: [{ id: 1, upload_id: 'demo-notes', attachment_type: 'file', original_name: '秋日市集准备清单.txt', mime_type: 'text/plain', file_size: 450, file_url: '/demo/workshop-notes.txt' }] })
  add(1, 1, '三点见，我带些咖啡。')
  add(2, 2, '林间，海报的钱我先垫了，一共一百八十元。')
  add(2, 1, '好，我记到账本上，周末结束后一起结算。')
  add(2, 2, '店里还送了我们几张小样，纸质不错。')
  const reply = add(2, 2, '你下午方便陪我去取吗？两卷海报有点难拿。')
  add(2, 1, '没问题，取完正好一起回工作室。', { reply_to_message_id: reply })
  add(2, 2, '那我两点半在楼下等你 ☕')
  add(3, 4, '周末天气不错，要不要去海边？')
  add(3, 3, '想去！上次那条沿海步道还没走完。')
  add(3, 4, '上次拍的照片，风景真的很好。', { message_type: 'image', attachments: [{ id: 2, upload_id: 'demo-coast', attachment_type: 'image', original_name: '海边的午后.svg', mime_type: 'image/svg+xml', file_size: 1980, file_url: '/demo/coast.svg' }] })
  add(3, 1, '那就周六早上出发，我带咖啡。')
  add(3, 3, '我带相机，九点地铁站见。')
  add(4, 3, '这周辛苦了，记得早点休息。')
  add(4, 1, '谢谢！周末出去走走，正好换换心情。')
  add(4, 3, '刚发现一家不错的咖啡店，回来一起去。')
  return { version: 1, rooms, messages, uploads: [], selectedRoomId: 1 }
}

export function readDemo() {
  if (memory) return memory
  try {
    const stored = JSON.parse(localStorage.getItem(DEMO_DATA_KEY))
    if (stored?.version === 1 && Array.isArray(stored.rooms) && Array.isArray(stored.messages)) memory = stored
  } catch { /* Replace invalid local state with a fresh workspace. */ }
  memory ||= seed()
  return memory
}
function persist() {
  try { localStorage.setItem(DEMO_DATA_KEY, JSON.stringify(memory)) } catch { throw new Error('浏览器存储空间不足，请清理后重试') }
}
export function resetDemo() { memory = seed(); persist(); return clone(memory) }
export function setDemoSelection(roomId) { readDemo().selectedRoomId = roomId; persist() }
export function demoRooms() {
  const state = readDemo()
  return clone(state.rooms.map((room) => {
    const last = state.messages.filter((message) => message.room_id === room.id).at(-1)
    const lastActivity = last?.created_at || room.created_at
    return { ...room, last_message: last, last_activity_at: lastActivity, updated_at: lastActivity }
  }).sort((a, b) => new Date(b.last_activity_at) - new Date(a.last_activity_at)))
}
function serialize(message) {
  const result = clone(message)
  if (result.is_recalled) { result.content = ''; result.attachments = [] }
  if (result.reply_to_message_id) {
    const target = readDemo().messages.find((item) => item.id === result.reply_to_message_id)
    if (target) {
      result.replied_message = clone(target)
      if (target.is_recalled) { result.replied_message.content = ''; result.replied_message.attachments = [] }
    }
  }
  return result
}

export async function demoRequest(method, url, body, config = {}) {
  const state = readDemo()
  let data
  if (method === 'get' && url === '/rooms/mine') data = demoRooms()
  else if (method === 'post' && /^\/rooms\/\d+\/read$/.test(url)) {
    const roomId = Number(url.split('/')[2])
    const room = state.rooms.find((item) => item.id === roomId)
    if (room) { room.unread_count = 0; persist() }
    data = { room_id: roomId, message_id: body.message_id }
  }
  else if (method === 'post' && /^\/messages\/room\/\d+\/sync$/.test(url)) data = state.messages.filter((message) => message.room_id === Number(url.split('/')[3]) && body.ids.includes(message.id)).map(serialize)
  else if (method === 'get' && url === '/users/me') data = DEMO_USER
  else if (method === 'get' && url === '/users/search') {
    const keyword = (config.params?.keyword || '').toLowerCase()
    data = people.filter((person) => person.id !== 1 && person.username.toLowerCase().includes(keyword))
  } else if (method === 'get' && /^\/messages\/room\/\d+$/.test(url)) {
    const roomId = Number(url.split('/').at(-1))
    const { before_id, after_id, limit = 50 } = config.params || {}
    let items = state.messages.filter((message) => message.room_id === roomId)
    if (before_id) items = items.filter((message) => message.id < before_id)
    if (after_id) items = items.filter((message) => message.id > after_id)
    data = (after_id ? items.slice(0, limit) : items.slice(-limit)).map(serialize)
  } else if (method === 'get' && /^\/messages\/\d+\/context$/.test(url)) {
    const target = state.messages.find((message) => message.id === Number(url.split('/')[2]))
    data = target ? state.messages.filter((message) => message.room_id === target.room_id && Math.abs(message.id - target.id) < 25).map(serialize) : []
  } else if (method === 'post' && url === '/messages') {
    const duplicate = state.messages.find((message) => message.client_message_id === body.client_message_id)
    if (duplicate) return { data: serialize(duplicate) }
    if (!state.rooms.some((room) => room.id === body.room_id)) throw new Error('会话不存在')
    const attachments = (body.attachments || []).map((attachment) => state.uploads.find((upload) => upload.upload_id === attachment.upload_id)).filter(Boolean)
    const message = { ...body, id: Math.max(0, ...state.messages.map((item) => item.id)) + 1, sender_id: 1, sender_username: DEMO_USER.username, attachments, created_at: new Date().toISOString(), is_recalled: false }
    state.messages.push(message)
    data = serialize(message)
    persist()
  } else if (method === 'post' && /^\/messages\/\d+\/recall$/.test(url)) {
    const message = state.messages.find((item) => item.id === Number(url.split('/')[2]))
    if (!message || message.sender_id !== 1) throw new Error('无法撤回这条消息')
    Object.assign(message, { is_recalled: true, content: '', attachments: [], recalled_at: new Date().toISOString() })
    data = serialize(message)
    persist()
  } else if (method === 'post' && url === '/rooms/private') {
    let room = state.rooms.find((item) => item.type === 'private' && item.member_ids.includes(body.target_user_id))
    if (!room) {
      const target = people.find((person) => person.id === body.target_user_id)
      room = { id: Math.max(...state.rooms.map((item) => item.id)) + 1, type: 'private', display_name: target.username, member_count: 2, my_role: 'member', member_ids: [1, target.id], created_at: new Date().toISOString() }
      state.rooms.push(room); persist()
    }
    data = { room }
  } else if (method === 'post' && url === '/rooms/group') {
    const room = { id: Math.max(...state.rooms.map((item) => item.id)) + 1, type: 'group', display_name: body.name, name: body.name, description: body.description, member_count: body.member_user_ids.length + 1, member_ids: [1, ...body.member_user_ids], my_role: 'owner', created_at: new Date().toISOString() }
    state.rooms.push(room); persist(); data = { room }
  } else if (method === 'post' && url === '/uploads') {
    const file = body.get('file')
    if (!file?.size) throw new Error('请选择有内容的文件')
    const fileUrl = await new Promise((resolve, reject) => { const reader = new FileReader(); reader.onload = () => resolve(reader.result); reader.onerror = reject; reader.readAsDataURL(file) })
    if (config.signal?.aborted) throw new DOMException('Upload cancelled', 'AbortError')
    const upload = { upload_id: crypto.randomUUID(), attachment_type: /^image\/(png|jpeg|webp|gif)$/.test(file.type) ? 'image' : 'file', original_name: file.name, mime_type: file.type, file_size: file.size, file_url: fileUrl }
    state.uploads.push(upload); persist(); data = { data: upload }
  } else if (method === 'get' && /^\/uploads\/[^/]+\/access$/.test(url)) {
    const uploadId = url.split('/')[2]
    const upload = state.uploads.find((item) => item.upload_id === uploadId) || state.messages.flatMap((item) => item.attachments || []).find((item) => item.upload_id === uploadId)
    if (!upload) throw new Error('附件已不可用')
    data = { file_url: upload.file_url }
  } else throw new Error('无法完成此操作，请重试')
  return { data: clone(data) }
}
