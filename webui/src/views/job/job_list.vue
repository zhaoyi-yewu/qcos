<template>
  <div class="device-list-container">
    <div class="header">
      <h2>作业查询</h2>
    </div>
    <div class="table-container">
      <el-table
        ref="tableRef"
        :data="pageData"
        style="width: 100%"
        border
        :header-cell-style="{ background: '#f5f7fa' }"
        @selection-change="handleSelectionChange"
      >
        <el-table-column
          type="selection"
          class-name="center-column"
          fixed="left"
          :selectable="checkSelectable"
        />
        <el-table-column
          prop="job_id"
          label="作业ID"
          fixed="left"
          class-name="center-column"
          sortable
        />
        <el-table-column
          label="作业名称"
          class-name="center-column"
          sortable
        >
          <template #default="scope">
            {{ scope.row.job_name || '-' }}
          </template>
        </el-table-column>
        <el-table-column
          label="提交时间"
          class-name="center-column"
          sortable
        >
          <template #default="scope">
            {{ scope.row.creation_date ? convertDate(scope.row.creation_date) : '未开始' }}
          </template>
        </el-table-column>
        <el-table-column
          label="完成时间"
          class-name="center-column"
          sortable
        >
          <template #default="scope">
            {{ scope.row.end_date ? convertDate(scope.row.end_date) : '-' }}
          </template>
        </el-table-column>
        <el-table-column
          prop="backend"
          label="后端设备"
          class-name="center-column"
          sortable
        >
          <template #default="scope">
            <el-button
              type="text"
              @click="viewJobBackend(scope.row.backend)"
            >
              {{ scope.row.backend }}
            </el-button>
          </template>
        </el-table-column>
        <el-table-column
          prop="shots"
          label="测量次数(shots)"
          class-name="center-column"
          sortable
        />
        <el-table-column
          prop="job_status"
          label="作业状态"
          class-name="center-column"
          sortable
        >
          <template #default="scope">
            <el-tag
              :type="getJobStatusTag(scope.row.job_status)"
              size="small"
            >
              {{ getJobStatus(scope.row.job_status) }}
            </el-tag>
            <div v-if="scope.row.progress<100 && scope.row.progress>=0" class="job-progress">
              <el-progress :percentage="scope.row.progress" :color="customColorMethod" />
            </div>
          </template>
        </el-table-column>
        <el-table-column
          prop="job_priority"
          label="优先级"
          class-name="center-column"
          sortable
        />
        <el-table-column
          prop="details"
          label="详情"
          class-name="center-column"
        >
          <template #default="scope">
            <el-button
              type="text"
              @click="viewJobDetail(scope.row.job_id)"
            >
              查看
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <div class="pagination-container">
      <el-pagination
        background
        layout="total, prev, pager, next"
        :total="taskList.length"
        :page-size="pageSize"
        :current-page="currentPage"
        @current-change="handlePageChange"
      />
    </div>

    <!-- 批量操作区 -->
    <div class="batch-operations">
      <el-button
        type="warning"
        size="default"
        :icon="Delete"
        :disabled="selectedRows.length === 0"
        @click="handleBatchCancel"
      >
        批量取消 ({{ selectedRows.length }})
      </el-button>
      <el-button
        type="danger"
        size="default"
        :icon="Delete"
        :disabled="selectedRows.length === 0"
        @click="handleBatchDelete"
      >
        批量删除 ({{ selectedRows.length }})
      </el-button>
      <el-button
        type="primary"
        size="default"
        :disabled="taskList.length === 0"
        @click="handleSelectAll"
      >
        {{ isAllSelected ? '取消全选' : '全选' }}
      </el-button>
    </div>
  </div>
</template>

<script>
import { Delete } from '@element-plus/icons-vue'
import { cancelTask, deleteTask, queryJobs } from '@/api/job'
import { convertDate, customColorMethod, getJobStatus, getJobStatusTag } from '@/common/library'

export default {
  components: { Delete },
  data() {
    return {
      taskList: [],
      currentPage: 1,
      pageSize: 10,
      timer: null,
      pollingInterval: 10000,
      selectedRows: []
    }
  },

  selectedIds: [],

  computed: {
    pageData() {
      const start = (this.currentPage - 1) * this.pageSize
      const end = this.currentPage * this.pageSize
      return this.taskList.slice(start, end)
    },

    // 判断是否全选
    isAllSelected() {
      // 过滤掉不可选的行
      const selectableCount = this.taskList.filter(item => this.checkSelectable(item)).length
      return this.selectedRows.length > 0 && this.selectedRows.length === selectableCount
    }
  },

  mounted() {
    this.startPolling()
  },

  beforeUnmount() {
    this.stopPolling()
  },

  methods: {
    convertDate,
    customColorMethod,
    getJobStatus,
    getJobStatusTag,

    handlePageChange(page) {
      this.currentPage = page
    },

    checkSelectable(row) {
      return row.status !== 'locked'
    },

    handleSelectionChange(selection) {
      this.selectedRows = selection
    },

    // 全选/取消全选
    handleSelectAll() {
      if (this.isAllSelected) {
        // 取消全选
        this.$refs.tableRef.clearSelection()
      } else {
        // 全选（只选中可选择的行）
        this.taskList.forEach(row => {
          if (this.checkSelectable(row)) {
            this.$refs.tableRef.toggleRowSelection(row, true)
          }
        })
      }
    },

    // 单行删除
    handleDelete(job_id) {
      this.$confirm(`确定要删除 job_id 为 ${job_id} 的数据吗？`, '删除确认', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }).then(() => {
        this.taskList = this.taskList.filter(item => item.job_id !== job_id)
        this.$message.success('删除成功')
      }).catch(() => {
        this.$message.info('已取消删除')
      })
    },

    // 批量取消
    handleBatchCancel() {
      const ids = this.selectedRows.map(row => row.job_id).join(', ')
      this.$confirm(`确定要取消选中的 ${this.selectedRows.length} 条数据（job_id: ${ids}）吗？`, '批量取消确认', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }).then(() => {
        const cancelIds = this.selectedRows.map(row => row.job_id)
        // cancel job_id
        if (cancelIds) {
          cancelTask(cancelIds)
        }
        this.$refs.tableRef.clearSelection() // 清空选中状态
        this.$message.success('批量取消成功')
      }).catch(() => {
        this.$message.info('已取消批量取消')
      })
    },

    // 批量删除
    handleBatchDelete() {
      const ids = this.selectedRows.map(row => row.job_id).join(', ')
      this.$confirm(`确定要删除选中的 ${this.selectedRows.length} 条数据（job_id: ${ids}）吗？`, '批量删除确认', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }).then(() => {
        const deleteIds = this.selectedRows.map(row => row.job_id)
        // delete job_id
        if (deleteIds) {
          deleteTask(deleteIds)
        }
        this.taskList = this.taskList.filter(item => !deleteIds.includes(item.job_id))
        this.$refs.tableRef.clearSelection() // 清空选中状态
        this.$message.success('批量删除成功')
      }).catch(() => {
        this.$message.info('已取消批量删除')
      })
    },

    async fetchTasks() {
      try {
        const response = await queryJobs('task_list', null)
        if (!response.error) {
          this.taskList = response.result
          this.taskList.sort((a, b) => {
            return new Date(b.creation_date) - new Date(a.creation_date)
          })
        } else {
          this.$message.error(`获取任务列表失败：${response.message || '未知错误'}`)
        }
      } catch (error) {
        console.error('获取任务列表失败:', error)
        this.$message.error('获取任务列表失败，请检查网络连接')
      }
    },

    startPolling() {
      this.fetchTasks()
      this.timer = setInterval(() => {
        this.fetchTasks()
      }, this.pollingInterval)
    },

    stopPolling() {
      if (this.timer) {
        clearInterval(this.timer)
        this.timer = null
      }
    },

    viewJobBackend(deviceName) {
      this.$router.push({ name: 'DeviceDetails', params: { deviceName: deviceName }})
    },

    viewJobDetail(taskId) {
      this.$router.push({ name: 'JobDetail', params: { taskId: taskId }})
    }
  }
}
</script>

<style scoped>
.device-list-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #f5f7fa;
  padding: 20px;
  box-sizing: border-box;
}

.header {
  margin-bottom: 0px;
}

.table-container {
  flex: 1;
  background: white;
  border-radius: 8px;
  padding: 15px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.05);
  overflow: auto;
}

.pagination-container {
  text-align: center;
  margin-top: 10px;
  padding: 0 20px 20px;
}

.batch-operations {
  text-align: right;
  margin-top: 10px;
  padding: 0 20px 50px;
}

.job-progress .el-progress--line {
  margin-bottom: 15px;
  max-width: 600px;
}

::v-deep .el-table {
  font-size: 15px;
  --el-table-row-height: 30px;
}

::v-deep .el-table th {
  padding: 12px 0;
  font-size: 16px;
  text-align: center;
}

::v-deep .el-pagination {
  margin-top: 20px;
}

::v-deep .center-column {
  text-align: center;
}

::v-deep .el-tag--red {
  color: red;
  background: lightyellow;
  font-weight: bold;
}

::v-deep .el-tag--yellow {
  color: yellow;
  font-weight: bold;
}

::v-deep .el-tag--orange {
  color: orange;
  font-weight: bold;
}

::v-deep .el-tag--indigo {
  color: indigo;
  font-weight: bold;
}

::v-deep .el-tag--green {
  color: green;
  font-weight: bold;
}

::v-deep .el-tag--blue {
  color: blue;
  font-weight: bold;
}

::v-deep .el-tag--grey {
  color: grey;
  font-weight: bold;
}
</style>
