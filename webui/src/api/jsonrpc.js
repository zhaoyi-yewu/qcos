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
import config from '@/config'

/**
 * Send a JSON-RPC 2.0 request to the backend.
 *
 * @param {string} endpoint - API endpoint path (e.g. '/v1/device/get_device')
 * @param {string} method - JSON-RPC method name
 * @param {object} body - request body params
 * @returns {Promise} axios response promise
 */
export function jsonrpcRequest(endpoint, method, body = {}) {
  return request({
    url: `${config.backendBaseUrl}${endpoint}`,
    method: 'post',
    headers: {
      'Content-Type': 'application/json'
    },
    data: {
      jsonrpc: '2.0',
      id: 1,
      method: method,
      params: { body: body }
    }
  })
}

/**
 * Send a raw HTTP request (non-JSON-RPC) to the backend.
 *
 * @param {string} endpoint - full API path (e.g. '/qc/v1/auto_calibration')
 * @param {string} method - HTTP method ('get', 'post', etc.)
 * @param {object} [data] - request body for POST/PUT
 * @param {object} [params] - query params for GET
 * @returns {Promise} axios response promise
 */
export function httpRequest(endpoint, method, data = null, params = null) {
  const opts = {
    url: `${config.backendBaseUrl}${endpoint}`,
    method: method,
    headers: {
      'Content-Type': 'application/json'
    }
  }
  if (data !== null) {
    opts.data = data
  }
  if (params !== null) {
    opts.params = params
  }
  return request(opts)
}
