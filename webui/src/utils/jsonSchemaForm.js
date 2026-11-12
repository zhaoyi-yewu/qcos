/**
 * Copyright© 2024-2026 China Mobile (SuZhou) Software Technology Co.,Ltd.
 *
 * qcos is licensed under Mulan PSL v2.
 * You can use this software according to the terms and conditions
 * of the Mulan PSL v2.
 * You may obtain a copy of Mulan PSL v2 at:
 *         http://license.coscl.org.cn/MulanPSL2
 * THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS,
 *     WITHOUT WARRANTIES OF ANY KIND,
 * EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
 * MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
 * See the Mulan PSL v2 for more details.
 */

import Ajv from 'ajv'

export const DYNAMIC_SCHEMA_SECTIONS = Object.freeze({
  driver_options: 'driverName',
  transpiler_options: 'transpilerName',
  qec_options: 'driverName'
})

export const SECTION_LABELS = Object.freeze({
  driver_options: '驱动参数',
  transpiler_options: '转译参数',
  options: '作业选项',
  qem_options: '误差缓解参数',
  qec_options: '量子纠错参数',
  extra_specs: '调度额外约束'
})

const DRAFT_07 = 'http://json-schema.org/draft-07/schema#'
const BLOCKED_PATH_SEGMENTS = new Set(['__proto__', 'prototype', 'constructor'])
const SENSITIVE_KEY_PATTERN = /(password|passwd|pwd|token|secret|api[-_]?key|access[-_]?key|credential)/i
const PARAMETER_SCOPE_KEY = 'x-qcos-parameter-scope'
const PARAMETER_SCOPED_SECTIONS = new Set(['driver_options', 'transpiler_options'])

export function isPlainObject(value) {
  if (value === null || typeof value !== 'object' || Array.isArray(value)) {
    return false
  }
  const prototype = Object.getPrototypeOf(value)
  return prototype === Object.prototype || prototype === null
}

export function deepClone(value) {
  if (Array.isArray(value)) {
    return value.map(item => deepClone(item))
  }
  if (isPlainObject(value)) {
    const result = {}
    Object.keys(value).forEach(key => {
      defineOwnValue(result, key, deepClone(value[key]))
    })
    return result
  }
  return value
}

function defineOwnValue(target, key, value) {
  Object.defineProperty(target, key, {
    value,
    enumerable: true,
    configurable: true,
    writable: true
  })
}

function hasOwn(value, key) {
  return value !== null && value !== undefined &&
    Object.prototype.hasOwnProperty.call(value, key)
}

export function pathKey(path) {
  return JSON.stringify(path)
}

export function formatPath(path) {
  return path.join('.')
}

export function updateInputError(errors, path, message) {
  const result = deepClone(errors)
  const key = pathKey(path)
  if (!message) {
    delete result[key]
    return result
  }
  defineOwnValue(result, key, {
    path: deepClone(path),
    key,
    pathText: formatPath(path),
    keyword: 'input-json',
    message
  })
  return result
}

export function clearInputErrors(errors, path) {
  const result = deepClone(errors)
  Object.keys(result).forEach(key => {
    const errorPath = result[key].path || []
    const insideRemovedPath = path.every((segment, index) => errorPath[index] === segment)
    if (insideRemovedPath) delete result[key]
  })
  return result
}

export function listInputErrors(errors) {
  return Object.keys(errors).map(key => deepClone(errors[key])).sort((left, right) => {
    return left.pathText.localeCompare(right.pathText, 'zh-CN')
  })
}

export function getAtPath(value, path) {
  let current = value
  for (const segment of path) {
    if (!hasOwn(current, segment)) return undefined
    current = current[segment]
  }
  return current
}

export function hasAtPath(value, path) {
  let current = value
  for (const segment of path) {
    if (!hasOwn(current, segment)) return false
    current = current[segment]
  }
  return true
}

export function setAtPath(value, path, nextValue) {
  if (!path.length || !isPlainObject(value)) {
    throw new Error('路径父节点必须是普通对象')
  }
  const result = deepClone(value)
  let current = result
  for (let index = 0; index < path.length - 1; index += 1) {
    const segment = path[index]
    if (!hasOwn(current, segment)) {
      defineOwnValue(current, segment, {})
    }
    if (!isPlainObject(current[segment])) {
      throw new Error(`路径 ${formatPath(path.slice(0, index + 1))} 不是对象，不能作为父节点`)
    }
    current = current[segment]
  }
  defineOwnValue(current, path[path.length - 1], deepClone(nextValue))
  return result
}

export function deleteAtPath(value, path, cleanup = true) {
  if (!path.length || !isPlainObject(value)) return deepClone(value)
  const result = deepClone(value)

  function remove(current, index) {
    if (!isPlainObject(current)) return
    const segment = path[index]
    if (!hasOwn(current, segment)) return
    if (index === path.length - 1) {
      delete current[segment]
      return
    }
    const child = current[segment]
    remove(child, index + 1)
    if (cleanup && isPlainObject(child) && Object.keys(child).length === 0) {
      delete current[segment]
    }
  }

  remove(result, 0)
  return result
}

export function omitEmptyRoots(value, sections) {
  const result = deepClone(value)
  if (!isPlainObject(result)) return result
  sections.forEach(section => {
    if (isPlainObject(result[section]) && Object.keys(result[section]).length === 0) {
      delete result[section]
    }
  })
  return result
}

export function getSchemaTypes(schema) {
  if (!isPlainObject(schema)) return []
  const types = []
  const append = type => {
    if (typeof type === 'string' && !types.includes(type)) types.push(type)
  }
  if (Array.isArray(schema.type)) {
    schema.type.forEach(append)
  } else {
    append(schema.type)
  }
  if (Array.isArray(schema.anyOf)) {
    schema.anyOf.forEach(branch => {
      getSchemaTypes(branch).forEach(append)
    })
  }
  return types
}

export function shouldUseJsonInput(schema) {
  const nonNullTypes = getSchemaTypes(schema).filter(type => type !== 'null')
  if (nonNullTypes.includes('array')) return true
  if (nonNullTypes.length === 1 && nonNullTypes[0] === 'object') return false
  return nonNullTypes.length > 1
}

export function isObjectSchema(schema) {
  return isPlainObject(schema) && (
    getSchemaTypes(schema).includes('object') ||
    isPlainObject(schema.properties) ||
    hasOwn(schema, 'additionalProperties')
  )
}

export function getChildSchema(schema, key) {
  if (!isObjectSchema(schema)) {
    return { known: false, blocked: true, schema: null }
  }
  if (isPlainObject(schema.properties) && hasOwn(schema.properties, key)) {
    return { known: true, blocked: false, schema: schema.properties[key] }
  }
  if (isPlainObject(schema.additionalProperties)) {
    return { known: true, blocked: false, schema: schema.additionalProperties, dynamic: true }
  }
  return { known: false, blocked: false, schema: null }
}

export function resolveSchemaPath(rootSchema, path) {
  let current = rootSchema
  for (let index = 0; index < path.length; index += 1) {
    const child = getChildSchema(current, path[index])
    if (child.blocked) {
      return {
        known: false,
        blocked: true,
        blockedPath: path.slice(0, index),
        customRoot: null,
        schema: null
      }
    }
    if (!child.known) {
      return {
        known: false,
        blocked: false,
        customRoot: path.slice(0, index + 1),
        schema: null
      }
    }
    current = child.schema
  }
  return { known: true, blocked: false, customRoot: null, schema: current }
}

function createGenericSchema(section) {
  return {
    type: 'object',
    alias_name: SECTION_LABELS[section] || section,
    description: '当前上下文未提供具体 Schema，可编辑通用 JSON 对象；后端是否支持以提交校验为准。',
    field_constraints: { schema: {}, runtime: {}}
  }
}

export function selectSectionSchemas(schemas, sections, context = {}) {
  const source = isPlainObject(schemas) ? schemas : {}
  const selected = {}
  const degraded = {}
  const resolveDynamic = context.resolveDynamic !== false

  sections.forEach(section => {
    const dynamicContextKey = DYNAMIC_SCHEMA_SECTIONS[section]
    if (dynamicContextKey && !resolveDynamic) {
      selected[section] = createGenericSchema(section)
      degraded[section] = 'Flavor 模式下最终实现尚未确定，当前按通用对象编辑。'
      return
    }

    let schema = source[section]
    if (dynamicContextKey) {
      const name = context[dynamicContextKey]
      schema = isPlainObject(schema) && name ? schema[name] : null
    }
    if (isPlainObject(schema)) {
      selected[section] = deepClone(schema)
      return
    }

    selected[section] = createGenericSchema(section)
    degraded[section] = dynamicContextKey
      ? '未找到当前实现对应的 Schema，已降级为通用对象编辑。'
      : '未获取到该参数组的 Schema，已降级为通用对象编辑。'
  })

  return { schemas: selected, degraded }
}

export function partitionSchemaByParameterScope(section, schema) {
  if (!PARAMETER_SCOPED_SECTIONS.has(section)) return null
  if (!isPlainObject(schema) || !isPlainObject(schema.properties)) return null
  const keys = Object.keys(schema.properties)
  if (!keys.length) return null
  const hasScopeMarker = keys.some(key => {
    const child = schema.properties[key]
    if (!isPlainObject(child)) return false
    return ['common', 'specific'].includes(child[PARAMETER_SCOPE_KEY])
  })
  if (!hasScopeMarker) return null

  // Nested objects (e.g. qes, sc_mapping_options) follow their top-level
  // scope as a whole; unmarked fields fall back to the common group.
  const commonProperties = {}
  const specificProperties = {}
  keys.forEach(key => {
    const child = schema.properties[key]
    const scope = isPlainObject(child) ? child[PARAMETER_SCOPE_KEY] : undefined
    const target = scope === 'specific' ? specificProperties : commonProperties
    defineOwnValue(target, key, child)
  })

  function buildSubset(properties) {
    const subset = deepClone(schema)
    subset.properties = deepClone(properties)
    if (Array.isArray(schema.required)) {
      subset.required = schema.required.filter(key => hasOwn(properties, key))
    }
    return subset
  }

  return {
    section,
    common: buildSubset(commonProperties),
    specific: buildSubset(specificProperties),
    commonKeys: Object.keys(commonProperties),
    specificKeys: Object.keys(specificProperties)
  }
}

export function stripSchemaMetadata(value) {
  if (Array.isArray(value)) return value.map(item => stripSchemaMetadata(item))
  if (!isPlainObject(value)) return value
  const result = {}
  Object.keys(value).forEach(key => {
    if (key === 'alias_name' || key === 'field_constraints' || key.startsWith('x-qcos-')) {
      return
    }
    defineOwnValue(result, key, stripSchemaMetadata(value[key]))
  })
  return result
}

export function buildCombinedSchema(selectedSchemas, sections) {
  const properties = {}
  sections.forEach(section => {
    const schema = stripSchemaMetadata(selectedSchemas[section] || { type: 'object' })
    delete schema.$schema
    defineOwnValue(properties, section, schema)
  })
  return {
    $schema: DRAFT_07,
    type: 'object',
    properties,
    additionalProperties: false
  }
}

export function compileSchema(schema) {
  try {
    const ajv = new Ajv({ allErrors: true, jsonPointers: true })
    return { validate: ajv.compile(schema), error: null }
  } catch (error) {
    return { validate: null, error: error.message || 'Schema 编译失败' }
  }
}

export function createDefaultValue(schema) {
  if (!isPlainObject(schema)) return null
  if (hasOwn(schema, 'default')) {
    const candidate = deepClone(schema.default)
    const cleanSchema = stripSchemaMetadata(schema)
    const { validate, error } = compileSchema(cleanSchema)
    if (!error && validate(candidate)) return candidate
  }
  if (Array.isArray(schema.enum) && schema.enum.length) {
    return deepClone(schema.enum[0])
  }
  const types = getSchemaTypes(schema)
  const type = types.find(item => item !== 'null') || types[0]
  switch (type) {
    case 'boolean':
      return false
    case 'integer':
    case 'number':
      return null
    case 'string':
      return ''
    case 'array':
      return []
    case 'object':
      return {}
    case 'null':
      return null
    default:
      return null
  }
}

export function detectCustomBranches(value, selectedSchemas, sections) {
  const branches = []
  const registered = new Set()
  if (!isPlainObject(value)) return branches

  function register(path) {
    const key = pathKey(path)
    if (!registered.has(key)) {
      registered.add(key)
      branches.push(path)
    }
  }

  function walk(currentValue, schema, path) {
    if (!isPlainObject(currentValue) || !isObjectSchema(schema)) return
    Object.keys(currentValue).forEach(key => {
      const child = getChildSchema(schema, key)
      const childPath = path.concat(key)
      if (!child.known) {
        register(childPath)
        return
      }
      walk(currentValue[key], child.schema, childPath)
    })
  }

  sections.forEach(section => {
    if (hasOwn(value, section)) {
      walk(value[section], selectedSchemas[section], [section])
    }
  })
  return branches
}

export function removeValidationExemptions(value, customBranches) {
  let result = deepClone(value)
  customBranches.forEach(path => {
    result = deleteAtPath(result, path, false)
  })
  return result
}

function decodePointerSegment(segment) {
  return segment.replace(/~1/g, '/').replace(/~0/g, '~')
}

function instancePathToSegments(error) {
  const pointer = typeof error.instancePath === 'string'
    ? error.instancePath
    : (error.dataPath || '')
  if (!pointer) return []
  if (pointer.startsWith('/')) {
    return pointer.slice(1).split('/').filter(Boolean).map(decodePointerSegment)
  }
  const segments = []
  pointer.replace(/\.([^.\[]+)|\[['"]?([^\]'"]+)['"]?\]/g, (match, dotKey, bracketKey) => {
    segments.push(dotKey !== undefined ? dotKey : bracketKey)
    return match
  })
  return segments
}

function constraintMessage(error) {
  const params = error.params || {}
  switch (error.keyword) {
    case 'required':
      return `缺少必填字段：${params.missingProperty}`
    case 'type':
      return `类型错误：应为 ${Array.isArray(params.type) ? params.type.join(' 或 ') : params.type}`
    case 'enum':
      return '值不在允许的枚举范围内'
    case 'additionalProperties':
      return `包含 Schema 未声明的字段：${params.additionalProperty}`
    case 'minimum':
      return `数值必须大于或等于 ${params.limit}`
    case 'maximum':
      return `数值必须小于或等于 ${params.limit}`
    case 'exclusiveMinimum':
      return `数值必须大于 ${params.limit}`
    case 'exclusiveMaximum':
      return `数值必须小于 ${params.limit}`
    case 'multipleOf':
      return `数值必须是 ${params.multipleOf} 的整数倍`
    case 'minLength':
      return `字符串长度不能小于 ${params.limit}`
    case 'maxLength':
      return `字符串长度不能大于 ${params.limit}`
    case 'pattern':
      return '字符串不符合要求的格式'
    case 'minItems':
      return `数组元素数量不能少于 ${params.limit}`
    case 'maxItems':
      return `数组元素数量不能多于 ${params.limit}`
    case 'uniqueItems':
      return '数组元素不能重复'
    case 'minProperties':
      return `对象字段数量不能少于 ${params.limit}`
    case 'maxProperties':
      return `对象字段数量不能多于 ${params.limit}`
    default:
      return `字段校验失败（${error.keyword || '未知规则'}）`
  }
}

export function convertAjvErrors(errors) {
  return (errors || []).map(error => {
    const path = instancePathToSegments(error)
    const params = error.params || {}
    if (error.keyword === 'required' && params.missingProperty) {
      path.push(params.missingProperty)
    } else if (error.keyword === 'additionalProperties' && params.additionalProperty) {
      path.push(params.additionalProperty)
    }
    return {
      path,
      key: pathKey(path),
      pathText: path.length ? formatPath(path) : '根对象',
      keyword: error.keyword,
      message: constraintMessage(error)
    }
  })
}

export function parseCustomPath(pathText, value, selectedSchemas, sections) {
  const normalized = typeof pathText === 'string' ? pathText.trim() : ''
  if (!normalized) return { ok: false, message: '请输入完整根路径' }
  const path = normalized.split('.')
  if (path.some(segment => !segment)) {
    return { ok: false, message: '路径不能包含空前缀、连续点或首尾点' }
  }
  if (path.some(segment => BLOCKED_PATH_SEGMENTS.has(segment))) {
    return { ok: false, message: '路径包含不安全字段名' }
  }
  if (!sections.includes(path[0])) {
    return { ok: false, message: `根节点必须是：${sections.join('、')}` }
  }
  if (path.length === 1) {
    return { ok: false, message: '自定义路径必须包含根节点下的字段名' }
  }

  const resolution = resolveSchemaPath(selectedSchemas[path[0]], path.slice(1))
  if (resolution.blocked) {
    return { ok: false, message: '不能把 scalar 或 array 字段作为父节点' }
  }
  if (resolution.known) {
    return { ok: false, message: '自定义路径不能与 Schema 已知字段或动态 map 字段重合' }
  }

  let current = value
  for (let index = 0; index < path.length - 1; index += 1) {
    if (!isPlainObject(current)) {
      return { ok: false, message: `路径 ${formatPath(path.slice(0, index)) || '根对象'} 不是对象` }
    }
    const segment = path[index]
    if (!hasOwn(current, segment)) break
    current = current[segment]
    if (!isPlainObject(current)) {
      return { ok: false, message: `路径 ${formatPath(path.slice(0, index + 1))} 不能作为父节点` }
    }
  }

  return {
    ok: true,
    path,
    customRoot: [path[0]].concat(resolution.customRoot || []),
    message: ''
  }
}

export function parseStrictJsonValue(text) {
  try {
    return { ok: true, value: JSON.parse(text), message: '' }
  } catch (error) {
    return { ok: false, value: undefined, message: `JSON 格式错误：${error.message}` }
  }
}

export function parseJsonLiteral(text) {
  const source = typeof text === 'string' ? text : ''
  try {
    return { ok: true, value: JSON.parse(source) }
  } catch {
    return { ok: true, value: source }
  }
}

export function isSensitiveField(path, schema) {
  if (schema && schema.writeOnly === true) return true
  const key = path.length ? path[path.length - 1] : ''
  return SENSITIVE_KEY_PATTERN.test(key)
}

export function formatPreviewValue(value, sensitive = false) {
  if (sensitive) return '******'
  if (typeof value === 'string') return value
  if (value === undefined) return '—'
  const serialized = JSON.stringify(value)
  return serialized === undefined ? String(value) : serialized
}

export function formatConstraints(constraints) {
  if (!isPlainObject(constraints) || Object.keys(constraints).length === 0) return ''
  return JSON.stringify(constraints)
}

export function countConfiguredLeaves(value, sections) {
  if (!isPlainObject(value)) return 0

  function count(current, path) {
    if (isPlainObject(current)) {
      const keys = Object.keys(current)
      if (!keys.length) return path.length > 1 ? 1 : 0
      return keys.reduce((total, key) => total + count(current[key], path.concat(key)), 0)
    }
    return 1
  }

  return sections.reduce((total, section) => {
    if (!hasOwn(value, section)) return total
    return total + count(value[section], [section])
  }, 0)
}

export function flattenPreviewRows(value, selectedSchemas, sections) {
  const rows = new Map()
  const source = isPlainObject(value) ? value : {}

  function makeRow(path, schema, configured, currentValue) {
    const fieldConstraints = isPlainObject(schema && schema.field_constraints)
      ? schema.field_constraints
      : {}
    const sensitive = isSensitiveField(path, schema)
    return {
      key: pathKey(path),
      path,
      pathText: formatPath(path),
      name: (schema && schema.alias_name) || path[path.length - 1],
      description: (schema && schema.description) || '',
      schemaConstraints: formatConstraints(fieldConstraints.schema),
      runtimeConstraints: formatConstraints(fieldConstraints.runtime),
      configured,
      sensitive,
      displayValue: configured ? formatPreviewValue(currentValue, sensitive) : '—'
    }
  }

  function collectSchema(schema, path) {
    if (isObjectSchema(schema)) {
      if (isPlainObject(schema.properties)) {
        Object.keys(schema.properties).forEach(key => {
          collectSchema(schema.properties[key], path.concat(key))
        })
      }
      const currentValue = getAtPath(source, path)
      if (isPlainObject(currentValue) && isPlainObject(schema.additionalProperties)) {
        Object.keys(currentValue).forEach(key => {
          if (!isPlainObject(schema.properties) || !hasOwn(schema.properties, key)) {
            collectSchema(schema.additionalProperties, path.concat(key))
          }
        })
      }
      return
    }
    const configured = hasAtPath(source, path)
    rows.set(pathKey(path), makeRow(path, schema, configured, getAtPath(source, path)))
  }

  function collectValue(currentValue, schema, path) {
    if (isPlainObject(currentValue) && Object.keys(currentValue).length) {
      Object.keys(currentValue).forEach(key => {
        const child = getChildSchema(schema, key)
        collectValue(currentValue[key], child.known ? child.schema : null, path.concat(key))
      })
      return
    }
    const key = pathKey(path)
    if (!rows.has(key)) {
      rows.set(key, makeRow(path, schema, true, currentValue))
      return
    }
    const existing = rows.get(key)
    const resolvedSchema = existing.name === path[path.length - 1] && schema ? schema : null
    rows.set(key, makeRow(path, resolvedSchema || schema || {
      alias_name: existing.name,
      description: existing.description,
      field_constraints: {
        schema: existing.schemaConstraints ? JSON.parse(existing.schemaConstraints) : {},
        runtime: existing.runtimeConstraints ? JSON.parse(existing.runtimeConstraints) : {}
      },
      writeOnly: existing.sensitive
    }, true, currentValue))
  }

  sections.forEach(section => {
    collectSchema(selectedSchemas[section], [section])
  })
  sections.forEach(section => {
    if (hasOwn(source, section)) {
      collectValue(source[section], selectedSchemas[section], [section])
    }
  })

  return Array.from(rows.values()).sort((left, right) => {
    const leftRoot = sections.indexOf(left.path[0])
    const rightRoot = sections.indexOf(right.path[0])
    if (leftRoot !== rightRoot) return leftRoot - rightRoot
    return left.pathText.localeCompare(right.pathText, 'zh-CN')
  })
}
