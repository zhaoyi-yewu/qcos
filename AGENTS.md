# AGENTS.md - QCOS AI Agent 指引

> 本文件遵循 [AGENTS.md 社区标准](https://agents.md)，为各类 AI 编码助手提供 QCOS 项目的统一指引。
> AI agent 在开始任何任务前，必须先阅读本文件。

## 项目概述

**WUYUEQbit 量子计算操作系统（QCOS）** 是一款开源通用量子计算操作系统，为不同架构的量子计算机（超导、中性原子、离子阱、光量子等）提供统一软件支持。

- **后端主语言**：Python（PEP8 规范）
- **前端技术栈**：Vue 3 + Vite + Element Plus（`webui/`）
- **运行环境**：Windows / Linux（BCLinux 21.10U4、OpenEuler 24.03 LTS）
- **许可证**：MulanPSL-2.0
- **在线文档**：https://qcos.readthedocs.io

## 工作流（Quick Start）

AI agent 处理任务的推荐流程：

1. **识别任务类型** — 判断属于哪种开发场景（新模块 / 新驱动 / 新页面 / 缺陷修复 / 问答）
1. **加载规则文件** — 按当前模式加载对应的 `.agents/rules/*.md`
1. **匹配技能文件** — 若任务符合技能触发条件，加载对应 `SKILL.md` 并严格按步骤执行
1. **定位代码** — 参考下文「目录结构速查」找到目标文件
1. **遵守关键约定** — 编码、提交、沟通均须符合「关键约定」章节
1. **自检** — 完成后对照规则文件中的检查清单自查

## 规则文件

AI agent 必须按当前模式加载对应规则文件。所有模式共享 [`core.md`](.agents/rules/core.md)，各模式有专用规则。

| 模式 | 规则文件 | 说明 |
|:-----|:---------|:-----|
| 所有模式 | [`.agents/rules/core.md`](.agents/rules/core.md) | 沟通语言、回复风格、Git 提交规范、安全约束 |
| code（代码） | [`.agents/rules/code.md`](.agents/rules/code.md) | PEP8 规范、编码检查清单、常见陷阱 |
| ask（问答） | [`.agents/rules/ask.md`](.agents/rules/ask.md) | 回答原则、分析原则、文档引用规范 |
| architect（架构） | [`.agents/rules/core.md`](.agents/rules/core.md) | 架构模式复用 core 规则 |
| debug（调试） | [`.agents/rules/code.md`](.agents/rules/code.md) | 调试模式复用 code 规则 |

## 技能文件

AI agent 在执行任务前，必须检查是否有匹配的技能文件。每个技能定义了完整的分步开发流程。

| 技能 | 描述 | 触发条件 |
|:-----|:-----|:---------|
| [`develop-new-module`](.agents/skills/develop-new-module/SKILL.md) | 开发新功能模块（数据模型、业务逻辑、API、CLI） | 用户要求开发新 QCOS 后端功能模块 |
| [`develop-new-driver`](.agents/skills/develop-new-driver/SKILL.md) | 开发新量子设备驱动（基类继承、配置校验、远程API） | 用户要求接入新量子硬件设备 |
| [`develop-new-webui-page`](.agents/skills/develop-new-webui-page/SKILL.md) | 开发 WebUI 新页面（命名规范、目录结构、组件、路由、API 对接） | 用户要求在 WebUI 中新增前端页面 |

**技能检查流程：**

1. 评估用户请求是否匹配任一技能的描述
1. 若匹配，加载对应 `SKILL.md` 并按其中的步骤执行
1. 若不匹配，正常响应即可
1. 每次只加载一个最匹配的技能，不要预加载所有技能

## 目录结构速查

```
WuYueOs/
├── AGENTS.md                     # ← 本文件（AI agent 入口）
├── .agents/                      # AI agent 规则和技能
│   ├── README.md                 # .agents 目录说明
│   ├── rules/                    # 规则文件（core/code/ask）
│   ├── skills/                   # 技能定义
│   └── integrations/             # AI 工具集成说明
├── src/wy_qcos/                  # QCOS 后端主源码
│   ├── api/                      # RESTful API 接口层
│   ├── api_server.py             # API server 入口
│   ├── server.py                 # 服务主入口
│   ├── cloud/                    # 云端对接
│   ├── common/                   # 公共工具
│   ├── db/                       # 数据库模型和仓储
│   ├── device/                   # 设备管理
│   ├── driver/                   # 量子设备驱动
│   ├── engine/                   # 量子引擎（线路聚合/拆分/纠错等）
│   ├── flavor/                   # Flavor 调度策略
│   ├── libs/                     # 第三方库封装
│   ├── log/                      # 日志
│   ├── metrics/                  # 监控指标
│   ├── qec/                      # 量子纠错
│   ├── qem/                      # 量子误差缓解
│   ├── resource_manager/         # 资源管理
│   ├── scheduler/                # 任务调度
│   ├── task_manager/             # 任务管理
│   ├── tests/                    # 单元测试和系统测试
│   ├── transpiler/               # 量子线路转译
│   └── user/                     # 用户/权限
├── webui/                        # WebUI 前端工程（Vue 3 + Vite）
│   ├── src/
│   │   ├── api/                  # 后端 API 封装
│   │   ├── views/                # 页面组件
│   │   ├── router/               # 路由配置
│   │   ├── store/                # Pinia 状态
│   │   └── utils/                # 工具函数
│   ├── package.json
│   └── vite.config.js
├── src_cpp/                      # C++ 高性能组件（转译器）
├── etc/                          # 配置文件（qcos.toml、conf.d/）
├── docs/sphinx/source/           # Sphinx 文档源码
├── build-scripts/                # 构建和部署脚本（含 webui Dockerfile）
├── cicd/                         # CI/CD 脚本
├── requirements/                 # Python 依赖清单
├── samples/                      # 示例代码
└── plans/                        # 设计文档与规划
```

## 关键约定

1. **沟通语言**：始终使用中文交流
1. **代码注释**：仅允许使用英文
1. **Git 提交**：标题用英文（祈使句），描述用中文，遵循模板格式
1. **路径处理**：使用 `pathlib` 或 `os.path.join`，禁止硬编码路径
1. **换行符**：LF
1. **导入规范**：所有 import 在文件顶部，禁止函数内 import（`server.py` 延迟导入除外）
1. **敏感信息**：密码、Token 等必须脱敏处理，禁止明文输出

## 常用命令速查

```bash
# ===== 后端（Python） =====
# 安装依赖
pip install -r requirements.txt

# 代码风格检查（ruff）
ruff check src/
ruff format --check src/

# 运行单元测试
pytest src/wy_qcos/tests/

# 启动 API 服务
python -m wy_qcos.server

# ===== 前端（webui/） =====
cd webui

# 安装依赖
npm install

# 启动开发服务器（需先准备 /etc/qcos/qcos-webui.toml）
npm run dev

# 生产构建
npm run build:prod

# ESLint 检查
npm run lint
```

## 集成能力

QCOS 提供 [MCP (Model Context Protocol)](.agents/integrations/README.md) 服务，AI agent 可通过 MCP 工具直接对接运行中的 QCOS 系统，执行设备查询、作业提交、用户管理等操作。详见 [`.agents/integrations/README.md`](.agents/integrations/README.md)。

## 更多信息

- [项目 README](README.md)
- [.agents 目录说明](.agents/README.md)
- [Skills 技能索引](.agents/skills/README.md)
- [AI 工具集成说明](.agents/integrations/README.md)
- [设计文档](docs/sphinx/source/design/)
