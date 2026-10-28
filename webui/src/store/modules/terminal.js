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

const DEFAULT_WIDTH = 900
const DEFAULT_HEIGHT = 560

// max concurrent shell sessions per user (matches backend MAX_SESSIONS_PER_USER)
export const MAX_SESSIONS = 4

// localStorage key used to persist the terminal theme across reloads
const THEME_STORAGE_KEY = 'qcos-terminal-theme'

// built-in terminal themes. each entry maps directly onto xterm's ITheme.
export const TERMINAL_THEMES = [
  {
    name: 'dark',
    label: '暗色',
    icon: 'Moon',
    theme: {
      background: '#1e1e1e',
      foreground: '#d4d4d4'
    }
  },
  {
    name: 'light',
    label: '亮色',
    icon: 'Sunny',
    theme: {
      background: '#ffffff',
      foreground: '#1e1e1e'
    }
  },
  {
    name: 'solarized-dark',
    label: 'Solarized Dark',
    icon: 'Monitor',
    theme: {
      background: '#002b36',
      foreground: '#839496'
    }
  }
]

const DEFAULT_THEME_NAME = TERMINAL_THEMES[0].name

function loadPersistedTheme() {
  try {
    const raw = typeof localStorage !== 'undefined'
      ? localStorage.getItem(THEME_STORAGE_KEY)
      : null
    if (!raw) return DEFAULT_THEME_NAME
    return TERMINAL_THEMES.some(t => t.name === raw) ? raw : DEFAULT_THEME_NAME
  } catch (e) {
    return DEFAULT_THEME_NAME
  }
}

function persistTheme(name) {
  try {
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem(THEME_STORAGE_KEY, name)
    }
  } catch (e) {
    // ignore persistence failures (private mode, etc.)
  }
}

let sessionSeq = 0

function nextSessionId() {
  sessionSeq += 1
  return `term-${Date.now()}-${sessionSeq}`
}

let titleSeq = 0

function nextTitle() {
  titleSeq += 1
  return `Terminal ${titleSeq}`
}

export const useTerminalStore = defineStore('terminal', {
  state: () => ({
    visible: false,
    minimized: false,
    fullscreen: false,
    // null means "not yet positioned"; the dialog will be centered on
    // first open. Once the user drags the dialog, position becomes a
    // concrete {x, y} and is kept across open/close.
    position: null,
    positionInitialized: false,
    size: { width: DEFAULT_WIDTH, height: DEFAULT_HEIGHT },
    // multi-session state
    sessions: [],
    activeSessionId: '',
    // global terminal theme (shared across sessions)
    theme: loadPersistedTheme(),
    currentPath: '',
    // set to true after any session has produced output and not yet
    // been exited; used by TerminalDialog to confirm before close
    hasForegroundOutput: false
  }),

  getters: {
    isOpen(state) {
      return state.visible && !state.minimized
    },
    activeSession(state) {
      return state.sessions.find(s => s.id === state.activeSessionId) || null
    },
    sessionCount(state) {
      return state.sessions.length
    },
    canAddSession(state) {
      return state.sessions.length < MAX_SESSIONS
    },
    currentTheme(state) {
      return TERMINAL_THEMES.find(t => t.name === state.theme) || TERMINAL_THEMES[0]
    },
    // any session still connected; used by dialog close confirm
    anyConnected(state) {
      return state.sessions.some(s => s.connected)
    }
  },

  actions: {
    openDialog() {
      // center the dialog on first open (position not initialized yet)
      if (!this.positionInitialized || !this.position) {
        const w = this.size.width || DEFAULT_WIDTH
        const h = this.size.height || DEFAULT_HEIGHT
        const vw = typeof window !== 'undefined' ? window.innerWidth : w
        const vh = typeof window !== 'undefined' ? window.innerHeight : h
        this.position = {
          x: Math.max(0, Math.round((vw - w) / 2)),
          y: Math.max(0, Math.round((vh - h) / 2))
        }
        this.positionInitialized = true
      }
      this.visible = true
      this.minimized = false
      // always make sure at least one session exists when opening
      if (this.sessions.length === 0) {
        this.addSession()
      }
    },
    closeDialog() {
      this.visible = false
      this.minimized = false
      this.fullscreen = false
      this.sessions = []
      this.activeSessionId = ''
      this.hasForegroundOutput = false
      // reset the title counter so a reopened dialog starts from
      // "Terminal 1" again instead of continuing the previous sequence
      titleSeq = 0
    },
    toggleMinimize() {
      this.minimized = !this.minimized
    },
    toggleFullscreen() {
      this.fullscreen = !this.fullscreen
    },
    setPosition(pos) {
      if (!pos) return
      this.position = {
        x: Number(pos.x) || 0,
        y: Number(pos.y) || 0
      }
      this.positionInitialized = true
    },
    setSize(size) {
      if (!size) return
      this.size = {
        width: Math.max(360, Number(size.width) || DEFAULT_WIDTH),
        height: Math.max(240, Number(size.height) || DEFAULT_HEIGHT)
      }
    },
    setPath(path) {
      this.currentPath = path || ''
    },
    setHasForegroundOutput(v) {
      this.hasForegroundOutput = !!v
    },

    // ---------- multi-session ----------
    addSession() {
      if (this.sessions.length >= MAX_SESSIONS) {
        return null
      }
      const id = nextSessionId()
      const session = {
        id,
        title: nextTitle(),
        sessionId: '', // backend session id once auth_ok arrives
        connected: false
      }
      this.sessions.push(session)
      this.activeSessionId = id
      return session
    },
    removeSession(id) {
      const idx = this.sessions.findIndex(s => s.id === id)
      if (idx === -1) return
      this.sessions.splice(idx, 1)
      if (this.activeSessionId === id) {
        const next = this.sessions[idx] || this.sessions[idx - 1] || null
        this.activeSessionId = next ? next.id : ''
      }
      // close the dialog when the last tab is closed
      if (this.sessions.length === 0) {
        this.closeDialog()
      }
    },
    setActiveSession(id) {
      if (this.sessions.some(s => s.id === id)) {
        this.activeSessionId = id
      }
    },
    updateSession(id, patch) {
      const s = this.sessions.find(item => item.id === id)
      if (!s) return
      if (patch.sessionId !== undefined) s.sessionId = patch.sessionId || ''
      if (patch.connected !== undefined) s.connected = !!patch.connected
      if (patch.title !== undefined) s.title = patch.title || s.title
    },

    // ---------- theme ----------
    setTheme(name) {
      if (!TERMINAL_THEMES.some(t => t.name === name)) return
      this.theme = name
      persistTheme(name)
    },
    cycleTheme() {
      const idx = TERMINAL_THEMES.findIndex(t => t.name === this.theme)
      const next = TERMINAL_THEMES[(idx + 1) % TERMINAL_THEMES.length]
      this.setTheme(next.name)
    }
  }
})
