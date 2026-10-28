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
  <el-tooltip v-if="hasToken" content="打开终端" :placement="tooltipPlacement" :show-after="200">
    <span class="terminal-button" @click="onOpen">
      <svg-icon icon-class="terminal" class="terminal-icon" />
    </span>
  </el-tooltip>
</template>

<script setup>
import { computed } from 'vue'
import { useTerminalStore } from '@/store/modules/terminal'
import { getTerminalToken } from '@/api/terminal'

defineOptions({ name: 'TerminalButton' })

// allow the host layout to pick the tooltip direction; the sidebar host
// uses the default "right", the top navbar passes "bottom"
defineProps({
  tooltipPlacement: {
    type: String,
    default: 'right'
  }
})

const terminalStore = useTerminalStore()

const hasToken = computed(() => !!getTerminalToken())

function onOpen() {
  terminalStore.openDialog()
}
</script>

<style lang="scss" scoped>
/*
 * Compact icon button rendered inside the sidebar next to the endpoint
 * switcher ("当前系统" selector). The button is square so it aligns
 * vertically with the el-select control; its colors follow the
 * sidebar's color mode via the --qcos-menu-* CSS variables set by
 * utils/theme.js, so the button stays legible on both the light and
 * dark sidebar palettes.
 */
/*
 * The button is sized to match the el-select next to it (32px tall,
 * 1px border, 4px radius) so the pair reads as a single toolbar row.
 */
.terminal-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  padding: 0;
  flex-shrink: 0;
  cursor: pointer;
  color: var(--qcos-menu-text, rgba(255, 255, 255, 0.92));
  border: 1px solid var(--el-border-color-lighter, rgba(255, 255, 255, 0.12));
  border-radius: 4px;
  background-color: var(--qcos-menu-hover, rgba(255, 255, 255, 0.08));
  box-sizing: border-box;
  transition: border-color .3s, background-color .3s, color .3s;

  &:hover {
    color: var(--qcos-menu-active-text, #fff);
    border-color: var(--el-border-color, rgba(255, 255, 255, 0.3));
    // Slightly darker than the default hover background so the active
    // state stands out.
    background-color: var(--qcos-sub-menu-hover, rgba(255, 255, 255, 0.16));
  }

  /*
   * svg-icon's scoped stylesheet pins it to 1em x 1em, so the icon's
   * rendered size follows font-size on the parent. The :deep() selector
   * is required to pierce the child component's scoped boundary when we
   * want to set an explicit width/height.
   */
  :deep(.terminal-icon) {
    font-size: 20px;
    width: 20px;
    height: 20px;
  }
}
</style>
