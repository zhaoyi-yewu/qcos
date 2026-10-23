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
  <div class="component-status-container">
    <div class="header">
      <h2>组件状态</h2>
      <div class="header-actions">
        <refresh-interval
          :default-interval="10"
          :refreshing="loading"
          @refresh="fetchHealth"
          @interval-change="onIntervalChange"
        />
      </div>
    </div>

    <!-- system overview cards -->
    <div class="overview-cards">
      <el-card class="overview-card" shadow="hover">
        <div class="overview-label">系统整体状态</div>
        <div class="overview-value">
          <el-tag
            :type="systemHealthy ? 'success' : 'danger'"
            size="large"
          >
            {{ systemHealthy ? '正常' : '异常' }}
          </el-tag>
        </div>
      </el-card>
      <el-card class="overview-card" shadow="hover">
        <div class="overview-label">最近心跳时间</div>
        <div class="overview-value">
          {{ heartbeatDisplay }}
        </div>
      </el-card>
      <el-card class="overview-card" shadow="hover">
        <div class="overview-label">组件总数</div>
        <div class="overview-value">{{ componentList.length }}</div>
      </el-card>
      <el-card class="overview-card" shadow="hover">
        <div class="overview-label">在线组件</div>
        <div class="overview-value online-count">{{ onlineCount }}</div>
      </el-card>
    </div>

    <!-- component status table -->
    <div class="table-container">
      <el-table
        ref="tableRef"
        v-loading="loading"
        :data="componentList"
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
          prop="name"
          label="组件名称"
          fixed="left"
          class-name="center-column"
          sortable
        >
          <template #default="scope">
            <el-icon class="component-icon"><Cpu /></el-icon>
            <span class="component-name">{{ scope.row.name }}</span>
          </template>
        </el-table-column>
        <el-table-column
          prop="status"
          label="状态"
          class-name="center-column"
          sortable
        >
          <template #default="scope">
            <el-tag
              :type="scope.row.status === 'online' ? 'success' : 'danger'"
              size="default"
            >
              <el-icon class="status-icon">
                <CircleCheck v-if="scope.row.status === 'online'" />
                <CircleClose v-else />
              </el-icon>
              {{ scope.row.status === 'online' ? '在线' : '离线' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column
          prop="description"
          label="说明"
          class-name="center-column"
        >
          <template #default="scope">
            {{ getComponentDescription(scope.row.name) }}
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script>
import { markRaw } from 'vue'
import { Cpu, CircleCheck, CircleClose } from '@element-plus/icons-vue'
import { getSystemHealth } from '@/api/system'
import RefreshInterval from '@/components/RefreshInterval/index.vue'

// human-readable descriptions for known components
const COMPONENT_DESCRIPTIONS = {
  fastapi: 'FastAPI Web 服务，提供 RESTful 和 JSON-RPC 接口',
  redis: 'Redis 缓存服务，用于任务队列和状态共享',
  prefect: 'Prefect 调度引擎，负责作业流程编排和调度',
  worker: 'Prefect Worker，执行量子作业的后台工作器'
}

export default {
  components: {
    RefreshInterval,
    CircleCheck,
    CircleClose,
    Cpu
  },
  data() {
    return {
      Cpu: markRaw(Cpu),
      CircleCheck: markRaw(CircleCheck),
      CircleClose: markRaw(CircleClose),
      loading: false,
      systemHealthy: false,
      heartbeatTimestamp: null,
      componentList: []
    }
  },

  computed: {
    heartbeatDisplay() {
      if (!this.heartbeatTimestamp) {
        return '-'
      }
      // heartbeat_timestamp is a Unix epoch in seconds
      const date = new Date(this.heartbeatTimestamp * 1000)
      const year = date.getFullYear()
      const month = String(date.getMonth() + 1).padStart(2, '0')
      const day = String(date.getDate()).padStart(2, '0')
      const hours = String(date.getHours()).padStart(2, '0')
      const minutes = String(date.getMinutes()).padStart(2, '0')
      const seconds = String(date.getSeconds()).padStart(2, '0')
      return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`
    },

    onlineCount() {
      return this.componentList.filter(item => item.status === 'online').length
    }
  },

  mounted() {
    this.fetchHealth()
  },

  methods: {
    async fetchHealth() {
      this.loading = true
      try {
        const response = await getSystemHealth()
        if (!response.error) {
          const result = response.result
          this.systemHealthy = !!result.system_healthy
          this.heartbeatTimestamp = result.heartbeat_timestamp || null
          // convert component_status object to array for table rendering
          const statusObj = result.component_status || {}
          this.componentList = Object.keys(statusObj).map(name => ({
            name: name,
            status: statusObj[name]
          }))
        } else {
          this.$message.error(`获取系统状态失败：${response.message || '未知错误'}`)
        }
      } catch (error) {
        console.error('获取系统状态失败:', error)
        this.$message.error('获取系统状态失败，请检查网络连接')
      } finally {
        this.loading = false
      }
    },

    getComponentDescription(name) {
      return COMPONENT_DESCRIPTIONS[name] || `${name} 组件`
    },

    onIntervalChange() {
      this.fetchHealth()
    }
  }
}
</script>

<style scoped>
.component-status-container {
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

/* overview cards row */
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
  font-size: 22px;
  font-weight: 700;
  color: var(--el-text-color-primary);
}

.overview-value.online-count {
  color: #67c23a;
}

.table-container {
  flex: 1;
  background: var(--el-bg-color);
  border-radius: 8px;
  padding: 15px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.05);
  overflow: auto;
}

.component-icon {
  font-size: 16px;
  color: #409eff;
  vertical-align: middle;
  margin-right: 6px;
}

.component-name {
  vertical-align: middle;
  font-weight: 500;
}

.status-icon {
  margin-right: 4px;
  vertical-align: middle;
}

:deep(.center-column .el-tag) {
  display: inline-flex;
  align-items: center;
  justify-content: center;
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
