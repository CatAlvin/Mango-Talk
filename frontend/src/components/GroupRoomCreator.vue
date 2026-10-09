<template>
  <div class="group-room-creator">
    <button
      class="create-btn group-btn"
      type="button"
      :disabled="creating"
      @click="handleToggle"
      title="新建群聊"
      aria-label="新建群聊"
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
        <path d="M7 9a3 3 0 100-6 3 3 0 000 6zM13 10a2.5 2.5 0 100-5 2.5 2.5 0 000 5zM7 11c-3.314 0-6 2.239-6 5a1 1 0 001 1h8.2a1 1 0 00.98-1.2C10.8 13.07 9.1 11 7 11zM13 11c-1.095 0-2.087.302-2.871.82A6.93 6.93 0 0112 16h6a1 1 0 001-1c0-2.21-2.239-4-5-4z"/>
      </svg>
    </button>

    <Teleport to="body">
    <div v-if="open" class="creator-backdrop" @click="handleClose"></div>
    <Transition name="panel">
      <div v-if="open" ref="panelRef" class="create-panel" role="dialog" aria-modal="true" aria-labelledby="group-dialog-title">
        <div class="panel-glow"></div>

        <div class="panel-header">
          <div class="panel-header-text">
            <div class="panel-title-row">
              <div class="panel-title-icon">
                <svg viewBox="0 0 20 20" fill="currentColor" width="14" height="14">
                  <path d="M7 9a3 3 0 100-6 3 3 0 000 6zM13 10a2.5 2.5 0 100-5 2.5 2.5 0 000 5zM7 11c-3.314 0-6 2.239-6 5a1 1 0 001 1h8.2a1 1 0 00.98-1.2C10.8 13.07 9.1 11 7 11zM13 11c-1.095 0-2.087.302-2.871.82A6.93 6.93 0 0112 16h6a1 1 0 001-1c0-2.21-2.239-4-5-4z"/>
                </svg>
              </div>
              <p id="group-dialog-title" class="panel-title">新建群聊</p>
            </div>
          </div>

          <button class="panel-close" type="button" aria-label="关闭新建群聊" @click="handleClose">
            <svg viewBox="0 0 20 20" fill="currentColor" width="14" height="14">
              <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"/>
            </svg>
          </button>
        </div>

        <div class="form-grid">
          <div class="form-block">
            <label for="group-name" class="field-label">群聊名称</label>
            <input
              id="group-name"
              v-model.trim="groupName"
              class="text-input"
              type="text"
              maxlength="100"
              placeholder="例如：周末读书会"
            />
          </div>

          <div class="form-block">
            <label for="group-description" class="field-label">群聊简介（可选）</label>
            <textarea
              id="group-description"
              v-model.trim="description"
              class="textarea-input"
              rows="2"
              maxlength="255"
              placeholder="说说这个群聊的主题"
            ></textarea>
          </div>
        </div>

        <div class="member-section">
          <div class="member-header">
            <span class="field-label">已选成员</span>
            <span class="member-count">{{ selectedUsers.length }} 人</span>
          </div>

          <div v-if="selectedUsers.length > 0" class="selected-list">
            <button
              v-for="user in selectedUsers"
              :key="user.id"
              class="selected-chip"
              type="button"
              @click="removeSelectedUser(user.id)"
              :aria-label="`移除 ${user.username}`"
            >
              <span class="chip-avatar">{{ getUserInitial(user.username) }}</span>
              <span class="chip-name">{{ user.username }}</span>
              <span class="chip-remove">×</span>
            </button>
          </div>

          <div v-else class="selected-empty">
            尚未选择成员
          </div>
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
              aria-label="搜索群成员"
              placeholder="搜索用户名或手机号"
              @keydown.enter.prevent="handleSearch"
            />
          </div>

          <button
            class="search-btn"
            type="button"
            :disabled="searching || creating"
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
            <span>正在搜索可添加成员...</span>
          </template>
          <template v-else-if="searched && results.length === 0">
            <span>没有找到匹配用户</span>
          </template>
          <template v-else>
            <span>{{ panelHintText }}</span>
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
            :disabled="creating"
            :style="{ '--i': index }"
            @click="toggleSelectedUser(user)"
          >
            <div class="result-avatar">
              {{ getUserInitial(user.username) }}
            </div>

            <div class="result-main">
              <p class="result-name">{{ user.username }}</p>
              <p class="result-sub">{{ user.phone || '未填写手机号' }}</p>
            </div>

            <span
              class="result-action"
              :class="{ selected: isSelected(user.id) }"
            >
              {{ isSelected(user.id) ? '已选择' : '添加' }}
            </span>
          </button>
        </TransitionGroup>

        <div class="panel-footer">
          <p class="footer-tip">
            你将成为群主
          </p>

          <button
            class="create-group-submit"
            type="button"
            :disabled="!canCreateGroup"
            @click="handleCreateGroupRoom"
          >
            <span v-if="creating" class="spinner-tiny"></span>
            <span v-else>创建群聊</span>
          </button>
        </div>
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
const groupName = ref('')
const description = ref('')
const keyword = ref('')
const results = ref([])
const selectedUsers = ref([])
const searching = ref(false)
const searched = ref(false)
const creating = ref(false)
const errorMessage = ref('')
let searchGeneration = 0

const canCreateGroup = computed(() => {
  return (
    !!groupName.value.trim() &&
    selectedUsers.value.length > 0 &&
    !creating.value
  )
})

const panelHintText = computed(() => {
  if (selectedUsers.value.length > 0) {
    return '可以继续搜索更多成员，或直接创建群聊'
  }

  return '先搜索用户，再点击“添加”加入群成员列表'
})

function getUserInitial(username) {
  return (username || 'U').charAt(0).toUpperCase()
}

function isSelected(userId) {
  return selectedUsers.value.some((user) => user.id === userId)
}

function toggleSelectedUser(user) {
  if (!user?.id) {
    return
  }

  if (isSelected(user.id)) {
    removeSelectedUser(user.id)
    return
  }

  selectedUsers.value = [...selectedUsers.value, user]
}

function removeSelectedUser(userId) {
  selectedUsers.value = selectedUsers.value.filter((user) => user.id !== userId)
}

function resetPanelState() {
  searchGeneration++
  groupName.value = ''
  description.value = ''
  keyword.value = ''
  results.value = []
  selectedUsers.value = []
  searching.value = false
  searched.value = false
  creating.value = false
  errorMessage.value = ''
}

function handleToggle() {
  open.value = !open.value

  if (!open.value) {
    resetPanelState()
  }
}

function handleClose() {
  if (creating.value) return
  open.value = false
  resetPanelState()
}

async function handleSearch() {
  if (searching.value || creating.value) return
  if (!keyword.value.trim()) { errorMessage.value = '请输入用户名或手机号'; return }
  const generation = ++searchGeneration
  errorMessage.value = ''
  searching.value = true
  searched.value = false

  try {
    const response = await http.get('/users/search', {
      params: {
        keyword: keyword.value,
        limit: 12,
      },
    })

    if (generation !== searchGeneration || !open.value) return
    results.value = Array.isArray(response.data) ? response.data : []
    searched.value = true
  } catch (error) {
    if (generation !== searchGeneration || !open.value) return
    console.error('搜索群成员失败:', error)
    errorMessage.value =
      error?.response?.data?.detail || '搜索用户失败，请稍后重试'
  } finally {
    if (generation === searchGeneration) searching.value = false
  }
}

async function handleCreateGroupRoom() {
  if (creating.value) return
  const name = groupName.value.trim()
  const desc = description.value.trim()

  errorMessage.value = ''

  if (!name) {
    errorMessage.value = '请输入群聊名称'
    return
  }

  if (selectedUsers.value.length === 0) {
    errorMessage.value = '请至少选择 1 位群成员'
    return
  }

  creating.value = true

  try {
    const response = await http.post('/rooms/group', {
      name,
      description: desc || null,
      member_user_ids: selectedUsers.value.map((user) => user.id),
    })

    const roomId = response?.data?.room?.id
    if (!roomId) {
      throw new Error('创建群聊成功，但未拿到房间 ID')
    }

    emit('room-created', roomId)
    creating.value = false
    handleClose()
  } catch (error) {
    console.error('创建群聊失败:', error)
    errorMessage.value =
      error?.response?.data?.detail || '创建群聊失败，请稍后重试'
  } finally {
    creating.value = false
  }
}
</script>

<style scoped lang="scss">
.group-room-creator {
  position: static;
}

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
    box-shadow: 0 0 12px rgba(6, 182, 212, 0.14);
  }

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
}

.group-btn:hover:not(:disabled),
.group-btn.active {
  background: rgba(6, 182, 212, 0.16);
  color: #22d3ee;
}

.create-icon {
  transition: transform 0.3s ease;
}

.create-icon.rotated {
  transform: scale(1.06);
}

.create-panel {
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);

  width: min(520px, calc(100% - 32px));
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
  right: -10px;
  width: 140px;
  height: 140px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(6, 182, 212, 0.12) 0%, transparent 72%);
  pointer-events: none;
}

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
  background: linear-gradient(135deg, rgba(6, 182, 212, 0.18), rgba(249, 115, 22, 0.12));
  color: #22d3ee;
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

.form-grid {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 12px;
}

.form-block {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field-label {
  font-size: 11px;
  font-weight: 700;
  color: rgba(255, 255, 255, 0.5);
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.text-input,
.textarea-input,
.search-input {
  width: 100%;
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.04);
  color: #fff;
  outline: none;
  font-family: inherit;
  font-size: 13px;
  box-sizing: border-box;
  transition: border-color 0.25s, background 0.25s, box-shadow 0.25s;

  &::placeholder {
    color: rgba(255, 255, 255, 0.65);
  }

  &:focus {
    border-color: rgba(6, 182, 212, 0.45);
    background: rgba(255, 255, 255, 0.06);
    box-shadow: 0 0 0 3px rgba(6, 182, 212, 0.08);
  }
}

.text-input {
  height: 38px;
  padding: 0 12px;
}

.textarea-input {
  resize: vertical;
  min-height: 64px;
  padding: 10px 12px;
  line-height: 1.5;
}

.member-section {
  margin-bottom: 12px;
}

.member-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.member-count {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.65);
}

.selected-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.selected-empty {
  padding: 10px 12px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.04);
  color: rgba(255, 255, 255, 0.65);
  font-size: 12px;
}

.selected-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: 1px solid rgba(6, 182, 212, 0.18);
  border-radius: 999px;
  background: rgba(6, 182, 212, 0.1);
  color: #d5fbff;
  padding: 6px 10px 6px 6px;
  cursor: pointer;
  transition: background 0.2s, border-color 0.2s;
  font-family: inherit;

  &:hover {
    background: rgba(6, 182, 212, 0.16);
    border-color: rgba(6, 182, 212, 0.28);
  }
}

.chip-avatar {
  width: 22px;
  height: 22px;
  border-radius: 999px;
  background: linear-gradient(135deg, #06b6d4, #0891b2);
  color: #fff;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 700;
}

.chip-name {
  font-size: 12px;
  font-weight: 600;
}

.chip-remove {
  font-size: 14px;
  opacity: 0.8;
}

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
}

.search-input {
  height: 38px;
  padding: 0 12px 0 32px;
}

.search-btn,
.create-group-submit {
  height: 38px;
  border: none;
  border-radius: 10px;
  padding: 0 14px;
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

  &:disabled {
    opacity: 0.55;
    cursor: not-allowed;
  }
}

.search-btn {
  min-width: 54px;
  background: linear-gradient(135deg, #06b6d4 0%, #0891b2 100%);
  box-shadow: 0 2px 8px rgba(6, 182, 212, 0.18);
}

.create-group-submit {
  min-width: 92px;
  background: linear-gradient(135deg, #f97316 0%, #ea580c 100%);
  box-shadow: 0 2px 8px rgba(249, 115, 22, 0.2);
}

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

.result-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-height: 220px;
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
  transition: background 0.2s, border-color 0.2s, transform 0.15s;
  font-family: inherit;

  &:hover:not(:disabled) {
    background: rgba(255, 255, 255, 0.06);
    border-color: rgba(6, 182, 212, 0.25);
    transform: translateX(2px);
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
  padding: 4px 10px;
  border-radius: 8px;
  background: rgba(249, 115, 22, 0.1);
  color: #fb923c;
  font-size: 11px;
  font-weight: 700;
  flex-shrink: 0;
}

.result-action.selected {
  background: rgba(6, 182, 212, 0.12);
  color: #22d3ee;
}

.panel-footer {
  position: sticky;
  bottom: -16px;
  padding: 14px 0;
  background: #0c1222;
  z-index: 2;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 14px;
}

.footer-tip {
  margin: 0;
  color: rgba(255, 255, 255, 0.65);
  font-size: 11px;
  line-height: 1.5;
  flex: 1;
}

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
