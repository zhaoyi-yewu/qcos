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
 * Query all flavors (resource specifications).
 *
 * @returns {Promise} JSON-RPC response, result is a list of flavor objects.
 */
export function getFlavors(query = null) {
  return jsonrpcRequest('/v1/flavor', 'get_flavors', {}, query)
}

/**
 * Create a new flavor (resource specification).
 *
 * @param {object} data - flavor creation payload
 * @param {string} data.name - flavor name (required)
 * @param {string} [data.description] - flavor description
 * @param {boolean} [data.is_public] - whether the flavor is public
 * @param {number} [data.min_qubits] - minimum qubits
 * @param {number} [data.max_qubits] - maximum qubits
 * @param {number} [data.gate_fidelity_1q_min] - min single-qubit gate fidelity
 * @param {number} [data.gate_fidelity_2q_min] - min two-qubit gate fidelity
 * @param {string[]} [data.device_groups] - device group IDs
 * @param {string} [data.project_id] - project ID
 * @param {object} [data.extra_properties] - extra properties
 * @returns {Promise} JSON-RPC response
 */
export function createFlavor(data) {
  return jsonrpcRequest('/v1/flavor', 'create_flavor', data)
}

/**
 * Get a flavor (resource specification) by ID.
 *
 * @param {string} flavorId - flavor id
 * @returns {Promise} JSON-RPC response
 */
export function getFlavor(flavorId) {
  return jsonrpcRequest('/v1/flavor', 'get_flavor', {
    flavor_id: flavorId
  })
}

/**
 * Update an existing flavor (resource specification).
 *
 * @param {object} data - flavor update payload
 * @param {string} data.flavor_id - flavor id (required)
 * @param {string} [data.name] - flavor name
 * @param {string} [data.description] - description
 * @param {boolean} [data.is_public] - whether the flavor is public
 * @param {number} [data.min_qubits] - minimum qubits
 * @param {number} [data.max_qubits] - maximum qubits
 * @param {number} [data.gate_fidelity_1q_min] - min single-qubit gate fidelity
 * @param {number} [data.gate_fidelity_2q_min] - min two-qubit gate fidelity
 * @param {object} [data.extra_properties] - extra properties to merge
 * @param {string[]} [data.device_groups] - device group IDs
 * @param {string} [data.project_id] - project ID
 * @returns {Promise} JSON-RPC response
 */
export function updateFlavor(data) {
  return jsonrpcRequest('/v1/flavor', 'update_flavor', data)
}

/**
 * Delete flavors in batch.
 *
 * @param {string[]} flavorIds - list of flavor ids to delete
 * @returns {Promise} JSON-RPC response
 */
export function deleteFlavors(flavorIds) {
  return jsonrpcRequest('/v1/flavor', 'delete_flavors', {
    flavor_ids: flavorIds
  })
}
