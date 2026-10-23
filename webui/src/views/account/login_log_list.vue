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
  <div class="login-log-list-container">
    <div class="header">
      <h2>登录日志</h2>
    </div>
    <PageTable
      ref="pageTableRef"
      :fetch-data="fetchLoginLogs"
      search-placeholder="全局搜索：用户名 / 用户ID / IP / 登录状态 …"
    >
      <template #toolbar-actions>
        <el-button
          type="warning"
          size="small"
          :icon="Delete"
          @click="openClearDialog"
        >
          清空日志
        </el-button>
      </template>
      <filterable-table-column
        prop="user_name"
        label="用户名"
        fixed="left"
        class-name="center-column"
        sortable="custom"
      />
      <filterable-table-column
        prop="user_id"
        label="用户ID"
        fixed="left"
        class-name="center-column"
        sortable="custom"
      />
      <filterable-table-column
        prop="project_id"
        label="项目ID"
        class-name="center-column"
        sortable="custom"
      />
      <filterable-table-column
        prop="login_time"
        label="登录时间"
        class-name="center-column"
        sortable="custom"
      />
      <filterable-table-column
        prop="ip_address"
        label="IP地址"
        class-name="center-column"
        sortable="custom"
      />
      <filterable-table-column
        prop="login_status"
        label="登录状态"
        class-name="center-column"
        sortable="custom"
      >
        <template #default="scope">
          <el-tag :type="scope.row.login_status ? 'success' : 'danger'">
            {{ scope.row.login_status ? '成功' : '失败' }}
          </el-tag>
        </template>
      </filterable-table-column>
      <filterable-table-column
        prop="failure_reason"
        label="失败原因"
        class-name="left-column"
        sortable="custom"
      />
    </PageTable>

    <!-- clear login logs dialog -->
    <el-dialog
      v-model="showClearDialog"
      title="清空登录日志"
      width="480px"
      align-center
      draggable
      @close="resetClearForm"
    >
      <el-form label-width="100px" label-position="right">
        <el-form-item label="清空范围">
          <el-radio-group v-model="clearForm.scope">
            <!-- non-admin users can only clear their own logs -->
            <el-radio v-if="isAdmin" value="all">全部</el-radio>
            <el-radio v-if="isAdmin" value="user_id">按用户ID</el-radio>
            <el-radio v-if="isAdmin" value="user_name">按用户名</el-radio>
            <el-radio value="self">本用户</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item
          v-if="clearForm.scope === 'user_id'"
          label="用户ID"
        >
          <el-input
            v-model="clearForm.user_id"
            placeholder="请输入用户ID (UUID)"
            clearable
          />
        </el-form-item>
        <el-form-item
          v-if="clearForm.scope === 'user_name'"
          label="用户名"
        >
          <el-input
            v-model="clearForm.user_name"
            placeholder="请输入用户名"
            clearable
          />
        </el-form-item>
        <el-form-item
          v-if="clearForm.scope === 'self'"
          label="当前用户"
        >
          <el-input
            :model-value="`${currentUserName} (${currentUserId})`"
            disabled
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showClearDialog = false">取消</el-button>
        <el-button
          type="warning"
          :loading="clearing"
          @click="submitClearLogs"
        >
          确定清空
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { markRaw, computed } from 'vue'
import { Delete } from '@element-plus/icons-vue'
import PageTable from '@/components/PageTable'
import FilterableTableColumn from '@/components/PageTable/FilterableTableColumn.vue'
import { getLoginLogs, clearLoginLogs } from '@/api/account'
import { useUserStore } from '@/store/modules/user'

export default {
  components: {
    PageTable,
    FilterableTableColumn
  },
  setup() {
    const userStore = useUserStore()
    // expose admin flag and current user identity to the template so the
    // clear-scope radio can hide admin-only options for regular users
    const isAdmin = computed(() => userStore.isAdmin)
    const currentUserId = computed(() => userStore.userId)
    const currentUserName = computed(() => userStore.name)
    return { isAdmin, currentUserId, currentUserName }
  },
  data() {
    return {
      Delete: markRaw(Delete),
      // clear login logs dialog state
      showClearDialog: false,
      clearing: false,
      clearForm: {
        scope: 'all',
        user_id: '',
        user_name: ''
      }
    }
  },
  methods: {
    // PageTable fetchData callback
    async fetchLoginLogs(params) {
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
      return await getLoginLogs(query)
    },

    // open the clear login logs dialog
    openClearDialog() {
      // default to 'self' for non-admin users so the only visible option
      // is pre-selected; admins keep the previous default ('all')
      const defaultScope = this.isAdmin ? 'all' : 'self'
      this.clearForm = { scope: defaultScope, user_id: '', user_name: '' }
      this.showClearDialog = true
    },

    resetClearForm() {
      const defaultScope = this.isAdmin ? 'all' : 'self'
      this.clearForm = { scope: defaultScope, user_id: '', user_name: '' }
    },

    // submit clear login logs request based on selected scope
    async submitClearLogs() {
      const scope = this.clearForm.scope
      // validate required input when filtering by user
      if (scope === 'user_id' && !this.clearForm.user_id.trim()) {
        this.$message.warning('请输入用户ID')
        return
      }
      if (scope === 'user_name' && !this.clearForm.user_name.trim()) {
        this.$message.warning('请输入用户名')
        return
      }
      // 'self' scope requires the current user's id; if it's missing the
      // user info has not been loaded yet, so block the action
      if (scope === 'self' && !this.currentUserId) {
        this.$message.error('当前用户信息未加载，无法清空本用户日志')
        return
      }

      const scopeLabel = scope === 'all'
        ? '全部'
        : (scope === 'user_id'
          ? `用户ID: ${this.clearForm.user_id}`
          : (scope === 'user_name'
            ? `用户名: ${this.clearForm.user_name}`
            : `本用户 (${this.currentUserName})`))
      this.$confirm(`确定要清空登录日志（${scopeLabel}）吗？此操作不可恢复`, '清空确认', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }).then(async() => {
        this.clearing = true
        try {
          const payload = {}
          if (scope === 'user_id') {
            payload.user_id = this.clearForm.user_id.trim()
          } else if (scope === 'user_name') {
            payload.user_name = this.clearForm.user_name.trim()
          } else if (scope === 'self') {
            // non-admin users can only clear their own logs by user_id
            payload.user_id = this.currentUserId
          }
          const response = await clearLoginLogs(payload)
          if (!response.error) {
            const count = (response.result && response.result.count) || 0
            this.$message.success(`已清空 ${count} 条登录日志`)
            this.showClearDialog = false
            this.$refs.pageTableRef.refresh()
          } else {
            this.$message.error(`清空登录日志失败：${response.message || '未知错误'}`)
          }
        } catch (error) {
          console.error('清空登录日志失败:', error)
          this.$message.error('清空登录日志失败，请检查网络连接')
        } finally {
          this.clearing = false
        }
      }).catch(() => {
        this.$message.info('已取消清空')
      })
    }
  }
}
</script>

<style scoped>
.login-log-list-container {
  display: flex;
  flex-direction: column;
  background: var(--el-fill-color-light);
  padding: 20px;
  box-sizing: border-box;
}

.header { margin: 0; }
</style>
