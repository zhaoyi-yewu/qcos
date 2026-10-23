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
  <el-table-column
    v-bind="$attrs"
    :prop="prop"
    :label="label"
    :sortable="sortable"
    :class-name="className"
    :fixed="fixed"
    :width="width"
    :label-class-name="labelClassName"
  >
    <!-- custom header: label + filter icon. Element Plus renders its own
         sort caret next to the #header slot when sortable is enabled, so
         the filter icon coexists with the sort caret automatically.
         Click stop is only applied on the icon so clicking the label still
         triggers the column sort. -->
    <template #header>
      <span class="ftc-header">
        <span class="ftc-label">{{ label }}</span>
        <el-popover
          v-model:visible="popoverVisible"
          placement="bottom-start"
          trigger="click"
          :width="240"
          popper-class="ftc-filter-popover"
          @show="onPopoverShow"
        >
          <template #reference>
            <el-button
              link
              class="ftc-filter-icon"
              :class="{ 'ftc-filter-active': hasActiveFilter }"
              :icon="Filter"
              @click.stop
            />
          </template>
          <div class="ftc-filter-panel">
            <el-input
              v-model="inputValue"
              :placeholder="`过滤：${label}`"
              clearable
              size="small"
              @keyup.enter="applyFilter"
            />
            <div class="ftc-filter-actions">
              <el-button size="small" @click="clearFilter">清除</el-button>
              <el-button
                size="small"
                type="primary"
                @click="applyFilter"
              >确定</el-button>
            </div>
          </div>
        </el-popover>
      </span>
    </template>
    <!-- pass through the default cell slot -->
    <template v-if="$slots.default" #default="scope">
      <slot v-bind="scope" />
    </template>
  </el-table-column>
</template>

<script>
import { markRaw, inject } from 'vue'
import { Filter } from '@element-plus/icons-vue'

export default {
  name: 'FilterableTableColumn',
  // disable attr fall-through so $attrs are forwarded explicitly to
  // el-table-column via v-bind="$attrs"
  inheritAttrs: false,
  props: {
    // column field name (used both as el-table-column prop and filter key)
    prop: {
      type: String,
      required: true
    },
    // column label
    label: {
      type: String,
      required: true
    },
    // whether the column is sortable (forwarded to el-table-column).
    // use "custom" so the parent PageTable handles sorting on the server.
    sortable: {
      type: [Boolean, String],
      default: false
    },
    // css class name forwarded to el-table-column (applies to td cells)
    className: {
      type: String,
      default: 'center-column'
    },
    // css class name forwarded to el-table-column th (header cell)
    labelClassName: {
      type: String,
      default: ''
    },
    // fixed position forwarded to el-table-column
    fixed: {
      type: [Boolean, String],
      default: false
    },
    // column width forwarded to el-table-column
    width: {
      type: [String, Number],
      default: undefined
    },
    // filter key used in backend filters; defaults to prop
    filterKey: {
      type: String,
      default: ''
    }
  },
  setup() {
    // PageTable provides getFilter/setFilter functions so this column can
    // sync its filter state with the parent table
    const pageTableFilter = inject('pageTableFilter', null)
    return { pageTableFilter }
  },
  data() {
    return {
      popoverVisible: false,
      inputValue: '',
      Filter: markRaw(Filter)
    }
  },
  computed: {
    effectiveFilterKey() {
      return this.filterKey || this.prop
    },
    hasActiveFilter() {
      if (!this.pageTableFilter) return false
      const v = this.pageTableFilter.getFilter(this.effectiveFilterKey)
      return v !== undefined && v !== null && String(v).length > 0
    }
  },
  mounted() {
    // initialize local input with any externally set filter value
    if (this.pageTableFilter) {
      const v = this.pageTableFilter.getFilter(this.effectiveFilterKey)
      if (v !== undefined && v !== null) {
        this.inputValue = String(v)
      }
    }
  },
  methods: {
    onPopoverShow() {
      // sync the input with the current filter value every time it opens
      if (this.pageTableFilter) {
        const v = this.pageTableFilter.getFilter(this.effectiveFilterKey)
        this.inputValue = v === undefined || v === null ? '' : String(v)
      }
    },
    applyFilter() {
      if (this.pageTableFilter) {
        this.pageTableFilter.setFilter(
          this.effectiveFilterKey,
          this.inputValue.trim()
        )
      }
      this.popoverVisible = false
    },
    clearFilter() {
      this.inputValue = ''
      if (this.pageTableFilter) {
        this.pageTableFilter.setFilter(this.effectiveFilterKey, '')
      }
      this.popoverVisible = false
    }
  }
}
</script>

<!-- NOT scoped: the header slot content is rendered inside el-table's th,
     which lives outside this component's DOM subtree, so scoped styles
     would not reach the filter icon. Using a unique prefix to avoid
     global class collisions. -->
<style>
.ftc-header {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  vertical-align: middle;
}

/* el-button[link] with only an icon still has padding; remove it so the
   icon sits flush next to the column label and aligns with the sort caret */
.ftc-filter-icon.el-button {
  padding: 0;
  height: auto;
  min-height: 0;
  color: #909399;
  font-size: 14px;
  vertical-align: middle;
  transition: color 0.2s;
}

.ftc-filter-icon.el-button:hover {
  color: #409eff;
}

.ftc-filter-icon.el-button.ftc-filter-active {
  color: #409eff;
}

.ftc-filter-panel {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.ftc-filter-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>
