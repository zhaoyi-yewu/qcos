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
  <div class="logs-panel">
    <!-- Toolbar -->
    <div class="logs-toolbar">
      <el-select
        v-model="timeRange"
        size="small"
        class="time-range-select"
        @change="onSearch"
      >
        <el-option
          v-for="opt in TIME_RANGE_OPTIONS"
          :key="opt.value"
          :label="opt.label"
          :value="opt.value"
        />
      </el-select>

      <el-input
        v-model="keyword"
        size="small"
        placeholder="关键字搜索（任意字段模糊匹配，支持 * 通配符）"
        class="keyword-input"
        clearable
        @keyup.enter="onSearch"
        @clear="onSearch"
      >
        <template #append>
          <el-button size="small" :loading="loading" @click="onSearch">
            查询
          </el-button>
        </template>
      </el-input>

      <el-tag size="small" type="info" class="total-tag">共 {{ total }} 条</el-tag>

      <el-button
        size="small"
        :icon="Refresh"
        circle
        :loading="loading"
        @click="onSearch"
      />
    </div>

    <!-- Log table -->
    <div class="logs-table-wrapper">
      <el-table
        v-loading="loading"
        :data="logs"
        size="small"
        stripe
        border
        height="100%"
        :header-cell-style="headerCellStyle"
        :default-sort="defaultSort"
        @sort-change="onSortChange"
        @header-dragend="onHeaderDragEnd"
      >
        <el-table-column
          v-for="col in columns"
          :key="col.prop"
          :prop="col.prop"
          :label="col.label"
          :width="col.width"
          :sortable="col.sortable"
          :show-overflow-tooltip="col.showOverflowTooltip !== false"
        >
          <template #header>
            <span class="lp-header">
              <span class="lp-label">{{ col.label }}</span>
              <el-popover
                v-if="col.filterable !== false"
                v-model:visible="col.popoverVisible"
                placement="bottom-start"
                trigger="click"
                :width="col.filterType === 'select' ? 220 : 240"
                popper-class="lp-filter-popover"
              >
                <template #reference>
                  <el-button
                    link
                    class="lp-filter-icon"
                    :class="{ 'lp-filter-active': isFilterActive(col.prop) }"
                    :icon="Filter"
                    @click.stop
                  />
                </template>
                <div class="lp-filter-panel">
                  <!-- select-type filter: pick one of a fixed list -->
                  <el-select
                    v-if="col.filterType === 'select'"
                    v-model="col.filterValue"
                    size="small"
                    clearable
                    :placeholder="`过滤：${col.label}`"
                    style="width: 100%"
                  >
                    <el-option
                      v-for="opt in col.filterOptions"
                      :key="opt.value"
                      :label="opt.label"
                      :value="opt.value"
                    />
                  </el-select>
                  <!-- text-type filter: free-form input -->
                  <el-input
                    v-else
                    v-model="col.filterValue"
                    :placeholder="`过滤：${col.label}`"
                    clearable
                    size="small"
                    @keyup.enter="applyColumnFilter(col)"
                  />
                  <div class="lp-filter-actions">
                    <el-button size="small" @click="clearColumnFilter(col)">
                      清除
                    </el-button>
                    <el-button
                      size="small"
                      type="primary"
                      @click="applyColumnFilter(col)"
                    >
                      确定
                    </el-button>
                  </div>
                </div>
              </el-popover>
            </span>
          </template>

          <template #default="scope">
            <!-- time -->
            <template v-if="col.prop === '_time'">
              {{ formatTime(scope.row._time || scope.row.ts) }}
            </template>
            <!-- tag (category) -->
            <template v-else-if="col.prop === 'tag'">
              <el-tag
                :type="getTagType(scope.row.tag)"
                size="small"
                effect="plain"
              >
                {{ tagLabel(scope.row.tag) }}
              </el-tag>
            </template>
            <!-- level -->
            <template v-else-if="col.prop === 'level'">
              <el-tag
                :type="getLevelTagType(scope.row.level)"
                size="small"
              >
                {{ scope.row.level || '-' }}
              </el-tag>
            </template>
            <!-- source file (basename) -->
            <template v-else-if="col.prop === 'file'">
              {{ formatFileName(scope.row.file) }}
            </template>
            <!-- message -->
            <template v-else-if="col.prop === 'msg'">
              {{ scope.row._msg || scope.row.msg || scope.row._raw || scope.row.log || '-' }}
            </template>
            <!-- default: plain field -->
            <template v-else>
              {{ scope.row[col.prop] || '-' }}
            </template>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="80" fixed="right">
          <template #default="scope">
            <el-button
              size="small"
              text
              type="primary"
              @click.stop="onRowClick(scope.row)"
            >
              详情
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- Pagination: left = pager buttons (PageTable style), right = total
         count + page-size selector, mirroring the alerts PageTable row. -->
    <div class="logs-pagination">
      <div class="logs-pagination-left">
        <el-pagination
          background
          size="small"
          layout="prev, pager, next"
          :total="total"
          :current-page="currentPage"
          @current-change="onPageChange"
        />
      </div>
      <div class="logs-pagination-right">
        <span class="logs-total-count">共 {{ total }} 条</span>
        <el-select
          :model-value="pageSize"
          size="small"
          class="logs-page-size-select"
          @change="onPageSizeChange"
        >
          <el-option
            v-for="size in [20, 50, 100, 200]"
            :key="size"
            :label="`${size} 条/页`"
            :value="size"
          />
        </el-select>
      </div>
    </div>

    <!-- Detail drawer -->
    <el-drawer
      v-model="drawerVisible"
      title="日志详情"
      size="600px"
      destroy-on-close
    >
      <div class="log-detail-json">
        <pre>{{ JSON.stringify(selectedLog, null, 2) }}</pre>
      </div>
    </el-drawer>
  </div>
</template>

<script>
import { Refresh, Filter } from '@element-plus/icons-vue'
import { queryLogs, parseNdjson, formatLogTime } from '@/api/logs'

const TIME_RANGE_OPTIONS = [
  { label: '近 15 分钟', value: 15 * 60 },
  { label: '近 30 分钟', value: 30 * 60 },
  { label: '近 1 小时', value: 60 * 60 },
  { label: '近 6 小时', value: 6 * 60 * 60 },
  { label: '近 24 小时', value: 24 * 60 * 60 },
  { label: '近 7 天', value: 7 * 24 * 60 * 60 }
]

// Log categories emitted by fluent-bit INPUT tags. Each INPUT has a
// dedicated record_modifier FILTER that materialises the short key as the
// `tag` record field, so the value stored in VictoriaLogs is exactly one
// of the values below.
const TAG_OPTIONS = [
  { label: 'API 服务', value: 'api' },
  { label: '设备作业', value: 'device' },
  { label: '设备监控', value: 'device_monitor' },
  { label: '设备管理', value: 'device_manager' }
]

const LEVEL_OPTIONS = [
  { label: 'DEBUG', value: 'DEBUG' },
  { label: 'INFO', value: 'INFO' },
  { label: 'WARNING', value: 'WARNING' },
  { label: 'ERROR', value: 'ERROR' },
  { label: 'CRITICAL', value: 'CRITICAL' },
  { label: 'PERF', value: 'PERF' },
  // emitted by the fluent-bit fallback FILTER when the parser regex
  // didn't match (uvicorn access lines, tracebacks, empty lines, etc.)
  { label: 'UNKNOWN', value: 'UNKNOWN' }
]

/**
 * Build the column schema. Each column declares:
 *   prop                  -- record field name (also used for sort)
 *   label                 -- column header text
 *   width                 -- column width (undefined = auto)
 *   sortable              -- 'custom' = backend-driven sort via LogSQL
 *   filterType            -- 'text' | 'select'
 *   filterOptions         -- for 'select', the dropdown options
 *   filterField           -- the LogSQL field name to filter on (defaults to prop)
 *   filterOp              -- how to build the LogSQL predicate:
 *                              'exact'    → field:"value"
 *                              'contains' → field:"*value*"
 *   showOverflowTooltip   -- forwarded to el-table-column
 */
function buildColumns() {
  const columns = [
    {
      prop: '_time',
      label: '时间',
      width: 170,
      sortable: 'custom',
      // time-column filter is rarely useful (the time-range picker covers
      // it); disable the filter icon for this column
      filterable: false,
      showOverflowTooltip: false
    },
    {
      prop: 'tag',
      label: '分类标签',
      width: 110,
      sortable: 'custom',
      filterType: 'select',
      filterOptions: TAG_OPTIONS,
      filterField: 'tag',
      filterOp: 'exact',
      filterValue: '',
      popoverVisible: false,
      showOverflowTooltip: false
    },
    {
      prop: 'level',
      label: '级别',
      width: 100,
      sortable: 'custom',
      filterType: 'select',
      filterOptions: LEVEL_OPTIONS,
      filterField: 'level',
      filterOp: 'exact',
      filterValue: '',
      popoverVisible: false,
      showOverflowTooltip: false
    },
    {
      prop: 'file',
      label: '来源文件',
      width: 180,
      sortable: 'custom',
      filterType: 'text',
      filterField: 'file',
      filterOp: 'contains',
      filterValue: '',
      popoverVisible: false
    },
    {
      prop: 'hostname',
      label: '主机',
      width: 130,
      sortable: 'custom',
      filterType: 'text',
      filterField: 'hostname',
      filterOp: 'contains',
      filterValue: '',
      popoverVisible: false
    },
    {
      prop: 'module',
      label: '模块',
      width: 160,
      sortable: 'custom',
      filterType: 'text',
      filterField: 'module',
      filterOp: 'contains',
      filterValue: '',
      popoverVisible: false
    },
    {
      prop: 'msg',
      label: '消息内容',
      width: undefined,
      sortable: false,
      filterType: 'text',
      filterField: '_msg',
      filterOp: 'contains',
      filterValue: '',
      popoverVisible: false
    }
  ]
  // Restore user-adjusted column widths (saved by onHeaderDragEnd) so
  // both LogsPanel instances share the same layout across reloads.
  try {
    const saved = JSON.parse(localStorage.getItem('monitor-center-logs-columns') || '{}')
    for (const col of columns) {
      if (saved[col.prop]) {
        col.width = saved[col.prop]
      }
    }
  } catch (e) {
    console.error('Failed to restore column widths:', e)
  }
  return columns
}

export default {
  name: 'LogsPanel',
  props: {
    // Optional auto-refresh interval in seconds (0 = disabled). The
    // overview monitor-center grid embeds this panel and passes the
    // shared refresh interval so log entries stay in sync with the
    // other overview panels.
    autoRefresh: {
      type: Number,
      default: 0
    }
  },
  data() {
    return {
      Refresh,
      Filter,
      TIME_RANGE_OPTIONS,
      timeRange: 30 * 60,
      keyword: '',
      columns: buildColumns(),
      // server-side sort state, mirrors Element Plus's sort-change event:
      // {prop, order} where order is 'ascending' | 'descending' | null
      sortProp: '_time',
      sortOrder: 'descending',
      logs: [],
      total: 0,
      currentPage: 1,
      pageSize: 50,
      loading: false,
      drawerVisible: false,
      selectedLog: {}
    }
  },
  computed: {
    headerCellStyle() {
      return { background: 'var(--el-fill-color-light)' }
    },
    // Element Plus default-sort descriptor, kept in sync with the initial
    // sort state so the time column shows a descending caret on mount
    defaultSort() {
      return { prop: this.sortProp, order: this.sortOrder }
    }
  },
  watch: {
    // Re-arm the auto-refresh timer when the parent changes the
    // interval (e.g. the user picks a new refresh cadence in the
    // monitor-center header).
    autoRefresh(seconds) {
      if (this._autoRefreshTimer) {
        clearInterval(this._autoRefreshTimer)
        this._autoRefreshTimer = null
      }
      if (seconds > 0) {
        this._autoRefreshTimer = setInterval(() => {
          this.fetchLogs()
        }, seconds * 1000)
      }
    }
  },
  mounted() {
    this.onSearch()
    // Optional periodic auto-refresh (used when embedded in the
    // monitor-center overview grid). Re-runs the current query silently
    // so new log entries appear without user interaction.
    if (this.autoRefresh > 0) {
      this._autoRefreshTimer = setInterval(() => {
        this.fetchLogs()
      }, this.autoRefresh * 1000)
    }
  },

  beforeUnmount() {
    if (this._autoRefreshTimer) {
      clearInterval(this._autoRefreshTimer)
      this._autoRefreshTimer = null
    }
  },
  methods: {
    formatTime: formatLogTime,

    /** Map a fluent-bit tag value to its Chinese display label. */
    tagLabel(tag) {
      if (!tag) return '-'
      const short = String(tag).startsWith('qcos.')
        ? String(tag).slice(5)
        : String(tag)
      const hit = TAG_OPTIONS.find(o => o.value === short)
      return hit ? hit.label : short
    },

    /** Element Plus tag color per log category. */
    getTagType(tag) {
      if (!tag) return 'info'
      const short = String(tag).startsWith('qcos.')
        ? String(tag).slice(5)
        : String(tag)
      const map = {
        api: 'primary',
        device: 'success',
        device_monitor: 'warning',
        device_manager: 'danger'
      }
      return map[short] || 'info'
    },

    getLevelTagType(level) {
      const map = {
        DEBUG: 'info',
        INFO: 'success',
        PERF: 'success',
        WARNING: 'warning',
        ERROR: 'danger',
        CRITICAL: 'danger',
        // UNKNOWN is the sentinel written by fluent-bit's fallback FILTER
        // when the parser regex didn't match (uvicorn access lines,
        // tracebacks, empty lines, etc.)
        UNKNOWN: 'info'
      }
      return map[level] || 'info'
    },

    /**
     * Shorten a log source file path to its basename for the table
     * column. The full path stays visible in the detail drawer.
     */
    formatFileName(file) {
      if (!file) return '-'
      const idx = file.lastIndexOf('/')
      return idx >= 0 ? file.slice(idx + 1) : file
    },

    /**
     * Build a safe LogsQL quoted-regex value from raw user input.
     *
     * Two-layer escaping, verified against the live VictoriaLogs:
     *   layer 1 (regex): prefix RE2 metacharacters with a backslash so
     *     the user's text matches literally (leading `*` or bare `(`
     *     would otherwise be a regex syntax error -> HTTP 400);
     *   layer 2 (LogsQL string): double every backslash, because the
     *     LogsQL lexer consumes one level - the regex engine receives
     *     the single-backslash form it expects.
     *
     * Also strips newlines (LogsQL string literals must stay
     * single-line) and double quotes (would break out of the literal).
     */
    escapeLogSqlRegexValue(value) {
      // (?i) inline flag: RE2 + VictoriaLogs both accept it and it
      // makes the substring search case-insensitive (verified live).
      const regexEscaped = String(value)
        .replace(/[\r\n]/g, ' ')
        .replace(/"/g, '')
        .replace(/[.*+?^${}()|[\]\\]/g, ch => '\\' + ch)
      return '(?i)' + regexEscaped.replace(/\\/g, '\\\\')
    },

    /** Whether a column currently has a non-empty filter applied. */
    isFilterActive(prop) {
      const col = this.columns.find(c => c.prop === prop)
      return !!(col && col.filterValue && String(col.filterValue).length > 0)
    },

    applyColumnFilter(col) {
      col.popoverVisible = false
      this.currentPage = 1
      this.fetchLogs()
    },

    clearColumnFilter(col) {
      col.filterValue = ''
      col.popoverVisible = false
      this.currentPage = 1
      this.fetchLogs()
    },

    onSortChange({ prop, order }) {
      // Element Plus emits order=null when the user clicks a column the
      // third time to clear its sort; in that case fall back to the
      // default _time desc.
      if (!order) {
        this.sortProp = '_time'
        this.sortOrder = 'descending'
      } else {
        this.sortProp = prop
        this.sortOrder = order
      }
      this.currentPage = 1
      this.fetchLogs()
    },

    /**
     * Translate the current filter/sort/keyword UI state into a LogSQL
     * query. Each active column filter becomes a predicate AND-ed onto
     * the base `_stream` selector; the global keyword is a substring
     * match on the message field via the regex `~` operator; sort is
     * appended via the `| sort by` pipe.
     */
    buildLogSql() {
      // Stream-field selectors must live inside the _stream filter.
      // `tag` was promoted to a stream field (see fluent-bit
      // _stream_fields), so its filter folds into the selector;
      // regular fields become separate predicates.
      const tagCol = this.columns.find(c => c.prop === 'tag')
      const tagValue = tagCol && String(tagCol.filterValue || '').trim()
      const streamSelector = tagValue
        ? `_stream:{job="qcos", tag="${tagValue}"}`
        : '_stream:{job="qcos"}'
      const predicates = [streamSelector]
      // global keyword: substring match on the message text.
      // VictoriaLogs indexes words, so a wildcard phrase like
      // "*abc*" never matches the word index - the `~` regex operator
      // is the supported way to do substring search. NOTE: in LogsQL
      // the `~` is glued to the field name with NO surrounding
      // spaces (`_msg~"x"`); a spaced form is a parse error and the
      // server answers HTTP 400.
      if (this.keyword && this.keyword.trim()) {
        const safe = this.escapeLogSqlRegexValue(this.keyword.trim())
        predicates.push(`_msg:~"${safe}"`)
      }
      // per-column filters
      for (const col of this.columns) {
        // tag is handled inside the _stream selector above
        if (col.prop === 'tag') continue
        const v = col.filterValue
        if (v === undefined || v === null || String(v).trim() === '') continue
        const value = String(v).trim()
        if (col.filterOp === 'exact') {
          // exact -- phrase match; escape only double quotes so the
          // phrase syntax stays intact
          const safe = value.replace(/"/g, '\\"')
          predicates.push(`${col.filterField}:"${safe}"`)
        } else {
          // contains -- substring match via the `~` regex operator,
          // glued to the field name without spaces (LogsQL syntax).
          const safe = this.escapeLogSqlRegexValue(value)
          predicates.push(`${col.filterField}:~"${safe}"`)
        }
      }
      let q = predicates.join(' AND ')
      if (this.sortProp && this.sortOrder) {
        const dir = this.sortOrder === 'ascending' ? 'asc' : 'desc'
        q += ` | sort by (${this.sortProp} ${dir})`
      }
      return q
    },

    async onSearch() {
      this.currentPage = 1
      await this.fetchLogs()
    },

    async onPageChange(page) {
      this.currentPage = page
      await this.fetchLogs()
    },

    async onPageSizeChange(size) {
      this.pageSize = size
      this.currentPage = 1
      await this.fetchLogs()
    },

    async fetchLogs() {
      this.loading = true
      try {
        const end = Math.floor(Date.now() / 1000)
        const start = end - this.timeRange
        const query = this.buildLogSql()
        const offset = (this.currentPage - 1) * this.pageSize

        const response = await queryLogs({
          query,
          start: String(start),
          end: String(end),
          limit: this.pageSize,
          offset
        })

        // VictoriaLogs returns NDJSON in the response body
        const entries = parseNdjson(response)
        this.logs = entries
        // VictoriaLogs doesn't return total count in query endpoint;
        // we approximate by whether we got a full page
        this.total = entries.length === this.pageSize
          ? (this.currentPage * this.pageSize) + 1
          : ((this.currentPage - 1) * this.pageSize) + entries.length
      } catch (error) {
        console.error('查询日志失败:', error)
        this.logs = []
        this.total = 0
        const msg = (error && error.message) || ''
        if (msg.includes('功能未开启')) {
          this.$message.warning(msg)
        } else {
          this.$message.error('日志服务不可用，请检查 VictoriaLogs 是否已启动')
        }
      } finally {
        this.loading = false
      }
    },

    onRowClick(row) {
      this.selectedLog = row
      this.drawerVisible = true
    },

    /**
     * Column resize handler: write the new width back into the column
     * schema and persist it to localStorage so both LogsPanel instances
     * (overview grid + standalone logs tab) keep the user's layout.
     * Element Plus emits (newWidth, oldWidth, column); the column's
     * `property` identifies which schema entry to update.
     */
    onHeaderDragEnd(newWidth, _oldWidth, column) {
      const col = this.columns.find(c => c.prop === column.property)
      if (!col) return
      col.width = Math.round(newWidth)
      try {
        const saved = {}
        for (const c of this.columns) {
          if (c.width) saved[c.prop] = c.width
        }
        localStorage.setItem('monitor-center-logs-columns', JSON.stringify(saved))
      } catch (e) {
        console.error('Failed to save column widths:', e)
      }
    }
  }
}
</script>

<style scoped>
.logs-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 480px;
  background: var(--el-bg-color);
  border-radius: 8px;
  overflow: hidden;
}

.logs-toolbar {
  display: flex;
  gap: 8px;
  padding: 12px;
  border-bottom: 1px solid var(--el-border-color-light);
  align-items: center;
  flex-wrap: wrap;
}

.time-range-select {
  width: 140px;
}

.keyword-input {
  flex: 1;
  min-width: 240px;
}

.total-tag {
  margin-left: auto;
}

.logs-table-wrapper {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.logs-pagination {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  padding: 6px 12px;
  border-top: 1px solid var(--el-border-color-light);
}

.logs-pagination-left {
  display: flex;
  align-items: center;
}

/* vertical alignment with the right page-size selector, mirrors the
   PageTable pagination container */
.logs-pagination-left :deep(.el-pagination) {
  margin-top: 0;
}

.logs-pagination-right {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--el-text-color-regular);
}

.logs-page-size-select {
  width: 110px;
}

.log-detail-json {
  padding: 16px;
  background: var(--el-fill-color-light);
  border-radius: 4px;
  overflow: auto;
}

.log-detail-json pre {
  margin: 0;
  font-size: 12px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-all;
}
</style>

<!--
  NOT scoped: the column header slot content is rendered inside el-table's
  th, which lives outside this component's DOM subtree, so scoped styles
  would not reach the filter icon. The `lp-` prefix keeps these rules
  unique to LogsPanel.
-->
<style>
.lp-header {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  vertical-align: middle;
}

.lp-filter-icon.el-button {
  padding: 0;
  height: auto;
  min-height: 0;
  color: #909399;
  font-size: 14px;
  vertical-align: middle;
  transition: color 0.2s;
}

.lp-filter-icon.el-button:hover {
  color: #409eff;
}

.lp-filter-icon.el-button.lp-filter-active {
  color: #409eff;
}

.lp-filter-panel {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.lp-filter-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>
