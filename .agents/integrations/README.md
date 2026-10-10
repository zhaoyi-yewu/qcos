# AI 工具集成说明

> 本文件说明各类 AI 编码助手如何集成 `.agents/` 目录下的规则和技能。

## 集成原理

所有支持 [AGENTS.md 社区标准](https://agents.md) 的 AI 编码助手，都会自动读取项目根目录的 `AGENTS.md` 文件，并按其中的指引加载 `.agents/` 目录下的规则和技能。

## 支持的 AI 工具

### Zoo Code

Zoo Code 是一款 AI 编码助手，原生支持 AGENTS.md 社区标准，按模式（code/ask/architect/debug）加载对应的规则文件。

**集成方式：** 确保 `AGENTS.md` 在项目根目录，Zoo Code 会自动读取并按其中的指引加载 `.agents/` 下的规则和技能文件。无需额外配置。

**加载机制：**

1. 读取根目录 `AGENTS.md` 获取项目指引
1. 检查是否有匹配技能（`mandatory_skill_check`）
1. 按当前模式加载 `rules/<mode>.md` + `rules/core.md`
1. 按需加载 `skills/<skill-name>/SKILL.md`

### Continue.dev (.continue/)

Continue.dev 支持通过 `config.yaml` 引用项目级规则文件。

**配置位置：** [`.continue/agents/new-config.yaml`](../../.continue/agents/new-config.yaml)

**集成方式：** 在 Continue 配置中引用 `AGENTS.md` 内容作为 system prompt，或将 `.agents/rules/*.md` 路径加入上下文。

### Cursor (.cursor/)

Cursor 会自动读取项目根目录的 `AGENTS.md` 文件（如存在）。

**集成方式：** 确保 `AGENTS.md` 在项目根目录，Cursor 会自动加载。无需额外配置。

### Kilo Code (.kilo/)

Kilo Code 是一款开源 AI 编码助手，支持通过 AGENTS.md 标准加载项目规则和技能。

**集成方式：** 确保 `AGENTS.md` 在项目根目录，Kilo Code 会自动读取并按其中的指引加载 `.agents/` 下的规则和技能文件。无需额外配置。

### Roo Code (.roo/)

Roo Code 通过其 `.roo/` 配置目录加载规则和技能。本项目的 `.agents/` 目录与 Roo Code 兼容：

**对应关系：**
| `.agents/` 路径 | Roo Code 对应路径 |
|:----------------|:------------------|
| `.agents/rules/core.md` | `.roo/rules-core/rules.md` |
| `.agents/rules/code.md` | `.roo/rules-code/rules.md` |
| `.agents/rules/ask.md` | `.roo/rules-ask/rules.md` |
| `.agents/skills/<name>/SKILL.md` | `.roo/skills/<name>/SKILL.md` |

**注意：** 若同时使用 Roo Code，可在 `.roo/` 下创建符号链接或复制文件到对应位置。

### Claude Code (CLAUDE.md)

Claude Code 读取 `CLAUDE.md` 文件。可在 `CLAUDE.md` 中引用 `AGENTS.md`：

```markdown
# Claude Code Instructions

See [AGENTS.md](AGENTS.md) for project guidelines and available skills.
```

### GitHub Copilot (.github/copilot-instructions.md)

GitHub Copilot 读取 `.github/copilot-instructions.md` 文件。可在其中引用 `AGENTS.md`：

```markdown
# Copilot Instructions

See [AGENTS.md](../../AGENTS.md) for project guidelines and available skills.
```

## 兼容性矩阵

| AI 工具 | 读取 AGENTS.md | 读取 .agents/ | 额外配置 |
|:--------|:--------------|:---------------|:---------|
| Zoo Code | ✅ 原生支持 | ✅ 原生支持 | 无需 |
| Cursor | ✅ 原生支持 | ⚠️ 需 AGENTS.md 引用 | 无需 |
| Kilo Code | ✅ 原生支持 | ✅ 原生支持 | 无需 |
| Continue.dev | ⚠️ 需配置引用 | ⚠️ 需配置引用 | config.yaml |
| Roo Code | ❌ 需 .roo/ 映射 | ❌ 需 .roo/ 映射 | 符号链接 |
| Claude Code | ❌ 需 CLAUDE.md | ❌ 需 CLAUDE.md | CLAUDE.md |
| GitHub Copilot | ❌ 需 copilot 配置 | ❌ 需 copilot 配置 | copilot-instructions.md |

## 新增 AI 工具集成

1. 在对应工具的配置文件中引用根目录 `AGENTS.md`
1. 确保 AI 能访问 `.agents/rules/core.md` 和对应模式的规则文件
1. 确保 AI 能在任务匹配时加载 `.agents/skills/<name>/SKILL.md`
1. 在本文件补充集成说明和兼容性矩阵
