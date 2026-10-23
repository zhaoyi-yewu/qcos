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

const LS_KEY = 'qcos_tokens'
const SESSION_TTL_MS = 30 * 24 * 3600 * 1000 // 30 days

/**
 * Load all endpoint sessions from localStorage.
 * Expired sessions (savedAt older than SESSION_TTL_MS) are lazily removed.
 *
 * @returns {Object} map of endpoint name -> session object
 */
export function loadAllSessions() {
  try {
    const all = JSON.parse(localStorage.getItem(LS_KEY) || '{}')
    const now = Date.now()
    let dirty = false
    for (const k of Object.keys(all)) {
      if (all[k] && all[k].savedAt && now - all[k].savedAt > SESSION_TTL_MS) {
        delete all[k]
        dirty = true
      }
    }
    if (dirty) {
      localStorage.setItem(LS_KEY, JSON.stringify(all))
    }
    return all
  } catch {
    return {}
  }
}

/**
 * Get the session for a specific endpoint.
 *
 * @param {string} name - endpoint name
 * @returns {Object|null} session object or null
 */
export function getSession(name) {
  if (!name) return null
  return loadAllSessions()[name] || null
}

/**
 * Save (merge) a session for a specific endpoint.
 *
 * @param {string} name - endpoint name
 * @param {Object} session - session fields to persist
 */
export function saveSession(name, session) {
  const all = loadAllSessions()
  all[name] = { ...(all[name] || {}), ...session, savedAt: Date.now() }
  localStorage.setItem(LS_KEY, JSON.stringify(all))
}

/**
 * Remove the session for a specific endpoint.
 *
 * @param {string} name - endpoint name
 */
export function removeSession(name) {
  const all = loadAllSessions()
  delete all[name]
  localStorage.setItem(LS_KEY, JSON.stringify(all))
}

/**
 * Remove all endpoint sessions.
 */
export function clearAllSessions() {
  localStorage.removeItem(LS_KEY)
}
