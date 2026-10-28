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
          <el-tooltip content="更新" placement="top">
            <el-button
              link
              type="primary"
              :icon="Edit"
              @click="openSetDeviceDialog(scope.row)"
            />
          </el-tooltip>
        </template>
      </el-table-column>
    </PageTable>

    <!-- Set Device dialog -->
    <el-dialog
      v-model="setDeviceDialog.visible"
      title="更新设备"
      width="520px"
      align-center
      :close-on-click-modal="false"
      @close="resetSetDeviceDialog"
    >
      <el-form
        ref="setDeviceFormRef"
        :model="setDeviceDialog.form"
        :rules="setDeviceRules"
        label-width="140px"
      >
        <el-form-item label="设备名称">
          <el-input v-model="setDeviceDialog.form.device_name" disabled />
        </el-form-item>
        <el-form-item label="状态" prop="state">
          <el-select
            v-model="setDeviceDialog.form.state"
            placeholder="不修改"
            clearable
            style="width: 100%"
          >
            <el-option
              v-for="opt in deviceStateOptions"
              :key="opt.value"
              :label="opt.label"
              :value="opt.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="启用" prop="enable">
          <el-select
            v-model="setDeviceDialog.form.enable"
            placeholder="不修改"
            clearable
            style="width: 100%"
          >
            <el-option label="启用 (true)" :value="true" />
            <el-option label="禁用 (false)" :value="false" />
          </el-select>
        </el-form-item>
        <el-form-item label="最大比特数" prop="max_qubits">
          <el-input
            v-model="setDeviceDialog.form.max_qubits"
            placeholder="不修改；填 auto 恢复驱动默认，或正整数"
            clearable
          />
        </el-form-item>
        <el-form-item label="可用比特数" prop="available_qubits">
          <el-input
            v-model="setDeviceDialog.form.available_qubits"
            placeholder="不修改；填 auto 恢复驱动默认，或正整数"
            clearable
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="setDeviceDialog.visible = false">取消</el-button>
        <el-button
          type="primary"
          :loading="setDeviceDialog.submitting"
          @click="submitSetDevice"
        >确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { markRaw } from 'vue'
import { View, Edit } from '@element-plus/icons-vue'
import PageTable from '@/components/PageTable'
import FilterableTableColumn from '@/components/PageTable/FilterableTableColumn.vue'
import { getDrivers } from '@/api/driver'
import { getDevices, setDevice } from '@/api/device'
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
    const qubitsValidator = (rule, value, callback) => {
      if (value === '' || value === null || value === undefined) {
        callback()
        return
      }
      if (value === 'auto') {
        callback()
        return
      }
      const n = Number(value)
      if (!Number.isInteger(n) || n <= 0) {
        callback(new Error('必须为 auto 或正整数'))
        return
      }
      callback()
    }
    return {
      versionData: {
        version: '',
        api_version: '',
        supported_api_versions: [],
        platform_version: '',
        capabilities: {}
      },
      driverDetails: {},
      View: markRaw(View),
      Edit: markRaw(Edit),
      // options shown in the "state" select of the set-device dialog;
      // label is "中文 (state)" per UX requirement, value is the raw
      // state string sent to the backend
      deviceStateOptions: [
        { value: 'auto', label: '自动 (auto)' },
        { value: 'online', label: '在线 (online)' },
        { value: 'offline', label: '离线 (offline)' },
        { value: 'busy', label: '繁忙 (busy)' },
        { value: 'disconnected', label: '断连 (disconnected)' },
        { value: 'calibrating', label: '校准 (calibrating)' },
        { value: 'maintain', label: '维护 (maintain)' },
        { value: 'unknown', label: '未知 (unknown)' }
      ],
      setDeviceDialog: {
        visible: false,
        submitting: false,
        form: {
          device_name: '',
          state: null,
          enable: null,
          max_qubits: '',
          available_qubits: ''
        }
      },
      setDeviceRules: {
        max_qubits: [{ validator: qubitsValidator, trigger: 'blur' }],
        available_qubits: [{ validator: qubitsValidator, trigger: 'blur' }]
      }
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
    },

    openSetDeviceDialog(row) {
      // Pre-fill state and enable from the current row so the selects
      // reflect the live values.
      // - When is_manual is false, the device is in auto mode -> pre-select 'auto'
      // - When is_manual is true, the device state was set manually -> pre-select
      //   the current status (online/offline/busy/...)
      // max_qubits / available_qubits stay empty so unchanged fields are not
      // sent on submit.
      const defaultState = row.is_manual === false ? 'auto' : (row.status || null)
      this.setDeviceDialog.form = {
        device_name: row.name,
        state: defaultState,
        enable: row.enable !== null && row.enable !== undefined ? row.enable : null,
        max_qubits: '',
        available_qubits: ''
      }
      this.setDeviceDialog.visible = true
    },

    resetSetDeviceDialog() {
      this.setDeviceDialog.submitting = false
      if (this.$refs.setDeviceFormRef) {
        this.$refs.setDeviceFormRef.clearValidate()
      }
    },

    async submitSetDevice() {
      const formRef = this.$refs.setDeviceFormRef
      if (formRef) {
        const valid = await formRef.validate().catch(() => false)
        if (!valid) return
      }
      const f = this.setDeviceDialog.form
      const payload = { device_name: f.device_name }
      if (f.state) payload.state = f.state
      if (f.enable !== null && f.enable !== undefined && f.enable !== '') {
        payload.enable = f.enable
      }
      if (f.max_qubits) payload.max_qubits = f.max_qubits
      if (f.available_qubits) payload.available_qubits = f.available_qubits

      const hasChange = Object.keys(payload).length > 1
      if (!hasChange) {
        this.$message.warning('未做任何修改')
        return
      }

      this.setDeviceDialog.submitting = true
      try {
        const response = await setDevice(payload)
        if (!response.error) {
          this.$message.success(`设备 ${f.device_name} 更新成功`)
          this.setDeviceDialog.visible = false
          // refresh device list
          if (this.$refs.pageTableRef && this.$refs.pageTableRef.refresh) {
            this.$refs.pageTableRef.refresh()
          }
        } else {
          this.$message.error(`更新失败：${response.message || '未知错误'}`)
        }
      } catch (error) {
        console.error('更新设备失败:', error)
        this.$message.error('更新设备失败，请检查网络连接')
      } finally {
        this.setDeviceDialog.submitting = false
      }
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
