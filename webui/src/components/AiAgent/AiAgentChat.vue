<!--
  Copyright© 2024-2026 China Mobile (SuZhou) Software Technology Co.,Ltd.

  qcos is licensed under Mulan PSL v2.
  You can use this software according to the terms and conditions
  of the Mulan PSL v2.
  You may obtain a copy of Mulan PSL v2 at:
          http://license.coscl.org.cn/MulanPSL2
  THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS,
      WITHOUT WARRANTIES OF ANY KIND,
  EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
  MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
  See the Mulan PSL v2 for more details.
-->

<template>
  <div
    class="ai-agent-chat"
    @dragenter="onDragEnter"
    @dragover="onDragOver"
    @dragleave="onDragLeave"
    @drop="onDrop"
  >
    <!-- Drag-over overlay: visible while a file is being dragged
         over the chat area. -->
    <div v-if="isDragOver" class="ai-agent-drag-overlay">
      <div class="drag-overlay-content">
        <ImageIcon size="32" />
        <span>松开以添加图片到当前消息</span>
      </div>
    </div>
    <!-- Main column: messages + input. -->
    <div class="ai-agent-main">
    <!-- Messages area: TDesign Chat list. Renders bubbles, avatars,
         streaming skeleton, and reasoning UI out of the box. We feed
         it a derived `chatData` array mapped from the aiAgent store. -->
    <div class="ai-agent-messages">
      <!-- Floating edge toggle for the session-history panel. Lives
           INSIDE .ai-agent-messages so `top:50%` tracks the messages
           area (not the full panel including the input below), which
           matches how the global sidebar toggle centers itself. -->
      <t-tooltip
        :content="showSessionList ? '收起会话历史' : '展开会话历史'"
        placement="right"
      >
        <button
          type="button"
          class="ai-agent-edge-toggle"
          :class="{ 'is-open': showSessionList }"
          :aria-label="showSessionList ? '收起会话历史' : '展开会话历史'"
          @click="onToggleSessionList"
        >
          <ChevronLeftIcon v-if="showSessionList" />
          <ChevronRightIcon v-else />
        </button>
      </t-tooltip>
      <div v-if="chatData.length === 0" class="ai-agent-empty">
        <t-empty description="开始对话吧">
          <template #image>
            <svg-icon icon-class="ai-robot" class="empty-icon" />
          </template>
        </t-empty>
      </div>
      <!-- Let <t-chat-list> render bubbles itself. We feed it typed
           content blocks (markdown / text / image), so no #content
           slot is needed - TDesign picks the right renderer per block. -->
      <t-chat-list
        v-else
        ref="chatListRef"
        :data="chatData"
        :text-loading="waitingForResponse"
        :clear-history="false"
        animation="skeleton"
        layout="both"
      >
        <!-- Per-message action bar (Cherry Studio style):
             copy / retry (assistant only) / delete + token usage.
             Subtle grey icons that highlight on hover. -->
        <template #actions="{ item }">
          <!-- Two-container layout: left = icon buttons, right =
               disclaimer + token chip. The outer flex uses
               justify-content: space-between so the right block is
               pinned to the far edge regardless of the icon count. -->
          <div class="message-actions" :class="`is-${item.role}`">
            <div class="message-actions-left">
              <t-tooltip content="复制" placement="top">
                <t-button
                  size="small"
                  variant="text"
                  shape="square"
                  class="action-btn"
                  @click="onCopyMessage(item)"
                >
                  <template #icon><CopyIcon /></template>
                </t-button>
              </t-tooltip>
              <t-tooltip v-if="item.role === 'assistant'" content="重新生成" placement="top">
                <t-button
                  size="small"
                  variant="text"
                  shape="square"
                  class="action-btn"
                  :disabled="streaming"
                  @click="onRetryMessage(item)"
                >
                  <template #icon><RefreshIcon /></template>
                </t-button>
              </t-tooltip>
              <t-tooltip content="删除" placement="top">
                <t-button
                  size="small"
                  variant="text"
                  shape="square"
                  class="action-btn action-btn-danger"
                  @click="onDeleteMessage(item)"
                >
                  <template #icon><DeleteIcon /></template>
                </t-button>
              </t-tooltip>
            </div>
            <div class="message-actions-right">
              <span class="message-token-usage">
                <template v-if="item.role === 'assistant'">
                  ↑ {{ formatTokens(getMessageInputTokens(item)) }}
                  ↓ {{ formatTokens(getMessageOutputTokens(item)) }}
                </template>
                <template v-else>
                  ↑ {{ formatTokens(getMessageInputTokens(item)) }}
                </template>
              </span>
              <span
                v-if="item.role === 'assistant'"
                class="message-disclaimer"
              >
                本回答由AI生成，仅供参考
              </span>
            </div>
          </div>
        </template>
      </t-chat-list>
      <div v-if="pendingToolCall" class="ai-agent-tool-call">
        <t-tag theme="default" variant="light" size="small">
          正在调用工具: {{ pendingToolCall.tool }}
        </t-tag>
      </div>
      <div v-if="waitingForResponse" class="ai-agent-waiting">
        <t-loading size="small" text="AI 助手正在思考中..." />
      </div>
      <!-- Custom scroll controls: stack "回到顶部" + "回到底部"
           on the right edge of the messages area. TDesign only
           ships a built-in to-bottom button; we add a twin for
           to-top so the user can jump in either direction. -->
      <div class="ai-agent-scroll-controls">
        <t-tooltip content="回到顶部" placement="left">
          <t-button
            size="small"
            variant="outline"
            shape="square"
            class="scroll-ctrl-btn"
            @click="scrollToTop"
          >
            <template #icon><ArrowUpIcon /></template>
          </t-button>
        </t-tooltip>
        <t-tooltip content="回到底部" placement="left">
          <t-button
            size="small"
            variant="outline"
            shape="square"
            class="scroll-ctrl-btn"
            @click="scrollToBottom"
          >
            <template #icon><ArrowDownIcon /></template>
          </t-button>
        </t-tooltip>
      </div>
    </div>

    <!-- Queued messages (grey box): shown while a previous stream is
         still in flight and the user has typed additional messages.
         Each row is individually cancellable via its delete icon. -->
    <div v-if="messageQueue.length > 0" class="ai-agent-queue">
      <div class="ai-agent-queue-header">
        <span class="queue-header-label">队列消息 ({{ messageQueue.length }})</span>
      </div>
      <div
        v-for="m in messageQueue"
        :key="m.id"
        class="ai-agent-queue-item"
      >
        <span class="queue-item-text">{{ m.text }}</span>
        <span
          class="queue-item-delete"
          @click="store.removeQueuedMessage(m.id)"
        >
          <DeleteIcon size="14" />
        </span>
      </div>
    </div>

    <!-- Pending image attachments preview -->
    <div v-if="pendingAttachments.length > 0" class="ai-agent-attachments">
      <div
        v-for="(att, idx) in pendingAttachments"
        :key="idx"
        class="attachment-preview"
      >
        <t-image
          :src="`data:${att.media_type};base64,${att.data}`"
          fit="cover"
          class="attachment-image"
        />
        <span class="attachment-remove" @click="removeAttachment(idx)">
          <CloseIcon size="14" />
        </span>
      </div>
    </div>

    <!-- Input area: text input on top, toolbar at bottom (like Cherry Studio) -->
    <div class="ai-agent-input-area">
      <t-textarea
        v-model="draft"
        placeholder="输入消息... (Ctrl+Enter 发送)"
        :autosize="{ minRows: 3, maxRows: 12 }"
        class="ai-agent-textarea"
        :on-keydown="onKeydown"
        :on-paste="onPaste"
      />
      <div class="ai-agent-input-toolbar">
        <div class="toolbar-left">
          <!-- RAG toggle as icon button. Disabled (with explanatory
               tooltip) when the backend embedding service is not
               configured. -->
          <t-tooltip
            :content="embeddingEnabled
              ? (enableRag ? '关闭知识库检索' : '启用知识库检索')
              : '知识库检索能力未启动'"
            placement="top"
          >
            <t-button
              size="small"
              variant="text"
              shape="square"
              :class="{ 'is-active': enableRag && embeddingEnabled, 'is-disabled': !embeddingEnabled }"
              :disabled="!embeddingEnabled"
              @click="toggleRag"
            >
              <template #icon><BookIcon /></template>
            </t-button>
          </t-tooltip>
          <!-- Image upload as icon button. Disabled when the backend
               has no vision model configured (the LLM would silently
               drop the attachment without analysing it). -->
          <t-tooltip
            :content="visionEnabled
              ? '粘贴 / 拖拽 / 点击上传图片'
              : '后端AI大模型不具备图片分析功能'"
            placement="top"
          >
            <t-button
              size="small"
              variant="text"
              shape="square"
              :disabled="!visionEnabled"
              @click="triggerFileInput"
            >
              <template #icon><ImageIcon /></template>
            </t-button>
          </t-tooltip>
          <!-- Clear current session as icon button. Uses a t-dialog
               (instead of t-popconfirm) so the confirmation is
               guaranteed to fire even when the button is rendered
               inside a tooltip / popper nesting context that breaks
               popconfirm's trigger wiring. -->
          <t-tooltip content="清空当前会话" placement="top">
            <t-button
              size="small"
              variant="text"
              shape="square"
              @click="showClearConfirm = true"
            >
              <template #icon><ClearIcon /></template>
            </t-button>
          </t-tooltip>
          <!-- Queued-send indicator: visible only while messages are
               waiting in the store's sequential send queue. -->
          <t-tooltip content="排队中的消息会按顺序在 AI 回答完成后发送" placement="top">
            <t-tag
              v-if="messageQueue.length > 0"
              size="small"
              theme="warning"
              variant="light"
              class="queue-indicator"
            >
              队列 {{ messageQueue.length }}
            </t-tag>
          </t-tooltip>
        </div>
        <!-- Middle container: context-window donut + token stats.
             Sits between the left button group and the right
             stop/send buttons so the readout is the visual anchor
             of the toolbar. -->
        <div class="toolbar-center">
          <t-tooltip placement="top">
            <template #content>
              <div class="token-usage-tooltip">
                <div>输入 Tokens: {{ tokenUsage.inputTokens }}</div>
                <div>输出 Tokens: {{ tokenUsage.outputTokens }}</div>
                <div>合计: {{ totalUsedTokens }}</div>
                <div>上下文窗口: {{ effectiveContextWindow }}</div>
                <div>已用占比: {{ contextUsedPercent }}%</div>
              </div>
            </template>
            <span class="token-usage-donut">
              <svg
                class="donut-svg"
                viewBox="0 0 32 32"
                role="img"
                :aria-label="`上下文已用 ${contextUsedPercent}%`"
              >
                <circle
                  class="donut-track"
                  cx="16" cy="16" r="14"
                  fill="none"
                  stroke-width="4"
                />
                <circle
                  class="donut-fill"
                  cx="16" cy="16" r="14"
                  fill="none"
                  stroke-width="4"
                  stroke-linecap="round"
                  :stroke-dasharray="`${donutArc} 87.96`"
                  transform="rotate(-90 16 16)"
                />
                <text
                  class="donut-text"
                  x="16" y="19"
                  text-anchor="middle"
                >
                  {{ contextUsedPercent }}%
                </text>
              </svg>
              <span class="donut-numbers">
                {{ formatTokens(totalUsedTokens) }}
                <span class="donut-divider">/</span>
                {{ formatTokens(effectiveContextWindow) }}
              </span>
            </span>
          </t-tooltip>
        </div>
        <div class="toolbar-right">
          <!-- Stop button shown only while a stream is in flight.
               Sends are NOT blocked - the user can keep typing and
               hit send to enqueue the next message; it will be sent
               automatically once the current stream finishes (see
               store.messageQueue). -->
          <t-button
            v-if="streaming"
            size="small"
            theme="danger"
            shape="square"
            @click="handleStop"
          >
            <template #icon><StopIcon /></template>
          </t-button>
          <!-- Send button: always available. While streaming the new
               message is appended to the store's send queue and
               delivered FIFO. -->
          <t-button
            size="small"
            theme="primary"
            shape="square"
            :disabled="!draft && pendingAttachments.length === 0"
            @click="onSend"
          >
            <template #icon><SendIcon /></template>
          </t-button>
        </div>
      </div>
      <input
        ref="fileInputRef"
        type="file"
        accept="image/*"
        multiple
        style="display: none"
        @change="onFileSelect"
      >

      <!-- Confirmation dialog for "clear current session". Using a
           t-dialog (rather than popconfirm) because the button lives
           inside the chat toolbar where a popconfirm's trigger has
           proven unreliable. -->
      <t-dialog
        v-model:visible="showClearConfirm"
        header="清空当前会话"
        :confirm-btn="{ content: '清空', theme: 'danger' }"
        cancel-btn="取消"
        @confirm="onConfirmClear"
      >
        确定清空当前会话的全部消息吗？此操作不可恢复。
      </t-dialog>
    </div>

    </div>
  </div>
</template>

<script setup>
import { ref, computed, inject } from 'vue'
import { MessagePlugin } from 'tdesign-vue-next'
import { CloseIcon, ImageIcon, CopyIcon, BookIcon, SendIcon, StopIcon, ClearIcon, ChevronLeftIcon, ChevronRightIcon, DeleteIcon, RefreshIcon, ArrowUpIcon, ArrowDownIcon } from 'tdesign-icons-vue-next'
import { useAiAgentStore } from '@/store/modules/aiAgent'
import { useUserStore } from '@/store/modules/user'
import { useComponentsStore } from '@/store/modules/components'
import { compressImage } from '@/utils/imageCompress'
// Default avatars shown in the chat bubbles. The user avatar comes
// from the user store (falls back to the bundled default if the user
// hasn't uploaded one). The assistant avatar reuses the same robot
// SVG shown in the navbar AI-agent button so the chat bubbles are
// visually consistent with the rest of the app.
import defaultUserAvatar from '@/assets/avatar/default_avatar.png'
import aiRobotSvgRaw from '@/icons/svg/ai-robot.svg?raw'

const AI_AVATAR_SVG = 'data:image/svg+xml;utf8,' + encodeURIComponent(aiRobotSvgRaw)

const store = useAiAgentStore()
const userStore = useUserStore()
const componentsStore = useComponentsStore()

// Resolved once per session: the user avatar shown next to user bubbles.
const userAvatar = computed(() => userStore.avatar || defaultUserAvatar)

const fileInputRef = ref(null)
const draft = ref('')
// Controls the visibility of the "clear current session" t-dialog.
const showClearConfirm = ref(false)

// Input history for up/down arrow navigation
const inputHistory = ref([])
const historyIndex = ref(-1)
const draftBackup = ref('')

const streaming = computed(() => store.streaming)
const waitingForResponse = computed(() => store.waitingForResponse)
const pendingToolCall = computed(() => store.pendingToolCall)
const pendingAttachments = computed(() => store.pendingAttachments)
const messageQueue = computed(() => store.messageQueue)
const embeddingEnabled = computed(() => componentsStore.embeddingEnabled)
// Cumulative token counters across the current session. Fed by the
// backend's `usage` payload on every RUN_FINISHED event.
const tokenUsage = computed(() => store.tokenUsage)
// Keep the computed for backwards compatibility with any external
// callers; the chip itself is now always rendered so this flag is
// no longer consulted from the template.
const hasTokenUsage = computed(() => store.messages.length > 0)

// Total tokens consumed in this session = input + output. Used by
// the donut readout in the toolbar.
const totalUsedTokens = computed(
  () => (tokenUsage.value.inputTokens || 0) + (tokenUsage.value.outputTokens || 0)
)

// Effective context-window size: prefer the value reported by the
// backend; fall back to 128k (a common default for GLM / Qwen /
// Doubao-class models) so the donut never shows "0 / 0" before the
// first response comes back. The backend value overwrites the
// default as soon as it arrives.
const DEFAULT_CONTEXT_WINDOW = 128 * 1024
const effectiveContextWindow = computed(
  () => tokenUsage.value.contextWindow > 0
    ? tokenUsage.value.contextWindow
    : DEFAULT_CONTEXT_WINDOW
)

// Used percentage of the context window, clamped to [0, 100].
const contextUsedPercent = computed(() => {
  const win = effectiveContextWindow.value
  if (win <= 0) return 0
  const pct = (totalUsedTokens.value / win) * 100
  // Round to integer for display; clamp at 100 so the ring never
  // overflows visually even when the actual usage exceeds the
  // reported window.
  return Math.min(100, Math.max(0, Math.round(pct)))
})

// SVG arc length for the donut's filled portion. Circumference of
// r=14 is 2πr ≈ 87.96 - we multiply by the percentage to get the
// visible arc.
const donutArc = computed(() => ((contextUsedPercent.value / 100) * 87.96).toFixed(2))
/**
 * Format a token count for the status bar. Always uses the `k`
 * suffix (per UX spec) so the context-window readout stays compact
 * and consistent - e.g. 128k for a 128k-token window, 92.4k for
 * 92,400 tokens consumed. Values below 1000 are shown verbatim.
 */
function formatTokens(n) {
  if (!n || n <= 0) return '0'
  if (n < 1000) return String(n)
  return (n / 1000).toFixed(1).replace(/\.0$/, '') + 'k'
}
// Mirrors the backend `is_vision_enabled()` flag exposed via /version's
// `components.vision` field; when false the image-attachment button is
// disabled with a tooltip explaining the backend has no vision support.
const visionEnabled = computed(() => componentsStore.visionEnabled)
const enableRag = computed({
  get: () => store.enableRag && embeddingEnabled.value,
  set: v => store.setEnableRag(v)
})

// Inject the session-list toggle from the parent AiAgentContainer so
// the toolbar history button can open the panel without prop drilling.
const showSessionList = inject('showSessionList', ref(false))

/**
 * Toggle the session-history panel. Bound to the History icon in the
 * left activity bar; clicking again collapses the panel.
 */
function onToggleSessionList() {
  showSessionList.value = !showSessionList.value
}

/**
 * The chat list is bound directly to `store.chatItems`, which the
 * store maintains imperatively alongside `messages`. Each item
 * keeps stable object identity across SSE chunks (and its content
 * blocks keep stable references too), which is what TDesign Chat's
 * internal typewriter animation needs to recognise deltas.
 *
 * We register a meta-resolver on the store so it can call back
 * into this view for user-specific data (name, avatar, formatted
 * datetime) without introducing a circular dependency on Pinia.
 */
store._chatItemMetaResolver = (m) => {
  const isAssistant = m.role === 'assistant'
  return {
    name: isAssistant ? 'AI 助手' : (userStore.name || '我'),
    avatar: isAssistant ? AI_AVATAR_SVG : userAvatar.value,
    datetime: m.createdAt ? formatDatetime(m.createdAt) : ''
  }
}

const chatData = computed(() => store.chatItems)

function formatDatetime(unixSeconds) {
  // Show only HH:MM for intraday; full date for older messages.
  const d = new Date(unixSeconds * 1000)
  const now = new Date()
  const sameDay = d.toDateString() === now.toDateString()
  if (sameDay) {
    return d.toTimeString().slice(0, 5)
  }
  const pad = n => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

/**
 * Handle keyboard events from the textarea. TDesign exposes the
 * `onKeydown` prop which receives `(value, { e })` where `e` is the
 * native KeyboardEvent. We use the prop form (not `@keydown`) because
 * TDesign's internal event wiring does not emit a standard `keydown`
 * Vue event - the prop is the only reliable way to intercept keys.
 */
function onKeydown(_value, context) {
  const e = context && context.e
  if (!e) return
  if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
    e.preventDefault()
    onSend().catch(err => {
      console.error('AI send failed:', err)
    })
    return
  }
  // Up/down arrow history navigation (like shell history)
  if (e.key === 'ArrowUp') {
    e.preventDefault()
    if (historyIndex.value === -1) {
      // Save current draft before entering history
      draftBackup.value = draft.value
    }
    if (historyIndex.value < inputHistory.value.length - 1) {
      historyIndex.value += 1
      draft.value = inputHistory.value[inputHistory.value.length - 1 - historyIndex.value]
    }
  } else if (e.key === 'ArrowDown') {
    e.preventDefault()
    if (historyIndex.value > 0) {
      historyIndex.value -= 1
      draft.value = inputHistory.value[inputHistory.value.length - 1 - historyIndex.value]
    } else if (historyIndex.value === 0) {
      // Restore the draft that was saved when entering history
      historyIndex.value = -1
      draft.value = draftBackup.value
    }
  }
}

/** Toggle RAG on/off via the toolbar icon button. */
function toggleRag() {
  store.setEnableRag(!store.enableRag)
}

/** Stop the currently streaming AI response. */
function handleStop() {
  store.cancelStreaming()
  MessagePlugin.info('已停止生成')
}

async function onSend() {
  const text = draft.value.trim()
  if (!text && pendingAttachments.value.length === 0) return
  // Save to input history for up/down navigation
  if (text) {
    inputHistory.value.push(text)
    // Keep history bounded (e.g. last 50 entries)
    if (inputHistory.value.length > 50) {
      inputHistory.value.shift()
    }
  }
  historyIndex.value = -1
  draftBackup.value = ''
  draft.value = ''
  try {
    await store.sendMessage(text)
  } catch (err) {
    MessagePlugin.error(`发送失败: ${err.message || 'AI 助手暂时不可用'}`)
  }
}

function triggerFileInput() {
  fileInputRef.value?.click()
}

/**
 * Compress an image file and append it to the pending-attachment
 * list. Shared by file-input / paste / drag-drop paths.
 */
async function processImageFile(f) {
  if (!f || !f.type.startsWith('image/')) return
  try {
    const compressed = await compressImage(f)
    store.addPendingAttachment(compressed)
  } catch (err) {
    console.error('Image compression failed:', err)
  }
}

async function onFileSelect(e) {
  const files = Array.from(e.target.files || [])
  for (const f of files) {
    await processImageFile(f)
  }
  e.target.value = ''
}

/*
 * Drag & drop support: dropping an image file anywhere on the chat
 * panel attaches it to the message being composed. We track drag
 * state to show a visual drop-zone highlight.
 */
const isDragOver = ref(false)

function onDragEnter(e) {
  if (!e.dataTransfer?.types?.includes('Files')) return
  e.preventDefault()
  isDragOver.value = true
}

function onDragOver(e) {
  if (!e.dataTransfer?.types?.includes('Files')) return
  e.preventDefault()
  // Required for the drop event to fire.
  e.dataTransfer.dropEffect = 'copy'
}

function onDragLeave(e) {
  // Only clear the highlight when the cursor actually leaves the
  // chat container (not when it moves between children).
  if (e.currentTarget.contains(e.relatedTarget)) return
  isDragOver.value = false
}

async function onDrop(e) {
  if (!e.dataTransfer?.files?.length) return
  e.preventDefault()
  isDragOver.value = false
  for (const f of e.dataTransfer.files) {
    await processImageFile(f)
  }
}

/**
 * TDesign textarea passes the paste event as the second argument of a
 * `(value, { e })` callback, just like onKeydown. Unwrap it before
 * reading the clipboard payload.
 */
function onPaste(_value, context) {
  const e = context && context.e
  if (!e) return
  const items = e.clipboardData?.items
  if (!items) return
  for (const item of items) {
    if (item.type.startsWith('image/')) {
      const file = item.getAsFile()
      if (file) {
        compressImage(file).then(compressed => {
          store.addPendingAttachment(compressed)
        })
      }
    }
  }
}

function removeAttachment(idx) {
  store.removePendingAttachment(idx)
}

/**
 * Handle the toolbar's "clear session" button: open the confirm
 * dialog. The dialog's @confirm hook below performs the actual
 * wipe. (Splitting open/confirm keeps the dialog flow symmetric
 * with the other "destructive action" dialogs in the app.)
 */
function onClearHistory() {
  showClearConfirm.value = true
}

/**
 * User confirmed the clear-session dialog. Wipe the local message
 * list, the cumulative token counters, and the backend session's
 * stored messages so a page reload does not resurrect them.
 */
async function onConfirmClear() {
  try {
    await store.clearMessages()
    // Reset the token-usage chip to 0 / 0 / 0 immediately so the
    // toolbar reflects the cleared session without waiting for the
    // next stream to finish.
    if (store.tokenUsage) {
      store.tokenUsage.inputTokens = 0
      store.tokenUsage.outputTokens = 0
      store.tokenUsage.contextWindow = 0
    }
    // The chat list keeps a cached scroll position keyed off the
    // previous content length; snap back to top so the next render
    // starts from a clean slate.
    scrollToTop()
    MessagePlugin.success('已清空当前会话')
  } catch (err) {
    MessagePlugin.error(`清空失败: ${err.message || '未知错误'}`)
  } finally {
    showClearConfirm.value = false
  }
}

/**
 * Ref to the t-chat-list instance so we can drive its scroll
 * position. The component exposes `scrollToBottom` (built-in); for
 * "scroll to top" we poke the inner list element directly.
 */
/**
 * Per-message token counters shown in the action bar. Backend
 * reports usage on the assistant message itself; for the user
 * message we fall back to a character-based estimate (1 token
 * ≈ 2 chars for Chinese text, 4 for English - we just use 2 as a
 * safe middle ground).
 */
function getMessageInputTokens(item) {
  const raw = item?._raw
  if (!raw) return 0
  if (raw.usage?.input_tokens) return raw.usage.input_tokens
  // Fallback: estimate from the message's text length.
  return Math.ceil((raw.content || '').length / 2)
}

function getMessageOutputTokens(item) {
  const raw = item?._raw
  if (!raw) return 0
  if (raw.usage?.output_tokens) return raw.usage.output_tokens
  return Math.ceil((raw.content || '').length / 2)
}

const chatListRef = ref(null)

/**
 * Locate the element that actually scrolls the chat list.
 *
 * TDesign Chat 0.7.0 renders <t-chat-list> as a Web Component with a
 * closed-ish Shadow DOM in some browsers, so the "obvious" queries
 * (ref.$el, document.querySelector('.t-chat-list')) can return a
 * non-scrollable wrapper while the real scroller is one level deeper.
 * We therefore walk through every plausible container and pick the
 * one whose scrollHeight exceeds its clientHeight - that is the
 * element the user can actually scroll. Falls back to the first
 * matching element when nothing scrollable is found yet (e.g. list
 * is empty).
 */
function _findScrollableChatEl() {
  const candidates = []
  const inst = chatListRef.value
  if (inst) {
    if (inst.$el) candidates.push(inst.$el)
    if (typeof inst.$el?.querySelector === 'function') {
      candidates.push(...inst.$el.querySelectorAll('.t-chat-list, .t-chat, [class*="chat"]'))
    }
    // Web Component host: try shadowRoot if exposed.
    if (inst.$el?.shadowRoot) {
      candidates.push(...inst.$el.shadowRoot.querySelectorAll('.t-chat-list, .t-chat, [class*="chat"]'))
    }
  }
  // Fallback: any .t-chat-list inside our messages container.
  const host = document.querySelector('.ai-agent-messages')
  if (host) {
    candidates.push(...host.querySelectorAll('.t-chat-list, .t-chat, [class*="chat"]'))
    // If the web-component is used, walk into its shadow root.
    for (const el of host.querySelectorAll('*')) {
      if (el.shadowRoot) {
        candidates.push(...el.shadowRoot.querySelectorAll('.t-chat-list, .t-chat, [class*="chat"]'))
      }
    }
  }
  // De-dup while preserving order.
  const seen = new Set()
  const uniq = candidates.filter(el => {
    if (!el || seen.has(el)) return false
    seen.add(el)
    return true
  })
  // Prefer a genuinely scrollable element; otherwise return the
  // first candidate (a scroll of 0 still resolves the promise).
  return uniq.find(el => el.scrollHeight > el.clientHeight) || uniq[0] || null
}

function scrollToBottom() {
  const inst = chatListRef.value
  if (inst && typeof inst.scrollToBottom === 'function') {
    try {
      inst.scrollToBottom({ behavior: 'smooth' })
      return
    } catch {
      // fall through to DOM path
    }
  }
  const el = _findScrollableChatEl()
  if (!el) return
  if (typeof el.scrollTo === 'function') {
    el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' })
  } else {
    el.scrollTop = el.scrollHeight
  }
}

function scrollToTop() {
  const el = _findScrollableChatEl()
  if (!el) return
  if (typeof el.scrollTo === 'function') {
    el.scrollTo({ top: 0, behavior: 'smooth' })
  } else {
    el.scrollTop = 0
  }
}

/**
 * Retry the assistant's reply: drop the assistant + user message
 * pair, then re-send the user prompt.
 */
async function onRetryMessage(item) {
  try {
    await store.retryMessage(item._raw)
  } catch (err) {
    MessagePlugin.error(`重试失败: ${err.message || '未知错误'}`)
  }
}

/**
 * Delete an assistant message and its preceding user prompt.
 */
function onDeleteMessage(item) {
  store.deleteMessage(item._raw)
}

/**
 * Copy a message's text content to the clipboard.
 * Uses the Clipboard API with a fallback for older browsers.
 */
async function onCopyMessage(item) {
  const text = item._raw?.content || ''
  if (!text) return
  try {
    await navigator.clipboard.writeText(text)
    MessagePlugin.success('已复制到剪切板')
  } catch {
    // Fallback for older browsers / non-secure contexts
    const textarea = document.createElement('textarea')
    textarea.value = text
    textarea.style.position = 'fixed'
    textarea.style.opacity = '0'
    document.body.appendChild(textarea)
    textarea.select()
    try {
      document.execCommand('copy')
      MessagePlugin.success('已复制到剪切板')
    } catch {
      MessagePlugin.error('复制失败')
    }
    document.body.removeChild(textarea)
  }
}
</script>

<style>
/* Customize TDesign Chat via CSS variables. TDesign Chat Web Components
   expose these variables on :root inside their Shadow DOM, but CSS
   custom properties pierce the shadow boundary, so redefining them
   here affects the chat bubbles. */
:root {
  --font-family-sans: "SimHei", "Heiti SC", "Microsoft YaHei",
    "PingFang SC", "Hiragino Sans GB", "Source Han Sans SC",
    "Noto Sans CJK SC", sans-serif;
  --font-size-sm: 14px;
  --line-height-normal: 1.6;
  /* Match the global TDesign text color. Hard-coding `red` here was a
     debugging leftover that turned every chat bubble bright red. */
  --base-font-color: var(--td-text-color-primary, rgba(0, 0, 0, 0.9));

  /* TDesign Chat CSS variables - these pierce Shadow DOM.
     --td-chat-font-size controls the base font size for all chat
     bubbles (default 16px). Set to 14px so both user questions
     and AI answers share the same size. */
  --td-chat-font-size: 14px;
  --td-chat-md-font: var(--td-text-color-primary);
  --td-chat-font-family: "SimHei", "Heiti SC", "Microsoft YaHei",
    "PingFang SC", "Hiragino Sans GB", sans-serif;
}

/* TDesign Chat 0.7.0 chat-bubble font overrides. Only target the
   message display area (t-chat-list), NOT the input textarea.
   The web-components use Shadow DOM, so we rely on CSS variables
   above for most styling, plus ::part() selectors for deep
   customization. */
.t-chat__text,
.t-chat__text__assistant,
.t-chat__text--user,
.t-chat__text__content,
.t-chat__text__markdown,
.t-chat__detail,
.t-chat__header,
.t-chat__name,
.t-chat__datetime {
  font-family: "SimHei", "Heiti SC", "Microsoft YaHei",
    "PingFang SC", "Hiragino Sans GB", sans-serif !important;
  font-size: 14px !important;
  line-height: 1.6 !important;
}

/* AI markdown content - the .cherry class is inside Shadow DOM
   but inherits --td-chat-font-size from :root. We also need to
   override the font shorthand that cherry-markdown sets. */
.t-chat__text .cherry,
.t-chat__text__markdown .cherry {
  font-family: "SimHei", "Heiti SC", "Microsoft YaHei",
    "PingFang SC", "Hiragino Sans GB", sans-serif !important;
  font-size: 14px !important;
  line-height: 1.6 !important;
}

/* Reasoning panel font - keep one step smaller than the answer. */
.t-chat__think__inner,
.t-chat__reasoning__text,
.t-chat__think__header__content {
  font-family: "SimHei", "Heiti SC", "Microsoft YaHei",
    "PingFang SC", "Hiragino Sans GB", sans-serif !important;
  font-size: 13px !important;
  line-height: 1.5 !important;
}

/* ===== Typewriter cursor effect =====
   TDesign Chat 0.7.0 does not have a built-in typewriter animation.
   We simulate it with a blinking cursor appended to the streaming
   AI answer. The cursor appears only while streaming is active
   (status='' + textLoading=true on t-chat-list). */
@keyframes ai-typewriter-cursor {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

/* The cursor is appended to the last markdown block of the AI
   answer while streaming. We use a CSS ::after pseudo-element on
   the chat item container. */
.t-chat__item--assistant .t-chat__detail .t-chat__text__markdown::after {
  content: "";
  display: inline-block;
  width: 2px;
  height: 1em;
  margin-left: 2px;
  vertical-align: text-bottom;
  background-color: currentColor;
  animation: ai-typewriter-cursor 0.8s step-end infinite;
}

/* Hide the cursor when streaming is complete. We rely on the
   fact that t-chat-list sets status="pending" on the last item
   while textLoading=true. When textLoading goes false, the
   pending status is removed and the cursor disappears. */
.t-chat__item--assistant:not([data-status="pending"]) .t-chat__text__markdown::after {
  display: none;
}
</style>

<style scoped>
.message-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 4px 0;
  opacity: 0.6;
  transition: opacity 0.2s;
  /* Inherit the width of whatever container TDesign places us in;
     the deep rules below ensure that container matches the bubble. */
  width: 100%;
  box-sizing: border-box;
}

/*
 * Align the actionbar's width AND horizontal position with the
 * chat bubble above it.
 *
 * TDesign Chat 0.7.0 renders each row as:
 *
 *   .t-chat__item
 *     └── .t-chat__item__main        (flex column; width: 100%)
 *           ├── .t-chat__item__content--base   (the bubble itself,
 *           │                                   sized by content
 *           │                                   via fit-content)
 *           └── [slot="actionbar"]   (our #actions slot; default
 *                                     width: 100% of __main, NOT
 *                                     of the bubble)
 *
 * The fix is two-fold:
 *
 * 1. Make the actionbar wrapper `width: fit-content` so it shrinks
 *    to the bubble width. Because both content and actionbar are
 *    siblings inside __main, they share the same alignment context
 *    (left for assistant, right for user) - so `fit-content` makes
 *    the actionbar track the bubble width AND follow its left /
 *    right alignment.
 *
 * 2. Force `align-self: inherit` on the actionbar so it copies the
 *    bubble's cross-axis alignment (flex-start for assistant rows,
 *    flex-end for user rows). Combined with (1) this puts the
 *    actionbar directly under the bubble, exactly matching its
 *    width and position.
 */
:deep([slot="actionbar"]),
:deep(.t-chat__actions),
:deep(.t-chat__actionbar) {
  width: fit-content;
  max-width: 100%;
  box-sizing: border-box;
  display: block;
  align-self: inherit;
}

/*
 * The inner .message-actions row uses justify-content: space-between
 * so its left group (icon buttons) and right group (token chip +
 * disclaimer) pin to opposite edges of the actionbar - which after
 * the rules above is the same width as the bubble.
 */

.message-actions:hover {
  opacity: 1;
}

/* Left container: copy / retry / delete icon buttons. */
.message-actions-left {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
}

/* Right container: AI disclaimer + token-usage chip. */
.message-actions-right {
  display: inline-flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
  margin-left: auto;
}

/*
 * Per-message token chip (the "↑ 553 ↓ 553" readout under each
 * bubble). Lives inside .message-actions-right, separated from the
 * disclaimer text by the parent's 12px gap.
 */
.message-actions .message-token-usage {
  font-size: 11px;
  line-height: 1.4;
  color: var(--td-text-color-placeholder);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.ai-agent-chat {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--td-bg-color-container);
  /* Anchor the drag-over overlay so it covers the whole chat area
     without affecting layout. */
  position: relative;
}

/*
 * Drag-over overlay shown while the user drags a file over the chat
 * panel. Sits above all chat content with a subtle backdrop blur.
 */
.ai-agent-drag-overlay {
  position: absolute;
  inset: 0;
  z-index: 20;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.35);
  backdrop-filter: blur(4px);
  pointer-events: none; /* let the drop bubble to the parent */
  border: 2px dashed var(--td-brand-color);
  border-radius: 6px;
  margin: 8px;
}

.ai-agent-drag-overlay .drag-overlay-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  color: #fff;
  font-size: 14px;
  font-weight: 500;
}

/*
 * Main column wrapper: wraps messages + input so the floating
 * edge-toggle can position itself against the chat area's left edge
 * via `position: absolute` on the nearest positioned ancestor.
 */
.ai-agent-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  height: 100%;
  position: relative;
}

/*
 * Floating edge toggle for the session-history panel. Mirrors the
 * global sidebar edge toggle (see layout/index.vue): a 20x36px
 * rounded button straddling the LEFT edge of the chat area, with a
 * chevron that flips direction based on the panel's open state.
 *
 * We use absolute positioning (not a separate flex column) so the
 * button never claims layout space - the chat and input areas stay
 * full-width regardless of the panel's open state.
 */
.ai-agent-edge-toggle {
  position: absolute;
  top: 50%;
  left: 0;
  transform: translateY(-50%);
  z-index: 11;

  width: 20px;
  height: 36px;
  padding: 0;
  border: none;
  border-radius: 0 4px 4px 0;
  /* Semi-transparent by default so the button doesn't fight with the
     chat content underneath; full opacity on hover. */
  background: rgba(0, 0, 0, 0.18);
  color: rgba(255, 255, 255, 0.85);
  cursor: pointer;

  display: inline-flex;
  align-items: center;
  justify-content: center;

  box-shadow: 1px 0 4px rgba(0, 0, 0, 0.08);
  backdrop-filter: blur(4px);
  transition: background-color 0.2s, color 0.2s;
}

.ai-agent-edge-toggle:hover,
.ai-agent-edge-toggle:focus-visible {
  background: var(--td-brand-color);
  color: #fff;
  outline: none;
}

.ai-agent-edge-toggle.is-open {
  background: rgba(0, 0, 0, 0.32);
  color: #fff;
}

.ai-agent-edge-toggle.is-open:hover,
.ai-agent-edge-toggle.is-open:focus-visible {
  background: var(--td-brand-color);
  color: #fff;
}

.ai-agent-messages {
  flex: 1;
  min-height: 0;
  overflow: hidden; /* t-chat-list owns its own scroll */
  display: flex;
  flex-direction: column;
  /* Anchor the floating edge-toggle button to this container so
     `top: 50%` centers it against the messages area only (not the
     full panel including the input below). */
  position: relative;
}

.ai-agent-messages :deep(.t-chat-list) {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 16px;
}

/*
 * Move the "scroll to bottom" floating button from its default
 * bottom-center position to the bottom-right corner of the chat
 * area. TDesign Chat 0.7.0 names the button `t-chat__to-bottom`
 * (NOT `t-chat-list__to-bottom`) and positions it via CSS
 * variables; we override both the variable-driven transform and
 * the literal left/right so the button docks to the right edge.
 */
.ai-agent-messages :deep(.t-chat) {
  --td-chat-list-scroll-button-left: auto;
  --td-chat-list-scroll-button-transform: none;
}
/*
 * Hide t-chat's built-in to-bottom button - we replace it with our
 * own paired scroll controls (top + bottom) so both buttons share
 * the same small semi-transparent style.
 */
.ai-agent-messages :deep(.t-chat__to-bottom) {
  display: none !important;
}

/*
 * Custom scroll-control stack pinned to the bottom-right of the
 * messages area. Two small semi-transparent buttons (top / bottom).
 * Pointer-events only on the buttons themselves so the strip does
 * not block clicks on the chat content underneath.
 */
.ai-agent-scroll-controls {
  position: absolute;
  right: 12px;
  bottom: 16px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  z-index: 12;
  pointer-events: none;
}

.ai-agent-scroll-controls .scroll-ctrl-btn {
  pointer-events: auto;
  width: 24px;
  height: 24px;
  padding: 0;
  background: rgba(0, 0, 0, 0.18) !important;
  color: rgba(255, 255, 255, 0.85) !important;
  border: none !important;
  backdrop-filter: blur(4px);
  border-radius: 4px;
  /* 50% opacity by default so the buttons stay subtle against the
     chat content; full opacity returns on hover for discoverability. */
  opacity: 0.5;
  transition: background 0.15s, color 0.15s, opacity 0.15s;
}

.ai-agent-scroll-controls .scroll-ctrl-btn:hover {
  background: var(--td-brand-color) !important;
  color: #fff !important;
  opacity: 1;
}

/*
 * Pull the user bubble (right-aligned) slightly inward so it doesn't
 * kiss the right edge of the floating window. TDesign renders user
 * messages with a `t-chat__item--user` modifier on the bubble root;
 * nudge it left by the same 8px the assistant bubble gets from the
 * avatar gutter.
 */
.ai-agent-messages :deep(.t-chat-list .t-chat__item--user) {
  margin-right: 8px;
}

.ai-agent-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
}

.empty-icon {
  font-size: 48px;
  color: var(--td-text-color-placeholder);
}

.ai-agent-tool-call {
  padding: 8px 16px;
  text-align: center;
  border-top: 1px dashed var(--td-component-border);
}

.ai-agent-waiting {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 12px 16px;
  border-top: 1px dashed var(--td-component-border);
}

/*
 * Queued messages box. Shown while a previous stream is still in
 * flight and the user has typed additional messages. Grey, subtle,
 * one row per queued message with an individual delete button.
 */
.ai-agent-queue {
  border-top: 1px solid var(--td-component-border);
  background: var(--td-bg-color-secondarycontainer);
  padding: 6px 12px;
  font-size: 12px;
}

.ai-agent-queue-header {
  margin-bottom: 4px;
}

.ai-agent-queue-header .queue-header-label {
  color: var(--td-text-color-placeholder);
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.ai-agent-queue-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 4px 8px;
  margin-bottom: 2px;
  background: var(--td-bg-color-container);
  border: 1px solid var(--td-component-border);
  border-radius: 4px;
  color: var(--td-text-color-secondary);
}

.ai-agent-queue-item .queue-item-text {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ai-agent-queue-item .queue-item-delete {
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  color: var(--td-text-color-placeholder);
  cursor: pointer;
  transition: color 0.15s;
}

.ai-agent-queue-item .queue-item-delete:hover {
  color: var(--td-error-color);
}

.rag-disabled-tip {
  font-size: 12px;
  color: var(--td-text-color-placeholder);
  margin-left: 4px;
}

.ai-agent-attachments {
  display: flex;
  gap: 8px;
  padding: 8px 16px;
  border-top: 1px solid var(--td-component-border);
  flex-wrap: wrap;
}

.attachment-preview {
  position: relative;
  width: 80px;
  height: 80px;
}

.attachment-image {
  width: 100%;
  height: 100%;
  border-radius: 4px;
  object-fit: cover;
}

.attachment-remove {
  position: absolute;
  top: -6px;
  right: -6px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  background: var(--td-error-color);
  color: #fff;
  border-radius: 50%;
  cursor: pointer;
  transition: transform 0.15s ease;
  /* Sit above the image preview. TDesign's t-image wrapper has
     z-index: 1 by default; we need a higher value so the remove
     button isn't covered when the image renders. */
  z-index: 2;
}

.attachment-remove:hover {
  transform: scale(1.15);
}

.ai-agent-input-area {
  border-top: 1px solid var(--td-component-border);
  padding: 12px;
}

/*
 * Force the message textarea to a usable minimum height. TDesign's
 * default rows=8 should be enough for ~6 lines, but the line-height
 * inside the chat bubble styles can end up smaller than expected, so
 * we pin a floor of 140px (~5 lines of 14px text at 1.6 line-height
 * plus padding). The textarea is still resizable by the user via
 * TDesign's built-in drag handle.
 */
/*
 * Cap the textarea's minimum height to ~3 lines of 14px text at 1.6
 * line-height plus padding (~22*3 + 16 = 82px). TDesign's autosize
 * `minRows: 3` already does this via inline styles, but the CSS floor
 * guarantees the box never collapses smaller if the autosize engine
 * miscalculates the row height on first paint.
 */
.ai-agent-textarea :deep(.t-textarea__inner) {
  min-height: 84px !important;
  font-size: 14px;
  line-height: 1.6;
}

/*
 * Context-usage donut: small SVG ring + "92.4k / 1.0m" text label,
 * sitting to the LEFT of the stop / send buttons. Replaces the old
 * "↑ X ↓ Y / Z" chip with a visual that makes it obvious how much
 * of the model's context window is already consumed.
 */
.token-usage-donut {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 2px 4px;
  cursor: default;
  user-select: none;
  color: var(--td-text-color-secondary);
}

.token-usage-donut .donut-svg {
  width: 24px;
  height: 24px;
  flex-shrink: 0;
}

.token-usage-donut .donut-track {
  stroke: var(--td-component-border);
}

.token-usage-donut .donut-fill {
  stroke: var(--td-brand-color);
  transition: stroke-dasharray 0.4s ease;
}

.token-usage-donut .donut-text {
  font-size: 9px;
  font-weight: 600;
  fill: var(--td-text-color-primary);
  font-family: inherit;
}

.token-usage-donut .donut-numbers {
  font-size: 11px;
  line-height: 1;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
  letter-spacing: 0.2px;
}

.token-usage-donut .donut-divider {
  margin: 0 4px;
  color: var(--td-text-color-placeholder);
}

.token-usage-tooltip {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 12px;
  line-height: 1.5;
}

.ai-agent-input-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px dashed var(--td-component-border);
  /* Three-container layout: left buttons / center donut / right
     stop+send. The center container claims any free space so the
     two flanking groups keep their natural size. */
  gap: 8px;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
}

/*
 * Middle container: hosts the context-window donut + token stats.
 * Flex-grows to absorb the free space between the left button
 * group and the right stop/send buttons; content is right-aligned
 * so the donut hugs the stop/send buttons on the right edge of
 * the toolbar (per UX feedback).
 */
.toolbar-center {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  justify-content: flex-end;
}

.toolbar-right {
  display: flex;
  align-items: center;
  flex-shrink: 0;
}

/* Icon buttons in the toolbar */
.toolbar-left :deep(.t-button),
.toolbar-right :deep(.t-button) {
  color: var(--td-text-color-secondary);
  transition: color 0.2s, background 0.2s;
}

.toolbar-left :deep(.t-button:hover),
.toolbar-right :deep(.t-button:hover) {
  color: var(--td-brand-color);
  background: var(--td-bg-color-container-hover);
}

/* Active state for the RAG toggle */
.toolbar-left :deep(.t-button.is-active) {
  color: var(--td-brand-color);
  background: var(--td-brand-color-light);
}

/* Disabled state */
.toolbar-left :deep(.t-button.is-disabled) {
  color: var(--td-text-color-disabled);
  cursor: not-allowed;
}

/*
 * Per-message AI disclaimer: tiny grey text rendered inside the
 * right-aligned actions container. Deliberately low-contrast and
 * non-interactive.
 */
.message-disclaimer {
  font-size: 11px;
  line-height: 1.4;
  color: var(--td-text-color-placeholder);
  user-select: none;
  pointer-events: none;
  white-space: nowrap;
}
</style>
