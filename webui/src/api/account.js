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
 * Query all projects.
 *
 * @returns {Promise} JSON-RPC response, result is a dict keyed by project id.
 */
export function getProjects(query = null) {
  return jsonrpcRequest('/v1/project', 'get_projects', {}, query)
}

/**
 * Get a single project by ID.
 *
 * @param {string} projectId - project id
 * @returns {Promise} JSON-RPC response
 */
export function getProject(projectId) {
  return jsonrpcRequest('/v1/project', 'get_project', {
    project_id: projectId
  })
}

/**
 * Create a new project.
 *
 * @param {object} data - project creation payload
 * @param {string} data.project_name - project name (required)
 * @param {string} [data.description] - project description
 * @returns {Promise} JSON-RPC response
 */
export function createProject(data) {
  return jsonrpcRequest('/v1/project', 'create_project', data)
}

/**
 * Update an existing project.
 *
 * @param {object} data - project update payload
 * @param {string} data.project_id - project id (required)
 * @param {string} [data.project_name] - project name
 * @param {string} [data.description] - project description
 * @returns {Promise} JSON-RPC response
 */
export function updateProject(data) {
  return jsonrpcRequest('/v1/project', 'update_project', data)
}

/**
 * Delete a project by ID.
 *
 * @param {string} projectId - project id
 * @returns {Promise} JSON-RPC response
 */
export function deleteProject(projectId) {
  return jsonrpcRequest('/v1/project', 'delete_project', {
    project_id: projectId
  })
}

/**
 * Query all roles.
 *
 * @returns {Promise} JSON-RPC response, result is a dict keyed by role id.
 */
export function getRoles(query = null) {
  return jsonrpcRequest('/v1/user', 'get_roles', {}, query)
}

/**
 * Get a single role by ID.
 *
 * @param {string} roleId - role id
 * @returns {Promise} JSON-RPC response
 */
export function getRole(roleId) {
  return jsonrpcRequest('/v1/user', 'get_role', {
    role_id: roleId
  })
}

/**
 * Create a new role.
 *
 * @param {object} data - role creation payload
 * @param {string} data.role_name - role name (required)
 * @param {string[]} [data.permissions] - role permissions
 * @param {string} [data.description] - role description
 * @returns {Promise} JSON-RPC response
 */
export function createRole(data) {
  return jsonrpcRequest('/v1/user', 'create_role', data)
}

/**
 * Update an existing role.
 *
 * @param {object} data - role update payload
 * @param {string} data.role_id - role id (required)
 * @param {string} [data.role_name] - role name
 * @param {string[]} [data.permissions] - role permissions
 * @param {string} [data.description] - role description
 * @returns {Promise} JSON-RPC response
 */
export function updateRole(data) {
  return jsonrpcRequest('/v1/user', 'update_role', data)
}

/**
 * Delete a role by ID.
 *
 * @param {string} roleId - role id
 * @returns {Promise} JSON-RPC response
 */
export function deleteRole(roleId) {
  return jsonrpcRequest('/v1/user', 'delete_role', {
    role_id: roleId
  })
}

/**
 * Query all users.
 *
 * @returns {Promise} JSON-RPC response, result is a dict keyed by user id.
 */
export function getUsers(query = null) {
  return jsonrpcRequest('/v1/user', 'get_users', {}, query)
}

/**
 * Get a single user by ID.
 *
 * @param {string} userId - user id
 * @returns {Promise} JSON-RPC response
 */
export function getUser(userId) {
  return jsonrpcRequest('/v1/user', 'get_user', {
    user_id: userId
  })
}

/**
 * Create a new user.
 *
 * @param {object} data - user creation payload
 * @param {string} [data.project_id] - project ID (optional)
 * @param {string} data.user_name - user name (required)
 * @param {string} data.password - password (required)
 * @param {string[]} [data.roles] - user roles
 * @param {number} [data.password_expiry_days] - password expiry days
 * @param {boolean} [data.is_enabled] - whether user is enabled
 * @param {boolean} [data.is_locked] - whether user is locked
 * @param {string} [data.description] - user description
 * @returns {Promise} JSON-RPC response
 */
export function createUser(data) {
  return jsonrpcRequest('/v1/user', 'create_user', data)
}

/**
 * Update an existing user.
 *
 * @param {object} data - user update payload
 * @param {string} data.user_id - user id (required)
 * @param {string[]} [data.roles] - user roles
 * @param {string} [data.description] - user description
 * @param {boolean} [data.is_enabled] - whether user is enabled
 * @param {boolean} [data.is_locked] - whether user is locked
 * @param {number} [data.password_expiry_days] - password expiry days
 * @returns {Promise} JSON-RPC response
 */
export function updateUser(data) {
  return jsonrpcRequest('/v1/user', 'update_user', data)
}

/**
 * Delete a user by ID.
 *
 * @param {string} userId - user id
 * @param {boolean} [force] - force delete even if user has resources
 * @returns {Promise} JSON-RPC response
 */
export function deleteUser(userId, force = false) {
  return jsonrpcRequest('/v1/user', 'delete_user', {
    user_id: userId,
    force: force
  })
}

/**
 * Change a user's password.
 *
 * Admins can change any user's password without old_password;
 * non-admin users must supply old_password to change their own.
 *
 * @param {object} data - password change payload
 * @param {string} data.user_id - user id (required)
 * @param {string} data.new_password - new password (required)
 * @param {string} [data.old_password] - old password (required for non-admin)
 * @returns {Promise} JSON-RPC response
 */
export function changePassword(data) {
  return jsonrpcRequest('/v1/user', 'change_password', data)
}

/**
 * Query all login logs.
 *
 * @returns {Promise} JSON-RPC response, result is an array of login log records.
 */
export function getLoginLogs(query = null) {
  return jsonrpcRequest('/v1/user', 'get_login_logs', {}, query)
}

/**
 * Clear login logs (all or for a specific user).
 *
 * @param {object} [data] - optional filter
 * @param {string} [data.user_id] - clear logs for this user ID (UUID)
 * @param {string} [data.user_name] - clear logs for this user name
 *   (user_id and user_name are mutually exclusive; omit both to clear all)
 * @returns {Promise} JSON-RPC response, result.count is the number cleared
 */
export function clearLoginLogs(data = {}) {
  return jsonrpcRequest('/v1/user', 'clear_login_logs', data)
}
