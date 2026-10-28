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
  <div class="device-group-list-container">
    <div class="header">
      <h2>设备组管理</h2>
    </div>
    <PageTable
      ref="pageTableRef"
      :fetch-data="fetchDeviceGroups"
      search-placeholder="全局搜索：设备组名称 / ID / 项目ID / 设备 …"
      row-key="id"
      @selection-change="handleSelectionChange"
    >
      <template #toolbar-actions>
        <el-button
          type="primary"
          size="small"
          :icon="Plus"
          @click="openCreateDialog"
        >
          新增设备组
        </el-button>
        <el-button
          type="danger"
          size="small"
          :icon="Delete"
          :disabled="selectedRows.length === 0"
          @click="handleBatchDelete"
        >
          批量删除 ({{ selectedRows.length }})
        </el-button>
      </template>
      <el-table-column
        type="selection"
        class-name="center-column"
        fixed="left"
        width="50"
      />
      <filterable-table-column
        prop="name"
        label="设备组名称"
        fixed="left"
        class-name="center-column"
        sortable="custom"
      />
      <filterable-table-column
        prop="id"
        label="设备组ID"
        fixed="left"
        class-name="center-column"
        sortable="custom"
      />
      <filterable-table-column
        prop="project_id"
        label="所属项目ID"
        class-name="center-column"
        sortable="custom"
      />
      <filterable-table-column
        prop="description"
        label="描述"
        class-name="left-column"
        sortable="custom"
      />
      <filterable-table-column
        prop="device_names"
        label="设备名称列表"
        class-name="left-column"
        sortable="custom"
      >
        <template #default="scope">
          {{ formatDeviceNames(scope.row.device_names) }}
        </template>
      </filterable-table-column>
      <filterable-table-column
        prop="is_public"
        label="是否公开"
        class-name="center-column"
        sortable="custom"
      >
        <template #default="scope">
          <el-tag :type="scope.row.is_public ? 'success' : 'info'">
            {{ scope.row.is_public ? '是' : '否' }}
          </el-tag>
        </template>
      </filterable-table-column>
      <filterable-table-column
        prop="created_at"
        label="创建时间"
        class-name="center-column"
        sortable="custom"
      />
      <filterable-table-column
        prop="updated_at"
        label="更新时间"
        class-name="center-column"
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
              @click="viewGroupDetails(scope.row.id)"
            />
          </el-tooltip>
          <el-tooltip content="更新" placement="top">
            <el-button
              link
              type="primary"
              :icon="Edit"
              @click="openUpdateDialog(scope.row)"
            />
          </el-tooltip>
        </template>
      </el-table-column>
    </PageTable>

    <!-- create/update device group dialog -->
    <el-dialog
      v-model="showFormDialog"
      :title="formMode === 'create' ? '新增设备组' : '更新设备组'"
      width="600px"
      align-center
      draggable
      @close="resetFormDialog"
    >
      <el-form
        ref="formRef"
        :model="formData"
        :rules="formRules"
        label-width="120px"
        label-position="right"
      >
        <el-form-item label="设备组名称" prop="name">
          <el-input
            v-model="formData.name"
            placeholder="请输入设备组名称"
            maxlength="64"
            show-word-limit
          />
        </el-form-item>

        <el-form-item label="描述" prop="description">
          <el-input
            v-model="formData.description"
            type="textarea"
            :rows="3"
            placeholder="请输入设备组描述（可选）"
          />
        </el-form-item>

        <el-form-item label="设备列表" prop="device_names">
          <el-select
            v-model="formData.device_names"
            multiple
            filterable
            placeholder="请选择设备（至少一个）"
            style="width: 100%"
            :loading="deviceLoading"
            @change="handleDeviceNamesChange"
          >
            <!-- special "_all" sentinel: matches Constant.DEVICE_GROUP_DN_ALL
                 on the backend; when chosen, the server replaces the whole
                 list with ["_all"], meaning "all devices" -->
            <el-option
              :key="DEVICE_ALL_VALUE"
              :label="DEVICE_ALL_VALUE + '（所有设备）'"
              :value="DEVICE_ALL_VALUE"
            >
              <el-tooltip
                placement="right"
                :show-after="200"
                raw-content
                :content="deviceAllTooltipHtml()"
                popper-class="device-option-tooltip"
              >
                <div class="device-option-row">
                  <span class="device-state-dot state-online" :title="'special'" />
                  <span class="device-alias">{{ DEVICE_ALL_VALUE }}</span>
                  <span class="device-name">（所有设备，与具体设备互斥）</span>
                </div>
              </el-tooltip>
            </el-option>
            <el-option
              v-for="device in deviceOptions"
              :key="device.name"
              :label="deviceOptionLabel(device)"
              :value="device.name"
            >
              <el-tooltip
                placement="right"
                :show-after="200"
                raw-content
                :content="deviceTooltipHtml(device)"
                popper-class="device-option-tooltip"
              >
                <div class="device-option-row">
                  <span
                    class="device-state-dot"
                    :class="'state-' + (device.status || 'unknown')"
                    :title="device.status || 'unknown'"
                  />
                  <span class="device-alias">{{ device.alias_name || device.name }}</span>
                  <span v-if="device.alias_name" class="device-name">({{ device.name }})</span>
                  <span class="device-qubits">[{{ deviceQubits(device) }} qubits]</span>
                </div>
              </el-tooltip>
            </el-option>
          </el-select>
        </el-form-item>

        <el-form-item label="是否公开" prop="is_public">
          <el-switch v-model="formData.is_public" />
          <span class="form-hint">{{ formData.is_public ? '公开：所有项目可见' : '私有：仅本项目可见' }}</span>
        </el-form-item>

        <el-form-item label="项目ID" prop="project_id">
          <el-input
            v-model="formData.project_id"
            placeholder="留空则使用当前用户所属项目"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showFormDialog = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitForm">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { markRaw } from 'vue'
import { Plus, Delete, Edit, View } from '@element-plus/icons-vue'
import PageTable from '@/components/PageTable'
import FilterableTableColumn from '@/components/PageTable/FilterableTableColumn.vue'
import {
  getDeviceGroups,
  createDeviceGroup,
  updateDeviceGroup,
  deleteDeviceGroups,
  getDevices
} from '@/api/device'
import {
  getDeviceStatusDisplay
} from '@/common/library'

// Special device-name sentinel meaning "all devices"; mirrors
// Constant.DEVICE_GROUP_DN_ALL on the backend. When this value is part of
// the submitted device_names list, the server replaces the whole list
// with ["_all"] before persisting
const DEVICE_ALL_VALUE = '_all'

export default {
  components: {
    PageTable,
    FilterableTableColumn
  },
  data() {
    return {
      Plus: markRaw(Plus),
      Delete: markRaw(Delete),
      Edit: markRaw(Edit),
      View: markRaw(View),
      // selected rows for batch operations (updated via PageTable
      // selection-change event)
      selectedRows: [],
      // create/update dialog state
      formMode: 'create',
      showFormDialog: false,
      submitting: false,
      deviceLoading: false,
      deviceOptions: [],
      // exposed to the template so the special "_all" el-option can bind
      // its key/label/value against the same constant the script uses
      DEVICE_ALL_VALUE,
      // current editing group id (for update mode)
      editingGroupId: null,
      formData: {
        name: '',
        description: '',
        device_names: [],
        is_public: true,
        project_id: ''
      },
      formRules: {
        name: [
          { required: true, message: '请输入设备组名称', trigger: 'blur' },
          { min: 1, max: 64, message: '名称长度在 1 到 64 个字符', trigger: 'blur' }
        ],
        device_names: [
          { required: true, type: 'array', message: '请至少选择一个设备', trigger: 'change' }
        ]
      }
    }
  },
  watch: {
    // load device options when create/update dialog opens
    showFormDialog(newVal) {
      if (newVal && this.deviceOptions.length === 0) {
        this.fetchDeviceOptions()
      }
    }
  },
  methods: {
    // PageTable fetchData callback
    async fetchDeviceGroups(params) {
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
      return await getDeviceGroups(query)
    },

    async fetchDeviceOptions() {
      this.deviceLoading = true
      try {
        const response = await getDevices()
        if (!response.error) {
          const devices = response.result
          this.deviceOptions = []
          if (devices && typeof devices === 'object') {
            for (const deviceName in devices) {
              const device = devices[deviceName]
              this.deviceOptions.push(device)
            }
          }
        }
      } catch (error) {
        console.error('获取设备列表失败:', error)
      } finally {
        this.deviceLoading = false
      }
    },

    // label used by the device dropdown option: "<alias> (<name>) [<N>
    // qubits]"; falls back to plain "<name>" when alias is missing.
    // Mirrors the "后端设备" presentation on the job submit page so the
    // same device renders identically across pages
    deviceOptionLabel(device) {
      if (!device) return ''
      const alias = device.alias_name || device.name
      const namePart = device.alias_name ? ` (${device.name})` : ''
      return `${alias}${namePart} [${this.deviceQubits(device)} qubits]`
    },

    // qubit count shown next to the device name: prefer available_qubits
    // and fall back to max_qubits, matching the job submit page rule
    deviceQubits(device) {
      if (!device) return '-'
      const aq = device.available_qubits
      const mq = device.max_qubits
      if (aq !== undefined && aq !== null) return aq
      if (mq !== undefined && mq !== null) return mq
      return '-'
    },

    // Build the HTML string used as the el-tooltip content for a device
    // option; mirrors the job submit page so the same device tooltip is
    // consistent everywhere. inline styles are used because the tooltip
    // popper is teleported to <body> and out of scoped CSS
    deviceTooltipHtml(device) {
      if (!device) return ''
      const rows = [
        ['名称', device.name],
        ['别名', device.alias_name || device.name],
        ['路线', device.tech_type || '-'],
        ['比特数', String(this.deviceQubits(device))],
        ['状态', getDeviceStatusDisplay(device.status || 'unknown', device.is_manual === true)],
        ['描述', device.description || '-']
      ]
      const rowStyle = 'display:flex;align-items:flex-start;gap:8px;line-height:1.5;'
      const labelStyle = 'font-weight:600;opacity:0.85;min-width:56px;display:inline-block;'
      const rowsHtml = rows.map(([label, value]) =>
        `<div style="${rowStyle}"><span style="${labelStyle}">${label}:</span><span>${value}</span></div>`
      ).join('')
      return `<div style="display:flex;flex-direction:column;gap:4px;font-size:12px;max-width:380px;word-break:break-all;">${rowsHtml}</div>`
    },

    // Tooltip content for the special "_all" sentinel option. Kept as a
    // separate builder so the visual style matches the regular device
    // tooltip while the wording explains the sentinel semantics
    deviceAllTooltipHtml() {
      const rows = [
        ['名称', DEVICE_ALL_VALUE],
        ['含义', '所有设备'],
        ['行为', '与具体设备互斥：选择 _all 时其他设备会被自动移除；选择具体设备时 _all 会被自动移除'],
        ['后端', '服务端收到 _all 后会将 device_names 规范为 ["_all"]，等价于"对所有设备生效"']
      ]
      const rowStyle = 'display:flex;align-items:flex-start;gap:8px;line-height:1.5;'
      const labelStyle = 'font-weight:600;opacity:0.85;min-width:56px;display:inline-block;'
      const rowsHtml = rows.map(([label, value]) =>
        `<div style="${rowStyle}"><span style="${labelStyle}">${label}:</span><span>${value}</span></div>`
      ).join('')
      return `<div style="display:flex;flex-direction:column;gap:4px;font-size:12px;max-width:380px;word-break:break-all;">${rowsHtml}</div>`
    },

    // Enforce the mutual-exclusion rule for the special "_all" sentinel:
    //  - picking _all clears every other selected device
    //  - picking any concrete device removes _all
    // The backend also enforces this on submit (it replaces device_names
    // with ["_all"] when _all is present), so the frontend behaviour is
    // purely a UX convenience to make the rule visible at selection time
    handleDeviceNamesChange(newValue) {
      if (!Array.isArray(newValue)) return
      const hasAll = newValue.includes(DEVICE_ALL_VALUE)
      const prevHadAll = Array.isArray(this._prevDeviceNames)
        ? this._prevDeviceNames.includes(DEVICE_ALL_VALUE)
        : false
      if (hasAll && !prevHadAll) {
        // _all was just added -> drop every other device
        this.formData.device_names = [DEVICE_ALL_VALUE]
      } else if (hasAll && newValue.length > 1) {
        // _all was already selected and the user added a concrete device
        // -> drop _all so only concrete devices remain
        this.formData.device_names = newValue.filter(v => v !== DEVICE_ALL_VALUE)
      }
      this._prevDeviceNames = [...this.formData.device_names]
    },

    viewGroupDetails(groupId) {
      this.$router.push({ name: 'DeviceGroupDetails', params: { groupId: groupId }})
    },

    // open the create dialog
    openCreateDialog() {
      this.formMode = 'create'
      this.editingGroupId = null
      this.formData = {
        name: '',
        description: '',
        device_names: [],
        is_public: true,
        project_id: ''
      }
      // seed the _all mutual-exclusion baseline so handleDeviceNamesChange
      // can distinguish "user just added _all" from "_all was already
      // selected" when the dialog opens with a pre-filled list
      this._prevDeviceNames = []
      this.showFormDialog = true
    },

    // open the update dialog with row data pre-filled
    openUpdateDialog(row) {
      this.formMode = 'update'
      this.editingGroupId = row.id
      this.formData = {
        name: row.name || '',
        description: row.description || '',
        device_names: Array.isArray(row.device_names) ? [...row.device_names] : [],
        is_public: !!row.is_public,
        project_id: row.project_id || ''
      }
      // seed the _all mutual-exclusion baseline; the existing list may
      // already contain "_all" when editing a group that targets every
      // device, in which case the next user action must be interpreted as
      // "add a concrete device and drop _all"
      this._prevDeviceNames = [...this.formData.device_names]
      this.showFormDialog = true
    },

    resetFormDialog() {
      this.formData = {
        name: '',
        description: '',
        device_names: [],
        is_public: true,
        project_id: ''
      }
      this.editingGroupId = null
      if (this.$refs.formRef) {
        this.$refs.formRef.resetFields()
      }
    },

    // submit create or update based on formMode
    async submitForm() {
      try {
        await this.$refs.formRef.validate()
      } catch {
        return
      }

      this.submitting = true
      try {
        const payload = {
          name: this.formData.name,
          device_names: this.formData.device_names,
          is_public: this.formData.is_public
        }
        if (this.formData.description) {
          payload.description = this.formData.description
        }
        if (this.formData.project_id) {
          payload.project_id = this.formData.project_id
        }

        let response
        if (this.formMode === 'create') {
          response = await createDeviceGroup(payload)
        } else {
          // update requires group_id
          payload.group_id = this.editingGroupId
          response = await updateDeviceGroup(payload)
        }

        if (!response.error) {
          this.$message.success(this.formMode === 'create' ? '设备组创建成功' : '设备组更新成功')
          this.showFormDialog = false
          this.$refs.pageTableRef.refresh()
        } else {
          this.$message.error(`${this.formMode === 'create' ? '创建' : '更新'}设备组失败：${response.message || '未知错误'}`)
        }
      } catch (error) {
        console.error(`${this.formMode === 'create' ? '创建' : '更新'}设备组失败:`, error)
        this.$message.error(`${this.formMode === 'create' ? '创建' : '更新'}设备组失败，请检查网络连接`)
      } finally {
        this.submitting = false
      }
    },

    // track selected rows for batch operations
    handleSelectionChange(selection) {
      this.selectedRows = selection
    },

    // batch delete selected device groups
    handleBatchDelete() {
      const selectedRows = this.selectedRows
      if (selectedRows.length === 0) {
        this.$message.warning('请先选择要删除的设备组')
        return
      }
      const ids = selectedRows.map(row => row.id)
      const names = selectedRows.map(row => row.name).join(', ')
      this.$confirm(`确定要删除选中的 ${selectedRows.length} 个设备组（${names}）吗？`, '批量删除确认', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }).then(async() => {
        try {
          const response = await deleteDeviceGroups(ids)
          if (!response.error) {
            this.$message.success('批量删除成功')
            this.$refs.pageTableRef.refresh()
          } else {
            this.$message.error(`批量删除失败：${response.message || '未知错误'}`)
          }
        } catch (error) {
          console.error('批量删除失败:', error)
          this.$message.error('批量删除失败，请检查网络连接')
        }
      }).catch(() => {
        this.$message.info('已取消批量删除')
      })
    },

    formatDeviceNames(deviceNames) {
      if (!deviceNames) return '-'
      if (Array.isArray(deviceNames)) {
        if (deviceNames.length === 0) return '[]'
        return deviceNames.join(', ')
      }
      return String(deviceNames)
    }
  }
}
</script>

<style scoped>
.device-group-list-container {
  display: flex;
  flex-direction: column;
  background: var(--el-fill-color-light);
  padding: 20px;
  box-sizing: border-box;
}

.header { margin: 0; }

.form-hint {
  margin-left: 12px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

/* device option row with a leading status dot -- mirrors the job
   submit page's "后端设备" dropdown so the same device renders
   identically across pages */
.device-option-row {
  display: flex;
  align-items: center;
  gap: 6px;
}

.device-state-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
  flex-shrink: 0;
}

/* status colors aligned with getDeviceStatusTagType in common/library.js */
.device-state-dot.state-online {
  background: var(--el-color-success);
}

.device-state-dot.state-offline {
  background: var(--el-color-info);
}

.device-state-dot.state-busy,
.device-state-dot.state-calibrating,
.device-state-dot.state-maintain {
  background: var(--el-color-warning);
}

.device-state-dot.state-disconnected {
  background: var(--el-color-danger);
}

.device-state-dot.state-unknown {
  background: var(--el-color-info);
}

.device-option-row .device-name,
.device-option-row .device-qubits {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}
</style>
