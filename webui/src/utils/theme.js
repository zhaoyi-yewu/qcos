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

/**
 * Element Plus theme utilities.
 *
 * Two orthogonal knobs are provided:
 *
 *   1. color mode: light (default) vs dark. Implemented by toggling the
 *      `dark` class on <html>; element-plus ships `theme-chalk/dark/css-vars.css`
 *      which remaps all `--el-*` variables under `html.dark`.
 *   2. primary color: a small set of preset brand colors that override
 *      `--el-color-primary` and its derived variants. Works in both
 *      light and dark modes.
 */

export const COLOR_MODES = [
  { key: 'light', label: '白天' },
  { key: 'dark', label: '夜晚' }
]

export const THEME_PRESETS = [
  { key: 'default', label: '默认蓝', color: '#409EFF' },
  { key: 'green', label: '深绿', color: '#16a34a' },
  { key: 'violet', label: '紫罗兰', color: '#7c3aed' },
  { key: 'orange', label: '橙色', color: '#ea580c' },
  { key: 'red', label: '红色', color: '#dc2626' },
  { key: 'cyan', label: '青色', color: '#0891b2' }
]

export const DEFAULT_COLOR_MODE = 'light'
export const DEFAULT_THEME_KEY = 'default'

const MODE_STORAGE_KEY = 'qcos-color-mode'
const THEME_STORAGE_KEY = 'qcos-theme'

// ---------- persistence helpers ----------

function safeGet(key) {
  try {
    return window.localStorage.getItem(key)
  } catch (e) {
    return null
  }
}

function safeSet(key, value) {
  try {
    window.localStorage.setItem(key, value)
  } catch (e) {
    // ignore (e.g. privacy mode)
  }
}

export function getPersistedColorMode() {
  const saved = safeGet(MODE_STORAGE_KEY)
  return COLOR_MODES.some(m => m.key === saved) ? saved : DEFAULT_COLOR_MODE
}

export function persistColorMode(mode) {
  safeSet(MODE_STORAGE_KEY, mode)
}

export function getPersistedThemeKey() {
  const saved = safeGet(THEME_STORAGE_KEY)
  return THEME_PRESETS.some(p => p.key === saved) ? saved : DEFAULT_THEME_KEY
}

export function persistThemeKey(key) {
  safeSet(THEME_STORAGE_KEY, key)
}

// ---------- lookup helpers ----------

export function getThemePreset(key) {
  return THEME_PRESETS.find(p => p.key === key) ||
    THEME_PRESETS.find(p => p.key === DEFAULT_THEME_KEY)
}

// ---------- color mixing (used to derive light-N / dark-2 variants) ----------

function mix(hex, ratio, target) {
  const h = hex.replace('#', '')
  const r = parseInt(h.substring(0, 2), 16)
  const g = parseInt(h.substring(2, 4), 16)
  const b = parseInt(h.substring(4, 6), 16)
  const t = target === 'white' ? 255 : 0
  const mixChannel = (c) => Math.round(c + (t - c) * ratio)
    .toString(16)
    .padStart(2, '0')
  return `#${mixChannel(r)}${mixChannel(g)}${mixChannel(b)}`
}

// ---------- apply functions ----------

/**
 * Apply the color mode (light/dark) by toggling the `dark` class on <html>.
 * Element Plus's dark/css-vars.css remaps all `--el-*` variables under
 * `html.dark`, so the whole UI switches appearance at once.
 */
export function applyColorMode(mode) {
  const root = document.documentElement
  if (mode === 'dark') {
    root.classList.add('dark')
  } else {
    root.classList.remove('dark')
  }
  root.setAttribute('data-color-mode', mode)

  // Sidebar follows the color mode: light theme uses a soft light-grey
  // sidebar with dark text; dark theme keeps the legacy deep blue.
  // Only set these variables when the user has not chosen a custom
  // primary color preset — applyTheme() writes the same variables for
  // non-default themes and we don't want to stomp on that choice.
  const themeKey = getPersistedThemeKey()
  if (themeKey === DEFAULT_THEME_KEY) {
    if (mode === 'dark') {
      // dark mode → legacy deep blue sidebar
      root.style.setProperty('--qcos-menu-bg', '#001529')
      root.style.setProperty('--qcos-menu-hover', '#000c17')
      root.style.setProperty('--qcos-sub-menu-bg', '#000c17')
      root.style.setProperty('--qcos-sub-menu-hover', '#00060e')
      root.style.setProperty('--qcos-menu-text', '#bfcbd9')
      root.style.setProperty('--qcos-menu-active-text', '#409EFF')
      root.style.setProperty('--qcos-sub-menu-active-text', '#f4f4f5')
    } else {
      // light mode → soft light sidebar. The hover background must be
      // noticeably darker than the base (#f5f7fa) so the highlight is
      // visible; #e4e7ed was too close and appeared "white on white".
      root.style.setProperty('--qcos-menu-bg', '#f5f7fa')
      root.style.setProperty('--qcos-menu-hover', '#e9ecef')
      root.style.setProperty('--qcos-sub-menu-bg', '#f0f2f5')
      root.style.setProperty('--qcos-sub-menu-hover', '#dde0e6')
      root.style.setProperty('--qcos-menu-text', '#303133')
      root.style.setProperty('--qcos-menu-active-text', '#409EFF')
      root.style.setProperty('--qcos-sub-menu-active-text', '#303133')
    }
  }
}

/**
 * Apply the primary color preset. Sets `--el-color-primary` plus the
 * derived light-N / dark-2 variants on <html> so Element Plus components
 * pick up the new color in both light and dark modes.
 *
 * Also derives sidebar colors from the primary color so the left sidebar
 * follows the active theme: the sidebar background uses a darker shade of
 * the primary color, and the hover/submenu colors are derived from it.
 */
export function applyTheme(key) {
  const preset = getThemePreset(key)
  if (!preset) return
  const root = document.documentElement
  const primary = preset.color
  root.style.setProperty('--el-color-primary', primary)
  root.style.setProperty('--el-color-primary-dark-2', mix(primary, 0.2, 'black'))
  for (let i = 1; i <= 9; i++) {
    root.style.setProperty(
      `--el-color-primary-light-${i}`,
      mix(primary, i / 10, 'white')
    )
  }
  // sidebar follows the primary color for non-default presets; for the
  // default blue theme keep the legacy dark blue sidebar so the UI looks
  // the same as before the theme picker was introduced
  if (preset.key === DEFAULT_THEME_KEY) {
    // Clear sidebar color overrides; applyColorMode() will re-apply the
    // appropriate light/dark sidebar palette for the default theme.
    root.style.removeProperty('--qcos-menu-bg')
    root.style.removeProperty('--qcos-menu-hover')
    root.style.removeProperty('--qcos-sub-menu-bg')
    root.style.removeProperty('--qcos-sub-menu-hover')
    root.style.removeProperty('--qcos-menu-active-text')
    root.style.removeProperty('--qcos-menu-text')
    root.style.removeProperty('--qcos-sub-menu-active-text')
    // Re-apply color-mode-specific sidebar palette for the default theme
    applyColorMode(getPersistedColorMode())
  } else {
    // darker shades of the primary color keep the active menu item (which
    // uses primary directly) readable against the sidebar background
    root.style.setProperty('--qcos-menu-bg', mix(primary, 0.78, 'black'))
    root.style.setProperty('--qcos-menu-hover', mix(primary, 0.68, 'black'))
    root.style.setProperty('--qcos-sub-menu-bg', mix(primary, 0.84, 'black'))
    root.style.setProperty('--qcos-sub-menu-hover', mix(primary, 0.74, 'black'))
    root.style.setProperty('--qcos-menu-active-text', primary)
  }
  root.setAttribute('data-theme', preset.key)
}
