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

import Cookies from 'js-cookie'
import { defineStore } from 'pinia'

// localStorage key for the user-resizable sidebar width
const SIDEBAR_WIDTH_KEY = 'qcos-sidebar-width'
const SIDEBAR_WIDTH_DEFAULT = 245
const SIDEBAR_WIDTH_MIN = 200
const SIDEBAR_WIDTH_MAX = 480

function loadSidebarWidth() {
  try {
    const raw = typeof localStorage !== 'undefined'
      ? localStorage.getItem(SIDEBAR_WIDTH_KEY)
      : null
    const n = Number(raw)
    if (!raw || !Number.isFinite(n) || n <= 0) return SIDEBAR_WIDTH_DEFAULT
    return Math.min(SIDEBAR_WIDTH_MAX, Math.max(SIDEBAR_WIDTH_MIN, Math.round(n)))
  } catch {
    return SIDEBAR_WIDTH_DEFAULT
  }
}

function persistSidebarWidth(w) {
  try {
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem(SIDEBAR_WIDTH_KEY, String(w))
    }
  } catch {
    // ignore persistence failures (private mode, etc.)
  }
}

export const useAppStore = defineStore('app', {
  state: () => ({
    sidebar: {
      opened: Cookies.get('sidebarStatus')
        ? !!+Cookies.get('sidebarStatus')
        : true,
      withoutAnimation: false,
      // user-resizable sidebar width in px; only meaningful when opened
      width: loadSidebarWidth()
    },
    device: 'desktop'
  }),
  actions: {
    toggleSideBar() {
      this.sidebar.opened = !this.sidebar.opened
      this.sidebar.withoutAnimation = false
      if (this.sidebar.opened) {
        Cookies.set('sidebarStatus', 1)
      } else {
        Cookies.set('sidebarStatus', 0)
      }
    },
    closeSideBar(withoutAnimation) {
      Cookies.set('sidebarStatus', 0)
      this.sidebar.opened = false
      this.sidebar.withoutAnimation = withoutAnimation
    },
    toggleDevice(device) {
      this.device = device
    },
    setSidebarWidth(width) {
      const n = Number(width)
      if (!Number.isFinite(n)) return
      const clamped = Math.min(SIDEBAR_WIDTH_MAX, Math.max(SIDEBAR_WIDTH_MIN, Math.round(n)))
      this.sidebar.width = clamped
      persistSidebarWidth(clamped)
    }
  }
})
