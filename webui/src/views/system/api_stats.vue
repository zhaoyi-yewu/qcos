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
  <div class="api-stats-container">
    <div class="header">
      <h2>API访问统计</h2>
      <div class="header-actions">
        <refresh-interval
          :default-interval="10"
          :refreshing="loading"
          @refresh="fetchApiStats"
          @interval-change="onIntervalChange"
        />
      </div>
    </div>

    <!-- overview cards -->
    <div class="overview-cards">
      <el-card class="overview-card" shadow="hover">
        <div class="overview-label">总请求数</div>
        <div class="overview-value">{{ apiStats.total_requests }}</div>
      </el-card>
      <el-card class="overview-card" shadow="hover">
        <div class="overview-label">最近1小时请求</div>
        <div class="overview-value">{{ apiStats.last_hour_requests }}</div>
      </el-card>
      <el-card class="overview-card" shadow="hover">
        <div class="overview-label">最近24小时请求</div>
        <div class="overview-value">{{ apiStats.last_day_requests }}</div>
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
import { getApiStats } from '@/api/system'
import RefreshInterval from '@/components/RefreshInterval/index.vue'

const METRIC_LABELS = {
  total_requests: 'API 总请求数（自服务启动以来）',
  last_hour_requests: '最近 1 小时内的 API 请求数',
  last_day_requests: '最近 24 小时内的 API 请求数'
}

export default {
  components: {
    RefreshInterval
  },
  data() {
    return {
      DataLine: markRaw(DataLine),
      loading: false,
      apiStats: {
        total_requests: 0,
        last_hour_requests: 0,
        last_day_requests: 0
      }
    }
  },

  computed: {
    statsTableData() {
      return Object.keys(this.apiStats).map(key => ({
        metric: key,
        label: METRIC_LABELS[key] || key,
        value: this.apiStats[key]
      }))
    }
  },

  mounted() {
    this.fetchApiStats()
  },

  methods: {
    async fetchApiStats() {
      this.loading = true
      try {
        const response = await getApiStats()
        if (!response.error) {
          this.apiStats = { ...response.result }
        } else {
          this.$message.error(`获取API统计失败：${response.message || '未知错误'}`)
        }
      } catch (error) {
        console.error('获取API统计失败:', error)
        this.$message.error('获取API统计失败，请检查网络连接')
      } finally {
        this.loading = false
      }
    },

    onIntervalChange() {
      this.fetchApiStats()
    }
  }
}
</script>

<style scoped>
.api-stats-container {
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
  flex: 1 1 200px;
  min-width: 200px;
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
  color: #409eff;
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
