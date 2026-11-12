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
  <el-form-item :prop="formProp" class="advanced-params-editor">
    <template #label>
      <div class="params-label">
        <span class="params-label-title">{{ displayLabel }}</span>
        <div class="params-label-actions">
          <span class="configured-count">已配置 {{ configuredCount }} 项</span>
          <el-button
            type="primary"
            link
            size="small"
            :loading="loadingSchemas"
            @click.stop.prevent="openEditor"
          >
            修改参数
          </el-button>
        </div>
      </div>
    </template>

    <el-table
      :data="previewRows"
      :height="previewHeight"
      :show-header="false"
      size="small"
      class="params-preview-table"
      empty-text="暂未配置参数"
    >
      <el-table-column min-width="100" show-overflow-tooltip>
        <template #default="{ row }">
          <span class="preview-path">{{ formatPath(row.path.slice(1)) }}</span>
        </template>
      </el-table-column>
      <el-table-column min-width="120" show-overflow-tooltip>
        <template #default="{ row }">
          <span class="preview-description">{{ row.description || '—' }}</span>
        </template>
      </el-table-column>
      <el-table-column min-width="80" show-overflow-tooltip>
        <template #default="{ row }">
          <span class="preview-value">{{ row.displayValue }}</span>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog
      :model-value="editing"
      :title="`编辑${previewTitle}`"
      width="60%"
      align-center
      draggable
      overflow
      append-to-body
      destroy-on-close
      :close-on-click-modal="false"
      class="advanced-params-dialog"
      @close="onDialogClose"
    >
      <el-alert
        v-for="(message, sectionName) in degradedSections"
        :key="sectionName"
        class="schema-alert"
        type="warning"
        :closable="false"
        show-icon
        :title="`${sectionName}：${message}`"
      />
      <el-alert
        v-if="schemaLoadError"
        class="schema-alert"
        type="warning"
        :closable="false"
        show-icon
        :title="schemaLoadError"
      />

      <div class="editor-columns">
        <div class="form-panel">
          <div class="parameter-selection">
            <template v-if="scopePartition">
              <div class="scope-group">
                <div class="scope-group-title">通用参数</div>
                <schema-form-node
                  v-if="scopePartition.commonKeys.length"
                  :key="`scope-common-${formRevision}`"
                  :schema="scopePartition.common"
                  :path="[scopePartition.section]"
                  :node-value="draft[scopePartition.section]"
                  :errors="errors"
                  root
                  :show-header="false"
                  :show-dynamic-adder="false"
                  @set="setFormValue"
                  @remove="removeFormValue"
                  @add-dynamic="addDynamicValue"
                  @input-error="onInputError"
                />
                <div v-else class="scope-group-empty">暂无通用参数</div>
              </div>
              <div class="scope-group">
                <div class="scope-group-title">专用参数</div>
                <schema-form-node
                  v-if="scopePartition.specificKeys.length"
                  :key="`scope-specific-${formRevision}`"
                  :schema="scopePartition.specific"
                  :path="[scopePartition.section]"
                  :node-value="draft[scopePartition.section]"
                  :errors="errors"
                  root
                  :show-header="false"
                  :exclude-dynamic-keys="scopePartition.commonKeys"
                  @set="setFormValue"
                  @remove="removeFormValue"
                  @add-dynamic="addDynamicValue"
                  @input-error="onInputError"
                />
                <div v-else class="scope-group-empty">暂无专用参数</div>
              </div>
            </template>
            <template v-else>
              <schema-form-node
                v-for="rootSection in effectiveSections"
                :key="`${rootSection}-${formRevision}`"
                :schema="selectedSchemas[rootSection]"
                :path="[rootSection]"
                :node-value="draft[rootSection]"
                :errors="errors"
                root
                @set="setFormValue"
                @remove="removeFormValue"
                @add-dynamic="addDynamicValue"
                @input-error="onInputError"
              />
            </template>
          </div>

          <div class="custom-kv-editor">
            <div class="custom-kv-title">添加自定义键值</div>
            <el-input
              v-model="customPath"
              size="small"
              :placeholder="customPathPlaceholder"
            />
            <el-input
              v-model="customValue"
              type="textarea"
              :rows="2"
              placeholder="JSON 值，如 true、123、{&quot;key&quot;:1}；普通文本按字符串处理"
            />
            <el-button size="small" @click="addCustomValue">添加自定义值</el-button>
            <div class="custom-kv-tip">{{ customPathTip }}</div>
          </div>
        </div>

        <div class="monaco-panel">
          <div class="monaco-title">完整 JSON（失焦后回填左侧表单）</div>
          <monaco-editor
            ref="monaco"
            :value="editorText"
            language="json"
            theme="vs-dark"
            lint-mode="object"
            :model-path="internalModelPath"
            :options="editorOptions"
            :show-status-bar="true"
            @change="onEditorChange"
            @blur="onEditorBlur"
          />
        </div>
      </div>

      <div v-if="errors.length" class="validation-summary">
        <div class="validation-title">存在未通过校验的输入，请修正后再确认应用：</div>
        <div v-for="(error, index) in errors" :key="`${error.key}-${error.keyword}-${index}`" class="validation-error">
          <span class="error-path">{{ error.pathText }}</span>
          <span>{{ error.message }}</span>
        </div>
      </div>
      <template #footer>
        <div class="dialog-footer">
          <el-button size="small" @click="formatEditor">格式化</el-button>
          <el-button size="small" @click="reset">重置</el-button>
          <el-button size="small" @click="close">取消</el-button>
          <el-button size="small" type="primary" @click="confirmApply">确认应用</el-button>
        </div>
      </template>
    </el-dialog>
  </el-form-item>
</template>

<script>
import MonacoEditor from '@/components/MonacoEditor/index.vue'
import SchemaFormNode from './SchemaFormNode.vue'
import { queryVersion } from '@/api/version'
import { normalizeJsonInput } from '@/common/library'
import {
  buildCombinedSchema,
  clearInputErrors,
  compileSchema,
  convertAjvErrors,
  countConfiguredLeaves,
  createDefaultValue,
  deepClone,
  deleteAtPath,
  detectCustomBranches,
  flattenPreviewRows,
  formatPath,
  isPlainObject,
  listInputErrors,
  omitEmptyRoots,
  parseCustomPath,
  parseJsonLiteral,
  partitionSchemaByParameterScope,
  pathKey,
  removeValidationExemptions,
  resolveSchemaPath,
  selectSectionSchemas,
  setAtPath,
  SECTION_LABELS,
  updateInputError
} from '@/utils/jsonSchemaForm'

let editorSequence = 0

export default {
  name: 'AdvancedParamsEditor',
  components: {
    MonacoEditor,
    SchemaFormNode
  },
  props: {
    value: {
      type: Object,
      default: () => ({})
    },
    schemas: {
      type: Object,
      default: () => ({})
    },
    section: {
      type: String,
      default: ''
    },
    label: {
      type: String,
      default: ''
    },
    formProp: {
      type: String,
      default: ''
    },
    previewHeight: {
      type: Number,
      default: 64
    },
    sections: {
      type: Array,
      default: () => [
        'driver_options',
        'transpiler_options',
        'options',
        'qem_options',
        'qec_options',
        'extra_specs'
      ]
    },
    driverName: {
      type: String,
      default: ''
    },
    transpilerName: {
      type: String,
      default: ''
    },
    resolveDynamic: {
      type: Boolean,
      default: true
    },
    modelPath: {
      type: String,
      default: ''
    }
  },
  emits: ['apply', 'editing-change'],
  data() {
    editorSequence += 1
    return {
      localAppliedValue: deepClone(this.value || {}),
      localSchemas: deepClone(this.schemas || {}),
      loadingSchemas: false,
      schemaQueryAttempted: false,
      schemaLoadError: '',
      editing: false,
      openRequestId: 0,
      openSnapshot: {},
      draft: {},
      baselineText: '{}',
      editorText: '{}',
      validationErrors: [],
      inputErrors: {},
      formRevision: 0,
      customBranches: [],
      customPath: '',
      customValue: '',
      internalModelPath: this.modelPath || `advanced-params-${editorSequence}.json`,
      editorOptions: {
        tabSize: 2,
        insertSpaces: true,
        automaticLayout: true,
        scrollBeyondLastLine: false
      }
    }
  },
  computed: {
    schemaSource() {
      return isPlainObject(this.schemas) && Object.keys(this.schemas).length
        ? this.schemas
        : this.localSchemas
    },
    effectiveSections() {
      return this.section ? [this.section] : this.sections
    },
    previewTitle() {
      if (this.effectiveSections.length !== 1) return '参数配置预览'
      const section = this.effectiveSections[0]
      const schema = this.selectedSchemas[section]
      return (schema && schema.alias_name) || SECTION_LABELS[section] || section
    },
    displayLabel() {
      return this.label || this.previewTitle
    },
    customPathPlaceholder() {
      return this.effectiveSections.length === 1
        ? '相对路径，如 server.debug'
        : '完整根路径，如 driver_options.server.debug'
    },
    customPathTip() {
      const suffix = '自定义字段会被保留，但后端是否支持以提交校验为准。'
      return this.effectiveSections.length === 1
        ? `无需输入 ${this.effectiveSections[0]} 根前缀，将自动补充。${suffix}`
        : `多参数组模式仍需输入完整根路径。${suffix}`
    },
    schemaSelection() {
      return selectSectionSchemas(this.schemaSource, this.effectiveSections, {
        driverName: this.driverName,
        transpilerName: this.transpilerName,
        resolveDynamic: this.resolveDynamic
      })
    },
    selectedSchemas() {
      return this.schemaSelection.schemas
    },
    scopePartition() {
      if (this.effectiveSections.length !== 1) return null
      const section = this.effectiveSections[0]
      return partitionSchemaByParameterScope(section, this.selectedSchemas[section])
    },
    degradedSections() {
      return this.schemaSelection.degraded
    },
    validatorState() {
      return compileSchema(buildCombinedSchema(this.selectedSchemas, this.effectiveSections))
    },
    errors() {
      return this.validationErrors.concat(listInputErrors(this.inputErrors))
    },
    hasInputErrors() {
      return Object.keys(this.inputErrors).length > 0
    },
    configuredCount() {
      return countConfiguredLeaves(this.localAppliedValue, this.effectiveSections)
    },
    previewRows() {
      return flattenPreviewRows(this.localAppliedValue, this.selectedSchemas, this.effectiveSections)
        .filter(row => row.configured)
    }
  },
  watch: {
    value: {
      deep: true,
      handler(value) {
        if (!this.editing) this.localAppliedValue = deepClone(value || {})
      }
    },
    schemas: {
      deep: true,
      handler(schemas) {
        if (isPlainObject(schemas) && Object.keys(schemas).length) {
          this.localSchemas = deepClone(schemas)
          this.schemaLoadError = ''
        }
        if (this.editing) this.validateDraft()
      }
    },
    driverName() {
      if (this.editing) this.validateDraft()
    },
    transpilerName() {
      if (this.editing) this.validateDraft()
    },
    resolveDynamic() {
      if (this.editing) this.validateDraft()
    },
    section() {
      if (this.editing) this.validateDraft()
    },
    sections: {
      deep: true,
      handler() {
        if (this.editing) this.validateDraft()
      }
    }
  },
  beforeUnmount() {
    this.openRequestId += 1
    this.clearSchemaMarkers()
  },
  methods: {
    formatPath,
    async ensureSchemas() {
      if (isPlainObject(this.schemaSource) && Object.keys(this.schemaSource).length) return
      if (this.schemaQueryAttempted) return
      this.schemaQueryAttempted = true
      this.loadingSchemas = true
      try {
        const response = await queryVersion()
        const result = response && response.result ? response.result : response
        const schemas = result && result.capabilities && result.capabilities.schemas
        if (isPlainObject(schemas) && Object.keys(schemas).length) {
          this.localSchemas = deepClone(schemas)
        } else {
          this.schemaLoadError = '版本接口未返回 capabilities.schemas，当前按通用对象编辑。'
        }
      } catch (error) {
        this.schemaLoadError = `获取参数 Schema 失败：${error.message || '未知错误'}；当前按通用对象编辑。`
      } finally {
        this.loadingSchemas = false
      }
    },
    async openEditor() {
      if (this.editing) return
      const requestId = ++this.openRequestId
      await this.ensureSchemas()
      if (requestId !== this.openRequestId) return
      this.openSnapshot = deepClone(this.localAppliedValue)
      this.draft = omitEmptyRoots(this.openSnapshot, this.effectiveSections)
      this.baselineText = JSON.stringify(this.draft, null, 2)
      this.editorText = this.baselineText
      this.customPath = ''
      this.customValue = ''
      this.validationErrors = []
      this.inputErrors = {}
      this.formRevision += 1
      this.customBranches = detectCustomBranches(this.draft, this.selectedSchemas, this.effectiveSections)
      this.editing = true
      this.$emit('editing-change', true)
      this.$nextTick(() => {
        this.validateDraft()
        this.clearSchemaMarkers()
      })
    },
    setFormValue(path, value) {
      this.inputErrors = clearInputErrors(this.inputErrors, path)
      try {
        this.commitFormDraft(setAtPath(this.draft, path, value))
      } catch (error) {
        this.$message.warning(error.message)
      }
    },
    removeFormValue(path) {
      this.inputErrors = clearInputErrors(this.inputErrors, path)
      this.commitFormDraft(deleteAtPath(this.draft, path, true))
    },
    onInputError(path, message) {
      this.inputErrors = updateInputError(this.inputErrors, path, message)
    },
    addDynamicValue(parentPath, key) {
      const root = parentPath[0]
      const resolution = resolveSchemaPath(this.selectedSchemas[root], parentPath.slice(1))
      if (!resolution.known || !isPlainObject(resolution.schema.additionalProperties)) {
        this.$message.warning('当前节点不支持动态字段')
        return
      }
      const value = createDefaultValue(resolution.schema.additionalProperties)
      try {
        this.commitFormDraft(setAtPath(this.draft, parentPath.concat(key), value))
      } catch (error) {
        this.$message.warning(error.message)
      }
    },
    resolveCustomInputPath() {
      const rawPath = this.customPath.trim()
      if (this.effectiveSections.length !== 1) return rawPath
      const section = this.effectiveSections[0]
      if (rawPath === section || rawPath.startsWith(`${section}.`)) return rawPath
      return `${section}.${rawPath}`
    },
    addCustomValue() {
      const parsedPath = parseCustomPath(
        this.resolveCustomInputPath(),
        this.draft,
        this.selectedSchemas,
        this.effectiveSections
      )
      if (!parsedPath.ok) {
        this.$message.warning(parsedPath.message)
        return
      }
      const parsedValue = parseJsonLiteral(this.customValue)
      try {
        this.inputErrors = clearInputErrors(this.inputErrors, parsedPath.path)
        this.commitFormDraft(setAtPath(this.draft, parsedPath.path, parsedValue.value))
        this.customPath = ''
        this.customValue = ''
      } catch (error) {
        this.$message.warning(error.message)
      }
    },
    commitFormDraft(draft) {
      this.draft = omitEmptyRoots(draft, this.effectiveSections)
      this.editorText = JSON.stringify(this.draft, null, 2)
      this.validateDraft()
    },
    validateCandidate(candidate) {
      const normalized = omitEmptyRoots(candidate, this.effectiveSections)
      const errors = []
      if (!isPlainObject(normalized)) {
        errors.push(this.makeError([], 'JSON 根节点必须是普通对象', 'root-type'))
        return { valid: false, errors, normalized, customBranches: [] }
      }

      Object.keys(normalized).forEach(root => {
        if (!this.effectiveSections.includes(root)) {
          errors.push(this.makeError([root], '根节点不在当前 sections 白名单中', 'root-whitelist'))
        }
      })

      const customBranches = detectCustomBranches(normalized, this.selectedSchemas, this.effectiveSections)
      const validationCopy = removeValidationExemptions(normalized, customBranches)
      const { validate, error } = this.validatorState
      if (error) {
        errors.push(this.makeError([], `Schema 编译失败：${error}`, 'schema-compile'))
      } else if (!validate(validationCopy)) {
        errors.push(...convertAjvErrors(validate.errors))
      }
      return { valid: errors.length === 0, errors, normalized, customBranches }
    },
    makeError(path, message, keyword) {
      return {
        path,
        key: pathKey(path),
        pathText: path.length ? formatPath(path) : '根对象',
        keyword,
        message
      }
    },
    validateDraft() {
      const result = this.validateCandidate(this.draft)
      this.customBranches = result.customBranches
      this.setErrors(result.errors)
      return { ...result, valid: result.valid && !this.hasInputErrors }
    },
    onEditorChange(text) {
      this.editorText = text
    },
    onEditorBlur(text) {
      this.processEditorText(text, false)
    },
    readEditorText() {
      const editor = this.$refs.monaco
      if (editor && typeof editor.getValue === 'function') return editor.getValue()
      return this.editorText
    },
    processEditorText(text, apply) {
      if (apply && this.hasInputErrors) return null
      const normalizedText = normalizeJsonInput(text)
      this.editorText = normalizedText
      let parsed
      try {
        parsed = JSON.parse(normalizedText)
      } catch (error) {
        this.setErrors([this.makeError([], `JSON 格式错误：${error.message}`, 'json-syntax')])
        return null
      }
      if (!isPlainObject(parsed)) {
        this.setErrors([this.makeError([], 'JSON 根节点必须是普通对象', 'root-type')])
        return null
      }

      const result = this.validateCandidate(parsed)
      if (!result.valid) {
        this.setErrors(result.errors)
        return null
      }

      this.inputErrors = {}
      this.formRevision += 1
      this.draft = deepClone(result.normalized)
      this.customBranches = result.customBranches
      this.editorText = JSON.stringify(this.draft, null, 2)
      this.setErrors([])
      if (apply) {
        const applied = deepClone(this.draft)
        this.localAppliedValue = deepClone(applied)
        this.openSnapshot = deepClone(applied)
        this.baselineText = JSON.stringify(applied, null, 2)
        this.$emit('apply', applied)
        this.editing = false
        this.clearSchemaMarkers()
        this.$emit('editing-change', false)
      }
      return deepClone(this.draft)
    },
    confirmApply() {
      if (this.hasInputErrors) {
        this.$message.warning('请先修正左侧 JSON 输入错误')
        return
      }
      const text = this.readEditorText()
      this.processEditorText(text, true)
    },
    formatEditor() {
      const normalizedText = normalizeJsonInput(this.readEditorText())
      this.editorText = normalizedText
      try {
        const parsed = JSON.parse(normalizedText)
        this.editorText = JSON.stringify(parsed, null, 2)
        this.processEditorText(this.editorText, false)
      } catch (error) {
        this.setErrors([this.makeError([], `JSON 格式错误：${error.message}`, 'json-syntax')])
      }
    },
    reset() {
      if (!this.editing) return
      this.draft = omitEmptyRoots(this.openSnapshot, this.effectiveSections)
      this.baselineText = JSON.stringify(this.draft, null, 2)
      this.editorText = this.baselineText
      this.customPath = ''
      this.customValue = ''
      this.inputErrors = {}
      this.formRevision += 1
      this.validateDraft()
    },
    close() {
      this.openRequestId += 1
      if (!this.editing) return
      this.reset()
      this.editing = false
      this.$emit('editing-change', false)
      this.clearSchemaMarkers()
    },
    onDialogClose() {
      if (this.editing) this.close()
    },
    hasPendingChanges() {
      return this.editing && (this.editorText !== this.baselineText || this.hasInputErrors)
    },
    setErrors(errors) {
      this.validationErrors = errors
      this.$nextTick(() => {
        if (!this.editing) return
        const editor = this.$refs.monaco
        if (!editor || typeof editor.setSchemaMarkers !== 'function') return
        editor.setSchemaMarkers(this.errorsToMarkers(this.editorText, errors))
      })
    },
    clearSchemaMarkers() {
      const editor = this.$refs.monaco
      if (editor && typeof editor.clearSchemaMarkers === 'function') {
        editor.clearSchemaMarkers()
      }
    },
    errorsToMarkers(text, errors) {
      return errors.map(error => {
        const position = this.findErrorPosition(text, error.path)
        return {
          severity: 'error',
          message: `${error.pathText}：${error.message}`,
          startLineNumber: position.line,
          startColumn: position.column,
          endLineNumber: position.line,
          endColumn: position.column + 1
        }
      })
    },
    findErrorPosition(text, path) {
      for (let index = path.length - 1; index >= 0; index -= 1) {
        const needle = JSON.stringify(path[index])
        const offset = text.indexOf(needle)
        if (offset >= 0) return this.offsetToPosition(text, offset)
      }
      return { line: 1, column: 1 }
    },
    offsetToPosition(text, offset) {
      const prefix = text.slice(0, offset)
      const lines = prefix.split('\n')
      return { line: lines.length, column: lines[lines.length - 1].length + 1 }
    }
  }
}
</script>

<style scoped>
.advanced-params-editor {
  width: 100%;
}

.params-label {
  display: flex;
  flex-direction: column;
  gap: 4px;
  line-height: 1.3;
}

.params-label-title {
  font-weight: 700;
}

.params-label-actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 2px;
}

.params-label-actions .el-button {
  margin-left: 0;
}

.configured-count {
  color: var(--el-text-color-secondary);
  font-size: 12px;
  white-space: nowrap;
}

.params-preview-table {
  width: 100%;
  overflow: hidden;
  border: 1px solid var(--el-border-color);
  border-radius: 4px;
  font-size: 12px;
  line-height: 1.25;
}

.params-preview-table :deep(.el-table__empty-text) {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.params-preview-table :deep(.el-table__cell) {
  padding: 2px 6px;
}

.params-preview-table :deep(.el-table__row) {
  line-height: 1.25;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

:global(.advanced-params-dialog) {
  display: flex;
  flex-direction: column;
  min-width: 720px;
  min-height: 420px;
  max-width: 96vw;
  max-height: 92vh;
  margin-bottom: 0;
  overflow: hidden;
  resize: both;
}

:global(.advanced-params-dialog .el-dialog__header),
:global(.advanced-params-dialog .el-dialog__footer) {
  flex-shrink: 0;
}

:global(.advanced-params-dialog .el-dialog__body) {
  flex: 1 1 auto;
  min-height: 0;
  max-height: none;
  overflow-y: auto;
}

.preview-description {
  line-height: 1.25;
  word-break: break-all;
}

.preview-path {
  color: var(--el-text-color-primary);
  font-family: Consolas, 'Courier New', monospace;
  font-size: 12px;
  word-break: break-all;
}

.preview-value {
  display: block;
  font-family: Consolas, 'Courier New', monospace;
  line-height: 1.25;
  white-space: pre-wrap;
  word-break: break-all;
}

.schema-alert {
  margin-bottom: 8px;
}

.editor-columns {
  --editor-panel-height: 650px;
  display: grid;
  grid-template-columns: minmax(400px, 1fr) minmax(320px, 1fr);
  gap: 16px;
  align-items: stretch;
}

.form-panel {
  display: flex;
  flex-direction: column;
  height: var(--editor-panel-height);
  min-width: 0;
  min-height: 0;
  overflow: hidden;
}

.parameter-selection {
  flex: 1 1 auto;
  min-height: 0;
  padding-right: 8px;
  overflow-y: auto;
}

.scope-group + .scope-group {
  margin-top: 16px;
}

.scope-group-title {
  margin-bottom: 8px;
  padding-bottom: 6px;
  border-bottom: 1px solid var(--el-border-color);
  font-weight: 600;
}

.scope-group-empty {
  padding: 8px 0;
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.monaco-panel {
  display: flex;
  flex-direction: column;
  height: var(--editor-panel-height);
  min-width: 0;
  min-height: 0;
  overflow: hidden;
  border: 1px solid var(--el-border-color);
  border-radius: 4px;
}

.monaco-title {
  flex-shrink: 0;
  height: 32px;
  padding: 7px 10px;
  color: var(--el-text-color-secondary);
  background: var(--el-fill-color-light);
  border-bottom: 1px solid var(--el-border-color);
  font-size: 12px;
}

.monaco-panel :deep(.monaco-editor-wrapper) {
  flex: 1 1 auto;
  height: auto;
  min-height: 0;
}

.custom-kv-editor {
  display: grid;
  flex-shrink: 0;
  gap: 8px;
  margin-top: 12px;
  padding: 12px;
  background: var(--el-fill-color-light);
  border: 1px dashed var(--el-border-color);
  border-radius: 4px;
}

.custom-kv-title {
  font-weight: 600;
}

.custom-kv-tip {
  color: var(--el-color-warning);
  font-size: 12px;
  line-height: 1.5;
}

.validation-summary {
  margin-top: 12px;
  padding: 10px 12px;
  color: var(--el-color-danger);
  background: var(--el-color-danger-light-9);
  border-radius: 4px;
  font-size: 12px;
}

.validation-title {
  margin-bottom: 6px;
  font-weight: 600;
}

.validation-error {
  display: flex;
  gap: 8px;
  padding: 2px 0;
}

.error-path {
  flex-shrink: 0;
  font-family: Consolas, 'Courier New', monospace;
}

@media (max-width: 1200px) {
  .editor-columns {
    grid-template-columns: minmax(0, 1fr);
    --editor-panel-height: 520px;
  }
}
</style>
