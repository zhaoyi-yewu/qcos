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
  <!-- Drawer mode -->
  <t-drawer
    v-if="store.displayMode === 'drawer'"
    v-model:visible="drawerVisible"
    placement="right"
    :size="`${store.drawerWidth}px`"
    :show-overlay="false"
    :footer="false"
    class="ai-agent-drawer"
    @close="onClose"
  >
    <!-- Customise the whole header: title + action buttons. TDesign's
         Drawer exposes `header` as a TNode slot, so we can put our
         "switch to floating" / "session history" controls next to the
         title instead of being stuck with a plain string. -->
    <!-- Resize handle: a thin strip on the drawer's LEFT edge that
         the user can grab to change the panel width. Placed inside
         the drawer template so it inherits the drawer's positioning
         context. -->
    <div
      class="drawer-resize-handle"
      :class="{ 'is-resizing': isDrawerResizing }"
      @mousedown="onDrawerResizeStart"
    />
    <template #header>
      <div class="drawer-header">
        <span class="drawer-header-title">AI 助手</span>
        <div class="drawer-header-actions">
          <t-tooltip content="切换为浮窗" placement="bottom">
            <t-button size="small" variant="text" shape="square" @click="switchToFloating">
              <template #icon><JumpIcon /></template>
            </t-button>
          </t-tooltip>
          <!-- Minimise from drawer mode: switch to floating AND minimise
               in one go, so the user sees the pill dock at the bottom
               right (the same place it would have come from had they
               started in floating mode). Drawer itself has no concept
               of a minimised pill, so reusing the floating pill keeps
               the mental model simple. -->
          <t-tooltip content="最小化" placement="bottom">
            <t-button
              size="small"
              variant="text"
              shape="square"
              class="drawer-minimize-btn"
              @click="minimizeFromDrawer"
            >
              <template #icon><MinusIcon /></template>
            </t-button>
          </t-tooltip>
        </div>
      </div>
    </template>
    <AiAgentChat />

    <!-- Session-history side panel. Slides in over the chat when the
         History button is clicked. Implemented as a plain overlay div
         (rather than a nested drawer) so the user can dismiss it by
         clicking the mask without losing the outer drawer state. -->
    <div
      v-if="showSessionList"
      class="session-list-overlay"
      @click.self="showSessionList = false"
    >
      <div class="session-list-panel">
        <div class="session-list-header">
          <span>会话历史</span>
          <t-button size="small" variant="text" shape="square" @click="showSessionList = false">
            <template #icon><CloseIcon /></template>
          </t-button>
        </div>
        <div class="session-list-actions">
          <t-button size="small" theme="primary" block @click="onNewSession">
            新建会话
          </t-button>
        </div>
        <!-- Batch ops bar: visible only when at least one session is
             selected. Provides "select all / none" toggle and a
             delete-selected button. -->
        <div v-if="sessions.length > 0" class="session-list-batchbar">
          <t-checkbox
            :checked="isAllSelected"
            :indeterminate="isIndeterminate"
            @change="onToggleSelectAll"
          >
            全选 ({{ selectedSessionIds.size }}/{{ sessions.length }})
          </t-checkbox>
          <t-popconfirm
            content="确定删除选中的会话吗？此操作不可恢复。"
            placement="bottom-right"
            @confirm="onDeleteSelected"
          >
            <t-button
              size="small"
              theme="danger"
              variant="text"
              :disabled="selectedSessionIds.size === 0"
            >
              <template #icon><DeleteIcon /></template>
              删除 ({{ selectedSessionIds.size }})
            </t-button>
          </t-popconfirm>
        </div>
        <div class="session-list-body">
          <div v-if="sessions.length === 0" class="session-empty">
            暂无历史会话
          </div>
          <div
            v-for="s in sessions"
            :key="s.session_id"
            class="session-item"
            :class="{ 'is-active': s.session_id === store.activeSessionId }"
            @click="onSelectSession(s.session_id)"
          >
            <t-checkbox
              :checked="selectedSessionIds.has(s.session_id)"
              class="session-item-checkbox"
              @click.stop
              @change="checked => onToggleSelectSession(s.session_id, checked)"
            />
            <div class="session-item-content">
              <div class="session-item-title">{{ s.title || '未命名会话' }}</div>
              <div class="session-item-meta">
                <span class="session-item-time">{{ formatSessionTime(s.updated_at || s.created_at) }}</span>
                <span
                  class="session-item-delete"
                  @click.stop="onDeleteSession(s.session_id)"
                >
                  <DeleteIcon />
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </t-drawer>

  <!-- Floating mode -->
  <teleport to="body">
    <div
      v-if="store.displayMode === 'floating' && store.visible"
      v-show="!store.minimized"
      ref="floatingRef"
      class="ai-agent-floating"
      :class="{ 'is-fullscreen': store.floatingFullscreen }"
      :style="floatingStyle"
    >
      <div
        class="floating-header"
        @mousedown="onHeaderMouseDown"
        @dblclick="onHeaderDblClick"
      >
        <div class="floating-title">
          <ChatBubbleIcon class="floating-title-icon" />
          <span class="floating-title-text">AI 助手</span>
        </div>
        <div class="floating-controls">
          <t-tooltip content="吸附到右侧" placement="bottom">
            <span class="ctrl-icon" @click.stop="switchToDrawer">
              <ChevronRightIcon />
            </span>
          </t-tooltip>
          <t-tooltip v-if="!store.floatingFullscreen" content="最小化" placement="bottom">
            <span class="ctrl-icon ctrl-minimize" @click.stop="store.toggleMinimize()">
              <MinusIcon />
            </span>
          </t-tooltip>
          <t-tooltip :content="store.floatingFullscreen ? '还原' : '最大化'" placement="bottom">
            <span class="ctrl-icon" @click.stop="store.toggleFloatingFullscreen()">
              <FullscreenExit1Icon v-if="store.floatingFullscreen" />
              <Fullscreen1Icon v-else />
            </span>
          </t-tooltip>
          <t-tooltip content="关闭" placement="bottom">
            <span class="ctrl-icon ctrl-close" @click.stop="onClose">
              <CloseIcon />
            </span>
          </t-tooltip>
        </div>
      </div>
      <div class="floating-body">
        <AiAgentChat />

        <!-- Session-history overlay (same as drawer mode). Rendered
             inside floating-body so it inherits the panel's bounds. -->
        <div
          v-if="showSessionList"
          class="session-list-overlay"
          @click.self="showSessionList = false"
        >
          <div class="session-list-panel">
            <div class="session-list-header">
              <span>会话历史</span>
              <t-button size="small" variant="text" shape="square" @click="showSessionList = false">
                <template #icon><CloseIcon /></template>
              </t-button>
            </div>
            <div class="session-list-actions">
              <t-button size="small" theme="primary" block @click="onNewSession">
                新建会话
              </t-button>
            </div>
            <!-- Batch ops bar (floating mode twin of the drawer one) -->
            <div v-if="sessions.length > 0" class="session-list-batchbar">
              <t-checkbox
                :checked="isAllSelected"
                :indeterminate="isIndeterminate"
                @change="onToggleSelectAll"
              >
                全选 ({{ selectedSessionIds.size }}/{{ sessions.length }})
              </t-checkbox>
              <t-popconfirm
                content="确定删除选中的会话吗？此操作不可恢复。"
                placement="bottom-right"
                @confirm="onDeleteSelected"
              >
                <t-button
                  size="small"
                  theme="danger"
                  variant="text"
                  :disabled="selectedSessionIds.size === 0"
                >
                  <template #icon><DeleteIcon /></template>
                  删除 ({{ selectedSessionIds.size }})
                </t-button>
              </t-popconfirm>
            </div>
            <div class="session-list-body">
              <div v-if="sessions.length === 0" class="session-empty">
                暂无历史会话
              </div>
              <div
                v-for="s in sessions"
                :key="s.session_id"
                class="session-item"
                :class="{ 'is-active': s.session_id === store.activeSessionId }"
                @click="onSelectSession(s.session_id)"
              >
                <t-checkbox
                  :checked="selectedSessionIds.has(s.session_id)"
                  class="session-item-checkbox"
                  @click.stop
                  @change="checked => onToggleSelectSession(s.session_id, checked)"
                />
                <div class="session-item-content">
                  <div class="session-item-title">{{ s.title || '未命名会话' }}</div>
                  <div class="session-item-meta">
                    <span class="session-item-time">{{ formatSessionTime(s.updated_at || s.created_at) }}</span>
                    <span
                      class="session-item-delete"
                      @click.stop="onDeleteSession(s.session_id)"
                    >
                      <DeleteIcon />
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
      <div
        v-if="!store.floatingFullscreen"
        class="floating-resize-handle"
        @mousedown="onResizeMouseDown"
      />
    </div>

    <!-- Minimized pill. When the terminal pill is also docked at the
         bottom-right, lift the AI pill one slot higher so the two
         never overlap. -->
    <div
      v-if="store.displayMode === 'floating' && store.visible && store.minimized"
      class="ai-agent-minimized-pill"
      :class="{ 'is-above-terminal': isTerminalPillVisible }"
      @click="store.restoreFromMinimize()"
    >
      <ChatBubbleIcon />
      <span>AI 助手</span>
    </div>
  </teleport>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, provide } from 'vue'
import {
  JumpIcon,
  ChevronRightIcon,
  MinusIcon,
  CloseIcon,
  ChatBubbleIcon,
  Fullscreen1Icon,
  FullscreenExit1Icon,
  DeleteIcon
} from 'tdesign-icons-vue-next'
import { useAiAgentStore } from '@/store/modules/aiAgent'
import { useTerminalStore } from '@/store/modules/terminal'
import AiAgentChat from './AiAgentChat.vue'

const store = useAiAgentStore()
const terminalStore = useTerminalStore()

// Mirror the visibility rule of TerminalDialog's minimized pill: the
// pill only renders while the terminal dialog itself is visible AND
// minimized. When that pill is on screen we lift ours one slot up.
const isTerminalPillVisible = computed(
  () => terminalStore.visible && terminalStore.minimized
)

const drawerVisible = computed({
  get: () => store.visible && store.displayMode === 'drawer',
  set: v => {
    if (!v) store.close()
  }
})

const showSessionList = ref(false)

// Provide the session-list toggle to child components (AiAgentChat)
// so the toolbar icon can open the history panel without prop drilling.
provide('showSessionList', showSessionList)

// Mirror the sessions array as a local computed so the template gets
// reactive updates when store.fetchSessions() resolves.
const sessions = computed(() => store.sessions)

/**
 * Load the session list whenever the panel opens. The store handles
 * errors internally, so we just fire-and-forget here.
 */
watch(showSessionList, async v => {
  if (v) {
    await store.fetchSessions()
  }
})

/*
 * Push the page content aside while the drawer is open so the AI
 * agent sits BESIDE the page (e.g. monitor-center) instead of
 * floating on top of it. We do this by adding a `padding-right`
 * equal to the drawer's width to <body> - the global layout uses
 * normal block flow for the main column, so the padding naturally
 * shrinks its width. The padding is removed again when the drawer
 * closes (or the user switches to floating mode).
 */
watch(
  () => [store.visible, store.displayMode, store.drawerWidth],
  ([visible, mode, width]) => {
    const shouldPad = visible && mode === 'drawer'
    // Push only the scrollable page-content region (.app-main) left;
    // the navbar stays at its natural full width. Padding the outer
    // .main-container would also shrink the fixed-position
    // .fixed-header because its `width: calc(100% - sidebar)` reads
    // from the padding-reduced content box, which is what caused the
    // navbar to be visually squeezed when the drawer snapped open.
    const appMain = document.querySelector('.app-main')
    if (appMain) {
      appMain.style.transition = shouldPad ? 'padding-right 0.2s ease' : ''
      appMain.style.paddingRight = shouldPad ? `${width}px` : ''
    }
  },
  { immediate: true }
)

// Restore the original padding when the container unmounts so
// navigation away from a page that had the drawer open doesn't
// leave stale padding behind.
onUnmounted(() => {
  const appMain = document.querySelector('.app-main')
  if (appMain) {
    appMain.style.paddingRight = ''
    appMain.style.transition = ''
  }
})

async function onSelectSession(sessionId) {
  await store.loadSession(sessionId)
  showSessionList.value = false
}

async function onDeleteSession(sessionId) {
  await store.removeSession(sessionId)
  // Drop the deleted id from the local selection set (if present)
  // so the batch bar's "N selected" counter stays accurate.
  selectedSessionIds.value.delete(sessionId)
}

/*
 * Multi-select state for batch-delete. Stored as a Set (Vue 3
 * reactivity tracks Set mutations via the `ref` wrapper).
 */
const selectedSessionIds = ref(new Set())

const isAllSelected = computed(
  () => sessions.value.length > 0
    && selectedSessionIds.value.size === sessions.value.length
)
const isIndeterminate = computed(
  () => selectedSessionIds.value.size > 0
    && selectedSessionIds.value.size < sessions.value.length
)

function onToggleSelectSession(sessionId, checked) {
  if (checked) {
    selectedSessionIds.value.add(sessionId)
  } else {
    selectedSessionIds.value.delete(sessionId)
  }
}

function onToggleSelectAll(checked) {
  if (checked) {
    selectedSessionIds.value = new Set(
      sessions.value.map(s => s.session_id)
    )
  } else {
    selectedSessionIds.value = new Set()
  }
}

/**
 * Batch-delete the selected sessions. Invoked only after the user
 * confirms via the Popconfirm in the batch bar.
 */
async function onDeleteSelected() {
  const ids = [...selectedSessionIds.value]
  // Sequentially remove to keep the backend session store happy and
  // surface per-session errors individually.
  for (const id of ids) {
    try {
      await store.removeSession(id)
    } catch (e) {
      console.error(`Failed to delete session ${id}:`, e)
    }
  }
  selectedSessionIds.value = new Set()
}

// Clear the selection when the session list is closed so re-opening
// starts fresh.
watch(showSessionList, v => {
  if (!v) selectedSessionIds.value = new Set()
})

async function onNewSession() {
  await store.createNewSession()
  // Keep the session list open after creating a new conversation so
  // the user can immediately see the new entry in the list (and can
  // switch back to a previous one without reopening the panel).
  await store.fetchSessions()
}

function formatSessionTime(ts) {
  if (!ts) return ''
  // Backend returns unix seconds; fall back gracefully for ISO strings.
  const d = typeof ts === 'number' ? new Date(ts * 1000) : new Date(ts)
  if (Number.isNaN(d.getTime())) return ''
  const pad = n => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

// Floating geometry
const floatingRef = ref(null)
const isDragging = ref(false)
const isResizing = ref(false)
const dragStart = ref({ x: 0, y: 0 })
const resizeStart = ref({ width: 0, height: 0, x: 0, y: 0 })

/**
 * Drag-to-resize state for the drawer's LEFT edge. The drawer is
 * anchored to the right side of the viewport, so dragging its left
 * edge further left should make it wider (and vice versa).
 */
const DRAWER_MIN_WIDTH = 320
const DRAWER_MAX_WIDTH = () => Math.floor(window.innerWidth * 0.8)
const isDrawerResizing = ref(false)
const drawerResizeStart = ref({ x: 0, width: 0 })

function onDrawerResizeStart(e) {
  if (e.button !== 0) return
  e.preventDefault()
  isDrawerResizing.value = true
  drawerResizeStart.value = {
    x: e.clientX,
    width: store.drawerWidth
  }
  document.addEventListener('mousemove', onDrawerResizeMove)
  document.addEventListener('mouseup', onDrawerResizeEnd)
}

function onDrawerResizeMove(e) {
  if (!isDrawerResizing.value) return
  const dx = drawerResizeStart.value.x - e.clientX
  const newWidth = Math.min(
    DRAWER_MAX_WIDTH(),
    Math.max(DRAWER_MIN_WIDTH, drawerResizeStart.value.width + dx)
  )
  store.drawerWidth = newWidth
}

function onDrawerResizeEnd() {
  if (!isDrawerResizing.value) return
  isDrawerResizing.value = false
  document.removeEventListener('mousemove', onDrawerResizeMove)
  document.removeEventListener('mouseup', onDrawerResizeEnd)
  // Persist the final width via the store's setter (writes to
  // localStorage through the persist() helper).
  store.setDrawerWidth(store.drawerWidth)
}

const floatingStyle = computed(() => {
  // In fullscreen mode the CSS class `.is-fullscreen` pins the panel to
  // the viewport edges with `!important`, so we can skip the inline
  // position/size styles entirely (returning only z-index keeps the
  // element above siblings while letting the class control geometry).
  if (store.floatingFullscreen) {
    return { zIndex: 1999 }
  }
  const pos = store.floatingPosition || { x: 100, y: 100 }
  const size = store.floatingSize
  return {
    left: `${pos.x}px`,
    top: `${pos.y}px`,
    width: `${size.width}px`,
    height: `${size.height}px`,
    zIndex: 1999
  }
})

function onClose() {
  store.close()
}

function switchToFloating() {
  store.setDisplayMode('floating')
}

function switchToDrawer() {
  store.setDisplayMode('drawer')
}

/**
 * Minimise while in drawer mode. The store remembers the previous
 * displayMode (drawer) and switches to floating internally so the
 * minimized pill can dock at the bottom-right. When the user clicks
 * the pill to restore, the store flips back to drawer mode - the
 * panel returns to whichever form it had before being minimized.
 */
function minimizeFromDrawer() {
  store.minimizeFromDrawer()
}

// Drag handlers
function onHeaderMouseDown(e) {
  if (e.button !== 0) return
  if (store.floatingFullscreen) return // disable drag in fullscreen
  isDragging.value = true
  dragStart.value = { x: e.clientX, y: e.clientY }
  document.addEventListener('mousemove', onDragMove)
  document.addEventListener('mouseup', onDragEnd)
}

function onDragMove(e) {
  if (!isDragging.value) return
  const dx = e.clientX - dragStart.value.x
  const dy = e.clientY - dragStart.value.y
  const pos = store.floatingPosition || { x: 100, y: 100 }
  store.setFloatingGeometry({
    position: { x: pos.x + dx, y: pos.y + dy }
  })
  dragStart.value = { x: e.clientX, y: e.clientY }
}

function onDragEnd() {
  isDragging.value = false
  document.removeEventListener('mousemove', onDragMove)
  document.removeEventListener('mouseup', onDragEnd)
}

// Resize handlers
function onResizeMouseDown(e) {
  if (e.button !== 0) return
  if (store.floatingFullscreen) return // disable resize in fullscreen
  isResizing.value = true
  resizeStart.value = {
    width: store.floatingSize.width,
    height: store.floatingSize.height,
    x: e.clientX,
    y: e.clientY
  }
  document.addEventListener('mousemove', onResizeMove)
  document.addEventListener('mouseup', onResizeEnd)
  e.preventDefault()
}

function onResizeMove(e) {
  if (!isResizing.value) return
  const dx = e.clientX - resizeStart.value.x
  const dy = e.clientY - resizeStart.value.y
  store.setFloatingGeometry({
    size: {
      width: Math.max(320, resizeStart.value.width + dx),
      height: Math.max(400, resizeStart.value.height + dy)
    }
  })
}

function onResizeEnd() {
  isResizing.value = false
  document.removeEventListener('mousemove', onResizeMove)
  document.removeEventListener('mouseup', onResizeEnd)
}

/**
 * Double-click the floating header to toggle fullscreen. Clicks that
 * land on a control icon (maximise / minimise / close / dock) should
 * not trigger fullscreen - those buttons have their own handlers.
 */
function onHeaderDblClick(e) {
  if (e.target && e.target.closest && e.target.closest('.ctrl-icon')) return
  store.toggleFloatingFullscreen()
}

// Keyboard shortcuts
function onKeydown(e) {
  if (e.ctrlKey && e.key === '/') {
    e.preventDefault()
    if (store.visible) {
      store.close()
    } else {
      store.open()
    }
  }
  if (e.ctrlKey && e.shiftKey && e.key === '/') {
    e.preventDefault()
    store.setDisplayMode(store.displayMode === 'drawer' ? 'floating' : 'drawer')
  }
}

onMounted(() => {
  document.addEventListener('keydown', onKeydown)
})

onUnmounted(() => {
  document.removeEventListener('keydown', onKeydown)
  document.removeEventListener('mousemove', onDragMove)
  document.removeEventListener('mouseup', onDragEnd)
  document.removeEventListener('mousemove', onResizeMove)
  document.removeEventListener('mouseup', onResizeEnd)
})
</script>

<!--
 * Global (non-scoped) overrides for the TDesign Drawer host. The
 * drawer is teleported to <body> at runtime, so scoped styles in
 * this SFC cannot reach it - any rule that targets .t-drawer or its
 * inner parts must live in a plain <style> block to take effect.
 -->
<style>
/*
 * Pin the AI drawer BELOW the global navbar (50px) so the two sit
 * side-by-side instead of stacking. TDesign Drawer defaults to
 * `position: fixed; top: 0; right: 0; height: 100vh`, which would
 * cover the navbar - we override top and height on the outer
 * container AND the inner content wrapper so every layer of the
 * drawer (including the absolute-positioned header / body / mask)
 * occupies only the viewport area below the navbar.
 */
.ai-agent-drawer .t-drawer,
.ai-agent-drawer .t-drawer__content-wrapper,
.ai-agent-drawer .t-drawer__content {
  top: 50px !important;
  height: calc(100vh - 50px) !important;
  max-height: calc(100vh - 50px) !important;
}

/*
 * Drawer-mode minimise button: 40% opacity by default (matches the
 * floating-mode minimise icon). Lives in the global stylesheet
 * because the drawer is teleported to <body> and is therefore
 * outside this SFC's scoped-styles tree.
 */
.ai-agent-drawer .drawer-minimize-btn {
  opacity: 0.4;
  transition: opacity 0.15s ease;
}

.ai-agent-drawer .drawer-minimize-btn:hover,
.ai-agent-drawer .drawer-minimize-btn:focus-visible {
  opacity: 1;
}
</style>

<style scoped>

/*
 * Resize handle pinned to the drawer's LEFT edge. The drawer body
 * is `position: relative`, so the handle can be `absolute` and
 * tracks the drawer's width automatically. Invisible by default;
 * a faint brand-color indicator line appears on hover.
 */
.drawer-resize-handle {
  position: absolute;
  left: -4px;
  top: 0;
  bottom: 0;
  width: 8px;
  cursor: col-resize;
  z-index: 5;
  background: transparent;
  transition: background 0.15s;
}

.drawer-resize-handle:hover,
.drawer-resize-handle.is-resizing {
  background: var(--td-brand-color-light);
}

.ai-agent-drawer :deep(.t-drawer__body) {
  padding: 0;
  /* Anchor the resize-handle (absolute) so it sits on the drawer's
     left edge. */
  position: relative;
  /* Anchor the session-history overlay (absolute) to the drawer body
     so it covers only the chat area, not the whole viewport. */
  position: relative;
}

.ai-agent-drawer :deep(.t-drawer__content-wrapper) {
  width: 100%;
}

.drawer-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  gap: 8px;
}

.drawer-header-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--td-text-color-primary);
  letter-spacing: 0.2px;
}

.drawer-header-actions {
  display: inline-flex;
  gap: 4px;
}

.ai-agent-floating {
  position: fixed;
  display: flex;
  flex-direction: column;
  background: var(--td-bg-color-container);
  border-radius: 14px;
  /* Layered shadows: a tight key light for definition + a soft ambient
     halo so the panel floats above the page instead of feeling pasted
     onto it. */
  box-shadow:
    0 1px 2px rgba(15, 23, 42, 0.06),
    0 8px 24px rgba(15, 23, 42, 0.12),
    0 24px 64px rgba(15, 23, 42, 0.08);
  border: 1px solid rgba(15, 23, 42, 0.06);
  overflow: hidden;
  /* Smooth entrance / minimize transitions. */
  transition: box-shadow 0.25s ease;
}

.ai-agent-floating:hover {
  box-shadow:
    0 1px 2px rgba(15, 23, 42, 0.08),
    0 12px 32px rgba(15, 23, 42, 0.16),
    0 32px 80px rgba(15, 23, 42, 0.12);
}

/* Fullscreen mode: pin the floating panel to the viewport edges and
   drop the rounded corners + shadow so it reads as a proper fullscreen
   surface, matching TerminalDialog's behaviour. Inline position/size
   styles are skipped via `floatingStyle` while this class is active. */
.ai-agent-floating.is-fullscreen {
  left: 0 !important;
  top: 0 !important;
  width: 100vw !important;
  height: 100vh !important;
  border-radius: 0;
  border: none;
  box-shadow: none;
}

.ai-agent-floating.is-fullscreen:hover {
  box-shadow: none;
}

.ai-agent-floating.is-fullscreen .floating-header {
  border-radius: 0;
}

.floating-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 14px;
  /* Subtle primary-tinted gradient so the header reads as the "brand"
     area without competing with the chat content. */
  background: linear-gradient(
    135deg,
    var(--td-brand-color-2) 0%,
    var(--td-brand-color-1) 60%,
    var(--td-bg-color-container) 100%
  );
  border-bottom: 1px solid var(--td-component-border);
  cursor: move;
  user-select: none;
}

.floating-title {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 600;
  color: var(--td-text-color-primary);
  letter-spacing: 0.2px;
}

.floating-title-icon {
  font-size: 16px;
  color: var(--td-brand-color);
}

.floating-title-text {
  line-height: 1;
}

.floating-controls {
  display: flex;
  gap: 4px;
  align-items: center;
}

.ctrl-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: var(--td-text-color-secondary);
  font-size: 14px;
  padding: 6px;
  border-radius: 6px;
  transition: background-color 0.15s ease, color 0.15s ease;
}

.ctrl-icon:hover {
  color: var(--td-brand-color);
  background: var(--td-brand-color-1);
}

.ctrl-close:hover {
  color: var(--td-error-color);
  background: var(--td-error-color-1);
}

/*
 * Minimise button (floating window only): rendered at 40% opacity by
 * default so it reads as a secondary affordance. Full opacity returns
 * on hover/focus. The drawer-mode twin lives in the global <style>
 * block above because the drawer is teleported out of the scoped
 * tree.
 */
.ctrl-icon.ctrl-minimize {
  opacity: 0.5;
  transition: opacity 0.15s ease, background-color 0.15s ease, color 0.15s ease;
}

.ctrl-icon.ctrl-minimize:hover,
.ctrl-icon.ctrl-minimize:focus-visible {
  opacity: 1;
}

.floating-body {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  background: var(--td-bg-color-page);
  /* Anchor the session-history overlay (absolute) so it stays inside
     the floating panel instead of escaping to the viewport. */
  position: relative;
}

.floating-resize-handle {
  position: absolute;
  bottom: 0;
  right: 0;
  width: 18px;
  height: 18px;
  cursor: nwse-resize;
  /* Slightly more visible than a 1px line, but still discreet. */
  background: linear-gradient(
    135deg,
    transparent 50%,
    var(--td-component-border) 50%,
    var(--td-component-border) 60%,
    transparent 60%
  );
  opacity: 0.6;
  transition: opacity 0.15s ease;
}

.floating-resize-handle:hover {
  opacity: 1;
}

/*
 * Minimized pill: 40% opacity by default so it reads as a passive
 * "dock" element on the page corner instead of competing with the
 * content underneath. Full opacity returns on hover so the click
 * target is still discoverable.
 */
.ai-agent-minimized-pill {
  position: fixed;
  bottom: 24px;
  right: 24px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 9px 16px;
  opacity: 0.4;
  /* Gradient + ring makes the pill feel like a FAB rather than a tag. */
  background: linear-gradient(
    135deg,
    var(--td-brand-color) 0%,
    var(--td-brand-color-7) 100%
  );
  color: #fff;
  font-size: 13px;
  font-weight: 500;
  letter-spacing: 0.2px;
  border-radius: 999px;
  cursor: pointer;
  box-shadow:
    0 2px 6px rgba(0, 82, 217, 0.35),
    0 8px 20px rgba(0, 82, 217, 0.25);
  z-index: 1999;
  transition:
    transform 0.2s ease,
    box-shadow 0.2s ease,
    filter 0.2s ease;
  /* Subtle "breathing" glow so the user notices the assistant is still
     alive while minimized. */
  animation: ai-pill-glow 2.6s ease-in-out infinite;
}

.ai-agent-minimized-pill:hover {
  opacity: 1;
  transform: translateY(-2px);
  box-shadow:
    0 4px 10px rgba(0, 82, 217, 0.45),
    0 12px 28px rgba(0, 82, 217, 0.3);
  filter: brightness(1.05);
}

.ai-agent-minimized-pill:active {
  transform: translateY(0);
  filter: brightness(0.98);
}

@keyframes ai-pill-glow {
  0%, 100% {
    box-shadow:
      0 2px 6px rgba(0, 82, 217, 0.35),
      0 8px 20px rgba(0, 82, 217, 0.25);
  }
  50% {
    box-shadow:
      0 2px 8px rgba(0, 82, 217, 0.45),
      0 10px 26px rgba(0, 82, 217, 0.35);
  }
}

/*
 * When the terminal minimized pill is docked at bottom:24px, lift the
 * AI pill one slot above it so the two don't overlap. The terminal
 * pill is roughly 34px tall (8px padding * 2 + ~18px line), so
 * 24 + 34 + 12 = 70px clears it with a small gap.
 */
.ai-agent-minimized-pill.is-above-terminal {
  bottom: 70px;
}

/* ===== Session-history side panel (drawer + floating mode) =====
 * Docked on the LEFT edge of the chat area so the conversation list
 * reads like a typical IDE sidebar / chat-app drawer. */
.session-list-overlay {
  position: absolute;
  inset: 0;
  background: rgba(15, 23, 42, 0.32);
  display: flex;
  justify-content: flex-start;
  z-index: 10;
}

.session-list-panel {
  width: 260px;
  max-width: 80%;
  height: 100%;
  background: var(--td-bg-color-container);
  box-shadow: 4px 0 16px rgba(15, 23, 42, 0.08);
  display: flex;
  flex-direction: column;
  animation: session-panel-slide 0.18s ease;
}

@keyframes session-panel-slide {
  from { transform: translateX(-100%); }
  to { transform: translateX(0); }
}

.session-list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 14px;
  font-size: 13px;
  font-weight: 600;
  color: var(--td-text-color-primary);
  border-bottom: 1px solid var(--td-component-border);
}

.session-list-actions {
  padding: 12px 14px;
  border-bottom: 1px solid var(--td-component-border);
}

/* Batch ops bar (select-all + delete-selected) sitting directly
   below the actions block. Hidden when no sessions exist. */
.session-list-batchbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 14px;
  border-bottom: 1px solid var(--td-component-border);
  background: var(--td-bg-color-secondarycontainer);
  font-size: 12px;
}

.session-list-body {
  flex: 1;
  overflow-y: auto;
  padding: 4px 0;
}

.session-empty {
  padding: 32px 16px;
  text-align: center;
  color: var(--td-text-color-placeholder);
  font-size: 13px;
}

.session-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 10px 14px;
  cursor: pointer;
  transition: background-color 0.15s ease;
  border-left: 2px solid transparent;
}

.session-item-checkbox {
  flex-shrink: 0;
  margin-top: 2px;
}

.session-item-content {
  flex: 1;
  min-width: 0;
}

.session-item:hover {
  background: var(--td-bg-color-container-hover);
}

.session-item.is-active {
  background: var(--td-brand-color-1);
  border-left-color: var(--td-brand-color);
}

.session-item-title {
  font-size: 13px;
  color: var(--td-text-color-primary);
  font-weight: 500;
  margin-bottom: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.session-item-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 11px;
  color: var(--td-text-color-placeholder);
}

.session-item-delete {
  display: inline-flex;
  align-items: center;
  padding: 2px;
  border-radius: 4px;
  color: var(--td-text-color-placeholder);
  transition: color 0.15s ease, background-color 0.15s ease;
}

.session-item-delete:hover {
  color: var(--td-error-color);
  background: var(--td-error-color-1);
}
</style>
