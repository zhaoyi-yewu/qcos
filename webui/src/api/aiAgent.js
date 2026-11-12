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

import request from '@/utils/request'
import { useConfigStore } from '@/store/modules/config'
import { useComponentsStore } from '@/store/modules/components'
import { getToken } from '@/store/getters'

/**
 * Build the full URL for the AI chat endpoint.
 *
 * @returns {string} absolute URL
 */
function getAiChatUrl() {
  const cfg = useConfigStore()
  const base = cfg.activeEndpoint?.url || ''
  return `${base}/v1/ai/chat`
}

/**
 * Build the full URL for the AG-UI protocol chat endpoint.
 *
 * @returns {string} absolute URL
 */
function getAguiChatUrl() {
  const cfg = useConfigStore()
  const base = cfg.activeEndpoint?.url || ''
  return `${base}/v1/ai/chat/agui`
}

/**
 * Guard that throws when the AI agent feature is disabled on the backend.
 * All AI-agent API entry points call this before issuing any request so
 * the network stays quiet when the feature is off.
 */
function ensureAiAgentEnabled() {
  const componentsStore = useComponentsStore()
  if (!componentsStore.aiAgentEnabled) {
    return Promise.reject(new Error('AI 智能体功能未开启'))
  }
  return null
}

/**
 * Stream a chat message to the AI agent via SSE.
 *
 * Uses fetch + ReadableStream instead of EventSource so we can attach
 * the Authorization header.
 *
 * @param {object} opts - Chat options
 * @param {string} [opts.sessionId] - Existing session ID (null for new)
 * @param {string} opts.message - User message text
 * @param {boolean} [opts.enableRag] - Whether to enable RAG retrieval
 * @param {Array} [opts.attachments] - Image attachments [{kind, media_type, data}]
 * @param {string} [opts.modelId] - Configured model ID (omitted when unset)
 * @param {function} opts.onChunk - Called for each text chunk: (delta)
 * @param {function} opts.onToolCall - Called when a tool is invoked: (tool, args)
 * @param {function} opts.onToolResult - Called when a tool returns: (tool, result)
 * @param {function} opts.onDone - Called when stream ends: (messageId)
 * @param {function} opts.onError - Called on error: (error)
 */
export function streamChat({
  sessionId,
  message,
  enableRag = true,
  attachments = [],
  modelId = null,
  onChunk,
  onToolCall,
  onToolResult,
  onDone,
  onError
}) {
  const rejected = ensureAiAgentEnabled()
  if (rejected) {
    rejected.catch(onError)
    return
  }
  const url = getAiChatUrl()
  const token = getToken()

  fetch(url, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
      Accept: 'text/event-stream'
    },
    body: JSON.stringify({
      session_id: sessionId || null,
      message,
      enable_rag: enableRag,
      attachments,
      // Only send model_id when explicitly selected so older servers
      // keep receiving the legacy request shape.
      ...(modelId ? { model_id: modelId } : {})
    })
  })
    .then(response => {
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }
      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      function pump() {
        reader.read().then(({ done, value }) => {
          if (done) {
            onDone && onDone()
            return
          }
          buffer += decoder.decode(value, { stream: true })
          // Parse SSE events from buffer
          const events = buffer.split('\n\n')
          buffer = events.pop() || '' // Keep incomplete event in buffer
          for (const evt of events) {
            const line = evt.trim()
            if (!line.startsWith('data: ')) continue
            try {
              const data = JSON.parse(line.slice(6))
              if (data.type === 'chunk' && onChunk) {
                onChunk(data.delta)
              } else if (data.type === 'tool_call' && onToolCall) {
                onToolCall(data.tool, data.args)
              } else if (data.type === 'tool_result' && onToolResult) {
                onToolResult(data.tool, data.result)
              } else if (data.type === 'done' && onDone) {
                onDone(data.message_id)
              } else if (data.type === 'error' && onError) {
                onError(new Error(data.error))
              }
            } catch {
              // Ignore malformed SSE lines
            }
          }
          pump()
        }).catch(onError)
      }
      pump()
    })
    .catch(onError)
}

/**
 * Extract a human-readable error detail from a non-2xx response.
 *
 * FastAPI errors carry ``{"detail": "..."}`` while LLM gateways
 * usually return ``{"error": {"message": "..."}}``. Surfacing the
 * body (e.g. quota exhaustion) lets the assistant bubble show the
 * actual cause instead of a bare HTTP status line.
 *
 * @param {Response} response - failed fetch response
 * @returns {Promise<string>} error detail, empty when unavailable
 */
async function readErrorDetail(response) {
  let text
  try {
    text = (await response.text()).trim()
  } catch {
    return ''
  }
  if (!text) return ''
  try {
    const data = JSON.parse(text)
    if (typeof data.detail === 'string') return data.detail
    if (typeof data.error === 'string') return data.error
    if (data.error && typeof data.error.message === 'string') {
      return data.error.message
    }
  } catch {
    // Not JSON: fall through to the bounded raw body below.
  }
  // Bound non-JSON bodies (proxy HTML error pages) so the bubble
  // stays readable.
  return text.length > 300 ? `${text.slice(0, 300)}...` : text
}

/**
 * Stream a chat message to the AI agent via AG-UI protocol SSE.
 *
 * Uses @tdesign/ai-chat-engine for standardized AG-UI protocol
 * communication.
 *
 * @param {object} opts - Chat options
 * @param {string} [opts.sessionId] - Existing session ID (null for new)
 * @param {string} opts.message - User message text
 * @param {boolean} [opts.enableRag] - Whether to enable RAG retrieval
 * @param {Array} [opts.attachments] - Image attachments [{kind, media_type, data}]
 * @param {string} [opts.modelId] - Configured model ID (omitted when unset)
 * @param {function} opts.onChunk - Called for each text chunk: (delta)
 * @param {function} opts.onToolCall - Called when a tool is invoked: (tool, args)
 * @param {function} opts.onToolResult - Called when a tool returns: (tool, result)
 * @param {function} opts.onDone - Called when stream ends: (messageId, usage, sessionId)
 * @param {function} opts.onError - Called on error: (error)
 * @param {function} opts.onMessageUpdate - Called when message content updates
 */
export function streamChatAgui({
  sessionId,
  message,
  enableRag = true,
  attachments = [],
  modelId = null,
  onChunk,
  onThinking,
  onToolCall,
  onToolResult,
  onDone,
  onError,
  onMessageUpdate,
  signal // AbortSignal for cancellation
}) {
  const rejected = ensureAiAgentEnabled()
  if (rejected) {
    rejected.catch(onError)
    return
  }

  const url = getAguiChatUrl()
  const token = getToken()

  fetch(url, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
      Accept: 'text/event-stream'
    },
    body: JSON.stringify({
      session_id: sessionId || null,
      message,
      enable_rag: enableRag,
      attachments,
      // Only send model_id when explicitly selected so older servers
      // keep receiving the legacy request shape.
      ...(modelId ? { model_id: modelId } : {})
    }),
    signal // Attach abort signal
  })
    .then(async response => {
      if (!response.ok) {
        const detail = await readErrorDetail(response)
        throw new Error(
          detail || `HTTP ${response.status}: ${response.statusText}`
        )
      }
      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      // Track whether RUN_FINISHED has already fired so the reader
      // `done` fallback does not invoke onDone a second time. The
      // backend sends RUN_FINISHED exactly once at the end of a
      // successful stream; without this guard the store's onDone was
      // called twice, which raced with the streaming-state cleanup.
      let runFinished = false
      // Real session id reported by RUN_STARTED / RUN_FINISHED. The
      // frontend keys sessions off this value; only legacy servers
      // (which omit it) fall back to the messageId-as-sessionId
      // compatibility path.
      let responseSessionId = null

      function processBuffer() {
        // Parse SSE events from buffer. AG-UI uses standard SSE with
        // both `event:` and `data:` lines per event block. Handle both
        // \n and \r\n line endings since different backends / proxies
        // may normalize line endings differently.
        const normalized = buffer.replace(/\r\n/g, '\n')
        const events = normalized.split('\n\n')
        buffer = events.pop() || '' // Keep incomplete event in buffer
        for (const evt of events) {
          const lines = evt.trim().split('\n')
          let eventType = ''
          let dataLine = ''
          for (const line of lines) {
            if (line.startsWith('event: ')) {
              eventType = line.slice(7).trim()
            } else if (line.startsWith('data: ')) {
              dataLine = line.slice(6)
            }
          }
          if (!dataLine) continue
          try {
            const data = JSON.parse(dataLine)
            // Map AG-UI event types to our internal callbacks
            // Note: some backends omit the `event:` line and only set
            // `type` in the JSON payload, so we check both.
            const type = eventType || data.type
            if (type === 'TEXT_MESSAGE_CONTENT') {
              if (onChunk) {
                onChunk(data.delta || '')
              }
              if (onMessageUpdate) onMessageUpdate(data.messageId, data)
            } else if (type === 'THINKING_CONTENT') {
              // Chain-of-thought delta (reasoning). Routed to a
              // dedicated callback so the view can render it into a
              // separate collapsible "thinking" panel above the
              // assistant's final answer.
              if (onThinking) onThinking(data.delta || '')
            } else if (type === 'TOOL_CALL_START') {
              if (onToolCall) onToolCall(data.toolCallName, data.toolCallId)
            } else if (type === 'TOOL_CALL_RESULT') {
              if (onToolResult) onToolResult(data.toolCallName || data.toolCallId, data.content)
            } else if (type === 'TEXT_MESSAGE_END') {
              // Message-level framing event: no store callback needed,
              // the bubble content is already up to date. Acknowledge
              // it so it does not fall into the unknown-type branch.
            } else if (type === 'RUN_STARTED') {
              // Run-level framing event: carries the real session id.
              if (data.sessionId) responseSessionId = data.sessionId
            } else if (type === 'TEXT_MESSAGE_START') {
              // Message-level framing event: no-op for our store.
            } else if (type === 'RUN_FINISHED') {
              runFinished = true
              if (data.sessionId) responseSessionId = data.sessionId
              // Forward token-usage stats (when present) so the
              // status bar can accumulate input/output counters.
              if (onDone) onDone(data.messageId, data.usage || null, responseSessionId)
            } else if (type === 'RUN_ERROR') {
              runFinished = true
              if (onError) onError(new Error(data.error || 'Unknown error'))
            }
          } catch (e) {
            console.warn('Failed to parse SSE data:', e, dataLine)
          }
        }
      }

      function pump() {
        reader.read().then(({ done, value }) => {
          if (done) {
            // Flush any remaining buffer before signaling completion
            if (buffer.trim()) {
              processBuffer()
            }
            // Only call onDone from the reader-finished path when the
            // backend never sent RUN_FINISHED (e.g. connection dropped
            // mid-stream). When RUN_FINISHED was already processed,
            // calling onDone again here would race with the store's
            // cleanup and re-trigger state transitions.
            if (!runFinished && onDone) onDone()
            return
          }
          const decoded = decoder.decode(value, { stream: true })
          buffer += decoded
          processBuffer()
          pump()
        }).catch(err => {
          // Ignore abort errors - they're expected when user cancels
          if (err.name !== 'AbortError') {
            console.error('AI stream reader error:', err)
            onError(err)
          }
        })
      }
      pump()
    })
    .catch(err => {
      // Ignore abort errors - they're expected when user cancels
      if (err.name !== 'AbortError') {
        console.error('AI chat fetch error:', err)
        onError(err)
      }
    })
}

/**
 * Build the full URL for an AI session endpoint.
 *
 * @param {string} path - endpoint path (e.g. '/v1/ai/sessions')
 * @returns {string} absolute URL
 */
function getAiApiUrl(path) {
  const cfg = useConfigStore()
  const base = cfg.activeEndpoint?.url || ''
  return `${base}${path}`
}

/**
 * List AI models configured on the server.
 *
 * Older servers respond 404; the store treats that as "model menu
 * unavailable" and keeps chatting with the server-side default.
 *
 * @returns {Promise} axios response promise ({default_model_id, models})
 */
export function listModels() {
  const rejected = ensureAiAgentEnabled()
  if (rejected) return rejected
  return request({
    url: getAiApiUrl('/v1/ai/models'),
    method: 'get',
    // A 404 here just means the server predates multi-model support;
    // the store degrades gracefully without a global error toast.
    skipErrorStatuses: [404]
  })
}

/**
 * List all AI chat sessions for the current user.
 *
 * @returns {Promise} axios response promise
 */
export function listSessions() {
  const rejected = ensureAiAgentEnabled()
  if (rejected) return rejected
  return request({
    url: getAiApiUrl('/v1/ai/sessions'),
    method: 'get'
  })
}

/**
 * Get messages for a single session.
 *
 * @param {string} sessionId - Session ID
 * @returns {Promise} axios response promise
 */
export function getSession(sessionId) {
  const rejected = ensureAiAgentEnabled()
  if (rejected) return rejected
  return request({
    url: getAiApiUrl(`/v1/ai/sessions/${sessionId}`),
    method: 'get',
    // A locally persisted session may have expired on the backend.
    // The store clears that stale id without surfacing a global error.
    skipErrorStatuses: [404]
  })
}

/**
 * Delete a session.
 *
 * @param {string} sessionId - Session ID
 * @returns {Promise} axios response promise
 */
export function deleteSession(sessionId) {
  const rejected = ensureAiAgentEnabled()
  if (rejected) return rejected
  return request({
    url: getAiApiUrl(`/v1/ai/sessions/${sessionId}`),
    method: 'delete'
  })
}

/**
 * Create a new empty session.
 *
 * @param {string} title - Session title
 * @returns {Promise} axios response promise
 */
export function createSession(title = 'New conversation') {
  const rejected = ensureAiAgentEnabled()
  if (rejected) return rejected
  return request({
    url: getAiApiUrl('/v1/ai/sessions'),
    method: 'post',
    data: { title }
  })
}

/**
 * Truncate a session from an edited user message onwards.
 *
 * @param {string} sessionId - Session ID
 * @param {number} fromIndex - Zero-based user-message index
 * @param {string} expectedContent - Original text used for conflict checks
 * @returns {Promise} retained message prefix
 */
export function truncateSessionMessages(sessionId, fromIndex, expectedContent) {
  const rejected = ensureAiAgentEnabled()
  if (rejected) return rejected
  return request({
    url: getAiApiUrl(`/v1/ai/sessions/${sessionId}/messages/truncate`),
    method: 'post',
    data: {
      from_index: fromIndex,
      expected_content: expectedContent
    }
  })
}

/**
 * Clear all messages in a session without deleting the session.
 * Keeps the session record (id / title / created_at) so the
 * conversation stays in the user's session list.
 *
 * @param {string} sessionId - Session ID
 * @returns {Promise} axios response promise
 */
export function clearSessionMessages(sessionId) {
  const rejected = ensureAiAgentEnabled()
  if (rejected) return rejected
  return request({
    url: getAiApiUrl(`/v1/ai/sessions/${sessionId}/messages`),
    method: 'delete'
  })
}
