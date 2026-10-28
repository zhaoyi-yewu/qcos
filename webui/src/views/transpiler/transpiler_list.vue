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
  <div class="transpiler-list-container">
    <div class="header">
      <h2>转译器列表</h2>
    </div>
    <PageTable
      ref="pageTableRef"
      :fetch-data="fetchTranspilers"
      search-placeholder="全局搜索：转译器名称 / 别名 / 状态 / 代码类型 …"
      row-key="name"
    >
      <filterable-table-column
        prop="name"
        label="转译器名称"
        fixed="left"
        class-name="center-column"
        sortable="custom"
      />
      <filterable-table-column
        prop="alias_name"
        label="转译器别名"
        fixed="left"
        class-name="center-column"
        sortable="custom"
      />
      <filterable-table-column
        prop="enable"
        label="启用"
        class-name="center-column"
        sortable="custom"
      >
        <template #default="scope">
          <el-tag :type="scope.row.enable ? 'success' : 'danger'">
            {{ getEnable(scope.row.enable) }}
          </el-tag>
        </template>
      </filterable-table-column>
      <filterable-table-column
        prop="supported_code_types"
        label="支持的代码类型"
        class-name="center-column"
        sortable="custom"
      >
        <template #default="scope">
          {{ scope.row.supported_code_types }}
        </template>
      </filterable-table-column>
      <el-table-column
        prop="details"
        label="操作"
        class-name="center-column"
        fixed="right"
        width="70"
      >
        <template #default="scope">
          <el-tooltip content="查看" placement="top">
            <el-button
              link
              :icon="View"
              @click="viewTranspilerDetails(scope.row.name)"
            />
          </el-tooltip>
        </template>
      </el-table-column>
    </PageTable>
  </div>
</template>

<script>
import { markRaw } from 'vue'
import { View } from '@element-plus/icons-vue'
import PageTable from '@/components/PageTable'
import FilterableTableColumn from '@/components/PageTable/FilterableTableColumn.vue'
import { getTranspilers } from '@/api/transpiler'
import { getEnable } from '@/common/library'

export default {
  components: {
    PageTable,
    FilterableTableColumn
  },
  data() {
    return {
      View: markRaw(View)
    }
  },
  methods: {
    getEnable,

    // PageTable fetchData callback
    async fetchTranspilers(params) {
      const query = {
        pagination: {
          page: params.page,
          page_size: params.page_size
        }
      }
      if (params.search) {
        query.search = params.search
      }
      if (params.filters) {
        query.filters = params.filters
      }
      if (params.sort) {
        query.sort = params.sort
      }
      return await getTranspilers(query)
    },

    viewTranspilerDetails(transpilerName) {
      this.$router.push({ name: 'TranspilerDetails', params: { transpilerName: transpilerName }})
    }
  }
}
</script>

<style scoped>
.transpiler-list-container {
  display: flex;
  flex-direction: column;
  background: var(--el-fill-color-light);
  padding: 20px;
  box-sizing: border-box;
}

.header { margin: 0; }
</style>
