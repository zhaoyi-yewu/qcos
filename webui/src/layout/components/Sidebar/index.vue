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
  <div
    class="sidebar-inner"
    :class="{'has-logo':showLogo}"
    :style="sidebarWidthStyle"
  >
    <endpoint-switcher :collapse="isCollapse" />
    <logo v-if="showLogo" :collapse="isCollapse" />
    <el-scrollbar wrap-class="scrollbar-wrapper" class="sidebar-menu-scroll">
      <el-menu
        :default-active="activeMenu"
        :collapse="isCollapse"
        background-color="var(--qcos-menu-bg, #304156)"
        text-color="var(--qcos-menu-text, #bfcbd9)"
        hover-background-color="var(--qcos-menu-hover, #263445)"
        :unique-opened="false"
        active-text-color="var(--qcos-menu-active-text, #409EFF)"
        :collapse-transition="false"
        mode="vertical"
      >
        <sidebar-item v-for="menuRoute in routes" :key="menuRoute.path" :item="menuRoute" :base-path="menuRoute.path" />
      </el-menu>
    </el-scrollbar>
    <!-- theme picker pinned to the bottom of the sidebar -->
    <theme-picker :collapse="isCollapse" class="sidebar-theme-picker" />

  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import Logo from './Logo'
import EndpointSwitcher from './EndpointSwitcher.vue'
import SidebarItem from './SidebarItem'
import ThemePicker from '@/components/ThemePicker/index.vue'
import variables from '@/styles/variables.module.scss'
import { useAppStore } from '@/store/modules/app'
import { useSettingsStore } from '@/store/modules/settings'
import { useUserStore } from '@/store/modules/user'

defineOptions({ name: 'SidebarMenu' })

const appStore = useAppStore()
const settingsStore = useSettingsStore()
const userStore = useUserStore()
const route = useRoute()
const router = useRouter()

const { sidebar } = storeToRefs(appStore)
const { sidebarLogo } = storeToRefs(settingsStore)
const { isAdmin } = storeToRefs(userStore)

// recursively filter routes by whether the user is admin
// routes without meta.roles are visible to everyone; routes with meta.roles
// require admin privileges when they include 'admin'
function filterRoutesByAdmin(routeList, isAdminUser) {
  const result = []
  for (const r of routeList) {
    const required = r.meta && r.meta.roles
    const visible = !required || required.length === 0 || (required.includes('admin') && isAdminUser)
    if (!visible) continue
    const copy = { ...r }
    if (copy.children && copy.children.length > 0) {
      copy.children = filterRoutesByAdmin(copy.children, isAdminUser)
    }
    result.push(copy)
  }
  return result
}

// cache the raw routes reference once so we don't re-read router.options on
// every render; the raw list is static for the lifetime of the app
const rawRoutes = router.options.routes

// pre-compute both admin and non-admin route arrays ONCE so the el-menu
// receives STABLE array references across renders; recreating them on every
// evaluation causes unstable vnodes which leads to "node is null" errors
const adminRoutes = filterRoutesByAdmin(rawRoutes, true)
const nonAdminRoutes = filterRoutesByAdmin(rawRoutes, false)

const routes = ref(isAdmin.value ? adminRoutes : nonAdminRoutes)

watch(isAdmin, (newVal) => {
  routes.value = newVal ? adminRoutes : nonAdminRoutes
})
const activeMenu = computed(() => {
  const { meta, path } = route
  if (meta.activeMenu) {
    return meta.activeMenu
  }
  return path
})
const showLogo = computed(() => sidebarLogo.value)
const isCollapse = computed(() => !sidebar.value.opened)

// user-resizable sidebar width: applied as an inline style so it
// overrides the static $sideBarWidth from sidebar.scss. When the sidebar
// is collapsed we fall back to the store default; the global
// .hideSidebar rules already force width:0 via display:none.
const sidebarWidthStyle = computed(() => {
  if (isCollapse.value) return {}
  const w = sidebar.value.width
  return w ? { width: `${w}px` } : {}
})
</script>

<style scoped>
/* the root div doubles as .sidebar-container (the layout merges
   class="sidebar-container" onto it); make it a fixed-position flex
   column so the theme picker can be pinned to the bottom while the
   menu fills the remaining space. We duplicate the layout-critical
   properties from sidebar.scss here so the component works even if
   the global stylesheet fails to load or is overridden. */
.sidebar-inner {
  display: flex;
  flex-direction: column;
  height: 100%;
}

/* :deep is required because el-scrollbar renders its own root element;
   scoped CSS would not reach it otherwise. flex:1 with min-height:0
   lets the menu fill the remaining space between logo and theme picker.
   NOTE: do NOT set height here; element-plus's own CSS keeps the inner
   .el-scrollbar__wrap at 100%, which is what actually scrolls. */
.sidebar-inner :deep(.sidebar-menu-scroll) {
  flex: 1 1 0;
  min-height: 0;
}

.sidebar-theme-picker {
  flex-shrink: 0;
}

</style>

