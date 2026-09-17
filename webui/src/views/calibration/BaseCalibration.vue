<template>
  <div class="config-container">
    <el-card shadow="never">
      <div #header>
        <div class="header-content">
          <div class="header-left">
            <span class="config-title">{{ config.title }}</span>

            <!-- 新增参数值显示区域 -->
            <div class="calibration-display">
              <span v-if="currentCalibrationValue !== null" class="current-value">
                当前参数值：{{ formatCalibrationValue(currentCalibrationValue) }}
              </span>
              <span v-else class="no-value">
                未获取参数值
              </span>
              <el-button
                size="small"
                :loading="isRefreshingValue"
                :icon="Refresh"
                class="refresh-btn"
                @click.stop="fetchCalibrationValue"
              />
            </div>
          </div>
          <el-button
            :type="scanStatus === 'running' ? 'danger' : 'primary'"
            :loading="isSubmitting"
            :disabled="isButtonDisabled"
            style="float: right;"
            class="run-button"
            @click="handleControlClick"
          >
            {{ scanStatus === 'running' ? '停止' : '运行' }}
          </el-button>
        </div>
      </div>
      <!-- 动态渲染参数表单 -->
      <el-form label-position="left" label-width="120px">
        <!-- 基础参数动态生成 -->
        <template v-for="(field, index) in config.formFields.base">
          <el-form-item :key="`base-${index}`" :label="field.label">
            <el-input-number
              v-model="params[field.key]"
              :min="field.min || 1"
              :step="field.step || 1"
              controls-position="right"
            />
          </el-form-item>
        </template>

        <!-- 科学计数法参数动态生成 -->
        <template v-for="param in config.formFields.sciParams">
          <el-form-item :key="param.key" :label="param.label">
            <div class="sci-input-group">
              <el-input-number
                v-model="params[param.key].coefficient"
                :precision="0"
                :min="1"
                :step="1"
                controls-position="right"
              />
              <span class="sci-symbol">e</span>
              <el-input-number
                v-model="params[param.key].exponent"
                :min="-20"
                :max="20"
                :step="1"
                controls-position="right"
              />
            </div>
          </el-form-item>
        </template>
      </el-form>

      <!-- 扫描结果展示 -->
      <div v-if="showScanResults" class="scan-results">
        <div class="scan-status">
          <span class="status-text">  当前扫描状态: {{ scanStatusMap[scanStatus] }}
            <span v-if="errorMessage" class="error-message">(错误信息: {{ errorMessage }})</span>
          </span>
          <div v-if="scanStatus === 'complete'" class="submit-area">
            <el-input
              v-model="submittedValue"
              placeholder="请输入校准值"
              size="mini"
              style="width: 180px; margin-left: 20px;"
            />
            <el-button
              type="success"
              size="mini"
              style="margin-left: 10px;"
              :loading="isSubmittingValue"
              @click="handleValueSubmit"
            >
              提交校准
            </el-button>
          </div>
        </div>

        <!-- 优化后的表格结构 -->
        <div class="horizontal-table">
          <el-table
            :data="transposedData"
            border
            style="width: 100%"
            :show-header="true"
          >
            <!-- 固定指标列 -->
            <el-table-column
              prop="metric"
              label="指标"
              width="120"
              fixed
              align="center"
            />

            <!-- 动态扫描点列 -->
            <el-table-column
              v-for="(scan, index) in scanResults"
              :key="index"
              :label="`扫描点 ${index + 1}`"
              align="center"
              width="100"
            >
              <template v-slot="{ row }">
                <div class="metric-value">
                  {{ row.values[index] }}
                </div>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script>
import { Refresh } from '@element-plus/icons-vue'
import {
  postCalibration,
  getCalibration,
  stopCalibration,
  submitCalibrationVal,
  getCalibrationVal
} from '@/api/job'

export default {
  components: { Refresh },
  props: {
    // 差异化配置
    config: {
      type: Object,
      required: true,
      validator: (value) => {
        return [
          'title', // 页面标题
          'apiType', // 接口类型（如 rabi/arrange_ch1）
          'formFields' // 表单字段配置
        ].every(key => key in value)
      }
    }
  },
  data() {
    return {
      params: this.generateInitialParams(),
      sciParams: [
        { key: 'init_val', label: '扫描起始值' },
        { key: 'step', label: '扫描步长' }
      ],
      currentConfig: {
        name: this.config.title,
        id: 1
      },
      isSubmitting: false,
      scanStatus: 'ready',
      scanResults: [],
      pollInterval: null,
      scanStatusMap: {
        running: '扫描进行中',
        complete: '扫描已完成',
        ready: '准备就绪',
        fail: '扫描失败',
        abort: '扫描已中止'
      },
      errorMessage: '',
      submittedValue: '', // 新增提交值字段
      isSubmittingValue: false, // 新增提交状态
      currentCalibrationValue: null, // 当前校准值
      calibrationValueInterval: null, // 自动刷新定时器
      isRefreshingValue: false // 刷新按钮加载状态
    }
  },

  // 计算属性
  computed: {
    transposedData() {
      return [
        {
          metric: '扫描值',
          values: this.scanResults.map(item => item.scan_value.toFixed(2))
        },
        {
          metric: '重排率 (%)',
          values: this.scanResults.map(item => item.rea_qubit_res.toFixed(2))
        },
        {
          metric: '翻转率 (%)',
          values: this.scanResults.map(item => item.raman_qubit_res.toFixed(2))
        }
      ]
    },
    showScanResults() {
      return ['running', 'complete', 'fail', 'abort'].includes(this.scanStatus) && this.scanResults.length > 0
    },
    // 新增按钮禁用状态计算
    isButtonDisabled() {
      return this.isSubmitting
    }
  },

  // 生命周期钩子
  /*mounted() {
    // 初始化获取一次
    this.fetchCalibrationValue()

    // 设置自动刷新
    this.calibrationValueInterval = setInterval(() => {
      if (!this.isRefreshingValue) {
        this.fetchCalibrationValue()
      }
    }, 5000)
  },*/
  mounted() {
    // 初始化获取一次
    this.fetchCalibrationValue()

    // 设置自动刷新
    this.calibrationValueInterval = setInterval(() => {
      if (!this.isRefreshingValue) {
        this.fetchCalibrationValue()
      }
    }, 5000)

    // 加载本地存储的扫描结果和状态
    this.loadFromLocalStorage()
  },

  // 方法
  methods: {
    // 20250604新增saveToLocalStorage和loadFromLocalStorage以应对刷新页面扫描结果丢失问题
    // 保存扫描结果和状态到本地存储
    saveToLocalStorage() {
      localStorage.setItem(`scanResults_${this.config.apiType}`, JSON.stringify(this.scanResults))
      localStorage.setItem(`scanStatus_${this.config.apiType}`, this.scanStatus)
    },
    // 从本地存储加载扫描结果和状态
    loadFromLocalStorage() {
      const savedScanResults = localStorage.getItem(`scanResults_${this.config.apiType}`)
      const savedScanStatus = localStorage.getItem(`scanStatus_${this.config.apiType}`)
      if (savedScanResults) {
        this.scanResults = JSON.parse(savedScanResults)
      }
      if (savedScanStatus) {
        this.scanStatus = savedScanStatus
      }
    },

    // 根据配置生成初始参数
    generateInitialParams() {
      const params = {}
      // 动态添加基础字段
      this.config.formFields.base.forEach(field => {
        params[field.key] = field.initialValue || 1
      })
      // 动态添加科学计数法字段
      this.config.formFields.sciParams.forEach(param => {
        params[param.key] = {
          coefficient: param.initialCoeff || 1,
          exponent: param.initialExpo || -6
        }
      })
      return params
    },

    // 格式化科学计数法显示
    formatCalibrationValue(value) {
      if (!value) return 'N/A'
      const exponent = Math.floor(Math.log10(value))
      const coefficient = value / Math.pow(10, exponent)
      return `${coefficient.toFixed(2)}e${exponent}`
    },

    // 获取校准值方法
    async fetchCalibrationValue() {
      try {
        this.isRefreshingValue = true
        const response = await getCalibrationVal(this.config.apiType) // 根据实际类型调整
        if (response.code === 0) {
          this.currentCalibrationValue = response.data
        }
      } catch (error) {
        console.error('获取校准值失败:', error)
      } finally {
        this.isRefreshingValue = false
      }
    },

    // 处理运行/停止按钮的点击事件
    handleControlClick() {
      if (this.scanStatus === 'running') {
        this.handleStop()
      } else {
        this.handleSubmit()
      }
    },

    // 停止扫描任务
    async handleStop() {
      try {
        const response = await stopCalibration()

        if (response.code === 0) {
          this.$notify({
            title: '操作成功',
            message: '扫描任务已停止',
            type: 'success',
            duration: 2000
          })
          this.startPolling()
        } else {
          this.$notify.error({
            title: '扫描任务终止失败',
            message: response.message || '未知错误导致任务失败',
            duration: 3500
          })
        }
      } catch (error) {
        this.$notify.error({
          title: '停止失败',
          message: error.message || '停止操作出现异常',
          duration: 3500
        })
      } finally {
        this.scanStatus = 'abort'
        this.stopPolling()
      }
    },

    // 停止轮询
    stopPolling() {
      if (this.pollInterval) {
        clearInterval(this.pollInterval)
        this.pollInterval = null
      }
    },

    // 提交扫描任务
    async handleSubmit() {
      try {
        if (this.isButtonDisabled) return

        this.isSubmitting = true

        // 开始新的扫描时清空历史结果
        this.scanResults = []
        this.scanStatus = 'ready'
        this.errorMessage = ''

        const requestData = {
          type: this.config.apiType,
          data: {
            ...this.mapParamsToApi()
          }
        }

        const response = await postCalibration(requestData)

        if (response.code === 0) {
          this.$notify({
            title: '操作成功',
            message: '扫描任务已成功启动',
            type: 'success',
            duration: 2000
          })
          this.startPolling()
        } else {
          this.$notify.error({
            title: '扫描失败',
            message: response.message || '未知错误导致任务失败',
            duration: 3500
          })
        }
      } catch (error) {
        this.$notify.error({
          title: '请求异常',
          message: error.message || '网络通信出现问题，请检查连接',
          duration: 4500
        })
      } finally {
        this.isSubmitting = false
      }
    },

    // 开始轮询扫描状态
    startPolling() {
      this.stopPolling()
      // 立即执行第一次查询
      this.pollInterval = setInterval(async() => {
        await this.fetchScanStatus()
      }, 5000)

      // 首次立即执行
      this.fetchScanStatus()
    },

    // 将表单参数映射为 API 请求格式
    mapParamsToApi() {
      return this.config.formFields.mapping(this.params)
    },

    // 获取扫描状态和结果
    /*async fetchScanStatus() {
      try {
        const res = await getCalibration(this.config.apiType)
        if (res.code === 0) {
          this.scanResults = res.data.res || []
          this.scanStatus = res.data.status
          // 扫描完成或失败时停止轮询
          if (res.data.status === 'complete' || res.data.status === 'fail') {
            if (res.data.status === 'fail') {
              this.errorMessage = res.data.message
            }
            clearInterval(this.pollInterval)
            this.pollInterval = null
          }
        }
      } catch (error) {
        console.error('获取扫描结果失败:', error)
        // 错误时停止轮询
        clearInterval(this.pollInterval)
        this.pollInterval = null
      }
    },*/
    async fetchScanStatus() {
      try {
        const res = await getCalibration(this.config.apiType)
        if (res.code === 0) {
          this.scanResults = res.data.res || []
          this.scanStatus = res.data.status
          this.saveToLocalStorage(); // 保存到本地存储
          // 扫描完成或失败时停止轮询
          if (res.data.status === 'complete' || res.data.status === 'fail') {
            if (res.data.status === 'fail') {
              this.errorMessage = res.data.message
            }
            clearInterval(this.pollInterval)
            this.pollInterval = null
          }
        }
      } catch (error) {
        console.error('获取扫描结果失败:', error)
        // 错误时停止轮询
        clearInterval(this.pollInterval)
        this.pollInterval = null
      }
    },

    // 组件销毁时清除定时器
    beforeUnmount() {
      // 清除定时器
      if (this.calibrationValueInterval) {
        clearInterval(this.calibrationValueInterval)
      }
      // 确保销毁时清除定时器
      if (this.pollInterval) {
        clearInterval(this.pollInterval)
        this.pollInterval = null
      }
    },

    // 计算科学计数法的值
    calcScientificValue(key) {
      const { coefficient, exponent } = this.params[key]
      return coefficient * Math.pow(10, exponent)
    },

    // 提交校准值
    /*async handleValueSubmit() {
      try {
        if (!this.submittedValue) {
          this.$message.warning('请输入要提交的校准值')
          return
        }

        this.isSubmittingValue = true

        // 调用提交接口（需要根据实际API修改）
        const response = await submitCalibrationVal({
          type: this.config.apiType,
          data: Number(this.submittedValue)
        })

        if (response.code === 0) {
          this.$notify({
            title: '提交成功',
            message: '校准值已成功提交至服务器',
            type: 'success',
            duration: 2000
          })
          this.submittedValue = '' // 清空输入框
        }
      } catch (error) {
        this.$notify.error({
          title: '提交失败',
          message: error.message || '校准值提交失败，请检查网络',
          duration: 3000
        })
      } finally {
        this.isSubmittingValue = false
      }
    }*/
    async handleValueSubmit() {
      try {
        if (!this.submittedValue) {
          this.$message.warning('请输入要提交的校准值')
          return
        }

        this.isSubmittingValue = true

        // 调用提交接口（需要根据实际API修改）
        const response = await submitCalibrationVal({
          type: this.config.apiType,
          data: Number(this.submittedValue)
        })

        if (response.code === 0) {
          this.$notify({
            title: '提交成功',
            message: '校准值已成功提交至服务器',
            type: 'success',
            duration: 2000
          })
          this.submittedValue = '' // 清空输入框
          this.saveToLocalStorage() // 保存到本地存储
        }
      } catch (error) {
        this.$notify.error({
          title: '提交失败',
          message: error.message || '校准值提交失败，请检查网络',
          duration: 3000
        })
      } finally {
        this.isSubmittingValue = false
      }
    }
  }
}
</script>

<style scoped>
.config-container {
  padding: 20px;
}

.config-title {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}

.sci-input-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.sci-symbol {
  padding: 0 5px;
  color: #606266;
}

.scan-results {
  margin-top: 30px;
  border-top: 1px solid #ebeef5;
  padding-top: 20px;
}

.scan-status {
  display: flex;
  align-items: center;
  margin-bottom: 20px;
}

.status-text {
  font-size: 14px;
  color: #606266;
}

/* 横向表格样式 */
.horizontal-table {
  position: relative;
  margin-top: 20px;
}

.metric-value {
  padding: 8px;
  font-size: 14px;
  color: #606266;
}

/* 调整表格行样式 */
::v-deep .el-table__row td {
  padding: 0 !important;
  border-right: 1px solid #ebeef5;
}

::v-deep .el-table__row:last-child td {
  border-bottom: 1px solid #ebeef5;
}

::v-deep .el-table th {
  background-color: #f5f7fa !important;
  color: #606266;
  font-weight: 600;
}

::v-deep .el-table td {
  padding: 12px 0;
}

.horizontal-table {
  overflow-x: auto;
}

.error-message {
  color: #F56C6C;
  margin-left: 10px;
  font-size: 12px;
}

.submit-area {
  display: flex;
  align-items: center;
  margin-left: auto; /* 使提交区域靠右 */
}

.calibration-display {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #606266;
  font-size: 14px;
}

.current-value {
  color: #67C23A;
}

.no-value {
  color: #909399;
}

.refresh-btn {
  padding: 5px;
  margin-left: 8px;
}

.header-content {
  display: flex;
  justify-content: space-between; /* 两侧对齐 */
  align-items: center;
  width: 100%; /* 确保占满父容器 */
}

.header-left {
  display: flex;
  align-items: center;
  gap: 20px;
  flex-grow: 1; /* 允许扩展剩余空间 */
}

.run-button {
  margin-left: 20px; /* 与左侧内容保持间距 */
  flex-shrink: 0; /* 防止按钮被压缩 */
}
</style>
