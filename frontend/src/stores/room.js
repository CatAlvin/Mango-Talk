import { defineStore } from 'pinia'
import api, { errorText } from '../lib/api'
import { isDemoActive, readDemo, setDemoSelection } from '../lib/demo'

export const useRoomStore = defineStore('room', {
  state: () => ({ rooms: [], selectedRoomId: null, loading: false, error: '', generation: 0 }),
  getters: { selectedRoom: (state) => state.rooms.find((room) => room.id === state.selectedRoomId) || null },
  actions: {
    async fetchMyRooms() {
      const generation = this.generation
      this.loading = true; this.error = ''
      try {
        const response = await api.get('/rooms/mine')
        if (generation !== this.generation) return []
        this.rooms = response.data
        if (!this.selectedRoomId && isDemoActive()) this.selectedRoomId = readDemo().selectedRoomId
        if (!this.rooms.some((room) => room.id === this.selectedRoomId)) this.selectedRoomId = this.rooms[0]?.id || null
        return this.rooms
      } catch (error) {
        if (generation === this.generation) this.error = errorText(error, '会话加载失败，请重试')
        throw error
      } finally { if (generation === this.generation) this.loading = false }
    },
    selectRoom(roomId) { this.selectedRoomId = roomId; if (isDemoActive()) setDemoSelection(roomId) },
    updateActivity(message, unread = false) {
      const room = this.rooms.find((item) => item.id === message.room_id)
      if (!room) return
      const isNew = !room.last_message || message.id > room.last_message.id
      if (!room.last_message || message.id >= room.last_message.id) { room.last_message = message; room.last_activity_at = message.created_at }
      if (unread && isNew) room.unread_count = (room.unread_count || 0) + 1
      this.rooms.sort((a, b) => new Date(b.last_activity_at || b.updated_at || 0) - new Date(a.last_activity_at || a.updated_at || 0))
    },
    async markRead(roomId, messageId) {
      if (!roomId || !messageId) return
      await api.post(`/rooms/${roomId}/read`, { message_id: messageId })
      const room = this.rooms.find((item) => item.id === roomId)
      if (room) room.unread_count = 0
    },
    clearRooms() { this.generation++; this.rooms = []; this.selectedRoomId = null; this.error = ''; this.loading = false },
  },
})
