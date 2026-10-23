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
  <div class="device-list-container">
    <div class="header">
      <h2>设备列表</h2>
    </div>
    <PageTable
      ref="pageTableRef"
      :fetch-data="fetchDevices"
      search-placeholder="全局搜索：设备名称 / 别名 / 驱动 / 状态 …"
      row-key="name"
    >
      <filterable-table-column
        prop="name"
        label="设备名称"
        fixed="left"
        class-name="center-column"
        sortable="custom"
      />
      <filterable-table-column
        prop="alias_name"
        label="设备别名"
        fixed="left"
        class-name="center-column"
        sortable="custom"
      />
      <filterable-table-column
        prop="driver_name"
        label="设备驱动"
        class-name="center-column"
        sortable="custom"
      >
        <template #default="scope">
          <el-button
            link
            @click="viewDriverDetails(scope.row.driver_name)"
          >
            {{ scope.row.driver_name }}
          </el-button>
        </template>
      </filterable-table-column>
      <filterable-table-column
        prop="enable"
        label="启用"
        class-name="center-column"
        sortable="custom"
      >
        <template #default="scope">
          {{ getEnable(scope.row.enable) }}
        </template>
      </filterable-table-column>
      <filterable-table-column
        prop="status"
        label="状态"
        class-name="center-column"
        sortable="custom"
      >
        <template #default="scope">
          <el-tag :type="getDeviceStatusTagType(scope.row.status)" size="small">
            {{ getDeviceStatusDisplay(scope.row.status, scope.row.is_manual) }}
          </el-tag>
        </template>
      </filterable-table-column>
      <filterable-table-column
        prop="version"
        label="驱动版本"
        class-name="center-column"
        sortable="custom"
      >
        <template #default="scope">
          {{ driverDetails[scope.row.driver_name]?.version }}
        </template>
      </filterable-table-column>
      <filterable-table-column
        prop="tech_type"
        label="技术路线"
        class-name="center-column"
        sortable="custom"
      >
        <template #default="scope">
          {{ getTechTypeName(versionData, driverDetails[scope.row.driver_name]?.tech_type) }}
        </template>
      </filterable-table-column>
      <filterable-table-column
        prop="max_qubits"
        label="量子比特数"
        class-name="center-column"
        sortable="custom"
      >
        <template #default="scope">
          {{ driverDetails[scope.row.driver_name]?.max_qubits }}
        </template>
      </filterable-table-column>
      <filterable-table-column
        prop="transpiler"
        label="默认转译器"
        class-name="center-column"
        sortable="custom"
      >
        <template #default="scope">
          <div v-if="getTranspilerName(scope.row)">
            <el-button
              link
              @click="viewTranspilerDetails(driverDetails[scope.row.driver_name]?.transpiler)"
            >
              {{ getTranspilerName(scope.row) }}
            </el-button>
          </div>
          <div v-else>
            -
          </div>
        </template>
      </filterable-table-column>
      <filterable-table-column
        prop="availability"
        label="可用率"
        class-name="center-column"
        sortable="custom"
      >
        <template #default="scope">
          <el-tag
            v-if="getAvailability(scope.row) !== null"
            :type="getAvailabilityTagType(getAvailability(scope.row))"
            size="small"
          >
            {{ (getAvailability(scope.row) * 100).toFixed(1) }}%
          </el-tag>
          <span v-else>-</span>
        </template>
      </filterable-table-column>
      <filterable-table-column
        prop="description"
        label="设备描述"
        class-name="left-column"
        sortable="custom"
      />
      <el-table-column
        prop="details"
        label="操作"
        class-name="center-column"
        fixed="right"
        width="90"
      >
        <template #default="scope">
          <el-tooltip content="查看" placement="top">
            <el-button
              link
              :icon="View"
              @click="viewDeviceDetails(scope.row.name)"
            />
          </el-tooltip>
        </template>
      </el-table-column>
    </PageTable>
  </div>
</template>

<script>
import { markRaw } from 'vue'
import { View } from '@element-plus/icons-vue'
import PageTable from '@/components/PageTable'
import FilterableTableColumn from '@/components/PageTable/FilterableTableColumn.vue'
import { getDrivers } from '@/api/driver'
import { getDevices } from '@/api/device'
import {
  getEnable,
  getStatus,
  getDeviceStatusDisplay,
  getDeviceStatusTagType,
  getTechTypeName
} from '@/common/library'
import { queryVersion } from '@/api/version'

export default {
  components: {
    PageTable,
    FilterableTableColumn
  },
  data() {
    return {
      versionData: {
        version: '',
        api_version: '',
        supported_api_versions: [],
        platform_version: '',
        capabilities: {}
      },
      driverDetails: {},
      View: markRaw(View)
    }
  },
  created() {
    this.initData()
  },
  methods: {
    getEnable,
    getStatus,
    getDeviceStatusDisplay,
    getDeviceStatusTagType,
    getTechTypeName,

    async initData() {
      await this.fetchVersion()
      await this.fetchDrivers()
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

    async fetchDrivers() {
      try {
        const response = await getDrivers()
        if (!response.error) {
          this.driverDetails = response.result
        } else {
          this.$message.error(`获取驱动列表失败：${response.message || '未知错误'}`)
        }
      } catch (error) {
        console.error('获取驱动列表失败:', error)
        this.$message.error('获取驱动列表失败，请检查网络连接')
      }
    },

    // PageTable fetchData callback
    async fetchDevices(params) {
      // params: {page, page_size, search, filters, sort}
      const query = {
        pagination: {
          page: params.page,
          page_size: params.page_size
        }
      }
      if (params.search) {
        query.search = params.search
      }
      if (params.filters) {
        query.filters = params.filters
      }
      if (params.sort) {
        query.sort = params.sort
      }
      return await getDevices(query)
    },

    getTranspilerName(row) {
      const driverName = row.driver_name
      const driver = this.driverDetails[driverName]
      const caps = this.versionData && this.versionData.capabilities
      if (!driver || !driver.transpiler) {
        return ''
      }
      if (!caps || !caps.transpilers) {
        return ''
      }
      const transpilerName = driver.transpiler
      const transpilers = caps.transpilers
      if (!transpilers[transpilerName]) {
        return ''
      }
      return transpilers[transpilerName].alias_name || '-'
    },

    getAvailability(row) {
      if (row && row.metrics && row.metrics.availability_total !== null && row.metrics.availability_total !== undefined) {
        return row.metrics.availability_total
      }
      return null
    },

    getAvailabilityTagType(rate) {
      if (rate === null || rate === undefined) return 'info'
      if (rate >= 0.9) return 'success'
      if (rate >= 0.6) return 'warning'
      return 'danger'
    },

    viewDriverDetails(driverName) {
      this.$router.push({ name: 'DriverDetails', params: { driverName: driverName }})
    },

    viewTranspilerDetails(transpilerName) {
      this.$router.push({ name: 'TranspilerDetails', params: { transpilerName: transpilerName }})
    },

    viewDeviceDetails(deviceName) {
      this.$router.push({ name: 'DeviceDetails', params: { deviceName: deviceName }})
    }
  }
}
</script>

<style scoped>
.device-list-container {
  display: flex;
  flex-direction: column;
  background: var(--el-fill-color-light);
  padding: 20px;
  box-sizing: border-box;
}

.header { margin: 0; }
</style>
