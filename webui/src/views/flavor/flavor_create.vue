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
  <div class="flavor-create-container">
    <div class="header">
      <h2>新增资源规格</h2>
    </div>
    <div class="form-container">
      <el-card class="create-card">
        <el-form
          ref="formRef"
          :model="form"
          :rules="rules"
          label-width="160px"
          label-position="right"
        >
          <el-form-item label="名称" prop="name">
            <el-input
              v-model="form.name"
              placeholder="请输入资源规格名称"
              maxlength="64"
              show-word-limit
            />
          </el-form-item>

          <el-form-item label="描述" prop="description">
            <el-input
              v-model="form.description"
              type="textarea"
              :rows="3"
              placeholder="请输入资源规格描述（可选）"
            />
          </el-form-item>

          <el-form-item label="是否公开" prop="is_public">
            <el-switch v-model="form.is_public" />
            <span class="form-hint">{{ form.is_public ? '公开：所有项目可见' : '私有：仅本项目可见' }}</span>
          </el-form-item>

          <el-form-item label="最小量子比特数" prop="min_qubits">
            <el-input-number
              v-model="form.min_qubits"
              :min="0"
              :step="1"
              controls-position="right"
              placeholder="最小量子比特数（可选）"
            />
          </el-form-item>

          <el-form-item label="最大量子比特数" prop="max_qubits">
            <el-input-number
              v-model="form.max_qubits"
              :min="0"
              :step="1"
              controls-position="right"
              placeholder="最大量子比特数（可选）"
            />
          </el-form-item>

          <el-form-item label="单比特门保真度" prop="gate_fidelity_1q_min">
            <el-input-number
              v-model="form.gate_fidelity_1q_min"
              :min="0"
              :max="1"
              :step="0.0001"
              :precision="6"
              controls-position="right"
              placeholder="0 ~ 1（可选）"
            />
          </el-form-item>

          <el-form-item label="双比特门保真度" prop="gate_fidelity_2q_min">
            <el-input-number
              v-model="form.gate_fidelity_2q_min"
              :min="0"
              :max="1"
              :step="0.0001"
              :precision="6"
              controls-position="right"
              placeholder="0 ~ 1（可选）"
            />
          </el-form-item>

          <el-form-item label="设备组" prop="device_groups">
            <el-select
              v-model="form.device_groups"
              multiple
              filterable
              placeholder="请选择设备组（至少一个）"
              style="width: 100%"
              :loading="deviceGroupLoading"
            >
              <el-option
                v-for="group in deviceGroupOptions"
                :key="group.id"
                :label="deviceGroupLabel(group)"
                :value="group.id"
              >
                <el-tooltip
                  placement="right"
                  :show-after="200"
                  raw-content
                  :content="deviceGroupTooltipHtml(group)"
                  popper-class="device-option-tooltip"
                  :disabled="!group.description"
                >
                  <div class="device-group-option-row">
                    <span class="group-name">{{ group.name }}</span>
                    <span v-if="group.description" class="group-desc">({{ group.description }})</span>
                  </div>
                </el-tooltip>
              </el-option>
            </el-select>
          </el-form-item>

          <el-form-item label="项目ID" prop="project_id">
            <el-input
              v-model="form.project_id"
              placeholder="留空则使用当前用户所属项目"
            />
          </el-form-item>

          <el-form-item label="额外属性">
            <div class="extra-properties">
              <div
                v-for="(item, index) in extraPropertiesList"
                :key="index"
                class="extra-property-row"
              >
                <el-input
                  v-model="item.key"
                  placeholder="属性名"
                  class="extra-key-input"
                  @input="updateExtraProperties"
                />
                <el-input
                  v-model="item.value"
                  placeholder="属性值"
                  class="extra-value-input"
                  @input="updateExtraProperties"
                />
                <el-button
                  type="danger"
                  link
                  @click="removeExtraProperty(index)"
                >
                  删除
                </el-button>
              </div>
              <el-button type="primary" link @click="addExtraProperty">
                + 添加属性
              </el-button>
            </div>
          </el-form-item>

          <el-form-item>
            <el-button
              type="primary"
              :loading="submitting"
              @click="handleSubmit"
            >
              创建
            </el-button>
            <el-button @click="handleCancel">取消</el-button>
          </el-form-item>
        </el-form>
      </el-card>
    </div>
  </div>
</template>

<script>
import { createFlavor } from '@/api/flavor'
import { getDeviceGroups } from '@/api/device'

export default {
  name: 'FlavorCreate',
  data() {
    const validateQubitsRange = (rule, value, callback) => {
      if (
        value !== null &&
        value !== undefined &&
        this.form.max_qubits !== null &&
        this.form.max_qubits !== undefined &&
        value > this.form.max_qubits
      ) {
        callback(new Error('最小量子比特数不能大于最大量子比特数'))
      } else {
        callback()
      }
    }

    return {
      formRef: null,
      submitting: false,
      deviceGroupLoading: false,
      deviceGroupOptions: [],
      form: {
        name: '',
        description: '',
        is_public: true,
        min_qubits: null,
        max_qubits: null,
        gate_fidelity_1q_min: null,
        gate_fidelity_2q_min: null,
        device_groups: [],
        project_id: ''
      },
      extraPropertiesList: [],
      rules: {
        name: [
          { required: true, message: '请输入资源规格名称', trigger: 'blur' },
          { min: 1, max: 64, message: '名称长度在 1 到 64 个字符', trigger: 'blur' }
        ],
        min_qubits: [
          { type: 'number', min: 0, message: '最小量子比特数不能小于 0', trigger: 'blur' },
          { validator: validateQubitsRange, trigger: 'blur' }
        ],
        max_qubits: [
          { type: 'number', min: 0, message: '最大量子比特数不能小于 0', trigger: 'blur' }
        ],
        gate_fidelity_1q_min: [
          { type: 'number', min: 0, max: 1, message: '保真度范围为 0 ~ 1', trigger: 'blur' }
        ],
        gate_fidelity_2q_min: [
          { type: 'number', min: 0, max: 1, message: '保真度范围为 0 ~ 1', trigger: 'blur' }
        ],
        device_groups: [
          {
            required: true,
            type: 'array',
            message: '请至少选择一个设备组',
            trigger: 'change'
          }
        ]
      }
    }
  },

  created() {
    this.fetchDeviceGroups()
  },

  methods: {
    async fetchDeviceGroups() {
      this.deviceGroupLoading = true
      try {
        const response = await getDeviceGroups()
        if (!response.error) {
          const groups = response.result
          this.deviceGroupOptions = []
          // keep the description so the option label and tooltip can
          // render "name (description)"; matches the resource spec
          // dropdown on the job submit page
          if (Array.isArray(groups)) {
            this.deviceGroupOptions = groups.map(g => ({
              id: g.id,
              name: g.name,
              description: g.description || ''
            }))
          } else if (groups && typeof groups === 'object') {
            for (const groupId in groups) {
              const g = groups[groupId]
              this.deviceGroupOptions.push({
                id: g.id,
                name: g.name,
                description: g.description || ''
              })
            }
          }
        } else {
          this.$message.error(`获取设备组列表失败：${response.message || '未知错误'}`)
        }
      } catch (error) {
        console.error('获取设备组列表失败:', error)
        this.$message.error('获取设备组列表失败，请检查网络连接')
      } finally {
        this.deviceGroupLoading = false
      }
    },

    addExtraProperty() {
      this.extraPropertiesList.push({ key: '', value: '' })
    },

    removeExtraProperty(index) {
      this.extraPropertiesList.splice(index, 1)
      this.updateExtraProperties()
    },

    updateExtraProperties() {
      // placeholder: extra_properties is built from list on submit
    },

    // label shown in the device-group dropdown: "name (description)" when
    // a description exists, otherwise just the name; matches the resource
    // spec dropdown on the job submit page
    deviceGroupLabel(group) {
      const desc = (group && group.description) || ''
      return desc ? `${group.name} (${desc})` : (group ? group.name : '')
    },

    // Build the HTML string used as the el-tooltip content for a device
    // group option; mirrors the flavor dropdown on the job submit page
    deviceGroupTooltipHtml(group) {
      if (!group || !group.description) return ''
      const rows = [
        ['名称', group.name],
        ['描述', group.description]
      ]
      const rowStyle = 'display:flex;align-items:flex-start;gap:8px;line-height:1.5;'
      const labelStyle = 'font-weight:600;opacity:0.85;min-width:56px;display:inline-block;'
      const rowsHtml = rows.map(([label, value]) =>
        `<div style="${rowStyle}"><span style="${labelStyle}">${label}:</span><span>${value}</span></div>`
      ).join('')
      return `<div style="display:flex;flex-direction:column;gap:4px;font-size:12px;max-width:380px;word-break:break-all;">${rowsHtml}</div>`
    },

    buildExtraProperties() {
      const result = {}
      for (const item of this.extraPropertiesList) {
        if (item.key && item.key.trim()) {
          result[item.key.trim()] = item.value
        }
      }
      return Object.keys(result).length > 0 ? result : null
    },

    async handleSubmit() {
      try {
        await this.$refs.formRef.validate()
      } catch {
        return
      }

      this.submitting = true
      try {
        const payload = {
          name: this.form.name,
          description: this.form.description || null,
          is_public: this.form.is_public,
          min_qubits: this.form.min_qubits,
          max_qubits: this.form.max_qubits,
          gate_fidelity_1q_min: this.form.gate_fidelity_1q_min,
          gate_fidelity_2q_min: this.form.gate_fidelity_2q_min,
          device_groups: this.form.device_groups
        }

        if (this.form.project_id) {
          payload.project_id = this.form.project_id
        }

        const extraProperties = this.buildExtraProperties()
        if (extraProperties) {
          payload.extra_properties = extraProperties
        }

        const response = await createFlavor(payload)
        if (!response.error) {
          this.$message.success('资源规格创建成功')
          this.$router.push({ name: 'flavorTree' })
        } else {
          this.$message.error(`创建资源规格失败：${response.message || '未知错误'}`)
        }
      } catch (error) {
        console.error('创建资源规格失败:', error)
        this.$message.error('创建资源规格失败，请检查网络连接')
      } finally {
        this.submitting = false
      }
    },

    handleCancel() {
      this.$router.push({ name: 'flavorTree' })
    }
  }
}
</script>

<style scoped>
.flavor-create-container {
  display: flex;
  flex-direction: column;
  background: var(--el-fill-color-light);
  padding: 20px;
  box-sizing: border-box;
}

.header {
  margin: 0;
}

.form-container {
  flex: 1;
  overflow: auto;
}

.create-card {
  max-width: 800px;
  margin: 0 auto;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.05);
  border-radius: 8px;
}

.form-hint {
  margin-left: 12px;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.extra-properties {
  width: 100%;
}

.extra-property-row {
  display: flex;
  align-items: center;
  margin-bottom: 10px;
  gap: 10px;
}

.extra-key-input {
  flex: 1;
}

.extra-value-input {
  flex: 2;
}

:deep(.el-form-item__label) {
  font-weight: 500;
}

/* device group option row -- mirrors the resource spec dropdown on the
   job submit page */
.device-group-option-row {
  display: flex;
  align-items: center;
  gap: 6px;
}

.device-group-option-row .group-desc {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}
</style>
