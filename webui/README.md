# QCOS WebUI

量子计算操作系统（QCOS）的 Web 管理界面，基于 Vue 3 + Element Plus + Vite 构建。

## 功能特性

- **作业管理**：QASM / QUBO 作业提交、查看、删除、高亮定位
- **设备管理**：量子设备列表、详情、状态监控、设备分组
- **资源规格（Flavor）**：自动调度策略配置
- **用户与权限**：用户/角色/项目管理、登录日志
- **系统监控**：API 统计、作业统计、组件状态、系统信息
- **多 Endpoint 切换**：支持配置多个 QCOS API endpoint，免登录动态切换
- **主题定制**：明暗色模式、自定义主题色

## 多 Endpoint 配置

WebUI 通过 `/etc/qcos/qcos-webui.toml` 配置文件管理 QCOS API endpoint：

```toml
[DEFAULT]
DEBUG = false
LISTEN_IP = "0.0.0.0"
LISTEN_PORT = 18401
DEFAULT_ENDPOINT = "local"

QCOS_API_ENDPOINTS = [
  { name = "local", alias = "本地开发环境", url = "http://127.0.0.1:18400" }
]
```

支持：
- 多个 endpoint 配置，登录页与侧边栏下拉切换
- 每个 endpoint 可选 `use_ssl = true` + `cacert` 自签名证书
- endpoint 健康探测（`/version`），不可用自动禁用
- 用户名 + token 按 endpoint 隔离保存，切换免登录

详细配置说明见 [`INSTALL.md`](INSTALL.md) 与 [`config-run-webui.rst`](../docs/sphinx/source/user-guide/deploy-guide/config-run-webui.rst)。

## 快速开始

### 容器部署（推荐）

```bash
cd build-scripts
cp ./env.template .env
vim .env
./build-images.sh -w
sudo mkdir -p /etc/qcos
sudo vim /etc/qcos/qcos-webui.toml
./run-docker-webui.sh
```

访问 `http://{IP}:18401`

### 本地开发

```bash
cd webui
npm install
npm run dev
```

访问 `http://localhost:9528`

## 项目结构

```
webui/
├── public/                 # 静态资源
├── src/
│   ├── api/               # API 请求封装（JSON-RPC / HTTP）
│   ├── assets/            # 图片、图标等资源
│   ├── common/            # 公共工具函数
│   ├── components/        # 公共组件（PageTable、ThemePicker、MonacoEditor 等）
│   ├── layout/            # 布局组件（Navbar、Sidebar、AppMain）
│   │   └── components/
│   │       └── Sidebar/
│   │           ├── EndpointSwitcher.vue  # endpoint 切换下拉
│   │           └── ...
│   ├── router/            # 路由配置
│   ├── store/             # Pinia 状态管理
│   │   └── modules/
│   │       ├── config.js  # endpoint 配置与健康探测
│   │       ├── user.js    # 用户会话（按 endpoint 隔离）
│   │       └── ...
│   ├── styles/            # 全局样式（SCSS 变量、暗色模式）
│   ├── utils/             # 工具函数（request、auth、session、theme 等）
│   ├── views/             # 页面组件
│   │   ├── login/         # 登录页（含 endpoint 下拉）
│   │   ├── job/           # 作业相关页面
│   │   ├── device/        # 设备相关页面
│   │   └── ...
│   ├── App.vue
│   ├── main.js            # 入口：加载 runtime config → 恢复 session → 挂载
│   └── permission.js      # 路由守卫
├── index.html
├── vite.config.js
└── package.json
```

## 核心机制

### 运行时配置加载

应用启动时（[`main.js`](src/main.js)）：

1. `fetch('/webui-config.json')` → 加载 endpoint 列表、debug 开关、探测超时
2. 从 localStorage 恢复当前 endpoint 的会话
3. 后台并发探测所有 endpoint 的 `/version` → 更新健康状态
4. 挂载 Vue 应用

### 会话隔离

- `localStorage` 键 `qcos_tokens`：按 endpoint `name` 存储 `{token, name, userId, roles, authMode, avatar, savedAt}`
- `Cookie` 键 `qcos_active_endpoint`：仅存当前激活的 endpoint `name`
- 所有 API 请求从 `activeEndpointName + qcos_tokens` 派生 `baseURL` 与 `Authorization` 头

### Endpoint 健康探测

- 登录页与侧边栏下拉框显示每个 endpoint 的版本号与可用状态
- 不可用 endpoint 自动禁用选择
- 探测超时默认 3000ms，30 秒内不重复探测

## 相关文档

- [`INSTALL.md`](INSTALL.md) — 安装部署详细说明
- [`config-run-webui.rst`](../docs/sphinx/source/user-guide/deploy-guide/config-run-webui.rst) — 配置与启动手册
- [`plans/webui-multi-endpoint-plan.md`](../plans/webui-multi-endpoint-plan.md) — 完整设计方案
- [`etc/qcos/qcos-webui.toml`](../etc/qcos/qcos-webui.toml) — 默认配置文件模板

## 许可证

MulanPSL-2.0
