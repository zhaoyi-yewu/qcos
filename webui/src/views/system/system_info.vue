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
  <div class="system-info-container">
    <div class="header">
      <h2>系统信息</h2>
      <div class="header-actions">
        <refresh-interval
          :default-interval="10"
          :refreshing="versionLoading || memLoading"
          @refresh="fetchData"
          @interval-change="onIntervalChange"
        />
      </div>
    </div>

    <!-- version info section -->
    <div class="section-container">
      <div class="section-title">版本信息</div>
      <div class="table-container version-table-container">
        <el-table
          v-loading="versionLoading"
          :data="versionTableData"
          style="width: 100%"
          border
          :header-cell-style="{ background: 'var(--el-fill-color-light)' }"
        >
          <el-table-column
            type="index"
            label="#"
            width="60"
            fixed="left"
            class-name="center-column"
          />
          <el-table-column
            prop="field"
            label="字段"
            fixed="left"
            class-name="center-column"
          >
            <template #default="scope">
              <el-icon class="field-icon"><InfoFilled /></el-icon>
              <span class="field-name">{{ scope.row.field }}</span>
            </template>
          </el-table-column>
          <el-table-column
            prop="label"
            label="说明"
            class-name="center-column"
          />
          <el-table-column
            prop="value"
            label="值"
            class-name="center-column"
          >
            <template #default="scope">
              <span v-if="scope.row.isExpandable" class="field-value-text">
                {{ scope.row.valuePreview }}
                <el-button
                  link
                  type="primary"
                  size="small"
                  @click="toggleExpand(scope.row)"
                >
                  {{ scope.row.expanded ? '收起' : '展开' }}
                </el-button>
              </span>
              <span v-else class="field-value">{{ scope.row.value }}</span>
            </template>
          </el-table-column>
        </el-table>

        <!-- expandable detail for large fields (e.g. capabilities) -->
        <el-collapse
          v-if="expandedFields.length > 0"
          v-model="activeCollapse"
          class="detail-collapse"
        >
          <el-collapse-item
            v-for="item in expandedFields"
            :key="item.field"
            :name="item.field"
            :title="`${item.field} (详细内容)`"
          >
            <pre class="json-detail">{{ item.jsonValue }}</pre>
          </el-collapse-item>
        </el-collapse>
      </div>
    </div>

    <!-- memory usage section -->
    <div class="section-container">
      <div class="section-header">
        <div class="section-title">内存占用</div>
        <div class="section-actions">
          <el-button
            type="warning"
            size="small"
            :icon="Delete"
            :loading="gcLoading"
            @click="doGcMem"
          >
            内存回收
          </el-button>
        </div>
      </div>

      <!-- GC result alert -->
      <el-alert
        v-if="gcResult"
        class="gc-result-alert"
        :title="gcResultTitle"
        type="success"
        :closable="true"
        show-icon
        @close="gcResult = null"
      >
        <div class="gc-detail">
          回收对象数：{{ gcResult.collected }}，
          不可回收：{{ gcResult.uncollectable }}，
          回收前对象总数：{{ gcResult.count_before }}，
          回收后对象总数：{{ gcResult.count_after }}，
          malloc_trim 返回值：{{ gcResult.malloc_trim_ret }}
        </div>
      </el-alert>

      <div class="overview-cards">
        <el-card class="overview-card" shadow="hover">
          <div class="overview-label">进程 PID</div>
          <div class="overview-value">{{ memInfo.pid }}</div>
        </el-card>
        <el-card class="overview-card" shadow="hover">
          <div class="overview-label">RSS 内存（MB）</div>
          <div class="overview-value primary">{{ memInfo.rss_mb }}</div>
        </el-card>
        <el-card class="overview-card" shadow="hover">
          <div class="overview-label">VMS 内存（MB）</div>
          <div class="overview-value">{{ memInfo.vms_mb }}</div>
        </el-card>
        <el-card class="overview-card" shadow="hover">
          <div class="overview-label">线程数</div>
          <div class="overview-value">{{ memInfo.thread_count }}</div>
        </el-card>
        <el-card class="overview-card" shadow="hover">
          <div class="overview-label">对象数量</div>
          <div class="overview-value">{{ memInfo.num_objects }}</div>
        </el-card>
        <el-card class="overview-card" shadow="hover">
          <div class="overview-label">CPU 占用率（%）</div>
          <div class="overview-value warning">{{ memInfo.cpu_percent }}</div>
        </el-card>
      </div>

      <div class="table-container">
        <el-table
          v-loading="memLoading"
          :data="memTableData"
          style="width: 100%"
          border
          :header-cell-style="{ background: 'var(--el-fill-color-light)' }"
        >
          <el-table-column
            type="index"
            label="#"
            width="60"
            fixed="left"
            class-name="center-column"
          />
          <el-table-column
            prop="field"
            label="字段"
            fixed="left"
            class-name="center-column"
          >
            <template #default="scope">
              <el-icon class="field-icon"><Cpu /></el-icon>
              <span class="field-name">{{ scope.row.field }}</span>
            </template>
          </el-table-column>
          <el-table-column
            prop="label"
            label="说明"
            class-name="center-column"
          />
          <el-table-column
            prop="value"
            label="值"
            class-name="center-column"
            sortable
          >
            <template #default="scope">
              <span class="field-value">{{ scope.row.value }}</span>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>
  </div>
</template>

<script>
import { markRaw } from 'vue'
import { InfoFilled, Cpu, Delete } from '@element-plus/icons-vue'
import { queryVersion } from '@/api/job'
import { showMem, gcMem } from '@/api/system'
import RefreshInterval from '@/components/RefreshInterval/index.vue'
import { ElMessageBox } from 'element-plus'

const VERSION_LABELS = {
  version: '服务端版本号',
  api_version: '当前 API 版本',
  supported_api_versions: '支持的 API 版本列表',
  platform_version: '平台版本描述',
  auth_mode: '认证模式',
  capabilities: '能力描述（内容较多，可展开查看）'
}

// threshold: if JSON string length exceeds this, show as expandable
const EXPAND_THRESHOLD = 80

const MEM_LABELS = {
  pid: '进程 ID',
  rss_mb: '实际使用物理内存（RSS，单位 MB）',
  vms_mb: '虚拟内存使用量（VMS，单位 MB）',
  thread_count: '线程数量',
  num_objects: 'Python 对象总数',
  cpu_percent: 'CPU 占用率（%）'
}

// format supported_api_versions array to readable string
function formatApiVersions(value) {
  if (!Array.isArray(value)) {
    return value
  }
  return value.map(item => {
    if (typeof item === 'object' && item !== null) {
      return `${item.version} (${item.status || 'N/A'})`
    }
    return String(item)
  }).join(', ')
}

export default {
  components: {
    RefreshInterval
  },
  data() {
    return {
      InfoFilled: markRaw(InfoFilled),
      Cpu: markRaw(Cpu),
      Delete: markRaw(Delete),
      gcLoading: false,
      gcResult: null,
      versionLoading: false,
      memLoading: false,
      versionInfo: {
        version: '',
        api_version: '',
        supported_api_versions: [],
        platform_version: '',
        auth_mode: '',
        capabilities: null
      },
      memInfo: {
        pid: 0,
        rss_mb: 0,
        vms_mb: 0,
        thread_count: 0,
        num_objects: 0,
        cpu_percent: 0
      },
      // track which expandable fields are expanded
      expandedFieldsState: {},
      // el-collapse v-model
      activeCollapse: []
    }
  },

  computed: {
    versionTableData() {
      return Object.keys(this.versionInfo).map(key => {
        const rawValue = key === 'supported_api_versions'
          ? formatApiVersions(this.versionInfo[key])
          : this.versionInfo[key]

        // check if value is large enough to be expandable
        let jsonStr = ''
        if (rawValue !== null && typeof rawValue === 'object') {
          jsonStr = JSON.stringify(rawValue, null, 2)
        } else {
          jsonStr = String(rawValue)
        }

        const isExpandable = jsonStr.length > EXPAND_THRESHOLD

        return {
          field: key,
          label: VERSION_LABELS[key] || key,
          value: isExpandable ? this.getPreviewText(rawValue) : rawValue,
          rawValue: rawValue,
          isExpandable: isExpandable,
          valuePreview: isExpandable ? this.getPreviewText(rawValue) : '',
          expanded: !!this.expandedFieldsState[key],
          jsonValue: isExpandable ? jsonStr : ''
        }
      })
    },

    // list of expanded fields for collapse display
    expandedFields() {
      return this.versionTableData.filter(item => item.isExpandable && item.expanded)
    },

    memTableData() {
      return Object.keys(this.memInfo).map(key => ({
        field: key,
        label: MEM_LABELS[key] || key,
        value: this.memInfo[key]
      }))
    },

    gcResultTitle() {
      if (!this.gcResult) return ''
      return `内存回收完成：回收了 ${this.gcResult.collected} 个对象`
    }
  },

  mounted() {
    this.fetchData()
  },

  methods: {
    async fetchData() {
      await Promise.all([
        this.fetchVersion(),
        this.fetchMem()
      ])
    },

    async fetchVersion() {
      this.versionLoading = true
      try {
        const response = await queryVersion()
        if (!response.error) {
          this.versionInfo = { ...response.result }
        } else {
          this.$message.error(`获取版本信息失败：${response.message || '未知错误'}`)
        }
      } catch (error) {
        console.error('获取版本信息失败:', error)
        this.$message.error('获取版本信息失败，请检查网络连接')
      } finally {
        this.versionLoading = false
      }
    },

    async fetchMem() {
      this.memLoading = true
      try {
        const response = await showMem()
        if (!response.error) {
          this.memInfo = { ...response.result }
        } else {
          this.$message.error(`获取内存信息失败：${response.message || '未知错误'}`)
        }
      } catch (error) {
        console.error('获取内存信息失败:', error)
        this.$message.error('获取内存信息失败，请检查网络连接')
      } finally {
        this.memLoading = false
      }
    },

    onIntervalChange() {
      this.fetchData()
    },

    // trigger garbage collection on the server
    async doGcMem() {
      try {
        await ElMessageBox.confirm(
          '确定要手动触发内存回收（GC）吗？此操作可能会短暂影响服务性能。',
          '内存回收确认',
          {
            confirmButtonText: '确定回收',
            cancelButtonText: '取消',
            type: 'warning'
          }
        )
      } catch {
        // user cancelled
        return
      }

      this.gcLoading = true
      try {
        const response = await gcMem(2)
        if (!response.error) {
          this.gcResult = response.result
          this.$message.success('内存回收成功')
          // refresh memory info after GC
          await this.fetchMem()
        } else {
          this.$message.error(`内存回收失败：${response.message || '未知错误'}`)
        }
      } catch (error) {
        console.error('内存回收失败:', error)
        this.$message.error('内存回收失败，请检查网络连接')
      } finally {
        this.gcLoading = false
      }
    },

    // toggle expand state for a large field
    toggleExpand(row) {
      this.expandedFieldsState[row.field] = !this.expandedFieldsState[row.field]
      // force reactivity by creating a new object
      this.expandedFieldsState = { ...this.expandedFieldsState }
      // sync activeCollapse with expanded fields
      if (this.expandedFieldsState[row.field]) {
        if (!this.activeCollapse.includes(row.field)) {
          this.activeCollapse.push(row.field)
        }
      } else {
        this.activeCollapse = this.activeCollapse.filter(f => f !== row.field)
      }
    },

    // get a short preview text for a large value
    getPreviewText(rawValue) {
      let str
      if (rawValue !== null && typeof rawValue === 'object') {
        str = JSON.stringify(rawValue)
      } else {
        str = String(rawValue)
      }
      if (str.length > EXPAND_THRESHOLD) {
        return str.substring(0, EXPAND_THRESHOLD) + '...'
      }
      return str
    }
  }
}
</script>

<style scoped>
.system-info-container {
  display: flex;
  flex-direction: column;
  background: var(--el-fill-color-light);
  padding: 20px;
  box-sizing: border-box;
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

.section-container {
  margin-bottom: 20px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.section-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.section-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--el-text-color-primary);
  padding-left: 10px;
  border-left: 4px solid #409eff;
}

.gc-result-alert {
  margin-bottom: 12px;
}

.gc-detail {
  font-size: 14px;
  line-height: 1.8;
  color: var(--el-text-color-primary);
}

.overview-cards {
  display: flex;
  gap: 16px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.overview-card {
  flex: 1 1 180px;
  min-width: 180px;
  text-align: center;
}

.overview-label {
  font-size: 14px;
  color: var(--el-text-color-secondary);
  margin-bottom: 8px;
}

.overview-value {
  font-size: 24px;
  font-weight: 700;
  color: var(--el-text-color-primary);
}

.overview-value.primary {
  color: #409eff;
}

.overview-value.warning {
  color: #e6a23c;
}

.table-container {
  background: var(--el-bg-color);
  border-radius: 8px;
  padding: 15px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.05);
  overflow: auto;
}

.field-icon {
  font-size: 16px;
  color: #409eff;
  vertical-align: middle;
  margin-right: 6px;
}

.field-name {
  vertical-align: middle;
  font-weight: 500;
}

.field-value {
  font-size: 16px;
  font-weight: 700;
  color: var(--el-text-color-primary);
}

/* version info table: render values without bold to match user request */
.version-table-container .field-value {
  font-weight: 400;
}
.version-table-container .field-value-text {
  font-weight: 400;
}

.field-value-text {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 15px;
  color: var(--el-text-color-primary);
}

.detail-collapse {
  margin-top: 12px;
  border: 1px solid #ebeef5;
  border-radius: 4px;
  background: #fafafa;
  padding: 0 10px;
}

.json-detail {
  margin: 0;
  padding: 10px;
  background: var(--el-fill-color-light);
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  font-family: Consolas, "Courier New", monospace;
  font-size: 13px;
  line-height: 1.6;
  color: var(--el-text-color-primary);
  white-space: pre-wrap;
  word-break: break-all;
  overflow-x: auto;
  max-height: 400px;
  overflow-y: auto;
}

:deep(.el-table) {
  font-size: 15px;
  --el-table-row-height: 30px;
}

:deep(.el-table th) {
  padding: 12px 0;
  font-size: 16px;
  text-align: center;
}

:deep(.center-column) {
  text-align: center;
}
</style>
