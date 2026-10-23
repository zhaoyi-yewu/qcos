# Skills 技能索引

> 本目录包含 QCOS 项目所有 AI agent 技能定义。每个技能是一个独立目录，包含 `SKILL.md` 文件。

## 技能列表

| 技能名称 | 描述 | 适用场景 |
|:---------|:-----|:---------|
| [`develop-new-module`](develop-new-module/SKILL.md) | 开发新功能模块（数据模型、业务逻辑、API、CLI） | 新增 QCOS 功能模块 |
| [`develop-new-driver`](develop-new-driver/SKILL.md) | 开发新量子设备驱动（基类继承、配置校验、远程API） | 接入新量子硬件设备 |

## 技能文件格式

每个技能目录下的 `SKILL.md` 文件遵循以下格式：

> **关键要求：** YAML frontmatter 必须以 `---` 开头和结尾，`name`、`description`、`version` 三个字段各占一行。格式错误（如写成 Markdown 标题、全部挤在一行、缺少 `---` 分隔符）会导致 Zoo Code 无法解析技能元数据，技能不会出现在 "AVAILABLE SKILLS" 列表中。

```markdown
---
name: <skill-name>
description: <简短描述>
version: <版本号>
---

## Preconditions             # 前置条件（阅读的规则、文档）

## Instructions              # 分步指令
### 步骤 1: ...              # 按编号步骤执行

## 编码规范检查清单           # 完成后的自查清单

## 常见陷阱                   # 已知的坑和注意事项
```

## 使用方式

### AI Agent 自动加载

支持 AGENTS.md 标准的 AI agent（如 Zoo Code、Cursor、Kilo Code、Continue 等）会自动读取根目录的 [`AGENTS.md`](../../../AGENTS.md)，并根据任务匹配加载对应技能。

### 手动引用

在对话中引用技能文件路径即可，例如：

```
请按照 .agents/skills/develop-new-module/SKILL.md 中的流程开发 xxx 模块
```

## 新增技能

1. 在本目录下创建 `<skill-name>/` 子目录
1. 创建 `SKILL.md` 文件，包含 YAML frontmatter 和指令正文
1. 更新本 README.md 的技能列表表格
1. 更新根目录 `AGENTS.md` 的技能引用
