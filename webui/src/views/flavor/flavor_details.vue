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
  <div v-if="loaded" class="flavor-detail-container">
    <div class="header">
      <h2>资源规格详情</h2>
    </div>
    <div class="detail-container">
      <el-card class="flavor-card">
        <div class="flavor-header">
          <h2>{{ flavorDetails.name || '未命名' }}</h2>
        </div>

        <div class="two-column-layout">
          <div class="left-column">
            <el-timeline>
              <el-timeline-item
                v-for="(item, index) in leftItems"
                :key="'left-' + index"
                :color="item.color"
                class="timeline-item"
              >
                <div class="timeline-label">{{ item.label }}</div>
                <div class="timeline-content">{{ item.value }}</div>
              </el-timeline-item>
            </el-timeline>
          </div>
          <div class="right-column">
            <el-timeline>
              <el-timeline-item
                v-for="(item, index) in rightItems"
                :key="'right-' + index"
                :color="item.color"
                class="timeline-item"
              >
                <div class="timeline-label">{{ item.label }}</div>
                <div class="timeline-content">{{ item.value }}</div>
              </el-timeline-item>
            </el-timeline>
          </div>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script>
import { getFlavor } from '@/api/flavor'

export default {
  name: 'FlavorDetails',
  data() {
    return {
      loaded: false,
      flavorId: this.$route.params.flavorId,
      flavorDetails: {},
      leftItems: [],
      rightItems: []
    }
  },
  watch: {
    '$route.params.flavorId'(newVal) {
      if (newVal !== this.flavorId) {
        this.flavorId = newVal
        this.fetchFlavorDetails()
      }
    }
  },
  created() {
    this.queryData()
  },

  methods: {
    async queryData() {
      await this.fetchFlavorDetails()
      this.formatFlavorItems()
      this.loaded = true
    },

    async fetchFlavorDetails() {
      try {
        const response = await getFlavor(this.flavorId)
        if (!response.error) {
          this.flavorDetails = response.result || {}
        } else {
          this.$message.error(`获取资源规格详情失败：${response.message || '未知错误'}`)
        }
      } catch (error) {
        console.error('获取资源规格详情失败:', error)
        this.$message.error('获取资源规格详情失败，请检查网络连接')
      }
    },

    formatFlavorItems() {
      const detail = this.flavorDetails

      // 左列信息
      this.leftItems = [
        { label: '规格ID', value: detail.id || '-', color: '#409EFF' },
        { label: '名称', value: detail.name || '-', color: '#409EFF' },
        { label: '项目ID', value: detail.project_id || '-', color: '#409EFF' },
        { label: '是否公开', value: detail.is_public ? '是' : '否', color: '#409EFF' },
        { label: '最小量子比特数', value: detail.min_qubits ?? '-', color: '#409EFF' },
        { label: '最大量子比特数', value: detail.max_qubits ?? '-', color: '#409EFF' },
        {
          label: '描述',
          value: detail.description || '未填写',
          color: '#409EFF'
        }
      ]

      // 右列信息
      this.rightItems = [
        { label: '单比特门保真度', value: detail.gate_fidelity_1q_min ?? '-', color: '#67C23A' },
        { label: '双比特门保真度', value: detail.gate_fidelity_2q_min ?? '-', color: '#67C23A' },
        { label: '设备组', value: this.formatDeviceGroups(detail.device_groups), color: '#67C23A' },
        {
          label: '额外属性',
          value: this.formatExtraProperties(detail.extra_properties),
          color: '#67C23A'
        },
        { label: '创建时间', value: detail.created_at || '-', color: '#67C23A' },
        { label: '更新时间', value: detail.updated_at || '-', color: '#67C23A' }
      ]
    },

    formatDeviceGroups(deviceGroups) {
      if (!deviceGroups || !Array.isArray(deviceGroups) || deviceGroups.length === 0) {
        return '-'
      }
      return deviceGroups.join(', ')
    },

    formatExtraProperties(extraProperties) {
      if (!extraProperties || Object.keys(extraProperties).length === 0) {
        return '-'
      }
      return JSON.stringify(extraProperties, null, 2)
    }
  }
}
</script>

<style scoped>
.flavor-detail-container {
  padding: 10px;
}

.header { margin: 0; }

.detail-container {
  background: var(--el-bg-color);
}

.flavor-card {
  box-shadow: 0 5px 12px rgba(0, 0, 0, 0.1);
  border-radius: 10px;
  overflow: hidden;
}

.flavor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px;
  border-bottom: 1px solid #f0f0f0;
}

.two-column-layout {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  padding: 0 20px 20px;
}

.timeline-item {
  padding: 10px 0;
}

.timeline-label {
  font-weight: bold;
  margin-bottom: 5px;
  color: var(--el-text-color-primary);
}

.timeline-content {
  white-space: pre-wrap;
  color: var(--el-text-color-regular);
  word-break: break-all;
}

:deep(.scrollable-content ) {
  width: 100%;
  max-height: 600px;
  overflow: auto;
  background-color: var(--el-fill-color-light);
  padding: 15px;
  border-radius: 5px;
  font-family: 'Courier New', Courier, monospace;
  color: #65676a;
  white-space: pre-wrap;
}
:deep(pre ) {
  margin: 0;
  white-space: pre-wrap;
}
</style>
