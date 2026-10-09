<template>
  <div class="chat-page">
    <!-- mobile overlay -->
    <div
      v-if="sidebarOpen"
      class="sidebar-overlay"
      @click="sidebarOpen = false"
    ></div>

    <!-- mobile hamburger -->
    <button
      class="mobile-menu-btn"
      aria-label="打开会话列表"
      :aria-expanded="sidebarOpen"
      @click="sidebarOpen = !sidebarOpen"
    >
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 6h16M4 12h16M4 18h16"/></svg>
    </button>

    <aside class="sidebar" :class="{ open: sidebarOpen }">
      <div class="brand-block">
        <div class="brand-logo">
          <svg viewBox="0 0 36 36" fill="none"><rect width="36" height="36" rx="10" fill="url(#sb)"/><path d="M10 15.5c0-3.3 3.6-6 7.5-6s7.5 2.7 7.5 6-3.6 6-7.5 6c-1 0-1.9-.13-2.75-.38L12 23l.88-2.65C11.56 19.16 10 17.44 10 15.5z" fill="#fff" fill-opacity=".9"/><defs><linearGradient id="sb" x1="0" y1="0" x2="36" y2="36"><stop stop-color="#fb923c"/><stop offset="1" stop-color="#f97316"/></linearGradient></defs></svg>
        </div>
        <div>
          <h2>Mango Talk</h2>
          <p class="muted">{{ authStore.demoMode ? '演示空间' : '让交流轻松一点' }}</p>
        </div>
      </div>

      <div class="user-card">
        <div class="avatar">
          {{ userInitial }}
        </div>
        <div class="user-meta">
          <p class="username">{{ authStore.user?.username || '未登录用户' }}</p>
          <p class="role">{{ authStore.demoMode ? '欢迎体验 Mango Talk' : roleLabel(authStore.user?.role) }}</p>
        </div>
      </div>

      <div class="room-section">
        <div class="room-section-header">
          <h3>会话</h3>

          <div class="room-header-actions">
            <GroupRoomCreator @room-created="handleGroupRoomCreated" />
            <PrivateRoomCreator @room-created="handlePrivateRoomCreated" />

            <button class="refresh-btn" aria-label="刷新会话" @click="handleRefreshRooms" :disabled="roomStore.loading">
              <svg v-if="!roomStore.loading" viewBox="0 0 20 20" fill="currentColor" width="14" height="14"><path fill-rule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clip-rule="evenodd"/></svg>
              <span v-else class="spinner-tiny"></span>
            </button>
          </div>
        </div>

        <div v-if="roomStore.loading && roomStore.rooms.length === 0" class="room-empty">
          <span class="spinner-tiny"></span>
          <span>正在加载房间列表...</span>
        </div>

        <div v-else-if="roomStore.error" class="room-empty room-error" role="alert">
          <span>{{ roomStore.error }}</span>
          <button type="button" @click="handleRefreshRooms">重新加载</button>
        </div>

        <div v-if="!roomStore.loading && !roomStore.error && roomStore.rooms.length === 0" class="room-empty">
          从上方发起私聊，或创建一个群聊
        </div>

        <div v-if="roomStore.rooms.length" class="room-list">
          <button
            v-for="room in roomStore.rooms"
            :key="room.id"
            class="room-item"
            :class="{ active: room.id === roomStore.selectedRoomId }"
            @click="handleSelectRoom(room.id); sidebarOpen = false"
          >
            <div class="room-avatar" :class="room.type">
              {{ getRoomInitial(room) }}
            </div>

            <div class="room-info">
              <div class="room-top">
                <p class="room-name">{{ room.display_name }}</p>
                <span class="room-type-badge" :class="room.type">
                  {{ room.type === 'private' ? '私聊' : '群聊' }}
                </span>
              </div>

              <div class="room-bottom">
                <span class="room-preview">{{ previewText(room.last_message) }}</span>
                <span v-if="room.unread_count" class="unread-badge">{{ room.unread_count > 99 ? '99+' : room.unread_count }}</span>
              </div>
            </div>
          </button>
        </div>
      </div>

      <button v-if="authStore.demoMode" class="demo-reset-btn" type="button" :disabled="resettingDemo" @click="handleResetDemo">{{ resettingDemo ? '正在重置…' : '重置演示' }}</button>
      <button class="logout-btn" @click="handleLogout">
        <svg viewBox="0 0 20 20" fill="currentColor" width="16" height="16"><path fill-rule="evenodd" d="M3 3a1 1 0 00-1 1v12a1 1 0 001 1h12a1 1 0 001-1V4a1 1 0 00-1-1H3zm7.707 4.293a1 1 0 010 1.414L9.414 10l1.293 1.293a1 1 0 01-1.414 1.414l-2-2a1 1 0 010-1.414l2-2a1 1 0 011.414 0z" clip-rule="evenodd"/><path d="M14 10a1 1 0 01-1 1H9a1 1 0 110-2h4a1 1 0 011 1z"/></svg>
        {{ authStore.demoMode ? '退出演示' : '退出登录' }}
      </button>
    </aside>

    <main class="chat-main">
      <header class="chat-header">
        <template v-if="roomStore.selectedRoom">
          <div class="chat-header-main">
            <div class="chat-header-text">
              <h2>{{ roomStore.selectedRoom.display_name }}</h2>
              <p>
                {{ roomStore.selectedRoom.type === 'private' ? '私聊' : '群聊' }}
                · {{ roomStore.selectedRoom.member_count }} 位成员
                <template v-if="roomStore.selectedRoom.type === 'group'">· {{ roleLabel(roomStore.selectedRoom.my_role) }}</template>
              </p>
            </div>

            <div class="ws-status" :class="wsStatusClass">
              <span class="ws-dot"></span>
              {{ wsStatusText }}
            </div>
          </div>
        </template>

        <template v-else>
          <div class="empty-header">
            <h2>欢迎回来</h2>
            <p>选择一个会话，开始交流</p>
          </div>
        </template>
      </header>

      <section class="message-list">
        <template v-if="roomStore.selectedRoom">
          <div v-if="isCurrentRoomLoading && !currentMessages.length" class="message-empty">
            <span class="spinner"></span>
            <span>正在加载消息记录...</span>
          </div>

          <div v-else-if="currentRoomError && !currentMessages.length" class="message-empty" role="alert">
            <span>{{ currentRoomError }}</span>
            <button class="history-btn" type="button" @click="loadCurrentRoomMessages">重新加载</button>
          </div>

          <div v-else-if="currentMessages.length === 0" class="message-empty">
            <svg viewBox="0 0 48 48" fill="none" width="48" height="48" style="opacity:0.4"><rect x="4" y="8" width="40" height="28" rx="6" stroke="currentColor" stroke-width="2"/><path d="M4 30l8-6 6 4 10-8 16 12" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/></svg>
            <span>还没有消息，打个招呼吧</span>
          </div>

          <div v-else class="message-area">
            <div
              ref="messageScrollRef"
              class="message-scroll"
              @scroll="handleMessageScroll"
            >
              <div class="history-control">
                <button v-if="messageStore.hasOlder[roomStore.selectedRoomId]" class="history-btn" type="button" :disabled="messageStore.olderLoading[roomStore.selectedRoomId]" @click="handleLoadOlder">{{ messageStore.olderLoading[roomStore.selectedRoomId] ? '正在加载…' : '查看更早消息' }}</button>
                <span v-else>已显示全部消息</span>
                <div v-if="currentRoomError" class="history-error" role="alert">{{ currentRoomError }} <button type="button" @click="loadCurrentRoomMessages">重试</button></div>
              </div>
              <div
                v-for="message in currentMessages"
                :key="message.id"
                class="message-row"
                :data-message-id="message.id"
                :class="{
                  mine: isMine(message),
                  'has-actions': canReplyMessage(message) || canRecallMessage(message),
                  'replying-target': replyDraft?.messageId === message.id,
                  'jump-highlight': activeJumpMessageId === message.id
                }"
              >
                <div class="message-avatar-col" v-if="!isMine(message)">
                  <div class="msg-avatar">{{ getSenderLabel(message).charAt(0) }}</div>
                </div>

                <div class="message-body">
                  <div class="message-meta">
                    <span class="sender">
                      {{ getSenderLabel(message) }}
                    </span>
                    <span class="time">
                      {{ formatTime(message.created_at) }}
                    </span>
                  </div>

                  <div
                    class="message-bubble"
                    :class="{
                      mine: isMine(message),
                      recalled: message.is_recalled
                    }"
                  >
                    <button
                      v-if="message.reply_to_message_id && !message.is_recalled"
                      type="button"
                      class="reply-preview"
                      :class="{
                        mine: isMine(message),
                        missing: !getReplyTargetMessage(message),
                        clickable: !!getReplyTargetMessage(message)
                      }"
                      title="查看原消息"
                      @click="handleReplyPreviewClick(message)"
                    >
                      <p class="reply-preview-label">
                        {{ getReplyPreviewTitle(message) }}
                      </p>
                      <p class="reply-preview-content">
                        {{ getReplyPreviewContent(message) }}
                      </p>
                    </button>

                    <p v-if="message.is_recalled" class="recalled-text">
                      该消息已被撤回
                    </p>

                    <template v-else>
                      <p v-if="message.content" class="message-content">
                        {{ message.content }}
                      </p>

                      <div
                        v-if="message.message_type === 'image' && getImageAttachments(message).length > 0"
                        class="attachment-list image-list"
                      >
                        <a
                          v-for="attachment in getImageAttachments(message)"
                          :key="attachment.id || attachment.stored_name"
                          class="image-attachment-link"
                          :href="attachment.file_url"
                          target="_blank"
                          rel="noopener noreferrer"
                          @click.prevent="openAttachment(attachment)"
                        >
                          <img
                            class="image-attachment-preview"
                            :src="attachment.file_url"
                            :alt="attachment.original_name"
                            loading="lazy"
                            @error="handleImageError(attachment)"
                            @load="handleImageLoad"
                          />
                        </a>
                      </div>

                      <div
                        v-if="message.message_type === 'file' && getFileAttachments(message).length > 0"
                        class="attachment-list file-list"
                      >
                        <a
                          v-for="attachment in getFileAttachments(message)"
                          :key="attachment.id || attachment.stored_name"
                          class="file-attachment-card"
                          :href="attachment.file_url"
                          target="_blank"
                          rel="noopener noreferrer"
                          @click.prevent="openAttachment(attachment)"
                        >
                          <div class="file-attachment-icon">
                            <svg viewBox="0 0 20 20" fill="currentColor" width="20" height="20"><path fill-rule="evenodd" d="M8 4a3 3 0 00-3 3v4a5 5 0 0010 0V7a1 1 0 112 0v4a7 7 0 11-14 0V7a5 5 0 0110 0v4a3 3 0 11-6 0V7a1 1 0 012 0v4a1 1 0 102 0V7a3 3 0 00-3-3z" clip-rule="evenodd"/></svg>
                          </div>
                          <div class="file-attachment-meta">
                            <p class="file-attachment-name">
                              {{ attachment.original_name }}
                            </p>
                            <p class="file-attachment-sub">
                              {{ attachment.mime_type || '未知类型' }} · {{ formatFileSize(attachment.file_size) }}
                            </p>
                          </div>
                        </a>
                      </div>

                      <p
                        v-if="
                          !message.content &&
                          getMessageAttachments(message).length === 0 &&
                          message.message_type !== 'text'
                        "
                        class="message-content empty-message-content"
                      >
                        该消息暂无可展示内容
                      </p>
                    </template>
                  </div>

                  <div
                    v-if="canReplyMessage(message) || canRecallMessage(message)"
                    class="message-actions"
                    :class="{ mine: isMine(message) }"
                  >
                    <button
                      v-if="canReplyMessage(message)"
                      class="reply-btn"
                      type="button"
                      :class="{ active: replyDraft?.messageId === message.id }"
                      @click="handleReplyMessage(message)"
                    >
                      回复
                    </button>

                    <button
                      v-if="canRecallMessage(message)"
                      class="recall-btn"
                      type="button"
                      :disabled="recallingMessageId === message.id"
                      @click="handleRecallMessage(message)"
                    >
                      {{ recallingMessageId === message.id ? '撤回中...' : '撤回' }}
                    </button>
                  </div>
                </div>
              </div>
            </div>

            <Transition name="fade-up">
              <button
                v-if="showScrollToBottom"
                class="scroll-to-bottom-btn"
                type="button"
                @click="handleScrollToBottom"
              >
                <svg viewBox="0 0 20 20" fill="currentColor" width="16" height="16"><path fill-rule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clip-rule="evenodd"/></svg>
                {{ hasUnreadIncoming ? '有新消息' : '回到底部' }}
              </button>
            </Transition>
          </div>
        </template>

        <div v-else class="message-empty welcome-empty">
          <div class="welcome-icon">
            <svg viewBox="0 0 64 64" fill="none" width="64" height="64">
              <circle cx="32" cy="32" r="30" stroke="currentColor" stroke-width="1.5" opacity="0.15"/>
              <path d="M20 28c0-5.5 5.4-10 12-10s12 4.5 12 10-5.4 10-12 10c-1.5 0-3-.2-4.4-.6L22 40l1.4-4.3C21.3 33.7 20 31 20 28z" stroke="currentColor" stroke-width="1.8" fill="none" opacity="0.35"/>
            </svg>
          </div>
          <p class="welcome-text">选择一个会话开始交流</p>
        </div>
      </section>

      <footer class="message-composer" v-if="roomStore.selectedRoom">
        <div class="composer-box">
          <div v-if="replyDraft" class="reply-draft-bar">
            <div class="reply-draft-text">
              <p class="reply-draft-label">
                正在回复 {{ replyDraft.senderLabel }}
              </p>
              <p class="reply-draft-content">
                {{ replyDraft.previewText }}
              </p>
            </div>

            <button
              class="reply-draft-cancel"
              type="button"
              @click="clearReplyDraft"
            >
              取消
            </button>
          </div>

          <div class="composer-input-row">
            <textarea
              v-model="draftMessage"
              class="composer-input"
              :placeholder="composerPlaceholder"
              aria-label="消息内容"
              maxlength="10000"
              @keydown="handleComposerKeydown"
            ></textarea>
          </div>

          <input
            ref="fileInputRef"
            class="file-input-hidden"
            type="file"
            @change="handleFileChange"
          />

          <div class="composer-actions">
            <div class="composer-feedback">
              <p v-if="sendError" class="send-error" role="alert">
                {{ sendError }}
              </p>
              <p v-else-if="uploading" class="send-pending">
                正在上传 {{ uploadProgress ? `${uploadProgress}%` : '…' }}
              </p>
              <p v-else-if="sending" class="send-pending">
                正在发送…
              </p>
              <p v-else class="send-hint">
                Enter 发送 · Shift+Enter 换行
              </p>
            </div>

            <div class="composer-buttons">
              <button
                class="upload-btn"
                type="button"
                :disabled="uploading || sending"
                @click="handlePickFile"
                title="上传文件或图片"
              >
                <svg viewBox="0 0 20 20" fill="currentColor" width="18" height="18"><path fill-rule="evenodd" d="M8 4a3 3 0 00-3 3v4a5 5 0 0010 0V7a1 1 0 112 0v4a7 7 0 11-14 0V7a5 5 0 0110 0v4a3 3 0 11-6 0V7a1 1 0 012 0v4a1 1 0 102 0V7a3 3 0 00-3-3z" clip-rule="evenodd"/></svg>
                <span class="upload-label">{{ uploading ? '上传中...' : '文件' }}</span>
              </button>

              <button v-if="failedTask" class="retry-send-btn" type="button" :disabled="sending || uploading" @click="retryFailedMessage">重新发送</button>
              <button v-if="failedTask" class="discard-send-btn" type="button" :disabled="sending" @click="discardFailedMessage" aria-label="关闭发送重试">×</button>

              <button
                v-if="wsStatus !== 'connected'"
                class="reconnect-btn"
                type="button"
                @click="handleReconnect"
              >
                重新连接
              </button>

              <button
                class="send-btn"
                type="button"
                aria-label="发送消息"
                :disabled="!canSend"
                @click="handleSendMessage"
              >
                <svg v-if="!sending" viewBox="0 0 20 20" fill="currentColor" width="18" height="18"><path d="M10.894 2.553a1 1 0 00-1.788 0l-7 14a1 1 0 001.169 1.409l5-1.429A1 1 0 009 15.571V11a1 1 0 112 0v4.571a1 1 0 00.725.962l5 1.428a1 1 0 001.17-1.408l-7-14z"/></svg>
                <span v-else class="spinner-tiny"></span>
              </button>
            </div>
          </div>
        </div>
      </footer>
    </main>
  </div>
</template>

<script setup>
import { useChat } from '../composables/useChat'
import PrivateRoomCreator from '../components/PrivateRoomCreator.vue'
import GroupRoomCreator from '../components/GroupRoomCreator.vue'
const { authStore, roomStore, messageStore, messageScrollRef, fileInputRef, sidebarOpen, recallingMessageId, activeJumpMessageId, currentMessages, isCurrentRoomLoading, currentRoomError, userInitial, wsStatus, wsStatusText, wsStatusClass, composerPlaceholder, showScrollToBottom, hasUnreadIncoming, resettingDemo, draftMessage, replyDraft, sendError, sending, uploading, uploadProgress, failedTask, canSend, clearReplyDraft, handleSendMessage, retryFailedMessage, discardFailedMessage, roleLabel, previewText, getRoomInitial, isMine, getSenderLabel, canReplyMessage, canRecallMessage, getReplyTargetMessage, getReplyPreviewTitle, getReplyPreviewContent, getMessageAttachments, getImageAttachments, getFileAttachments, handleReplyMessage, handleReplyPreviewClick, handleMessageScroll, handleScrollToBottom, handleLoadOlder, loadCurrentRoomMessages, handleRefreshRooms, handlePrivateRoomCreated, handleGroupRoomCreated, handleSelectRoom, handleLogout, handleComposerKeydown, handleReconnect, handlePickFile, handleFileChange, handleRecallMessage, handleResetDemo, handleImageError, handleImageLoad, openAttachment, formatTime, formatFileSize } = useChat()
</script>

<style scoped lang="scss">

/* ========== TOKENS ========== */
.chat-page {
  --c-orange: #f97316;
  --c-orange-hover: #ea580c;
  --c-orange-subtle: #fff7ed;
  --c-orange-border: #fed7aa;
  --c-cyan: #06b6d4;
  --c-cyan-deep: #0891b2;
  --c-cyan-subtle: #ecfeff;
  --c-cyan-border: #a5f3fc;
  --c-sidebar-bg: #0c1222;
  --c-sidebar-surface: rgba(255,255,255,0.05);
  --c-sidebar-text: rgba(255,255,255,0.7);
  --c-sidebar-text-dim: rgba(255,255,255,0.6);
  --c-main-bg: #f0f4f8;
  --c-surface: #ffffff;
  --c-text: #0f172a;
  --c-text-secondary: #64748b;
  --c-border: #e2e8f0;
  --c-danger: #ef4444;
  --radius-lg: 18px;
  --radius-md: 14px;
  --radius-sm: 10px;

  display: flex;
  height: 100dvh;
  min-height: 0;
  background: var(--c-main-bg);
  overflow: hidden;
  font-family: 'DM Sans', system-ui, -apple-system, sans-serif;
  color: var(--c-text);
}

/* ========== SIDEBAR ========== */
.sidebar {
  width: 320px;
  padding: 20px 16px;
  background: var(--c-sidebar-bg);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  min-width: 0;
  overflow: hidden;
  position: relative;
  z-index: 20;

  &::after {
    content: '';
    position: absolute;
    top: 0;
    right: 0;
    bottom: 0;
    width: 1px;
    background: linear-gradient(180deg, rgba(6,182,212,0.3) 0%, rgba(249,115,22,0.3) 100%);
  }
}

.brand-block {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 24px;
  padding: 0 4px;

  h2 {
    margin: 0;
    font-family: 'Outfit', sans-serif;
    font-size: 22px;
    font-weight: 800;
    background: linear-gradient(135deg, var(--c-orange) 30%, var(--c-cyan) 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }

  .muted {
    margin: 2px 0 0;
    color: var(--c-sidebar-text-dim);
    font-size: 11px;
    letter-spacing: 0.03em;
  }
}

.brand-logo {
  width: 36px;
  height: 36px;
  flex-shrink: 0;

  svg {
    width: 100%;
    height: 100%;
    filter: drop-shadow(0 2px 8px rgba(249,115,22,0.3));
  }
}

.user-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px;
  border-radius: var(--radius-md);
  background: var(--c-sidebar-surface);
  border: 1px solid rgba(255,255,255,0.06);
  margin-bottom: 20px;
  position: relative;
}

.avatar {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  background: linear-gradient(135deg, var(--c-orange), var(--c-cyan));
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: 'Outfit', sans-serif;
  font-size: 16px;
  font-weight: 700;
  flex-shrink: 0;
}

.user-online-dot {
  position: absolute;
  right: 14px;
  top: 50%;
  transform: translateY(-50%);
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #22c55e;
  box-shadow: 0 0 6px rgba(34,197,94,0.5);
}

.user-meta {
  min-width: 0;
  flex: 1;

  .username {
    margin: 0 0 2px;
    color: #fff;
    font-size: 14px;
    font-weight: 700;
    word-break: break-word;
  }

  .role {
    margin: 0;
    color: var(--c-sidebar-text-dim);
    font-size: 12px;
  }
}

/* ---- Room list ---- */
.room-section {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.room-section-header {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  padding: 0 4px;

  h3 {
    margin: 0;
    font-size: 11px;
    font-weight: 700;
    color: var(--c-sidebar-text-dim);
    text-transform: uppercase;
    letter-spacing: 0.1em;
  }
}

.room-header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.refresh-btn {
  width: 28px;
  height: 28px;
  border: none;
  border-radius: 8px;
  background: var(--c-sidebar-surface);
  color: var(--c-sidebar-text);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s, color 0.2s;

  &:hover:not(:disabled) {
    background: rgba(255,255,255,0.1);
    color: var(--c-cyan);
  }

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
}

.room-empty {
  padding: 16px;
  border-radius: var(--radius-md);
  background: var(--c-sidebar-surface);
  color: var(--c-sidebar-text-dim);
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.room-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  overflow-y: auto;
  padding-right: 4px;
  min-width: 0;

  &::-webkit-scrollbar {
    width: 4px;
  }
  &::-webkit-scrollbar-track {
    background: transparent;
  }
  &::-webkit-scrollbar-thumb {
    background: rgba(255,255,255,0.1);
    border-radius: 2px;
  }
}

.room-item {
  width: 100%;
  border: 1px solid transparent;
  background: transparent;
  border-radius: var(--radius-md);
  padding: 12px;
  display: flex;
  gap: 12px;
  text-align: left;
  cursor: pointer;
  transition: all 0.2s ease;
  min-width: 0;
  color: inherit;

  &:hover {
    background: var(--c-sidebar-surface);
  }

  &.active {
    background: rgba(6,182,212,0.1);
    border-color: rgba(6,182,212,0.2);
  }
}

.room-avatar {
  width: 38px;
  height: 38px;
  border-radius: 12px;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: 'Outfit', sans-serif;
  font-size: 15px;
  font-weight: 700;
  flex-shrink: 0;

  &.private {
    background: linear-gradient(135deg, var(--c-cyan), #0e7490);
  }

  &.group {
    background: linear-gradient(135deg, var(--c-orange), #c2410c);
  }
}

.room-info {
  flex: 1;
  min-width: 0;
}

.room-top {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
  min-width: 0;
}

.room-name {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: rgba(255,255,255,0.9);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.room-type-badge {
  padding: 1px 7px;
  border-radius: 6px;
  font-size: 10px;
  font-weight: 600;
  flex-shrink: 0;
  letter-spacing: 0.02em;

  &.private {
    background: rgba(6,182,212,0.15);
    color: var(--c-cyan);
  }

  &.group {
    background: rgba(249,115,22,0.15);
    color: var(--c-orange);
  }
}

.room-bottom {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  font-size: 11px;
  color: var(--c-sidebar-text-dim);
}

.room-role {
  color: rgba(6,182,212,0.7);
}

.logout-btn {
  margin-top: 12px;
  height: 40px;
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: var(--radius-md);
  background: transparent;
  color: var(--c-sidebar-text);
  font-family: inherit;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  transition: background 0.2s, color 0.2s;

  &:hover {
    background: rgba(239,68,68,0.1);
    color: #fca5a5;
    border-color: rgba(239,68,68,0.2);
  }
}

/* ========== MAIN AREA ========== */
.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
}

.chat-header {
  padding: 18px 28px;
  background: var(--c-surface);
  border-bottom: 1px solid var(--c-border);

  h2 {
    margin: 0 0 4px;
    color: var(--c-text);
    font-family: 'Outfit', sans-serif;
    font-size: 20px;
    font-weight: 700;
  }

  p {
    margin: 0;
    color: var(--c-text-secondary);
    font-size: 13px;
    line-height: 1.5;
  }
}

.chat-header-main {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.chat-header-text {
  min-width: 0;
}

.empty-header h2 {
  margin-bottom: 4px;
}

.ws-status {
  flex-shrink: 0;
  padding: 5px 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  white-space: nowrap;
  display: flex;
  align-items: center;
  gap: 6px;

  .ws-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
  }

  &.idle .ws-dot,
  &.closed .ws-dot {
    background: #94a3b8;
  }

  &.connecting .ws-dot {
    background: #f59e0b;
    animation: pulse-dot 1.2s ease-in-out infinite;
  }

  &.connected .ws-dot {
    background: #22c55e;
    box-shadow: 0 0 4px rgba(34,197,94,0.5);
  }

  &.error .ws-dot {
    background: var(--c-danger);
  }

  &.idle, &.closed {
    background: #f1f5f9;
    color: #64748b;
  }

  &.connecting {
    background: #fffbeb;
    color: #b45309;
  }

  &.connected {
    background: #f0fdf4;
    color: #15803d;
  }

  &.error {
    background: #fef2f2;
    color: #b91c1c;
  }
}

@keyframes pulse-dot {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

/* ========== MESSAGE LIST ========== */
.message-list {
  flex: 1 1 0;
  padding: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  min-height: 0;
  background: var(--c-main-bg);
}

.message-area {
  position: relative;
  display: flex;
  flex-direction: column;
  flex: 1 1 0;
  min-height: 0;
}

.message-empty {
  margin: 24px;
  padding: 32px 24px;
  border-radius: var(--radius-lg);
  background: var(--c-surface);
  color: var(--c-text-secondary);
  box-shadow: 0 1px 3px rgba(15,23,42,0.04);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  font-size: 14px;
}

.welcome-empty {
  flex: 1;
  margin: 24px;
  justify-content: center;
}

.welcome-icon {
  color: var(--c-text-secondary);
}

.welcome-text {
  margin: 0;
  font-size: 15px;
  color: var(--c-text-secondary);
}

.message-scroll {
  flex: 1 1 0;
  min-height: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 20px 28px;

  &::-webkit-scrollbar {
    width: 5px;
  }
  &::-webkit-scrollbar-track {
    background: transparent;
  }
  &::-webkit-scrollbar-thumb {
    background: rgba(0,0,0,0.08);
    border-radius: 3px;
  }
}

.scroll-to-bottom-btn {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  bottom: 12px;
  border: none;
  border-radius: 999px;
  padding: 8px 18px;
  background: var(--c-sidebar-bg);
  color: #fff;
  font-family: inherit;
  font-size: 12px;
  font-weight: 600;
  box-shadow: 0 4px 16px rgba(15,23,42,0.2);
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
  z-index: 5;
}

.fade-up-enter-active,
.fade-up-leave-active {
  transition: all 0.25s ease;
}
.fade-up-enter-from,
.fade-up-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(8px);
}

/* ---- Message rows ---- */
.message-row {
  display: flex;
  align-items: flex-start;
  gap: 10px;

  &.mine {
    flex-direction: row-reverse;

    .message-body {
      align-items: flex-end;
    }

    .message-meta {
      flex-direction: row-reverse;
    }
  }
}

.message-avatar-col {
  flex-shrink: 0;
  padding-top: 20px;
}

.msg-avatar {
  width: 32px;
  height: 32px;
  border-radius: 10px;
  background: linear-gradient(135deg, var(--c-cyan), var(--c-cyan-deep));
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: 'Outfit', sans-serif;
  font-size: 13px;
  font-weight: 700;
}

.message-body {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  max-width: min(72%, 540px);
  min-width: 0;
}

.message-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
  font-size: 11px;
  color: #94a3b8;

  .sender {
    font-weight: 600;
    color: var(--c-text-secondary);
  }
}

.message-bubble {
  padding: 10px 14px;
  border-radius: 16px 16px 16px 4px;
  background: var(--c-surface);
  color: var(--c-text);
  box-shadow: 0 1px 3px rgba(15,23,42,0.05);
  border: 1px solid var(--c-border);
  word-break: break-word;

  &.mine {
    background: linear-gradient(135deg, var(--c-orange) 0%, var(--c-orange-hover) 100%);
    color: #fff;
    border-color: transparent;
    border-radius: 16px 16px 4px 16px;
    box-shadow: 0 2px 8px rgba(249,115,22,0.2);
  }

  &.recalled {
    background: var(--c-main-bg);
    color: #94a3b8;
    border-style: dashed;
    border-color: var(--c-border);
  }
}

.message-actions {
  display: flex;
  gap: 6px;
  margin-top: 4px;
  opacity: 0;
  transform: translateY(-2px);
  pointer-events: none;
  transition: opacity 0.18s ease, transform 0.18s ease;

  &.mine {
    justify-content: flex-end;
  }
}

.message-row.has-actions:hover .message-actions,
.message-row.has-actions:focus-within .message-actions,
.message-row.replying-target .message-actions {
  opacity: 1;
  transform: translateY(0);
  pointer-events: auto;
}

.reply-btn,
.recall-btn {
  border: none;
  background: transparent;
  color: #94a3b8;
  font-family: inherit;
  font-size: 11px;
  cursor: pointer;
  padding: 2px 6px;
  border-radius: 6px;
  transition: color 0.2s, background 0.2s, opacity 0.2s;

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
}

.reply-btn {
  &:hover:enabled,
  &.active {
    color: var(--c-cyan-deep);
    background: rgba(6,182,212,0.08);
  }
}

.recall-btn {
  &:hover:enabled {
    color: var(--c-danger);
    background: rgba(239,68,68,0.06);
  }
}

.reply-preview {
  margin: 0 0 8px;
  padding: 8px 10px;
  border-radius: 10px;
  background: rgba(15, 23, 42, 0.06);
  border-left: 3px solid rgba(6, 182, 212, 0.75);
}

.message-bubble.mine .reply-preview {
  background: rgba(255, 255, 255, 0.14);
  border-left-color: rgba(255, 255, 255, 0.75);
}

.reply-preview.missing {
  opacity: 0.82;
}

.reply-preview.clickable {
  cursor: pointer;
  transition: background 0.2s, transform 0.2s, border-left-color 0.2s;
}

.reply-preview.clickable:hover {
  background: rgba(15, 23, 42, 0.09);
  transform: translateY(-1px);
}

.message-bubble.mine .reply-preview.clickable:hover {
  background: rgba(255, 255, 255, 0.18);
}

.reply-preview-label {
  margin: 0 0 4px;
  font-size: 11px;
  font-weight: 700;
  line-height: 1.4;
  opacity: 0.92;
}

.reply-preview-content {
  margin: 0;
  font-size: 12px;
  line-height: 1.45;
  opacity: 0.78;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.message-row.jump-highlight .message-bubble {
  animation: jump-highlight-flash 1.8s ease;
  box-shadow:
    0 0 0 2px rgba(6, 182, 212, 0.24),
    0 10px 26px rgba(6, 182, 212, 0.14);
}

.message-row.jump-highlight.mine .message-bubble {
  box-shadow:
    0 0 0 2px rgba(255, 255, 255, 0.30),
    0 10px 28px rgba(249, 115, 22, 0.20);
}

.message-content,
.recalled-text {
  margin: 0;
  line-height: 1.65;
  font-size: 14px;
  word-break: break-word;
}

.empty-message-content {
  opacity: 0.65;
}

/* ---- Attachments ---- */
.attachment-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 8px;
}

.image-list {
  max-width: 100%;
}

.image-attachment-link {
  display: block;
  width: 260px;
  max-width: min(260px, 100%);
  border-radius: 12px;
  overflow: hidden;
}

.image-attachment-preview {
  display: block;
  width: 100%;
  max-width: 260px;
  aspect-ratio: 16 / 10;
  max-height: 300px;
  object-fit: contain;
  border-radius: 12px;
  border: 1px solid rgba(226,232,240,0.8);
  background: var(--c-main-bg);
}

.message-bubble.mine .image-attachment-preview {
  border-color: rgba(255,255,255,0.2);
}

.file-attachment-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 12px;
  text-decoration: none;
  color: inherit;
  background: rgba(248,250,252,0.9);
  border: 1px solid var(--c-border);
  transition: transform 0.15s, box-shadow 0.15s;

  &:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(15,23,42,0.08);
  }
}

.message-bubble.mine .file-attachment-card {
  background: rgba(255,255,255,0.12);
  border-color: rgba(255,255,255,0.18);
}

.file-attachment-icon {
  width: 36px;
  height: 36px;
  border-radius: var(--radius-sm);
  background: var(--c-cyan-subtle);
  color: var(--c-cyan-deep);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.message-bubble.mine .file-attachment-icon {
  background: rgba(255,255,255,0.15);
  color: #fff;
}

.file-attachment-meta {
  min-width: 0;
  flex: 1;
}

.file-attachment-name {
  margin: 0 0 2px;
  font-size: 13px;
  font-weight: 600;
  word-break: break-word;
}

.file-attachment-sub {
  margin: 0;
  font-size: 11px;
  opacity: 0.7;
  word-break: break-word;
}

/* ========== COMPOSER ========== */
.message-composer {
  flex-shrink: 0;
  padding: 14px 24px 18px;
  background: var(--c-surface);
  border-top: 1px solid var(--c-border);
}

.composer-box {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.file-input-hidden {
  display: none;
}

.reply-draft-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 12px;
  background: rgba(6,182,212,0.06);
  border: 1px solid rgba(6,182,212,0.14);
}

.reply-draft-text {
  min-width: 0;
  flex: 1;
}

.reply-draft-label {
  margin: 0 0 3px;
  font-size: 12px;
  font-weight: 700;
  color: var(--c-cyan-deep);
}

.reply-draft-content {
  margin: 0;
  font-size: 12px;
  line-height: 1.45;
  color: var(--c-text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.reply-draft-cancel {
  height: 30px;
  padding: 0 10px;
  border: none;
  border-radius: 8px;
  background: rgba(15,23,42,0.06);
  color: var(--c-text-secondary);
  font-family: inherit;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  flex-shrink: 0;
  transition: background 0.2s, color 0.2s;

  &:hover {
    background: rgba(239,68,68,0.08);
    color: var(--c-danger);
  }
}

.composer-input-row {
  position: relative;
}

.composer-input {
  width: 100%;
  min-height: 48px;
  max-height: 160px;
  resize: none;
  border: 1.5px solid var(--c-border);
  border-radius: var(--radius-md);
  padding: 12px 16px;
  font-family: inherit;
  font-size: 14px;
  line-height: 1.6;
  color: var(--c-text);
  outline: none;
  box-sizing: border-box;
  background: var(--c-main-bg);
  transition: border-color 0.2s, box-shadow 0.2s, background 0.2s;

  &::placeholder {
    color: #94a3b8;
  }

  &:focus {
    border-color: var(--c-cyan);
    background: var(--c-surface);
    box-shadow: 0 0 0 3px rgba(6,182,212,0.1);
  }
}

.composer-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.composer-feedback {
  flex: 1;
  min-width: 0;
}

.send-error,
.send-pending,
.send-hint {
  margin: 0;
  font-size: 12px;
  line-height: 1.5;
}

.send-error {
  color: var(--c-danger);
}

.send-pending {
  color: #b45309;
}

.send-hint {
  color: #94a3b8;
}

.composer-buttons {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.upload-btn {
  height: 40px;
  padding: 0 14px;
  border: 1.5px solid var(--c-border);
  border-radius: var(--radius-sm);
  background: var(--c-surface);
  color: var(--c-text-secondary);
  font-family: inherit;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
  transition: border-color 0.2s, color 0.2s;

  &:hover:not(:disabled) {
    border-color: var(--c-cyan);
    color: var(--c-cyan-deep);
  }

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
}

.reconnect-btn {
  height: 40px;
  padding: 0 16px;
  border: 1.5px solid var(--c-border);
  border-radius: var(--radius-sm);
  background: var(--c-surface);
  color: var(--c-text-secondary);
  font-family: inherit;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: border-color 0.2s;

  &:hover {
    border-color: var(--c-orange);
    color: var(--c-orange);
  }
}

.send-btn {
  width: 44px;
  height: 40px;
  border: none;
  border-radius: var(--radius-sm);
  background: linear-gradient(135deg, var(--c-orange) 0%, var(--c-orange-hover) 100%);
  color: #fff;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: transform 0.15s, box-shadow 0.15s, opacity 0.2s;
  box-shadow: 0 2px 8px rgba(249,115,22,0.25);

  &:hover:not(:disabled) {
    transform: translateY(-1px);
    box-shadow: 0 4px 14px rgba(249,115,22,0.35);
  }

  &:disabled {
    opacity: 0.45;
    cursor: not-allowed;
    box-shadow: none;
  }
}

/* ========== SPINNERS ========== */
.spinner {
  width: 24px;
  height: 24px;
  border: 2.5px solid var(--c-border);
  border-top-color: var(--c-cyan);
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

.spinner-tiny {
  display: inline-block;
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255,255,255,0.25);
  border-top-color: currentColor;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@keyframes jump-highlight-flash {
  0% {
    transform: scale(0.985);
  }
  20% {
    transform: scale(1.008);
  }
  100% {
    transform: scale(1);
  }
}

/* ========== MOBILE ========== */
.mobile-menu-btn {
  display: none;
}

.sidebar-overlay {
  display: none;
}

@media (max-width: 900px) {
  .sidebar {
    position: fixed;
    left: 0;
    top: 0;
    bottom: 0;
    width: 300px;
    transform: translateX(-100%);
    transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    z-index: 100;
    box-shadow: none;

    &.open {
      transform: translateX(0);
      box-shadow: 8px 0 30px rgba(0,0,0,0.3);
    }
  }

  .sidebar-overlay {
    display: block;
    position: fixed;
    inset: 0;
    z-index: 99;
    background: rgba(0,0,0,0.4);
    backdrop-filter: blur(2px);
    -webkit-backdrop-filter: blur(2px);
    animation: fade-in 0.2s ease;
  }

  @keyframes fade-in {
    from { opacity: 0; }
  }

  .mobile-menu-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    position: fixed;
    top: 14px;
    left: 14px;
    z-index: 30;
    width: 40px;
    height: 40px;
    border: none;
    border-radius: 12px;
    background: var(--c-surface);
    box-shadow: 0 2px 10px rgba(15,23,42,0.1);
    color: var(--c-text);
    cursor: pointer;

    svg {
      width: 20px;
      height: 20px;
    }
  }

  .chat-header {
    padding: 16px 16px 16px 64px;
  }

  .message-scroll {
    padding: 16px;
  }

  .message-composer {
    padding: 12px 16px 16px;
  }

  .message-body {
    max-width: 85%;
  }
}

@media (max-width: 640px) {
  .chat-header {
    h2 { font-size: 18px; }
    p { font-size: 12px; }
  }

  .chat-header-main {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }

  .message-scroll {
    padding: 12px;
    gap: 6px;
  }

  .message-body {
    max-width: 88%;
  }

  .message-actions {
    opacity: 1;
    transform: none;
    pointer-events: auto;
  }

  .message-bubble {
    padding: 9px 12px;
    border-radius: 14px 14px 14px 4px;

    &.mine {
      border-radius: 14px 14px 4px 14px;
    }
  }

  .message-meta {
    font-size: 10px;
  }

  .msg-avatar {
    width: 28px;
    height: 28px;
    font-size: 11px;
    border-radius: 8px;
  }

  .composer-input {
    min-height: 44px;
    font-size: 14px;
    padding: 10px 14px;
  }

  .composer-actions {
    flex-direction: column;
    align-items: stretch;
    gap: 8px;
  }

  .composer-buttons {
    width: 100%;
    justify-content: flex-end;
  }

  .upload-label {
    display: none;
  }

  .upload-btn {
    width: 40px;
    padding: 0;
    justify-content: center;
  }
}
</style>

<style scoped>
.room-preview { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; min-width: 0; }
.unread-badge { padding: 2px 6px; border-radius: 20px; min-width: 20px; text-align: center; background: #f97316; color: #fff; font-size: 11px; flex-shrink: 0; }
.demo-reset-btn { border: 1px solid rgba(255,255,255,.16); color: #dce6f5; background: transparent; padding: 10px; border-radius: 10px; cursor: pointer; margin: 10px 0 4px; }
.room-error { flex-direction: column; align-items: flex-start; color: #fecaca; }
.room-error button { border: 0; background: transparent; color: #fb923c; padding: 4px 0; cursor: pointer; }
.history-control { color: #64748b; font-size: 12px; text-align: center; padding: 0 0 20px; }
.history-btn { border: 1px solid #cbd5e1; background: white; color: #475569; padding: 8px 16px; border-radius: 20px; cursor: pointer; }
.history-error { color: #b91c1c; padding-top: 8px; }
.history-error button { border: 0; background: transparent; color: #b91c1c; text-decoration: underline; cursor: pointer; }
.reply-preview { display: block; width: 100%; border-top: 0; border-right: 0; border-bottom: 0; text-align: left; font-family: inherit; color: inherit; cursor: pointer; }
.retry-send-btn, .discard-send-btn { border: 0; border-radius: 8px; background: #fff7ed; color: #c2410c; cursor: pointer; padding: 8px 10px; font-size: 12px; white-space: nowrap; }
.discard-send-btn { background: transparent; font-size: 18px; padding: 4px; }
.chat-main { min-height: 0; }
.message-composer { padding-bottom: max(16px, env(safe-area-inset-bottom)); }
@media (max-width: 768px) { .composer-feedback { min-width: 0; } .send-hint { display: none; } .sidebar { padding-top: max(20px, env(safe-area-inset-top)); padding-bottom: max(16px, env(safe-area-inset-bottom)); } }
@media (max-height: 600px) { .user-card { margin-bottom: 12px; padding: 10px; } .brand-block { margin-bottom: 14px; } .message-composer { padding-top: 8px; padding-bottom: max(8px, env(safe-area-inset-bottom)); } .composer-input { min-height: 48px; height: 48px; } }
</style>
