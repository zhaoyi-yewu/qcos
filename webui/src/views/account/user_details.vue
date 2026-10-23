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
  <div v-if="loaded" class="user-detail-container">
    <div class="header">
      <h2>用户详情</h2>
    </div>
    <div class="detail-container">
      <el-card class="detail-card">
        <div class="detail-header">
          <h2>{{ userDetails.user_name || '未命名' }}</h2>
          <el-button
            type="primary"
            size="small"
            :icon="Edit"
            @click="openUpdateDialog"
          >
            更新信息
          </el-button>
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

    <el-dialog
      v-model="showUpdateDialog"
      title="更新用户"
      width="600px"
      align-center
      draggable
      @close="resetUpdateForm"
    >
      <el-form
        ref="formRef"
        :model="formData"
        :rules="formRules"
        label-width="120px"
        label-position="right"
      >
        <el-form-item label="用户名">
          <el-input
            :model-value="formData.user_name"
            disabled
          />
        </el-form-item>

        <el-form-item label="所属项目ID">
          <el-input
            :model-value="formData.project_id"
            disabled
          />
        </el-form-item>

        <el-form-item label="新密码" prop="new_password">
          <el-input
            v-model="formData.new_password"
            type="password"
            show-password
            placeholder="留空则不修改密码"
            maxlength="128"
          />
        </el-form-item>

        <el-form-item label="确认新密码" prop="confirm_password">
          <el-input
            v-model="formData.confirm_password"
            type="password"
            show-password
            placeholder="请再次输入新密码"
            maxlength="128"
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
            placeholder="0 表示不限制"
          />
        </el-form-item>

        <el-form-item label="是否启用" prop="is_enabled">
          <el-switch v-model="formData.is_enabled" />
        </el-form-item>

        <el-form-item label="是否锁定" prop="is_locked">
          <el-switch v-model="formData.is_locked" />
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
        <el-button @click="showUpdateDialog = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitUpdateForm">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { markRaw } from 'vue'
import { Edit } from '@element-plus/icons-vue'
import { getUser, updateUser, getRoles, changePassword } from '@/api/account'

export default {
  name: 'UserDetails',
  data() {
    return {
      loaded: false,
      userId: this.$route.params.userId,
      userDetails: {
        id: '',
        project_id: '',
        user_name: '',
        roles: null,
        is_enabled: false,
        is_locked: false,
        password_expiry_days: null,
        last_login: null,
        password_changed_at: '',
        locked_until: null,
        description: '',
        created_at: '',
        updated_at: ''
      },
      leftItems: [],
      rightItems: [],
      // update dialog state
      Edit: markRaw(Edit),
      showUpdateDialog: false,
      submitting: false,
      roleLoading: false,
      roleOptions: [],
      formData: {
        user_name: '',
        project_id: '',
        new_password: '',
        confirm_password: '',
        roles: [],
        password_expiry_days: null,
        is_enabled: true,
        is_locked: false,
        description: ''
      },
      formRules: {
        new_password: [
          { validator: (rule, value, callback) => {
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
    '$route.params.userId'(newVal) {
      if (newVal !== this.userId) {
        this.userId = newVal
        this.queryData()
      }
    }
  },
  created() {
    this.queryData()
  },
  methods: {
    formatRoles(roles) {
      if (!roles) return '-'
      if (Array.isArray(roles)) {
        return roles.join(', ') || '-'
      }
      if (typeof roles === 'object') {
        return Object.keys(roles).join(', ') || '-'
      }
      return String(roles)
    },

    formatBool(val) {
      if (val === true) return '是'
      if (val === false) return '否'
      return '-'
    },

    async queryData() {
      await this.fetchUserDetails()
      this.formatItems()
      this.loaded = true
    },

    async fetchUserDetails() {
      try {
        const response = await getUser(this.userId)
        if (!response.error) {
          this.userDetails = response.result
        } else {
          this.$message.error(`获取用户详情失败：${response.message || '未知错误'}`)
        }
      } catch (error) {
        console.error('获取用户详情失败:', error)
        this.$message.error('获取用户详情失败，请检查网络连接')
      }
    },

    formatItems() {
      const d = this.userDetails
      this.leftItems = [
        { label: '用户ID', value: d.id || '-', color: '#409EFF' },
        { label: '用户名', value: d.user_name || '-', color: '#409EFF' },
        { label: '所属项目ID', value: d.project_id || '-', color: '#409EFF' },
        { label: '角色', value: this.formatRoles(d.roles), color: '#409EFF' },
        { label: '启用', value: this.formatBool(d.is_enabled), color: '#409EFF' },
        { label: '锁定', value: this.formatBool(d.is_locked), color: '#409EFF' },
        { label: '描述', value: d.description || '未填写', color: '#409EFF' }
      ]
      this.rightItems = [
        { label: '密码到期天数', value: d.password_expiry_days ?? '-', color: '#67C23A' },
        { label: '最后登录', value: d.last_login || '-', color: '#67C23A' },
        { label: '密码修改时间', value: d.password_changed_at || '-', color: '#67C23A' },
        { label: '锁定截止时间', value: d.locked_until || '-', color: '#67C23A' },
        { label: '创建时间', value: d.created_at || '-', color: '#67C23A' },
        { label: '更新时间', value: d.updated_at || '-', color: '#67C23A' }
      ]
    },

    // normalize roles value to an array for multi-select binding
    normalizeRoles(roles) {
      if (!roles) return []
      if (Array.isArray(roles)) return [...roles]
      if (typeof roles === 'object') return Object.keys(roles)
      return [String(roles)]
    },

    // fetch role options for the select dropdown
    async fetchRoleOptions() {
      this.roleLoading = true
      try {
        const response = await getRoles()
        if (!response.error) {
          const roles = response.result
          this.roleOptions = []
          for (const roleId in roles) {
            this.roleOptions.push(roles[roleId])
          }
        }
      } catch (error) {
        console.error('获取角色列表失败:', error)
      } finally {
        this.roleLoading = false
      }
    },

    // open the update dialog with current user details pre-filled
    openUpdateDialog() {
      const d = this.userDetails
      this.formData = {
        user_name: d.user_name || '',
        project_id: d.project_id || '',
        new_password: '',
        confirm_password: '',
        roles: this.normalizeRoles(d.roles),
        password_expiry_days: d.password_expiry_days ?? null,
        is_enabled: !!d.is_enabled,
        is_locked: !!d.is_locked,
        description: d.description || ''
      }
      if (this.roleOptions.length === 0) {
        this.fetchRoleOptions()
      }
      this.showUpdateDialog = true
    },

    // reset update form when dialog closes
    resetUpdateForm() {
      this.formData = {
        user_name: '',
        project_id: '',
        new_password: '',
        confirm_password: '',
        roles: [],
        password_expiry_days: null,
        is_enabled: true,
        is_locked: false,
        description: ''
      }
      if (this.$refs.formRef) {
        this.$refs.formRef.resetFields()
      }
    },

    // submit update user request
    async submitUpdateForm() {
      try {
        await this.$refs.formRef.validate()
      } catch {
        return
      }

      this.submitting = true
      try {
        const payload = {
          user_id: this.userId,
          roles: this.formData.roles,
          is_enabled: this.formData.is_enabled,
          is_locked: this.formData.is_locked
        }
        if (this.formData.password_expiry_days !== null) {
          payload.password_expiry_days = this.formData.password_expiry_days
        }
        if (this.formData.description) {
          payload.description = this.formData.description
        }
        const response = await updateUser(payload)

        // change password separately when new_password is filled
        if (!response.error && this.formData.new_password) {
          const pwdResp = await changePassword({
            user_id: this.userId,
            new_password: this.formData.new_password
          })
          if (pwdResp.error) {
            this.$message.warning(`用户信息已更新，但修改密码失败：${pwdResp.message || '未知错误'}`)
            this.showUpdateDialog = false
            await this.queryData()
            this.submitting = false
            return
          }
        }

        if (!response.error) {
          this.$message.success('用户更新成功')
          this.showUpdateDialog = false
          await this.queryData()
        } else {
          this.$message.error(`更新用户失败：${response.message || '未知错误'}`)
        }
      } catch (error) {
        console.error('更新用户失败:', error)
        this.$message.error('更新用户失败，请检查网络连接')
      } finally {
        this.submitting = false
      }
    }
  }
}
</script>

<style scoped>
.user-detail-container {
  padding: 10px;
}

.header { margin: 0; }

.detail-container {
  background: var(--el-bg-color);
}

.detail-card {
  box-shadow: 0 5px 12px rgba(0, 0, 0, 0.1);
  border-radius: 10px;
  overflow: hidden;
}

.detail-header {
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
  white-space: pre-line;
  color: var(--el-text-color-regular);
  word-break: break-all;
}
</style>
