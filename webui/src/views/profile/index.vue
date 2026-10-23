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
      <h2>用户信息</h2>
    </div>
    <div class="detail-container">
      <el-card class="detail-card">
        <div class="detail-header">
          <h2>{{ userInfo.user_name || '未命名' }}</h2>
          <el-button
            type="primary"
            size="small"
            :icon="Edit"
            @click="openEditDialog"
          >
            修改信息
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
      v-model="showEditDialog"
      title="修改个人信息"
      width="600px"
      align-center
      draggable
      @close="resetEditForm"
    >
      <el-form
        ref="formRef"
        :model="formData"
        :rules="formRules"
        label-width="120px"
        label-position="right"
      >
        <el-form-item label="用户名">
          <el-input :model-value="formData.user_name" disabled />
        </el-form-item>

        <el-form-item label="所属项目ID">
          <el-input :model-value="formData.project_id" disabled />
        </el-form-item>

        <el-form-item label="描述" prop="description">
          <el-input
            v-model="formData.description"
            type="textarea"
            :rows="3"
            placeholder="请输入个人描述（可选）"
          />
        </el-form-item>

        <el-divider content-position="left">修改密码（可选）</el-divider>

        <el-form-item label="原密码" prop="old_password">
          <el-input
            v-model="formData.old_password"
            type="password"
            show-password
            placeholder="修改密码时必填"
            maxlength="128"
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
      </el-form>
      <template #footer>
        <el-button @click="showEditDialog = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitEditForm">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { markRaw } from 'vue'
import { Edit } from '@element-plus/icons-vue'
import { getInfo } from '@/api/user'
import { updateUser, changePassword } from '@/api/account'

export default {
  name: 'ProfilePage',
  data() {
    return {
      loaded: false,
      Edit: markRaw(Edit),
      userInfo: {
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
      // edit dialog state
      showEditDialog: false,
      submitting: false,
      formData: {
        user_name: '',
        project_id: '',
        description: '',
        old_password: '',
        new_password: '',
        confirm_password: ''
      },
      formRules: {
        old_password: [
          { validator: (rule, value, callback) => {
            // old password is required only when user wants to change password
            if (this.formData.new_password && !value) {
              callback(new Error('修改密码时请输入原密码'))
            } else {
              callback()
            }
          }, trigger: 'blur' }
        ],
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
      await this.fetchUserInfo()
      this.formatItems()
      this.loaded = true
    },

    async fetchUserInfo() {
      try {
        const response = await getInfo()
        if (!response.error) {
          this.userInfo = response.result
        } else {
          this.$message.error(`获取用户信息失败：${response.message || '未知错误'}`)
        }
      } catch (error) {
        console.error('获取用户信息失败:', error)
        this.$message.error('获取用户信息失败，请检查网络连接')
      }
    },

    formatItems() {
      const d = this.userInfo
      this.leftItems = [
        { label: '用户ID', value: d.id || '-', color: '#409EFF' },
        { label: '用户名', value: d.user_name || '-', color: '#409EFF' },
        { label: '项目ID', value: d.project_id || '-', color: '#409EFF' },
        { label: '角色', value: this.formatRoles(d.roles), color: '#409EFF' },
        { label: '是否启用', value: this.formatBool(d.is_enabled), color: '#409EFF' },
        { label: '是否锁定', value: this.formatBool(d.is_locked), color: '#409EFF' },
        { label: '描述', value: d.description || '未填写', color: '#409EFF' }
      ]
      this.rightItems = [
        { label: '密码过期天数', value: d.password_expiry_days ?? '-', color: '#67C23A' },
        { label: '最后登录时间', value: d.last_login || '-', color: '#67C23A' },
        { label: '密码修改时间', value: d.password_changed_at || '-', color: '#67C23A' },
        { label: '锁定截止时间', value: d.locked_until || '-', color: '#67C23A' },
        { label: '创建时间', value: d.created_at || '-', color: '#67C23A' },
        { label: '更新时间', value: d.updated_at || '-', color: '#67C23A' }
      ]
    },

    // open edit dialog with current user info pre-filled
    openEditDialog() {
      const d = this.userInfo
      this.formData = {
        user_name: d.user_name || '',
        project_id: d.project_id || '',
        description: d.description || '',
        old_password: '',
        new_password: '',
        confirm_password: ''
      }
      this.showEditDialog = true
    },

    // reset edit form when dialog closes
    resetEditForm() {
      this.formData = {
        user_name: '',
        project_id: '',
        description: '',
        old_password: '',
        new_password: '',
        confirm_password: ''
      }
      if (this.$refs.formRef) {
        this.$refs.formRef.resetFields()
      }
    },

    // submit profile update: description via updateUser, password via changePassword
    async submitEditForm() {
      try {
        await this.$refs.formRef.validate()
      } catch {
        return
      }

      this.submitting = true
      try {
        // step 1: update description (and any other editable profile fields)
        const updateResp = await updateUser({
          user_id: this.userInfo.id,
          description: this.formData.description
        })
        if (updateResp.error) {
          this.$message.error(`更新个人信息失败：${updateResp.message || '未知错误'}`)
          this.submitting = false
          return
        }

        // step 2: change password when new_password is provided
        if (this.formData.new_password) {
          const pwdResp = await changePassword({
            user_id: this.userInfo.id,
            old_password: this.formData.old_password,
            new_password: this.formData.new_password
          })
          if (pwdResp.error) {
            this.$message.warning(`个人信息已更新，但修改密码失败：${pwdResp.message || '未知错误'}`)
            this.showEditDialog = false
            await this.queryData()
            this.submitting = false
            return
          }
        }

        this.$message.success('个人信息更新成功')
        this.showEditDialog = false
        await this.queryData()
      } catch (error) {
        console.error('更新个人信息失败:', error)
        this.$message.error('更新个人信息失败，请检查网络连接')
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

/* use element-plus variables so the card background follows the active
   color mode (white in 白天, dark panel in 夜晚) instead of hard-coded white */
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
  border-bottom: 1px solid var(--el-border-color-lighter);
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
  /* use element-plus primary text color so it stays readable in both
     light and dark modes (dark gray in light, light gray in dark) */
  color: var(--el-text-color-primary);
}

.timeline-content {
  white-space: pre-line;
  /* regular text color: slightly dimmer than primary but still readable
     on both light and dark backgrounds */
  color: var(--el-text-color-regular);
  word-break: break-all;
}
</style>
