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
import { streamChatAgui, listSessions, getSession, deleteSession, createSession, clearSessionMessages } from '@/api/aiAgent'
import { useComponentsStore } from '@/store/modules/components'

const STORAGE_KEY = 'qcos-ai-agent'

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

      // ===== Input draft =====
      draft: '',

      // ===== AbortController for cancelling streaming =====
      currentAbortController: null,

      // Injected by AiAgentChat.vue on setup so _buildChatItem can
      // resolve name/avatar/datetime without a circular dependency.
      _chatItemMetaResolver: null
    }
  },

  actions: {
    open(mode) {
      if (mode) {
        this.displayMode = mode
      }
      this.visible = true
      this.minimized = false
      // Restore the previous conversation when the panel re-opens and
      // we still have a session id from a prior visit (persisted in
      // localStorage). Messages are loaded lazily only when empty so
      // we don't clobber an in-progress draft conversation.
      if (
        this.activeSessionId
        && this.messages.length === 0
      ) {
        this.loadSession(this.activeSessionId).catch(() => {
          // Session may have expired on the backend - clear the
          // stale id so the next send starts a fresh conversation.
          this.activeSessionId = null
          persist(this)
        })
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

    async fetchSessions() {
      try {
        const res = await listSessions()
        this.sessions = res || []
      } catch (e) {
        console.error('Failed to fetch AI sessions:', e)
        this.sessions = []
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
          attachments: m.attachments || []
        }))
        this._rebuildChatItems()
      } catch (e) {
        console.error('Failed to load session:', e)
        this.messages = []
        this.chatItems = []
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
        data: text
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
        // TDesign Chat 0.7.0 bug: any truthy item.status is coerced
        // to "pending" by t-chat-list's status expression, causing
        // the loading spinner to show forever. Use '' for normal
        ///streaming states so the textLoading prop on t-chat-list
        // controls the pending animation instead.
        status: m.error ? 'error'
              : m.aborted ? 'stop'
              : '',
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
     * Retry an assistant message: drop the assistant reply, then
     * re-send the preceding user message. Used by the per-message
     * retry button.
     */
    async retryMessage(raw) {
      const idx = this.messages.indexOf(raw)
      if (idx < 0 || raw.role !== 'assistant') return
      // Find the user message that prompted this reply.
      const userMsg = this.messages[idx - 1]
      if (!userMsg || userMsg.role !== 'user') return
      const text = userMsg.content
      // Drop both messages (assistant + user prompt) and re-send.
      this.messages.splice(idx - 1, 2)
      this._rebuildChatItems()
      await this.sendMessage(text)
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
      // (the in-flight assistant bubble shows the failure).
      this.sendMessage(next.text).catch(err => {
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

    async sendMessage(text) {
      if (!text && this.pendingAttachments.length === 0) return

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
          attachments: [...this.pendingAttachments]
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
        thinking: true // Mark as waiting for first chunk
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
          if (answerBlock) answerBlock.data = last.content

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
          onDone: (messageId, usage) => {
            stopTypewriter()
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
                if (answerBlock) answerBlock.data = last.content
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
            if (!this.activeSessionId && messageId) {
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
            console.error('AI chat stream error:', err)
            stopTypewriter()
            const last = this.messages[this.messages.length - 1]
            const lastItem = this.chatItems[this.chatItems.length - 1]
            if (last && last.role === 'assistant') {
              const errorDetail = err.message || '未知错误'
              last.streaming = false
              last.thinking = false
              last.error = true
              if (!last.content) {
                last.content = `抱歉，AI 助手请求失败: ${errorDetail}`
              }
              if (lastItem) {
                lastItem.status = 'error'
                const answerBlock = lastItem.content.find(
                  b => b.type === 'markdown'
                )
                if (answerBlock) answerBlock.data = last.content
              }
            }
            this.waitingForResponse = false
            this.streaming = false
            this.currentAbortController = null
            // Force Vue re-render on error so the error state is visible.
            this.chatItems = [...this.chatItems]
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
      const last = this.messages[this.messages.length - 1]
      const lastItem = this.chatItems[this.chatItems.length - 1]
      if (last && last.role === 'assistant' && last.streaming) {
        last.streaming = false
        last.thinking = false
        last.aborted = true
        if (!last.content) last.content = '[已停止生成]'
        if (lastItem) {
          // TDesign Chat 0.7.0: use '' so t-chat-list's
          // textLoading controls the pending animation.
          lastItem.status = ''
          const answerBlock = lastItem.content.find(
            b => b.type === 'markdown'
          )
          if (answerBlock) answerBlock.data = last.content
        }
      }
      this.streaming = false
      this.waitingForResponse = false
      // Force Vue re-render on cancel.
      this.chatItems = [...this.chatItems]
    }
  }
})
