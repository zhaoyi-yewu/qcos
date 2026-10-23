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
  <div v-if="loaded" class="worker-detail-container">
    <div class="header">
      <h2>工作器详情</h2>
      <el-button
        type="warning"
        :icon="Refresh"
        :loading="restarting"
        @click="handleRestartWorker(workerDetails.worker_name)"
      >
        重启工作器
      </el-button>
    </div>
    <div class="detail-container">
      <el-card class="detail-card">
        <div class="detail-header">
          <h2>{{ workerDetails.worker_name || '未命名' }}</h2>
          <el-tag
            :type="getWorkerStatusTagType(workerDetails.worker_status)"
            class="status-tag"
          >
            {{ getWorkerStatusDisplay(workerDetails.worker_status) }}
          </el-tag>
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
  </div>
</template>

<script>
import { markRaw } from 'vue'
import { ElMessageBox, ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import { getWorkers, restartWorker } from '@/api/device'

export default {
  name: 'WorkerDetails',
  data() {
    return {
      loaded: false,
      // expose the Refresh icon to the template via data (markRaw); it is
      // only used as an :icon value, not as a component tag
      Refresh: markRaw(Refresh),
      workerName: this.$route.params.workerName,
      workerDetails: {
        worker_name: '',
        work_pool: '',
        device_name: '',
        worker_status: '',
        pid: ''
      },
      leftItems: [],
      rightItems: []
    }
  },
  watch: {
    '$route.params.workerName'(newVal) {
      if (newVal !== this.workerName) {
        this.workerName = newVal
        this.queryData()
      }
    }
  },
  created() {
    this.queryData()
  },
  methods: {
    getWorkerStatusDisplay(status) {
      if (status === 'online') return '在线'
      return '离线'
    },
    getWorkerStatusTagType(status) {
      if (status === 'online') return 'success'
      return 'info'
    },

    async queryData() {
      await this.fetchWorkerDetails()
      this.formatWorkerItems()
      this.loaded = true
    },

    async fetchWorkerDetails() {
      try {
        const response = await getWorkers()
        if (!response.error) {
          const workers = response.result.workers
          if (Array.isArray(workers)) {
            const found = workers.find(
              w => w.worker_name === this.workerName
            )
            this.workerDetails = found || {
              worker_name: this.workerName,
              work_pool: '',
              device_name: '',
              worker_status: '',
              pid: ''
            }
          }
        } else {
          this.$message.error(`获取工作器详情失败：${response.message || '未知错误'}`)
        }
      } catch (error) {
        console.error('获取工作器详情失败:', error)
        this.$message.error('获取工作器详情失败，请检查网络连接')
      }
    },

    formatWorkerItems() {
      const w = this.workerDetails
      this.leftItems = [
        { label: '工作器名称', value: w.worker_name || '-', color: '#409EFF' },
        { label: '工作池', value: w.work_pool || '-', color: '#409EFF' },
        { label: '设备名称', value: w.device_name || '-', color: '#409EFF' }
      ]
      this.rightItems = [
        { label: '工作器状态', value: this.getWorkerStatusDisplay(w.worker_status), color: '#67C23A' },
        { label: '进程ID', value: w.pid ?? '-', color: '#67C23A' }
      ]
    },

    handleRestartWorker(workerName) {
      if (!workerName) {
        ElMessage.warning('工作器名称无效，无法重启')
        return
      }
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
          this.doRestartWorker(workerName)
        })
        .catch(() => {})
    },

    async doRestartWorker(workerName) {
      this.restarting = true
      try {
        const response = await restartWorker(workerName)
        if (!response.error) {
          ElMessage.success(`工作器 "${workerName}" 重启指令已发送`)
          // refresh details after a short delay to pick up status change
          setTimeout(() => {
            this.fetchWorkerDetails()
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
.worker-detail-container {
  padding: 10px;
}

.header {
  margin: 0;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

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

.status-tag {
  font-size: 14px;
  font-weight: bold;
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
