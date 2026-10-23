---
name: develop-new-webui-page
description: 在 QCOS WebUI 中开发新页面，包含命名规范、目录结构、组件开发、路由配置和 API 对接的完整开发流程
version: 1.0.0
---

# Develop New WebUI Page

> 本技能定义了在 QCOS WebUI 中开发新页面的完整流程和规范。
> 触发条件：用户要求开发新的 WebUI 页面或组件。

## 1. 命名规范

### 1.1 文件与目录命名

| 对象 | 规范 | 示例 |
|------|------|------|
| 组件文件 (.vue) | PascalCase | `StockList.vue`、`TradeDetail.vue` |
| 目录 | kebab-case 或全小写单词 | `components/`、`stock-detail/` |
| 普通工具/服务文件 | camelCase 或 kebab-case（统一） | `formatDate.ts` |
| composables | camelCase，use 开头 | `useStocks.ts`、`useWebSocket.ts` |
| Pinia store | camelCase，useXxxStore | `useUserStore.ts` |

### 1.2 代码命名

| 对象 | 规范 | 示例 |
|------|------|------|
| 变量、方法、函数 | camelCase | `stockList`、`fetchQuotes()` |
| 全局常量 | UPPER_SNAKE_CASE | `MAX_PAGE_SIZE` |
| CSS 类名 | kebab-case | `.stock-card` |

### 1.3 模板命名

| 对象 | 规范 | 示例 |
|------|------|------|
| 模板中使用组件 | kebab-case | `<stock-list :page-size="20" />` |
| 声明 props | camelCase | `defineProps({ pageSize: Number })` |

## 2. 页面开发流程

### 2.1 创建页面组件

1. **确定页面路径**：在 `webui/src/views/` 下按业务模块创建目录（kebab-case）
1. **创建 .vue 文件**：使用 PascalCase 命名，如 `DeviceList.vue`
1. **模板结构**：
   ```vue
   <template>
     <div class="page-name-container">
       <div class="header">
         <h2>页面标题</h2>
       </div>
       <!-- 列表页使用 PageTable 组件 -->
       <page-table
         :fetch-data="fetchData"
         :search-placeholder="'全局搜索...'"
       >
         <el-table-column prop="name" label="名称" />
       </page-table>
     </div>
   </template>
   ```

### 2.2 使用 PageTable 组件（列表页）

列表页必须使用 `PageTable` 组件实现服务端分页/搜索/过滤：

```vue
<script>
import PageTable from '@/components/PageTable'

export default {
  components: { PageTable },
  methods: {
    async fetchData(params) {
      // params: {page, page_size, search}
      const query = {
        pagination: { page: params.page, page_size: params.page_size }
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

### 2.3 API 层规范

1. **API 文件位置**：`webui/src/api/` 下按模块命名（camelCase 或 kebab-case）
1. **函数命名**：camelCase，动词开头，如 `getDevices`、`createFlavor`
1. **分页参数**：所有列表 API 必须支持 `query` 参数：
   ```javascript
   export function getDevices(query = null) {
     return jsonrpcRequest('/v1/device', 'get_devices', { details: true }, query)
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

## 3. 样式规范

1. **CSS 类名**：kebab-case，如 `.device-list-container`
1. **布局**：使用 flex 布局，页面容器统一 padding: 20px
1. **表格样式**：统一使用 Element Plus 的 `el-table`，边框、表头背景色 #f5f7fa
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

## 5. 参考文件

- 公共组件：`webui/src/components/PageTable/index.vue`
- API 示例：`webui/src/api/device.js`
- 页面示例：`webui/src/views/device/device_list.vue`
