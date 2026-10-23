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
  <div class="device-list-container">
    <div class="header">
      <h2>作业列表</h2>
    </div>

    <PageTable
      ref="pageTableRef"
      :fetch-data="fetchTasks"
      search-placeholder="全局搜索：作业ID / 名称 / 设备 / 状态 …"
      row-key="job_id"
      @selection-change="handleSelectionChange"
    >
      <template #toolbar-actions>
        <el-button
          type="primary"
          size="small"
          :icon="Upload"
          @click="showSubmitDialog = true"
        >
          作业提交
        </el-button>
        <el-button
          type="warning"
          size="small"
          :icon="Delete"
          :disabled="selectedRows.length === 0"
          @click="handleBatchCancel"
        >
          批量取消 ({{ selectedRows.length }})
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
        <refresh-interval
          :default-interval="5"
          :refreshing="refreshing"
          @refresh="refreshData"
          @interval-change="onIntervalChange"
        />
      </template>
      <el-table-column
        type="selection"
        class-name="center-column"
        fixed="left"
        :selectable="checkSelectable"
      />
      <filterable-table-column
        prop="job_id"
        label="作业ID"
        fixed="left"
        class-name="center-column"
        sortable="custom"
      />
      <filterable-table-column
        prop="job_name"
        label="作业名称"
        class-name="center-column"
        sortable="custom"
      >
        <template #default="scope">
          {{ scope.row.job_name || '-' }}
        </template>
      </filterable-table-column>
      <filterable-table-column
        prop="created_at"
        label="提交时间"
        class-name="center-column"
        sortable="custom"
      >
        <template #default="scope">
          {{ scope.row.created_at ? convertDate(scope.row.created_at) : '未开始' }}
        </template>
      </filterable-table-column>
      <filterable-table-column
        prop="ended_at"
        label="完成时间"
        class-name="center-column"
        sortable="custom"
      >
        <template #default="scope">
          {{ scope.row.ended_at ? convertDate(scope.row.ended_at) : '-' }}
        </template>
      </filterable-table-column>
      <filterable-table-column
        prop="backend"
        label="后端设备"
        class-name="center-column"
        sortable="custom"
      >
        <template #default="scope">
          <el-button
            link
            @click="viewJobBackend(scope.row.backend)"
          >
            {{ scope.row.backend }}
          </el-button>
        </template>
      </filterable-table-column>
      <filterable-table-column
        prop="shots"
        label="测量次数(shots)"
        class-name="center-column"
        sortable="custom"
      />
      <filterable-table-column
        prop="job_status"
        label="作业状态"
        class-name="center-column"
        sortable="custom"
      >
        <template #default="scope">
          <div class="job-status-cell">
            <el-tag
              :type="getJobStatusTag(scope.row.job_status)"
              size="small"
              class="job-status-tag"
            >
              {{ getJobStatus(scope.row.job_status) }}
            </el-tag>
            <el-progress
              v-if="shouldShowProgress(scope.row)"
              class="job-progress"
              :percentage="getProgressValue(scope.row)"
              :color="customColorMethod"
              :stroke-width="12"
              :text-inside="true"
              :status="getProgressStatus(scope.row)"
            />
          </div>
        </template>
      </filterable-table-column>
      <filterable-table-column
        prop="job_priority"
        label="优先级"
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
              @click="viewJobDetail(scope.row.job_id)"
            />
          </el-tooltip>
        </template>
      </el-table-column>
    </PageTable>

    <!-- job submit dialog: embeds the unified job submit page -->
    <el-dialog
      v-model="showSubmitDialog"
      title="作业提交"
      width="90%"
      align-center
      class="job-submit-dialog"
      :close-on-click-modal="false"
      destroy-on-close
    >
      <job-submit v-if="showSubmitDialog" embedded />
    </el-dialog>
  </div>
</template>

<script>
import { markRaw } from 'vue'
import { Delete, Upload, View } from '@element-plus/icons-vue'
import PageTable from '@/components/PageTable'
import FilterableTableColumn from '@/components/PageTable/FilterableTableColumn.vue'
import RefreshInterval from '@/components/RefreshInterval/index.vue'
import { cancelTask, deleteTask, queryJobs } from '@/api/job'
import { convertDate, customColorMethod, getJobStatus, getJobStatusTag } from '@/common/library'
import JobSubmit from './job_submit.vue'

export default {
  components: {
    PageTable,
    FilterableTableColumn,
    JobSubmit,
    RefreshInterval
  },
  data() {
    return {
      Delete: markRaw(Delete),
      Upload: markRaw(Upload),
      View: markRaw(View),
      // control visibility of the job submit dialog
      showSubmitDialog: false,
      selectedRows: [],
      // job ID to highlight after navigating from submit page (fades out after 5s)
      highlightJobId: null,
      highlightTimer: null,
      // client-side display progress per job_id; eases towards the server
      // progress so the el-progress bar grows smoothly between server polls
      displayProgressMap: {},
      // animation timer driving the local display progress forwards
      progressAnimTimer: null,
      // reference to the latest table rows so the animation timer can read
      // server progress without poking into PageTable internals on every tick
      latestTableRows: [],
      // whether a table refresh is in progress (drives RefreshInterval spinner)
      refreshing: false
    }
  },
  mounted() {
    if (this.$route.query.highlight) {
      this.highlightJobId = this.$route.query.highlight
      this.highlightTimer = setTimeout(() => {
        this.highlightJobId = null
        this.highlightTimer = null
      }, 5000)
    }
    // start the local animation loop that makes progress bars visually
    // grow between server refreshes
    this.startProgressAnimation()
  },
  beforeUnmount() {
    if (this.highlightTimer) {
      clearTimeout(this.highlightTimer)
      this.highlightTimer = null
    }
    this.stopProgressAnimation()
  },
  methods: {
    convertDate,
    customColorMethod,
    getJobStatus,
    getJobStatusTag,

    // decide whether to show progress bar for a job row; the backend
    // returns job_status in UPPER_CASE (QUEUED/RUNNING/CANCELLING/...),
    // so we normalise before comparing
    shouldShowProgress(row) {
      const status = String(row.job_status || '').toUpperCase()
      const progress = row.progress
      // show progress for queued, running, cancelling jobs
      if (['QUEUED', 'RUNNING', 'CANCELLING'].includes(status)) {
        return true
      }
      // also show for any job with valid progress (0-99)
      if (progress !== undefined && progress !== null && progress >= 0 && progress < 100) {
        return true
      }
      return false
    },

    // get progress percentage value for el-progress; prefer the locally
    // animated display value (which eases towards the server value) so the
    // bar grows smoothly instead of jumping on each server refresh
    getProgressValue(row) {
      const serverValue = this.resolveServerProgress(row)
      const jobId = row.job_id
      const displayed = this.displayProgressMap[jobId]
      if (displayed === undefined || displayed === null) {
        return serverValue
      }
      // never display more than the server-reported progress would allow;
      // the animation timer is responsible for pushing the displayed value
      // forward, here we just clamp to valid range
      return Math.min(100, Math.max(0, Math.floor(displayed)))
    },

    // resolve the raw server-reported progress (clamped 0-100); returns 0
    // for queued/running jobs that have no progress value yet
    resolveServerProgress(row) {
      const progress = row.progress
      if (progress === undefined || progress === null || progress < 0) {
        return 0
      }
      return Math.min(100, Math.max(0, Math.floor(progress)))
    },

    // el-progress status for color indication; backend job_status is
    // UPPER_CASE so we normalise before comparing
    getProgressStatus(row) {
      const status = String(row.job_status || '').toUpperCase()
      if (status === 'FAILED' || status === 'CANCELLED' || status === 'DELETED') {
        return 'exception'
      }
      if (row.progress >= 100 || status === 'COMPLETED') {
        return 'success'
      }
      return undefined
    },

    // start a light-weight timer that nudges displayProgressMap values
    // towards the server progress so the bar visibly grows between polls
    startProgressAnimation() {
      // ~5 ticks per second feels smooth without burning CPU
      this.progressAnimTimer = setInterval(() => {
        this.tickDisplayProgress()
      }, 200)
    },

    stopProgressAnimation() {
      if (this.progressAnimTimer) {
        clearInterval(this.progressAnimTimer)
        this.progressAnimTimer = null
      }
    },

    // single animation step: for every job that should show a progress
    // bar, advance the displayed value towards the server value by a small
    // step; snap immediately when the job reaches a terminal state
    tickDisplayProgress() {
      const rows = this.latestTableRows || []
      if (!rows.length) return
      const next = { ...this.displayProgressMap }
      const activeJobIds = new Set()
      for (const row of rows) {
        const jobId = row.job_id
        if (jobId === undefined || jobId === null) continue
        if (!this.shouldShowProgress(row)) {
          // terminal state -- clear local animation state so the row shows
          // the final server value directly
          delete next[jobId]
          continue
        }
        activeJobIds.add(jobId)
        const serverValue = this.resolveServerProgress(row)
        const current = next[jobId]
        if (current === undefined || current === null) {
          // first time we see this job: start from the server value
          next[jobId] = serverValue
          continue
        }
        if (serverValue > current) {
          // server jumped ahead -- catch up immediately to avoid
          // displaying stale low progress
          next[jobId] = serverValue
        } else if (current < 99) {
          // server has not reported new progress yet; gently ease the
          // displayed value forward so the user sees the bar moving,
          // but cap prediction at serverValue + 5 to avoid running away
          const predictedCap = Math.min(99, serverValue + 5)
          if (current < predictedCap) {
            next[jobId] = current + 1
          }
        }
      }
      // drop entries for jobs that are no longer in the current page
      for (const key of Object.keys(next)) {
        if (!activeJobIds.has(key) && !activeJobIds.has(Number(key))) {
          delete next[key]
        }
      }
      this.displayProgressMap = next
    },

    // row class name -- highlight the job row navigated from submit page
    tableRowClassName({ row }) {
      if (this.highlightJobId && String(row.job_id) === String(this.highlightJobId)) {
        return 'highlight-row'
      }
      return ''
    },

    checkSelectable(row) {
      return row.status !== 'locked'
    },

    handleSelectionChange(selection) {
      this.selectedRows = selection
    },

    refreshData() {
      this.refreshing = true
      this.$refs.pageTableRef.refresh()
      // pageTable refresh is synchronous; clear refreshing after a short delay
      setTimeout(() => {
        this.refreshing = false
      }, 500)
    },

    // user picked a new auto-refresh interval: refresh immediately so the
    // list reflects the latest data instead of waiting for the next tick
    onIntervalChange() {
      this.refreshData()
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
        this.$refs.pageTableRef.refresh()
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
        this.$refs.pageTableRef.refresh()
        this.$message.success('批量删除成功')
      }).catch(() => {
        this.$message.info('已取消批量删除')
      })
    },

    // PageTable fetchData callback
    async fetchTasks(params) {
      const query = {
        pagination: {
          page: params.page,
          page_size: params.page_size
        },
        // server-side sort: prefer user-clicked column, fall back to
        // the default "-created_at" so the list shows newest jobs first
        sort: params.sort && params.sort.length > 0
          ? params.sort
          : ['-created_at']
      }
      if (params.search) {
        query.search = params.search
      }
      if (params.filters) {
        query.filters = params.filters
      }
      const response = await queryJobs(query)
      // keep a snapshot of the latest rows for the local progress
      // animation loop; align displayProgressMap with the new server
      // values so freshly-reported progress takes effect immediately
      if (response && !response.error && response.result) {
        const result = response.result
        let rows = []
        if (Array.isArray(result.items)) {
          rows = result.items
        } else if (Array.isArray(result)) {
          rows = result
        } else {
          rows = Object.values(result)
        }
        this.latestTableRows = rows
        const next = { ...this.displayProgressMap }
        for (const row of rows) {
          const jobId = row && row.job_id
          if (jobId === undefined || jobId === null) continue
          const serverValue = this.resolveServerProgress(row)
          const displayed = next[jobId]
          if (displayed === undefined || serverValue > displayed) {
            next[jobId] = serverValue
          }
        }
        this.displayProgressMap = next
      }
      return response
    },

    viewJobBackend(deviceName) {
      this.$router.push({ name: 'DeviceDetails', params: { deviceName: deviceName }})
    },

    viewJobDetail(jobId) {
      this.$router.push({ name: 'JobDetail', params: { jobId: jobId }})
    }
  }
}
</script>

<style scoped>
.device-list-container {
  display: flex;
  flex-direction: column;
  background: var(--el-fill-color-light);
  padding: 20px;
  box-sizing: border-box;
}

.header { margin: 0; }

/* status column: tag on top, progress bar below; both are centered
   horizontally and the row is allowed to grow beyond the default 28px */
.job-status-cell {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  width: 100%;
  padding: 4px 0;
}
.job-status-tag {
  align-self: center;
}
.job-progress {
  width: 100%;
  max-width: 240px;
  min-width: 120px;
}
.job-progress :deep(.el-progress--line) {
  margin-bottom: 0;
  width: 100%;
}
.job-progress :deep(.el-progress__text) {
  font-size: 11px !important;
  min-width: 2em;
}

:deep(.el-table) {
  font-size: 13px;
  --el-table-row-height: 28px;
}

:deep(.el-table th) {
  padding: 8px 0;
  font-size: 13px;
  text-align: center;
}

:deep(.el-table th .cell) {
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: center;
  flex-wrap: nowrap;
  white-space: nowrap;
  gap: 2px;
}

:deep(.el-table th .caret-wrapper) {
  display: inline-flex;
  align-items: center;
  flex-shrink: 0;
}

:deep(.el-pagination) {
  margin-top: 20px;
}

:deep(.center-column) {
  text-align: center;
}

:deep(.el-tag--red) {
  color: red;
  background: lightyellow;
  font-weight: bold;
}

:deep(.el-tag--yellow) {
  color: yellow;
  font-weight: bold;
}

:deep(.el-tag--orange) {
  color: orange;
  font-weight: bold;
}

:deep(.el-tag--indigo) {
  color: indigo;
  font-weight: bold;
}

:deep(.el-tag--green) {
  color: green;
  font-weight: bold;
}

:deep(.el-tag--blue) {
  color: blue;
  font-weight: bold;
}

:deep(.el-tag--grey) {
  color: grey;
  font-weight: bold;
}

/* highlight-row: blue gradient background that fades out over 5s */
:deep(.el-table__row.highlight-row) > td.el-table__cell {
  animation: highlight-fade 5s ease-out forwards;
}

@keyframes highlight-fade {
  0% { background-color: rgba(64, 158, 255, 0.25); }
  100% { background-color: transparent; }
}

/* job submit dialog: vertically centered (align-center) with a
   scrollable body so the complex form never overflows the viewport */
:deep(.job-submit-dialog .el-dialog) {
  max-height: 88vh;
  display: flex;
  flex-direction: column;
}
:deep(.job-submit-dialog .el-dialog__body) {
  max-height: calc(88vh - 55px);
  overflow-y: auto;
  padding: 12px 16px;
  flex: 1 1 auto;
}
</style>
