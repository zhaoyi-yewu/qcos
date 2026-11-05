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
  <t-tooltip
    :content="enabled ? 'AI 助手 (Ctrl+/)' : '功能未开启'"
    placement="bottom"
    :show-after="200"
  >
    <span
      class="ai-agent-button"
      :class="{ 'is-disabled': !enabled }"
      @click="onClick"
    >
      <svg-icon icon-class="ai-robot" class="ai-agent-icon" />
    </span>
  </t-tooltip>
</template>

<script setup>
import { computed } from 'vue'
import { ElMessage } from 'element-plus'
import { useAiAgentStore } from '@/store/modules/aiAgent'
import { useComponentsStore } from '@/store/modules/components'

defineOptions({ name: 'AiAgentButton' })

const store = useAiAgentStore()
const componentsStore = useComponentsStore()

const enabled = computed(() => componentsStore.aiAgentEnabled)

function onClick() {
  if (!enabled.value) {
    ElMessage.warning('AI 助手功能未开启')
    return
  }
  store.open()
}
</script>

<style lang="scss" scoped>
/*
 * Icon button shown in the top Navbar next to the terminal launcher.
 * Sized and colored to match the existing navbar icon buttons
 * (hamburger / collapse toggle) so the right-menu icon row reads
 * as one consistent toolbar.
 */
.ai-agent-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  padding: 0;
  cursor: pointer;
  border-radius: 4px;
  color: var(--td-text-color-secondary, #5a5e66);
  transition: background 0.2s, color 0.2s;

  &:hover {
    background: var(--td-bg-color-container-hover, rgba(0, 0, 0, 0.04));
    color: var(--td-brand-color);
  }

  /*
   * svg-icon's scoped stylesheet pins it to 1em x 1em; use :deep() to
   * set an explicit rendered size that fills the button.
   */
  :deep(.ai-agent-icon) {
    font-size: 22px;
    width: 22px;
    height: 22px;
  }
}
</style>
