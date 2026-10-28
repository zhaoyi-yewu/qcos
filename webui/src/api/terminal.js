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

import axios from 'axios'
import { useConfigStore } from '@/store/modules/config'
import { getSession } from '@/utils/session'

const HEARTBEAT_INTERVAL_MS = 25 * 1000
const MAX_RECONNECT_ATTEMPTS = 3
const INITIAL_RECONNECT_DELAY_MS = 1000

/**
 * Get the currently active endpoint's HTTP base URL.
 *
 * The endpoint's `url` field has two shapes depending on the runtime:
 *   - dev mode (vite proxy): a relative path like `/api/<name>`; the
 *     vite dev server proxies it to the real QCOS API.
 *   - prod mode (nginx): an absolute URL like `http://host:18401`; nginx
 *     forwards `/api/<name>/...` to the upstream QCOS API.
 *
 * In both cases the returned base already ends with the per-endpoint
 * prefix when needed, so callers can append `/v1/...` directly.
 *
 * @returns {string} base URL or empty string when no endpoint is configured
 */
function getHttpBase() {
  const cfg = useConfigStore()
  const url = cfg.activeEndpoint && cfg.activeEndpoint.url
  if (!url || typeof url !== 'string') {
    // fallback to same-origin
    return window.location.origin
  }
  // dev mode: relative path (e.g. `/api/local`) — keep as-is so the
  // vite proxy intercepts it; same-origin so no host prefix is needed.
  if (url.startsWith('/')) {
    return url
  }
  // prod mode: absolute URL pointing at the webui nginx. The nginx
  // config routes per-endpoint under `/api/<name>/`, so append that
  // prefix here. Only the origin (protocol + host + port) is taken
  // from the configured URL; any trailing path is dropped.  Wrap in
  // try/catch because a malformed URL would otherwise bubble a
  // TypeError out of every upload/download call.
  let parsed
  try {
    parsed = new URL(url)
  } catch (e) {
    return window.location.origin
  }
  const name = cfg.activeEndpointName
  return `${parsed.origin}/api/${name}`
}

/**
 * Get the JWT token for the active endpoint session.
 *
 * @returns {string} token or empty string
 */
export function getTerminalToken() {
  const cfg = useConfigStore()
  const sess = cfg.activeEndpointName ? getSession(cfg.activeEndpointName) : null
  return (sess && sess.token) || ''
}

/**
 * Build the WebSocket base URL for the terminal endpoint.
 *
 * Mirrors getHttpBase() but uses the ws(s) scheme. Handles both shapes
 * of `activeEndpoint.url`:
 *   - relative path `/api/<name>` (dev mode, vite proxy with ws:true)
 *   - absolute URL `http(s)://host:port` (prod mode, webui nginx)
 *
 * In prod mode the per-endpoint nginx prefix `/api/<name>` is appended
 * so nginx can route the request to the correct upstream QCOS API.
 *
 * @returns {string} ws(s)://host[:port][/api/<name>]
 */
export function getWsBase() {
  const cfg = useConfigStore()
  const url = cfg.activeEndpoint && cfg.activeEndpoint.url
  const wsProtoOf = (p) => (p === 'https:' ? 'wss:' : 'ws:')

  if (!url || typeof url !== 'string') {
    // fallback to same-origin
    const proto = wsProtoOf(window.location.protocol)
    return `${proto}//${window.location.host}`
  }
  // dev mode: relative path (e.g. `/api/local`) — base on current
  // origin so the vite dev-server proxy (with ws:true) picks it up.
  if (url.startsWith('/')) {
    const proto = wsProtoOf(window.location.protocol)
    return `${proto}//${window.location.host}${url}`
  }
  // prod mode: absolute URL pointing at the webui nginx. Take only the
  // origin and append the per-endpoint prefix `/api/<name>` so nginx
  // routes the upgrade request to the right upstream.
  let parsed
  try {
    parsed = new URL(url)
  } catch (e) {
    const proto = wsProtoOf(window.location.protocol)
    return `${proto}//${window.location.host}`
  }
  const proto = wsProtoOf(parsed.protocol)
  const name = cfg.activeEndpointName
  return `${proto}//${parsed.host}/api/${name}`
}

/**
 * Normalize axios/fetch errors into a plain { status, message } object.
 *
 * @param {Error|Object} err - thrown error
 * @param {string} fallback - fallback message when the error has none
 * @returns {{status: number, message: string}}
 */
function normalizeHttpError(err, fallback = 'request failed') {
  if (!err) {
    return { status: 0, message: fallback }
  }
  if (err.status !== undefined && err.message !== undefined && !err.isAxiosError) {
    return { status: err.status, message: err.message }
  }
  const resp = err.response
  if (resp) {
    const data = resp.data
    let msg = ''
    if (data && typeof data === 'object') {
      msg = data.message || data.detail || (data.error && data.error.message) || ''
    } else if (typeof data === 'string') {
      msg = data
    }
    return { status: resp.status || 0, message: msg || fallback }
  }
  return { status: 0, message: err.message || fallback }
}

/**
 * Build axios request config with Authorization header attached.
 *
 * @param {Object} extra - extra axios config to merge
 * @returns {Object} axios config
 */
function withAuth(extra = {}) {
  const token = getTerminalToken()
  const headers = { ...(extra.headers || {}) }
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }
  return { ...extra, headers }
}

/**
 * Create a terminal WebSocket connection.
 *
 * The socket authenticates on the first frame, forwards messages to
 * `onMessage`, reconnects with exponential backoff (max
 * MAX_RECONNECT_ATTEMPTS attempts) on unexpected close, and sends a
 * heartbeat `ping` every 25s while open.
 *
 * @param {Object} options
 * @param {number} options.cols - initial terminal columns
 * @param {number} options.rows - initial terminal rows
 * @param {string} options.token - JWT token (sent as the first auth frame)
 * @param {Function} options.onMessage - called with the parsed JSON message
 * @param {Function} [options.onOpen] - called after the socket opens
 * @param {Function} [options.onClose] - called when the socket closes
 *   (after any automatic reconnect attempts are exhausted or after a
 *   manual close())
 * @param {Function} [options.onError] - called on socket error
 * @returns {{send: Function, close: Function, isOpen: Function}}
 */
export function createTerminalSocket({ cols, rows, token, onMessage, onOpen, onClose, onError }) {
  let ws = null
  let heartbeatTimer = null
  let reconnectAttempts = 0
  let closedByUser = false
  let authed = false

  const buildUrl = () => {
    const base = getWsBase()
    const c = encodeURIComponent(cols)
    const r = encodeURIComponent(rows)
    return `${base}/v1/terminal/ws?cols=${c}&rows=${r}`
  }

  const clearHeartbeat = () => {
    if (heartbeatTimer) {
      clearInterval(heartbeatTimer)
      heartbeatTimer = null
    }
  }

  const startHeartbeat = () => {
    clearHeartbeat()
    heartbeatTimer = setInterval(() => {
      if (ws && ws.readyState === WebSocket.OPEN) {
        try {
          ws.send(JSON.stringify({ type: 'ping' }))
        } catch (e) {
          // ignore send errors on heartbeat
        }
      }
    }, HEARTBEAT_INTERVAL_MS)
  }

  const connect = () => {
    const url = buildUrl()
    ws = new WebSocket(url)

    ws.onopen = () => {
      try {
        ws.send(JSON.stringify({ type: 'auth', token }))
      } catch (e) {
        // fall through; server will close with 4401 on timeout
      }
      if (typeof onOpen === 'function') {
        onOpen()
      }
    }

    ws.onmessage = (ev) => {
      let msg = null
      try {
        msg = JSON.parse(ev.data)
      } catch (e) {
        return
      }
      if (msg && msg.type === 'auth_ok') {
        authed = true
        reconnectAttempts = 0
        startHeartbeat()
      }
      if (typeof onMessage === 'function') {
        onMessage(msg)
      }
    }

    ws.onerror = (ev) => {
      if (typeof onError === 'function') {
        onError(ev)
      }
    }

    ws.onclose = (ev) => {
      clearHeartbeat()
      const wasAuthed = authed
      authed = false
      if (closedByUser) {
        if (typeof onClose === 'function') {
          onClose(ev, { willReconnect: false })
        }
        return
      }
      // Do not attempt to reconnect if the server rejected auth (4401/4403)
      // or if the close arrived before a successful auth.
      if (ev.code === 4401 || ev.code === 4403 || !wasAuthed) {
        if (typeof onClose === 'function') {
          onClose(ev, { willReconnect: false })
        }
        return
      }
      if (reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
        if (typeof onClose === 'function') {
          onClose(ev, { willReconnect: false })
        }
        return
      }
      const delay = INITIAL_RECONNECT_DELAY_MS * Math.pow(2, reconnectAttempts)
      reconnectAttempts += 1
      if (typeof onClose === 'function') {
        onClose(ev, { willReconnect: true, attempt: reconnectAttempts, delay })
      }
      setTimeout(connect, delay)
    }
  }

  connect()

  return {
    /**
     * Send a JSON message over the socket. No-op when not connected.
     *
     * @param {Object} obj - message payload
     */
    send(obj) {
      if (ws && ws.readyState === WebSocket.OPEN) {
        try {
          ws.send(JSON.stringify(obj))
        } catch (e) {
          // ignore
        }
      }
    },
    /**
     * Permanently close the socket; disables automatic reconnect.
     */
    close() {
      closedByUser = true
      clearHeartbeat()
      if (ws) {
        try {
          ws.close()
        } catch (e) {
          // ignore
        }
      }
    },
    /**
     * @returns {boolean} true when the socket is currently OPEN
     */
    isOpen() {
      return !!ws && ws.readyState === WebSocket.OPEN
    }
  }
}

/**
 * List files under a directory in the current user's sandbox /data.
 *
 * @param {string} path - path relative to /data; '' for the root
 * @returns {Promise<Array<{name,is_dir,size,mtime}>>}
 */
export async function listFiles(path = '') {
  const base = getHttpBase()
  try {
    const resp = await axios(withAuth({
      url: `${base}/v1/terminal/files`,
      method: 'get',
      params: { path }
    }))
    return Array.isArray(resp.data) ? resp.data : []
  } catch (err) {
    throw normalizeHttpError(err, 'list files failed')
  }
}

/**
 * Upload a file into a directory in the sandbox /data.
 *
 * @param {string} dir - target directory, relative to /data
 * @param {File|Blob} file - the file to upload
 * @param {Function} [onProgress] - called with percent (0-100)
 * @returns {Promise<Object>} server response data
 */
export async function uploadFile(dir, file, onProgress) {
  const base = getHttpBase()
  const form = new FormData()
  form.append('file', file)
  try {
    const resp = await axios(withAuth({
      url: `${base}/v1/terminal/files/upload`,
      method: 'post',
      params: { path: dir },
      data: form,
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 0,
      onUploadProgress: (e) => {
        if (typeof onProgress === 'function' && e && e.total) {
          onProgress(Math.round((e.loaded * 100) / e.total))
        }
      }
    }))
    return resp.data
  } catch (err) {
    throw normalizeHttpError(err, 'upload failed')
  }
}

/**
 * Trigger a browser download for a file in the sandbox /data.
 *
 * @param {string} path - file path relative to /data
 * @returns {Promise<void>}
 */
export async function downloadFile(path) {
  const base = getHttpBase()
  try {
    const resp = await axios(withAuth({
      url: `${base}/v1/terminal/files/download`,
      method: 'get',
      params: { path },
      responseType: 'blob',
      timeout: 0
    }))
    const blob = resp.data
    // Derive the filename from the requested path; the backend sends a
    // Content-Disposition but it is simpler and safer to use the basename.
    const name = (path || '').split('/').filter(Boolean).pop() || 'download'
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = name
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    window.URL.revokeObjectURL(url)
  } catch (err) {
    throw normalizeHttpError(err, 'download failed')
  }
}

/**
 * Delete a file or empty directory in the sandbox /data.
 *
 * @param {string} path - path relative to /data
 * @returns {Promise<Object>} server response data
 */
export async function deleteFile(path) {
  const base = getHttpBase()
  try {
    const resp = await axios(withAuth({
      url: `${base}/v1/terminal/files`,
      method: 'delete',
      params: { path }
    }))
    return resp.data
  } catch (err) {
    throw normalizeHttpError(err, 'delete failed')
  }
}
