<template>
  <div class="private-room-creator">
    <button
      class="create-btn"
      type="button"
      :disabled="creatingUserId !== null"
      @click="handleToggle"
      title="新建私聊"
      aria-label="新建私聊"
      :class="{ active: open }"
    >
      <svg
        class="create-icon"
        :class="{ rotated: open }"
        viewBox="0 0 20 20"
        fill="currentColor"
        width="14"
        height="14"
      >
        <path
          fill-rule="evenodd"
          d="M10 4a1 1 0 011 1v4h4a1 1 0 110 2h-4v4a1 1 0 11-2 0v-4H5a1 1 0 110-2h4V5a1 1 0 011-1z"
          clip-rule="evenodd"
        />
      </svg>
    </button>

    <Teleport to="body">
    <div v-if="open" class="creator-backdrop" @click="handleClose"></div>
    <Transition name="panel">
      <div v-if="open" ref="panelRef" class="create-panel" role="dialog" aria-modal="true" aria-labelledby="private-dialog-title">
        <div class="panel-glow"></div>

        <div class="panel-header">
          <div class="panel-header-text">
            <div class="panel-title-row">
              <div class="panel-title-icon">
                <svg viewBox="0 0 20 20" fill="currentColor" width="14" height="14">
                  <path d="M8 9a3 3 0 100-6 3 3 0 000 6zM8 11a6 6 0 016 6H2a6 6 0 016-6zM16 7a1 1 0 10-2 0v1h-1a1 1 0 100 2h1v1a1 1 0 102 0v-1h1a1 1 0 100-2h-1V7z"/>
                </svg>
              </div>
              <p id="private-dialog-title" class="panel-title">新建私聊</p>
            </div>
          </div>

          <button class="panel-close" type="button" aria-label="关闭新建私聊" @click="handleClose">
            <svg viewBox="0 0 20 20" fill="currentColor" width="14" height="14">
              <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"/>
            </svg>
          </button>
        </div>

        <div class="search-row">
          <div class="search-input-wrap">
            <svg class="search-icon" viewBox="0 0 20 20" fill="currentColor" width="14" height="14">
              <path fill-rule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" clip-rule="evenodd"/>
            </svg>
            <input
              v-model.trim="keyword"
              class="search-input"
              type="text"
              aria-label="搜索用户"
              placeholder="输入用户名或手机号"
              @keydown.enter.prevent="handleSearch"
            />
          </div>

          <button
            class="search-btn"
            type="button"
            :disabled="searching"
            @click="handleSearch"
          >
            <span v-if="searching" class="spinner-tiny"></span>
            <span v-else>搜索</span>
          </button>
        </div>

        <div v-if="errorMessage" class="panel-message panel-error" role="alert">
          <svg viewBox="0 0 20 20" fill="currentColor" width="14" height="14">
            <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/>
          </svg>
          <span>{{ errorMessage }}</span>
        </div>

        <div v-else class="panel-message panel-hint">
          <template v-if="searching">
            <span class="spinner-tiny hint-spinner"></span>
            <span>正在搜索用户...</span>
          </template>
          <template v-else-if="searched && results.length === 0">
            <svg viewBox="0 0 20 20" fill="currentColor" width="14" height="14" style="opacity:0.5">
              <path fill-rule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" clip-rule="evenodd"/>
            </svg>
            <span>没有找到匹配用户</span>
          </template>
          <template v-else>
            <span>输入关键词后搜索，点击用户即可创建或进入已有私聊</span>
          </template>
        </div>

        <TransitionGroup
          v-if="results.length > 0"
          name="result"
          tag="div"
          class="result-list"
        >
          <button
            v-for="(user, index) in results"
            :key="user.id"
            class="result-item"
            type="button"
            :disabled="creatingUserId !== null"
            :style="{ '--i': index }"
            @click="handleCreatePrivateRoom(user)"
          >
            <div class="result-avatar">
              {{ getUserInitial(user.username) }}
            </div>

            <div class="result-main">
              <p class="result-name">{{ user.username }}</p>
              <p class="result-sub">
                {{ user.phone || '未填写手机号' }}
              </p>
            </div>

            <span class="result-action" :class="{ creating: creatingUserId === user.id }">
              <template v-if="creatingUserId === user.id">
                <span class="spinner-tiny"></span>
              </template>
              <template v-else>
                <svg viewBox="0 0 20 20" fill="currentColor" width="12" height="12">
                  <path d="M2 5a2 2 0 012-2h7a2 2 0 012 2v4a2 2 0 01-2 2H9l-3 3v-3H4a2 2 0 01-2-2V5z"/>
                  <path d="M15 7v2a4 4 0 01-4 4H9.828l-1.766 1.767c.28.149.599.233.938.233h2l3 3v-3h2a2 2 0 002-2V9a2 2 0 00-2-2h-1z"/>
                </svg>
                <span>私聊</span>
              </template>
            </span>
          </button>
        </TransitionGroup>
      </div>
    </Transition>
    </Teleport>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import http from '../lib/api'
import { useDialog } from '../composables/useDialog'

const emit = defineEmits(['room-created'])

const open = ref(false)
const { panelRef } = useDialog(open, handleClose)
const keyword = ref('')
const results = ref([])
const searching = ref(false)
const searched = ref(false)
const creatingUserId = ref(null)
const errorMessage = ref('')
let searchGeneration = 0

const panelHintText = computed(() => {
  if (searching.value) {
    return '正在搜索用户...'
  }

  if (searched.value && results.value.length === 0) {
    return '没有找到匹配用户'
  }

  return '输入关键词后搜索，点击用户即可创建或进入已有私聊'
})

function getUserInitial(username) {
  return (username || 'U').charAt(0).toUpperCase()
}

function resetPanelState() {
  searchGeneration++
  keyword.value = ''
  results.value = []
  searching.value = false
  searched.value = false
  creatingUserId.value = null
  errorMessage.value = ''
}

function handleToggle() {
  open.value = !open.value

  if (!open.value) {
    resetPanelState()
  }
}

function handleClose() {
  if (creatingUserId.value !== null) return
  open.value = false
  resetPanelState()
}

async function handleSearch() {
  if (searching.value || creatingUserId.value !== null) return
  if (!keyword.value.trim()) { errorMessage.value = '请输入用户名或手机号'; return }
  const generation = ++searchGeneration
  errorMessage.value = ''
  searching.value = true
  searched.value = false

  try {
    const response = await http.get('/users/search', {
      params: {
        keyword: keyword.value,
        limit: 10,
      },
    })

    if (generation !== searchGeneration || !open.value) return
    results.value = response.data
    searched.value = true
  } catch (error) {
    if (generation !== searchGeneration || !open.value) return
    console.error('搜索用户失败:', error)
    errorMessage.value =
      error?.response?.data?.detail || '搜索用户失败，请稍后重试'
  } finally {
    if (generation === searchGeneration) searching.value = false
  }
}

async function handleCreatePrivateRoom(user) {
  if (creatingUserId.value !== null) return
  if (!user?.id) {
    return
  }

  errorMessage.value = ''
  creatingUserId.value = user.id

  try {
    const response = await http.post('/rooms/private', {
      target_user_id: user.id,
    })

    const roomId = response?.data?.room?.id
    if (!roomId) {
      throw new Error('创建私聊成功，但未拿到房间 ID')
    }

    emit('room-created', roomId)
    creatingUserId.value = null
    handleClose()
  } catch (error) {
    console.error('创建私聊失败:', error)
    errorMessage.value =
      error?.response?.data?.detail || '创建私聊失败，请稍后重试'
  } finally {
    creatingUserId.value = null
  }
}
</script>

<style scoped lang="scss">
.private-room-creator {
  position: static;
}

/* ========== Trigger Button ========== */
.create-btn {
  width: 28px;
  height: 28px;
  border: none;
  border-radius: 8px;
  background: var(--c-sidebar-surface, rgba(255,255,255,0.05));
  color: var(--c-sidebar-text, rgba(255,255,255,0.7));
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.25s, color 0.25s, box-shadow 0.25s;

  &:hover:not(:disabled) {
    background: rgba(249, 115, 22, 0.15);
    color: #fb923c;
    box-shadow: 0 0 12px rgba(249, 115, 22, 0.15);
  }

  &.active {
    background: rgba(249, 115, 22, 0.2);
    color: #fb923c;
  }

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
}

.create-icon {
  transition: transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);

  &.rotated {
    transform: rotate(45deg);
  }
}

/* ========== Panel ========== */
.create-panel {
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);

  width: min(480px, calc(100% - 32px));
  max-width: calc(100% - 32px);
  max-height: calc(100dvh - 32px);
  box-sizing: border-box;

  padding: 16px;
  border-radius: 16px;
  background: rgba(12, 18, 34, 0.95);
  backdrop-filter: blur(24px) saturate(1.3);
  -webkit-backdrop-filter: blur(24px) saturate(1.3);
  border: 1px solid rgba(255, 255, 255, 0.08);
  box-shadow:
    0 20px 60px rgba(0, 0, 0, 0.45),
    0 0 1px rgba(255, 255, 255, 0.08),
    inset 0 1px 0 rgba(255, 255, 255, 0.05);
  z-index: 201;
  overflow-y: auto;
  overflow-x: hidden;
}

.creator-backdrop { position: fixed; inset: 0; background: rgba(2, 6, 23, .65); backdrop-filter: blur(4px); z-index: 200; }

.panel-glow {
  position: absolute;
  top: -40px;
  left: -20px;
  width: 120px;
  height: 120px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(249, 115, 22, 0.1) 0%, transparent 70%);
  pointer-events: none;
}

/* -- Panel transition -- */
.panel-enter-active {
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}

.panel-leave-active {
  transition: all 0.2s cubic-bezier(0.4, 0, 1, 1);
}

.panel-enter-from {
  opacity: 0;
  transform: translate(-50%, calc(-50% - 8px)) scale(0.96);
}

.panel-leave-to {
  opacity: 0;
  transform: translate(-50%, calc(-50% - 4px)) scale(0.98);
}

/* ========== Panel Header ========== */
.panel-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 14px;
}

.panel-header-text {
  min-width: 0;
}

.panel-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.panel-title-icon {
  width: 24px;
  height: 24px;
  border-radius: 7px;
  background: linear-gradient(135deg, rgba(249, 115, 22, 0.2), rgba(6, 182, 212, 0.15));
  color: #fb923c;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.panel-title {
  margin: 0;
  color: #fff;
  font-size: 14px;
  font-weight: 700;
  letter-spacing: 0.01em;
}

.panel-subtitle {
  margin: 0;
  color: rgba(255, 255, 255, 0.65);
  font-size: 11px;
  line-height: 1.5;
}

.panel-close {
  width: 26px;
  height: 26px;
  border: none;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.04);
  color: rgba(255, 255, 255, 0.65);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: background 0.2s, color 0.2s;

  &:hover {
    background: rgba(255, 255, 255, 0.1);
    color: #fff;
  }
}

/* ========== Search ========== */
.search-row {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.search-input-wrap {
  flex: 1;
  min-width: 0;
  position: relative;
}

.search-icon {
  position: absolute;
  left: 11px;
  top: 50%;
  transform: translateY(-50%);
  color: rgba(255, 255, 255, 0.65);
  pointer-events: none;
  transition: color 0.25s;
}

.search-input-wrap:focus-within .search-icon {
  color: rgba(6, 182, 212, 0.6);
}

.search-input {
  width: 100%;
  height: 38px;
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: 10px;
  padding: 0 12px 0 32px;
  background: rgba(255, 255, 255, 0.04);
  color: #fff;
  outline: none;
  font-family: inherit;
  font-size: 13px;
  transition: border-color 0.25s, background 0.25s, box-shadow 0.25s;
  box-sizing: border-box;

  &::placeholder {
    color: rgba(255, 255, 255, 0.65);
  }

  &:focus {
    border-color: rgba(6, 182, 212, 0.4);
    background: rgba(255, 255, 255, 0.06);
    box-shadow: 0 0 0 3px rgba(6, 182, 212, 0.08);
  }
}

.search-btn {
  height: 38px;
  min-width: 54px;
  border: none;
  border-radius: 10px;
  padding: 0 14px;
  background: linear-gradient(135deg, #f97316 0%, #ea580c 100%);
  color: #fff;
  font-family: inherit;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: transform 0.15s, box-shadow 0.15s, opacity 0.2s;
  box-shadow: 0 2px 8px rgba(249, 115, 22, 0.2);

  &:hover:not(:disabled) {
    transform: translateY(-1px);
    box-shadow: 0 4px 14px rgba(249, 115, 22, 0.3);
  }

  &:active:not(:disabled) {
    transform: translateY(0);
  }

  &:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
}

/* ========== Messages ========== */
.panel-message {
  display: flex;
  align-items: center;
  gap: 7px;
  margin: 0 0 12px;
  font-size: 12px;
  line-height: 1.5;
  min-height: 20px;
}

.panel-error {
  color: #fca5a5;
  padding: 8px 10px;
  border-radius: 8px;
  background: rgba(239, 68, 68, 0.08);
  border: 1px solid rgba(239, 68, 68, 0.12);
}

.panel-hint {
  color: rgba(255, 255, 255, 0.65);
}

.hint-spinner {
  border-top-color: rgba(6, 182, 212, 0.7) !important;
}

/* ========== Result List ========== */
.result-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-height: 260px;
  overflow-y: auto;
  padding-right: 2px;

  &::-webkit-scrollbar {
    width: 3px;
  }

  &::-webkit-scrollbar-track {
    background: transparent;
  }

  &::-webkit-scrollbar-thumb {
    background: rgba(255, 255, 255, 0.08);
    border-radius: 2px;
  }
}

/* -- Result item transitions -- */
.result-enter-active {
  transition: all 0.35s cubic-bezier(0.16, 1, 0.3, 1);
  transition-delay: calc(var(--i, 0) * 0.04s);
}

.result-leave-active {
  transition: all 0.2s ease;
}

.result-enter-from {
  opacity: 0;
  transform: translateY(8px) scale(0.97);
}

.result-leave-to {
  opacity: 0;
  transform: scale(0.97);
}

.result-item {
  width: 100%;
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.03);
  padding: 10px 12px;
  display: flex;
  align-items: center;
  gap: 10px;
  text-align: left;
  cursor: pointer;
  color: inherit;
  transition: background 0.2s, border-color 0.2s, transform 0.15s, box-shadow 0.2s;

  &:hover:not(:disabled) {
    background: rgba(255, 255, 255, 0.06);
    border-color: rgba(6, 182, 212, 0.25);
    transform: translateX(2px);
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.15);
  }

  &:active:not(:disabled) {
    transform: translateX(2px) scale(0.99);
  }

  &:disabled {
    opacity: 0.55;
    cursor: not-allowed;
  }
}

.result-avatar {
  width: 34px;
  height: 34px;
  border-radius: 10px;
  background: linear-gradient(135deg, #06b6d4, #0891b2);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 700;
  flex-shrink: 0;
  box-shadow: 0 2px 6px rgba(6, 182, 212, 0.2);
}

.result-main {
  flex: 1;
  min-width: 0;
}

.result-name {
  margin: 0 0 2px;
  color: rgba(255, 255, 255, 0.92);
  font-size: 13px;
  font-weight: 600;
  word-break: break-word;
}

.result-sub {
  margin: 0;
  color: rgba(255, 255, 255, 0.65);
  font-size: 11px;
  word-break: break-word;
}

.result-action {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 4px 10px;
  border-radius: 8px;
  background: rgba(249, 115, 22, 0.1);
  color: #fb923c;
  font-size: 11px;
  font-weight: 700;
  flex-shrink: 0;
  transition: background 0.2s, color 0.2s;

  &.creating {
    background: rgba(6, 182, 212, 0.1);
    color: #22d3ee;
  }
}

.result-item:hover:not(:disabled) .result-action:not(.creating) {
  background: rgba(249, 115, 22, 0.18);
  color: #fdba74;
}

/* ========== Spinner ========== */
.spinner-tiny {
  display: inline-block;
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.15);
  border-top-color: currentColor;
  border-radius: 50%;
  animation: spin 0.65s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
