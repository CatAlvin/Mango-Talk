import { defineStore } from 'pinia'
import api, { errorText } from '../lib/api'
import { mergeMessages } from '../lib/messages'

export const useMessageStore = defineStore('message', {
  state: () => ({ roomMessages: {}, loadingRooms: {}, olderLoading: {}, hasOlder: {}, errors: {}, generation: 0 }),
  getters: {
    getMessagesByRoom: (state) => (roomId) => state.roomMessages[roomId] || [],
    isRoomLoading: (state) => (roomId) => !!state.loadingRooms[roomId],
  },
  actions: {
    merge(roomId, items) { this.roomMessages[roomId] = mergeMessages(this.roomMessages[roomId] || [], items) },
    async fetchRoomMessages(roomId, limit = 50) {
      if (!roomId) return []
      const generation = this.generation
      this.loadingRooms[roomId] = true
      this.errors[roomId] = ''
      try {
        const response = await api.get(`/messages/room/${roomId}`, { params: { limit } })
        if (generation !== this.generation) return []
        this.merge(roomId, response.data)
        this.hasOlder[roomId] = response.data.length === limit
        return response.data
      } catch (error) {
        if (generation === this.generation) this.errors[roomId] = errorText(error, '消息加载失败，请重试')
        throw error
      } finally { if (generation === this.generation) this.loadingRooms[roomId] = false }
    },
    async fetchOlder(roomId, limit = 50) {
      if (this.olderLoading[roomId] || this.hasOlder[roomId] === false) return []
      const generation = this.generation
      const beforeId = this.getMessagesByRoom(roomId)[0]?.id
      if (!beforeId) return []
      this.olderLoading[roomId] = true
      this.errors[roomId] = ''
      try {
        const response = await api.get(`/messages/room/${roomId}`, { params: { before_id: beforeId, limit } })
        if (generation !== this.generation) return []
        this.merge(roomId, response.data)
        this.hasOlder[roomId] = response.data.length === limit
        return response.data
      } catch (error) {
        if (generation === this.generation) this.errors[roomId] = errorText(error, '历史消息加载失败，请重试')
        throw error
      } finally { if (generation === this.generation) this.olderLoading[roomId] = false }
    },
    async syncAfter(roomId, recoveryCursor) {
      const generation = this.generation
      let afterId = recoveryCursor ?? this.getMessagesByRoom(roomId).at(-1)?.id
      if (!afterId) return this.fetchRoomMessages(roomId)
      let batch
      do {
        const response = await api.get(`/messages/room/${roomId}`, { params: { after_id: afterId, limit: 100 } })
        if (generation !== this.generation) return
        batch = response.data
        this.merge(roomId, batch)
        afterId = batch.at(-1)?.id || afterId
      } while (batch.length === 100)
    },
    async fetchContext(roomId, messageId) {
      const generation = this.generation
      const response = await api.get(`/messages/${messageId}/context`, { params: { limit: 50 } })
      const context = response.data
      const existing = this.getMessagesByRoom(roomId)
      const collected = [...context]
      let cursor
      let destination
      if (context.length && existing.length) {
        if (context.at(-1).id < existing[0].id) { cursor = context.at(-1).id; destination = existing[0].id }
        else if (existing.at(-1).id < context[0].id) { cursor = existing.at(-1).id; destination = context[0].id }
      }
      while (cursor && cursor < destination) {
        const gap = await api.get(`/messages/room/${roomId}`, { params: { after_id: cursor, limit: 100 } })
        if (generation !== this.generation) return []
        if (!gap.data.length) break
        collected.push(...gap.data)
        cursor = gap.data.at(-1).id
      }
      if (generation === this.generation) this.merge(roomId, collected)
      return collected
    },
    async reconcileLoaded(roomId, ids) {
      const generation = this.generation
      for (let index = 0; index < ids.length; index += 200) {
        const response = await api.post(`/messages/room/${roomId}/sync`, { ids: ids.slice(index, index + 200) })
        if (generation !== this.generation) return
        this.merge(roomId, response.data)
      }
    },
    appendOrUpdateMessage(roomId, message) { if (roomId && message?.id) this.merge(roomId, [message]) },
    clearMessages() {
      this.generation++
      this.roomMessages = {}; this.loadingRooms = {}; this.olderLoading = {}; this.hasOlder = {}; this.errors = {}
    },
  },
})
