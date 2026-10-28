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
  <div class="job-detail-container">
    <div class="header">
      <h2>作业详情</h2>
    </div>
    <div class="detail-container">
      <el-card class="job-card">
        <div class="job-header">
          <h2>{{ taskDetail.job_name || '未命名' }}</h2>
          <el-tag
            :type="getJobStatusTag(taskDetail.job_status)"
            class="status-tag"
          >
            {{ getJobStatus(taskDetail.job_status) }}
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
              <el-timeline-item color="#409EFF" class="timeline-item">
                <div class="timeline-label">
                  作业内容 (代码类型: {{ taskDetail.code_type }})
                </div>
                <template
                  v-for="(item, index) in sourceCodeList"
                  :key="'source-' + index"
                >
                  <el-card class="source-code-card" shadow="hover">
                    <template #header>
                      <div class="card-collapse-header" @click="toggleSource(index)">
                        <span class="source-code-card-header">{{ item.name }}</span>
                        <el-icon class="collapse-icon">
                          <ArrowDown v-if="isSourceCollapsed(index)" />
                          <ArrowUp v-else />
                        </el-icon>
                      </div>
                    </template>
                    <div v-show="!isSourceCollapsed(index)" class="source-code-body">
                      <!-- v-text performs HTML escaping internally; pass the raw
                           code so it renders as plain text (no XSS surface). -->
                      <pre class="code-block"><code v-text="item.code" /></pre>
                    </div>
                  </el-card>
                  <br>
                </template>
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
              <el-timeline-item
                color="#67C23A"
              >
                <div class="timeline-label">作业结果</div>
                <template
                  v-for="(item, index) in getJobResultsContent(taskDetail.results, taskDetail.code_type)"
                  :key="'results-' + index"
                >
                  <el-card class="result-card" shadow="hover">
                    <template #header>
                      <div class="card-collapse-header" @click="toggleResult(index)">
                        <span class="source-code-card-header">结果[{{ index }}]</span>
                        <el-icon class="collapse-icon">
                          <ArrowDown v-if="isResultCollapsed(index)" />
                          <ArrowUp v-else />
                        </el-icon>
                      </div>
                    </template>
                    <div v-show="!isResultCollapsed(index)" class="result-body">
                      <template v-if="'error' in item">
                        错误码: {{ item['error']['code'] }}
                        <br>
                        错误信息: {{ item['error']['message'] }}
                      </template>
                      <template v-else>
                        量子比特数: {{ item['num_qubits'] || 'N/A' }} <br>
                        性能分析(profiling): <br>
                        <pre>{{ item['profiling'] }}</pre>
                        <br>
                        结果: <br>
                        <pre>{{ item['result'] }}</pre>
                      </template>
                    </div>
                  </el-card>
                  <br>
                </template>
              </el-timeline-item>
            </el-timeline>
          </div>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script>
import { queryJobDetails } from '@/api/job'
import {
  convertDate,
  getCircuitAggregation,
  getJobStatus,
  getJobStatusTag,
  getJobResultsContent,
  getQuboPrettyPrint
} from '@/common/library'
import { ArrowUp, ArrowDown } from '@element-plus/icons-vue'

export default {
  name: 'TaskDetail',
  components: {
    ArrowUp,
    ArrowDown
  },
  data() {
    return {
      jobId: this.$route.params.jobId,
      taskDetail: {
        job_id: '',
        job_status: '',
        source_code: '',
        code_type: '',
        backend: '',
        driver_options: '',
        transpiler: '',
        transpiler_options: '',
        circuit_aggregation: '',
        job_priority: '',
        description: '',
        shots: '',
        dry_run: '',
        results: '',
        profiling: '',
        num_qubits: '',
        progress: 0,
        creation_date: '',
        end_date: ''
      },
      leftItems: [],
      rightItems: [],
      // collapse state for source code / result cards (expanded by default)
      collapsedSource: {},
      collapsedResult: {}
    }
  },
  computed: {
    sourceCodeList() {
      const rawCode = this.taskDetail.source_code
      const codeType = this.taskDetail.code_type
      if (!rawCode) {
        return []
      }
      let sourceCode = rawCode
      if (typeof sourceCode === 'string') {
        try {
          sourceCode = JSON.parse(sourceCode)
        } catch (e) {
          return [{
            name: '代码[0]',
            code: sourceCode,
            language: this.getLanguage(codeType)
          }]
        }
      }
      if (!Array.isArray(sourceCode)) {
        return []
      }
      const list = []
      for (let i = 0; i < sourceCode.length; i++) {
        let code
        if (codeType === 'qubo') {
          code = getQuboPrettyPrint(sourceCode[i])
        } else {
          code = sourceCode[i]
        }
        list.push({
          name: `代码[${i}]`,
          code: code,
          language: this.getLanguage(codeType)
        })
      }
      return list
    }
  },
  watch: {
    '$route.params.jobId'(newVal) {
      if (newVal !== this.jobId) {
        this.jobId = newVal
        this.fetchTaskDetails()
      }
    }
  },
  created() {
    this.fetchTaskDetails()
  },
  mounted() {
    this.formatTaskItems()
  },
  methods: {
    getJobStatus,
    getJobStatusTag,
    getJobResultsContent,

    fetchTaskDetails() {
      // 调用API获取任务详情
      queryJobDetails(this.jobId)
        .then(response => {
          if (!response.error) {
            this.taskDetail = response.result
            this.formatTaskItems()
          }
        })
        .catch(error => {
          console.error('获取任务详情失败:', error)
          this.$message.error(`获取任务详情失败：${error || '未知错误'}`)
        })
    },
    formatTaskItems() {
      // 左列信息
      this.leftItems = [
        { label: '作业ID', value: this.taskDetail.job_id, color: '#409EFF' },
        {
          label: '提交时间',
          value: convertDate(this.taskDetail.created_at),
          color: '#409EFF'
        },
        {
          label: '更新时间',
          value: convertDate(this.taskDetail.updated_at),
          color: '#409EFF'
        },
        {
          label: '代码参数',
          value: this.taskDetail.params && Object.keys(this.taskDetail.params).length
            ? JSON.stringify(this.taskDetail.params, null, 2)
            : '未指定',
          color: '#409EFF'
        },
        {
          label: '作业自定义选项',
          value: this.taskDetail.options && Object.keys(this.taskDetail.options).length
            ? JSON.stringify(this.taskDetail.options, null, 2)
            : '未指定',
          color: '#409EFF'
        },
        {
          label: '转译器',
          value: this.taskDetail.transpiler || '无',
          color: '#409EFF'
        },
        {
          label: '转译器自定义选项',
          value: this.taskDetail.transpiler_options && Object.keys(this.taskDetail.transpiler_options).length
            ? JSON.stringify(this.taskDetail.transpiler_options, null, 2)
            : '未指定',
          color: '#409EFF'
        },
        { label: '后端设备', value: this.taskDetail.backend, color: '#409EFF' },
        {
          label: '后端驱动自定义选项',
          value: this.taskDetail.driver_options && Object.keys(this.taskDetail.driver_options).length
            ? JSON.stringify(this.taskDetail.driver_options, null, 2)
            : '未指定',
          color: '#409EFF'
        },
        {
          label: '错误缓解自定义选项',
          value: this.taskDetail.qem_options && Object.keys(this.taskDetail.qem_options).length
            ? JSON.stringify(this.taskDetail.qem_options, null, 2)
            : '未指定',
          color: '#409EFF'
        },
        {
          label: '错误纠正自定义选项',
          value: this.taskDetail.qec_options && Object.keys(this.taskDetail.qec_options).length
            ? JSON.stringify(this.taskDetail.qec_options, null, 2)
            : '未指定',
          color: '#409EFF'
        },
        {
          label: '作业描述',
          value: this.taskDetail.description || '未填写',
          color: '#409EFF'
        }
      ]

      // 右列信息
      this.rightItems = [
        {
          label: '作业状态',
          value: getJobStatus(this.taskDetail.job_status),
          color: '#67C23A'
        },
        {
          label: '完成时间',
          value: convertDate(this.taskDetail.ended_at),
          color: '#67C23A'
        },
        {
          label: '优先级',
          value: this.taskDetail.job_priority,
          color: '#67C23A'
        },
        {
          label: '线路聚合',
          value: getCircuitAggregation(this.taskDetail.circuit_aggregation),
          color: '#67C23A'
        },
        {
          label: '运行模式',
          value: this.taskDetail.dry_run ? '模拟运行(dry-run)' : '真实运行',
          color: '#67C23A'
        },
        {
          label: '测量次数(shots)',
          value: this.taskDetail.shots,
          color: '#67C23A'
        }
      ]
    },
    isSequenceTask() {
      return this.taskDetail.task_type === 'sequence_task'
    },

    // Map job code_type to a language id for display purposes.
    getLanguage(codeType) {
      if (['qasm', 'qasm2', 'qasm3'].includes(codeType)) {
        return 'qasm'
      }
      if (codeType === 'json' || codeType === 'qubo') {
        return 'json'
      }
      return 'qasm'
    },

    // Source code is rendered via `v-text`, which escapes HTML natively.
    // The previous monaco.editor.colorize + v-html pipeline was removed
    // to eliminate the v-html XSS surface flagged by static analysis.

    // Collapse toggles for source code and result cards (expanded by default)
    isSourceCollapsed(index) {
      return !!this.collapsedSource[index]
    },
    toggleSource(index) {
      this.collapsedSource[index] = !this.collapsedSource[index]
    },
    isResultCollapsed(index) {
      return !!this.collapsedResult[index]
    },
    toggleResult(index) {
      this.collapsedResult[index] = !this.collapsedResult[index]
    }
  }
}
</script>

<style scoped>
.job-detail-container {
  padding: 10px;
}

.header { margin: 0; }

.detail-container {
  background: var(--el-bg-color);
}

.job-card {
  box-shadow: 0 5px 12px rgba(0, 0, 0, 0.1);
  border-radius: 10px;
  overflow: hidden;
}

.job-header {
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
  white-space: pre-wrap;
  color: var(--el-text-color-regular);
  word-break: break-all;
}

.job-content h3 {
  margin-bottom: 15px;
  font-size: 16px;
}

:deep(.job-content pre ) {
  background-color: var(--el-fill-color-light);
  padding: 15px;
  border-radius: 5px;
  font-family: 'Courier New', Courier, monospace;
  color: #666a71;
  white-space: pre-wrap;
  word-wrap: break-word;
}

:deep(.scrollable-content ) {
  width: 100%;
  max-height: 600px;
  overflow: auto;
  background-color: var(--el-fill-color-light);
  padding: 15px;
  border-radius: 5px;
  font-family: 'Courier New', Courier, monospace;
  color: #65676a;
  white-space: pre-wrap;
}
:deep(pre ) {
  margin: 0;
  white-space: pre-wrap;
}

:deep(.el-tag--red ) {
  color: red;
  background: lightyellow;
  font-weight: bold;
}

:deep(.el-tag--yellow ) {
  color: yellow;
  font-weight: bold;
}

:deep(.el-tag--orange ) {
  color: orange;
  font-weight: bold;
}

:deep(.el-tag--indigo ) {
  color: indigo;
  font-weight: bold;
}

:deep(.el-tag--green ) {
  color: green;
  font-weight: bold;
}

:deep(.el-tag--blue ) {
  color: blue;
  font-weight: bold;
}

:deep(.el-tag--grey ) {
  color: grey;
  font-weight: bold;
}

/* source code card */
.source-code-card {
  margin-bottom: 8px;
}
.card-collapse-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  user-select: none;
}
.source-code-card-header {
  font-weight: 600;
  color: var(--el-text-color-primary);
  font-size: 14px;
}
.collapse-icon {
  color: var(--el-text-color-secondary);
  font-size: 14px;
}

:deep(.source-code-card .el-card__header) {
  padding: 8px 15px;
}
:deep(.source-code-card .el-card__body) {
  padding: 0;
}
.source-code-body {
  overflow-x: auto;
}

/* result card */
.result-card {
  margin-bottom: 8px;
}
:deep(.result-card .el-card__header) {
  padding: 8px 15px;
}
.result-body {
  padding: 12px 15px;
}

/* code block rendered by monaco.editor.colorize (mtk* classes are styled
   by monaco's injected theme CSS) */
.code-block {
  background-color: #f8f9fa;
  padding: 12px 15px;
  margin: 0;
  font-family: 'Consolas', 'Courier New', Courier, monospace;
  font-size: 13px;
  line-height: 1.6;
  overflow-x: auto;
}
.code-block code {
  white-space: pre;
  font-family: inherit;
}
</style>
