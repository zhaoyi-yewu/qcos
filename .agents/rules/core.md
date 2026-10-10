# 核心规则（所有模式共享）

> 本文件定义所有 AI 模式（code、ask、architect、debug 等）共享的核心约束。
> 模式专用规则见同目录下的 `code.md`、`ask.md` 等文件。

## 1. 沟通约束

- **沟通语言**：始终使用中文交流。
- **回复风格**：极致精简。禁止闲聊、禁止任何开场白（如"好的"、"没问题"）和结束语。
- **回复结构**：直接输出结果。总结报告（如有）必须置于回复末尾的分割线后，严禁生成独立文件。

## 2. 环境与兼容性

- **运行环境**：Windows 系统。生成的终端指令必须兼容 PowerShell 或 Windows CMD。
- **文件格式**：必须使用 LF (Line Feed) 换行符。
- **权限模拟**：逻辑上设定文件模式为 chmod 644（非执行权限）。
- **路径处理**：禁止硬编码路径字符串，必须使用 `pathlib` 库或 `os.path.join` 确保 Windows 兼容性。

## 3. Git 提交规范

- **生成要求**：生成 Git commit message 时必须严格执行以下模板，严禁漏项。

- **语言约束**：标题（Title）必须使用**英文**（祈使句，首字母大写）；描述（Description）必须使用**中文**。

- **模板格式**：
  [English Title Here]

  Code Source From: Self Code
  AI Co-author: NONE

  Description:

  1. [中文描述变更点1]
  1. [中文描述变更点2]

  Jira: #[从分支或上下文中提取，无则填 NONE]
  市场项目编号（名称）：[从上下文中提取，无则填 NONE]

- **细节控制**：

  - **Description 拆解**：必须逻辑化拆分为多点（1. 2. 3.），每点独立成行。
  - **空行要求**：标题后、Description 后均必须保留一个标准空行。

## 4. 安全约束

- 密码、Token 等敏感信息不允许明文显示到日志或屏幕上。
- 必须打印时需调用 `Library._mask_connection_url`、`Library.mask_password` 或 `Library.mask_password_from_pydantic` 等方法进行脱敏处理。
- 禁止硬编码密码等敏感信息。
