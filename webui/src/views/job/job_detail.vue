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
                <div class="timeline-content" v-text="item.value" />
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
                <div class="timeline-content" v-text="item.value" />
              </el-timeline-item>
              <el-timeline-item
                color="#67C23A"
              >
                <div class="timeline-label">作业结果</div>
                <template
                  v-for="(item, index) in getTaskResultsContent(taskDetail.results, taskDetail.code_type)"
                >
                  <el-card v-if="'error' in item" :key="'results-' + index">
                    <b>代码[{{ index }}]错误信息:</b><br>
                    <div class="scrollable-content">
                      错误码: {{ item['error']['code'] }}
                      <br>
                      错误信息: {{ item['error']['message'] }}
                    </div>
                  </el-card>
                  <el-card v-else :key="'results-' + index">
                    <b>代码[{{ index }}]结果:</b><br>
                    量子比特数: {{ item['num_qubits'] || 'N/A' }} <br>
                    性能分析(profiling): <br>
                    <div class="scrollable-content">
                      <pre>{{ item['profiling'] }}</pre>
                    </div>
                    <br>
                    结果: <br>
                    <div class="scrollable-content">
                      <pre>{{ item['result'] }}</pre>
                    </div>
                  </el-card>
                  <br :key="'br-' + index">
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
  getTaskCompletedTimeDisplay,
  getTaskResultsContent,
  getTaskSourceContent
} from '@/common/library'

export default {
  name: 'TaskDetail',
  data() {
    return {
      taskId: this.$route.params.taskId,
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
      rightItems: []
    }
  },
  watch: {
    '$route.params.taskId'(newVal) {
      if (newVal !== this.taskId) {
        this.taskId = newVal
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
    getTaskResultsContent,

    fetchTaskDetails() {
      // 调用API获取任务详情
      queryJobDetails('task_info', this.taskId)
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
          value: convertDate(this.taskDetail.creation_date),
          color: '#409EFF'
        },
        {
          label: '转译器',
          value: this.taskDetail.transpiler || '无',
          color: '#409EFF'
        },
        {
          label: '转译器自定义参数',
          value: this.taskDetail.transpiler_options || '未指定',
          color: '#409EFF'
        },
        { label: '后端设备', value: this.taskDetail.backend, color: '#409EFF' },
        {
          label: '后端驱动自定义参数',
          value: this.taskDetail.driver_options || '未指定',
          color: '#409EFF'
        },
        {
          label: '作业描述',
          value: `<div class="scrollable-content"><pre>${this.taskDetail.description || '未填写'}</pre></div>`,
          color: '#409EFF'
        },
        {
          label: `作业内容 (代码类型: ${this.taskDetail.code_type})`,
          value: `${getTaskSourceContent(this.taskDetail.source_code, this.taskDetail.code_type)}`,
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
          value: getTaskCompletedTimeDisplay(this.taskDetail.job_status, this.taskDetail.end_date),
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
    }
  }
}
</script>

<style scoped>
.job-detail-container {
  padding: 10px;
}

.header {
  margin-bottom: 20px;
}

.detail-container {
  background: white;
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
  color: #3b3f48;
}

.timeline-content {
  white-space: pre-line;
  color: #665c5c;
  word-break: break-all;
}

.job-content h3 {
  margin-bottom: 15px;
  font-size: 16px;
}

::v-deep .job-content pre {
  background-color: #f5f7fa;
  padding: 15px;
  border-radius: 5px;
  font-family: 'Courier New', Courier, monospace;
  color: #666a71;
  white-space: pre-wrap;
  word-wrap: break-word;
}

::v-deep .scrollable-content {
  width: 100%;
  max-height: 600px;
  overflow: auto;
  background-color: #f5f7fa;
  padding: 15px;
  border-radius: 5px;
  font-family: 'Courier New', Courier, monospace;
  color: #65676a;
  white-space: pre-wrap;
}
::v-deep pre {
  margin: 0;
  white-space: pre-wrap;
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
