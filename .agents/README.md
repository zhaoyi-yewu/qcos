# .agents 目录说明

> 本目录遵循 [AGENTS.md 社区标准](https://agents.md)，为各类 AI 编码助手提供统一的项目规范、规则和技能定义。

## 目录结构

```
.agents/
├── README.md                     # 本文件：目录结构和用途说明
├── rules/                        # AI agent 规则定义
│   ├── core.md                   # 核心规则（所有模式共享）
│   ├── code.md                   # 代码模式（code）专用规则
│   └── ask.md                    # 问答模式（ask）专用规则
├── skills/                       # AI agent 技能定义
│   ├── README.md                 # Skills 索引和使用说明
│   ├── develop-new-module/       # 新功能模块开发技能
│   │   └── SKILL.md
│   └── develop-new-driver/       # 新量子设备驱动开发技能
│       └── SKILL.md
└── integrations/                 # 各 AI 工具集成说明
    └── README.md
```

## 规则文件说明

| 文件 | 适用模式 | 说明 |
|:-----|:---------|:-----|
| `rules/core.md` | 所有模式 | 沟通语言、回复风格、环境兼容性、Git 提交规范、安全约束 |
| `rules/code.md` | code（代码） | PEP8 规范、编码检查清单、常见陷阱 |
| `rules/ask.md` | ask（问答） | 回答原则、分析原则、文档引用规范 |

## 技能文件说明

每个技能位于 `skills/<skill-name>/SKILL.md`，使用 YAML frontmatter 定义元数据：

```yaml
---
name: <skill-name>
description: <简短描述>
version: <版本号>
---
```

技能文件正文包含：Preconditions（前置条件）、Instructions（分步指令）、检查清单、常见陷阱。

## 与 AGENTS.md 的关系

根目录下的 [`AGENTS.md`](../../AGENTS.md) 是 AI agent 的入口文件，指向本目录。AI agent 读取 AGENTS.md 后，按指引加载 `rules/` 和 `skills/` 中的内容。
