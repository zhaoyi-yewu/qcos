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
  <div class="job-stats-container">
    <div class="header">
      <h2>作业统计</h2>
      <div class="header-actions">
        <refresh-interval
          :default-interval="10"
          :refreshing="loading"
          @refresh="fetchJobStats"
          @interval-change="onIntervalChange"
        />
      </div>
    </div>

    <!-- overview cards -->
    <div class="overview-cards">
      <el-card class="overview-card" shadow="hover">
        <div class="overview-label">作业总数</div>
        <div class="overview-value">{{ jobStats.total }}</div>
      </el-card>
      <el-card class="overview-card" shadow="hover">
        <div class="overview-label">已完成</div>
        <div class="overview-value success">{{ jobStats.completed }}</div>
      </el-card>
      <el-card class="overview-card" shadow="hover">
        <div class="overview-label">失败</div>
        <div class="overview-value danger">{{ jobStats.failed }}</div>
      </el-card>
      <el-card class="overview-card" shadow="hover">
        <div class="overview-label">运行中</div>
        <div class="overview-value primary">{{ jobStats.running }}</div>
      </el-card>
      <el-card class="overview-card" shadow="hover">
        <div class="overview-label">排队中</div>
        <div class="overview-value warning">{{ jobStats.queued }}</div>
      </el-card>
    </div>

    <!-- rate cards -->
    <div class="overview-cards">
      <el-card class="overview-card" shadow="hover">
        <div class="overview-label">提交速率（次/分钟）</div>
        <div class="overview-value">{{ jobStats.submitted_job_rate_min }}</div>
      </el-card>
      <el-card class="overview-card" shadow="hover">
        <div class="overview-label">完成速率（次/分钟）</div>
        <div class="overview-value">{{ jobStats.completed_job_rate_min }}</div>
      </el-card>
    </div>

    <!-- detail table -->
    <div class="table-container">
      <el-table
        v-loading="loading"
        :data="statsTableData"
        style="width: 100%"
        border
        :header-cell-style="{ background: 'var(--el-fill-color-light)' }"
      >
        <el-table-column
          type="index"
          label="#"
          width="60"
          fixed="left"
          class-name="center-column"
        />
        <el-table-column
          prop="metric"
          label="指标"
          fixed="left"
          class-name="center-column"
        >
          <template #default="scope">
            <el-icon class="metric-icon"><DataLine /></el-icon>
            <span class="metric-name">{{ scope.row.metric }}</span>
          </template>
        </el-table-column>
        <el-table-column
          prop="label"
          label="说明"
          class-name="center-column"
        />
        <el-table-column
          prop="value"
          label="数值"
          class-name="center-column"
          sortable
        >
          <template #default="scope">
            <span class="metric-value">{{ scope.row.value }}</span>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script>
import { markRaw } from 'vue'
import { DataLine } from '@element-plus/icons-vue'
import { getJobStats } from '@/api/system'
import RefreshInterval from '@/components/RefreshInterval/index.vue'

const METRIC_LABELS = {
  total: '作业总数',
  completed: '已完成的作业数',
  failed: '失败的作业数',
  running: '正在运行的作业数',
  queued: '排队中的作业数',
  cancelling: '正在取消的作业数',
  cancelled: '已取消的作业数',
  deleting: '正在删除的作业数',
  deleted: '已删除的作业数',
  unknown: '未知状态的作业数',
  submitted_job_rate_min: '每分钟提交作业速率',
  completed_job_rate_min: '每分钟完成作业速率'
}

export default {
  components: {
    RefreshInterval
  },
  data() {
    return {
      DataLine: markRaw(DataLine),
      loading: false,
      jobStats: {
        total: 0,
        completed: 0,
        failed: 0,
        running: 0,
        queued: 0,
        cancelling: 0,
        cancelled: 0,
        deleting: 0,
        deleted: 0,
        unknown: 0,
        submitted_job_rate_min: 0,
        completed_job_rate_min: 0
      }
    }
  },

  computed: {
    statsTableData() {
      return Object.keys(this.jobStats).map(key => ({
        metric: key,
        label: METRIC_LABELS[key] || key,
        value: this.jobStats[key]
      }))
    }
  },

  mounted() {
    this.fetchJobStats()
  },

  methods: {
    async fetchJobStats() {
      this.loading = true
      try {
        const response = await getJobStats()
        if (!response.error) {
          this.jobStats = { ...response.result }
        } else {
          this.$message.error(`获取作业统计失败：${response.message || '未知错误'}`)
        }
      } catch (error) {
        console.error('获取作业统计失败:', error)
        this.$message.error('获取作业统计失败，请检查网络连接')
      } finally {
        this.loading = false
      }
    },

    onIntervalChange() {
      this.fetchJobStats()
    }
  }
}
</script>

<style scoped>
.job-stats-container {
  display: flex;
  flex-direction: column;
  background: var(--el-fill-color-light);
  padding: 20px;
  box-sizing: border-box;
}

.header {
  margin: 0;
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  margin-bottom: 10px;
}

.header-actions {
  padding-bottom: 5px;
}

.overview-cards {
  display: flex;
  gap: 16px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.overview-card {
  flex: 1 1 180px;
  min-width: 180px;
  text-align: center;
}

.overview-label {
  font-size: 14px;
  color: var(--el-text-color-secondary);
  margin-bottom: 8px;
}

.overview-value {
  font-size: 28px;
  font-weight: 700;
  color: var(--el-text-color-primary);
}

.overview-value.success {
  color: #67c23a;
}

.overview-value.danger {
  color: #f56c6c;
}

.overview-value.primary {
  color: #409eff;
}

.overview-value.warning {
  color: #e6a23c;
}

.table-container {
  flex: 1;
  background: var(--el-bg-color);
  border-radius: 8px;
  padding: 15px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.05);
  overflow: auto;
}

.metric-icon {
  font-size: 16px;
  color: #409eff;
  vertical-align: middle;
  margin-right: 6px;
}

.metric-name {
  vertical-align: middle;
  font-weight: 500;
}

.metric-value {
  font-size: 16px;
  font-weight: 700;
  color: var(--el-text-color-primary);
}

:deep(.el-table) {
  font-size: 15px;
  --el-table-row-height: 30px;
}

:deep(.el-table th) {
  padding: 12px 0;
  font-size: 16px;
  text-align: center;
}

:deep(.center-column) {
  text-align: center;
}
</style>
