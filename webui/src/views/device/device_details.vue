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
  <div v-if="loaded" class="device-detail-container">
    <div class="header">
      <h2>设备详情</h2>
    </div>
    <div class="detail-container">
      <el-card class="device-card">
        <div class="device-header">
          <h2>{{ deviceDetails.name || '未命名' }} ({{ deviceDetails.alias_name || '无别名' }})</h2>
          <el-tag
            :type="getDeviceStatusTagType(deviceDetails.status)"
            class="status-tag"
          >
            {{ getDeviceStatusDisplay(deviceDetails.status, deviceDetails.is_manual) }}
          </el-tag>
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
import { getDevice } from '@/api/device'
import { getDriver } from '@/api/driver'
import {
  getEnable,
  getResultsFetchMode,
  getStatus,
  getDeviceStatusDisplay,
  getDeviceStatusTagType
} from '@/common/library'
import { queryVersion } from '@/api/version'

export default {
  name: 'DeviceDetails',
  data() {
    return {
      loaded: false,
      versionData: {
        version: '',
        api_version: '',
        supported_api_versions: [],
        platform_version: '',
        capabilities: {}
      },
      deviceName: this.$route.params.deviceName,
      driverDetails: {
        name: '',
        alias_name: '',
        version: '',
        description: '',
        tech_type: '',
        max_qubits: '',
        enable_transpiler: '',
        transpiler: '',
        supported_transpilers: '',
        enable_circuit_aggregation: '',
        supported_code_types: '',
        supported_basis_gates: '',
        results_fetch_mode: ''
      },
      deviceDetails: {
        name: '',
        alias_name: '',
        description: '',
        driver_name: '',
        enable: '',
        status: '',
        configs: ''
      },
      leftItems: [],
      rightItems: []
    }
  },
  watch: {
    '$route.params.deviceName'(newVal) {
      if (newVal !== this.deviceName) {
        this.deviceName = newVal
        this.fetchDeviceDetails()
      }
    }
  },
  created() {
    this.queryData()
  },
  methods: {
    getStatus,
    getDeviceStatusDisplay,
    getDeviceStatusTagType,
    async queryData() {
      await this.fetchVersion()
      await this.fetchDeviceDetails()
      await this.fetchDriverDetails()
      this.formatDeviceItems()
      this.loaded = true
    },

    async fetchVersion() {
      try {
        const response = await queryVersion()
        if (!response.error) {
          this.versionData = response.result
        } else {
          this.$message.error(`获取版本能力失败：${response.message || '未知错误'}`)
        }
      } catch (error) {
        console.error('获取版本能力失败:', error)
        this.$message.error('获取版本能力失败，请检查网络连接')
      }
    },

    async fetchDeviceDetails() {
      // 调用API获取设备详情
      try {
        const response = await getDevice(this.deviceName)
        if (!response.error) {
          this.deviceDetails = response.result
        } else {
          this.$message.error(`获取设备详情失败：${response.message || '未知错误'}`)
        }
      } catch (error) {
        console.error('获取设备详情失败:', error)
        this.$message.error('获取设备详情失败，请检查网络连接')
      }
    },

    async fetchDriverDetails() {
      // 调用API获取驱动详情
      try {
        const response = await getDriver(this.deviceDetails.driver_name)
        if (!response.error) {
          this.driverDetails = response.result
        } else {
          this.$message.error(`获取驱动详情失败：${response.message || '未知错误'}`)
        }
      } catch (error) {
        console.error('获取驱动详情失败:', error)
        this.$message.e
      }
    },

    formatDeviceItems() {
      // 左列信息
      this.leftItems = [
        { label: '设备名称', value: this.deviceDetails.name, color: '#409EFF' },
        { label: '驱动名称', value: this.deviceDetails.driver_name, color: '#409EFF' },
        { label: '驱动版本', value: this.driverDetails.version, color: '#409EFF' },
        { label: '启用', value: getEnable(this.deviceDetails.enable), color: '#409EFF' },
        { label: '状态', value: getDeviceStatusDisplay(this.deviceDetails.status, this.deviceDetails.is_manual), color: '#409EFF' },
        { label: '技术路线', value: this.versionData.capabilities['tech_types'][this.driverDetails.tech_type]['alias_name'], color: '#409EFF' },
        { label: '量子比特数', value: this.driverDetails.max_qubits, color: '#409EFF' },
        {
          label: '设备描述',
          value: this.deviceDetails.description || '未填写',
          color: '#409EFF'
        }
      ]

      // 右列信息
      let transpiler = '-'
      if (this.driverDetails.transpiler) {
        const caps = this.versionData && this.versionData.capabilities
        const transpilers = caps && caps.transpilers
        if (transpilers && transpilers[this.driverDetails.transpiler]) {
          transpiler = transpilers[this.driverDetails.transpiler].alias_name || this.driverDetails.transpiler
        } else {
          transpiler = this.driverDetails.transpiler
        }
      }
      this.rightItems = [
        { label: '默认转译器', value: transpiler, color: '#67C23A' },
        { label: '转译器开关', value: getEnable(this.driverDetails.enable_transpiler), color: '#67C23A' },
        { label: '支持的转译器', value: this.driverDetails.supported_transpilers, color: '#67C23A' },
        { label: '线路聚合开关', value: getEnable(this.driverDetails.enable_circuit_aggregation), color: '#67C23A' },
        { label: '支持的代码类型', value: this.driverDetails.supported_code_types, color: '#67C23A' },
        { label: '支持的基础量子门', value: this.driverDetails.supported_basis_gates, color: '#67C23A' },
        { label: '结果获取模式', value: getResultsFetchMode(this.driverDetails.results_fetch_mode), color: '#67C23A' },
        { label: '设备配置信息',
          value: JSON.stringify(this.deviceDetails.configs, null, 2),
          color: '#67C23A'
        }
      ]
    }
  }
}
</script>

<style scoped>
.device-detail-container {
  padding: 10px;
}

.header { margin: 0; }

.detail-container {
  background: var(--el-bg-color);
}

.device-card {
  box-shadow: 0 5px 12px rgba(0, 0, 0, 0.1);
  border-radius: 10px;
  overflow: hidden;
}

.device-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px;
  border-bottom: 1px solid #f0f0f0;
}

.status-tag {
  font-size: 14px;
  font-weight: bold;
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

.device-content h3 {
  margin-bottom: 15px;
  font-size: 16px;
}

:deep(.device-content pre ) {
  background-color: var(--el-fill-color-light);
  padding: 15px;
  border-radius: 5px;
  font-family: 'Courier New', Courier, monospace;
  color: #666a71;
  white-space: pre-wrap;
  word-wrap: break-word;
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
