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
  <div class="project-list-container">
    <div class="header">
      <h2>项目管理</h2>
    </div>
    <PageTable
      ref="pageTableRef"
      :fetch-data="fetchProjects"
      search-placeholder="全局搜索：项目ID / 名称 / 描述 …"
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
          新增项目
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
        label="项目ID"
        fixed="left"
        class-name="center-column"
        sortable="custom"
      />
      <filterable-table-column
        prop="name"
        label="项目名称"
        fixed="left"
        class-name="center-column"
        sortable="custom"
      />
      <filterable-table-column
        prop="description"
        label="项目描述"
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
          <el-tooltip content="查看" placement="top">
            <el-button
              link
              :icon="View"
              @click="viewProjectDetails(scope.row.id)"
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

    <!-- create/update project dialog -->
    <el-dialog
      v-model="showFormDialog"
      :title="formMode === 'create' ? '新增项目' : '更新项目'"
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
        <el-form-item label="项目名称" prop="project_name">
          <el-input
            v-model="formData.project_name"
            placeholder="请输入项目名称"
            maxlength="64"
            show-word-limit
          />
        </el-form-item>

        <el-form-item label="描述" prop="description">
          <el-input
            v-model="formData.description"
            type="textarea"
            :rows="3"
            placeholder="请输入项目描述（可选）"
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
import { getProjects, createProject, updateProject, deleteProject } from '@/api/account'

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
      // current editing project id (for update mode)
      editingProjectId: null,
      formData: {
        project_name: '',
        description: ''
      },
      formRules: {
        project_name: [
          { required: true, message: '请输入项目名称', trigger: 'blur' },
          { min: 1, max: 64, message: '名称长度在 1 到 64 个字符', trigger: 'blur' }
        ]
      }
    }
  },
  methods: {
    // PageTable fetchData callback
    async fetchProjects(params) {
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
      return await getProjects(query)
    },

    handleSelectionChange(selection) {
      this.selectedRows = selection
    },

    viewProjectDetails(projectId) {
      this.$router.push({ name: 'ProjectDetails', params: { projectId: projectId }})
    },

    // open the create dialog
    openCreateDialog() {
      this.formMode = 'create'
      this.editingProjectId = null
      this.formData = { project_name: '', description: '' }
      this.showFormDialog = true
    },

    // open the update dialog with row data pre-filled
    openUpdateDialog(row) {
      this.formMode = 'update'
      this.editingProjectId = row.id
      this.formData = {
        project_name: row.name || '',
        description: row.description || ''
      }
      this.showFormDialog = true
    },

    resetFormDialog() {
      this.formData = { project_name: '', description: '' }
      this.editingProjectId = null
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
          project_name: this.formData.project_name
        }
        if (this.formData.description) {
          payload.description = this.formData.description
        }

        let response
        if (this.formMode === 'create') {
          response = await createProject(payload)
        } else {
          // update requires project_id
          payload.project_id = this.editingProjectId
          response = await updateProject(payload)
        }

        if (!response.error) {
          this.$message.success(this.formMode === 'create' ? '项目创建成功' : '项目更新成功')
          this.showFormDialog = false
          this.$refs.pageTableRef.refresh()
        } else {
          this.$message.error(`${this.formMode === 'create' ? '创建' : '更新'}项目失败：${response.message || '未知错误'}`)
        }
      } catch (error) {
        console.error(`${this.formMode === 'create' ? '创建' : '更新'}项目失败:`, error)
        this.$message.error(`${this.formMode === 'create' ? '创建' : '更新'}项目失败，请检查网络连接`)
      } finally {
        this.submitting = false
      }
    },

    // batch delete selected projects (backend supports single delete,
    // so we loop over selected rows and delete one by one)
    handleBatchDelete() {
      const ids = this.selectedRows.map(row => row.id)
      const names = this.selectedRows.map(row => row.name).join(', ')
      this.$confirm(`确定要删除选中的 ${this.selectedRows.length} 个项目（${names}）吗？`, '批量删除确认', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }).then(async() => {
        let failCount = 0
        for (const id of ids) {
          try {
            const response = await deleteProject(id)
            if (response.error) {
              failCount++
            }
          } catch (error) {
            console.error('删除项目失败:', error)
            failCount++
          }
        }
        this.$refs.pageTableRef.refresh()
        if (failCount === 0) {
          this.$message.success('批量删除成功')
        } else {
          this.$message.warning(`批量删除完成，其中 ${failCount} 个项目删除失败`)
        }
      }).catch(() => {
        this.$message.info('已取消批量删除')
      })
    }
  }
}
</script>

<style scoped>
.project-list-container {
  display: flex;
  flex-direction: column;
  background: var(--el-fill-color-light);
  padding: 20px;
  box-sizing: border-box;
}

.header { margin: 0; }
</style>
