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
  <div class="driver-list-container">
    <div class="header">
      <h2>驱动列表</h2>
    </div>
    <PageTable
      ref="pageTableRef"
      :fetch-data="fetchDrivers"
      search-placeholder="全局搜索：驱动名称 / 别名 / 版本 / 技术路线 …"
      row-key="name"
    >
      <filterable-table-column
        prop="name"
        label="驱动名称"
        fixed="left"
        class-name="center-column"
        sortable="custom"
      />
      <filterable-table-column
        prop="alias_name"
        label="驱动别名"
        fixed="left"
        class-name="center-column"
        sortable="custom"
      />
      <filterable-table-column
        prop="version"
        label="驱动版本"
        class-name="center-column"
        sortable="custom"
      />
      <filterable-table-column
        prop="tech_type"
        label="技术路线"
        class-name="center-column"
        sortable="custom"
      >
        <template #default="scope">
          {{ getTechTypeName(versionData, scope.row.tech_type) }}
        </template>
      </filterable-table-column>
      <filterable-table-column
        prop="max_qubits"
        label="量子比特数"
        class-name="center-column"
        sortable="custom"
      />
      <filterable-table-column
        prop="transpiler"
        label="默认转译器"
        class-name="center-column"
        sortable="custom"
      >
        <template #default="scope">
          <div v-if="scope.row.transpiler">
            <el-button
              link
              @click="viewTranspilerDetails(scope.row.transpiler)"
            >
              {{ getTranspilerAliasName(scope.row.transpiler) }}
            </el-button>
          </div>
          <div v-else>
            -
          </div>
        </template>
      </filterable-table-column>
      <filterable-table-column
        prop="description"
        label="驱动描述"
        class-name="left-column"
        sortable="custom"
      />
      <el-table-column
        prop="details"
        label="操作"
        class-name="center-column"
        fixed="right"
        width="90"
      >
        <template #default="scope">
          <el-tooltip content="查看" placement="top">
            <el-button
              link
              :icon="View"
              @click="viewDriverDetails(scope.row.name)"
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
import { getDrivers } from '@/api/driver'
import { getTechTypeName } from '@/common/library'
import { queryVersion } from '@/api/version'

export default {
  components: {
    PageTable,
    FilterableTableColumn
  },
  data() {
    return {
      versionData: {
        version: '',
        api_version: '',
        supported_api_versions: [],
        platform_version: '',
        capabilities: {}
      },
      View: markRaw(View)
    }
  },
  created() {
    this.fetchVersion()
  },
  methods: {
    getTechTypeName,

    async fetchVersion() {
      try {
        const response = await queryVersion()
        if (!response.error) {
          this.versionData = response.result
        } else {
          this.$message.error(`获取版本能力失败：${response.message || '未知错误'}`)
        }
      } catch (error) {
        console.error('获取版本能力失败:', error)
        this.$message.error('获取版本能力失败，请检查网络连接')
      }
    },

    getTranspilerAliasName(transpilerName) {
      const caps = this.versionData && this.versionData.capabilities
      if (!caps || !caps.transpilers || !caps.transpilers[transpilerName]) {
        return '-'
      }
      return caps.transpilers[transpilerName].alias_name || '-'
    },

    // PageTable fetchData callback
    async fetchDrivers(params) {
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
      return await getDrivers(query)
    },

    viewTranspilerDetails(transpilerName) {
      this.$router.push({ name: 'TranspilerDetails', params: { transpilerName: transpilerName }})
    },

    viewDriverDetails(driverName) {
      this.$router.push({ name: 'DriverDetails', params: { driverName: driverName }})
    }
  }
}
</script>

<style scoped>
.driver-list-container {
  display: flex;
  flex-direction: column;
  background: var(--el-fill-color-light);
  padding: 20px;
  box-sizing: border-box;
}

.header { margin: 0; }
</style>
