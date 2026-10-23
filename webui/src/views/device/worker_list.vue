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
  <div class="worker-list-container">
    <div class="header">
      <h2>工作器列表</h2>
    </div>
    <PageTable
      ref="pageTableRef"
      :fetch-data="fetchWorkers"
      search-placeholder="全局搜索：工作器名称 / 工作池 / 设备 / 状态 …"
      row-key="worker_name"
    >
      <filterable-table-column
        prop="worker_name"
        label="工作器名称"
        fixed="left"
        class-name="center-column"
        sortable="custom"
      />
      <filterable-table-column
        prop="work_pool"
        label="工作池"
        class-name="center-column"
        sortable="custom"
      />
      <filterable-table-column
        prop="device_name"
        label="设备名称"
        class-name="center-column"
        sortable="custom"
      />
      <filterable-table-column
        prop="worker_status"
        label="工作器状态"
        class-name="center-column"
        sortable="custom"
      >
        <template #default="scope">
          <el-tag :type="scope.row.worker_status === 'online' ? 'success' : 'info'">
            {{ scope.row.worker_status === 'online' ? '在线' : '离线' }}
          </el-tag>
        </template>
      </filterable-table-column>
      <filterable-table-column
        prop="pid"
        label="进程ID"
        class-name="center-column"
        sortable="custom"
      />
      <el-table-column
        label="操作"
        class-name="center-column"
        fixed="right"
        width="120"
      >
        <template #default="scope">
          <el-tooltip content="查看" placement="top">
            <el-button
              link
              :icon="View"
              @click="viewWorkerDetails(scope.row.worker_name)"
            />
          </el-tooltip>
          <el-tooltip content="重启工作器" placement="top">
            <el-button
              link
              :icon="Refresh"
              @click="handleRestartWorker(scope.row.worker_name)"
            />
          </el-tooltip>
        </template>
      </el-table-column>
    </PageTable>
  </div>
</template>

<script>
import { markRaw } from 'vue'
import { ElMessageBox, ElMessage } from 'element-plus'
import { View, Refresh } from '@element-plus/icons-vue'
import PageTable from '@/components/PageTable'
import FilterableTableColumn from '@/components/PageTable/FilterableTableColumn.vue'
import { getWorkers, restartWorker } from '@/api/device'

export default {
  components: {
    PageTable,
    FilterableTableColumn
  },
  data() {
    return {
      View: markRaw(View),
      Refresh: markRaw(Refresh),
      restarting: false
    }
  },
  methods: {
    // PageTable fetchData callback
    async fetchWorkers(params) {
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
      return await getWorkers(query)
    },

    viewWorkerDetails(workerName) {
      this.$router.push({ name: 'WorkerDetails', params: { workerName: workerName }})
    },

    handleRestartWorker(workerName) {
      ElMessageBox.confirm(
        `确定要重启工作器 "${workerName}" 吗？重启期间该工作器上的作业将受到影响。`,
        '重启工作器',
        {
          confirmButtonText: '确定重启',
          cancelButtonText: '取消',
          type: 'warning'
        }
      )
        .then(() => {
          this.restartWorker(workerName)
        })
        .catch(() => {})
    },

    async restartWorker(workerName) {
      this.restarting = true
      try {
        const response = await restartWorker(workerName)
        if (!response.error) {
          ElMessage.success(`工作器 "${workerName}" 重启指令已发送`)
          // refresh list after a short delay to pick up status change
          setTimeout(() => {
            this.$refs.pageTableRef.refresh()
          }, 2000)
        } else {
          ElMessage.error(`重启工作器失败：${response.message || '未知错误'}`)
        }
      } catch (error) {
        console.error('重启工作器失败:', error)
        ElMessage.error('重启工作器失败，请检查网络连接')
      } finally {
        this.restarting = false
      }
    }
  }
}
</script>

<style scoped>
.worker-list-container {
  display: flex;
  flex-direction: column;
  background: var(--el-fill-color-light);
  padding: 20px;
  box-sizing: border-box;
}

.header { margin: 0; }
</style>
