# AI Programming & Git Instructions (.ai-rules)

## 1. 核心约束 (Core Constraints)

- **沟通语言**：始终使用中文交流。
- **回复风格**：极致精简。禁止闲聊、禁止任何开场白（如“好的”、“没问题”）和结束语。
- **回复结构**：直接输出结果。总结报告（如有）必须置于回复末尾的分割线后，严禁生成独立文件。

## 2. Python 编程规范 (PEP8 & Standards)

- **代码标准**：严格执行 PEP8 规范。
- **命名规范**：变量/函数使用 snake_case，类名使用 PascalCase。
- **排版要求**：4空格缩进；函数间 1 空行，类间 2 空行；单行上限 79 字符。
- **导入规范**：严禁在函数/方法内部进行 import，所有库必须在文件顶部统一导入。
- **注释要求**：代码内部注释（Comments）仅允许使用英文。

## 3. 环境与兼容性 (Environment & OS)

- **运行环境**：Windows 系统。生成的终端指令必须兼容 PowerShell 或 Windows CMD。
- **文件格式**：必须使用 LF (Line Feed) 换行符。
- **权限模拟**：逻辑上设定文件模式为 chmod 644（非执行权限）。
- **路径处理**：禁止硬编码路径字符串，必须使用 `pathlib` 库或 `os.path.join` 确保 Windows 兼容性。

## 4. Git 提交规范 (Git Commit Standards)

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
