，<!--
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
  <div class="endpoint-switcher" :class="{ collapse }">
    <div v-if="!collapse" class="endpoint-label">当前系统</div>
    <el-select
      v-model="activeName"
      :size="collapse ? 'small' : 'default'"
      class="endpoint-select"
      :class="{ 'is-collapse': collapse }"
      popper-class="endpoint-switcher-popper"
      @change="onChange"
    >
      <template v-if="activeStatus" #prefix>
        <span
          class="endpoint-state-dot"
          :class="'state-' + activeStatus"
          :title="activeStatus"
        />
      </template>
      <el-option
        v-for="ep in endpointOptions"
        :key="ep.name"
        :value="ep.name"
        :label="ep.alias || ep.name"
        :disabled="ep.usable === false"
        :title="ep.status === 'ok' ? `平台版本: ${ep.platformVersion}\n版本: ${ep.version}\n系统状态: 可用` : ep.status === 'fail' ? `错误: ${ep.error}` : '探测中…'"
      >
        <div class="endpoint-option">
          <span
            class="endpoint-state-dot"
            :class="'state-' + (ep.status || 'probing')"
            :title="ep.status || 'probing'"
          />
          <span class="endpoint-option-alias">{{ ep.alias || ep.name }}</span>
          <span class="endpoint-option-meta">
            <template v-if="ep.status === 'probing'">
              <el-icon class="is-loading"><Loading /></el-icon>
            </template>
            <template v-else-if="ep.status === 'ok'">
              <span class="endpoint-option-version">v{{ ep.version }}</span>
            </template>
          </span>
        </div>
      </el-option>
    </el-select>
  </div>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Loading } from '@element-plus/icons-vue'
import { useConfigStore } from '@/store/modules/config'
import { useUserStore } from '@/store/modules/user'
import { removeSession } from '@/utils/session'

defineOptions({ name: 'EndpointSwitcher' })

const props = defineProps({
  collapse: {
    type: Boolean,
    default: false
  }
})

const cfg = useConfigStore()
const userStore = useUserStore()
const route = useRoute()
const router = useRouter()

const activeName = ref(cfg.activeEndpointName)

const endpointOptions = computed(() => cfg.endpoints.map(ep => {
  const h = cfg.healthMap[ep.name] || {}
  return {
    ...ep,
    status: h.status || 'probing',
    version: h.version || '',
    platformVersion: h.platformVersion || '',
    error: h.error || '',
    usable: h.status === 'ok'
  }
}))

// status of the currently active endpoint, used to render the leading
// status dot inside the select input (prefix slot); empty string when no
// endpoint is selected or its health has not been probed yet
const activeStatus = computed(() => {
  const h = cfg.healthMap[cfg.activeEndpointName]
  return (h && h.status) || ''
})

onMounted(() => {
  // refresh health status when the sidebar mounts
  cfg.probeAll()
})

async function onChange(name) {
  if (name === cfg.activeEndpointName) return
  // ensure health info is up-to-date before switching
  const health = await cfg.probeEndpoint(name)
  if (!health || health.status !== 'ok') {
    ElMessage.warning(`endpoint ${name} 当前不可用，无法切换`)
    activeName.value = cfg.activeEndpointName
    return
  }
  cfg.setActive(name)

  // check if auth mode is "no" for the new endpoint; if so, treat as authenticated
  const authMode = String(health.authMode || '').toLowerCase().trim()
  if (authMode === 'no') {
    userStore.noAuthLogin()
    location.reload()
    return
  }

  // jwt (or other auth modes): restore the persisted session and verify
  // the token is still accepted by the backend before reloading the page.
  // Without this verification step, an expired/invalid token would only be
  // detected by the route guard after a full reload, forcing the user to
  // log in again even though a re-login is unavoidable anyway.
  const hasSession = userStore.loadSessionForActiveEndpoint()
  if (!hasSession) {
    router.push({ path: '/login', query: { redirect: route.fullPath, endpoint: name }})
    return
  }
  try {
    // validate the restored token against the new endpoint; on success the
    // userStore is refreshed with the latest profile and we can reload so
    // every view fetches data against the new endpoint
    await userStore.getInfo()
    location.reload()
  } catch (e) {
    // token no longer valid on the target endpoint: drop the stored session
    // so the login page does not loop, then send the user to re-authenticate
    removeSession(name)
    userStore.resetToken()
    ElMessage.warning(`endpoint ${name} 登录态已失效，请重新登录`)
    router.push({ path: '/login', query: { redirect: route.fullPath, endpoint: name }})
  }
}
</script>

<style lang="scss" scoped>
.endpoint-switcher {
  padding: 8px 10px;
  // Follow the sidebar color-mode-aware background. The
  // --qcos-sub-menu-bg variable is set by utils/theme.js for both
  // light and dark color modes (and by applyTheme() for non-default
  // primary presets), so this block blends seamlessly with the rest
  // of the sidebar.
  background: var(--qcos-sub-menu-bg, #1f2d3d);
  border-bottom: 1px solid var(--el-border-color-lighter, rgba(255, 255, 255, 0.06));
  display: flex;
  align-items: center;
  gap: 8px;

  &.collapse {
    padding: 6px 4px;
    justify-content: center;
  }
}

.endpoint-label {
  font-size: 12px;
  font-weight: 600;
  // Use the same color as regular sidebar menu text so the label is
  // legible in both light (#303133 on #f0f2f5) and dark (rgba(255,255,255,0.65)
  // on #1f2d3d) sidebars.
  color: var(--qcos-menu-text, rgba(255, 255, 255, 0.65));
  white-space: nowrap;
  flex-shrink: 0;
}

.endpoint-select {
  flex: 1;
  min-width: 0;

  &.is-collapse {
    :deep(.el-select__wrapper) {
      padding: 4px 6px;
      min-height: 28px;
    }
  }

  :deep(.el-select__wrapper) {
    // Subtle hover-ish background that works in both light and dark
    // sidebar palettes: use the menu-hover variable at low opacity via
    // color-mix. Fallback to a translucent white for legacy.
    background: var(--qcos-menu-hover, rgba(255, 255, 255, 0.08));
    box-shadow: none;
    border: 1px solid var(--el-border-color-lighter, rgba(255, 255, 255, 0.12));
    color: var(--qcos-menu-text, #fff);
    font-size: 12px;

    .el-select__placeholder {
      color: var(--qcos-menu-text, rgba(255, 255, 255, 0.5));
      opacity: 0.6;
      font-size: 12px;
    }

    .el-select__selected-item {
      color: var(--qcos-menu-text, #fff);
      font-size: 12px;
    }
  }
}

.endpoint-option {
  display: flex;
  align-items: center;
  width: 100%;
  gap: 8px;
}

.endpoint-option-alias {
  font-weight: 500;
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.endpoint-option-meta {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  margin-left: auto;
}

.endpoint-option-version {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

/* status dot: color reflects the endpoint health status */
.endpoint-state-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
  background: var(--el-color-info);
}

.endpoint-state-dot.state-ok {
  background: var(--el-color-success);
}

.endpoint-state-dot.state-fail {
  background: var(--el-color-danger);
}

.endpoint-state-dot.state-probing {
  background: var(--el-color-info);
}
</style>
