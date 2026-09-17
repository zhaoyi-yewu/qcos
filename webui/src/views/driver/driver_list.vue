<template>
  <div v-if="loaded" class="driver-list-container">
    <div class="header">
      <h2>驱动查询</h2>
    </div>
    <div class="table-container">
      <el-table
        ref="tableRef"
        :data="pageData"
        style="width: 100%"
        border
        :header-cell-style="{ background: '#f5f7fa' }"
      >
        <el-table-column
          prop="name"
          label="驱动名称"
          fixed="left"
          class-name="center-column"
          sortable
        />
        <el-table-column
          prop="alias_name"
          label="驱动别名"
          fixed="left"
          class-name="center-column"
          sortable
        />
        <el-table-column
          prop="version"
          label="驱动版本"
          class-name="center-column"
          sortable
        />
        <el-table-column
          prop="tech_type"
          label="技术路线"
          class-name="center-column"
          sortable
        >
          <template #default="scope">
            {{ versionData.capabilities['tech_types'][scope.row.tech_type]['alias_name'] || '-' }}
          </template>
        </el-table-column>
        <el-table-column
          prop="max_qubits"
          label="量子比特数"
          class-name="center-column"
          sortable
        />
        <el-table-column
          prop="transpiler"
          label="默认转译器"
          class-name="center-column"
          sortable
        >
          <template #default="scope">
            <div v-if="scope.row.transpiler">
              <el-button
                type="text"
                @click="viewTranspilerDetails(scope.row.transpiler)"
              >
                {{ versionData.capabilities['transpilers'][scope.row.transpiler]['alias_name'] || '-' }}
              </el-button>
            </div>
            <div v-else>
              -
            </div>
          </template>
        </el-table-column>
        <el-table-column
          prop="description"
          label="驱动描述"
          class-name="left-column"
          sortable
        />
        <el-table-column
          prop="details"
          label="详情"
          class-name="center-column"
        >
          <template #default="scope">
            <el-button
              type="text"
              @click="viewDriverDetails(scope.row.name)"
            >
              查看
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <div class="pagination-container">
      <el-pagination
        background
        layout="total, prev, pager, next"
        :total="driverList.length"
        :page-size="pageSize"
        :current-page="currentPage"
        @current-change="handlePageChange"
      />
    </div>
  </div>
</template>

<script>
import { getDrivers } from '@/api/driver'
import { queryVersion } from '@/api/version'

export default {
  data() {
    return {
      loaded: false,
      versionData: {
        version: '',
        api_version: '',
        supported_api_versions: [],
        platform_version: '',
        capabilities: {}
      },
      driverList: [],
      currentPage: 1,
      pageSize: 10,
      timer: null,
      pollingInterval: 10000,
      selectedRows: []
    }
  },

  selectedIds: [],

  computed: {
    pageData() {
      const start = (this.currentPage - 1) * this.pageSize
      const end = this.currentPage * this.pageSize
      return this.driverList.slice(start, end)
    },

    // 判断是否全选
    isAllSelected() {
      // 过滤掉不可选的行
      const selectableCount = this.driverList.filter(item => this.checkSelectable(item)).length
      return this.selectedRows.length > 0 && this.selectedRows.length === selectableCount
    }
  },

  mounted() {
    this.startPolling()
  },

  beforeUnmount() {
    this.stopPolling()
  },

  created() {
    this.queryData()
  },

  methods: {
    handlePageChange(page) {
      this.currentPage = page
    },

    async queryData() {
      await this.fetchVersion()
      await this.fetchDrivers()
      this.loaded = true
    },

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

    async fetchDrivers() {
      try {
        const response = await getDrivers()
        if (!response.error) {
          const drivers = response.result
          this.driverList = []
          for (const driverName in drivers) {
            const driver = drivers[driverName]
            this.driverList.push(driver)
          }
        } else {
          this.$message.error(`获取驱动列表失败：${response.message || '未知错误'}`)
        }
      } catch (error) {
        console.error('获取驱动列表失败:', error)
        this.$message.error('获取驱动列表失败，请检查网络连接')
      }
    },

    startPolling() {
      this.fetchDrivers()
      this.timer = setInterval(() => {
        this.fetchDrivers()
      }, this.pollingInterval)
    },

    stopPolling() {
      if (this.timer) {
        clearInterval(this.timer)
        this.timer = null
      }
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
  height: 100vh;
  background: #f5f7fa;
  padding: 20px;
  box-sizing: border-box;
}

.header {
  margin-bottom: 0px;
}

.table-container {
  flex: 1;
  background: white;
  border-radius: 8px;
  padding: 15px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.05);
  overflow: auto;
}

.pagination-container {
  text-align: center;
  margin-top: 10px;
  padding: 0 20px 50px;
}

::v-deep .el-table {
  font-size: 15px;
  --el-table-row-height: 30px;
}

::v-deep .el-table th {
  padding: 12px 0;
  font-size: 16px;
  text-align: center;
}

::v-deep .el-pagination {
  margin-top: 20px;
}

::v-deep .center-column {
  text-align: center;
}
</style>
