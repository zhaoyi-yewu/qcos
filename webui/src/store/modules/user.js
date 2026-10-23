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

import { login, logout, getInfo } from '@/api/user'
import { queryVersion } from '@/api/version'
import { getSession, saveSession, removeSession } from '@/utils/session'
import { resetRouter } from '@/router'
import { defineStore } from 'pinia'
import { useConfigStore } from '@/store/modules/config'

export const useUserStore = defineStore('user', {
  state: () => ({
    token: '',
    name: '',
    userId: '',
    avatar: '',
    roles: [],
    authMode: ''
  }),
  getters: {
    // true when the user has the `admin` role; used by sidebar to filter
    // admin-only menu items (IAM, system monitoring, worker list)
    isAdmin: (state) => {
      const roles = state.roles
      if (!roles) return false
      if (Array.isArray(roles)) return roles.includes('admin')
      if (typeof roles === 'object') return 'admin' in roles
      return roles === 'admin'
    }
  },
  actions: {
    // check auth mode from version API
    checkAuthMode() {
      return queryVersion()
        .then(response => {
          const result = response.result
          this.authMode = result.auth_mode || 'jwt'
          return this.authMode
        })
        .catch(() => {
          this.authMode = 'jwt'
          return 'jwt'
        })
    },

    // no-auth login: skip credential validation
    noAuthLogin() {
      const cfg = useConfigStore()
      return new Promise(resolve => {
        this.token = 'no-auth'
        this.name = 'anonymous'
        this.roles = ['admin']
        saveSession(cfg.activeEndpointName, {
          token: 'no-auth',
          name: 'anonymous',
          authMode: 'no',
          roles: ['admin']
        })
        resolve()
      })
    },

    // user login (jwt mode)
    login(userInfo) {
      const { username, password } = userInfo
      const cfg = useConfigStore()
      return new Promise((resolve, reject) => {
        login({ username: username.trim(), password: password })
          .then(response => {
            const result = response.result
            this.token = result.access_token
            this.name = username.trim()
            saveSession(cfg.activeEndpointName, {
              token: this.token,
              name: this.name,
              authMode: 'jwt'
            })
            resolve()
          })
          .catch(error => {
            reject(error)
          })
      })
    },

    /**
     * Restore the session for the currently active endpoint from
     * localStorage. Called at app startup and after endpoint switches.
     *
     * @returns {boolean} true when a valid session was restored
     */
    loadSessionForActiveEndpoint() {
      const cfg = useConfigStore()
      const sess = getSession(cfg.activeEndpointName)
      if (sess && sess.token) {
        this.token = sess.token
        this.name = sess.name || ''
        this.userId = sess.userId || ''
        this.roles = sess.roles || []
        this.authMode = sess.authMode || ''
        this.avatar = sess.avatar || ''
        return true
      }
      this._clearAuthState({ keepSessions: true })
      return false
    },

    // get user info
    getInfo() {
      return new Promise((resolve, reject) => {
        getInfo()
          .then(response => {
            const result = response.result

            if (!result) {
              return reject('Verification failed, please Login again.')
            }

            this.name = result.user_name
            this.avatar = '/src/assets/avatar/default_avatar.png'
            // persist roles so sidebar can filter admin-only menu items
            this.roles = result.roles || []
            // persist user id so non-admin users can clear only their own logs
            this.userId = result.id || ''
            resolve(result)
          })
          .catch(error => {
            reject(error)
          })
      })
    },

    // user logout
    logout() {
      const cfg = useConfigStore()
      return new Promise(resolve => {
        logout()
          .catch(() => {
            // ignore API errors during logout, still clear local state
          })
          .finally(() => {
            // clear only the current endpoint's session; other endpoints
            // keep their saved tokens so the user can switch back later
            removeSession(cfg.activeEndpointName)
            this._clearAuthState({ keepSessions: true })
            resolve()
          })
      })
    },

    // internal helper: clear every piece of user-specific state, including
    // in-memory fields and any leftover browser storage entries that may
    // carry over from previous sessions
    _clearAuthState(options = {}) {
      const { keepSessions = false } = options
      // 1. reset dynamic routes added by permission system
      resetRouter()
      // 2. clear pinia state
      this.token = ''
      this.name = ''
      this.userId = ''
      this.avatar = ''
      this.roles = []
      this.authMode = ''
      // 3. clear potentially sensitive localStorage entries (last picked
      // file paths, cached form state, etc.); failures are ignored since
      // storage may be disabled in private browsing
      if (!keepSessions) {
        try {
          const keysToRemove = []
          for (let i = 0; i < localStorage.length; i++) {
            const k = localStorage.key(i)
            // drop app-specific keys but preserve unrelated ones
            if (k && (k.startsWith('qasm.') || k.startsWith('qubo.') || k.startsWith('qcos.'))) {
              keysToRemove.push(k)
            }
          }
          keysToRemove.forEach(k => localStorage.removeItem(k))
        } catch (e) { /* ignore */ }
      }
      // 4. clear sessionStorage completely (it is per-tab and should not
      // survive a logout)
      try {
        sessionStorage.clear()
      } catch (e) { /* ignore */ }
    },

    // remove token
    resetToken() {
      return new Promise(resolve => {
        this._clearAuthState()
        resolve()
      })
    }
  }
})
