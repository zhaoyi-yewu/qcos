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
  <div class="schema-form-node">
    <el-collapse
      v-if="isObjectNode"
      v-model="openNames"
      class="object-collapse"
      :class="{ 'header-hidden': !showHeader }"
    >
      <el-collapse-item :name="collapseName">
        <template #title>
          <div class="object-title">
            <el-checkbox
              v-if="!root"
              :model-value="enabled"
              :aria-label="`启用 ${displayName}`"
              @click.stop
              @change="toggleEnabled"
            />
            <div class="object-heading">
              <span class="field-name">{{ displayName }}</span>
              <span class="field-key">{{ pathText }}</span>
              <span v-if="required" class="required-tag">必填</span>
              <span v-if="custom" class="custom-tag">自定义</span>
            </div>
            <el-checkbox
              v-if="supportsObjectNull"
              :model-value="nodeValue === null"
              :disabled="!enabled"
              class="null-checkbox"
              @click.stop
              @change="toggleNull"
            >null</el-checkbox>
            <el-tooltip placement="top" :show-after="200">
              <template #content>
                <div class="tooltip-content">
                  <div>{{ description || '暂无描述' }}</div>
                  <div v-if="schemaConstraints">提交约束：{{ schemaConstraints }}</div>
                  <div v-if="runtimeConstraints">运行时约束（仅提示）：{{ runtimeConstraints }}</div>
                </div>
              </template>
              <span class="description-trigger" @click.stop>说明</span>
            </el-tooltip>
            <el-button
              v-if="dynamic"
              text
              type="danger"
              size="small"
              @click.stop="$emit('remove', path)"
            >删除</el-button>
          </div>
        </template>

        <div v-if="custom" class="custom-notice">后端是否支持以提交校验为准。</div>
        <div v-for="error in ownErrors" :key="`${error.keyword}-${error.message}`" class="field-error">
          {{ error.message }}
        </div>
        <div v-if="enabled && nodeValue !== null" class="object-children">
          <schema-form-node
            v-for="key in propertyNames"
            :key="`property-${key}`"
            :schema="schema.properties[key]"
            :path="path.concat(key)"
            :node-value="childValue(key)"
            :required="requiredNames.includes(key)"
            :errors="errors"
            @set="forwardSet"
            @remove="forwardRemove"
            @add-dynamic="forwardAddDynamic"
            @input-error="forwardInputError"
          />
          <schema-form-node
            v-for="key in dynamicNames"
            :key="`dynamic-${key}`"
            :schema="schema.additionalProperties"
            :path="path.concat(key)"
            :node-value="childValue(key)"
            :errors="errors"
            dynamic
            @set="forwardSet"
            @remove="forwardRemove"
            @add-dynamic="forwardAddDynamic"
            @input-error="forwardInputError"
          />
          <schema-form-node
            v-for="key in unknownNames"
            :key="`custom-${key}`"
            :schema="unknownSchema(key)"
            :path="path.concat(key)"
            :node-value="childValue(key)"
            :errors="errors"
            custom
            @set="forwardSet"
            @remove="forwardRemove"
            @add-dynamic="forwardAddDynamic"
            @input-error="forwardInputError"
          />
        </div>

        <div v-if="enabled && nodeValue !== null && hasDynamicSchema && showDynamicAdder" class="dynamic-key-adder">
          <el-input
            v-model="dynamicKey"
            size="small"
            placeholder="新增动态 Key"
            @keyup.enter="addDynamicKey"
          />
          <el-button size="small" @click="addDynamicKey">添加动态字段</el-button>
        </div>
      </el-collapse-item>
    </el-collapse>

    <div v-else class="leaf-node" :class="{ 'has-error': ownErrors.length }">
      <div class="leaf-main">
        <el-checkbox
          :model-value="enabled"
          :aria-label="`启用 ${displayName}`"
          @change="toggleEnabled"
        />
        <div class="leaf-label">
          <div>
            <span class="field-name">{{ displayName }}</span>
            <span v-if="required" class="required-tag">必填</span>
            <span v-if="custom" class="custom-tag">自定义</span>
          </div>
          <div class="field-key">{{ pathText }}</div>
        </div>
        <span class="type-label">{{ typeLabel }}</span>
        <div class="field-control">
          <el-select
            v-if="controlType === 'enum'"
            :model-value="nodeValue"
            size="small"
            :disabled="!enabled"
            @change="setValue"
          >
            <el-option
              v-for="option in enumOptions"
              :key="JSON.stringify(option)"
              :label="optionLabel(option)"
              :value="option"
            />
          </el-select>
          <el-switch
            v-else-if="controlType === 'boolean'"
            :model-value="nodeValue"
            :disabled="!enabled || (nullable && nodeValue === null)"
            @change="setValue"
          />
          <el-input-number
            v-else-if="controlType === 'integer' || controlType === 'number'"
            :model-value="nodeValue"
            size="small"
            controls-position="right"
            :disabled="!enabled || (nullable && nodeValue === null)"
            :precision="controlType === 'integer' ? 0 : undefined"
            :min="numberLimits.min"
            :max="numberLimits.max"
            :step="numberLimits.step"
            @update:model-value="setValue"
          />
          <el-input
            v-else-if="controlType === 'string'"
            :model-value="nodeValue"
            size="small"
            :disabled="!enabled || (nullable && nodeValue === null)"
            :type="sensitive ? 'password' : 'text'"
            :show-password="sensitive"
            :maxlength="stringMaxLength"
            :show-word-limit="stringMaxLength !== undefined"
            @update:model-value="setValue"
          />
          <el-input
            v-else
            :model-value="jsonDraft"
            type="textarea"
            :rows="3"
            resize="vertical"
            :disabled="!enabled"
            placeholder="请输入 JSON 值"
            @focus="jsonFocused = true"
            @update:model-value="updateJsonValue"
            @blur="finishJsonEdit"
          />
        </div>
        <el-checkbox
          v-if="supportsDirectNull"
          :model-value="nodeValue === null"
          :disabled="!enabled"
          class="null-checkbox"
          @change="toggleNull"
        >null</el-checkbox>
        <el-tooltip placement="top" :show-after="200">
          <template #content>
            <div class="tooltip-content">
              <div>{{ description || '暂无描述' }}</div>
              <div v-if="schemaConstraints">提交约束：{{ schemaConstraints }}</div>
              <div v-if="runtimeConstraints">运行时约束（仅提示）：{{ runtimeConstraints }}</div>
            </div>
          </template>
          <span class="description-trigger">说明</span>
        </el-tooltip>
        <el-button
          v-if="dynamic"
          text
          type="danger"
          size="small"
          @click="$emit('remove', path)"
        >删除</el-button>
      </div>
      <div v-if="custom" class="custom-notice leaf-notice">后端是否支持以提交校验为准。</div>
      <div v-for="error in ownErrors" :key="`${error.keyword}-${error.message}`" class="field-error">
        {{ error.message }}
      </div>
    </div>
  </div>
</template>

<script>
import {
  createDefaultValue,
  formatConstraints,
  formatPath,
  getSchemaTypes,
  isObjectSchema,
  isPlainObject,
  isSensitiveField,
  parseStrictJsonValue,
  pathKey,
  shouldUseJsonInput
} from '@/utils/jsonSchemaForm'

export default {
  name: 'SchemaFormNode',
  props: {
    schema: {
      type: Object,
      required: true
    },
    path: {
      type: Array,
      required: true
    },
    nodeValue: {
      type: [String, Number, Boolean, Object, Array],
      default: undefined
    },
    required: {
      type: Boolean,
      default: false
    },
    root: {
      type: Boolean,
      default: false
    },
    dynamic: {
      type: Boolean,
      default: false
    },
    custom: {
      type: Boolean,
      default: false
    },
    showHeader: {
      type: Boolean,
      default: true
    },
    showDynamicAdder: {
      type: Boolean,
      default: true
    },
    excludeDynamicKeys: {
      type: Array,
      default: () => []
    },
    errors: {
      type: Array,
      default: () => []
    }
  },
  emits: ['set', 'remove', 'add-dynamic', 'input-error'],
  data() {
    return {
      openNames: [pathKey(this.path)],
      dynamicKey: '',
      jsonDraft: '',
      jsonFocused: false
    }
  },
  computed: {
    enabled() {
      return this.root || this.nodeValue !== undefined
    },
    collapseName() {
      return pathKey(this.path)
    },
    pathText() {
      return formatPath(this.path)
    },
    displayName() {
      return this.schema.alias_name || this.path[this.path.length - 1]
    },
    description() {
      return this.schema.description || ''
    },
    fieldConstraints() {
      return isPlainObject(this.schema.field_constraints) ? this.schema.field_constraints : {}
    },
    schemaConstraints() {
      return formatConstraints(this.fieldConstraints.schema)
    },
    runtimeConstraints() {
      return formatConstraints(this.fieldConstraints.runtime)
    },
    schemaTypes() {
      return getSchemaTypes(this.schema)
    },
    nullable() {
      return this.schemaTypes.includes('null')
    },
    isObjectNode() {
      return isObjectSchema(this.schema) && !this.usesJsonInput
    },
    usesJsonInput() {
      return shouldUseJsonInput(this.schema)
    },
    supportsObjectNull() {
      return this.isObjectNode && this.nullable
    },
    controlType() {
      if (Array.isArray(this.schema.enum) && this.schema.enum.length) return 'enum'
      if (this.usesJsonInput) return 'json'
      const types = this.schemaTypes.filter(type => type !== 'null')
      if (types.length === 1) return types[0]
      if (typeof this.nodeValue === 'string') return 'string'
      if (typeof this.nodeValue === 'boolean') return 'boolean'
      if (typeof this.nodeValue === 'number') {
        return Number.isInteger(this.nodeValue) ? 'integer' : 'number'
      }
      return 'json'
    },
    typeLabel() {
      return this.schemaTypes.length ? this.schemaTypes.join(' | ') : this.controlType
    },
    propertyNames() {
      return isPlainObject(this.schema.properties) ? Object.keys(this.schema.properties) : []
    },
    requiredNames() {
      return Array.isArray(this.schema.required) ? this.schema.required : []
    },
    hasDynamicSchema() {
      return isPlainObject(this.schema.additionalProperties)
    },
    dynamicNames() {
      // When the dynamic adder is hidden (common scope group), dynamic and
      // custom keys are rendered only by the specific group to avoid duplicates.
      // excludeDynamicKeys filters keys owned by the sibling scope group so
      // they are never re-rendered (or coerced) as dynamic fields here.
      if (!this.showDynamicAdder) return []
      if (!this.hasDynamicSchema || !isPlainObject(this.nodeValue)) return []
      return Object.keys(this.nodeValue).filter(key =>
        !this.propertyNames.includes(key) && !this.excludeDynamicKeys.includes(key))
    },
    unknownNames() {
      if (!this.showDynamicAdder) return []
      if (this.hasDynamicSchema || !isPlainObject(this.nodeValue)) return []
      return Object.keys(this.nodeValue).filter(key =>
        !this.propertyNames.includes(key) && !this.excludeDynamicKeys.includes(key))
    },
    ownErrors() {
      const key = pathKey(this.path)
      return this.errors.filter(error => error.key === key)
    },
    enumOptions() {
      if (Array.isArray(this.schema.enum)) return this.schema.enum
      const constraints = this.fieldConstraints.schema
      return constraints && Array.isArray(constraints.enum) ? constraints.enum : []
    },
    controlConstraints() {
      return isPlainObject(this.fieldConstraints.schema) ? this.fieldConstraints.schema : {}
    },
    numberLimits() {
      const constraints = this.controlConstraints
      const integer = this.controlType === 'integer'
      let min = constraints.minimum
      let max = constraints.maximum
      if (constraints.exclusive_minimum !== undefined) {
        min = integer ? constraints.exclusive_minimum + 1 : constraints.exclusive_minimum
      }
      if (constraints.exclusive_maximum !== undefined) {
        max = integer ? constraints.exclusive_maximum - 1 : constraints.exclusive_maximum
      }
      return {
        min,
        max,
        step: constraints.multiple_of !== undefined
          ? constraints.multiple_of
          : (integer ? 1 : undefined)
      }
    },
    stringMaxLength() {
      return this.controlConstraints.max_length
    },
    supportsDirectNull() {
      return this.nullable && !this.usesJsonInput && this.controlType !== 'enum'
    },
    sensitive() {
      return isSensitiveField(this.path, this.schema)
    },
    serializedValue() {
      return this.nodeValue === undefined ? '' : JSON.stringify(this.nodeValue, null, 2)
    }
  },
  watch: {
    serializedValue: {
      immediate: true,
      handler(value) {
        if (!this.jsonFocused) this.jsonDraft = value
      }
    }
  },
  methods: {
    childValue(key) {
      return isPlainObject(this.nodeValue) ? this.nodeValue[key] : undefined
    },
    setValue(value) {
      this.$emit('set', this.path, value)
    },
    toggleEnabled(enabled) {
      if (enabled) {
        this.$emit('set', this.path, createDefaultValue(this.schema))
      } else {
        this.$emit('remove', this.path)
      }
    },
    toggleNull(isNull) {
      if (isNull) {
        this.$emit('set', this.path, null)
        return
      }
      const type = this.schemaTypes.find(item => item !== 'null')
      const defaults = {
        boolean: false,
        integer: 0,
        number: 0,
        string: '',
        object: {}
      }
      this.$emit('set', this.path, defaults[type])
    },
    updateJsonValue(text) {
      this.jsonDraft = text
      const result = parseStrictJsonValue(text)
      if (!result.ok) {
        this.$emit('input-error', this.path, result.message)
        return
      }
      this.$emit('input-error', this.path, '')
      this.$emit('set', this.path, result.value)
    },
    finishJsonEdit() {
      this.jsonFocused = false
      const result = parseStrictJsonValue(this.jsonDraft)
      if (!result.ok) {
        this.$emit('input-error', this.path, result.message)
        return
      }
      this.jsonDraft = JSON.stringify(result.value, null, 2)
      this.$emit('input-error', this.path, '')
      this.$emit('set', this.path, result.value)
    },
    optionLabel(option) {
      if (option === null) return 'null（空）'
      return typeof option === 'string' ? option : JSON.stringify(option)
    },
    unknownSchema(key) {
      const value = this.nodeValue[key]
      const schema = {
        alias_name: key,
        description: '自定义字段，后端是否支持以提交校验为准。',
        field_constraints: { schema: {}, runtime: {}}
      }
      if (isPlainObject(value)) {
        schema.type = 'object'
        schema.properties = {}
        Object.keys(value).forEach(childKey => {
          Object.defineProperty(schema.properties, childKey, {
            value: { type: this.inferType(value[childKey]) },
            enumerable: true,
            configurable: true,
            writable: true
          })
        })
      } else if (Array.isArray(value)) {
        schema.type = 'array'
      } else if (value === null) {
        schema.type = 'null'
      } else {
        schema.type = typeof value
      }
      return schema
    },
    inferType(value) {
      if (value === null) return 'null'
      if (Array.isArray(value)) return 'array'
      return typeof value
    },
    addDynamicKey() {
      const key = this.dynamicKey.trim()
      if (!key) return
      if (isPlainObject(this.nodeValue) && Object.prototype.hasOwnProperty.call(this.nodeValue, key)) {
        this.$message.warning('动态 Key 已存在')
        return
      }
      this.$emit('add-dynamic', this.path, key)
      this.dynamicKey = ''
    },
    forwardSet(path, value) {
      this.$emit('set', path, value)
    },
    forwardRemove(path) {
      this.$emit('remove', path)
    },
    forwardAddDynamic(path, key) {
      this.$emit('add-dynamic', path, key)
    },
    forwardInputError(path, message) {
      this.$emit('input-error', path, message)
    }
  }
}
</script>

<style scoped>
.schema-form-node {
  width: 100%;
}

.object-collapse {
  border-top: 0;
  border-bottom: 0;
}

.object-collapse.header-hidden :deep(> .el-collapse-item > .el-collapse-item__header) {
  display: none;
}

.object-collapse.header-hidden :deep(> .el-collapse-item > .el-collapse-item__wrap) {
  border-bottom: 0;
}

.object-collapse.header-hidden :deep(> .el-collapse-item > .el-collapse-item__wrap > .el-collapse-item__content) {
  padding-bottom: 0;
}

.object-title {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  min-width: 0;
  padding-right: 8px;
}

.object-heading {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
  min-width: 0;
  flex: 1;
}

.object-heading .field-name,
.object-heading .field-key,
.leaf-label .field-key {
  display: block;
  width: 100%;
}

.object-children {
  padding-left: 12px;
}

.field-name {
  color: var(--el-text-color-primary);
  font-weight: 500;
}

.field-key {
  color: var(--el-text-color-secondary);
  font-family: Consolas, 'Courier New', monospace;
  font-size: 12px;
  word-break: break-all;
}

.required-tag,
.custom-tag {
  flex-shrink: 0;
  padding: 0 4px;
  border-radius: 3px;
  font-size: 11px;
  line-height: 18px;
}

.required-tag {
  color: var(--el-color-danger);
  background: var(--el-color-danger-light-9);
}

.custom-tag {
  color: var(--el-color-warning);
  background: var(--el-color-warning-light-9);
}

.description-trigger {
  flex-shrink: 0;
  color: var(--el-color-primary);
  font-size: 12px;
  cursor: help;
}

.tooltip-content {
  max-width: 460px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}

.leaf-node {
  padding: 8px 0;
  border-bottom: 1px solid var(--el-border-color-extra-light);
}

.leaf-main {
  display: flex;
  align-items: center;
  gap: 8px;
}

.leaf-label {
  flex: 1 1 240px;
  min-width: 180px;
}

.type-label {
  flex: 0 0 90px;
  color: var(--el-text-color-secondary);
  font-family: Consolas, 'Courier New', monospace;
  font-size: 12px;
}

.field-control {
  flex: 0 1 260px;
  min-width: 150px;
}

.field-control :deep(.el-input-number),
.field-control :deep(.el-select) {
  width: 100%;
}

.null-checkbox {
  flex-shrink: 0;
}

.field-error,
.json-error {
  padding: 4px 0 0 32px;
  color: var(--el-color-danger);
  font-size: 12px;
  line-height: 1.5;
}

.custom-notice {
  padding: 2px 0 6px 32px;
  color: var(--el-color-warning);
  font-size: 12px;
}

.leaf-notice {
  padding-top: 4px;
}

.dynamic-key-adder {
  display: flex;
  gap: 8px;
  margin: 8px 0 8px 32px;
  max-width: 420px;
}

@media (max-width: 1000px) {
  .leaf-main {
    flex-wrap: wrap;
  }

  .leaf-label {
    min-width: 220px;
  }

  .field-control {
    flex-basis: 320px;
  }
}
</style>
