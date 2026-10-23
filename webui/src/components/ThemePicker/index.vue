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
  <div class="theme-picker" :class="{ collapsed: collapse }">
    <el-popover
      v-model:visible="popoverVisible"
      placement="top-start"
      trigger="click"
      :width="240"
      popper-class="theme-picker-popover"
    >
      <template #reference>
        <div class="theme-picker-trigger">
          <el-icon class="theme-picker-trigger-icon sub-el-icon">
            <Sunny v-if="colorMode === 'light'" />
            <Moon v-else />
          </el-icon>
          <span v-if="!collapse" class="theme-picker-label">
            主题：{{ colorMode === 'light' ? '白天' : '夜晚' }}
          </span>
          <el-icon v-if="!collapse" class="theme-picker-arrow">
            <ArrowUp />
          </el-icon>
        </div>
      </template>

      <div class="theme-picker-panel">
        <!-- color mode toggle -->
        <div class="theme-section">
          <div class="theme-section-title">外观模式</div>
          <div class="theme-mode-row">
            <button
              v-for="mode in colorModes"
              :key="mode.key"
              type="button"
              class="theme-mode-btn"
              :class="{ active: mode.key === colorMode }"
              @click="handleModeChange(mode.key)"
            >
              <el-icon>
                <Sunny v-if="mode.key === 'light'" />
                <Moon v-else />
              </el-icon>
              <span>{{ mode.label }}</span>
            </button>
          </div>
        </div>

        <!-- primary color -->
        <div class="theme-section">
          <div class="theme-section-title">主题色</div>
          <div class="theme-color-row">
            <button
              v-for="preset in presets"
              :key="preset.key"
              type="button"
              class="theme-color-btn"
              :class="{ active: preset.key === currentTheme }"
              :style="{ backgroundColor: preset.color }"
              :title="preset.label"
              @click="handleColorChange(preset.key)"
            >
              <el-icon v-if="preset.key === currentTheme" class="check-icon">
                <Check />
              </el-icon>
            </button>
          </div>
        </div>
      </div>
    </el-popover>
  </div>
</template>

<script>
import { ArrowUp, Check, Moon, Sunny } from '@element-plus/icons-vue'
import { storeToRefs } from 'pinia'
import { useSettingsStore } from '@/store/modules/settings'
import { COLOR_MODES, THEME_PRESETS } from '@/utils/theme'

export default {
  name: 'ThemePicker',
  components: { ArrowUp, Check, Moon, Sunny },
  props: {
    // when the sidebar is collapsed only the icon is shown
    collapse: {
      type: Boolean,
      default: false
    }
  },
  setup() {
    const settingsStore = useSettingsStore()
    const { theme, colorMode } = storeToRefs(settingsStore)
    return { settingsStore, theme, colorMode }
  },
  data() {
    return {
      popoverVisible: false,
      presets: THEME_PRESETS,
      colorModes: COLOR_MODES
    }
  },
  computed: {
    currentTheme() {
      return this.theme
    }
  },
  methods: {
    handleModeChange(mode) {
      this.settingsStore.setColorMode(mode)
    },
    handleColorChange(key) {
      this.settingsStore.setTheme(key)
    }
  }
}
</script>

<style scoped>
.theme-picker {
  padding: 8px 12px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}

.theme-picker.collapsed {
  padding: 8px 0;
  display: flex;
  justify-content: center;
}

.theme-picker-trigger {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  color: #bfcbd9;
  font-size: 13px;
  padding: 6px;
  border-radius: 4px;
  transition: background 0.2s, color 0.2s;
  outline: none;
}

.theme-picker.collapsed .theme-picker-trigger {
  padding: 6px;
}

.theme-picker-trigger:hover {
  background: rgba(255, 255, 255, 0.08);
  color: #ffffff;
}

/* match the sidebar menu item icon style (1em, currentColor) */
.theme-picker-trigger-icon {
  width: 1em;
  height: 1em;
  font-size: 18px;
  color: currentColor;
  flex-shrink: 0;
  vertical-align: middle;
}

.theme-picker-label {
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.theme-picker-arrow {
  font-size: 12px;
  color: #909399;
}

/* popover panel layout */
.theme-picker-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.theme-section-title {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-bottom: 6px;
}

/* color mode buttons */
.theme-mode-row {
  display: flex;
  gap: 8px;
}

.theme-mode-btn {
  flex: 1;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  padding: 6px 0;
  font-size: 13px;
  color: var(--el-text-color-regular);
  background: var(--el-fill-color-light);
  border: 1px solid var(--el-border-color);
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
}

.theme-mode-btn:hover {
  border-color: var(--el-color-primary);
  color: var(--el-color-primary);
}

.theme-mode-btn.active {
  background: var(--el-color-primary);
  border-color: var(--el-color-primary);
  color: #ffffff;
}

/* color swatches */
.theme-color-row {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.theme-color-btn {
  width: 24px;
  height: 24px;
  border-radius: 4px;
  border: 1px solid rgba(0, 0, 0, 0.1);
  cursor: pointer;
  padding: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: transform 0.15s, box-shadow 0.15s;
}

.theme-color-btn:hover {
  transform: scale(1.1);
}

.theme-color-btn.active {
  box-shadow: 0 0 0 2px var(--el-bg-color), 0 0 0 4px currentColor;
}

.theme-color-btn .check-icon {
  color: #ffffff;
  font-size: 14px;
}
</style>
