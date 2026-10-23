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
  <div v-if="loaded" class="project-detail-container">
    <div class="header">
      <h2>项目详情</h2>
    </div>
    <div class="detail-container">
      <el-card class="detail-card">
        <div class="detail-header">
          <h2>{{ projectDetails.name || '未命名' }}</h2>
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
import { getProject } from '@/api/account'

export default {
  name: 'ProjectDetails',
  data() {
    return {
      loaded: false,
      projectId: this.$route.params.projectId,
      projectDetails: {
        id: '',
        name: '',
        description: '',
        created_at: '',
        updated_at: ''
      },
      leftItems: [],
      rightItems: []
    }
  },
  watch: {
    '$route.params.projectId'(newVal) {
      if (newVal !== this.projectId) {
        this.projectId = newVal
        this.queryData()
      }
    }
  },
  created() {
    this.queryData()
  },
  methods: {
    async queryData() {
      await this.fetchProjectDetails()
      this.formatItems()
      this.loaded = true
    },

    async fetchProjectDetails() {
      try {
        const response = await getProject(this.projectId)
        if (!response.error) {
          this.projectDetails = response.result
        } else {
          this.$message.error(`获取项目详情失败：${response.message || '未知错误'}`)
        }
      } catch (error) {
        console.error('获取项目详情失败:', error)
        this.$message.error('获取项目详情失败，请检查网络连接')
      }
    },

    formatItems() {
      const d = this.projectDetails
      this.leftItems = [
        { label: '项目ID', value: d.id || '-', color: '#409EFF' },
        { label: '项目名称', value: d.name || '-', color: '#409EFF' },
        { label: '项目描述', value: d.description || '未填写', color: '#409EFF' }
      ]
      this.rightItems = [
        { label: '创建时间', value: d.created_at || '-', color: '#67C23A' },
        { label: '更新时间', value: d.updated_at || '-', color: '#67C23A' }
      ]
    }
  }
}
</script>

<style scoped>
.project-detail-container {
  padding: 10px;
}

.header { margin: 0; }

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
