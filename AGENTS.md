# AGENTS.md - QCOS AI Agent 指引

> 本文件遵循 [AGENTS.md 社区标准](https://agents.md)，为各类 AI 编码助手提供 QCOS 项目的统一指引。
> AI agent 在开始任何任务前，必须先阅读本文件。

## 项目概述

**WUYUEQbit 量子计算操作系统（QCOS）** 是一款开源通用量子计算操作系统，为不同架构的量子计算机（超导、中性原子、离子阱、光量子等）提供统一软件支持。

- **主语言**：Python（PEP8 规范）
- **运行环境**：Windows / Linux（BCLinux 21.10U4、OpenEuler 24.03 LTS）
- **许可证**：MulanPSL-2.0
- **在线文档**：https://qcos.readthedocs.io

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
| [`develop-new-module`](.agents/skills/develop-new-module/SKILL.md) | 开发新功能模块（数据模型、业务逻辑、API、CLI） | 用户要求开发新 QCOS 功能模块 |
| [`develop-new-driver`](.agents/skills/develop-new-driver/SKILL.md) | 开发新量子设备驱动（基类继承、配置校验、远程API） | 用户要求接入新量子硬件设备 |

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
├── src/wy_qcos/                  # QCOS 主源码
│   ├── driver/                   # 量子设备驱动
│   ├── engine/                   # 量子引擎（线路聚合/拆分/纠错等）
│   ├── api/                      # API 接口层
│   ├── db/                       # 数据库模型和仓储
│   └── tests/                    # 单元测试和系统测试
├── etc/                          # 配置文件（qcos.toml、conf.d/）
├── docs/sphinx/source/           # Sphinx 文档源码
├── build-scripts/                # 构建和部署脚本
└── cicd/                         # CI/CD 脚本
```

## 关键约定

1. **沟通语言**：始终使用中文交流
1. **代码注释**：仅允许使用英文
1. **Git 提交**：标题用英文（祈使句），描述用中文，遵循模板格式
1. **路径处理**：使用 `pathlib` 或 `os.path.join`，禁止硬编码路径
1. **换行符**：LF
1. **导入规范**：所有 import 在文件顶部，禁止函数内 import（`server.py` 延迟导入除外）
1. **敏感信息**：密码、Token 等必须脱敏处理，禁止明文输出

## 更多信息

- [项目 README](README.md)
- [.agents 目录说明](.agents/README.md)
- [Skills 技能索引](.agents/skills/README.md)
- [AI 工具集成说明](.agents/integrations/README.md)
- [设计文档](docs/sphinx/source/design/)
