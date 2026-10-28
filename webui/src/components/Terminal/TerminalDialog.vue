<!--
  Copyright© 2024-2026 China Mobile (SuZhou) Software Technology Co.,Ltd.

  qcos is licensed under Mulan PSL v2.
  You can use this software according to the terms and conditions
  of the Mulan PSL v2.
  You may obtain a copy of Mulan PSL v2 at:
          http://license.coscl.org.cn/MulanPSL2
  THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS,
      WITHOUT WARRANTIES OF ANY KIND,
  EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
  MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
  See the Mulan PSL v2 for more details.
-->

<template>
  <teleport to="body">
    <!-- minimized pill, docked at the bottom-right corner -->
    <div
      v-if="visible && minimized"
      class="terminal-minimized-pill"
      @click="restoreFromMinimize"
    >
      <el-icon><Monitor /></el-icon>
      <span class="pill-text">终端</span>
      <span v-if="anyConnected" class="pill-dot pill-dot-on" />
      <span v-else class="pill-dot" />
    </div>

    <!-- floating dialog -->
    <div
      v-if="visible && !minimized"
      ref="dialogRef"
      class="terminal-dialog"
      :class="{ 'is-fullscreen': fullscreen }"
      :style="dialogStyle"
    >
      <div
        class="terminal-dialog-header"
        @mousedown="onHeaderMouseDown"
        @dblclick="onHeaderDblClick"
      >
        <div class="terminal-dialog-title">
          <el-icon><Monitor /></el-icon>
          <span>QCOS 终端</span>
          <span v-if="activeBackendSessionId" class="terminal-dialog-session">[{{ activeBackendSessionId.slice(0, 8) }}]</span>
        </div>
        <div class="terminal-dialog-controls">
          <el-tooltip :content="themeTooltip" placement="bottom">
            <el-icon class="ctrl-icon" @click.stop="cycleTheme"><component :is="themeIcon" /></el-icon>
          </el-tooltip>
          <el-tooltip :content="showFilePanel ? '隐藏文件面板' : '显示文件面板'" placement="bottom">
            <el-icon class="ctrl-icon" @click.stop="toggleFilePanel"><FolderOpened v-if="showFilePanel" /><Folder v-else /></el-icon>
          </el-tooltip>
          <el-tooltip :content="fullscreen ? '还原' : '全屏'" placement="bottom">
            <el-icon class="ctrl-icon" @click.stop="toggleFullscreen"><Aim v-if="fullscreen" /><FullScreen v-else /></el-icon>
          </el-tooltip>
          <el-tooltip content="最小化" placement="bottom">
            <el-icon class="ctrl-icon" @click.stop="minimize"><Minus /></el-icon>
          </el-tooltip>
          <el-tooltip content="关闭" placement="bottom">
            <el-icon class="ctrl-icon ctrl-close" @click.stop="onClose"><Close /></el-icon>
          </el-tooltip>
        </div>
      </div>

      <!-- tab bar -->
      <div class="terminal-tab-bar">
        <div
          v-for="s in sessions"
          :key="s.id"
          class="terminal-tab"
          :class="{ 'is-active': s.id === activeSessionId }"
          @click="setActiveSession(s.id)"
        >
          <span v-if="s.connected" class="tab-dot tab-dot-on" />
          <span v-else class="tab-dot tab-dot-off" />
          <span class="tab-title">{{ s.title }}</span>
          <el-icon class="tab-close" @click.stop="closeTab(s)"><Close /></el-icon>
        </div>
        <el-tooltip :content="addTabTooltip" placement="bottom" :disabled="canAddSession">
          <span class="tab-add-wrapper">
            <el-icon
              class="tab-add"
              :class="{ 'is-disabled': !canAddSession }"
              @click.stop="onAddTab"
            ><Plus /></el-icon>
          </span>
        </el-tooltip>
      </div>

      <div class="terminal-dialog-body">
        <div class="terminal-pane" :style="terminalPaneStyle">
          <TerminalSession
            v-for="s in sessions"
            v-show="s.id === activeSessionId"
            :key="s.id"
            :ref="el => setSessionRef(s.id, el)"
            :session-id="s.id"
            :active="s.id === activeSessionId"
            @session-open="onSessionOpen(s.id, $event)"
            @session-close="onSessionClose(s.id)"
          />
        </div>
        <div v-if="showFilePanel" class="file-pane">
          <FilePanel />
        </div>
      </div>

      <div
        v-if="!fullscreen"
        class="terminal-dialog-resize-handle"
        @mousedown="onResizeMouseDown"
      />
    </div>
  </teleport>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import { ElMessageBox } from 'element-plus'
import {
  Aim,
  Close,
  Folder,
  FolderOpened,
  FullScreen,
  Minus,
  Monitor,
  Moon,
  Plus,
  Sunny
} from '@element-plus/icons-vue'

import TerminalSession from './TerminalSession.vue'
import FilePanel from './FilePanel.vue'
import { useTerminalStore } from '@/store/modules/terminal'

defineOptions({ name: 'TerminalDialog' })

const terminalStore = useTerminalStore()

const dialogRef = ref(null)
const showFilePanel = ref(false)

// map of session id -> TerminalSession component instance
const sessionRefs = new Map()

function setSessionRef(id, el) {
  if (el) {
    sessionRefs.set(id, el)
  } else {
    sessionRefs.delete(id)
  }
}

function activeSessionRef() {
  return sessionRefs.get(terminalStore.activeSessionId) || null
}

const visible = computed(() => terminalStore.visible)
const minimized = computed(() => terminalStore.minimized)
const fullscreen = computed(() => terminalStore.fullscreen)
const sessions = computed(() => terminalStore.sessions)
const activeSessionId = computed(() => terminalStore.activeSessionId)
const canAddSession = computed(() => terminalStore.canAddSession)
const anyConnected = computed(() => terminalStore.anyConnected)
const activeSession = computed(() => terminalStore.activeSession)
const activeBackendSessionId = computed(() => activeSession.value ? activeSession.value.sessionId : '')

const themeIcon = computed(() => {
  const iconName = terminalStore.currentTheme.icon
  if (iconName === 'Sunny') return Sunny
  if (iconName === 'Moon') return Moon
  return Monitor
})

const themeTooltip = computed(() => `主题：${terminalStore.currentTheme.label}`)

const addTabTooltip = computed(() => canAddSession.value ? '新建标签页' : '已达单用户最大会话数')

const dialogStyle = computed(() => {
  if (fullscreen.value) {
    return {}
  }
  // position may be null before the dialog is first opened; fall back
  // to a top-left origin so template access never throws. the store
  // computes the centered position inside openDialog().
  const pos = terminalStore.position || { x: 0, y: 0 }
  const { width, height } = terminalStore.size
  return {
    left: `${pos.x}px`,
    top: `${pos.y}px`,
    width: `${width}px`,
    height: `${height}px`
  }
})

const terminalPaneStyle = computed(() => {
  const themeBg = terminalStore.currentTheme.theme.background
  return showFilePanel.value
    ? { height: '60%', background: themeBg }
    : { height: '100%', background: themeBg }
})

// ---------- drag to move ----------
let dragState = null

function onHeaderMouseDown(e) {
  if (fullscreen.value) return
  // do not start drag when clicking on header control icons
  if (e.target && e.target.closest && e.target.closest('.ctrl-icon')) return
  dragState = {
    startX: e.clientX,
    startY: e.clientY,
    originX: terminalStore.position.x,
    originY: terminalStore.position.y
  }
  window.addEventListener('mousemove', onDragMove)
  window.addEventListener('mouseup', onDragEnd, { once: true })
}

function onDragMove(e) {
  if (!dragState) return
  const dx = e.clientX - dragState.startX
  const dy = e.clientY - dragState.startY
  terminalStore.setPosition({
    x: Math.max(0, dragState.originX + dx),
    y: Math.max(0, dragState.originY + dy)
  })
}

function onDragEnd() {
  dragState = null
  window.removeEventListener('mousemove', onDragMove)
}

// ---------- resize ----------
let resizeState = null

function onResizeMouseDown(e) {
  if (fullscreen.value) return
  e.preventDefault()
  resizeState = {
    startX: e.clientX,
    startY: e.clientY,
    originW: terminalStore.size.width,
    originH: terminalStore.size.height
  }
  window.addEventListener('mousemove', onResizeMove)
  window.addEventListener('mouseup', onResizeEnd, { once: true })
}

function onResizeMove(e) {
  if (!resizeState) return
  const dx = e.clientX - resizeState.startX
  const dy = e.clientY - resizeState.startY
  terminalStore.setSize({
    width: resizeState.originW + dx,
    height: resizeState.originH + dy
  })
}

function onResizeEnd() {
  resizeState = null
  window.removeEventListener('mousemove', onResizeMove)
  nextTick(() => {
    fitAllSessions()
  })
}

function fitAllSessions() {
  sessionRefs.forEach((r) => {
    if (r && r.fit) r.fit()
  })
}

// ---------- controls ----------
// guards against re-entering ElMessageBox.confirm while one is already
// pending; without this, every additional click on the close icon (or
// tab-close icon) stacks another modal overlay and the page background
// gets progressively darker while the dialog never actually closes
let closeDialogPending = false
const closingTabIds = new Set()

// Element Plus assigns popup z-indexes starting at 2000 and increments
// per popup.  The terminal dialog itself is fixed at z-index 3000 (see
// the .terminal-dialog rule below), so without an explicit override the
// confirm MessageBox renders *underneath* the dialog and the user can
// never see or click it.  Push the confirm above the dialog so the
// button is reachable.
const CONFIRM_Z_INDEX = 4000

function cycleTheme() {
  terminalStore.cycleTheme()
}

function toggleFilePanel() {
  showFilePanel.value = !showFilePanel.value
  nextTick(() => {
    fitAllSessions()
  })
}

function toggleFullscreen() {
  terminalStore.toggleFullscreen()
  nextTick(() => {
    fitAllSessions()
  })
}

function minimize() {
  terminalStore.toggleMinimize()
}

// double-click the header to toggle fullscreen
function onHeaderDblClick(e) {
  // ignore double clicks on control icons
  if (e.target && e.target.closest && e.target.closest('.ctrl-icon')) return
  toggleFullscreen()
}

function restoreFromMinimize() {
  terminalStore.toggleMinimize()
  nextTick(() => {
    const r = activeSessionRef()
    if (r) {
      r.fit()
      r.focus()
    }
  })
}

async function onClose() {
  if (closeDialogPending) return
  // confirm only when any shell produced output and is still connected
  if (terminalStore.anyConnected && terminalStore.hasForegroundOutput) {
    closeDialogPending = true
    try {
      await ElMessageBox.confirm(
        '终端会话仍在运行，关闭将中断当前任务，确认关闭？',
        '关闭确认',
        {
          type: 'warning',
          confirmButtonText: '关闭',
          cancelButtonText: '取消',
          zIndex: CONFIRM_Z_INDEX
        }
      )
    } catch {
      return
    } finally {
      closeDialogPending = false
    }
  }
  terminalStore.closeDialog()
}

function onSessionOpen(id, msg) {
  terminalStore.updateSession(id, {
    sessionId: (msg && msg.session_id) || '',
    connected: true
  })
}

function onSessionClose(id) {
  terminalStore.updateSession(id, { connected: false })
}

// ---------- tab bar ----------
function setActiveSession(id) {
  terminalStore.setActiveSession(id)
  nextTick(() => {
    const r = activeSessionRef()
    if (r) {
      r.fit()
      r.focus()
    }
  })
}

async function closeTab(session) {
  // ignore re-entrant clicks for the same tab; this prevents multiple
  // overlapping modal overlays when the user clicks the close icon
  // several times before the first confirm resolves
  if (closingTabIds.has(session.id)) return
  // if the tab is still connected and has foreground output, confirm first
  if (session.connected && terminalStore.hasForegroundOutput) {
    closingTabIds.add(session.id)
    try {
      await ElMessageBox.confirm(
        `会话 "${session.title}" 仍在运行，关闭将中断当前任务，确认关闭？`,
        '关闭确认',
        {
          type: 'warning',
          confirmButtonText: '关闭',
          cancelButtonText: '取消',
          zIndex: CONFIRM_Z_INDEX
        }
      )
    } catch {
      return
    } finally {
      closingTabIds.delete(session.id)
    }
  }
  terminalStore.removeSession(session.id)
}

function onAddTab() {
  if (!canAddSession.value) return
  terminalStore.addSession()
}

// whenever the dialog re-opens, focus the active terminal
watch(visible, async(v) => {
  if (v) {
    await nextTick()
    const r = activeSessionRef()
    if (r) {
      r.fit()
      r.focus()
    }
  }
})

// whenever a new session becomes active, fit and focus it
watch(activeSessionId, async() => {
  await nextTick()
  const r = activeSessionRef()
  if (r) {
    r.fit()
    r.focus()
  }
})
</script>

<style lang="scss" scoped>
.terminal-dialog {
  position: fixed;
  // keep below Element Plus popup z-index base (2000) so MessageBox
  // confirms render above this dialog; otherwise the confirm is hidden
  // behind the dialog and the close action appears broken
  z-index: 1999;
  display: flex;
  flex-direction: column;
  background: #fff;
  border: 1px solid #dcdfe6;
  border-radius: 6px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.18);
  overflow: hidden;

  &.is-fullscreen {
    top: 0 !important;
    left: 0 !important;
    width: 100vw !important;
    height: 100vh !important;
    border-radius: 0;
  }
}

.terminal-dialog-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 36px;
  padding: 0 8px 0 12px;
  background: #2b2f3a;
  color: #cfd3dc;
  cursor: move;
  user-select: none;
  overflow: hidden;

  .terminal-dialog-title {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 13px;
    flex: 1 1 auto;
    min-width: 0;
    overflow: hidden;

    span {
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .terminal-dialog-session {
      color: #909399;
      font-size: 12px;
      flex-shrink: 0;
    }
  }

  .terminal-dialog-controls {
    display: inline-flex;
    align-items: center;
    gap: 2px;
    flex-shrink: 0;
    margin-left: 8px;
    // keep the controls visible even when the dialog is dragged narrower
    // than the title text; without this the title's flex:1 can squeeze the
    // icons out of the visible area at small widths
    min-width: max-content;

    .ctrl-icon {
      cursor: pointer;
      padding: 6px;
      font-size: 14px;
      color: #cfd3dc;
      // make sure each control always renders at a clickable size; some
      // Element Plus icon wrappers collapse to 0-width without explicit
      // inline-flex layout when nested inside flex parents
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 26px;
      height: 26px;
      box-sizing: border-box;

      &:hover {
        color: #fff;
      }
    }

    .ctrl-close:hover {
      color: #f56c6c;
    }
  }
}

.terminal-tab-bar {
  display: flex;
  align-items: center;
  height: 32px;
  padding: 0 4px;
  background: #252830;
  overflow-x: auto;
  overflow-y: hidden;
  user-select: none;

  &::-webkit-scrollbar {
    height: 4px;
  }

  &::-webkit-scrollbar-thumb {
    background: #4a4f5a;
    border-radius: 2px;
  }
}

.terminal-tab {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 28px;
  padding: 0 10px;
  margin-right: 2px;
  background: #2f333d;
  color: #9ca3af;
  font-size: 12px;
  border-top-left-radius: 4px;
  border-top-right-radius: 4px;
  cursor: pointer;
  white-space: nowrap;

  &:hover {
    color: #e5e7eb;
  }

  &.is-active {
    background: #3a3f4b;
    color: #f3f4f6;
  }

  .tab-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    flex-shrink: 0;
  }

  .tab-dot-on {
    background: #67c23a;
  }

  .tab-dot-off {
    background: #f56c6c;
  }

  .tab-title {
    max-width: 140px;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .tab-close {
    font-size: 12px;
    padding: 2px;
    border-radius: 2px;
    color: #6b7280;

    &:hover {
      color: #f56c6c;
      background: rgba(255, 255, 255, 0.08);
    }
  }
}

.tab-add-wrapper {
  display: inline-flex;
  align-items: center;
  margin-left: 6px;
}

.tab-add {
  cursor: pointer;
  // larger hit-area and a visible tile so the button is not lost
  // against the dark tab-bar background
  width: 24px;
  height: 24px;
  padding: 0;
  font-size: 16px;
  font-weight: 600;
  color: #e5e7eb;
  background: #3a3f4b;
  border: 1px solid #4b5563;
  border-radius: 4px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  box-sizing: border-box;
  transition: background 0.15s ease, color 0.15s ease;

  &:hover {
    color: #ffffff;
    background: #4a5160;
    border-color: #6b7280;
  }

  &.is-disabled {
    cursor: not-allowed;
    color: #6b7280;
    background: #2f333d;
    border-color: #3a3f4b;

    &:hover {
      color: #6b7280;
      background: #2f333d;
      border-color: #3a3f4b;
    }
  }
}

.terminal-dialog-body {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;

  .terminal-pane {
    flex: 1;
    min-height: 0;
  }

  .file-pane {
    height: 40%;
    min-height: 120px;
    border-top: 1px solid #e4e7ed;
    background: #fff;
    overflow: auto;
  }
}

.terminal-dialog-resize-handle {
  position: absolute;
  right: 0;
  bottom: 0;
  width: 14px;
  height: 14px;
  cursor: nwse-resize;
  background: linear-gradient(135deg, transparent 50%, #c0c4cc 50%, #c0c4cc 60%, transparent 60%);
}

.terminal-minimized-pill {
  position: fixed;
  right: 24px;
  bottom: 24px;
  // match .terminal-dialog so popups still render above
  z-index: 1999;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  background: #2b2f3a;
  color: #fff;
  border-radius: 18px;
  cursor: pointer;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.18);

  .pill-text {
    font-size: 13px;
  }

  .pill-dot {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #909399;
  }

  .pill-dot-on {
    background: #67c23a;
  }
}
</style>
