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
  <div :class="classObj" class="app-wrapper">
    <div v-if="device==='mobile'&&sidebar.opened" class="drawer-bg" @click="handleClickOutside" />
    <!--
      sidebar is in normal document flow (NOT position:fixed) so it sits
      side-by-side with .main-container instead of floating above it.
      .app-wrapper is a flex row: sidebar has a fixed width, main-container
      flexes to fill the remaining space. See the scoped styles below.
    -->
    <Sidebar class="sidebar-container" />
    <div class="main-container">
      <div :class="{'fixed-header':fixedHeader}">
        <navbar />
      </div>
      <app-main />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { storeToRefs } from 'pinia'
import { Navbar, Sidebar, AppMain } from './components'
import ResizeHandler from './mixin/ResizeHandler'
import { useAppStore } from '@/store/modules/app'
import { useSettingsStore } from '@/store/modules/settings'

defineOptions({ name: 'LayoutIndex' })

const appStore = useAppStore()
const settingsStore = useSettingsStore()

const { sidebar: sidebarState, device } = storeToRefs(appStore)
const { fixedHeader } = storeToRefs(settingsStore)

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

  .fixed-header {
    position: fixed;
    top: 0;
    right: 0;
    z-index: 9;
    width: calc(100% - #{$sideBarWidth});
    transition: width 0.28s;
  }

  .hideSidebar .fixed-header {
    width: calc(100% - 54px)
  }

  .mobile .fixed-header {
    width: 100%;
  }
</style>
