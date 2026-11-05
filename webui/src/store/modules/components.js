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
import { queryVersion } from '@/api/version'

/**
 * Component switch status store.
 *
 * Loads the `components` field from the `/version` API once at app startup
 * and exposes reactive getters so UI elements can hide/disable features
 * that are turned off on the backend.
 */
export const useComponentsStore = defineStore('components', {
  state: () => ({
    // Raw component switch map from the backend
    // e.g. { ai_agent: true, ai_mcp_server: false, terminal: true, ... }
    switches: {},
    // Whether the initial load has completed (success or failure)
    loaded: false,
    // Loading error message, if any
    loadError: ''
  }),

  getters: {
    /**
     * Check if a component is enabled.
     * Returns true when the switch is missing (fail-open for unknown
     * components so we don't accidentally hide core UI).
     *
     * @param {string} name - component key from the backend
     * @returns {boolean}
     */
    isEnabled: (state) => (name) => {
      if (!state.loaded) return true
      const val = state.switches[name]
      return val === undefined ? true : !!val
    },

    aiAgentEnabled() {
      return this.isEnabled('ai_agent')
    },
    aiMcpServerEnabled() {
      return this.isEnabled('ai_mcp_server')
    },
    terminalEnabled() {
      return this.isEnabled('terminal')
    },
    metricsServerEnabled() {
      return this.isEnabled('metrics_server')
    },
    proxyPrometheusEnabled() {
      return this.isEnabled('proxy_prometheus')
    },
    proxyAlertmanagerEnabled() {
      return this.isEnabled('proxy_alertmanager')
    },
    proxyVictorialogsEnabled() {
      return this.isEnabled('proxy_victorialogs')
    },
    embeddingEnabled() {
      return this.isEnabled('embedding')
    },
    /**
     * Whether the backend vision model is configured. Drives the
     * image-attachment button on the AI agent chat toolbar - when
     * false, the button is disabled with a tooltip explaining that
     * the backend has no image-analysis capability.
     */
    visionEnabled() {
      return this.isEnabled('vision')
    }
  },

  actions: {
    /**
     * Fetch component switches from the version API.
     * Safe to call multiple times; subsequent calls are no-ops once loaded.
     */
    async load() {
      if (this.loaded) return
      try {
        const resp = await queryVersion()
        const result = resp && resp.result ? resp.result : resp
        // The backend wraps ai-related switches under `components.ai`
        // and proxy-related switches under `components.proxy`, while
        // the getters below do flat lookups via `isEnabled('<name>')`.
        // Flatten the two nested groups into the top level so
        // `isEnabled('embedding')` / `isEnabled('prometheus')` etc.
        // resolve correctly.
        const raw = result.components || {}
        const flat = { ...raw }
        for (const group of ['ai', 'proxy']) {
          if (raw[group] && typeof raw[group] === 'object') {
            Object.assign(flat, raw[group])
            delete flat[group]
          }
        }
        this.switches = flat
        this.loaded = true
        this.loadError = ''
      } catch (err) {
        // On failure leave switches empty and mark as loaded so the UI
        // does not spin forever. All getters default to true (fail-open).
        this.switches = {}
        this.loaded = true
        this.loadError = (err && err.message) || 'failed to load component switches'
      }
    }
  }
})
