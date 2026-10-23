# WebUI 页面开发指南

> 本指南介绍在 QCOS WebUI 中开发新页面的完整流程和规范。
> 遵循 Vue 3 官方风格指南和 Element Plus 组件库最佳实践。

## 1. 命名规范

### 1.1 文件与目录命名

| 对象 | 规范 | 示例 |
|------|------|------|
| 组件文件 (.vue) | PascalCase | `StockList.vue`、`TradeDetail.vue` |
| 目录 | kebab-case 或全小写单词 | `components/`、`stock-detail/` |
| 普通工具/服务文件 | camelCase 或 kebab-case（统一） | `formatDate.ts` |
| composables | camelCase，use 开头 | `useStocks.ts`、`useWebSocket.ts` |
| Pinia store | camelCase，useXxxStore | `useUserStore.ts` |

**要点**：目录必须使用 kebab-case，避免 macOS/Windows（大小写不敏感）和 Linux（敏感）之间的大小写冲突。

### 1.2 代码命名

| 对象 | 规范 | 示例 |
|------|------|------|
| 变量、方法、函数 | camelCase | `stockList`、`fetchQuotes()` |
| 全局常量 | UPPER_SNAKE_CASE | `MAX_PAGE_SIZE` |
| CSS 类名 | kebab-case | `.stock-card` |

**要点**：camelCase 是 JavaScript 的绝对标准，snake_case 在 JS 代码中会显得格格不入。

### 1.3 模板命名

| 对象 | 规范 | 示例 |
|------|------|------|
| 模板中使用组件 | kebab-case | `<stock-list :page-size="20" />` |
| 声明 props | camelCase | `defineProps({ pageSize: Number })` |

**要点**：props 是两套写法配合 —— 声明时用 camelCase，模板里传参用 kebab-case，Vue 自动对应。

## 2. 页面开发流程

### 2.1 创建页面组件

1. **确定页面路径**：在 `webui/src/views/` 下按业务模块创建目录（kebab-case）
1. **创建 .vue 文件**：使用 PascalCase 命名，如 `DeviceList.vue`
1. **模板结构**：

```vue
<template>
  <div class="device-list-container">
    <div class="header">
      <h2>设备列表</h2>
    </div>
    <!-- 列表页使用 PageTable 组件 -->
    <page-table
      :fetch-data="fetchDevices"
      search-placeholder="全局搜索：设备名称 / 别名 / 驱动 / 状态 …"
    >
      <el-table-column prop="name" label="设备名称" />
      <el-table-column prop="driver_name" label="设备驱动" />
    </page-table>
  </div>
</template>
```

### 2.2 使用 PageTable 组件（列表页）

所有列表页必须使用 `PageTable` 组件实现服务端分页/搜索/过滤，禁止本地分页：

```vue
<script>
import PageTable from '@/components/PageTable'
import { getDevices } from '@/api/device'

export default {
  components: { PageTable },
  methods: {
    // PageTable fetchData callback
    // params: {page, page_size, search}
    async fetchDevices(params) {
      const query = {
        pagination: {
          page: params.page,
          page_size: params.page_size
        }
      }
      if (params.search) {
        query.search = params.search
      }
      return await getDevices(query)
    }
  }
}
</script>
```

**PageTable 组件特性**：

- 自动处理服务端分页（page/page_size）
- 自动处理全局搜索（search 参数，300ms 防抖）
- 每页大小下拉框（10/20/50/100，默认 10）
- 右对齐"共 X 条"统计显示
- 加载状态管理

### 2.3 API 层规范

1. **API 文件位置**：`webui/src/api/` 下按模块命名（camelCase 或 kebab-case）
1. **函数命名**：camelCase，动词开头，如 `getDevices`、`createFlavor`
1. **分页参数**：所有列表 API 必须支持 `query` 参数：

```javascript
import { jsonrpcRequest } from '@/api/jsonrpc'

export function getDevices(query = null) {
  return jsonrpcRequest('/v1/device', 'get_devices', { details: true }, query)
}
```

`query` 对象结构：

```javascript
{
  pagination: { page: 1, page_size: 10 },
  search: "keyword",        // 可选
  filters: { name: "x" },   // 可选
  sort: ["-created_at"]     // 可选
}
```

### 2.4 路由注册

在 `webui/src/router/index.js` 中注册路由：

```javascript
{
  path: '/device-list',
  name: 'DeviceList',
  component: () => import('@/views/device/device-list.vue'),
  meta: { title: '设备列表', icon: 'device' }
}
```

**要点**：路由 `name` 使用 PascalCase，`path` 使用 kebab-case。

## 3. 样式规范

1. **CSS 类名**：kebab-case，如 `.device-list-container`
1. **布局**：使用 flex 布局，页面容器统一 `padding: 20px`
1. **表格样式**：统一使用 Element Plus 的 `el-table`，边框、表头背景色 `#f5f7fa`
1. **分页样式**：右对齐，显示"共 X 条"和每页大小下拉框

## 4. 检查清单

开发完成后对照以下清单检查：

- [ ] 组件文件名为 PascalCase，目录名为 kebab-case
- [ ] 变量/方法使用 camelCase，常量使用 UPPER_SNAKE_CASE
- [ ] 模板中组件使用 kebab-case，props 声明使用 camelCase
- [ ] 列表页使用 PageTable 组件，实现服务端分页/搜索
- [ ] API 函数支持 query 参数（pagination/search/filters）
- [ ] CSS 类名使用 kebab-case
- [ ] 路由已注册，菜单已配置（如需要）
- [ ] 组件名必须是多单词（避免和 HTML 原生标签冲突）

## 5. 参考文件

| 文件 | 说明 |
|------|------|
| `webui/src/components/PageTable/index.vue` | 公共分页表格组件 |
| `webui/src/api/device.js` | API 层示例 |
| `webui/src/views/device/device_list.vue` | 列表页面示例 |
| `.agents/skills/develop-new-webui-page/SKILL.md` | AI Agent 技能定义 |
