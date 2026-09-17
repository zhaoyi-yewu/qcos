<template>
  <div v-if="loaded" class="task-submit-container">
    <div class="header">
      <h2>QUBO矩阵作业提交</h2>
    </div>
    <div class="form-container">
      <el-form
        ref="taskForm"
        :model="taskData"
        :rules="rules"
        label-width="150px"
        status-icon
        class="task-form"
      >
        <el-form-item label="选择QUBO文件" prop="taskFile">
          <div class="file-upload">
            <el-upload
              ref="upload"
              class="upload-demo"
              accept=".json,.csv"
              action=""
              :auto-upload="false"
              :on-change="handleFileChange"
              :on-remove="handleFileChange"
              :multiple="true"
              :file-list="taskData.taskFileList"
            >
              <el-button type="primary">选择文件</el-button>
            </el-upload>
          </div>
        </el-form-item>

        <el-form-item label="作业名称" prop="taskName">
          <el-input
            v-model="taskData.taskName"
            placeholder="请输入作业名称 (可选)"
            label="作业名称"
          />
        </el-form-item>

        <el-form-item label="作业描述" prop="taskDescription">
          <el-input
            v-model="taskData.taskDescription"
            type="textarea"
            rows="2"
            placeholder="请输入作业描述 (可选)"
            label="作业描述"
          />
        </el-form-item>

        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="后端设备" prop="taskBackend">
              <el-select
                v-model="taskData.taskBackend"
                class="auto-width"
                placeholder="请输入后端设备"
                label="后端驱动"
              >
                <el-option
                  v-for="(device, device_name) in devices"
                  :key="device_name"
                  :label="device['alias_name'] + ' (' + device_name + ')'"
                  :value="device_name"
                />
              </el-select>
            </el-form-item>
          </el-col>

          <el-col :span="12">
            <el-form-item label="驱动自定义参数" prop="driverOptions">
              <el-input
                v-model="taskData.driverOptions"
                type="textarea"
                rows="2"
                placeholder="请输入驱动自定义参数 (可选)"
                label="驱动自定义参数"
              />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="作业优先级" prop="taskPriority">
          <el-input-number
            v-model="taskData.taskPriority"
            :min="1"
            :max="10"
            label="作业优先级"
          />
        </el-form-item>

        <el-form-item label="运行模式" prop="taskDryRun">
          <el-radio-group v-model="taskData.taskDryRun">
            <el-radio label="false" border>真实运行</el-radio>
            <el-radio label="true" border>模拟运行</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="性能调测选项" prop="profiling">
          <el-checkbox v-model="taskData.profilingScheduling">记录调度器耗时</el-checkbox>
          <el-checkbox v-model="taskData.profilingDriverParse">记录代码解析耗时</el-checkbox>
          <el-checkbox v-model="taskData.profilingCode">记录单代码运行耗时</el-checkbox>
          <el-checkbox v-model="taskData.profilingDriverRun">记录后端运行耗时</el-checkbox>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="submitForm">提交作业</el-button>
          <el-button @click="resetForm">重置</el-button>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<script>
import { postSubmitJob } from '@/api/job'
import { queryVersion } from '@/api/version'
import {
  filterDevices,
  isEmptyStr,
  quboParser,
  readMultiFiles
} from '@/common/library'
import { getDevices } from '@/api/device'

export default {
  data() {
    return {
      loaded: false,
      versionData: {
        version: '',
        api_version: '',
        supported_api_versions: [],
        platform_version: '',
        capabilities: {}
      },
      devices: {},
      devicesDetails: {},
      taskData: {
        taskFile: '',
        taskFileList: [],
        taskName: null,
        taskDescription: null,
        taskTranspiler: null,
        transpilerOptions: null,
        taskBackend: 'tiangong100',
        driverOptions: null,
        taskDryRun: 'false',
        shotCount: 1,
        taskPriority: 5,
        aggregationMode: 'none',
        profilingScheduling: false,
        profilingDriverParse: false,
        profilingDriverTranspile: false,
        profilingCode: false,
        profilingDriverRun: false
      },

      /*
      typeList: [
        { label: 'type1', value: 'PriorityTask' },
        { label: 'type2', value: 'ResponseRatioTask' },
        { label: 'type3', value: 'ShortestJobFirstTask' },
        { label: 'type4', value: 'TimePrecedenceTask' },
        { label: 'type5', value: 'Periodicask' },
        { label: 'type6', value: 'DependentTask' },
        { label: 'type7', value: 'BatchTask' },
        { label: 'type8', value: 'RealTimeTask' }
      ],
      */

      rules: {
        taskFile: [
          { required: true, message: '请选择QUBO文件', trigger: 'change' }
        ],
        taskName: [
          { required: false, message: '请输入作业名称 (可选)', trigger: 'blur' }
        ],
        taskDescription: [
          { required: false, message: '请输入作业描述 (可选)', trigger: 'blur' }
        ],
        taskBackend: [
          { required: true, message: '请输入后端驱动', trigger: 'blur' }
        ],
        taskDryRun: [
          { required: true, message: '请输入是否模拟运行(dry-run) (可选)', trigger: 'blur' }
        ],
        taskPriority: [
          { required: true, message: '请输入作业优先级', trigger: 'blur' }
        ]
        /*
        taskType: [
          { required: true, message: '请选择任务类型', trigger: 'blur' }
        ]
          */
      }
    }
  },

  created() {
    this.queryData()
  },

  methods: {
    async queryData() {
      await this.fetchVersion()
      await this.fetchDevices()
      this.devices = filterDevices(
        this.versionData,
        this.devicesDetails,
        {
          'code_types': ['qubo'],
          'enable': true
        }
      )
      this.loaded = true
    },

    async fetchVersion() {
      try {
        const response = await queryVersion()
        if (!response.error) {
          this.versionData = response.result
        } else {
          this.$message.error(`获取版本能力失败：${response.message || '未知错误'}`)
        }
      } catch (error) {
        console.error('获取版本能力失败:', error)
        this.$message.error('获取版本能力失败，请检查网络连接')
      }
    },

    async fetchDevices() {
      try {
        const response = await getDevices()
        if (!response.error) {
          this.devicesDetails = response.result
        } else {
          this.$message.error(`获取设备列表失败：${response.message || '未知错误'}`)
        }
      } catch (error) {
        console.error('获取设备列表失败:', error)
        this.$message.error('获取设备列表失败，请检查网络连接')
      }
    },

    // 处理文件上传变化
    handleFileChange(file, fileList) {
      // 添加文件类型验证
      const isAllowedType = file.name.endsWith('.json') || file.name.endsWith('.csv')
      if (!isAllowedType) {
        this.$message.error('只能上传json、csv格式的文件！')
        fileList.pop() // 如果类型不正确，移除该文件
        return
      }

      // 添加文件大小验证
      const isLt2M = file.size / 1024 / 1024 < 2
      if (!isLt2M) {
        this.$message.error('上传的文件大小不能超过 2MB！')
        fileList.pop() // 如果大小超过限制，移除该文件
        return
      }

      this.taskData.taskFile = file
      this.taskData.taskFileList = fileList
    },

    handleExceed(files, fileList) {
      this.handleFileChange(fileList[0], fileList)
    },

    submitForm() {
      this.$refs.taskForm.validate((valid) => {
        if (!valid) {
          this.$message.error('请完善作业提交信息！')
          return
        }

        if (!this.taskData.taskFile) {
          this.$message.error('请至少上传一个文件！')
          return
        }

        // 使用 readMultiFiles 方法读取多个文件
        readMultiFiles(this.taskData.taskFileList).then((fileObjList) => {
          const source_codes = []
          fileObjList.forEach(fileObj => {
            const fileName = fileObj['fileName']
            const content = fileObj['content']
            source_codes.push(quboParser(fileName, content))
          })

          let driverOptions = null
          if (!isEmptyStr(this.taskData.driverOptions)) {
            try {
              driverOptions = JSON.parse(this.taskData.driverOptions.trim())
            } catch (error) {
              this.$notify.error({
                title: '作业提交失败',
                message: error.message,
                duration: 4500
              })
              return
            } finally {
              this.isSubmitting = false
            }
          }

          let transpilerOptions = null
          if (!isEmptyStr(this.taskData.transpilerOptions)) {
            try {
              transpilerOptions = JSON.parse(this.taskData.transpilerOptions.trim())
            } catch (error) {
              this.$notify.error({
                title: '作业提交失败',
                message: error.message,
                duration: 4500
              })
              return
            } finally {
              this.isSubmitting = false
            }
          }

          const profiling = []
          if (this.taskData.profilingScheduling) {
            profiling.push('scheduling')
          }
          if (this.taskData.profilingDriverParse) {
            profiling.push('driver:parse')
          }
          if (this.taskData.profilingDriverTranspile) {
            profiling.push('driver:transpile')
          }
          if (this.taskData.profilingCode) {
            profiling.push('code')
          }
          if (this.taskData.profilingDriverRun) {
            profiling.push('driver:run')
          }

          const requestData = {
            jsonrpc: '2.0',
            id: 1,
            method: 'submit_job',
            params: {
              body: {
                source_code: source_codes,
                code_type: 'qubo',
                job_name: this.taskData.taskName,
                description: this.taskData.taskDescription,
                job_type: 'sampling',
                job_sched_policy: 'time_precedence',
                job_priority: this.taskData.taskPriority,
                backend: this.taskData.taskBackend,
                driver_options: driverOptions,
                transpiler: this.taskData.taskTranspiler,
                transpiler_options: transpilerOptions,
                profiling: profiling,
                dry_run: this.taskData.taskDryRun,
                shots: this.taskData.shotCount
              }
            }
          }

          postSubmitJob(requestData)
            .then((response) => {
              if (!response.error) {
                this.$notify({
                  title: '作业提交成功',
                  message: '作业已成功启动',
                  type: 'success',
                  duration: 2000
                })
              } else {
                this.$notify.error({
                  title: '作业提交失败',
                  message: '未知错误导致失败',
                  duration: 3500
                })
              }
            })
            .catch((error) => {
              this.$notify.error({
                title: '作业提交失败',
                message: error.message || '网络通信出现问题，请检查连接',
                duration: 4500
              })
            })
            .finally(() => {
              this.isSubmitting = false
            })
        }).catch((error) => {
          this.$notify.error({
            title: '文件读取错误',
            message: error.message,
            duration: 4500
          })
        })
      })
    },

    resetForm() {
      this.$refs.taskForm.resetFields()
      this.taskData.taskFileList = []
      this.taskData.taskFile = null
    }
  }
}
</script>

<style scoped>
.task-submit-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #f5f7fa;
  padding: 20px;
}

.header {
  margin-bottom: 30px;
}

.form-container {
  flex: 1;
  background: white;
  border-radius: 8px;
  padding: 30px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.05);
}

.task-form {
  max-width: 1500px;
}

.file-upload {
  width: 100%;
}

.upload-tip {
  margin-top: 8px;
  font-size: 12px;
  color: #909399;
}

.el-form-item {
  margin-bottom: 25px;
}

.el-button {
  margin-right: 15px;
}

.auto-width {
  min-width: 350px;
  text-align: start;
}
</style>
