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
  <div v-if="loaded" class="task-submit-container">
    <div class="form-container">
      <el-form
        ref="taskForm"
        :model="taskData"
        :rules="rules"
        label-width="150px"
        status-icon
        class="task-form"
      >
        <el-row :gutter="20" class="qasm-main-row">
          <el-col ref="leftCol" :span="10" class="qasm-left-col">
            <el-form-item>
              <template #label><span style="font-weight: 700;">选择QUBO文件</span></template>
              <div class="file-upload">
                <el-upload
                  ref="upload"
                  class="upload-demo"
                  accept=".json,.csv"
                  action=""
                  :auto-upload="false"
                  :show-file-list="false"
                  :on-change="handleFileChange"
                  :multiple="true"
                >
                  <el-button type="primary">选择文件</el-button>
                </el-upload>
                <div v-if="lastFilePath" class="last-file-hint">
                  <span class="last-file-path" :title="lastFilePath">{{ lastFilePath }}</span>
                  <el-tooltip content="复制路径" placement="top">
                    <el-button
                      link
                      type="primary"
                      :icon="CopyDocument"
                      class="copy-btn"
                      @click="copyLastPath"
                    />
                  </el-tooltip>
                </div>
              </div>
            </el-form-item>
            <el-form-item label="作业名称" prop="taskName">
              <el-input
                v-model="taskData.taskName"
                placeholder="请输入作业名称 (可选)"
              />
            </el-form-item>
            <el-form-item label="作业描述" prop="taskDescription">
              <el-input
                v-model="taskData.taskDescription"
                type="textarea"
                :rows="2"
                placeholder="请输入作业描述 (可选)"
              />
            </el-form-item>
            <el-form-item label="代码参数" prop="params">
              <el-input
                v-model="taskData.params"
                type="textarea"
                :rows="2"
                placeholder="请输入代码参数 (可选, JSON格式)"
              />
            </el-form-item>
            <el-form-item label="作业选项" prop="options">
              <el-input
                v-model="taskData.options"
                type="textarea"
                :rows="2"
                placeholder="请输入作业选项 (可选, JSON格式)"
              />
            </el-form-item>
            <div class="inline-form-row">
              <div class="inline-form-col inline-form-left">
                <el-form-item label="作业优先级" prop="taskPriority" class="inline-form-item">
                  <el-input-number
                    v-model="taskData.taskPriority"
                    :min="1"
                    :max="10"
                    label="作业优先级"
                  />
                </el-form-item>
              </div>
            </div>
          </el-col>
          <el-col :span="14" style="padding-right: 0;" class="qasm-right-col">
            <el-form-item class="qasm-form-item">
              <template #label><span style="font-weight: 700;"><span style="color: #f56c6c;">*</span> 源代码</span></template>
              <div
                class="qasm-tabs-container"
                :class="{ 'qasm-fullscreen': editorFullscreen }"
                :style="tabsContainerStyle"
              >
                <div class="qasm-tabs-header">
                  <span class="qasm-tab-scroll-btn" title="向左滚动" @click="scrollTabsLeft">&lsaquo;</span>
                  <div ref="tabsScroll" class="qasm-tabs-scroll">
                    <span
                      v-for="(tab, index) in taskData.quboTabs"
                      :key="index"
                      :class="['qasm-tab', { active: taskData.activeQuboTab === index }]"
                      :title="tab.name"
                      @click="switchQuboTab(index)"
                    >
                      <el-icon v-if="tab.fromFile" class="qasm-tab-icon"><Document /></el-icon>
                      <span class="qasm-tab-label">{{ tabLabel(tab, index) }}</span>
                      <span
                        class="qasm-tab-close"
                        @click.stop="removeQuboTab(index)"
                      >&times;</span>
                    </span>
                  </div>
                  <span class="qasm-tab-add" title="新建代码标签" @click="addQuboTab">&plus;</span>
                  <span class="qasm-tab-scroll-btn" title="向右滚动" @click="scrollTabsRight">&rsaquo;</span>
                  <span
                    class="qasm-fullscreen-btn"
                    :title="editorFullscreen ? '退出全屏' : '全屏编辑'"
                    @click="toggleFullscreen"
                  >
                    <el-icon><FullScreen /></el-icon>
                  </span>
                </div>
                <div
                  ref="monacoWrapper"
                  class="qasm-monaco-wrapper"
                  :style="editorWrapperStyle"
                >
                  <div v-if="taskData.quboTabs.length === 0" class="qasm-empty-placeholder">
                    <el-icon class="qasm-empty-icon"><Document /></el-icon>
                    <p class="qasm-empty-text">请点击右上角的 <span class="qasm-empty-plus">&plus;</span> 新建代码标签，或在左侧选择 QUBO 文件<br>提交作业后，会按照代码顺序在一个作业中以多代码列表方式执行</p>
                  </div>
                  <monaco-editor
                    v-else
                    :value="activeTabCode"
                    :path="activeTabPath"
                    :language="activeTabLanguage"
                    theme="vs"
                    :options="editorOptions"
                    class="qasm-monaco-editor"
                    @change="onEditorChange"
                  />
                </div>
                <div
                  class="qasm-resize-handle"
                  title="拖拽调整编辑器高度，双击恢复自适应"
                  @mousedown.prevent="startResize"
                  @dblclick="resetEditorHeight"
                >
                  <span class="qasm-resize-grip" />
                </div>
              </div>
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="20">
          <el-col :span="10">
            <el-form-item required prop="scheduleMode">
              <template #label><span style="font-weight: 700;">调度模式</span></template>
              <el-radio-group v-model="taskData.scheduleMode" @change="handleScheduleModeChange">
                <el-radio value="backend" border>手动调度</el-radio>
                <el-radio value="flavor" border>自动调度</el-radio>
              </el-radio-group>
            </el-form-item>
            <el-form-item
              v-if="taskData.scheduleMode === 'backend'"
              label="后端设备"
              prop="taskBackend"
              required
            >
              <el-select
                v-model="taskData.taskBackend"
                class="auto-width backend-device-select"
                placeholder="请输入后端设备"
                label="后端设备"
                popper-class="backend-device-select-popper"
                @change="handleBackendChange"
              >
                <template v-if="currentBackendStatus" #prefix>
                  <span
                    class="device-state-dot"
                    :class="'state-' + currentBackendStatus"
                    :title="currentBackendStatus"
                  />
                </template>
                <el-option-group
                  v-for="group in groupedDevices"
                  :key="group.techType"
                  :label="group.label"
                >
                  <el-option
                    v-for="device in group.items"
                    :key="device.name"
                    :label="device.aliasName + ' (' + device.name + ') [' + device.maxQubits + ' qubits]'"
                    :value="device.name"
                    :disabled="device.disabled"
                    class="backend-device-option"
                  >
                    <el-tooltip
                      placement="right"
                      :show-after="200"
                      raw-content
                      :content="deviceTooltipHtml(device)"
                      popper-class="device-option-tooltip"
                    >
                      <div class="device-option-row">
                        <span
                          class="device-state-dot"
                          :class="'state-' + (device.status || 'unknown')"
                          :title="device.status || 'unknown'"
                        />
                        <span class="device-alias">{{ device.aliasName }}</span>
                        <span class="device-name">({{ device.name }})</span>
                        <span class="device-qubits">[{{ device.maxQubits }} qubits]</span>
                        <span
                          v-if="device.availability !== null"
                          class="device-availability"
                          :class="availabilityTagClass(device.availability)"
                          :title="'可用率 ' + formatAvailability(device.availability)"
                        >
                          <el-icon class="device-availability-icon"><Odometer /></el-icon>
                          <span class="device-availability-value">{{ formatAvailability(device.availability) }}</span>
                        </span>
                      </div>
                    </el-tooltip>
                  </el-option>
                </el-option-group>
              </el-select>
            </el-form-item>
            <el-form-item
              v-else
              label="资源规格"
              prop="taskFlavor"
              required
            >
              <el-select
                v-model="taskData.taskFlavor"
                class="auto-width"
                placeholder="请选择资源规格 (flavor)"
                label="资源规格"
                :loading="flavorLoading"
                @change="handleFlavorChange"
              >
                <el-option
                  v-for="flavor in effectiveFlavorOptions"
                  :key="flavor.id"
                  :label="flavorLabel(flavor)"
                  :value="flavor.id"
                >
                  <el-tooltip
                    placement="right"
                    :show-after="200"
                    raw-content
                    :content="flavorTooltipHtml(flavor)"
                    popper-class="device-option-tooltip"
                    :disabled="!flavor.description"
                  >
                    <div class="device-option-row">
                      <span class="device-alias">{{ flavor.name }}</span>
                      <span v-if="flavor.description" class="device-name">({{ flavor.description }})</span>
                    </div>
                  </el-tooltip>
                </el-option>
              </el-select>
            </el-form-item>
            <el-form-item
              v-if="taskData.scheduleMode === 'flavor'"
              label="额外调度参数"
              prop="extraSpecs"
            >
              <el-input
                v-model="taskData.extraSpecs"
                type="textarea"
                :rows="3"
                placeholder="请输入额外调度参数 (可选, JSON格式)，例如 {&quot;qcos:min_qubits&quot;: 5, &quot;qc:tech_types&quot;: &quot;superconducting&quot;}"
              />
            </el-form-item>
          </el-col>

          <el-col :span="14" style="padding-right: 0;">
            <el-form-item label="驱动自定义选项" prop="driverOptions">
              <el-input
                v-model="taskData.driverOptions"
                type="textarea"
                :rows="4"
                placeholder="请输入驱动自定义选项 (可选, JSON格式)"
              />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="20">
          <el-col :span="10">
            <el-form-item label="转译器" prop="taskTranspiler">
              <el-select
                v-model="taskData.taskTranspiler"
                class="auto-width"
                placeholder="请选择转译器"
                label="转译器"
              >
                <el-option
                  v-for="transpiler in currentTranspilers"
                  :key="transpiler.name"
                  :label="transpiler.alias_name + ' (' + transpiler.name + ')'"
                  :value="transpiler.name"
                />
              </el-select>
            </el-form-item>
          </el-col>

          <el-col :span="14" style="padding-right: 0;">
            <el-form-item label="转译器自定义选项" prop="transpilerOptions">
              <el-input
                v-model="taskData.transpilerOptions"
                type="textarea"
                :rows="2"
                placeholder="请输入转译器自定义选项 (可选, JSON格式)"
              />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="20">
          <el-col :span="10">
            <el-form-item label="运行模式" prop="taskDryRun">
              <el-radio-group v-model="taskData.taskDryRun">
                <el-radio value="false" border>真实运行</el-radio>
                <el-radio value="true" border>空载运行(dry-run)</el-radio>
              </el-radio-group>
            </el-form-item>
          </el-col>

          <el-col :span="14" style="padding-right: 0;">
            <el-form-item label="线路聚合模式" prop="circuitAggregation">
              <el-radio-group v-model="taskData.circuitAggregation">
                <el-radio value="none" border>无(串行)</el-radio>
                <el-radio value="internal" border>作业内并行</el-radio>
                <el-radio value="external" border>多作业并行</el-radio>
              </el-radio-group>
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item prop="profiling">
          <template #label><span style="font-weight: 700;">性能调测选项</span></template>
          <el-checkbox v-model="taskData.profilingAll" @change="handleProfilingAll">记录所有耗时</el-checkbox>
          <el-checkbox v-model="taskData.profilingQueuing">记录排队耗时</el-checkbox>
          <el-checkbox v-model="taskData.profilingScheduling">记录调度器耗时</el-checkbox>
          <el-checkbox v-model="taskData.profilingDriverParse">记录代码解析耗时</el-checkbox>
          <el-checkbox v-model="taskData.profilingDriverTranspile">记录转译耗时</el-checkbox>
          <el-checkbox v-model="taskData.profilingCode">记录单代码运行耗时</el-checkbox>
          <el-checkbox v-model="taskData.profilingDriverRun">记录后端运行耗时</el-checkbox>
          <el-checkbox v-model="taskData.profilingMachine">记录量子计算机运行耗时</el-checkbox>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<script>
import { markRaw } from 'vue'
import { getDevices } from '@/api/device'
import { submitJob } from '@/api/job'
import { queryVersion } from '@/api/version'
import {
  filterDevices,
  getDeviceStatusDisplay,
  isEmptyStr,
  normalizeJsonInput,
  quboParser
} from '@/common/library'
import MonacoEditor from '@/components/MonacoEditor/index.vue'
import { Document, FullScreen, CopyDocument, Odometer } from '@element-plus/icons-vue'
import { getFlavors } from '@/api/flavor'
import * as monaco from 'monaco-editor/esm/vs/editor/editor.api'
// Import JSON language contribution to enable syntax highlighting
// (editor.api does not include language contributions by default)
import 'monaco-editor/esm/vs/language/json/monaco.contribution'

// Register CSV language for syntax highlighting (Monaco does not ship CSV by default)
if (!monaco.languages.getLanguages().some(lang => lang.id === 'csv')) {
  monaco.languages.register({ id: 'csv' })
  monaco.languages.setMonarchTokensProvider('csv', {
    tokenizer: {
      root: [
        // numbers
        [/-?\d+\.?\d*[eE]?-?\d*/, 'number'],
        // strings in double quotes
        [/"[^"]*"/, 'string'],
        // strings in single quotes
        [/'[^']*'/, 'string'],
        // comma delimiter
        [/,/, 'delimiter'],
        // semicolon delimiter
        [/;/, 'delimiter'],
        // header keywords (first row)
        [/^[^,\n;]+/, 'keyword'],
        // identifiers / text
        [/[a-zA-Z_]\w*/, 'identifier']
      ]
    }
  })
}

export default {
  name: 'QuboSubmit',
  components: {
    MonacoEditor,
    Document,
    FullScreen,
    Odometer
  },
  props: {
    // code type selected by the parent page (qubo)
    codeType: {
      type: String,
      default: 'qubo'
    },
    // version capabilities forwarded by the parent job_submit page; when
    // provided, this component skips its own /version API call so the
    // whole submit page only issues a single request per upstream endpoint
    versionData: {
      type: Object,
      default: null
    },
    // device details map forwarded by the parent page; same purpose as
    // versionData -- avoids duplicate /v1/device API calls
    devicesDetails: {
      type: Object,
      default: null
    },
    // flavor options forwarded by the parent page; same purpose as
    // versionData -- avoids duplicate /v1/flavor API calls
    flavorOptions: {
      type: Array,
      default: null
    }
  },
  data() {
    return {
      loaded: false,
      // expose CopyDocument icon to the template via data (markRaw); it is
      // only used as an :icon value, not as a component tag
      CopyDocument: markRaw(CopyDocument),
      // local fallback copy of version capabilities, populated either by
      // the parent's versionData prop (preferred, no extra request) or by
      // a self-issued /version call when the prop is missing
      localVersionData: {
        version: '',
        api_version: '',
        supported_api_versions: [],
        platform_version: '',
        capabilities: {}
      },
      // local fallback copy of the device details map; populated either
      // by the parent's devicesDetails prop or by a self-issued
      // /v1/device call when the prop is missing
      localDevicesDetails: {},
      devices: {},
      taskData: {
        taskFile: '',
        taskFileList: [],
        taskName: null,
        taskDescription: null,
        taskTranspiler: null,
        transpilerOptions: null,
        // scheduling mode: 'backend' (manual) or 'flavor' (auto)
        scheduleMode: 'backend',
        taskBackend: '',
        taskFlavor: '',
        // extra scheduling specs (JSON text), only meaningful in flavor
        // mode; parsed into extra_specs on submit and forwarded to the
        // auto-scheduler to override flavor defaults
        extraSpecs: null,
        driverOptions: null,
        params: null,
        options: null,
        taskDryRun: 'false',
        shotCount: 1,
        taskPriority: 5,
        circuitAggregation: 'none',
        quboTabs: [],
        activeQuboTab: 0,
        // remember the last selected file name to display and copy
        lastFilePath: '',
        profilingAll: false,
        profilingQueuing: false,
        profilingScheduling: false,
        profilingDriverParse: false,
        profilingDriverTranspile: false,
        profilingCode: false,
        profilingDriverRun: false,
        profilingMachine: false
      },
      // local fallback list of flavor options; populated either by the
      // parent's flavorOptions prop or by a self-issued /v1/flavor call
      // when the prop is missing
      localFlavorOptions: [],
      flavorLoading: false,

      rules: {
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
      },
      editorMinHeight: null,
      editorFullscreen: false
    }
  },

  computed: {
    // unified accessors that prefer the parent-forwarded props and fall
    // back to the locally-fetched copies when this component is used
    // standalone (i.e. the parent did not provide the data)
    effectiveVersionData() {
      return this.versionData || this.localVersionData
    },
    effectiveDevicesDetails() {
      return this.devicesDetails || this.localDevicesDetails
    },
    // status of the currently selected backend device, used to render the
    // leading status dot inside the select input (prefix slot); empty
    // string when nothing is selected or the device is unknown
    currentBackendStatus() {
      const backend = this.taskData.taskBackend
      if (!backend) return ''
      const device = this.effectiveDevicesDetails[backend]
      return (device && device['status']) || ''
    },
    effectiveFlavorOptions() {
      return this.flavorOptions || this.localFlavorOptions
    },
    // group the visible devices by their technology route (tech_type) so
    // the backend dropdown can render them under per-route headers; the
    // groups follow a fixed ordering (simulator -> superconducting ->
    // neutral atom -> ion trap -> nmr -> others); tech_type / max_qubits /
    // status are read from the device details (device API), while the
    // version API only provides the tech_types alias mapping
    groupedDevices() {
      const groups = {}
      const caps = (this.effectiveVersionData && this.effectiveVersionData.capabilities) || {}
      const techTypes = caps['tech_types'] || {}
      for (const deviceName in this.devices) {
        const details = this.effectiveDevicesDetails[deviceName] || {}
        const techType = details['tech_type'] || 'unknown'
        const techTypeAlias = (techTypes[techType] && techTypes[techType].alias_name) || techType
        if (!groups[techType]) {
          groups[techType] = {
            techType: techType,
            label: techTypeAlias,
            items: []
          }
        }
        // qubit count shown in the dropdown: prefer available_qubits from
        // the device API; fall back to max_qubits when it is nullish
        const availableQubits = details['available_qubits']
        const maxQubits = details['max_qubits']
        const qubits = availableQubits !== undefined && availableQubits !== null
          ? availableQubits
          : (maxQubits !== undefined && maxQubits !== null ? maxQubits : '-')
        // availability rate (0-1) from device metrics; null when missing
        const metrics = details['metrics'] || {}
        const availability = (metrics['availability_total'] !== undefined && metrics['availability_total'] !== null)
          ? metrics['availability_total']
          : null
        // a device is selectable only when it is enabled AND its runtime
        // status is online; everything else is rendered but disabled so
        // the user can still see it and read the tooltip explanation
        const enabled = details['enable'] !== false
        const status = details['status'] || 'unknown'
        const selectable = enabled && status === 'online'
        groups[techType].items.push({
          name: deviceName,
          aliasName: details['alias_name'] || deviceName,
          status: status,
          isManual: details['is_manual'] === true,
          enabled: enabled,
          disabled: !selectable,
          maxQubits: qubits,
          techType: techType,
          techTypeAlias: techTypeAlias,
          availability: availability
        })
      }
      // fixed group ordering: simulator first, then superconducting,
      // neutral atom, ion trap, nmr; any remaining tech types keep their
      // alphabetical order at the end
      const TECH_TYPE_ORDER = [
        'generic_simulator',
        'superconducting',
        'neutral_atom',
        'ion_trap',
        'nmr'
      ]
      const sorted = Object.values(groups)
      sorted.sort((a, b) => {
        const ia = TECH_TYPE_ORDER.indexOf(a.techType)
        const ib = TECH_TYPE_ORDER.indexOf(b.techType)
        const ra = ia === -1 ? TECH_TYPE_ORDER.length : ia
        const rb = ib === -1 ? TECH_TYPE_ORDER.length : ib
        if (ra !== rb) return ra - rb
        return String(a.label).localeCompare(String(b.label))
      })
      for (const g of sorted) {
        g.items.sort((a, b) => String(a.aliasName).localeCompare(String(b.aliasName)))
      }
      return sorted
    },
    // transpiler options derived from the currently selected backend's
    // driver via version API capabilities: device -> driver_name ->
    // capabilities.drivers[driver_name].supported_transpilers; the
    // driver's default transpiler (drivers[driver_name].transpiler) is
    // placed first so the dropdown shows it as the leading option
    currentTranspilers() {
      const backend = this.taskData.taskBackend
      if (!backend) return []
      const device = this.effectiveDevicesDetails[backend]
      if (!device) return []
      const driverName = device['driver_name']
      if (!driverName) return []
      const capabilities = (this.effectiveVersionData && this.effectiveVersionData.capabilities) || {}
      const drivers = capabilities['drivers'] || {}
      const transpilers = capabilities['transpilers'] || {}
      const driver = drivers[driverName] || {}
      const supported = driver['supported_transpilers'] || []
      const defaultName = driver['transpiler'] || ''
      // build the ordered name list: default first, then the rest in
      // declaration order, deduplicated
      const ordered = []
      if (defaultName && supported.includes(defaultName)) {
        ordered.push(defaultName)
      }
      for (const name of supported) {
        if (!ordered.includes(name)) {
          ordered.push(name)
        }
      }
      const result = []
      for (const name of ordered) {
        const t = transpilers[name] || {}
        result.push({
          name: name,
          alias_name: t['alias_name'] || name
        })
      }
      return result
    },
    // name of the default transpiler for the currently selected backend;
    // empty string when the backend/driver has no default configured
    currentDefaultTranspiler() {
      const backend = this.taskData.taskBackend
      if (!backend) return ''
      const device = this.effectiveDevicesDetails[backend]
      if (!device) return ''
      const driverName = device['driver_name']
      if (!driverName) return ''
      const capabilities = (this.effectiveVersionData && this.effectiveVersionData.capabilities) || {}
      const drivers = capabilities['drivers'] || {}
      const driver = drivers[driverName] || {}
      return driver['transpiler'] || ''
    },
    activeTabCode() {
      const tab = this.taskData.quboTabs[this.taskData.activeQuboTab]
      return tab ? tab.code : ''
    },
    activeTabLanguage() {
      const tab = this.taskData.quboTabs[this.taskData.activeQuboTab]
      if (!tab || !tab.name) return 'json'
      const ext = tab.name.toLowerCase().split('.').pop()
      if (ext === 'csv') return 'csv'
      return 'json'
    },
    activeTabPath() {
      return `qubo-tab-${this.taskData.activeQuboTab}`
    },
    editorOptions() {
      return {
        automaticLayout: true,
        fontSize: 14,
        lineHeight: 21,
        minimap: { enabled: false },
        scrollBeyondLastLine: false,
        wordWrap: 'on',
        tabSize: 4,
        insertSpaces: true,
        fontFamily: 'Consolas, "Courier New", monospace',
        lineNumbers: 'on',
        folding: true,
        bracketPairColorization: { enabled: true }
      }
    },
    editorWrapperStyle() {
      if (this.editorFullscreen) {
        return { height: 'calc(100vh - 110px)', width: '100%' }
      }
      const h = this.editorMinHeight !== null ? this.editorMinHeight : 360
      return { height: h + 'px' }
    },
    tabsContainerStyle() {
      if (this.editorFullscreen) {
        return {
          position: 'fixed',
          top: '40px',
          left: '40px',
          width: 'calc(100vw - 80px)',
          height: 'calc(100vh - 80px)',
          zIndex: '2000',
          background: '#ffffff',
          border: '1px solid #dcdfe6',
          borderRadius: '6px',
          boxShadow: '0 8px 30px rgba(0, 0, 0, 0.2)',
          padding: '8px',
          boxSizing: 'border-box',
          overflow: 'hidden'
        }
      }
      return {}
    }
  },

  created() {
    this.queryData()
  },

  mounted() {
    this.initSyncLeftHeight()
    this._onKeyDown = this.onKeyDown.bind(this)
    document.addEventListener('keydown', this._onKeyDown)
  },

  beforeUnmount() {
    this.destroySyncLeftHeight()
    if (this._onKeyDown) {
      document.removeEventListener('keydown', this._onKeyDown)
      this._onKeyDown = null
    }
  },

  methods: {
    // re-export from common/library so the template can call it directly
    getDeviceStatusDisplay,

    onKeyDown(event) {
      if (event.key === 'Escape' && this.editorFullscreen) {
        this.editorFullscreen = false
      }
    },

    initSyncLeftHeight() {
      this.syncLeftHeight()
      if (typeof ResizeObserver !== 'undefined' && this.$refs.leftCol) {
        const el = this.$refs.leftCol.$el || this.$refs.leftCol
        this.resizeObserver = new ResizeObserver(this.syncLeftHeight.bind(this))
        this.resizeObserver.observe(el)
      }
    },

    destroySyncLeftHeight() {
      if (this.resizeObserver) {
        this.resizeObserver.disconnect()
        this.resizeObserver = null
      }
      if (this._onResizeMove) {
        document.removeEventListener('mousemove', this._onResizeMove)
        document.removeEventListener('mouseup', this._onResizeStop)
      }
    },

    syncLeftHeight() {
      this.$nextTick(() => {
        const leftCol = this.$refs.leftCol
        if (!leftCol) return
        const el = leftCol.$el || leftCol
        if (!el) return
        const colHeight = el.offsetHeight
        const headerH = 30
        const handleH = 8
        const marginH = 25
        const minH = colHeight - headerH - handleH - marginH
        if (minH > 100) {
          this.editorMinHeight = minH
        }
      })
    },

    startResize(event) {
      const wrapper = this.$refs.monacoWrapper
      if (!wrapper) return
      this._resizing = true
      this._startY = event.clientY
      this._startHeight = wrapper.offsetHeight
      this._onResizeMove = this.onResizeMove.bind(this)
      this._onResizeStop = this.onResizeStop.bind(this)
      document.addEventListener('mousemove', this._onResizeMove)
      document.addEventListener('mouseup', this._onResizeStop)
      document.body.style.cursor = 'ns-resize'
      document.body.style.userSelect = 'none'
    },

    onResizeMove(event) {
      if (!this._resizing) return
      const deltaY = event.clientY - this._startY
      let newHeight = this._startHeight + deltaY
      if (newHeight < 120) newHeight = 120
      if (newHeight > 1200) newHeight = 1200
      this.editorMinHeight = newHeight
    },

    onResizeStop() {
      this._resizing = false
      document.removeEventListener('mousemove', this._onResizeMove)
      document.removeEventListener('mouseup', this._onResizeStop)
      this._onResizeMove = null
      this._onResizeStop = null
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
    },

    resetEditorHeight() {
      this.editorMinHeight = null
      this.syncLeftHeight()
    },

    toggleFullscreen() {
      this.editorFullscreen = !this.editorFullscreen
    },

    async queryData() {
      // only fetch the data the parent did not already provide via
      // props; when all three props are set (the normal case when this
      // component is hosted by job_submit.vue), zero API calls are made
      // here and the page renders instantly from the parent's cache
      const fetchers = []
      if (!this.versionData) fetchers.push(this.fetchVersion())
      if (!this.devicesDetails) fetchers.push(this.fetchDevices())
      if (!this.flavorOptions) fetchers.push(this.fetchFlavors())
      if (fetchers.length > 0) {
        await Promise.all(fetchers)
      }
      // NOTE: do NOT pass `enable: true` here -- disabled devices must still
      // appear in the dropdown (as non-selectable entries) so the user can
      // see them and inspect their details via tooltip
      this.devices = filterDevices(
        this.effectiveVersionData,
        this.effectiveDevicesDetails,
        {
          'code_types': ['qubo']
        }
      )
      // default backend selection: prefer the first selectable device whose
      // tech_type is generic_simulator; fall back to the first selectable
      // device overall; fall back to empty when nothing is selectable
      const preferred = this.pickDefaultBackend()
      if (preferred) {
        this.taskData.taskBackend = preferred
      } else {
        this.taskData.taskBackend = ''
      }
      // initialise transpiler selection based on the resolved backend
      this.syncTranspilerWithBackend()
      // auto-scheduling: pre-select the first flavor so the dropdown has
      // a sensible default as soon as the user switches to flavor mode
      const flavors = this.effectiveFlavorOptions
      if (!this.taskData.taskFlavor && flavors.length > 0) {
        this.taskData.taskFlavor = flavors[0].id
      }
      this.loaded = true
      this.syncLeftHeight()
    },

    // reset taskTranspiler to the driver's default transpiler for the
    // currently selected backend (which is also the first option in the
    // dropdown); falls back to the first supported transpiler when no
    // default is configured, and clears the value when nothing is
    // available so the form does not carry a stale selection
    syncTranspilerWithBackend() {
      const list = this.currentTranspilers
      if (list.length === 0) {
        this.taskData.taskTranspiler = ''
        return
      }
      const defaultName = this.currentDefaultTranspiler
      const hasDefault = defaultName && list.some(t => t.name === defaultName)
      this.taskData.taskTranspiler = hasDefault ? defaultName : list[0].name
    },

    async fetchVersion() {
      try {
        const response = await queryVersion()
        if (!response.error) {
          this.localVersionData = response.result
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
          this.localDevicesDetails = response.result
        } else {
          this.$message.error(`获取设备列表失败：${response.message || '未知错误'}`)
        }
      } catch (error) {
        console.error('获取设备列表失败:', error)
        this.$message.error('获取设备列表失败，请检查网络连接')
      }
    },

    // build tab display label: "代码N" or "代码N (filename)"
    tabLabel(tab, index) {
      const seq = index + 1
      if (tab.fromFile && tab.name) {
        return `代码${seq} (${tab.name})`
      }
      return `代码${seq}`
    },

    // Pick the default backend device: prefer the first selectable device
    // whose tech_type is generic_simulator; fall back to the first
    // selectable device overall; return empty string when nothing is
    // selectable so the form does not carry a stale selection
    pickDefaultBackend() {
      const names = Object.keys(this.devices)
      if (names.length === 0) return ''
      // first pass: find the first selectable generic_simulator device
      for (const name of names) {
        const details = this.effectiveDevicesDetails[name] || {}
        const techType = details['tech_type'] || 'unknown'
        const enabled = details['enable'] !== false
        const status = details['status'] || 'unknown'
        if (techType === 'generic_simulator' && enabled && status === 'online') {
          return name
        }
      }
      // second pass: find the first selectable device regardless of tech_type
      for (const name of names) {
        const details = this.effectiveDevicesDetails[name] || {}
        const enabled = details['enable'] !== false
        const status = details['status'] || 'unknown'
        if (enabled && status === 'online') {
          return name
        }
      }
      return ''
    },

    // Format availability rate (0-1) as a percentage string; returns '-'
    // when the value is null/undefined
    formatAvailability(rate) {
      if (rate === null || rate === undefined) return '-'
      return (rate * 100).toFixed(1) + '%'
    },

    // Build the HTML string used as the el-tooltip content for a backend
    // device option; el-option's inline template scope does not propagate
    // the v-for `device` variable into the tooltip #content slot, so the
    // tooltip HTML is built imperatively here and bound via `raw-content`;
    // inline styles are used because the tooltip popper is teleported to
    // <body> and is therefore out of scope of this component's scoped CSS
    deviceTooltipHtml(device) {
      const rows = [
        ['名称', device.name],
        ['别名', device.aliasName],
        ['路线', device.techTypeAlias],
        ['比特数', String(device.maxQubits)],
        ['状态', this.getDeviceStatusDisplay(device.status, device.isManual)],
        ['可用率', this.formatAvailability(device.availability)]
      ]
      // device metadata is trusted (returned by our own backend), so
      // simple string coercion is sufficient here; no HTML escaping needed
      const escapeHtml = (s) => String(s)
      const rowStyle = 'display:flex;align-items:center;gap:8px;line-height:1.5;'
      const labelStyle = 'font-weight:600;opacity:0.85;min-width:56px;display:inline-block;'
      const rowsHtml = rows.map(([label, value]) =>
        `<div style="${rowStyle}"><span style="${labelStyle}">${escapeHtml(label)}:</span><span>${escapeHtml(value)}</span></div>`
      ).join('')
      return `<div style="display:flex;flex-direction:column;gap:4px;font-size:12px;">${rowsHtml}</div>`
    },

    // label shown in the flavor dropdown: "name (description)" when a
    // description exists, otherwise just the name; matches the resource
    // spec list page so the same flavor renders identically everywhere
    flavorLabel(flavor) {
      const desc = (flavor && flavor.description) || ''
      return desc ? `${flavor.name} (${desc})` : (flavor ? flavor.name : '')
    },

    // Build the HTML string used as the el-tooltip content for a flavor
    // option; mirrors deviceTooltipHtml so both dropdowns share the same
    // visual language. Returns an empty string when there is no
    // description -- the tooltip is then disabled via :disabled
    flavorTooltipHtml(flavor) {
      if (!flavor || !flavor.description) return ''
      const rows = [
        ['名称', flavor.name],
        ['描述', flavor.description]
      ]
      const rowStyle = 'display:flex;align-items:flex-start;gap:8px;line-height:1.5;'
      const labelStyle = 'font-weight:600;opacity:0.85;min-width:56px;display:inline-block;'
      const rowsHtml = rows.map(([label, value]) =>
        `<div style="${rowStyle}"><span style="${labelStyle}">${label}:</span><span>${value}</span></div>`
      ).join('')
      return `<div style="display:flex;flex-direction:column;gap:4px;font-size:12px;max-width:380px;word-break:break-all;">${rowsHtml}</div>`
    },

    // CSS class for the availability badge, aligned with the tag type
    // thresholds used on the device list page
    availabilityTagClass(rate) {
      if (rate === null || rate === undefined) return 'availability-unknown'
      if (rate >= 0.9) return 'availability-high'
      if (rate >= 0.6) return 'availability-medium'
      return 'availability-low'
    },

    // 处理后端选择变更：转译器下拉列表自动刷新为该设备驱动
    // supported_transpilers 字段声明的转译器集合（driver 的默认 transpiler
    // 始终排在第一位），并把 taskTranspiler 重置为该默认值；如果新后端
    // 没有任何转译器，则把旧值清空避免残留
    handleBackendChange() {
      this.syncTranspilerWithBackend()
    },

    // 处理调度模式切换：flavor 列表已在页面加载时预取，这里只需在
    // 切到自动调度时确保有默认选中项
    handleScheduleModeChange(mode) {
      const flavors = this.effectiveFlavorOptions
      if (mode === 'flavor' && !this.taskData.taskFlavor && flavors.length > 0) {
        this.taskData.taskFlavor = flavors[0].id
      }
    },

    // 处理资源规格选择变更；后端会根据 flavor 自动调度到符合条件的设备
    handleFlavorChange(value) {
      // flavor 模式下用户无需手动选择后端设备；保留 taskBackend 字段
      // 以便切回 backend 模式时仍有上次的记忆
    },

    // 拉取 flavor 列表（资源规格），用于动态调度
    async fetchFlavors() {
      this.flavorLoading = true
      try {
        const response = await getFlavors()
        if (!response.error) {
          const flavors = response.result || {}
          this.localFlavorOptions = []
          // result is a dict keyed by flavor id
          for (const fid in flavors) {
            const f = flavors[fid]
            this.localFlavorOptions.push({
              id: f.id || fid,
              name: f.name || fid,
              // keep description so flavorLabel / flavorTooltipHtml can
              // render the same "name (description)" presentation as the
              // parent-propelled flavorOptions
              description: f.description || ''
            })
          }
          // default to the first flavor if none selected yet, so the
          // auto-scheduling dropdown is never empty after switching
          if (!this.taskData.taskFlavor && this.localFlavorOptions.length > 0) {
            this.taskData.taskFlavor = this.localFlavorOptions[0].id
          }
        } else {
          this.$message.error(`获取资源规格列表失败：${response.message || '未知错误'}`)
        }
      } catch (error) {
        console.error('获取资源规格列表失败:', error)
        this.$message.error('获取资源规格列表失败，请检查网络连接')
      } finally {
        this.flavorLoading = false
      }
    },

    // copy the last selected file name to clipboard
    async copyLastPath() {
      if (!this.lastFilePath) return
      try {
        await navigator.clipboard.writeText(this.lastFilePath)
        this.$message.success('已复制文件路径')
      } catch (error) {
        console.error('复制失败:', error)
        this.$message.error('复制失败，请手动复制')
      }
    },

    // handle file upload change -- create a qubo tab from the selected file
    handleFileChange(file) {
      // add file type validation
      const isAllowedType = file.name.endsWith('.json') || file.name.endsWith('.csv')
      if (!isAllowedType) {
        this.$message.error('只能上传json、csv格式的文件！')
        return
      }

      // add file size validation
      const isLt10M = file.size / 1024 / 1024 < 10
      if (!isLt10M) {
        this.$message.error('上传的文件大小不能超过 10MB！')
        return
      }

      // read file content and put into a new qubo tab named after the file
      if (file.raw) {
        const reader = new FileReader()
        reader.onload = (e) => {
          const content = e.target.result
          const fileName = file.name
          // remember the last selected file name for display and copy
          this.lastFilePath = fileName
          const newTabIndex = this.taskData.quboTabs.length
          this.taskData.quboTabs.push({
            name: fileName,
            code: content,
            fromFile: true
          })
          this.taskData.activeQuboTab = newTabIndex
          this.syncLeftHeight()
        }
        reader.readAsText(file.raw)
      }
    },

    // handle profiling all checkbox
    handleProfilingAll(val) {
      const keys = ['profilingQueuing', 'profilingScheduling', 'profilingDriverParse', 'profilingDriverTranspile', 'profilingCode', 'profilingDriverRun', 'profilingMachine']
      keys.forEach(key => {
        this.taskData[key] = val
      })
    },

    // switch qubo tab
    switchQuboTab(index) {
      this.taskData.activeQuboTab = index
    },

    scrollTabsLeft() {
      const scrollEl = this.$refs.tabsScroll
      if (scrollEl) {
        scrollEl.scrollBy({ left: -200, behavior: 'smooth' })
      }
    },

    scrollTabsRight() {
      const scrollEl = this.$refs.tabsScroll
      if (scrollEl) {
        scrollEl.scrollBy({ left: 200, behavior: 'smooth' })
      }
    },

    // add a new empty qubo tab
    addQuboTab() {
      const newTabIndex = this.taskData.quboTabs.length
      this.taskData.quboTabs.push({ name: '', code: '', fromFile: false })
      this.taskData.activeQuboTab = newTabIndex
      this.syncLeftHeight()
    },

    // remove a qubo tab
    removeQuboTab(index) {
      this.taskData.quboTabs.splice(index, 1)
      if (this.taskData.quboTabs.length === 0) {
        this.taskData.activeQuboTab = 0
      } else if (this.taskData.activeQuboTab >= this.taskData.quboTabs.length) {
        this.taskData.activeQuboTab = this.taskData.quboTabs.length - 1
      }
      this.syncLeftHeight()
    },

    // handle content change from monaco editor
    onEditorChange(value) {
      const tab = this.taskData.quboTabs[this.taskData.activeQuboTab]
      if (tab) {
        tab.code = value
      }
    },

    submitForm() {
      this.$refs.taskForm.validate((valid) => {
        if (!valid) {
          this.$message.error('请完善作业提交信息！')
          return
        }

        const source_codes = []

        if (this.taskData.quboTabs.length === 0) {
          this.$message.error('QUBO源代码至少有1个！')
          return
        }

        // add codes from qubo tabs only (in order)
        this.taskData.quboTabs.forEach((tab, index) => {
          if (tab.code && tab.code.trim()) {
            source_codes.push(quboParser(tab.name || `tab_${index}.json`, tab.code))
          }
        })
        if (source_codes.length === 0) {
          this.$message.error('QUBO源代码至少有1个！')
          return
        }
        this.doSubmit(source_codes)
      })
    },

    doSubmit(source_codes) {
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
          this.isSubmitting = false
          return
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
          this.isSubmitting = false
          return
        }
      }

      let paramsObj = null
      if (!isEmptyStr(this.taskData.params)) {
        try {
          paramsObj = JSON.parse(this.taskData.params.trim())
        } catch (error) {
          this.$notify.error({
            title: '作业提交失败',
            message: '代码参数格式错误，请输入合法的 JSON',
            duration: 4500
          })
          this.isSubmitting = false
          return
        }
      }

      let optionsObj = null
      if (!isEmptyStr(this.taskData.options)) {
        try {
          optionsObj = JSON.parse(this.taskData.options.trim())
        } catch (error) {
          this.$notify.error({
            title: '作业提交失败',
            message: '作业选项格式错误，请输入合法的 JSON',
            duration: 4500
          })
          this.isSubmitting = false
          return
        }
      }

      // extra_specs -- optional JSON dict with scheduling overrides, only
      // allowed when scheduleMode === 'flavor' (mutually exclusive with
      // backend on the server side). Parsed early so a malformed payload
      // fails fast before any submit request is issued
      let extraSpecsObj = null
      if (this.taskData.scheduleMode === 'flavor' && !isEmptyStr(this.taskData.extraSpecs)) {
        try {
          extraSpecsObj = JSON.parse(normalizeJsonInput(this.taskData.extraSpecs))
        } catch (error) {
          this.$notify.error({
            title: '作业提交失败',
            message: '额外调度参数格式错误，请输入合法的 JSON',
            duration: 4500
          })
          this.isSubmitting = false
          return
        }
      }

      let circuitAggregation = null
      if (this.taskData.circuitAggregation !== 'none') {
        circuitAggregation = this.taskData.circuitAggregation
      }

      const profiling = []
      if (this.taskData.profilingAll) {
        profiling.push('all')
      }
      if (this.taskData.profilingQueuing) {
        profiling.push('queuing')
      }
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
      if (this.taskData.profilingMachine) {
        profiling.push('machine')
      }

      const requestData = {
        source_code: source_codes,
        // use the code type selected in the parent page (qubo)
        code_type: this.codeType,
        job_name: this.taskData.taskName,
        description: this.taskData.taskDescription,
        job_type: 'sampling',
        job_sched_policy: 'time_precedence',
        job_priority: this.taskData.taskPriority,
        driver_options: driverOptions,
        transpiler: this.taskData.taskTranspiler,
        transpiler_options: transpilerOptions,
        circuit_aggregation: circuitAggregation,
        profiling: profiling,
        dry_run: this.taskData.taskDryRun,
        shots: this.taskData.shotCount,
        params: paramsObj,
        options: optionsObj
      }

      // backend vs flavor_id are mutually exclusive on the server side;
      // pick the right field based on the user's scheduling mode
      if (this.taskData.scheduleMode === 'flavor') {
        requestData.flavor_id = this.taskData.taskFlavor
        if (extraSpecsObj) {
          requestData.extra_specs = extraSpecsObj
        }
      } else {
        requestData.backend = this.taskData.taskBackend
      }

      submitJob(requestData)
        .then((response) => {
          if (!response.error) {
            this.$notify({
              title: '作业提交成功',
              message: '作业已成功启动',
              type: 'success',
              duration: 2000
            })
            this.$router.push({ path: '/jobs/', query: { highlight: response.result.job_id }})
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
    },

    resetForm() {
      this.$refs.taskForm.resetFields()
      this.taskData.quboTabs = []
      this.taskData.activeQuboTab = 0
      // clear the last file path display
      this.lastFilePath = ''
      this.editorMinHeight = null
      this.syncLeftHeight()
    }
  }
}
</script>

<style scoped>
.task-submit-container {
  display: flex;
  flex-direction: column;
  background: var(--el-fill-color-light);
  padding: 20px;
}

.header {
  margin: 0;
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  margin-bottom: 10px;
}
.header-actions {
  padding-bottom: 5px;
}

.form-container {
  flex: 1;
  background: var(--el-bg-color);
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

.last-file-hint {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 8px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.last-file-path {
  max-width: 220px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.copy-btn {
  padding: 0;
  height: auto;
}

.el-form-item {
  margin-bottom: 25px;
}
.inline-form-row {
  display: flex;
  flex-wrap: nowrap;
  align-items: flex-start;
  width: 100%;
}
.inline-form-col {
  flex: 1 1 50%;
  min-width: 0;
  display: flex;
  align-items: flex-start;
}
.inline-form-left {
  justify-content: flex-start;
}
.inline-form-right {
  justify-content: flex-end;
}
.inline-form-item {
  display: inline-flex;
  width: auto;
  vertical-align: bottom;
  flex-shrink: 0;
}

.el-button {
  margin-right: 15px;
}

.auto-width {
  min-width: 350px;
  text-align: start;
}

/* backend device option row with a leading status dot */
.device-option-row {
  display: flex;
  align-items: center;
  gap: 6px;
}

.device-state-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
  background: var(--el-color-info);
}

/* status colors aligned with getDeviceStatusTagType in common/library.js */
.device-state-dot.state-online {
  background: var(--el-color-success);
}

.device-state-dot.state-offline {
  background: var(--el-color-info);
}

.device-state-dot.state-busy,
.device-state-dot.state-calibrating,
.device-state-dot.state-maintain {
  background: var(--el-color-warning);
}

.device-state-dot.state-disconnected {
  background: var(--el-color-danger);
}

.device-state-dot.state-unknown {
  background: var(--el-color-info);
}

.device-option-row .device-name,
.device-option-row .device-qubits {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

/* availability badge inside the backend device option row: icon + small
   percentage text; colours follow the same thresholds as the device list
   page (>=90% success, >=60% warning, else danger) */
.device-availability {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  margin-left: 4px;
  font-size: 11px;
  line-height: 1;
}

.device-availability-icon {
  font-size: 11px;
}

.device-availability-value {
  font-size: 11px;
}

.device-availability.availability-high {
  color: var(--el-color-success);
}

.device-availability.availability-medium {
  color: var(--el-color-warning);
}

.device-availability.availability-low {
  color: var(--el-color-danger);
}

.device-availability.availability-unknown {
  color: var(--el-color-info);
}

/* disabled device option: dim the whole row so it looks non-selectable */
.backend-device-option.is-disabled .device-option-row {
  opacity: 0.5;
}

/* tooltip content for the backend device option hover card */
.device-tooltip {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.device-tooltip-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.device-tooltip-label {
  font-weight: 600;
  color: var(--el-text-color-secondary);
  min-width: 56px;
}

.device-tooltip-value {
  color: var(--el-text-color-primary);
}

/* main row -- stretch both columns to equal height */
.qasm-main-row {
  align-items: stretch;
}

/* tabs and Monaco editor */
.qasm-form-item {
  margin-bottom: 0;
}

.qasm-tabs-container {
  width: 100%;
  display: flex;
  flex-direction: column;
}

.qasm-tabs-header {
  display: flex;
  align-items: stretch;
  background: #f0f2f5;
  border: 1px solid var(--el-border-color);
  border-bottom: none;
  border-radius: 4px 4px 0 0;
  padding: 0;
  height: 30px;
  overflow: hidden;
}

.qasm-tabs-scroll {
  display: flex;
  align-items: stretch;
  flex: 1;
  overflow-x: auto;
  overflow-y: hidden;
  scrollbar-width: none;
  -ms-overflow-style: none;
}

.qasm-tabs-scroll::-webkit-scrollbar {
  display: none;
}

.qasm-tab {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  cursor: pointer;
  font-size: 12px;
  color: var(--el-text-color-regular);
  background: var(--el-fill-color);
  border-right: 1px solid #dcdfe6;
  max-width: 240px;
  flex-shrink: 0;
  white-space: nowrap;
  transition: background 0.2s, color 0.2s;
}
.qasm-tab:hover {
  background: var(--el-fill-color-light);
  color: var(--el-text-color-primary);
}
.qasm-tab.active {
  background: var(--el-bg-color);
  color: var(--el-text-color-primary);
  font-weight: 600;
}

.qasm-tab-icon {
  font-size: 12px;
  color: #409eff;
  flex-shrink: 0;
}

.qasm-tab-label {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 180px;
}

.qasm-tab-close {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 14px;
  height: 14px;
  font-size: 12px;
  line-height: 1;
  border-radius: 50%;
  color: var(--el-text-color-secondary);
  flex-shrink: 0;
  margin-left: 2px;
}
.qasm-tab-close:hover {
  background: #f56c6c;
  color: #ffffff;
}

.qasm-tab-add {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  font-size: 16px;
  cursor: pointer;
  color: var(--el-text-color-regular);
  border-left: 1px solid #dcdfe6;
  flex-shrink: 0;
  transition: background 0.2s, color 0.2s;
}
.qasm-tab-add:hover {
  background: #f0f7ff;
  color: #409eff;
}

.qasm-tab-scroll-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  font-size: 14px;
  cursor: pointer;
  color: var(--el-text-color-secondary);
  flex-shrink: 0;
  user-select: none;
  transition: background 0.2s, color 0.2s;
}
.qasm-tab-scroll-btn:hover {
  background: var(--el-fill-color-dark);
  color: #409eff;
}

.qasm-monaco-wrapper {
  border: 1px solid var(--el-border-color);
  border-top: none;
  overflow: hidden;
  width: 100%;
  box-sizing: border-box;
  position: relative;
}
q
.qasm-monaco-editor {
  width: 100%;
  height: 100%;
}

.qasm-empty-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: 12px;
  color: var(--el-text-color-secondary);
  user-select: none;
}
.qasm-empty-icon {
  font-size: 48px;
  color: #c0c4cc;
}
.qasm-empty-text {
  font-size: 14px;
  color: var(--el-text-color-secondary);
  margin: 0;
}
.qasm-empty-plus {
  display: inline-block;
  font-size: 18px;
  color: #409eff;
  font-weight: 700;
}

.qasm-resize-handle {
  height: 8px;
  cursor: ns-resize;
  background: #f0f2f5;
  border: 1px solid var(--el-border-color);
  border-top: none;
  border-radius: 0 0 4px 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: background 0.2s;
}
.qasm-resize-handle:hover {
  background: #e6f0ff;
}
.qasm-resize-grip {
  display: block;
  width: 36px;
  height: 3px;
  background: #c0c4cc;
  border-radius: 2px;
  transition: background 0.2s;
}
.qasm-resize-handle:hover .qasm-resize-grip {
  background: #409eff;
}
.qasm-fullscreen-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  font-size: 14px;
  cursor: pointer;
  color: var(--el-text-color-secondary);
  border-left: 1px solid #dcdfe6;
  flex-shrink: 0;
  user-select: none;
  transition: background 0.2s, color 0.2s;
}
.qasm-fullscreen-btn:hover {
  background: var(--el-fill-color-dark);
  color: #409eff;
}

.qasm-fullscreen {
  z-index: 2000;
}
</style>

  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: background 0.2s;
}
.qasm-resize-handle:hover {
  background: #e6f0ff;
}
.qasm-resize-grip {
  display: block;
  width: 36px;
  height: 3px;
  background: #c0c4cc;
  border-radius: 2px;
  transition: background 0.2s;
}
.qasm-resize-handle:hover .qasm-resize-grip {
  background: #409eff;
}
.qasm-fullscreen-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  font-size: 14px;
  cursor: pointer;
  color: var(--el-text-color-secondary);
  border-left: 1px solid #dcdfe6;
  flex-shrink: 0;
  user-select: none;
  transition: background 0.2s, color 0.2s;
}
.qasm-fullscreen-btn:hover {
  background: var(--el-fill-color-dark);
  color: #409eff;
}
