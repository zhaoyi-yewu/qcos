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
  <div class="job-submit-container" :class="{ 'is-embedded': embedded }">
    <div v-if="!embedded" class="header">
      <h2>作业提交</h2>
    </div>
    <div class="code-type-selector">
      <el-form label-width="120px" label-position="right">
        <el-form-item required>
          <template #label><span class="selector-label">作业种类</span></template>
          <div class="selector-row">
            <div class="selector-group">
              <el-select
                v-model="jobCatalog"
                placeholder="请选择作业种类"
                style="width: 240px"
                :loading="catalogLoading"
                @change="onJobCatalogChange"
              >
                <el-option
                  v-for="item in jobCatalogOptions"
                  :key="item.value"
                  :label="item.label"
                  :value="item.value"
                />
              </el-select>
              <span class="selector-label"><span class="required-star">*</span>源代码类型</span>
              <el-select
                v-model="codeType"
                placeholder="请选择源代码类型"
                style="width: 200px"
                :disabled="codeTypeOptions.length === 0"
                @change="onCodeTypeChange"
              >
                <el-option
                  v-for="item in codeTypeOptions"
                  :key="item.value"
                  :label="item.label"
                  :value="item.value"
                />
              </el-select>
            </div>
            <div class="header-actions">
              <el-button type="primary" @click="handleSubmit">提交作业</el-button>
              <el-button @click="handleReset">重置</el-button>
            </div>
          </div>
        </el-form-item>
      </el-form>
    </div>
    <div class="submit-content">
      <component
        :is="currentComponent"
        ref="submitComp"
        :key="codeType"
        :code-type="codeType"
        :version-data="sharedVersionData"
        :devices-details="sharedDevicesDetails"
        :flavor-options="sharedFlavorOptions"
      />
    </div>
  </div>
</template>

<script>
import { markRaw } from 'vue'
import QasmSubmit from './qasm.vue'
import QuboSubmit from './qubo.vue'
import { queryVersion } from '@/api/version'
import { getDevices } from '@/api/device'
import { getFlavors } from '@/api/flavor'

// Code types that should use the QUBO matrix submit page
const QUBO_CODE_TYPES = ['qubo']

export default {
  name: 'JobSubmit',
  components: {
    QasmSubmit,
    QuboSubmit
  },
  props: {
    // when true, the page is rendered inside a dialog and the inner
    // header/padding are hidden to avoid duplication with the dialog
    embedded: {
      type: Boolean,
      default: false
    }
  },
  data() {
    return {
      jobCatalog: '',
      codeType: '',
      currentComponent: null,
      // raw job_catalogs map from version capabilities, kept as-is so the
      // code_types cascade can be derived without re-fetching
      jobCatalogs: {},
      jobCatalogOptions: [],
      codeTypeOptions: [],
      catalogLoading: false,
      // shared page-level data fetched once on entry and forwarded to the
      // inner QASM/QUBO submit component via props, so child components
      // do not need to call the version/devices/flavors APIs again --
      // opening the submit page therefore triggers exactly one request
      // per upstream endpoint regardless of catalog/code-type switches
      sharedVersionData: null,
      sharedDevicesDetails: null,
      sharedFlavorOptions: null
    }
  },
  created() {
    this.fetchAllData()
  },
  methods: {
    // Fetch all upstream data (version capabilities, device list, flavor
    // list) exactly once on page entry, in parallel; the results are
    // stored on shared* data fields and forwarded to the active child
    // submit component as props, eliminating duplicate API calls when
    // the user switches job catalog or code type
    async fetchAllData() {
      this.catalogLoading = true
      try {
        const [versionResp, devicesResp, flavorsResp] = await Promise.all([
          queryVersion(),
          getDevices(),
          getFlavors()
        ])
        // version -- required for job catalogs + driver/transpiler mapping
        if (versionResp && !versionResp.error) {
          this.sharedVersionData = versionResp.result
        } else {
          this.$message.error(`获取版本能力失败：${(versionResp && versionResp.message) || '未知错误'}`)
        }
        // devices -- forwarded to child components for backend dropdown
        if (devicesResp && !devicesResp.error) {
          this.sharedDevicesDetails = devicesResp.result || {}
        } else {
          this.$message.error(`获取设备列表失败：${(devicesResp && devicesResp.message) || '未知错误'}`)
        }
        // flavors -- forwarded to child components for auto-scheduling
        if (flavorsResp && !flavorsResp.error) {
          const raw = flavorsResp.result || {}
          const list = []
          for (const fid in raw) {
            const f = raw[fid] || {}
            // carry the description so the dropdown can render
            // "name (description)" labels and tooltips; falls back to
            // empty string when the flavor has no description
            list.push({
              id: f.id || fid,
              name: f.name || fid,
              description: f.description || ''
            })
          }
          this.sharedFlavorOptions = list
        } else {
          this.$message.error(`获取资源规格列表失败：${(flavorsResp && flavorsResp.message) || '未知错误'}`)
        }
        // build the job catalog options from the version capabilities
        this.buildJobCatalogOptions()
      } catch (error) {
        console.error('获取作业提交初始化数据失败:', error)
        this.$message.error('获取作业提交初始化数据失败，请检查网络连接')
      } finally {
        this.catalogLoading = false
      }
    },

    // Build the job catalog dropdown from the cached versionData; catalogs
    // with empty/null code_types are hidden from the dropdown
    buildJobCatalogOptions() {
      const capabilities = (this.sharedVersionData && this.sharedVersionData.capabilities) || {}
      const catalogs = capabilities.job_catalogs || {}
      this.jobCatalogs = catalogs
      this.jobCatalogOptions = []
      for (const key in catalogs) {
        const item = catalogs[key] || {}
        const codeTypes = item.code_types
        // skip catalogs with null/empty code_types -- nothing runnable
        if (!Array.isArray(codeTypes) || codeTypes.length === 0) {
          continue
        }
        this.jobCatalogOptions.push({
          value: key,
          label: item.alias_name || key,
          codeTypes: codeTypes
        })
      }
      // default to the first available catalog + its first code type
      if (this.jobCatalogOptions.length > 0) {
        const first = this.jobCatalogOptions[0]
        this.jobCatalog = first.value
        this.setCodeTypeOptions(first.codeTypes)
      }
    },

    // Rebuild the code type dropdown options for the given code_types
    // list, then pick the first one as default and resolve the page;
    // the label is the raw code_type string from the version API
    setCodeTypeOptions(codeTypes) {
      this.codeTypeOptions = (codeTypes || []).map(ct => ({
        value: ct,
        label: ct
      }))
      if (this.codeTypeOptions.length > 0) {
        this.codeType = this.codeTypeOptions[0].value
      } else {
        this.codeType = ''
      }
      this.currentComponent = this.codeType
        ? markRaw(this.resolveComponent(this.codeType))
        : null
    },

    // Resolve the submit page component for a given code type
    resolveComponent(codeType) {
      if (QUBO_CODE_TYPES.includes(codeType)) {
        return QuboSubmit
      }
      // QASM code types (and any unknown type) fall back to OpenQASM page
      return QasmSubmit
    },

    onJobCatalogChange(val) {
      const opt = this.jobCatalogOptions.find(o => o.value === val)
      this.setCodeTypeOptions(opt ? opt.codeTypes : [])
    },

    onCodeTypeChange(val) {
      this.currentComponent = val
        ? markRaw(this.resolveComponent(val))
        : null
    },

    handleSubmit() {
      const comp = this.$refs.submitComp
      if (comp && typeof comp.submitForm === 'function') {
        comp.submitForm()
      }
    },

    handleReset() {
      const comp = this.$refs.submitComp
      if (comp && typeof comp.resetForm === 'function') {
        comp.resetForm()
      }
    }
  }
}
</script>

<style scoped>
.job-submit-container {
  display: flex;
  flex-direction: column;
  background: var(--el-fill-color-light);
  padding: 20px;
  box-sizing: border-box;
}

/* when embedded inside a dialog, drop the outer padding and background
   so the dialog body padding takes effect and the page blends in */
.job-submit-container.is-embedded {
  padding: 0;
  background: transparent;
}

.header {
  margin: 0;
}

.code-type-selector {
  background: var(--el-bg-color);
  border-radius: 8px;
  padding: 15px 20px;
  margin-bottom: 0;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.05);
}

.code-type-selector :deep(.el-form-item) {
  margin-bottom: 0;
}

.selector-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}

.selector-group {
  display: flex;
  align-items: center;
  gap: 12px;
}

/* bold label consistent with other form labels in submit pages */
.selector-label {
  font-weight: 700;
  color: var(--el-text-color-regular);
  font-size: 14px;
  white-space: nowrap;
}

/* red asterisk for required fields, matching element-plus default color */
.required-star {
  color: #f56c6c;
  margin-right: 4px;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.submit-content {
  flex: 1;
  /* add spacing between the code type selector and the inner submit page */
  margin-top: 16px;
}

/* override inner page container padding since outer already has padding */
.submit-content :deep(.task-submit-container) {
  padding: 0;
  background: transparent;
}
</style>
