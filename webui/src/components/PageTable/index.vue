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
  <div class="page-table-container">
    <!-- Toolbar: search + optional actions slot -->
    <div class="table-toolbar">
      <el-input
        v-model="searchKeyword"
        :placeholder="searchPlaceholder"
        clearable
        :prefix-icon="Search"
        class="global-search"
        @input="handleSearchChange"
        @clear="handleSearchChange"
      />
      <div class="toolbar-actions">
        <slot name="toolbar-actions" />
      </div>
    </div>

    <!-- Table -->
    <div class="table-container">
      <el-table
        ref="tableRef"
        v-loading="showLoading"
        :data="tableData"
        style="width: 100%"
        border
        :header-cell-style="headerCellStyle"
        :row-key="rowKey"
        @selection-change="handleSelectionChange"
        @sort-change="handleSortChange"
      >
        <slot />
      </el-table>
    </div>

    <!-- Pagination: left=page, right=total+page-size -->
    <div class="pagination-container">
      <div class="pagination-left">
        <el-pagination
          background
          layout="prev, pager, next"
          :total="total"
          :page-size="currentPageSize"
          :current-page="currentPage"
          @current-change="handlePageChange"
        />
      </div>
      <div class="pagination-right">
        <span class="total-count">共 {{ total }} 条</span>
        <el-select
          v-model="currentPageSize"
          class="page-size-select"
          @change="handlePageSizeChange"
        >
          <el-option
            v-for="item in pageSizeOptions"
            :key="item.value"
            :label="item.label"
            :value="item.value"
          />
        </el-select>
      </div>
    </div>
  </div>
</template>

<script>
import { markRaw } from 'vue'
import { Search } from '@element-plus/icons-vue'

export default {
  name: 'PageTable',
  provide() {
    // expose a small API for FilterableTableColumn children to read/update
    // the column filter state without prop-drilling through el-table-column.
    // bind methods explicitly so that the injected callbacks keep the
    // correct `this` when invoked from a child component.
    return {
      pageTableFilter: {
        getFilter: (key) => this.getColumnFilter(key),
        setFilter: (key, value) => this.setColumnFilter(key, value)
      }
    }
  },
  props: {
    // Fetch function: (params) => Promise<{items: [], total: N}>
    // params: {page, page_size, search, filters, sort}
    fetchData: {
      type: Function,
      required: true
    },
    // Search input placeholder
    searchPlaceholder: {
      type: String,
      default: '全局搜索...'
    },
    // Default page size
    defaultPageSize: {
      type: Number,
      default: 10
    },
    // Page size options
    pageSizeOptions: {
      type: Array,
      default: () => [
        { label: '10 条/页', value: 10 },
        { label: '20 条/页', value: 20 },
        { label: '50 条/页', value: 50 },
        { label: '100 条/页', value: 100 }
      ]
    },
    // Auto fetch on mounted
    autoFetch: {
      type: Boolean,
      default: true
    },
    // row-key forwarded to el-table. Setting a stable row-key (e.g. "job_id")
    // lets Vue track row identity across refreshes, so inline components
    // like progress bars keep their state instead of being re-mounted.
    rowKey: {
      type: [String, Function],
      default: undefined
    }
  },
  emits: ['selection-change'],
  data() {
    return {
      loading: false,
      // hasLoadedOnce tracks whether the table has completed at least one
      // successful fetch. The loading spinner is only shown during the
      // first load; subsequent refreshes (filter, sort, search, pagination,
      // manual refresh) update the data silently to avoid UI flicker and
      // to preserve transient row state (e.g. job progress bars).
      hasLoadedOnce: false,
      tableData: [],
      total: 0,
      currentPage: 1,
      currentPageSize: this.defaultPageSize,
      searchKeyword: '',
      // column-level filters: {filter_key: value}; empty/missing value means
      // the column is not filtered. Managed by FilterableTableColumn via the
      // provided pageTableFilter API below.
      columnFilters: {},
      // server-side sort state. Element Plus emits sort-change events with
      // {prop, order} when sortable="custom" columns are clicked. We keep a
      // single-column sort (multi-column sort is not commonly needed here);
      // sortFields is a list of strings like ["-created_at"] ("-" = desc).
      sortFields: [],
      Search: markRaw(Search),
      // Debounce timer for search
      searchTimer: null
    }
  },
  computed: {
    // header cell style uses the element-plus fill-color variable so the
    // header follows the active color mode (light gray in light mode,
    // darker fill in dark mode) instead of a hard-coded #f5f7fa
    headerCellStyle() {
      return { background: 'var(--el-fill-color-light)' }
    },
    // show the loading spinner only during the very first load. Once the
    // table has data, refreshes happen in the background without spinner
    // so the user can keep interacting with the list (e.g. progress bars
    // keep animating instead of being hidden behind a loading mask).
    showLoading() {
      return this.loading && !this.hasLoadedOnce
    }
  },
  mounted() {
    if (this.autoFetch) {
      this.fetchTableData()
    }
  },
  methods: {
    async fetchTableData() {
      this.loading = true
      try {
        const params = {
          page: this.currentPage,
          page_size: this.currentPageSize
        }
        if (this.searchKeyword) {
          params.search = this.searchKeyword
        }
        // include server-side sort fields when set; backend convention:
        // "-field" = desc, "field" = asc (see plans/list-api-pagination-filter.md)
        if (this.sortFields.length > 0) {
          params.sort = this.sortFields
        }
        // include column filters only when at least one filter is set, so
        // list pages can simply do `if (params.filters) query.filters = ...`
        const activeFilters = this.getActiveColumnFilters()
        if (Object.keys(activeFilters).length > 0) {
          params.filters = activeFilters
        }
        const response = await this.fetchData(params)
        if (response && !response.error) {
          const result = response.result || {}
          // Handle paginated response: {items: [], total: N}
          if (Array.isArray(result.items)) {
            this.tableData = result.items
            this.total = result.total || 0
          } else if (Array.isArray(result)) {
            // Handle non-paginated list response
            this.tableData = result
            this.total = result.length
          } else {
            // Handle dict response (e.g. {name: {...}, ...})
            this.tableData = Object.values(result)
            this.total = this.tableData.length
          }
          // mark first successful load so subsequent refreshes skip the spinner
          this.hasLoadedOnce = true
        } else {
          this.$message.error(`获取数据失败：${response?.message || '未知错误'}`)
          this.tableData = []
          this.total = 0
        }
      } catch (error) {
        console.error('获取数据失败:', error)
        this.$message.error('获取数据失败，请检查网络连接')
        this.tableData = []
        this.total = 0
      } finally {
        this.loading = false
      }
    },

    handlePageChange(page) {
      this.currentPage = page
      this.fetchTableData()
    },

    handlePageSizeChange(size) {
      this.currentPageSize = size
      this.currentPage = 1
      this.fetchTableData()
    },

    handleSearchChange() {
      // Debounce search to avoid too many requests
      if (this.searchTimer) {
        clearTimeout(this.searchTimer)
      }
      this.searchTimer = setTimeout(() => {
        this.currentPage = 1
        this.fetchTableData()
      }, 300)
    },

    // ---- server-side sort ----

    // Element Plus sort-change handler. With sortable="custom", el-table
    // emits {column, prop, order} and lets the parent do the actual sorting.
    // We translate that into the backend convention and re-fetch.
    handleSortChange({ prop, order }) {
      if (!prop || !order) {
        // user clicked the same column until sort was cleared
        this.sortFields = []
      } else {
        // order is 'ascending' | 'descending'
        const field = order === 'descending' ? `-${prop}` : prop
        this.sortFields = [field]
      }
      // stay on the current page when only sort changes? The safer option
      // is to go back to page 1 because the data window shifts entirely.
      this.currentPage = 1
      this.fetchTableData()
    },

    // ---- column filter API (provided to FilterableTableColumn) ----

    // get the current value of a column filter; undefined means no filter
    getColumnFilter(key) {
      return this.columnFilters[key]
    },

    // set/clear a column filter and refresh the table from page 1
    setColumnFilter(key, value) {
      const normalized = value === null || value === undefined
        ? ''
        : String(value).trim()
      const next = { ...this.columnFilters }
      if (normalized.length === 0) {
        if (!(key in next)) {
          // nothing changed, avoid unnecessary refresh
          return
        }
        delete next[key]
      } else {
        if (next[key] === normalized) {
          // same value, no need to refresh
          return
        }
        next[key] = normalized
      }
      this.columnFilters = next
      this.currentPage = 1
      this.fetchTableData()
    },

    // build the filters object that is sent to the backend
    getActiveColumnFilters() {
      const result = {}
      for (const [key, value] of Object.entries(this.columnFilters)) {
        if (value !== undefined && value !== null && String(value).length > 0) {
          result[key] = value
        }
      }
      return result
    },

    // public helper to clear all column filters at once (e.g. used by a
    // "reset filters" button in the toolbar)
    clearAllColumnFilters() {
      if (Object.keys(this.columnFilters).length === 0) {
        return
      }
      this.columnFilters = {}
      this.currentPage = 1
      this.fetchTableData()
    },

    // forward el-table selection-change to parent so the parent component
    // can track selectedRows for batch operations (batch delete, etc.)
    handleSelectionChange(selection) {
      this.$emit('selection-change', selection)
    },

    // Public method to refresh data
    refresh() {
      this.fetchTableData()
    }
  }
}
</script>

<style scoped>
.page-table-container {
  display: flex;
  flex-direction: column;
  /* use element-plus variables so the background follows the active
     color mode (light: #f5f7fa-ish, dark: dark page bg) */
  background: var(--el-bg-color-page);
  padding: 20px;
  box-sizing: border-box;
}

.table-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.global-search {
  max-width: 380px;
}

.toolbar-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.pagination-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

/* unify font size between left pagination buttons, the total-count text
   and the page-size el-select so the whole row looks visually consistent */
.total-count {
  font-size: 13px;
  color: #909399;
  white-space: nowrap;
}

.page-size-select {
  width: 110px;
}

.page-size-select :deep(.el-input__inner),
.page-size-select :deep(.el-select__placeholder),
.page-size-select :deep(.el-select__selected-item) {
  font-size: 13px;
}

.table-container {
  flex: 1;
  /* var(--el-bg-color) is white in light mode and dark panel bg in dark mode */
  background: var(--el-bg-color);
  border-radius: 8px;
  padding: 15px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.05);
  overflow: auto;
}

.pagination-container {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 10px;
  padding: 0 20px 50px;
}

.pagination-left {
  display: flex;
  align-items: center;
  height: 32px;
}

.pagination-right {
  display: flex;
  align-items: center;
  gap: 12px;
  height: 32px;
}

/* keep total-count text vertically aligned with the page-size select */
.pagination-right .total-count {
  display: inline-flex;
  align-items: center;
  height: 100%;
}

:deep(.el-table) {
  font-size: 13px;
  --el-table-row-height: 28px;
}

:deep(.el-table th) {
  padding: 8px 0;
  font-size: 13px;
  text-align: center;
}

/* center only the .center-column cells (used for action buttons and
   status indicators) so the .left-column cells (description etc.) remain
   left-aligned as designed */
:deep(.el-table .center-column .cell) {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
}

/* keep the tooltip wrapper from breaking the flex layout */
:deep(.el-table .center-column .cell .el-tooltip__trigger) {
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

/* center pagination vertically; the default margin-top: 20px pushes the
   left pagination down and breaks the horizontal alignment with the
   right page-size selector */
:deep(.el-pagination) {
  margin-top: 0;
  display: flex;
  align-items: center;
}
</style>
