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

export function getDevices(query = null) {
  return jsonrpcRequest('/v1/device', 'get_devices', {
    details: true
  }, query)
}

export function getDevice(deviceName) {
  return jsonrpcRequest('/v1/device', 'get_device', {
    name: deviceName,
    details: true
  })
}

/**
 * Set device attributes (state, enable, max_qubits, available_qubits).
 *
 * Each field is optional; pass only the fields to be changed.
 *
 * @param {object} data - update payload
 * @param {string} data.device_name - device name (required)
 * @param {string} [data.state] - one of: auto, online, offline, busy,
 *   disconnected, calibrating, maintain, unknown
 * @param {boolean} [data.enable] - enable or disable the device
 * @param {string} [data.max_qubits] - 'auto' or positive integer string
 * @param {string} [data.available_qubits] - 'auto' or positive integer string
 * @returns {Promise} JSON-RPC response
 */
export function setDevice(data) {
  return jsonrpcRequest('/v1/device', 'set_device', data)
}

/**
 * Query all device groups.
 *
 * @returns {Promise} JSON-RPC response, result is a list of device group objects.
 */
export function getDeviceGroups(query = null) {
  return jsonrpcRequest('/v1/device_group', 'get_device_groups', {}, query)
}

/**
 * Get a device group by ID.
 *
 * @param {string} groupId - device group id
 * @returns {Promise} JSON-RPC response
 */
export function getDeviceGroup(groupId) {
  return jsonrpcRequest('/v1/device_group', 'get_device_group', {
    group_id: groupId
  })
}

/**
 * Create a new device group.
 *
 * @param {object} data - device group creation payload
 * @param {string} data.name - device group name (required)
 * @param {string} [data.project_id] - project ID (optional)
 * @param {string} [data.description] - description
 * @param {string[]} data.device_names - list of device names (required)
 * @param {boolean} [data.is_public] - whether the group is public
 * @returns {Promise} JSON-RPC response
 */
export function createDeviceGroup(data) {
  return jsonrpcRequest('/v1/device_group', 'create_device_group', data)
}

/**
 * Update an existing device group.
 *
 * @param {object} data - device group update payload
 * @param {string} data.group_id - device group id (required)
 * @param {string} [data.name] - device group name
 * @param {string} [data.description] - description
 * @param {string[]} [data.device_names] - list of device names
 * @param {boolean} [data.is_public] - whether the group is public
 * @param {string} [data.project_id] - project ID
 * @returns {Promise} JSON-RPC response
 */
export function updateDeviceGroup(data) {
  return jsonrpcRequest('/v1/device_group', 'update_device_group', data)
}

/**
 * Delete device groups in batch.
 *
 * @param {string[]} groupIds - list of device group ids to delete
 * @returns {Promise} JSON-RPC response
 */
export function deleteDeviceGroups(groupIds) {
  return jsonrpcRequest('/v1/device_group', 'delete_device_groups', {
    group_ids: groupIds
  })
}

/**
 * Query all worker processes.
 *
 * @returns {Promise} JSON-RPC response, result.workers is a list of worker objects.
 */
export function getWorkers(query = null) {
  return jsonrpcRequest('/v1/system', 'list_workers', {}, query)
}

/**
 * Restart a specific Prefect worker.
 *
 * @param {string} workerName Worker name to restart.
 * @returns {Promise} JSON-RPC response with restart result.
 */
export function restartWorker(workerName) {
  return jsonrpcRequest('/v1/system', 'restart_worker', { worker_name: workerName })
}
