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
          <el-tooltip content="更新" placement="top">
            <el-button
              link
              type="primary"
              :icon="Edit"
              @click="openUpdateDialog(scope.row)"
            />
          </el-tooltip>
          <el-tooltip content="查看" placement="top">
            <el-button
              link
              :icon="View"
              @click="viewGroupDetails(scope.row.id)"
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
          >
            <el-option
              v-for="device in deviceOptions"
              :key="device.name"
              :label="device.alias_name ? (device.alias_name + ' (' + device.name + ')') : device.name"
              :value="device.name"
            />
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
</style>
