<template>
  <div class="transpiler-detail-container">
    <div class="header">
      <h2>转译器详情</h2>
    </div>
    <div class="detail-container">
      <el-card class="transpiler-card">
        <div class="transpiler-header">
          <h2>{{ transpilerDetails.name || '未命名' }} ({{ transpilerDetails.alias_name || '无别名' }})</h2>
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
            </el-timeline>
          </div>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script>
import { getTranspiler } from '@/api/transpiler'
import { getEnable } from '@/common/library'

export default {
  name: 'TranspilerDetails',
  data() {
    return {
      transpilerName: this.$route.params.transpilerName,
      transpilerDetails: {
        name: '',
        alias_name: '',
        enable: '',
        supported_code_types: '',
        transpiler_options: '',
        transpiler_options_schema: ''
      },
      leftItems: [],
      rightItems: []
    }
  },
  watch: {
    '$route.params.transpilerName'(newVal) {
      if (newVal !== this.transpilerName) {
        this.transpilerName = newVal
        this.fetchTranspilerDetails()
      }
    }
  },
  created() {
    this.fetchTranspilerDetails()
  },
  mounted() {
    this.formatTranspilerItems()
  },
  methods: {
    getEnable,
    fetchTranspilerDetails() {
      // 调用API获取转译器详情
      getTranspiler(this.transpilerName)
        .then(response => {
          if (!response.error) {
            this.transpilerDetails = response.result
            this.formatTranspilerItems()
          }
        })
        .catch(error => {
          console.error('获取转译器详情失败:', error)
          this.$message.error(`获取转译器详情失败：${error || '未知错误'}`)
        })
    },
    formatTranspilerItems() {
      // 左列信息
      this.leftItems = [
        { label: '转译器名称', value: this.transpilerDetails.name, color: '#409EFF' },
        { label: '启用', value: getEnable(this.transpilerDetails.enable), color: '#409EFF' },
        { label: '支持的代码类型', value: this.transpilerDetails.supported_code_types, color: '#409EFF' },
        { label: '转译器选项', value: this.transpilerDetails.transpiler_options || '无', color: '#409EFF' },
        { label: '转译器选项schema', value: this.transpilerDetails.transpiler_options_schema || '无', color: '#409EFF' }
      ]

      // 右列信息
      this.rightItems = [
      ]
    }
  }
}
</script>

<style scoped>
.transpiler-detail-container {
  padding: 10px;
}

.header {
  margin-bottom: 20px;
}

.detail-container {
  background: white;
}

.transpiler-card {
  box-shadow: 0 5px 12px rgba(0, 0, 0, 0.1);
  border-radius: 10px;
  overflow: hidden;
}

.transpiler-header {
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

.transpiler-content h3 {
  margin-bottom: 15px;
  font-size: 16px;
}

::v-deep .transpiler-content pre {
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
</style>
