---
name: develop-new-webui-page
description: 在 QCOS WebUI 中开发新页面，包含命名规范、目录结构、组件开发、路由配置和 API 对接的完整开发流程
version: 1.2.0
---

## Preconditions

- 已阅读 `.agents/rules/core.md` 核心规则
- 已阅读 `.agents/rules/code.md` 代码模式规则
- 熟悉 Vue 3、Vue Router、Pinia 和 Element Plus 的基本用法
- 已安装 Node.js 18+、npm 8+，并在 `webui/` 目录执行过 `npm install`
- 需要联调时，已准备 QCOS API 服务和 `qcos-webui.toml` 配置

## Instructions

在 QCOS WebUI 中开发一个包含页面组件、API 对接、路由配置和权限控制的完整页面时，按以下步骤执行。仅开发独立组件时，复用相关步骤，不强制创建路由或 Pinia 状态。

### 步骤总览

```
1. 需求分析 → 2. 设计文档 → 3. 目录与命名 → 4. API 层 → 5. 页面组件
→ 6. 路由与权限 → 7. 状态管理 → 8. 样式与兼容 → 9. 测试验证 → 10. 文档更新
```

### 步骤 1: 需求分析

- 明确页面类型：列表、详情、表单、仪表盘或复合页面
- 确认用户角色、菜单入口、路由参数和页面操作权限
- 梳理后端接口、字段结构、分页/搜索/过滤/排序能力及错误码
- 阅读同类实现，优先复用现有组件和工具：
  - `webui/src/views/device/device_list.vue`：列表页面
  - `webui/src/components/PageTable/index.vue`：服务端分页表格
  - `webui/src/api/device.js`：JSON-RPC API 封装
  - `webui/src/router/index.js`：路由、菜单和角色配置
- 输出：页面原型、交互清单、接口定义和权限要求

### 步骤 2: 设计文档

- 在 `plans/` 目录编写设计文档（Markdown）
- 包含页面结构、组件划分、路由设计、接口时序和状态流转
- 复杂页面补充 Mermaid 架构图或时序图，明确加载、空数据、失败和提交状态
- 明确哪些状态属于页面局部状态，哪些需要通过 Pinia 跨页面共享
- 经用户确认后再进入实现阶段

### 步骤 3: 目录与命名

按业务模块组织文件，避免把页面逻辑集中写入全局组件：

```
webui/src/
├── api/<feature>.js                     # API 封装
├── components/<feature>/                # 可复用业务组件（可选）
├── store/modules/<feature>.js           # Pinia 状态（可选）
├── views/<feature>/<FeatureList>.vue     # 页面组件
└── router/index.js                      # 路由与菜单配置
```

**命名规范：**

| 对象 | 规范 | 示例 |
|:-----|:-----|:-----|
| 页面和组件文件 | PascalCase | `DeviceList.vue`、`DeviceDetail.vue` |
| 目录 | kebab-case 或全小写单词 | `device/`、`device-detail/` |
| API、工具和服务文件 | camelCase，保持同目录一致 | `device.js`、`formatDate.js` |
| composables | camelCase，`use` 开头 | `useDevices.js`、`useWebSocket.js` |
| Pinia store | camelCase，`useXxxStore` | `useDeviceStore.js` |
| 变量、方法、函数 | camelCase | `deviceList`、`fetchDevices()` |
| 全局常量 | UPPER_SNAKE_CASE | `MAX_PAGE_SIZE` |
| 路由 `name` | PascalCase，全局唯一 | `DeviceList` |
| 路由 `path` | kebab-case | `/device-list` |
| CSS 类名 | kebab-case | `.device-list-container` |
| 模板中的组件 | kebab-case | `<page-table :default-page-size="20" />` |
| props 声明 | camelCase | `defineProps({ defaultPageSize: Number })` |

**要点：**

- Vue 组件名必须是多单词，模板中使用 kebab-case，props 声明使用 camelCase
- props 声明使用 camelCase，模板传参使用 kebab-case，Vue 会自动完成名称对应
- 新增文件遵循上述规范；既有文件仅在任务范围内调整，不做无关的大规模重命名
- 文件路径大小写必须与磁盘和动态导入完全一致，避免 Windows 可用而 Linux 构建失败

### 步骤 4: API 层

在 `webui/src/api/` 下按业务模块新增或扩展 API 文件：

```javascript
import { jsonrpcRequest } from '@/api/jsonrpc'

export function getDevices(query = null) {
  return jsonrpcRequest('/v1/device', 'get_devices', {
    details: true
  }, query)
}

export function getDevice(deviceName) {
  return jsonrpcRequest('/v1/device', 'get_device', {
    name: deviceName,
    details: true
  })
}
```

列表查询的 `query` 对象结构如下，可选字段仅在有值时传递：

```javascript
const query = {
  pagination: { page: 1, page_size: 10 },
  search: 'keyword',
  filters: { name: 'x' },
  sort: ['-created_at']
}
```

**要点：**

- API 函数使用 camelCase，以动词开头，如 `getDevices`、`createDevice`
- JSON-RPC 接口复用 `jsonrpcRequest`；REST、SSE、WebSocket 复用对应模块的现有封装
- 列表 API 接受 `query` 参数，支持 `pagination`、`search`、`filters` 和 `sort`
- 不在页面组件中拼接基础 URL 或重复实现认证、错误处理和请求拦截器
- 对响应结构的处理与现有 `jsonrpcRequest` 封装保持一致，不重复解包
- API 注释使用英文，新增文件保留项目版权声明

### 步骤 5: 页面组件

在 `webui/src/views/` 下创建页面。列表页必须使用 `PageTable` 实现服务端分页、搜索、过滤和排序，禁止用前端数组切片代替服务端分页：

```vue
<template>
  <div class="device-list-container">
    <div class="header">
      <h2>设备列表</h2>
    </div>
    <page-table
      :fetch-data="fetchDevices"
      search-placeholder="全局搜索：设备名称 / 别名 / 状态"
      row-key="name"
    >
      <filterable-table-column
        prop="name"
        label="设备名称"
        sortable="custom"
      />
      <filterable-table-column
        prop="status"
        label="状态"
        sortable="custom"
      />
    </page-table>
  </div>
</template>

<script>
import PageTable from '@/components/PageTable'
import FilterableTableColumn from '@/components/PageTable/FilterableTableColumn.vue'
import { getDevices } from '@/api/device'

export default {
  name: 'DeviceList',
  components: { PageTable, FilterableTableColumn },
  methods: {
    async fetchDevices(params) {
      const query = {
        pagination: {
          page: params.page,
          page_size: params.page_size
        }
      }
      if (params.search) query.search = params.search
      if (params.filters) query.filters = params.filters
      if (params.sort) query.sort = params.sort
      return getDevices(query)
    }
  }
}
</script>
```

**PageTable 组件特性：**

- 自动处理服务端分页（`page` / `page_size`）
- 自动处理全局搜索（`search` 参数，300ms 防抖）
- 支持列过滤和服务端排序，并自动回到第一页刷新数据
- 每页大小选项为 10/20/50/100，默认 10
- 左侧显示页码，右侧显示“共 X 条”和每页大小下拉框
- 首次加载显示加载状态，后续刷新在后台进行以避免界面闪烁

**要点：**

- 保持与相邻页面一致的 Options API 或 Composition API 风格，不无理由混用
- `PageTable` 的回调参数是扁平结构，API 的 `query.pagination` 是嵌套结构，必须按示例转换
- 表格数据来自 `response.result.items`，总数来自 `response.result.total`；`PageTable` 已处理该结构
- 可过滤列使用 `FilterableTableColumn`，服务端排序列设置 `sortable="custom"`
- 为表格设置稳定的 `row-key`，需要刷新时通过 `ref` 调用 `PageTable` 的刷新方法
- 表单提供校验、提交中状态和错误提示，防止重复提交
- 页面应覆盖加载中、空数据、请求失败和无权限状态
- 可复用逻辑下沉到组件或 composable，避免复制整页代码

### 步骤 6: 路由与权限

在 `webui/src/router/index.js` 的合适业务分组中注册路由：

```javascript
{
  path: 'devices',
  name: 'DeviceList',
  component: () => import('@/views/device/DeviceList.vue'),
  meta: {
    title: '设备列表',
    icon: 'el-icon-monitor',
    roles: ['admin']
  }
}
```

**要点：**

- 路由 `name` 全局唯一，并供页面跳转和 `<keep-alive>` 使用
- 菜单项设置 `meta.title` 和 `meta.icon`，按角色要求设置 `meta.roles`
- 详情页等无菜单入口的路由设置 `hidden: true`，并配置正确的 `meta.activeMenu`
- 动态路由参数在组件中统一校验，页面刷新后仍能独立加载
- `hidden` 只控制菜单显示，不等同于访问权限；后端 API 仍必须执行权限校验
- 不为新页面重复创建已有父级路由或 `Layout`

### 步骤 7: 状态管理

仅在状态需要跨页面、跨组件共享或持久化时使用 Pinia：

```
webui/src/store/modules/<feature>.js
```

**要点：**

- 页面私有的表单、对话框和表格状态保留在组件内部
- store 文件名使用 camelCase，store 定义使用 `useXxxStore` 风格
- action 返回 Promise，并明确加载、成功和失败状态
- 不重复缓存可由后端实时获取且无需共享的数据
- 不在源码或日志中硬编码、打印密码、Token 等敏感信息

### 步骤 8: 样式与兼容

- CSS 类名使用 kebab-case，页面样式优先使用 `scoped`，避免污染其他页面
- 布局使用 flex/grid，容器间距、表格和操作区样式与同类页面保持一致
- 使用 Element Plus CSS 变量，如 `var(--el-fill-color-light)`，适配明暗主题
- 表格使用 Element Plus 组件，不硬编码固定表头背景色
- 图标、按钮、标签和消息提示复用现有设计体系
- 检查窄屏、长文本、空数据和大数据量下的布局表现
- 遵守 `webui/vite.config.js` 的浏览器构建目标，新增 CSS 和 JavaScript 特性需经过生产构建验证

### 步骤 9: 测试验证

在 `webui/` 目录执行：

```bash
npm run lint
npm run build:prod
```

需要页面联调时，先准备 `/etc/qcos/qcos-webui.toml`，或通过 `WEBUI_TOML` 指定配置文件，再启动开发服务器：

```bash
npm run dev
```

**验证清单：**

- 直接访问和刷新路由，检查菜单、面包屑、图标及角色权限
- 验证分页、每页条数、搜索、过滤、排序和刷新均请求后端
- 验证新增、编辑、删除、取消及表单校验流程
- 验证加载中、空数据、接口失败、无权限和重复提交场景
- 检查浏览器控制台无新增错误，网络请求参数和响应处理正确
- 检查生产构建无新增警告，本次修改文件无新增 ESLint 问题

### 步骤 10: 文档更新

**用户文档：**

- 更新 `docs/sphinx/source/user-guide/` 下的相关文档
- 说明菜单入口、角色要求、操作步骤、字段含义和注意事项
- 新页面包含截图时，确保截图不含真实 Token、密码或其他敏感信息

**开发文档：**

- 如新增公共组件、composable 或改变开发规范，同步更新
  `docs/sphinx/source/developer-guide/develop-new-webui-page.md`
- 如后端 API 同步变更，更新 `docs/sphinx/source/design/api/` 下的接口文档

**CHANGELOG：**

- 在 `CHANGELOG.md` 中记录新增页面、交互调整和问题修复
- 格式参考现有条目，包含版本号、日期和变更类型

## 编码规范检查清单

- [ ] YAML frontmatter 和 Markdown 结构保持有效（修改本技能文件时）
- [ ] 新页面和组件文件使用 PascalCase，目录使用 kebab-case 或全小写单词
- [ ] Vue 组件名为多单词，模板组件使用 kebab-case，props 使用 camelCase
- [ ] 变量、方法和 API 函数使用 camelCase，常量使用 UPPER_SNAKE_CASE
- [ ] 新增文件包含项目版权声明，代码注释仅使用英文，文件使用 LF 换行符
- [ ] 列表页使用 `PageTable`，分页、搜索、过滤和排序均由服务端处理
- [ ] API 的 `query` 正确传递 `pagination`、`search`、`filters` 和 `sort`
- [ ] 路由名称唯一，菜单、图标、角色、`hidden` 和 `activeMenu` 配置正确
- [ ] 仅在跨页面共享状态时使用 Pinia，不无理由扩大全局状态
- [ ] 表单具有校验、加载和错误状态，能够防止重复提交
- [ ] 样式使用 Element Plus 变量并兼容明暗主题，无无关全局样式污染
- [ ] 无硬编码密码、Token、基础 URL 或敏感信息
- [ ] `npm run lint` 和 `npm run build:prod` 已执行，本次修改无新增问题
- [ ] 页面路由、权限、交互和异常场景已验证，相关文档已更新

## 常见陷阱

1. **本地分页代替服务端分页**：页面数据量增大后会漏数据；列表页必须使用 `PageTable` 并传递服务端查询参数
1. **查询参数结构错误**：`PageTable` 提供扁平的 `page/page_size`，后端 `query` 需要嵌套的 `pagination`，必须显式转换
1. **重复解包响应**：`PageTable` 已读取 `response.result.items/total`，`fetchData` 应返回原始 API Promise 结果
1. **路由仅隐藏菜单**：`hidden: true` 不提供权限控制，必须同时配置前端角色和后端 API 权限
1. **路径大小写不一致**：Windows 下可解析的导入路径可能在 Linux 构建中失败，动态导入必须与真实文件名完全一致
1. **开发服务器缺少配置**：`npm run dev` 需要 `qcos-webui.toml`，缺失时会直接退出；生产构建不读取该开发配置
1. **异步状态未清理**：轮询、定时器和事件监听必须在组件卸载时清理，提交操作必须防止并发重复执行
1. **硬编码样式破坏主题**：优先使用 Element Plus CSS 变量，不复制旧页面的固定背景色覆盖主题
