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

import defaultSettings from '@/settings'
import { defineStore } from 'pinia'
import {
  DEFAULT_COLOR_MODE,
  DEFAULT_THEME_KEY,
  applyColorMode,
  applyTheme,
  getPersistedColorMode,
  getPersistedThemeKey,
  persistColorMode,
  persistThemeKey
} from '@/utils/theme'

const { showSettings, fixedHeader, sidebarLogo } = defaultSettings

export const useSettingsStore = defineStore('settings', {
  state: () => ({
    showSettings: showSettings,
    fixedHeader: fixedHeader,
    sidebarLogo: sidebarLogo,
    // color mode: 'light' or 'dark'; controls the html.dark class which
    // remaps all element-plus CSS variables via theme-chalk/dark/css-vars.css
    colorMode: DEFAULT_COLOR_MODE,
    // primary color preset key; see utils/theme.js for the preset list
    theme: DEFAULT_THEME_KEY
  }),
  actions: {
    changeSetting({ key, value }) {
      // eslint-disable-next-line no-prototype-builtins
      if (this.hasOwnProperty(key)) {
        this[key] = value
      }
    },

    // initialize color mode and primary theme from localStorage; called
    // once at app startup so the user's previous choice is restored
    // before the UI is painted (avoids a flash of the default theme)
    initTheme() {
      const mode = getPersistedColorMode()
      const key = getPersistedThemeKey()
      this.colorMode = mode
      this.theme = key
      applyColorMode(mode)
      applyTheme(key)
    },

    // switch color mode (light <-> dark)
    setColorMode(mode) {
      if (this.colorMode === mode) return
      this.colorMode = mode
      persistColorMode(mode)
      applyColorMode(mode)
    },

    // convenience toggle used by the theme picker switch
    toggleColorMode() {
      this.setColorMode(this.colorMode === 'dark' ? 'light' : 'dark')
    },

    // switch primary color preset
    setTheme(key) {
      if (this.theme === key) return
      this.theme = key
      persistThemeKey(key)
      applyTheme(key)
    }
  }
})
