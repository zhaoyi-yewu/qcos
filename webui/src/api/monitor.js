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

import { jsonrpcRequest, httpRequest } from '@/api/jsonrpc'
import request from '@/utils/request'
import { useConfigStore } from '@/store/modules/config'

/**
 * Query health status of reverse-proxy upstream services
 * (Prometheus, Alertmanager, etc.).
 *
 * The response.result contains:
 *   - targets: Array of {name, path, base_url, enabled, healthy, status, latency_ms, detail}
 *
 * @returns {Promise} axios response promise
 */
export function getProxyHealth() {
  return jsonrpcRequest('/v1/metrics', 'get_proxy_health')
}

/**
 * Build the full URL for a Prometheus HTTP API path.
 *
 * Resolution order:
 *   1. If the active endpoint defines `prometheus_url`, the path is appended
 *      to that base and returned as an absolute URL (direct access, no QCOS
 *      reverse proxy involved).
 *   2. Otherwise fall back to the QCOS API reverse-proxy path
 *      `/v1/proxy/prometheus/...` resolved against the active endpoint url.
 *
 * @param {string} path - Prometheus API path starting with '/' (e.g. '/api/v1/query')
 * @returns {string|null} absolute URL when `prometheus_url` is set, or null
 *   to signal the caller should use the default reverse-proxy path
 */
function resolvePrometheusUrl(path) {
  const cfg = useConfigStore()
  const base = cfg.activeEndpoint && cfg.activeEndpoint.prometheus_url
  if (!base) return null
  return `${base}${path}`
}

/**
 * Build the full URL for an Alertmanager HTTP API path.
 *
 * Mirrors resolvePrometheusUrl() but for Alertmanager. See that function
 * for resolution order details.
 *
 * @param {string} path - Alertmanager API path starting with '/' (e.g. '/api/v2/alerts')
 * @returns {string|null} absolute URL when `alertmanager_url` is set, or null
 *   to signal the caller should use the default reverse-proxy path
 */
function resolveAlertmanagerUrl(path) {
  const cfg = useConfigStore()
  const base = cfg.activeEndpoint && cfg.activeEndpoint.alertmanager_url
  if (!base) return null
  return `${base}${path}`
}

/**
 * Issue a GET request against an absolute URL (used when prometheus_url /
 * alertmanager_url overrides are configured on the active endpoint).
 *
 * Shares the same axios instance as `httpRequest` so interceptors (error
 * handling, etc.) apply uniformly, but skips the QCOS endpoint base URL
 * because the target lives outside the QCOS API server.
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
 * Query Prometheus instant metric.
 *
 * Uses the endpoint's `prometheus_url` override when configured; otherwise
 * falls back to the QCOS API reverse proxy `/v1/proxy/prometheus/...`.
 *
 * @param {string} query - PromQL expression, e.g. 'sum(job_count{status="total"})'
 * @param {number} [time] - Evaluation timestamp (Unix seconds). Default: now
 * @returns {Promise} axios response promise
 */
export function queryPrometheus(query, time = null) {
  const params = { query }
  if (time !== null) {
    params.time = time
  }
  const direct = resolvePrometheusUrl('/api/v1/query')
  if (direct) {
    return httpRequestAbsolute(direct, params)
  }
  return httpRequest('/v1/proxy/prometheus/api/v1/query', 'get', null, params)
}

/**
 * Query Prometheus range metric.
 *
 * Uses the endpoint's `prometheus_url` override when configured; otherwise
 * falls back to the QCOS API reverse proxy `/v1/proxy/prometheus/...`.
 *
 * @param {string} query - PromQL expression
 * @param {number} start - Start timestamp (Unix seconds)
 * @param {number} end - End timestamp (Unix seconds)
 * @param {number|string} step - Query resolution step width (seconds or duration string like '15s')
 * @returns {Promise} axios response promise
 */
export function queryPrometheusRange(query, start, end, step = '15s') {
  const params = { query, start, end, step }
  const direct = resolvePrometheusUrl('/api/v1/query_range')
  if (direct) {
    return httpRequestAbsolute(direct, params)
  }
  return httpRequest('/v1/proxy/prometheus/api/v1/query_range', 'get', null, params)
}

/**
 * Get active alerts from Alertmanager.
 *
 * Uses the endpoint's `alertmanager_url` override when configured; otherwise
 * falls back to the QCOS API reverse proxy `/v1/proxy/alertmanager/...`.
 *
 * @param {object} [filter] - Filter options
 * @param {boolean} [filter.active] - Show active alerts (default: true)
 * @param {boolean} [filter.silenced] - Show silenced alerts (default: false)
 * @param {boolean} [filter.inhibited] - Show inhibited alerts (default: false)
 * @param {boolean} [filter.unprocessed] - Show unprocessed alerts (default: false)
 * @returns {Promise} axios response promise
 */
export function getAlerts(filter = {}) {
  const params = {
    active: filter.active !== undefined ? filter.active : true,
    silenced: filter.silenced !== undefined ? filter.silenced : false,
    inhibited: filter.inhibited !== undefined ? filter.inhibited : false,
    unprocessed: filter.unprocessed !== undefined ? filter.unprocessed : false
  }
  const direct = resolveAlertmanagerUrl('/api/v2/alerts')
  if (direct) {
    return httpRequestAbsolute(direct, params)
  }
  return httpRequest('/v1/proxy/alertmanager/api/v2/alerts', 'get', null, params)
}

/**
 * Get alert groups from Alertmanager.
 *
 * Uses the endpoint's `alertmanager_url` override when configured; otherwise
 * falls back to the QCOS API reverse proxy `/v1/proxy/alertmanager/...`.
 *
 * @returns {Promise} axios response promise
 */
export function getAlertGroups() {
  const direct = resolveAlertmanagerUrl('/api/v2/alerts/groups')
  if (direct) {
    return httpRequestAbsolute(direct, {})
  }
  return httpRequest('/v1/proxy/alertmanager/api/v2/alerts/groups', 'get', null, {})
}

// ==================== 预定义 PromQL 查询 ====================

export const PROMQL = {
  // 系统健康
  systemHealthy: 'system_healthy',
  // 作业统计
  jobTotal: 'sum(job_count{status="total"}) or vector(0)',
  jobRunning: 'sum(job_count{status="running"}) or vector(0)',
  jobQueued: 'sum(job_count{status="queued"}) or vector(0)',
  jobCompleted: 'sum(job_count{status="completed"}) or vector(0)',
  jobFailed: 'sum(job_count{status="failed"}) or vector(0)',
  jobCancelled: 'sum(job_count{status="cancelled"}) or vector(0)',
  jobSubmittedRate: 'sum(job_count{status="submitted_job_rate_min"}) or vector(0)',
  jobCompletedRate: 'sum(job_count{status="completed_job_rate_min"}) or vector(0)',
  // 作业趋势（范围查询）
  jobTrendTotal: 'sum(job_count{status="total"})',
  jobTrendCompleted: 'sum(job_count{status="completed"})',
  jobTrendFailed: 'sum(job_count{status="failed"})',
  // API 统计
  apiRequestRate: 'sum(rate(api_requests_total[5m])) by (status_code)',
  apiDurationP95: 'histogram_quantile(0.95, sum(rate(api_request_duration_bucket[5m])) by (le))',
  apiDurationP50: 'histogram_quantile(0.50, sum(rate(api_request_duration_bucket[5m])) by (le))',
  apiInProgress: 'api_requests_in_progress',
  apiEndpointCalls: 'sum by (endpoint) (increase(api_requests_total[1h]))'
}

// ==================== 数据解析工具 ====================

/**
 * 从 Prometheus 响应中提取最新值
 * @param {object} response - Prometheus API 响应
 * @returns {number|null} 最新值，解析失败返回 null
 */
export function extractLatestValue(response) {
  try {
    if (response.status !== 'success' || !response.data || !response.data.result) {
      return null
    }
    const result = response.data.result
    if (result.length === 0) {
      return 0
    }
    const value = result[0].value
    if (!value || value.length < 2) {
      return null
    }
    return parseFloat(value[1])
  } catch (e) {
    console.error('Failed to extract latest value:', e)
    return null
  }
}

/**
 * 从 Prometheus 范围查询响应中提取时序数据
 * @param {object} response - Prometheus API 响应
 * @param {string} [label] - 序列名称（用于图例）
 * @returns {Array} ECharts 数据格式 [[timestamp, value], ...]
 */
export function extractTimeSeries(response, label = '') {
  try {
    if (response.status !== 'success' || !response.data || !response.data.result) {
      return []
    }
    const result = response.data.result
    if (result.length === 0) {
      return []
    }
    // 取第一个序列的值
    const values = result[0].values || []
    return values.map(v => [v[0] * 1000, parseFloat(v[1])])
  } catch (e) {
    console.error('Failed to extract time series:', e)
    return []
  }
}

/**
 * 从 Prometheus 范围查询响应中提取多个序列
 * @param {object} response - Prometheus API 响应
 * @param {string} [defaultName] - 当 metric 为空时的默认序列名称
 * @returns {Array} [{name, data: [[timestamp, value], ...]}, ...]
 */
export function extractMultiTimeSeries(response, defaultName = '') {
  try {
    if (response.status !== 'success' || !response.data || !response.data.result) {
      return []
    }
    return response.data.result.map(series => {
      const metric = series.metric || {}
      const name = metric.status_code || metric.endpoint || metric.__name__ || defaultName || 'unknown'
      const values = series.values || []
      return {
        name,
        data: values.map(v => [v[0] * 1000, parseFloat(v[1])])
      }
    })
  } catch (e) {
    console.error('Failed to extract multi time series:', e)
    return []
  }
}

/**
 * 格式化告警数据用于表格展示
 * @param {Array} alerts - Alertmanager 告警列表
 * @returns {Array} 格式化后的告警对象数组
 */
export function formatAlerts(alerts) {
  if (!Array.isArray(alerts)) {
    return []
  }
  return alerts.map(alert => ({
    alertname: alert.labels?.alertname || 'Unknown',
    severity: alert.labels?.severity || 'info',
    instance: alert.labels?.instance || '-',
    status: alert.status?.state || 'unknown',
    startsAt: alert.startsAt ? new Date(alert.startsAt).toLocaleString('zh-CN') : '-',
    // Alertmanager sets endsAt to a zero/future timestamp while the alert
    // is still firing; once resolved it carries the actual resolution time.
    // Treat zero/1-01-01 or future timestamps as "still active" so the
    // history column shows "-" instead of a bogus date.
    endsAt: (() => {
      if (!alert.endsAt) return '-'
      const t = new Date(alert.endsAt)
      if (Number.isNaN(t.getTime())) return '-'
      if (t.getFullYear() <= 1) return '-'
      if (t.getTime() > Date.now()) return '-'
      return t.toLocaleString('zh-CN')
    })(),
    summary: alert.annotations?.summary || alert.annotations?.description || '-',
    raw: alert
  }))
}
