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
  <div class="flavor-list-container">
    <div class="header">
      <h2>资源规格列表</h2>
    </div>
    <PageTable
      ref="pageTableRef"
      :fetch-data="fetchFlavors"
      search-placeholder="全局搜索：名称 / 描述 / 比特数 / 设备组 …"
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
          新增资源规格
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
        label="名称"
        fixed="left"
        class-name="center-column"
        sortable="custom"
      />
      <filterable-table-column
        prop="description"
        label="描述"
        class-name="left-column"
        show-overflow-tooltip
        sortable="custom"
      />
      <filterable-table-column
        prop="is_public"
        label="是否公开"
        class-name="center-column"
        sortable="custom"
      >
        <template #default="scope">
          <el-tag :type="scope.row.is_public ? 'success' : 'info'" size="small">
            {{ scope.row.is_public ? '是' : '否' }}
          </el-tag>
        </template>
      </filterable-table-column>
      <filterable-table-column
        prop="min_qubits"
        label="最小量子比特数"
        class-name="center-column"
        sortable="custom"
      />
      <filterable-table-column
        prop="max_qubits"
        label="最大量子比特数"
        class-name="center-column"
        sortable="custom"
      />
      <filterable-table-column
        prop="gate_fidelity_1q_min"
        label="单比特门保真度"
        class-name="center-column"
        sortable="custom"
      />
      <filterable-table-column
        prop="gate_fidelity_2q_min"
        label="双比特门保真度"
        class-name="center-column"
        sortable="custom"
      />
      <filterable-table-column
        prop="device_groups"
        label="设备组"
        class-name="center-column"
        sortable="custom"
      >
        <template #default="scope">
          {{ formatDeviceGroups(scope.row.device_groups) }}
        </template>
      </filterable-table-column>
      <filterable-table-column
        prop="created_at"
        label="创建时间"
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
              @click="viewFlavorDetails(scope.row.id)"
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

    <!-- Create/Update Dialog -->
    <el-dialog
      v-model="showFormDialog"
      :title="formMode === 'create' ? '新增资源规格' : '更新资源规格'"
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
        <el-form-item label="名称" prop="name">
          <el-input
            v-model="formData.name"
            placeholder="请输入资源规格名称"
            maxlength="64"
            show-word-limit
          />
        </el-form-item>

        <el-form-item label="描述" prop="description">
          <el-input
            v-model="formData.description"
            type="textarea"
            :rows="3"
            placeholder="请输入资源规格描述（可选）"
          />
        </el-form-item>

        <el-form-item label="是否公开" prop="is_public">
          <el-switch v-model="formData.is_public" />
          <span class="form-hint">{{ formData.is_public ? '公开：所有项目可见' : '私有：仅本项目可见' }}</span>
        </el-form-item>

        <el-form-item label="最小量子比特数" prop="min_qubits">
          <el-input-number
            v-model="formData.min_qubits"
            :min="0"
            :step="1"
            controls-position="right"
            placeholder="最小量子比特数（可选）"
          />
        </el-form-item>

        <el-form-item label="最大量子比特数" prop="max_qubits">
          <el-input-number
            v-model="formData.max_qubits"
            :min="0"
            :step="1"
            controls-position="right"
            placeholder="最大量子比特数（可选）"
          />
        </el-form-item>

        <el-form-item label="单比特门保真度" prop="gate_fidelity_1q_min">
          <el-input-number
            v-model="formData.gate_fidelity_1q_min"
            :min="0"
            :max="1"
            :step="0.0001"
            :precision="6"
            controls-position="right"
            placeholder="0 ~ 1（可选）"
          />
        </el-form-item>

        <el-form-item label="双比特门保真度" prop="gate_fidelity_2q_min">
          <el-input-number
            v-model="formData.gate_fidelity_2q_min"
            :min="0"
            :max="1"
            :step="0.0001"
            :precision="6"
            controls-position="right"
            placeholder="0 ~ 1（可选）"
          />
        </el-form-item>

        <el-form-item label="设备组" prop="device_groups">
          <el-select
            v-model="formData.device_groups"
            multiple
            filterable
            placeholder="请选择设备组（至少一个）"
            style="width: 100%"
            :loading="deviceGroupLoading"
          >
            <el-option
              v-for="group in deviceGroupOptions"
              :key="group.id"
              :label="deviceGroupLabel(group)"
              :value="group.id"
            >
              <el-tooltip
                placement="right"
                :show-after="200"
                raw-content
                :content="deviceGroupTooltipHtml(group)"
                popper-class="device-option-tooltip"
                :disabled="!group.description"
              >
                <div class="device-group-option-row">
                  <span class="group-name">{{ group.name }}</span>
                  <span v-if="group.description" class="group-desc">({{ group.description }})</span>
                </div>
              </el-tooltip>
            </el-option>
          </el-select>
        </el-form-item>

        <el-form-item label="项目ID" prop="project_id">
          <el-input
            v-model="formData.project_id"
            placeholder="留空则使用当前用户所属项目"
          />
        </el-form-item>

        <el-form-item label="额外属性">
          <div class="extra-properties">
            <div
              v-for="(item, index) in extraPropertiesList"
              :key="index"
              class="extra-property-row"
            >
              <el-input
                v-model="item.key"
                placeholder="属性名"
                class="extra-key-input"
              />
              <el-input
                v-model="item.value"
                placeholder="属性值"
                class="extra-value-input"
              />
              <el-button
                type="danger"
                link
                @click="removeExtraProperty(index)"
              >
                删除
              </el-button>
            </div>
            <el-button type="primary" link @click="addExtraProperty">
              + 添加属性
            </el-button>
          </div>
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
import { getFlavors, createFlavor, updateFlavor, deleteFlavors } from '@/api/flavor'
import { getDeviceGroups } from '@/api/device'

export default {
  components: {
    PageTable,
    FilterableTableColumn
  },
  data() {
    const validateQubitsRange = (rule, value, callback) => {
      if (
        value !== null &&
        value !== undefined &&
        this.formData.max_qubits !== null &&
        this.formData.max_qubits !== undefined &&
        value > this.formData.max_qubits
      ) {
        callback(new Error('最小量子比特数不能大于最大量子比特数'))
      } else {
        callback()
      }
    }

    return {
      Plus: markRaw(Plus),
      Delete: markRaw(Delete),
      // selected rows for batch operations (updated via PageTable
      // selection-change event)
      selectedRows: [],
      Edit: markRaw(Edit),
      View: markRaw(View),
      // create/update dialog state
      formMode: 'create',
      showFormDialog: false,
      submitting: false,
      deviceGroupLoading: false,
      deviceGroupOptions: [],
      // current editing flavor id (for update mode)
      editingFlavorId: null,
      formData: {
        name: '',
        description: '',
        is_public: true,
        min_qubits: null,
        max_qubits: null,
        gate_fidelity_1q_min: null,
        gate_fidelity_2q_min: null,
        device_groups: [],
        project_id: ''
      },
      extraPropertiesList: [],
      formRules: {
        name: [
          { required: true, message: '请输入资源规格名称', trigger: 'blur' },
          { min: 1, max: 64, message: '名称长度在 1 到 64 个字符', trigger: 'blur' }
        ],
        min_qubits: [
          { type: 'number', min: 0, message: '最小量子比特数不能小于 0', trigger: 'blur' },
          { validator: validateQubitsRange, trigger: 'blur' }
        ],
        max_qubits: [
          { type: 'number', min: 0, message: '最大量子比特数不能小于 0', trigger: 'blur' }
        ],
        gate_fidelity_1q_min: [
          { type: 'number', min: 0, max: 1, message: '保真度范围为 0 ~ 1', trigger: 'blur' }
        ],
        gate_fidelity_2q_min: [
          { type: 'number', min: 0, max: 1, message: '保真度范围为 0 ~ 1', trigger: 'blur' }
        ],
        device_groups: [
          {
            required: true,
            type: 'array',
            message: '请至少选择一个设备组',
            trigger: 'change'
          }
        ]
      }
    }
  },
  created() {
    this.fetchDeviceGroups()
  },
  methods: {
    // PageTable fetchData callback
    async fetchFlavors(params) {
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
      return await getFlavors(query)
    },

    async fetchDeviceGroups() {
      this.deviceGroupLoading = true
      try {
        const response = await getDeviceGroups()
        if (!response.error) {
          const groups = response.result
          this.deviceGroupOptions = []
          // keep the description so the option label and tooltip can
          // render "name (description)"; matches the resource spec
          // dropdown on the job submit page
          if (Array.isArray(groups)) {
            this.deviceGroupOptions = groups.map(g => ({
              id: g.id,
              name: g.name,
              description: g.description || ''
            }))
          } else if (groups && typeof groups === 'object') {
            for (const groupId in groups) {
              const g = groups[groupId]
              this.deviceGroupOptions.push({
                id: g.id,
                name: g.name,
                description: g.description || ''
              })
            }
          }
        } else {
          this.$message.error(`获取设备组列表失败：${response.message || '未知错误'}`)
        }
      } catch (error) {
        console.error('获取设备组列表失败:', error)
        this.$message.error('获取设备组列表失败，请检查网络连接')
      } finally {
        this.deviceGroupLoading = false
      }
    },

    formatDeviceGroups(deviceGroups) {
      if (!deviceGroups || !Array.isArray(deviceGroups) || deviceGroups.length === 0) {
        return '-'
      }
      return deviceGroups.join(', ')
    },

    // label shown in the device-group dropdown: "name (description)" when
    // a description exists, otherwise just the name; matches the resource
    // spec dropdown on the job submit page
    deviceGroupLabel(group) {
      const desc = (group && group.description) || ''
      return desc ? `${group.name} (${desc})` : (group ? group.name : '')
    },

    // Build the HTML string used as the el-tooltip content for a device
    // group option; mirrors the flavor dropdown on the job submit page
    deviceGroupTooltipHtml(group) {
      if (!group || !group.description) return ''
      const rows = [
        ['名称', group.name],
        ['描述', group.description]
      ]
      const rowStyle = 'display:flex;align-items:flex-start;gap:8px;line-height:1.5;'
      const labelStyle = 'font-weight:600;opacity:0.85;min-width:56px;display:inline-block;'
      const rowsHtml = rows.map(([label, value]) =>
        `<div style="${rowStyle}"><span style="${labelStyle}">${label}:</span><span>${value}</span></div>`
      ).join('')
      return `<div style="display:flex;flex-direction:column;gap:4px;font-size:12px;max-width:380px;word-break:break-all;">${rowsHtml}</div>`
    },

    viewFlavorDetails(flavorId) {
      this.$router.push({ name: 'FlavorDetails', params: { flavorId: flavorId }})
    },

    // open the create dialog
    openCreateDialog() {
      this.formMode = 'create'
      this.editingFlavorId = null
      this.formData = {
        name: '',
        description: '',
        is_public: true,
        min_qubits: null,
        max_qubits: null,
        gate_fidelity_1q_min: null,
        gate_fidelity_2q_min: null,
        device_groups: [],
        project_id: ''
      }
      this.extraPropertiesList = []
      this.showFormDialog = true
    },

    // open the update dialog with row data pre-filled
    openUpdateDialog(row) {
      this.formMode = 'update'
      this.editingFlavorId = row.id
      this.formData = {
        name: row.name || '',
        description: row.description || '',
        is_public: !!row.is_public,
        min_qubits: row.min_qubits ?? null,
        max_qubits: row.max_qubits ?? null,
        gate_fidelity_1q_min: row.gate_fidelity_1q_min ?? null,
        gate_fidelity_2q_min: row.gate_fidelity_2q_min ?? null,
        device_groups: Array.isArray(row.device_groups) ? [...row.device_groups] : [],
        project_id: row.project_id || ''
      }
      // pre-fill extra properties list from row data
      this.extraPropertiesList = []
      if (row.extra_properties && typeof row.extra_properties === 'object') {
        for (const key in row.extra_properties) {
          this.extraPropertiesList.push({ key: key, value: String(row.extra_properties[key]) })
        }
      }
      this.showFormDialog = true
    },

    addExtraProperty() {
      this.extraPropertiesList.push({ key: '', value: '' })
    },

    removeExtraProperty(index) {
      this.extraPropertiesList.splice(index, 1)
    },

    buildExtraProperties() {
      const result = {}
      for (const item of this.extraPropertiesList) {
        if (item.key && item.key.trim()) {
          result[item.key.trim()] = item.value
        }
      }
      return Object.keys(result).length > 0 ? result : null
    },

    resetFormDialog() {
      this.formData = {
        name: '',
        description: '',
        is_public: true,
        min_qubits: null,
        max_qubits: null,
        gate_fidelity_1q_min: null,
        gate_fidelity_2q_min: null,
        device_groups: [],
        project_id: ''
      }
      this.extraPropertiesList = []
      this.editingFlavorId = null
      if (this.$refs.formRef) {
        this.$refs.formRef.clearValidate()
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
          description: this.formData.description || null,
          is_public: this.formData.is_public,
          min_qubits: this.formData.min_qubits,
          max_qubits: this.formData.max_qubits,
          gate_fidelity_1q_min: this.formData.gate_fidelity_1q_min,
          gate_fidelity_2q_min: this.formData.gate_fidelity_2q_min,
          device_groups: this.formData.device_groups
        }

        if (this.formData.project_id) {
          payload.project_id = this.formData.project_id
        }

        const extraProperties = this.buildExtraProperties()
        if (extraProperties) {
          payload.extra_properties = extraProperties
        }

        let response
        if (this.formMode === 'create') {
          response = await createFlavor(payload)
        } else {
          // update requires flavor_id
          payload.flavor_id = this.editingFlavorId
          response = await updateFlavor(payload)
        }

        if (!response.error) {
          this.$message.success(this.formMode === 'create' ? '资源规格创建成功' : '资源规格更新成功')
          this.showFormDialog = false
          this.resetFormDialog()
          this.$refs.pageTableRef.refresh()
        } else {
          this.$message.error(`${this.formMode === 'create' ? '创建' : '更新'}资源规格失败：${response.message || '未知错误'}`)
        }
      } catch (error) {
        console.error(`${this.formMode === 'create' ? '创建' : '更新'}资源规格失败:`, error)
        this.$message.error(`${this.formMode === 'create' ? '创建' : '更新'}资源规格失败，请检查网络连接`)
      } finally {
        this.submitting = false
      }
    },

    // track selected rows for batch operations
    handleSelectionChange(selection) {
      this.selectedRows = selection
    },

    // batch delete selected flavors
    handleBatchDelete() {
      const selectedRows = this.selectedRows
      if (selectedRows.length === 0) {
        this.$message.warning('请先选择要删除的资源规格')
        return
      }
      const ids = selectedRows.map(row => row.id)
      const names = selectedRows.map(row => row.name).join(', ')
      this.$confirm(`确定要删除选中的 ${selectedRows.length} 个资源规格（${names}）吗？`, '批量删除确认', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }).then(async() => {
        try {
          const response = await deleteFlavors(ids)
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
    }
  }
}
</script>

<style scoped>
.flavor-list-container {
  display: flex;
  flex-direction: column;
  background: var(--el-fill-color-light);
  padding: 20px;
  box-sizing: border-box;
}

.header { margin: 0; }

.form-hint {
  margin-left: 12px;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.extra-properties {
  width: 100%;
}

.extra-property-row {
  display: flex;
  align-items: center;
  margin-bottom: 10px;
  gap: 10px;
}

.extra-key-input {
  flex: 1;
}

.extra-value-input {
  flex: 2;
}

:deep(.el-form-item__label) {
  font-weight: 500;
}

/* device group option row -- mirrors the resource spec dropdown on the
   job submit page */
.device-group-option-row {
  display: flex;
  align-items: center;
  gap: 6px;
}

.device-group-option-row .group-desc {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}
</style>
