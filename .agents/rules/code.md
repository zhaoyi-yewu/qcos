# 代码模式规则（Code Mode）

> 本文件定义代码模式（code mode）专用规则。
> 核心规则见同目录下的 `core.md`，代码模式必须同时遵守 `core.md` 和本文件。

## 1. Python 编程规范（PEP8 & Standards）

- **代码标准**：严格执行 PEP8 规范。
- **命名规范**：变量/函数使用 snake_case，类名使用 PascalCase。
- **排版要求**：4空格缩进；函数间 1 空行，类间 2 空行；单行上限 79 字符。
- **导入规范**：严禁在函数/方法内部进行 import，所有库必须在文件顶部统一导入。
- **注释要求**：代码内部注释（Comments）仅允许使用英文。

## 2. 编码规范检查清单

每次编写或修改代码后，对照以下清单检查：

- [ ] PEP8 规范：4 空格缩进，snake_case，79 字符限制
- [ ] 文件头部版权声明
- [ ] 所有 import 在文件顶部（除 server.py 延迟导入）
- [ ] 代码注释使用英文
- [ ] LF 换行符
- [ ] 路径使用 `pathlib` 或 `os.path.join`
- [ ] 无硬编码路径字符串
- [ ] 无硬编码密码等敏感信息
- [ ] 密码脱敏处理（调用 `Library._mask_connection_url` 等方法）
- [ ] shell.py 中可追加参数使用 `nargs="+"`，而非 `action="append"`
- [ ] 导入（import/from）必须放在文件开始处，不得在代码中间使用延迟导入
- [ ] **严禁使用 `# noqa` 抑制 lint 错误**：发现 lint 报错必须从根本上修复代码，不得用 `# noqa`、`# ruff: noqa` 或 `# type: ignore` 等方式绕过检查。唯一例外是驱动测试文件中密码 secret 必须用 `# ruff: noqa: S105`（这是项目既有约定，新代码不得效仿）

## 3. 常见陷阱

1. **DeviceState 不可哈希**：dataclass 包含 `list`/`dict` 字段时默认不可哈希，不能作为 dict key
1. **pytest 不收集 `__init__.py`**：测试必须放在 `test_*.py` 文件中
1. **循环导入**：`server.py` 初始化时使用延迟导入
1. **Schema 导出**：新增 Schema 必须在 `api/schemas/__init__.py` 中导入
1. **路由注册**：新增路由模块必须在 `routes_jsonrpc/__init__.py` 中 `from . import xxx`
1. **venv 依赖冲突**：不同驱动 SDK 可能存在版本冲突，必须使用独立 venv
1. **远程 API 超时**：远程调用必须加超时保护，避免 worker 进程永久阻塞
1. **状态未恢复**：`run` 方法中设备状态设为 BUSY 后，无论成功失败都必须恢复为 ONLINE
