<template>
  <div class="transpiler-list-container">
    <div class="header">
      <h2>转译器查询</h2>
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
          label="转译器名称"
          fixed="left"
          class-name="center-column"
          sortable
        />
        <el-table-column
          prop="alias_name"
          label="转译器别名"
          fixed="left"
          class-name="center-column"
          sortable
        />
        <el-table-column
          prop="enable"
          label="启用"
          class-name="center-column"
          sortable
        >
          <template #default="scope">
            {{ getEnable(scope.row.enable) }}
          </template>
        </el-table-column>
        <el-table-column
          prop="supported_code_types"
          label="支持的代码类型"
          class-name="center-column"
          sortable
        >
          <template #default="scope">
            {{ scope.row.supported_code_types }}
          </template>
        </el-table-column>
        <el-table-column
          prop="details"
          label="详情"
          class-name="center-column"
        >
          <template #default="scope">
            <el-button
              type="text"
              @click="viewTranspilerDetails(scope.row.name)"
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
        :total="transpilerList.length"
        :page-size="pageSize"
        :current-page="currentPage"
        @current-change="handlePageChange"
      />
    </div>
  </div>
</template>

<script>
import { getTranspilers } from '@/api/transpiler'
import { getEnable } from '@/common/library'

export default {
  data() {
    return {
      transpilerList: [],
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
      return this.transpilerList.slice(start, end)
    },

    // 判断是否全选
    isAllSelected() {
      // 过滤掉不可选的行
      const selectableCount = this.transpilerList.filter(item => this.checkSelectable(item)).length
      return this.selectedRows.length > 0 && this.selectedRows.length === selectableCount
    }
  },

  mounted() {
    this.startPolling()
  },

  beforeUnmount() {
    this.stopPolling()
  },

  methods: {
    getEnable,
    handlePageChange(page) {
      this.currentPage = page
    },

    async fetchDrivers() {
      try {
        const response = await getTranspilers()
        if (!response.error) {
          const transpilers = response.result
          this.transpilerList = []
          for (const transpilerName in transpilers) {
            const transpiler = transpilers[transpilerName]
            this.transpilerList.push(transpiler)
          }
        } else {
          this.$message.error(`获取转译器列表失败：${response.message || '未知错误'}`)
        }
      } catch (error) {
        console.error('获取转译器列表失败:', error)
        this.$message.error('获取转译器列表失败，请检查网络连接')
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
    }
  }
}
</script>

<style scoped>
.transpiler-list-container {
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
