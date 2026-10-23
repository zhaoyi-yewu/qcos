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
  <div class="user-list-container">
    <div class="header">
      <h2>用户管理</h2>
    </div>
    <PageTable
      ref="pageTableRef"
      :fetch-data="fetchUsers"
      search-placeholder="全局搜索：用户ID / 用户名 / 角色 / 状态 …"
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
          新增用户
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
        label="用户ID"
        fixed="left"
        class-name="center-column"
        sortable="custom"
      />
      <filterable-table-column
        prop="user_name"
        label="用户名"
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
        prop="roles"
        label="角色"
        class-name="center-column"
        sortable="custom"
      >
        <template #default="scope">
          {{ formatRoles(scope.row.roles) }}
        </template>
      </filterable-table-column>
      <filterable-table-column
        prop="is_enabled"
        label="启用"
        class-name="center-column"
        sortable="custom"
      >
        <template #default="scope">
          <el-tag :type="scope.row.is_enabled ? 'success' : 'danger'">
            {{ scope.row.is_enabled ? '是' : '否' }}
          </el-tag>
        </template>
      </filterable-table-column>
      <filterable-table-column
        prop="is_locked"
        label="锁定"
        class-name="center-column"
        sortable="custom"
      >
        <template #default="scope">
          <el-tag :type="scope.row.is_locked ? 'danger' : 'success'">
            {{ scope.row.is_locked ? '是' : '否' }}
          </el-tag>
        </template>
      </filterable-table-column>
      <filterable-table-column
        prop="password_expiry_days"
        label="密码到期天数"
        class-name="center-column"
        sortable="custom"
      />
      <filterable-table-column
        prop="last_login"
        label="最后登录"
        class-name="center-column"
        sortable="custom"
      />
      <filterable-table-column
        prop="password_changed_at"
        label="密码修改时间"
        class-name="center-column"
        sortable="custom"
      />
      <filterable-table-column
        prop="locked_until"
        label="锁定截止时间"
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
              @click="viewUserDetails(scope.row.id)"
            />
          </el-tooltip>
        </template>
      </el-table-column>
    </PageTable>

    <!-- create/update user dialog -->
    <el-dialog
      v-model="showFormDialog"
      :title="formMode === 'create' ? '新增用户' : '更新用户'"
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
        <!-- user_name and password are only editable when creating -->
        <el-form-item v-if="formMode === 'create'" label="用户名" prop="user_name">
          <el-input
            v-model="formData.user_name"
            placeholder="请输入用户名"
            maxlength="64"
            show-word-limit
          />
        </el-form-item>

        <el-form-item v-if="formMode === 'create'" label="密码" prop="password">
          <el-input
            v-model="formData.password"
            type="password"
            show-password
            placeholder="请输入密码"
            maxlength="128"
          />
        </el-form-item>

        <!-- allow changing password in update mode (optional) -->
        <el-form-item v-if="formMode === 'update'" label="新密码" prop="new_password">
          <el-input
            v-model="formData.new_password"
            type="password"
            show-password
            placeholder="留空则不修改密码"
            maxlength="128"
          />
        </el-form-item>

        <el-form-item v-if="formMode === 'update'" label="确认新密码" prop="confirm_password">
          <el-input
            v-model="formData.confirm_password"
            type="password"
            show-password
            placeholder="请再次输入新密码"
            maxlength="128"
          />
        </el-form-item>

        <el-form-item v-if="formMode === 'create'" label="所属项目ID" prop="project_id">
          <el-input
            v-model="formData.project_id"
            placeholder="留空则使用默认项目"
          />
        </el-form-item>

        <el-form-item label="角色" prop="roles">
          <el-select
            v-model="formData.roles"
            multiple
            filterable
            allow-create
            default-first-option
            placeholder="请选择或输入角色名称"
            style="width: 100%"
            :loading="roleLoading"
          >
            <el-option
              v-for="role in roleOptions"
              :key="role.id"
              :label="role.role_name"
              :value="role.role_name"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="密码到期天数" prop="password_expiry_days">
          <el-input-number
            v-model="formData.password_expiry_days"
            :min="0"
            :step="1"
            controls-position="right"
            placeholder="留空表示不限制"
          />
        </el-form-item>

        <el-form-item label="是否启用" prop="is_enabled">
          <el-switch v-model="formData.is_enabled" />
        </el-form-item>

        <el-form-item label="描述" prop="description">
          <el-input
            v-model="formData.description"
            type="textarea"
            :rows="3"
            placeholder="请输入用户描述（可选）"
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
import { getUsers, createUser, updateUser, deleteUser, getRoles, changePassword } from '@/api/account'

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
      roleLoading: false,
      roleOptions: [],
      // current editing user id (for update mode)
      editingUserId: null,
      formData: {
        user_name: '',
        password: '',
        new_password: '',
        confirm_password: '',
        project_id: '',
        roles: ['user'],
        password_expiry_days: null,
        is_enabled: true,
        description: ''
      },
      formRules: {
        user_name: [
          { required: true, message: '请输入用户名', trigger: 'blur' },
          { min: 1, max: 64, message: '用户名长度在 1 到 64 个字符', trigger: 'blur' }
        ],
        password: [
          { required: true, message: '请输入密码', trigger: 'blur' },
          { min: 1, max: 128, message: '密码长度在 1 到 128 个字符', trigger: 'blur' }
        ],
        new_password: [
          { validator: (rule, value, callback) => {
            // empty means no password change; otherwise length 1-128
            if (value === '' || value === null || value === undefined) {
              callback()
            } else if (value.length > 128) {
              callback(new Error('密码长度不能超过 128 个字符'))
            } else {
              callback()
            }
          }, trigger: 'blur' }
        ],
        confirm_password: [
          { validator: (rule, value, callback) => {
            const newPwd = this.formData.new_password
            if (!newPwd) {
              callback()
            } else if (value !== newPwd) {
              callback(new Error('两次输入的密码不一致'))
            } else {
              callback()
            }
          }, trigger: 'blur' }
        ]
      }
    }
  },
  watch: {
    // load role options when create/update dialog opens
    showFormDialog(newVal) {
      if (newVal && this.roleOptions.length === 0) {
        this.fetchRoleOptions()
      }
    }
  },
  methods: {
    // PageTable fetchData callback
    async fetchUsers(params) {
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
      return await getUsers(query)
    },

    handleSelectionChange(selection) {
      this.selectedRows = selection
    },

    viewUserDetails(userId) {
      this.$router.push({ name: 'UserDetails', params: { userId: userId }})
    },

    async fetchRoleOptions() {
      this.roleLoading = true
      try {
        const response = await getRoles()
        if (!response.error) {
          const roles = response.result
          this.roleOptions = []
          for (const roleId in roles) {
            const role = roles[roleId]
            this.roleOptions.push(role)
          }
        }
      } catch (error) {
        console.error('获取角色列表失败:', error)
      } finally {
        this.roleLoading = false
      }
    },

    // open the create dialog
    openCreateDialog() {
      this.formMode = 'create'
      this.editingUserId = null
      this.formData = {
        user_name: '',
        password: '',
        new_password: '',
        confirm_password: '',
        project_id: '',
        roles: ['user'],
        password_expiry_days: null,
        is_enabled: true,
        description: ''
      }
      this.showFormDialog = true
    },

    // open the update dialog with row data pre-filled;
    // user_name and password are not editable in update mode
    openUpdateDialog(row) {
      this.formMode = 'update'
      this.editingUserId = row.id
      // normalize roles to an array for the multi-select
      let roles = row.roles
      if (!roles) {
        roles = []
      } else if (Array.isArray(roles)) {
        roles = [...roles]
      } else if (typeof roles === 'object') {
        roles = Object.keys(roles)
      } else {
        roles = [String(roles)]
      }
      this.formData = {
        user_name: row.user_name || '',
        password: '',
        new_password: '',
        confirm_password: '',
        project_id: row.project_id || '',
        roles: roles,
        password_expiry_days: row.password_expiry_days ?? null,
        is_enabled: !!row.is_enabled,
        description: row.description || ''
      }
      this.showFormDialog = true
    },

    resetFormDialog() {
      this.formData = {
        user_name: '',
        password: '',
        new_password: '',
        confirm_password: '',
        project_id: '',
        roles: ['user'],
        password_expiry_days: null,
        is_enabled: true,
        description: ''
      }
      this.editingUserId = null
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
        let response
        if (this.formMode === 'create') {
          const payload = {
            user_name: this.formData.user_name,
            password: this.formData.password,
            roles: this.formData.roles,
            is_enabled: this.formData.is_enabled
          }
          if (this.formData.project_id) {
            payload.project_id = this.formData.project_id
          }
          if (this.formData.password_expiry_days !== null) {
            payload.password_expiry_days = this.formData.password_expiry_days
          }
          if (this.formData.description) {
            payload.description = this.formData.description
          }
          response = await createUser(payload)
        } else {
          // update_user only allows roles/description/is_enabled/
          // is_locked/password_expiry_days; user_name is NOT editable here
          const payload = {
            user_id: this.editingUserId,
            roles: this.formData.roles,
            is_enabled: this.formData.is_enabled
          }
          if (this.formData.password_expiry_days !== null) {
            payload.password_expiry_days = this.formData.password_expiry_days
          }
          if (this.formData.description) {
            payload.description = this.formData.description
          }
          response = await updateUser(payload)

          // change password separately when new_password is filled
          if (!response.error && this.formData.new_password) {
            const pwdResp = await changePassword({
              user_id: this.editingUserId,
              new_password: this.formData.new_password
            })
            if (pwdResp.error) {
              this.$message.warning(`用户信息已更新，但修改密码失败：${pwdResp.message || '未知错误'}`)
              this.showFormDialog = false
              this.$refs.pageTableRef.refresh()
              this.submitting = false
              return
            }
          }
        }

        if (!response.error) {
          this.$message.success(this.formMode === 'create' ? '用户创建成功' : '用户更新成功')
          this.showFormDialog = false
          this.$refs.pageTableRef.refresh()
        } else {
          this.$message.error(`${this.formMode === 'create' ? '创建' : '更新'}用户失败：${response.message || '未知错误'}`)
        }
      } catch (error) {
        console.error(`${this.formMode === 'create' ? '创建' : '更新'}用户失败:`, error)
        this.$message.error(`${this.formMode === 'create' ? '创建' : '更新'}用户失败，请检查网络连接`)
      } finally {
        this.submitting = false
      }
    },

    // batch delete selected users (backend supports single delete,
    // so we loop over selected rows and delete one by one)
    handleBatchDelete() {
      const ids = this.selectedRows.map(row => row.id)
      const names = this.selectedRows.map(row => row.user_name).join(', ')
      this.$confirm(`确定要删除选中的 ${this.selectedRows.length} 个用户（${names}）吗？`, '批量删除确认', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }).then(async() => {
        let failCount = 0
        for (const id of ids) {
          try {
            const response = await deleteUser(id)
            if (response.error) {
              failCount++
            }
          } catch (error) {
            console.error('删除用户失败:', error)
            failCount++
          }
        }
        this.$refs.pageTableRef.refresh()
        if (failCount === 0) {
          this.$message.success('批量删除成功')
        } else {
          this.$message.warning(`批量删除完成，其中 ${failCount} 个用户删除失败`)
        }
      }).catch(() => {
        this.$message.info('已取消批量删除')
      })
    },

    formatRoles(roles) {
      if (!roles) return '-'
      if (Array.isArray(roles)) {
        return roles.join(', ') || '-'
      }
      if (typeof roles === 'object') {
        return Object.keys(roles).join(', ') || '-'
      }
      return String(roles)
    }
  }
}
</script>

<style scoped>
.user-list-container {
  display: flex;
  flex-direction: column;
  background: var(--el-fill-color-light);
  padding: 20px;
  box-sizing: border-box;
}

.header { margin: 0; }
</style>
