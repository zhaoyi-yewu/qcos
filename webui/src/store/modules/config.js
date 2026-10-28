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

import { defineStore } from 'pinia'
import { getActiveEndpoint, setActiveEndpoint } from '@/utils/auth'

export const useConfigStore = defineStore('config', {
  state: () => ({
    debug: false,
    defaultEndpoint: '',
    endpointProbeTimeoutMs: 3000,
    endpoints: [], // [{name, alias, url}]
    activeEndpointName: '',
    // endpoint health status: { <name>: {status, version, apiVersion, authMode, error, probedAt} }
    healthMap: {}
  }),

  getters: {
    activeEndpoint(state) {
      return state.endpoints.find(e => e.name === state.activeEndpointName) || null
    },
    endpointHealth: (state) => (name) => state.healthMap[name] || null,
    isEndpointUsable: (state) => (name) => {
      const h = state.healthMap[name]
      return !!(h && h.status === 'ok')
    }
  },

  actions: {
    /**
     * Load runtime config from /webui-config.json.
     * Must be called once at app startup before any API request.
     */
    async load() {
      const r = await fetch('/webui-config.json', { cache: 'no-store' })
      const data = await r.json()
      this.debug = !!data.debug
      this.defaultEndpoint = data.defaultEndpoint || ''
      this.endpointProbeTimeoutMs = data.endpointProbeTimeoutMs || 3000
      this.endpoints = data.endpoints || []
      const cookieName = getActiveEndpoint()
      const fallback = this.defaultEndpoint ||
        (this.endpoints[0] && this.endpoints[0].name) || ''
      this.activeEndpointName =
        this.endpoints.some(e => e.name === cookieName) ? cookieName : fallback
    },

    /**
     * Switch the active endpoint.
     * Only allows names present in the configured endpoints list.
     *
     * @param {string} name - endpoint name
     */
    setActive(name) {
      if (!this.endpoints.some(e => e.name === name)) return
      this.activeEndpointName = name
      setActiveEndpoint(name)
    },

    /**
     * Probe a single endpoint's /version API and update healthMap.
     *
     * @param {string} name - endpoint name
     * @returns {Object|null} the health entry after probing
     */
    async probeEndpoint(name) {
      const ep = this.endpoints.find(e => e.name === name)
      if (!ep) return null
      // Throttle: skip if probed within the last 30 seconds
      const existing = this.healthMap[name]
      if (existing && existing.probedAt && (Date.now() - existing.probedAt) < 30000) {
        return existing
      }
      this.healthMap[name] = { ...(existing || {}), status: 'probing' }
      const ctrl = new AbortController()
      const timer = setTimeout(() => ctrl.abort(), this.endpointProbeTimeoutMs)
      try {
        const resp = await fetch(`${ep.url}/version`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            jsonrpc: '2.0',
            id: 1,
            method: 'version',
            params: { body: { details: false }}
          }),
          signal: ctrl.signal
        })
        const data = await resp.json()
        if (data && data.result && data.result.version) {
          this.healthMap[name] = {
            status: 'ok',
            version: data.result.version,
            platformVersion: data.result.platform_version || '',
            apiVersion: data.result.api_version || '',
            authMode: data.result.auth_mode || '',
            probedAt: Date.now()
          }
        } else {
          this.healthMap[name] = {
            status: 'fail',
            error: (data && data.error && data.error.message) || 'invalid response',
            probedAt: Date.now()
          }
        }
      } catch (err) {
        this.healthMap[name] = {
          status: 'fail',
          error: err && err.name === 'AbortError' ? 'timeout' : (err.message || 'network error'),
          probedAt: Date.now()
        }
      } finally {
        clearTimeout(timer)
      }
      return this.healthMap[name]
    },

    /**
     * Probe all configured endpoints concurrently.
     * Called at app startup and when the login/sidebar pages mount.
     */
    async probeAll() {
      await Promise.allSettled(this.endpoints.map(e => this.probeEndpoint(e.name)))
    }
  }
})
