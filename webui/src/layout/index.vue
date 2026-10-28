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
  <div :class="classObj" class="app-wrapper" :style="sidebarWidthVarStyle">
    <div v-if="device==='mobile'&&sidebar.opened" class="drawer-bg" @click="handleClickOutside" />
    <!--
      sidebar is in normal document flow (NOT position:fixed) so it sits
      side-by-side with .main-container instead of floating above it.
      .app-wrapper is a flex row: sidebar has a fixed width, main-container
      flexes to fill the remaining space. See the scoped styles below.
    -->
    <Sidebar class="sidebar-container" />
    <div class="main-container" :class="{ 'navbar-collapsed': navbarCollapsed }">
      <div :class="{'fixed-header':fixedHeader, 'navbar-is-collapsed': navbarCollapsed}">
        <navbar />
      </div>
      <app-main />
      <!-- Floating expand button shown when navbar is collapsed -->
      <el-tooltip
        v-if="navbarCollapsed"
        content="展开导航栏"
        placement="left"
        :show-after="200"
      >
        <button
          type="button"
          class="navbar-expand-fab"
          aria-label="展开导航栏"
          @click="toggleNavbar"
        >
          <el-icon><ArrowDown /></el-icon>
        </button>
      </el-tooltip>
    </div>
    <div class="global-version-footer">QCOS管理界面版本: v{{ webuiVersion }}</div>

    <!--
      Floating collapse toggle pinned to the right edge of the sidebar,
      vertically centered on the viewport.

      Lives at the Layout level (NOT inside <Sidebar />) because the sidebar
      itself becomes display:none when collapsed - a button rendered inside
      the sidebar would be hidden along with it, leaving no way to expand.

      Icon semantics:
        - sidebar expanded  -> ArrowLeft  (click to collapse)
        - sidebar collapsed -> ArrowRight (click to expand)
    -->
    <el-tooltip
      :content="sidebarState.opened ? '折叠侧边栏' : '展开侧边栏'"
      placement="right"
      :show-after="200"
    >
      <button
        type="button"
        class="sidebar-edge-toggle"
        :class="{ 'is-collapsed': !sidebarState.opened }"
        :aria-label="sidebarState.opened ? '折叠侧边栏' : '展开侧边栏'"
        @click="toggleSideBar"
      >
        <el-icon class="sidebar-edge-toggle-icon">
          <ArrowLeft v-if="sidebarState.opened" />
          <ArrowRight v-else />
        </el-icon>
      </button>
    </el-tooltip>

    <!--
      Sidebar width drag handle. Rendered only when the sidebar is open on
      desktop; collapsed/mobile states hide it. The handle is positioned
      at the sidebar's right edge via the same --qcos-sidebar-width CSS
      variable that drives the sidebar's own width.
    -->
    <div
      v-if="sidebarState.opened && device==='desktop'"
      class="sidebar-width-handle"
      :style="sidebarWidthVarStyle"
      title="拖动调整侧边栏宽度"
      @mousedown="onSidebarWidthDragStart"
    />

    <!-- global singleton terminal dialog; lives outside <app-main> so it
         survives route changes and keeps its WebSocket session alive -->
    <terminal-dialog />
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount } from 'vue'
import { storeToRefs } from 'pinia'
import { ArrowLeft, ArrowRight, ArrowDown } from '@element-plus/icons-vue'
import { Navbar, Sidebar, AppMain } from './components'
import TerminalDialog from '@/components/Terminal/TerminalDialog.vue'
import ResizeHandler from './mixin/ResizeHandler'
import { useAppStore } from '@/store/modules/app'
import { useSettingsStore } from '@/store/modules/settings'
import { WEBUI_VERSION } from '@/version'

defineOptions({ name: 'LayoutIndex' })

const webuiVersion = WEBUI_VERSION

const appStore = useAppStore()
const settingsStore = useSettingsStore()

const { sidebar: sidebarState, device } = storeToRefs(appStore)
const { fixedHeader, navbarCollapsed } = storeToRefs(settingsStore)

function toggleNavbar() {
  settingsStore.toggleNavbarCollapsed()
}

const classObj = computed(() => {
  return {
    hideSidebar: !sidebarState.value.opened,
    openSidebar: sidebarState.value.opened,
    withoutAnimation: sidebarState.value.withoutAnimation,
    mobile: device.value === 'mobile'
  }
})

function handleClickOutside() {
  appStore.closeSideBar(false)
}

function toggleSideBar() {
  appStore.toggleSideBar()
}

// expose the current sidebar width to CSS so the fixed-header offset and
// the edge toggle can follow user-driven resizes without JS sync.
// The variable is set on the wrapper div and inherited by all children.
const sidebarWidthVarStyle = computed(() => {
  const w = sidebarState.value.width
  return w ? { '--qcos-sidebar-width': `${w}px` } : {}
})

// ---------- sidebar width drag ----------
let sidebarDragState = null

function onSidebarWidthDragStart(e) {
  e.preventDefault()
  sidebarDragState = {
    startX: e.clientX,
    originWidth: sidebarState.value.width || 245
  }
  window.addEventListener('mousemove', onSidebarWidthDragMove)
  window.addEventListener('mouseup', onSidebarWidthDragEnd, { once: true })
}

function onSidebarWidthDragMove(e) {
  if (!sidebarDragState) return
  const dx = e.clientX - sidebarDragState.startX
  appStore.setSidebarWidth(sidebarDragState.originWidth + dx)
}

function onSidebarWidthDragEnd() {
  sidebarDragState = null
  window.removeEventListener('mousemove', onSidebarWidthDragMove)
}

onBeforeUnmount(() => {
  if (sidebarDragState) {
    window.removeEventListener('mousemove', onSidebarWidthDragMove)
    sidebarDragState = null
  }
})

ResizeHandler()
</script>

<style lang="scss" scoped>
  @use "../styles/mixin.scss" as *;
  @use "../styles/variables.scss" as *;

  /* make the app wrapper a flex row so the sidebar and the main container
     sit side-by-side in normal document flow; the sidebar is a fixed-width
     column (width set in sidebar.scss) and the main container flexes to
     fill the remaining space. The sidebar no longer uses position:fixed. */
  .app-wrapper {
    display: flex;
    flex-direction: row;
    position: relative;
    height: 100%;
    width: 100%;
    &.mobile.openSidebar{
      position: fixed;
      top: 0;
    }
  }
  .drawer-bg {
    background: #000;
    opacity: 0.3;
    width: 100%;
    top: 0;
    height: 100%;
    position: absolute;
    z-index: 999;
  }

  /*
   * Use the runtime CSS variable --qcos-sidebar-width (set on .app-wrapper
   * via inline style) so the header width follows user-driven sidebar
   * resizes. The SCSS variable $sideBarWidth remains as the fallback when
   * the CSS variable is not set (e.g. very first paint before mount).
   */
  .fixed-header {
    position: fixed;
    top: 0;
    right: 0;
    z-index: 9;
    width: calc(100% - var(--qcos-sidebar-width, #{$sideBarWidth}));
    transition: width 0.28s;
  }

  .hideSidebar .fixed-header {
    width: calc(100% - 54px)
  }

  .mobile .fixed-header {
    width: 100%;
  }

  /* Collapsed navbar: slide the fixed header up out of view, but keep it
     in the DOM so the transition is smooth and the expand FAB can be
     clicked to bring it back. */
  .fixed-header.navbar-is-collapsed {
    transform: translateY(-100%);
    transition: transform 0.28s ease-in-out, width 0.28s;
  }

  /* When the navbar is collapsed, AppMain loses the 50px top padding. */
  .navbar-collapsed .fixed-header+.app-main,
  .navbar-collapsed .app-main {
    padding-top: 0;
  }

  /* Floating expand button, pinned to top-right of the main container. */
  .navbar-expand-fab {
    position: fixed;
    top: 4px;
    right: 8px;
    z-index: 1002;
    width: 28px;
    height: 22px;
    padding: 0;
    border: 1px solid var(--el-border-color);
    border-top: none;
    border-radius: 0 0 4px 4px;
    background: var(--el-bg-color);
    color: var(--el-text-color-regular);
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.08);
    transition: background 0.2s, color 0.2s;
  }

  .navbar-expand-fab:hover {
    background: var(--el-fill-color-light);
    color: var(--el-color-primary);
  }

  /*
   * Global version badge pinned to the bottom-right of every page.
   *
   * Auto right-aligned to the viewport's right edge regardless of sidebar
   * collapse state or window width, while `padding-right: 2em` keeps a
   * 2-CJK-character visual gap between the text and the screen edge.
   * `text-align:right` keeps the text flush against the padding box if
   * it ever wraps to two lines.
   */
  .global-version-footer {
    position: fixed;
    right: 0;
    bottom: 8px;
    padding-right: 2em;
    font-size: 12px;
    color: #909399;
    opacity: 0.75;
    pointer-events: none;
    user-select: none;
    z-index: 10;
    text-align: right;
  }

  /*
   * Floating collapse toggle pinned to the right edge of the sidebar,
   * vertically centered on the viewport. Uses position:fixed so it is always
   * reachable regardless of how far the main content is scrolled.
   *
   * The `left` offset tracks the sidebar's current width so the button sits
   * half-inside / half-outside the sidebar edge:
   *   - sidebar opened:    left = 245px - 10px (button straddles the edge)
   *   - sidebar collapsed: left = 0 (sidebar is display:none, so the button
   *     docks to the viewport's left edge and remains clickable to expand)
   *
   * The horizontal position is animated via `transition: left` so the button
   * slides together with the sidebar collapse/expand animation.
   */
  .sidebar-edge-toggle {
    position: fixed;
    top: 50%;
    left: calc(var(--qcos-sidebar-width, 245px) - 10px);
    transform: translateY(-50%);
    z-index: 1001;

    width: 20px;
    height: 36px;
    padding: 0;
    border: none;
    border-radius: 0 4px 4px 0;
    background: var(--qcos-menu-bg, #304156);
    color: #bfcbd9;
    cursor: pointer;

    display: inline-flex;
    align-items: center;
    justify-content: center;

    box-shadow: 1px 0 4px rgba(0, 0, 0, 0.15);
    transition:
      left 0.28s,
      background-color 0.2s,
      color 0.2s;
  }

  .sidebar-edge-toggle.is-collapsed {
    left: 0;
  }

  .sidebar-edge-toggle:hover,
  .sidebar-edge-toggle:focus-visible {
    background: var(--qcos-menu-active-text, #409eff);
    color: #fff;
    outline: none;
  }

  .sidebar-edge-toggle-icon {
    font-size: 12px;
  }

  /*
   * Drag handle that lets the user resize the sidebar by grabbing its
   * right edge. The handle sits on top of the boundary between sidebar
   * and main content; its left offset tracks the sidebar's current width
   * via the shared CSS variable. While the sidebar is collapsed the
   * handle is hidden (v-if in the template).
   */
  .sidebar-width-handle {
    position: fixed;
    top: 0;
    bottom: 0;
    left: calc(var(--qcos-sidebar-width, 245px) - 3px);
    width: 6px;
    z-index: 1000;
    cursor: col-resize;
    background: transparent;
    transition: background-color 0.15s;
  }

  .sidebar-width-handle:hover {
    background: rgba(64, 158, 255, 0.25);
  }

  .sidebar-width-handle:active {
    background: rgba(64, 158, 255, 0.45);
  }
</style>
