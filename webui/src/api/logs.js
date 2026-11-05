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

import { httpRequest } from '@/api/jsonrpc'
import request from '@/utils/request'
import { useConfigStore } from '@/store/modules/config'
import { useComponentsStore } from '@/store/modules/components'

/**
 * Guard that rejects when the VictoriaLogs reverse proxy is disabled.
 *
 * @returns {Promise|null} rejected promise when disabled, null when enabled
 */
function ensureVictorialogsEnabled() {
  const componentsStore = useComponentsStore()
  if (!componentsStore.proxyVictorialogsEnabled) {
    return Promise.reject(new Error('日志功能未开启'))
  }
  return null
}

/**
 * Build the full URL for a VictoriaLogs HTTP API path.
 *
 * Resolution order:
 *   1. If the active endpoint defines `victorialogs_url`, the path is appended
 *      to that base and returned as an absolute URL (direct access, no QCOS
 *      reverse proxy involved).
 *   2. Otherwise fall back to the QCOS API reverse-proxy path
 *      `/v1/proxy/victorialogs/...` resolved against the active endpoint url.
 *
 * @param {string} path - VictoriaLogs API path starting with '/' (e.g. '/select/logsql/query')
 * @returns {string|null} absolute URL when `victorialogs_url` is set, or null
 *   to signal the caller should use the default reverse-proxy path
 */
function resolveVictoriaLogsUrl(path) {
  const cfg = useConfigStore()
  const base = cfg.activeEndpoint && cfg.activeEndpoint.victorialogs_url
  if (!base) return null
  return `${base}${path}`
}

/**
 * Issue a GET request against an absolute URL (used when victorialogs_url
 * override is configured on the active endpoint).
 *
 * @param {string} url - absolute URL
 * @param {object} [params] - query params
 * @returns {Promise} axios response promise
 */
function httpRequestAbsolute(url, params = null) {
  const opts = {
    url,
    method: 'get',
    headers: { 'Content-Type': 'application/json' }
  }
  if (params !== null) {
    opts.params = params
  }
  return request(opts)
}

/**
 * Query logs from VictoriaLogs via LogSQL.
 *
 * Uses the endpoint's `victorialogs_url` override when configured; otherwise
 * falls back to the QCOS API reverse proxy `/v1/proxy/victorialogs/...`.
 *
 * @param {object} opts - Query options
 * @param {string} opts.query - LogSQL query string
 * @param {string} [opts.start] - Start time (RFC3339 or Unix timestamp)
 * @param {string} [opts.end] - End time (RFC3339 or Unix timestamp)
 * @param {number} [opts.limit] - Max number of entries to return
 * @param {number} [opts.offset] - Offset for pagination
 * @returns {Promise} axios response promise (NDJSON body)
 */
export function queryLogs({ query, start, end, limit, offset }) {
  const rejected = ensureVictorialogsEnabled()
  if (rejected) return rejected
  const params = { query }
  if (start !== undefined && start !== null) params.start = start
  if (end !== undefined && end !== null) params.end = end
  if (limit !== undefined && limit !== null) params.limit = limit
  if (offset !== undefined && offset !== null) params.offset = offset

  const direct = resolveVictoriaLogsUrl('/select/logsql/query')
  if (direct) {
    return httpRequestAbsolute(direct, params)
  }
  return httpRequest('/v1/proxy/victorialogs/select/logsql/query', 'get', null, params)
}

/**
 * Get available log field names from VictoriaLogs.
 *
 * @returns {Promise} axios response promise
 */
export function getLogFields() {
  const rejected = ensureVictorialogsEnabled()
  if (rejected) return rejected
  const direct = resolveVictoriaLogsUrl('/select/logsql/field_names')
  if (direct) {
    return httpRequestAbsolute(direct, {})
  }
  return httpRequest('/v1/proxy/victorialogs/select/logsql/field_names', 'get', null, {})
}

/**
 * Get values for a specific log field from VictoriaLogs.
 *
 * @param {string} field - Field name
 * @param {object} [opts] - Query options
 * @param {string} [opts.query] - LogSQL query to filter entries
 * @param {string} [opts.start] - Start time
 * @param {string} [opts.end] - End time
 * @param {number} [opts.limit] - Max values to return
 * @returns {Promise} axios response promise
 */
export function getLogFieldValues(field, opts = {}) {
  const rejected = ensureVictorialogsEnabled()
  if (rejected) return rejected
  const params = { field }
  if (opts.query) params.query = opts.query
  if (opts.start) params.start = opts.start
  if (opts.end) params.end = opts.end
  if (opts.limit) params.limit = opts.limit

  const direct = resolveVictoriaLogsUrl('/select/logsql/field_values')
  if (direct) {
    return httpRequestAbsolute(direct, params)
  }
  return httpRequest('/v1/proxy/victorialogs/select/logsql/field_values', 'get', null, params)
}

/**
 * Parse NDJSON response text into an array of log entries.
 *
 * VictoriaLogs returns one JSON object per line. Empty lines are skipped.
 *
 * @param {string} text - Raw NDJSON response body
 * @returns {Array<Object>} Parsed log entries
 */
export function parseNdjson(text) {
  if (!text || typeof text !== 'string') {
    return []
  }
  return text
    .split('\n')
    .filter(line => line.trim().length > 0)
    .map(line => {
      try {
        return JSON.parse(line)
      } catch {
        return { _raw: line }
      }
    })
}

/**
 * Format a log timestamp for display.
 *
 * @param {string|number} ts - Timestamp (RFC3339 string or Unix seconds/ms)
 * @returns {string} Formatted timestamp
 */
export function formatLogTime(ts) {
  if (!ts) return '-'
  try {
    const d = new Date(ts)
    if (Number.isNaN(d.getTime())) return String(ts)
    return d.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false
    })
  } catch {
    return String(ts)
  }
}
