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
  <div class="refresh-interval">
    <span class="interval-label">刷新间隔</span>
    <el-dropdown trigger="click" @command="handleIntervalChange" @visible-change="onDropdownVisibleChange">
      <el-button size="small" class="interval-btn">
        {{ currentLabel }}
        <span class="dropdown-arrow" />
      </el-button>
      <template #dropdown>
        <el-dropdown-menu>
          <el-dropdown-item
            v-for="opt in intervalOptions"
            :key="opt.value"
            :command="opt.value"
            :class="{ 'is-active': opt.value === selectedInterval }"
          >
            {{ opt.label }}
          </el-dropdown-item>
          <!-- divider before custom input -->
          <div class="custom-divider" />
          <div class="custom-input-wrapper" @click.stop>
            <span class="custom-label">自定义(秒)</span>
            <el-input-number
              v-model="customSeconds"
              :min="1"
              :max="86400"
              :step="1"
              :precision="0"
              size="small"
              controls-position="right"
              class="custom-input"
              @keyup.enter="applyCustomInterval"
            />
            <el-button
              size="small"
              type="primary"
              @click="applyCustomInterval"
            >
              应用
            </el-button>
          </div>
        </el-dropdown-menu>
      </template>
    </el-dropdown>
    <el-button
      :icon="refreshing ? Loading : Refresh"
      size="small"
      circle
      :class="{ 'is-refreshing': refreshing }"
      @click="handleManualRefresh"
    />
  </div>
</template>

<script>
import { markRaw } from 'vue'
import { Refresh, Loading } from '@element-plus/icons-vue'

// refresh interval options (Grafana-style)
const INTERVAL_OPTIONS = [
  { value: 0, label: '关闭' },
  { value: 5, label: '5秒' },
  { value: 10, label: '10秒' },
  { value: 30, label: '30秒' },
  { value: 60, label: '1分钟' },
  { value: 300, label: '5分钟' }
]

export default {
  name: 'RefreshInterval',
  props: {
    // default interval in seconds; 0 means off
    defaultInterval: {
      type: Number,
      default: 10
    },
    // whether a refresh is currently in progress
    refreshing: {
      type: Boolean,
      default: false
    }
  },
  emits: ['refresh', 'interval-change'],
  data() {
    return {
      Refresh: markRaw(Refresh),
      Loading: markRaw(Loading),
      selectedInterval: this.defaultInterval,
      customSeconds: 10,
      timer: null
    }
  },

  computed: {
    intervalOptions() {
      return INTERVAL_OPTIONS
    },
    currentLabel() {
      // check if it matches a preset option
      const opt = INTERVAL_OPTIONS.find(o => o.value === this.selectedInterval)
      if (opt) {
        return opt.label
      }
      // custom interval
      return `${this.selectedInterval}秒`
    }
  },

  mounted() {
    this.startTimer()
  },

  beforeUnmount() {
    this.stopTimer()
  },

  methods: {
    handleManualRefresh() {
      this.$emit('refresh')
    },

    handleIntervalChange(value) {
      this.selectedInterval = value
      this.stopTimer()
      this.startTimer()
      this.$emit('interval-change', value)
    },

    // apply custom interval from input -- el-input-number ensures integer
    applyCustomInterval() {
      if (!this.customSeconds || this.customSeconds < 1) {
        this.$message.warning('请输入大于 0 的整数秒数')
        return
      }
      // ensure integer
      const seconds = Math.floor(this.customSeconds)
      this.selectedInterval = seconds
      this.stopTimer()
      this.startTimer()
      this.$emit('interval-change', seconds)
    },

    onDropdownVisibleChange(visible) {
      // sync customSeconds with current selectedInterval when dropdown opens
      if (visible && this.selectedInterval > 0) {
        this.customSeconds = this.selectedInterval
      }
    },

    startTimer() {
      if (this.selectedInterval > 0) {
        this.timer = setInterval(() => {
          this.$emit('refresh')
        }, this.selectedInterval * 1000)
      }
    },

    stopTimer() {
      if (this.timer) {
        clearInterval(this.timer)
        this.timer = null
      }
    }
  }
}
</script>

<style scoped>
.refresh-interval {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.interval-label {
  font-size: 13px;
  color: #606266;
  white-space: nowrap;
}

.interval-btn {
  font-size: 13px;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

/* CSS triangle dropdown indicator (downward arrow) */
.dropdown-arrow {
  display: inline-block;
  width: 0;
  height: 0;
  border-left: 4px solid transparent;
  border-right: 4px solid transparent;
  border-top: 5px solid #909399;
  margin-left: 4px;
  vertical-align: middle;
  transition: border-top-color 0.2s;
}

.interval-btn:hover .dropdown-arrow {
  border-top-color: #409eff;
}

:deep(.is-active) {
  color: #409eff;
  font-weight: 600;
}

.custom-divider {
  height: 1px;
  background: #ebeef5;
  margin: 6px 0;
}

.custom-input-wrapper {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  white-space: nowrap;
}

.custom-label {
  font-size: 13px;
  color: #606266;
  white-space: nowrap;
}

.custom-input {
  width: 120px;
}
.is-refreshing {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
</style>
