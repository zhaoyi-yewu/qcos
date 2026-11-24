/**
 * Copyright© 2024-2026 China Mobile (SuZhou) Software Technology Co.,Ltd.
 *
 * qcos is licensed under Mulan PSL v2.
 * You can use this software according to the terms and conditions
 * of the Mulan PSL v2.
 * You may obtain a copy of Mulan PSL v2 at:
 *         http://license.coscl.org.cn/MulanPSL2
 * THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS,
 *     WITHOUT WARRANTIES OF ANY KIND,
 * EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
 * MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
 * See the Mulan PSL v2 for more details.
 */

import { defineStore } from 'pinia'
import { streamChatAgui, listModels, listSessions, getSession, deleteSession, createSession, clearSessionMessages, truncateSessionMessages } from '@/api/aiAgent'
import { useComponentsStore } from '@/store/modules/components'

const STORAGE_KEY = 'qcos-ai-agent'

/**
 * Normalise diagram code-fence language tags so the chat markdown
 * renderer recognises them. Cherry-markdown's PlantUML plugin only
 * registers a renderer for the `plantuml` language, while models
 * frequently emit ```puml instead. Rewrite the fence info string on
 * the full accumulated text (safe during streaming: every render
 * passes the whole string, so a partial fence simply stays a plain
 * code block until its info line completes).
 */
function normalizeDiagramLang(text) {
  if (!text) return text
  return text.replace(/^([ \t]*)```puml([ \t]*)$/gim, '$1```plantuml')
}

function loadPersisted() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return {}
    return JSON.parse(raw)
  } catch {
    return {}
  }
}

function persist(state) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({
      displayMode: state.displayMode,
      drawerWidth: state.drawerWidth,
      floatingPosition: state.floatingPosition,
      floatingSize: state.floatingSize,
      enableRag: state.enableRag,
      // Persist the active session id so a page reload re-opens the
      // same conversation instead of starting a brand-new one.
      activeSessionId: state.activeSessionId
    }))
  } catch {
    // ignore
  }
}

export const useAiAgentStore = defineStore('aiAgent', {
  state: () => {
    const persisted = loadPersisted()
    return {
      // ===== Display mode =====
      visible: false,
      displayMode: persisted.displayMode || 'drawer', // 'drawer' | 'floating'
      minimized: false,
      // The displayMode the panel was in BEFORE the user minimized.
      // Restored on restore-from-minimized so the panel returns to its
      // previous form (drawer vs floating) instead of always opening
      // as floating. Null when not minimized.
      _displayModeBeforeMinimize: null,
      // True while the floating window is stretched to fill the viewport.
      // Not persisted - always start in normal mode after reload.
      floatingFullscreen: false,
      floatingPosition: persisted.floatingPosition || null, // {x, y}
      floatingSize: persisted.floatingSize || { width: 520, height: 640 },
      drawerWidth: persisted.drawerWidth || 480,

      // ===== Session & messages =====
      // Restored from localStorage so a page reload continues the
      // previous conversation instead of starting a new one. The
      // message list itself is loaded lazily via loadSession() when
      // the panel first opens.
      activeSessionId: persisted.activeSessionId || null,
      sessions: [],
      messages: [],
      // TDesign Chat view items, maintained imperatively alongside
      // `messages`. Each entry has stable object identity across the
      // message's lifetime (and stable content block references) so
      // <t-chat-list> can detect in-place deltas and run the
      // typewriter animation. Do NOT derive this via a computed -
      // computed recreation breaks the chat's internal animation
      // state machine.
      chatItems: [],
      streaming: false,
      waitingForResponse: false,
      // True while an edited question is being truncated on the backend.
      // Blocks concurrent sends until the retained prefix is restored.
      historyMutating: false,
      enableRag: persisted.enableRag !== undefined ? persisted.enableRag : true,
      pendingToolCall: null,
      pendingAttachments: [],
      // Cumulative token counters across the current session. Each
      // ``RUN_FINISHED`` event from the backend carries an optional
      // ``usage`` payload; we accumulate it here so the status bar
      // can display total input/output tokens and a context-window
      // capacity hint. Reset when switching sessions.
      tokenUsage: {
        inputTokens: 0,
        outputTokens: 0,
        contextWindow: 0,
      },
      // Pending user messages queued while streaming. When the user
      // hits send mid-stream, the new message is appended here instead
      // of being dropped or interrupting the in-flight request; the
      // queue is flushed FIFO once the current stream finishes
      // (zoo-code style sequential queue).
      messageQueue: [],

      // ===== Model selection =====
      // Non-sensitive model list from GET /v1/ai/models. Empty on
      // older servers (modelsUnavailable=true) where the menu is
      // disabled and chat simply uses the server-side default.
      availableModels: [],
      defaultModelId: null,
      // Explicitly selected model id; null means "follow the session
      // / server default" and no model_id is sent with requests.
      selectedModelId: null,
      modelsLoaded: false,
      modelsUnavailable: false,
      // In-flight fetch promise so the panel open and session restore
      // paths share one request instead of racing each other.
      _modelsFetchPromise: null,

      // ===== Input draft =====
      draft: '',

      // ===== AbortController for cancelling streaming =====
      currentAbortController: null,

      // Injected by AiAgentChat.vue on setup so _buildChatItem can
      // resolve name/avatar/datetime without a circular dependency.
      _chatItemMetaResolver: null
    }
  },

  getters: {
    /**
     * Effective model for the NEXT message: the explicit selection
     * when present, otherwise the server default. Null when the model
     * list is unavailable (legacy server) or not loaded yet.
     */
    currentModel(state) {
      const id = state.selectedModelId || state.defaultModelId
      if (!id) return null
      return state.availableModels.find(m => m.id === id) || null
    },
    /**
     * Whether the CURRENT model accepts image attachments. Falls back
     * to true when no model info is available so the legacy
     * components.vision flag stays authoritative on old servers.
     */
    currentModelSupportsVision(state) {
      const id = state.selectedModelId || state.defaultModelId
      if (!id) return null
      const model = state.availableModels.find(m => m.id === id)
      return model ? model.supports_vision : null
    }
  },

  actions: {
    open(mode) {
      if (mode) {
        this.displayMode = mode
      }
      this.visible = true
      this.minimized = false
      // Load the model list when the panel opens; safe to call
      // repeatedly (in-flight requests are shared).
      this.fetchModels()
      // Restore the previous conversation when the panel re-opens and
      // we still have a session id from a prior visit (persisted in
      // localStorage). Validate the id against the current user's
      // session list first so an expired id never triggers a 404 GET.
      if (
        this.activeSessionId
        && this.messages.length === 0
      ) {
        this._restoreActiveSession(this.activeSessionId)
      }
    },

    close() {
      this.visible = false
      this.minimized = false
    },

    toggleMinimize() {
      if (this.displayMode === 'floating') {
        this.minimized = !this.minimized
        if (this.minimized) {
          this._displayModeBeforeMinimize = 'floating'
        } else {
          this._displayModeBeforeMinimize = null
        }
      }
    },

    /**
     * Minimize from drawer mode: remember the previous displayMode so
     * a later restore can put the panel back into drawer form (instead
     * of always opening as floating). Switches to floating internally
     * because only the floating mode has a "minimized pill" UI.
     */
    minimizeFromDrawer() {
      this._displayModeBeforeMinimize = 'drawer'
      this.displayMode = 'floating'
      this.minimized = true
    },

    /**
     * Restore from the minimized pill. Returns the panel to whichever
     * displayMode it was in before being minimized (drawer or
     * floating).
     */
    restoreFromMinimize() {
      if (!this.minimized) return
      this.minimized = false
      if (this._displayModeBeforeMinimize === 'drawer') {
        this.displayMode = 'drawer'
      }
      this._displayModeBeforeMinimize = null
    },

    toggleFloatingFullscreen() {
      if (this.displayMode === 'floating' && !this.minimized) {
        this.floatingFullscreen = !this.floatingFullscreen
      }
    },

    setDisplayMode(mode) {
      if (this.displayMode === mode) return
      this.displayMode = mode
      persist(this)
    },

    setFloatingGeometry({ position, size }) {
      if (position) this.floatingPosition = position
      if (size) this.floatingSize = size
      persist(this)
    },

    setDrawerWidth(w) {
      this.drawerWidth = w
      persist(this)
    },

    setEnableRag(v) {
      // When embedding service is disabled, force RAG off
      const componentsStore = useComponentsStore()
      if (!componentsStore.embeddingEnabled && v) {
        this.enableRag = false
      } else {
        this.enableRag = v
      }
      persist(this)
    },

    /**
     * Fetch the configured model list. Older servers answer 404: the
     * menu is then disabled ("默认模型") and chat requests omit the
     * model_id field entirely, so default conversations keep working.
     */
    async fetchModels() {
      if (this.modelsLoaded || this.modelsUnavailable) return
      if (this._modelsFetchPromise) return this._modelsFetchPromise
      this._modelsFetchPromise = (async() => {
        try {
          const res = await listModels()
          this.availableModels = res?.models || []
          this.defaultModelId = res?.default_model_id || null
          this.modelsLoaded = true
          this.modelsUnavailable = false
          // A previously selected model may have been removed from the
          // server configuration; fall back to the default entry.
          if (
            this.selectedModelId &&
            !this.availableModels.some(m => m.id === this.selectedModelId)
          ) {
            this.selectedModelId = this.defaultModelId
          }
        } catch (e) {
          console.warn('AI model list unavailable; using server default:', e)
          this.availableModels = []
          this.defaultModelId = null
          this.selectedModelId = null
          this.modelsLoaded = false
          this.modelsUnavailable = true
        } finally {
          this._modelsFetchPromise = null
        }
      })()
      return this._modelsFetchPromise
    },

    /**
     * Select a model for subsequent messages. Unknown ids are rejected
     * against the fetched whitelist; the change never affects
     * in-flight or already-queued messages (they keep their snapshot).
     */
    setSelectedModel(modelId) {
      if (!this.modelsLoaded) return
      const target = modelId || this.defaultModelId
      if (!target) return
      if (!this.availableModels.some(m => m.id === target)) return
      this.selectedModelId = target
    },

    async _restoreActiveSession(sessionId) {
      const fetched = await this.fetchSessions()
      // The user may have selected another session or started a new
      // message while the list request was in flight. Do not overwrite
      // that newer state with this stale restoration request.
      if (
        !fetched ||
        this.activeSessionId !== sessionId ||
        this.messages.length > 0
      ) {
        return
      }
      const exists = this.sessions.some(s => s.session_id === sessionId)
      if (!exists) {
        this.activeSessionId = null
        persist(this)
        return
      }
      await this.loadSession(sessionId)
    },

    async fetchSessions() {
      try {
        const res = await listSessions()
        this.sessions = res || []
        return true
      } catch (e) {
        console.error('Failed to fetch AI sessions:', e)
        this.sessions = []
        return false
      }
    },

    async loadSession(sessionId) {
      try {
        const res = await getSession(sessionId)
        this.activeSessionId = sessionId
        persist(this)
        // Reset cumulative token counters - they are per-session.
        this.tokenUsage = { inputTokens: 0, outputTokens: 0, contextWindow: 0 }
        this.messages = (res.messages || []).map(m => ({
          role: m.role,
          content: m.content,
          createdAt: m.created_at,
          attachments: m.attachments || [],
          modelId: m.model_id || null,
          model: m.model || null
        }))
        this._rebuildChatItems()
        // Restore the session's saved model. Wait for the model list
        // first so a session restore and the list fetch cannot race
        // each other into an inconsistent selection.
        await this.fetchModels()
        const savedModelId = res.session?.model_id || null
        if (this.modelsLoaded) {
          if (savedModelId && this.availableModels.some(m => m.id === savedModelId)) {
            this.selectedModelId = savedModelId
          } else {
            // Deleted / unknown model: fall back to the default entry.
            // The backend repairs its session metadata on next append;
            // we repair the local value here.
            this.selectedModelId = this.defaultModelId
          }
        }
      } catch (e) {
        const isMissingSession = e?.response?.status === 404
        if (!isMissingSession) {
          console.error('Failed to load session:', e)
        }
        this.messages = []
        this.chatItems = []
        if (isMissingSession) {
          // The session expired, was deleted, or belongs to another
          // user. Forget it so reopening the panel does not request the
          // same missing id again; the next send starts a fresh session.
          this.activeSessionId = null
          this.sessions = this.sessions.filter(
            s => s.session_id !== sessionId
          )
          this.tokenUsage = { inputTokens: 0, outputTokens: 0, contextWindow: 0 }
          persist(this)
        }
      }
    },

    async createNewSession(title = '新的会话') {
      try {
        const res = await createSession(title)
        this.activeSessionId = res.session_id
        persist(this)
        // Reset cumulative token counters - new conversation starts
        // from zero.
        this.tokenUsage = { inputTokens: 0, outputTokens: 0, contextWindow: 0 }
        this.messages = []
        this.chatItems = []
        // New sessions start on the configured default model.
        this.selectedModelId = this.defaultModelId
        return res.session_id
      } catch (e) {
        console.error('Failed to create session:', e)
        return null
      }
    },

    async removeSession(sessionId) {
      try {
        await deleteSession(sessionId)
        if (this.activeSessionId === sessionId) {
          this.activeSessionId = null
          persist(this)
          this.messages = []
          this.chatItems = []
        }
        await this.fetchSessions()
      } catch (e) {
        console.error('Failed to delete session:', e)
      }
    },

    /**
     * Build a TDesign Chat item from a raw message. Called once per
     * message - the returned object is stored in `chatItems` and
     * mutated in place on subsequent chunks. Avatar/name callbacks
     * are injected by the view layer via `setChatItemMetaResolver`.
     */
    _buildChatItem(m) {
      const isAssistant = m.role === 'assistant'
      // While the assistant is still waiting for the first SSE chunk
      // (thinking=true, content=''), render a placeholder so the
      // bubble isn't blank. Once the first chunk arrives, onChunk
      // mutates the content blocks in place.
      const text = m.content || (isAssistant && m.thinking ? '正在思考...' : '')
      // TDesign Chat 0.7.0 (web-components-chat) expects content to
      // be an ARRAY of ChatContentData objects. Each element has
      // {type, data, status?}. The type determines which renderer
      // is used:
      //   - 'markdown' / 'text' -> t-chat-md-content (markdown renderer)
      //   - 'reasoning' -> collapsible thinking panel
      //   - 'image' -> img tag
      const blocks = []
      // Chain-of-thought (reasoning) block. The data field must be
      // an ARRAY of {type: 'text', data: string} items, one per
      // paragraph. The renderReasoning function maps over them.
      if (isAssistant && m.thinkingContent) {
        blocks.push({
          type: 'reasoning',
          data: [{ type: 'text', data: m.thinkingContent }],
          status: m.thinking ? 'streaming' : 'complete',
          // Default-collapsed: TDesign web-components-chat spreads
          // `content.ext` into renderReasoning's props, and the
          // reasoning component reads `collapsed: Boolean` to set its
          // initial collapse state. Keep the panel closed by default
          // so long chain-of-thought sections don't push the actual
          // answer off-screen; users can click to expand.
          ext: { collapsed: true }
        })
      }
      // Main answer content block.
      blocks.push({
        type: isAssistant ? 'markdown' : 'text',
        data: isAssistant ? normalizeDiagramLang(text) : text
      })
      // Image attachments (base64 data URLs).
      if (Array.isArray(m.attachments) && m.attachments.length > 0) {
        for (const att of m.attachments) {
          blocks.push({
            type: 'image',
            data: {
              name: att.name || 'image',
              url: `data:${att.media_type};base64,${att.data}`
            }
          })
        }
      }
      const meta = this._chatItemMetaResolver
        ? this._chatItemMetaResolver(m)
        : { name: '', avatar: '', datetime: '' }
      return {
        role: isAssistant ? 'assistant' : 'user',
        content: blocks,
        name: meta.name,
        avatar: meta.avatar,
        datetime: meta.datetime,
        // Error answers are rendered as NORMAL markdown content (the
        // backend already prefixes them with a human-readable failure
        // message). Do NOT map them to the TDesign 'error' status:
        // that status is meant for an empty-error placeholder and can
        // hide the actual failure text from the bubble, which is
        // exactly what users reported (log shows the error, the chat
        // bubble shows nothing).
        status: m.aborted ? 'stop' : '',
        _raw: m
      }
    },

    /**
     * Rebuild the chatItems array from scratch. Used on session load.
     * During streaming we never rebuild - only mutate items in place.
     */
    _rebuildChatItems() {
      this.chatItems = this.messages.map(m => this._buildChatItem(m))
    },

    addMessage(msg) {
      this.messages.push(msg)
      this.chatItems.push(this._buildChatItem(msg))
    },

    /**
     * Clear all messages in the current session.
     *
     * Calls the backend ``DELETE /v1/ai/sessions/{id}/messages`` so
     * the wipe survives page reloads (the session record is kept,
     * only the message list is cleared). Falls back to local-only
     * clearing when no active session exists yet.
     */
    async clearMessages() {
      const sessionId = this.activeSessionId
      this.messages = []
      this.chatItems = []
      if (sessionId) {
        try {
          await clearSessionMessages(sessionId)
        } catch (e) {
          console.error('Failed to clear session messages:', e)
        }
      }
    },

    updateLastAssistantMessage(delta) {
      const last = this.messages[this.messages.length - 1]
      if (last && last.role === 'assistant') {
        last.content += delta
      }
    },

    addPendingAttachment(att) {
      this.pendingAttachments.push(att)
    },

    removePendingAttachment(index) {
      this.pendingAttachments.splice(index, 1)
    },

    clearPendingAttachments() {
      this.pendingAttachments = []
    },

    /**
     * Delete a single assistant message (and its preceding user
     * message if it directly answers one). Used by the per-message
     * delete button in the chat action bar.
     */
    deleteMessage(raw) {
      if (this.streaming || this.historyMutating) return
      const idx = this.messages.indexOf(raw)
      if (idx < 0) return
      // If the message is an assistant reply, drop the preceding
      // user message as well so the chat history stays paired.
      const isAssistant = raw.role === 'assistant'
      const startIdx = isAssistant && idx > 0 ? idx - 1 : idx
      this.messages.splice(startIdx, isAssistant && idx > 0 ? 2 : 1)
      this._rebuildChatItems()
    },

    /**
     * Edit a user question and regenerate from that point. The backend
     * truncates the old branch first so Redis and the browser retain the
     * same history after a reload.
     */
    async editAndRetryMessage(rawUserMessage, newText) {
      const idx = this.messages.indexOf(rawUserMessage)
      if (idx < 0 || rawUserMessage.role !== 'user') {
        throw new Error('找不到要修改的问题')
      }
      if (!newText.trim() && !(rawUserMessage.attachments || []).length) {
        throw new Error('修改后的问题不能为空')
      }
      if (this.streaming || this.historyMutating || this.messageQueue.length) {
        throw new Error('请等待当前回答完成后再修改问题')
      }
      const sessionId = this.activeSessionId
      if (!sessionId) {
        throw new Error('当前会话尚未保存，请刷新后重试')
      }

      this.historyMutating = true
      try {
        const res = await truncateSessionMessages(
          sessionId,
          idx,
          rawUserMessage.content
        )
        if (this.activeSessionId !== sessionId) {
          throw new Error('会话已切换，请重新选择后再修改')
        }
        this.messages = (res.messages || []).map(m => ({
          role: m.role,
          content: m.content,
          createdAt: m.created_at,
          attachments: m.attachments || [],
          modelId: m.model_id || null,
          model: m.model || null
        }))
        this._rebuildChatItems()
        this.tokenUsage = { inputTokens: 0, outputTokens: 0, contextWindow: 0 }

        // sendMessage consumes pendingAttachments synchronously. Swap in
        // the original question's attachments, start the stream, then
        // immediately restore any attachments the user was drafting.
        const previousPending = this.pendingAttachments
        this.pendingAttachments = [...(rawUserMessage.attachments || [])]
        this.historyMutating = false
        let sendPromise
        try {
          sendPromise = this.sendMessage(newText)
        } finally {
          this.pendingAttachments = previousPending
        }
        sendPromise.catch(err => {
          // Stream errors are rendered by the assistant bubble, just as
          // they are for a normal send. Do not reopen the edit dialog.
          console.error('Edited question retry failed:', err)
        })
      } finally {
        this.historyMutating = false
      }
    },

    /**
     * Retry an assistant message using the same branch-truncation path
     * as question editing, including the original image attachments.
     */
    async retryMessage(raw) {
      const idx = this.messages.indexOf(raw)
      if (idx < 0 || raw.role !== 'assistant') return
      const userMsg = this.messages[idx - 1]
      if (!userMsg || userMsg.role !== 'user') return
      await this.editAndRetryMessage(userMsg, userMsg.content)
    },

    /**
     * Flush the queued messages (if any) one at a time. Called after
     * a stream finishes (onDone) or fails (onError). Only one flush
     * runs at a time - re-entry is suppressed by the streaming flag
     * that sendMessage sets before actually starting a request.
     */
    _flushMessageQueue() {
      if (this.streaming) return
      if (this.messageQueue.length === 0) return
      const next = this.messageQueue.shift()
      // Re-attach any queued attachments to pendingAttachments so
      // sendMessage picks them up via its normal flow.
      if (Array.isArray(next.attachments)) {
        this.pendingAttachments = next.attachments
      }
      // Fire-and-forget: errors are surfaced via the message stream
      // (the in-flight assistant bubble shows the failure). The
      // queued model snapshot is passed explicitly so a later model
      // switch cannot rewrite already-queued messages.
      this.sendMessage(next.text, { modelId: next.modelId }).catch(err => {
        console.error('Failed to flush queued message:', err)
      })
    },

    /**
     * Remove a single queued message by id. Lets the user cancel a
     * still-pending send without interrupting the in-flight one.
     */
    removeQueuedMessage(id) {
      const idx = this.messageQueue.findIndex(m => m.id === id)
      if (idx >= 0) this.messageQueue.splice(idx, 1)
    },

    async sendMessage(text, options = {}) {
      if (this.historyMutating) {
        throw new Error('正在更新对话历史，请稍候')
      }
      if (!text && this.pendingAttachments.length === 0) return

      // Snapshot the model for THIS message at entry. The snapshot is
      // stored on queued items and passed back on dequeue, so switching
      // models after enqueueing never rewrites pending messages.
      //
      // Fall back to the DEFAULT model when nothing is explicitly
      // selected: the selector button shows the default model in that
      // case, so the request must name that same model. Sending no
      // model_id here would let the backend silently restore the
      // SESSION's saved model (e.g. kimi) while the button displays
      // the default (e.g. GLM) - the exact "selector shows GLM but the
      // answer still comes from kimi" mismatch.
      const requestModelId = options.modelId !== undefined
        ? options.modelId
        : (this.selectedModelId || this.defaultModelId)

      // Block image attachments for vision-less models. The pending
      // attachments are intentionally NOT dropped: the user can switch
      // to a vision-capable model and send again.
      if (this.pendingAttachments.length > 0 && this.modelsLoaded) {
        const model = this.currentModel
        if (model && !model.supports_vision) {
          throw new Error(
            `当前模型「${model.display_name}」不支持图片分析，` +
            '请切换到支持视觉的模型或先移除图片'
          )
        }
      }

      // Sequential send queue: while a previous stream is still in
      // flight, append the message to the queue instead of starting
      // a parallel request. The queue is flushed in onDone / onError
      // once the current stream finishes.
      if (this.streaming) {
        // Push the message onto the sequential send queue. Each item
        // gets a stable id so the UI can render it (and the user can
        // delete individual queued items before they fire).
        this.messageQueue.push({
          id: `q-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
          text,
          attachments: [...this.pendingAttachments],
          modelId: requestModelId
        })
        this.clearPendingAttachments()
        return
      }

      // When embedding service is disabled, force RAG off
      const componentsStore = useComponentsStore()
      const effectiveEnableRag = componentsStore.embeddingEnabled ? this.enableRag : false

      const userMsg = {
        role: 'user',
        content: text,
        createdAt: Date.now() / 1000,
        attachments: [...this.pendingAttachments]
      }
      this.addMessage(userMsg)

      const assistantMsg = {
        role: 'assistant',
        content: '',
        thinkingContent: '',
        createdAt: Date.now() / 1000,
        streaming: true,
        thinking: true, // Mark as waiting for first chunk
        // Wall-clock start time so the action bar can show "X.Xs"
        // after the run finishes.
        startedAt: Date.now()
      }
      this.addMessage(assistantMsg)
      this.streaming = true
      this.waitingForResponse = true

      const attachments = this.pendingAttachments.map(a => ({
        kind: 'image',
        media_type: a.media_type,
        data: a.data
      }))
      this.clearPendingAttachments()

      // Create AbortController for cancellation support
      const abortController = new AbortController()
      this.currentAbortController = abortController

      return new Promise((resolve, reject) => {
        // Typewriter queue: accumulate incoming deltas and flush
        // them one character at a time so the UI shows a true
        // typewriter effect instead of instant block updates.
        this._typewriterQueue = []
        this._typewriterTimer = null
        this._typewriterDone = false

        const flushTypewriter = () => {
          const last = this.messages[this.messages.length - 1]
          const lastItem = this.chatItems[this.chatItems.length - 1]
          if (!last || !lastItem || last.role !== 'assistant') return

          if (this._typewriterQueue.length === 0) {
            // Queue empty: if stream is done, stop the timer.
            if (this._typewriterDone) {
              clearInterval(this._typewriterTimer)
              this._typewriterTimer = null
            }
            return
          }

          // Take the next character(s) from the queue.
          const next = this._typewriterQueue.shift()
          if (last.thinking) {
            last.thinking = false
            last.content = next
          } else {
            last.content += next
          }

          // Update the markdown block.
          const answerBlock = lastItem.content.find(
            b => b.type === 'markdown'
          )
          if (answerBlock) answerBlock.data = normalizeDiagramLang(last.content)

          // NOTE: do NOT mark the reasoning block as 'complete' here.
          // The reasoning stream (thinking deltas) can outlive the
          // first answer chunk - some backends interleave CoT and
          // final answer sections. Marking it complete here would
          // flip the collapse panel's "已完成" label too early,
          // while additional thinking text is still being appended.
          // The status transition happens in onDone instead.

          lastItem.status = ''
          this.chatItems = [...this.chatItems]
        }

        const startTypewriter = () => {
          if (this._typewriterTimer) return
          this._typewriterTimer = setInterval(flushTypewriter, 30)
        }

        const stopTypewriter = () => {
          this._typewriterDone = true
          // Flush any remaining queue immediately so the final
          // content is complete.
          while (this._typewriterQueue.length > 0) {
            flushTypewriter()
          }
          if (this._typewriterTimer) {
            clearInterval(this._typewriterTimer)
            this._typewriterTimer = null
          }
        }

        // Use AG-UI protocol for chat streaming
        streamChatAgui({
          sessionId: this.activeSessionId,
          message: text,
          enableRag: effectiveEnableRag,
          attachments,
          modelId: requestModelId,
          signal: abortController.signal,
          onChunk: (delta) => {
            this.waitingForResponse = false
            // Push each character of the delta into the typewriter
            // queue. The timer will flush them one by one.
            for (const ch of delta) {
              this._typewriterQueue.push(ch)
            }
            startTypewriter()
          },
          onThinking: (delta) => {
            // Chain-of-thought delta: append to the message's
            // thinkingContent and lazily insert a `reasoning` block
            // at the front of the chat item if it doesn't exist yet.
            this.waitingForResponse = false
            const last = this.messages[this.messages.length - 1]
            const lastItem = this.chatItems[this.chatItems.length - 1]
            if (!last || last.role !== 'assistant' || !lastItem) return
            last.thinkingContent = (last.thinkingContent || '') + delta
            // Find the reasoning block and update its data array.
            // The reasoning block's data must be an array of
            // {type: 'text', data: string} items.
            let reasoningBlock = lastItem.content.find(
              b => b.type === 'reasoning'
            )
            if (!reasoningBlock) {
              // Lazily prepend the reasoning block at the front.
              reasoningBlock = {
                type: 'reasoning',
                data: [],
                status: 'streaming',
                // See _buildChatItem for why we default-collapsed the
                // reasoning panel.
                ext: { collapsed: true }
              }
              lastItem.content.unshift(reasoningBlock)
            }
            // Update the reasoning text. We keep a single text
            // item and mutate its data field for simplicity.
            if (reasoningBlock.data.length === 0) {
              reasoningBlock.data.push({ type: 'text', data: '' })
            }
            reasoningBlock.data[0].data = last.thinkingContent
            // TDesign Chat 0.7.0: use '' so t-chat-list's
            // textLoading controls the pending animation.
            lastItem.status = ''
            // Force Vue re-render for reasoning updates too.
            this.chatItems = [...this.chatItems]
          },
          onToolCall: (tool, args) => {
            this.pendingToolCall = { tool, args }
          },
          onToolResult: () => {
            this.pendingToolCall = null
          },
          onDone: (messageId, usage, responseSessionId) => {
            stopTypewriter()
            // Wall-clock elapsed time from message creation to
            // RUN_FINISHED; attached to the last assistant message so
            // the action bar can display it (e.g. "8.2s").
            const lastForDuration = this.messages[this.messages.length - 1]
            if (
              lastForDuration
              && lastForDuration.role === 'assistant'
              && lastForDuration.startedAt
            ) {
              lastForDuration.durationMs =
                Date.now() - lastForDuration.startedAt
              delete lastForDuration.startedAt
            }
            // Accumulate token usage reported by the backend (when
            // present). Counters reset on session switch.
            if (usage) {
              this.tokenUsage.inputTokens += usage.input_tokens || 0
              this.tokenUsage.outputTokens += usage.output_tokens || 0
              if (usage.context_window) {
                this.tokenUsage.contextWindow = usage.context_window
              }
              // Attach per-message usage so the action bar under the
              // assistant bubble can show "Tokens: N ↑M".
              const last = this.messages[this.messages.length - 1]
              if (last && last.role === 'assistant') {
                last.usage = usage
              }
            }
            // Guard against double-invocation: the SSE client may call
            // onDone once for the RUN_FINISHED event and once more from
            // the reader's stream-end fallback. Only the first call
            // performs the cleanup; subsequent calls are no-ops.
            if (!this.streaming && !this.waitingForResponse) {
              return
            }
            const last = this.messages[this.messages.length - 1]
            const lastItem = this.chatItems[this.chatItems.length - 1]
            if (last && last.role === 'assistant') {
              last.streaming = false
              last.thinking = false
              last.error = false
              last.aborted = false
              // If thinking never produced any content (e.g. the LLM
              // went straight to the answer), clear the placeholder
              // so the bubble does not keep showing "正在思考...".
              if (!last.content && lastItem) {
                last.content = ''
              }
              if (lastItem) {
                // TDesign Chat 0.7.0: use '' so t-chat-list's
                // textLoading controls the pending animation.
                lastItem.status = ''
                const answerBlock = lastItem.content.find(
                  b => b.type === 'markdown'
                )
                if (answerBlock) answerBlock.data = normalizeDiagramLang(last.content)
                // Mark reasoning as complete if present.
                const reasoningBlock = lastItem.content.find(
                  b => b.type === 'reasoning'
                )
                if (reasoningBlock) reasoningBlock.status = 'complete'
              }
            }
            this.streaming = false
            this.waitingForResponse = false
            this.currentAbortController = null
            // Prefer the real sessionId reported by RUN_STARTED /
            // RUN_FINISHED. Only legacy servers (which omit it) use
            // the old messageId-as-sessionId compatibility fallback.
            if (responseSessionId) {
              if (this.activeSessionId !== responseSessionId) {
                this.activeSessionId = responseSessionId
                persist(this)
              }
            } else if (!this.activeSessionId && messageId) {
              this.activeSessionId = messageId
              persist(this)
            }
            // Force Vue re-render on completion (same reason as above).
            this.chatItems = [...this.chatItems]
            resolve()
            // Flush the sequential send queue. We await the recursive
            // sendMessage call in a microtask so this run's promise
            // resolves first; the next queued message starts only
            // after the UI has settled.
            this._flushMessageQueue()
          },
          onError: (err) => {
            // AbortController raises AbortError after cancelStreaming has
            // already rendered the stopped message; keep that state intact.
            if (err?.name === 'AbortError') {
              resolve()
              return
            }
            console.error('AI chat stream error:', err)
            stopTypewriter()
            const last = this.messages[this.messages.length - 1]
            const lastItem = this.chatItems[this.chatItems.length - 1]
            if (last && last.role === 'assistant') {
              const errorDetail = err.message || '未知错误'
              const failureMessage = `抱歉，AI 智能体思考失败：${errorDetail}`
              last.streaming = false
              last.thinking = false
              last.error = true
              // The backend sends the failure as normal answer content
              // before RUN_ERROR. Append it here only when the stream did
              // not already provide it (for example, a network failure).
              if (!last.content.endsWith(failureMessage)) {
                last.content = last.content
                  ? `${last.content}\n\n${failureMessage}`
                  : failureMessage
              }
              if (lastItem) {
                // Keep the bubble in the NORMAL status so the failure
                // text stays visible as regular markdown content; the
                // TDesign 'error' status can hide the answer body.
                lastItem.status = ''
                const answerBlock = lastItem.content.find(
                  b => b.type === 'markdown'
                )
                if (answerBlock) answerBlock.data = normalizeDiagramLang(last.content)
              }
            }
            this.waitingForResponse = false
            this.streaming = false
            this.currentAbortController = null
            // Force Vue re-render on error so the error state is visible.
            this.chatItems = [...this.chatItems]
            // Mark the error as already rendered inside the assistant
            // bubble (e.g. provider quota exhaustion) so callers can
            // skip a duplicate global error toast.
            err.shownInBubble = true
            reject(err)
          }
        })
      })
    },

    /**
     * Cancel the currently streaming message.
     * Aborts the fetch request and marks the last assistant message as
     * stopped. Safe to call when nothing is streaming.
     */
    cancelStreaming() {
      if (this.currentAbortController) {
        this.currentAbortController.abort()
        this.currentAbortController = null
      }
      // Stop queued typewriter updates as well as the network stream so
      // no late frame can revive the thinking animation after cancellation.
      if (this._typewriterTimer) {
        clearInterval(this._typewriterTimer)
        this._typewriterTimer = null
      }
      this._typewriterQueue = []
      this._typewriterDone = true

      const last = this.messages[this.messages.length - 1]
      const lastItem = this.chatItems[this.chatItems.length - 1]
      if (last && last.role === 'assistant' && (last.streaming || last.thinking)) {
        last.streaming = false
        last.thinking = false
        last.aborted = true
        if (!last.content) last.content = '[已停止生成]'
        if (lastItem) {
          lastItem.status = 'stop'
          const answerBlock = lastItem.content.find(
            b => b.type === 'markdown'
          )
          if (answerBlock) answerBlock.data = normalizeDiagramLang(last.content)
          const reasoningBlock = lastItem.content.find(
            b => b.type === 'reasoning'
          )
          if (reasoningBlock) reasoningBlock.status = 'complete'
        }
      }
      this.streaming = false
      this.waitingForResponse = false
      // Force Vue re-render on cancel.
      this.chatItems = [...this.chatItems]
    }
  }
})
