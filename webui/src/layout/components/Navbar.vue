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
  <div class="navbar">
    <el-tooltip
      :content="sidebar.opened ? '折叠侧边栏' : '展开侧边栏'"
      placement="right"
      :show-after="200"
      popper-class="navbar-hamburger-tooltip"
    >
      <template #default>
        <span class="hamburger-tooltip-wrapper">
          <hamburger :is-active="sidebar.opened" class="hamburger-container" @toggle-click="toggleSideBar" />
        </span>
      </template>
    </el-tooltip>

    <breadcrumb class="breadcrumb-container" />

    <div class="right-menu">
      <!-- terminal launcher, moved here from the sidebar endpoint switcher -->
      <terminal-button class="right-menu-icon navbar-terminal-btn" tooltip-placement="bottom" />
      <!-- AI agent entry: placeholder that shows a "coming soon" message -->
      <ai-agent-button class="right-menu-icon" />
      <el-tooltip
        :content="navbarCollapsed ? '展开导航栏' : '向上折叠导航栏'"
        placement="bottom"
        :show-after="200"
      >
        <el-icon class="navbar-collapse-btn" @click="toggleNavbar">
          <ArrowDown v-if="navbarCollapsed" />
          <ArrowUp v-else />
        </el-icon>
      </el-tooltip>
      <el-dropdown class="avatar-container" trigger="click">
        <div class="avatar-wrapper">
          <el-tooltip :content="name || '未登录'" placement="bottom" effect="dark">
            <!-- use the local default avatar as fallback when the store has
                 none (e.g. before login info loads); the onerror handler
                 guards against a broken/missing avatar URL -->
            <img
              :src="avatar || defaultAvatar"
              class="user-avatar"
              @error="e => e.target.src = defaultAvatar"
            >
          </el-tooltip>
          <el-icon><ArrowDown /></el-icon>
        </div>
        <template #dropdown>
          <el-dropdown-menu class="user-dropdown">
            <router-link to="/">
              <el-dropdown-item>
                首页
              </el-dropdown-item>
            </router-link>
            <el-dropdown-item @click="goToProfile">
              用户信息
            </el-dropdown-item>
            <el-dropdown-item divided @click="logout">
              <span style="display:block;">退出登录</span>
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </div>
</template>

<script setup>
import { storeToRefs } from 'pinia'
import { useRouter, useRoute } from 'vue-router'
import { ArrowDown, ArrowUp } from '@element-plus/icons-vue'
import Breadcrumb from '@/components/Breadcrumb'
import Hamburger from '@/components/Hamburger'
import TerminalButton from '@/components/Terminal/TerminalButton.vue'
import AiAgentButton from '@/components/AiAgent/AiAgentButton.vue'
import { useAppStore } from '@/store/modules/app'
import { useUserStore } from '@/store/modules/user'
import { useSettingsStore } from '@/store/modules/settings'

defineOptions({ name: 'NavbarHeader' })
import defaultAvatar from '@/assets/avatar/default_avatar.png'

const appStore = useAppStore()
const userStore = useUserStore()
const settingsStore = useSettingsStore()
const router = useRouter()
const route = useRoute()

const { sidebar } = storeToRefs(appStore)
const { avatar, name } = storeToRefs(userStore)
const { navbarCollapsed } = storeToRefs(settingsStore)

function toggleSideBar() {
  appStore.toggleSideBar()
}

function toggleNavbar() {
  settingsStore.toggleNavbarCollapsed()
}

function goToProfile() {
  router.push('/user-settings/profile')
}

async function logout() {
  // delegate to userStore.logout which clears token cookie, in-memory state,
  // localStorage app keys, sessionStorage, and calls backend logout API
  await userStore.logout().catch(() => {})
  // redirect to login page after state is cleared
  router.push(`/login?redirect=${route.fullPath}`)
}
</script>

<style lang="scss" scoped>
.navbar {
  height: 50px;
  overflow: hidden;
  position: relative;
  background: #fff;
  box-shadow: 0 1px 4px rgba(0,21,41,.08);

  /*
   * The tooltip reference wrapper must be inline-block (and match the
   * hamburger's box) so Element Plus measures the trigger element's
   * bounding rect correctly. With the default inline display the popper
   * is anchored to the text baseline and appears offset from the icon.
   */
  .hamburger-tooltip-wrapper {
    display: inline-block;
    height: 50px;
    line-height: 50px;
    float: left;
  }

  .hamburger-container {
    line-height: 46px;
    height: 100%;
    float: none;
    display: inline-flex;
    align-items: center;
    cursor: pointer;
    transition: background .3s;
    -webkit-tap-highlight-color:transparent;

    &:hover {
      background: rgba(0, 0, 0, .025)
    }
  }

  .breadcrumb-container {
    float: left;
  }

  .right-menu {
    float: right;
    height: 100%;
    /*
     * Flex row so the icon buttons are vertically centered on the 50px
     * navbar line, matching the visual midline of the 14px breadcrumb
     * text ("首页" etc.) which is centered by its line-height: 50px.
     * The previous `line-height: 50px` + `vertical-align: middle` combo
     * aligned icons to the inline strut's x-height center instead of the
     * true line center, leaving them a few pixels lower than the text.
     */
    display: flex;
    align-items: center;
    line-height: 50px;

    &:focus {
      outline: none;
    }

    .right-menu-item {
      display: inline-block;
      padding: 0 8px;
      height: 100%;
      font-size: 18px;
      color: #5a5e66;
      vertical-align: text-bottom;

      &.hover-effect {
        cursor: pointer;
        transition: background .3s;

        &:hover {
          background: rgba(0, 0, 0, .025)
        }
      }
    }

    // icon buttons pinned in the right-menu (terminal, AI agent, ...);
    // the wider right margin pulls the whole icon group towards the left,
    // away from the avatar dropdown
    .right-menu-icon {
      margin-right: 16px;
    }

    /*
     * TerminalButton was styled for the dark sidebar palette; override its
     * CSS variables so it blends with the light navbar background and
     * matches the neighboring icon buttons.
     */
    .navbar-terminal-btn {
      :deep(.terminal-button) {
        border: none;
        color: var(--el-text-color-regular, #5a5e66);
        background-color: transparent;

        &:hover {
          color: var(--el-color-primary);
          border-color: transparent;
          background-color: var(--el-fill-color-light, rgba(0, 0, 0, 0.04));
        }

        /*
         * Same rendered glyph size as the AI agent button (16px inside a
         * 26px square) so the two icons read as a matched pair.
         */
        .terminal-icon {
          font-size: 16px;
          width: 16px;
          height: 16px;
        }
      }
    }

    // navbar collapse toggle button (向上折叠 / 展开)
    .navbar-collapse-btn {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 32px;
      height: 32px;
      margin-right: 8px;
      font-size: 16px;
      cursor: pointer;
      border-radius: 4px;
      color: var(--el-text-color-regular);
      transition: background 0.2s, color 0.2s;

      &:hover {
        background: var(--el-fill-color-light);
        color: var(--el-color-primary);
      }
    }

    .avatar-container {
      margin-right: 40px;

      .avatar-wrapper {
        /*
         * No margin-top here: the right-menu is a flex row with
         * align-items: center, so the 40px avatar wrapper is already
         * centered on the 50px navbar line. A top margin would push it
         * off-center.
         */
        position: relative;

        .user-avatar {
          cursor: pointer;
          width: 40px;
          height: 40px;
          border-radius: 10px;
        }

        .el-icon-caret-bottom {
          cursor: pointer;
          position: absolute;
          right: -20px;
          top: 25px;
          font-size: 12px;
        }
      }
    }
  }
}
</style>

<!--
  Global (non-scoped) overrides for the hamburger tooltip popper.
  `popper-class="navbar-hamburger-tooltip"` renders outside the scoped
  tree, so its offset cannot be tuned from the scoped block above.
  Pull the popper a few pixels toward the trigger so it hugs the button
  instead of floating with the default 12px gap.
-->
<style lang="scss">
.navbar-hamburger-tooltip.el-popper.is-light {
  margin-left: -4px;
}
</style>
