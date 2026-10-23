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

import { jsonrpcRequest } from '@/api/jsonrpc'

/**
 * Query the overall system health status.
 *
 * The response.result contains:
 *   - system_healthy: boolean
 *   - heartbeat_timestamp: float
 *   - component_status: { fastapi, redis, prefect, worke
 *
 * @returns {Promise} axios response promise
 */
export function getSystemHealth() {
  return jsonrpcRequest('/v1/metrics', 'get_system_health')
}

/**
 * Query API access statistics.
 *
 * The response.result contains:
 *   - total_requests: int
 *   - last_hour_requests: int
 *   - last_day_requests: int
 *
 * @returns {Promise} axios response promise
 */
export function getApiStats() {
  return jsonrpcRequest('/v1/metrics', 'get_api_stats')
}

/**
 * Query job statistics.
 *
 * The response.result contains:
 *   - total, completed, failed, running, queued,
 *     cancelling, cancelled, deleting, deleted, unknown: int
 *   - submitted_job_rate_min: float
 *   - completed_job_rate_min: float
 *
 * @returns {Promise} axios response promise
 */
export function getJobStats() {
  return jsonrpcRequest('/v1/metrics', 'get_job_stats')
}

/**
 * Query memory usage of the API server process.
 *
 * The response.result contains:
 *   - pid: int
 *   - rss_mb: float
 *   - vms_mb: float
 *   - thread_count: int
 *   - num_objects: int
 *   - cpu_percent: float
 *
 * @returns {Promise} axios response promise
 */
export function showMem() {
  return jsonrpcRequest('/v1/system', 'show_mem')
}

/**
 * Manually trigger garbage collection on the API server process.
 *
 * @param {number} generations - GC generations to collect (0, 1, 2). Default: 2
 * @returns {Promise} axios response promise
 */
export function gcMem(generations = 2) {
  return jsonrpcRequest('/v1/system', 'gc_mem', { generations })
}
