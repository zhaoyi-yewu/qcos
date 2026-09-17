<template>
  <div class="task-submit-container">
    <div class="header">
      <h2>序列任务提交</h2>
    </div>
    <div class="form-container">
      <el-form
        ref="taskForm"
        :model="taskData"
        :rules="rules"
        label-width="120px"
        status-icon
        class="task-form"
      >
        <el-form-item label="选择任务文件" prop="taskFile">
          <div class="file-upload">
            <el-upload
              ref="upload"
              class="upload-demo"
              action=""
              :auto-upload="false"
              :on-change="handleFileChange"
              :limit="1"
              :file-list="taskData.taskFileList"
            >
              <el-button type="primary">选择文件</el-button>
              <div slot="tip" class="upload-tip">
                请上传任务文件
              </div>
            </el-upload>
          </div>
        </el-form-item>

        <el-form-item label="任务id" prop="taskID">
          <el-input
            v-model="taskData.taskID"
            placeholder="请输入任务id"
            label="任务id"
          />
        </el-form-item>

        <el-form-item label="任务执行shot" prop="shotCount">
          <el-input-number
            v-model="taskData.shotCount"
            :min="1"
            :max="10000"
            label="任务执行shot"
            :step="1"
          />
        </el-form-item>

        <el-form-item label="任务比特数" prop="qnum">
          <el-input-number
            v-model="taskData.qnum"
            :min="1"
            :max="1000"
            label="任务比特数"
          />
        </el-form-item>

        <!--
        <el-form-item label="任务类型" prop="type">
          <el-select v-model="taskData.taskType" placeholder="任务类型">
            <el-option
              v-for="item in typeList"
              :key="item.label"
              :label="item.value"
              :value="item.value"
            ></el-option>
          </el-select>
        </el-form-item>
      -->

        <el-form-item>
          <el-button type="primary" @click="submitForm">提交任务</el-button>
          <el-button @click="resetForm">重置</el-button>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<script>
import { postSubmitSequence } from '@/api/job'

export default {
  data() {
    return {
      taskData: {
        taskFile: '',
        taskFileList: [],
        taskID: '',
        shotCount: 100,
        qnum: 1
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
          { required: true, message: '请选择任务文件', trigger: 'change' }
        ],
        taskID: [
          { required: true, message: '请输入任务ID', trigger: 'blur' }
        ],
        shotCount: [
          { required: true, message: '请输入任务执行shot', trigger: 'blur' }
        ],
        taskQnum: [
          { required: true, message: '请输入任务比特数', trigger: 'blur' }
        ]
        /*
        taskType: [
          { required: true, message: '请选择任务类型', trigger: 'blur' }
        ]
          */
      }
    }
  },

  methods: {
    // 处理文件上传变化
    handleFileChange(file, fileList) {
      // 添加文件类型验证
      const isAllowedType = file.name.endsWith('.txt')
      if (!isAllowedType) {
        this.$message.error('只能上传TXT格式的文件！')
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

    submitForm() {
      this.$refs.taskForm.validate((valid) => {
        if (!valid) {
          this.$message.error('请完善表单信息！')
          return
        }

        if (!this.taskData.taskFile) {
          this.$message.error('请至少上传一个文件！')
          return
        }

        // 定义 reader
        const reader = new FileReader()

        // 文件读取成功后的回调
        reader.onload = (e) => {
          const fileContentBase64 = e.target.result
          console.log(fileContentBase64)

          const requestData = {
            data: {
              task_content: fileContentBase64,
              task_id: this.taskData.taskID,
              shots: this.taskData.shotCount,
              q_num: this.taskData.qnum
            }
          }

          postSubmitSequence(requestData)
            .then((response) => {
              if (response.code === 0) {
                this.$notify({
                  title: '任务提交成功',
                  message: '提交任务已成功启动',
                  type: 'success',
                  duration: 2000
                })
              } else {
                this.$notify.error({
                  title: '任务提交失败',
                  message: response.message || '未知错误导致失败',
                  duration: 3500
                })
              }
            })
            .catch((error) => {
              this.$notify.error({
                title: '请求异常',
                message: error.message || '网络通信出现问题，请检查连接',
                duration: 4500
              })
            })
            .finally(() => {
              this.isSubmitting = false
            })
        }

        // 文件读取错误的回调
        reader.onerror = (error) => {
          this.$message.error('文件读取失败：' + error.message)
          console.error('文件读取失败:', error)
        }

        // 使用 readAsDataURL 方法读取文件
        reader.readAsDataURL(this.taskData.taskFile.raw)
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
    max-width: 800px;
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
</style>
