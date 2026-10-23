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
  <div class="role-list-container">
    <div class="header">
      <h2>角色管理</h2>
    </div>
    <PageTable
      ref="pageTableRef"
      :fetch-data="fetchRoles"
      search-placeholder="全局搜索：角色ID / 名称 / 权限 / 描述 …"
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
          新增角色
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
        prop="id"
        label="角色ID"
        fixed="left"
        class-name="center-column"
        sortable="custom"
      />
      <filterable-table-column
        prop="role_name"
        label="角色名称"
        fixed="left"
        class-name="center-column"
        sortable="custom"
      />
      <filterable-table-column
        prop="permissions"
        label="权限"
        class-name="left-column"
        sortable="custom"
      >
        <template #default="scope">
          {{ formatPermissions(scope.row.permissions) }}
        </template>
      </filterable-table-column>
      <filterable-table-column
        prop="description"
        label="描述"
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
              @click="viewRoleDetails(scope.row.id)"
            />
          </el-tooltip>
        </template>
      </el-table-column>
    </PageTable>

    <!-- create/update role dialog -->
    <el-dialog
      v-model="showFormDialog"
      :title="formMode === 'create' ? '新增角色' : '更新角色'"
      width="500px"
      align-center
      draggable
      @close="resetFormDialog"
    >
      <el-form
        ref="formRef"
        :model="formData"
        :rules="formRules"
        label-width="100px"
        label-position="right"
      >
        <el-form-item label="角色名称" prop="role_name">
          <el-input
            v-model="formData.role_name"
            placeholder="请输入角色名称"
            maxlength="64"
            show-word-limit
          />
        </el-form-item>

        <el-form-item label="权限" prop="permissions">
          <el-select
            v-model="formData.permissions"
            multiple
            filterable
            allow-create
            default-first-option
            placeholder="输入权限路径后回车（如 /version 或 * ）"
            style="width: 100%"
          >
            <el-option label="全部权限 (*)" value="*" />
            <el-option label="/version" value="/version" />
            <el-option label="/v1/device/get_devices" value="/v1/device/get_devices" />
            <el-option label="/v1/device/get_device" value="/v1/device/get_device" />
            <el-option label="/v1/job" value="/v1/job" />
          </el-select>
        </el-form-item>

        <el-form-item label="描述" prop="description">
          <el-input
            v-model="formData.description"
            type="textarea"
            :rows="3"
            placeholder="请输入角色描述（可选）"
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
import { getRoles, createRole, updateRole, deleteRole } from '@/api/account'

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
      // selected rows for batch operations
      selectedRows: [],
      // create/update dialog state
      formMode: 'create',
      showFormDialog: false,
      submitting: false,
      // current editing role id (for update mode)
      editingRoleId: null,
      formData: {
        role_name: '',
        permissions: [],
        description: ''
      },
      formRules: {
        role_name: [
          { required: true, message: '请输入角色名称', trigger: 'blur' },
          { min: 2, max: 64, message: '名称长度在 2 到 64 个字符', trigger: 'blur' }
        ]
      }
    }
  },
  methods: {
    // PageTable fetchData callback
    async fetchRoles(params) {
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
      return await getRoles(query)
    },

    handleSelectionChange(selection) {
      this.selectedRows = selection
    },

    viewRoleDetails(roleId) {
      this.$router.push({ name: 'RoleDetails', params: { roleId: roleId }})
    },

    // open the create dialog
    openCreateDialog() {
      this.formMode = 'create'
      this.editingRoleId = null
      this.formData = { role_name: '', permissions: [], description: '' }
      this.showFormDialog = true
    },

    // open the update dialog with row data pre-filled
    openUpdateDialog(row) {
      this.formMode = 'update'
      this.editingRoleId = row.id
      // normalize permissions to an array for the multi-select
      let perms = row.permissions
      if (!perms) {
        perms = []
      } else if (Array.isArray(perms)) {
        perms = [...perms]
      } else if (typeof perms === 'object') {
        perms = Object.keys(perms)
      } else {
        perms = [String(perms)]
      }
      this.formData = {
        role_name: row.role_name || '',
        permissions: perms,
        description: row.description || ''
      }
      this.showFormDialog = true
    },

    resetFormDialog() {
      this.formData = { role_name: '', permissions: [], description: '' }
      this.editingRoleId = null
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
          role_name: this.formData.role_name,
          permissions: this.formData.permissions
        }
        if (this.formData.description) {
          payload.description = this.formData.description
        }

        let response
        if (this.formMode === 'create') {
          response = await createRole(payload)
        } else {
          // update requires role_id
          payload.role_id = this.editingRoleId
          response = await updateRole(payload)
        }

        if (!response.error) {
          this.$message.success(this.formMode === 'create' ? '角色创建成功' : '角色更新成功')
          this.showFormDialog = false
          this.$refs.pageTableRef.refresh()
        } else {
          this.$message.error(`${this.formMode === 'create' ? '创建' : '更新'}角色失败：${response.message || '未知错误'}`)
        }
      } catch (error) {
        console.error(`${this.formMode === 'create' ? '创建' : '更新'}角色失败:`, error)
        this.$message.error(`${this.formMode === 'create' ? '创建' : '更新'}角色失败，请检查网络连接`)
      } finally {
        this.submitting = false
      }
    },

    // batch delete selected roles (backend supports single delete,
    // so we loop over selected rows and delete one by one)
    handleBatchDelete() {
      const ids = this.selectedRows.map(row => row.id)
      const names = this.selectedRows.map(row => row.role_name).join(', ')
      this.$confirm(`确定要删除选中的 ${this.selectedRows.length} 个角色（${names}）吗？`, '批量删除确认', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }).then(async() => {
        let failCount = 0
        for (const id of ids) {
          try {
            const response = await deleteRole(id)
            if (response.error) {
              failCount++
            }
          } catch (error) {
            console.error('删除角色失败:', error)
            failCount++
          }
        }
        this.$refs.pageTableRef.refresh()
        if (failCount === 0) {
          this.$message.success('批量删除成功')
        } else {
          this.$message.warning(`批量删除完成，其中 ${failCount} 个角色删除失败`)
        }
      }).catch(() => {
        this.$message.info('已取消批量删除')
      })
    },

    formatPermissions(permissions) {
      if (!permissions) return '-'
      if (Array.isArray(permissions)) {
        return permissions.join(', ') || '-'
      }
      if (typeof permissions === 'object') {
        return Object.keys(permissions).join(', ') || '-'
      }
      return String(permissions)
    }
  }
}
</script>

<style scoped>
.role-list-container {
  display: flex;
  flex-direction: column;
  background: var(--el-fill-color-light);
  padding: 20px;
  box-sizing: border-box;
}

.header { margin: 0; }
</style>
