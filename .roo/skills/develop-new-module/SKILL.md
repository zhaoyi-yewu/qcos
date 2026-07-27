---
name: develop-new-module
description: 在 QCOS 项目中开发新功能模块，包含数据模型、业务逻辑、API 接口和 CLI 命令的完整开发流程
version: 1.0.0
---

## Preconditions

- 已阅读 `.roo/rules-code/rules.md` 编码规范
- 已阅读 `.roo/rules-ask/rules.md` 沟通规范
- 熟悉 QCOS 项目架构（参见 [`docs/sphinx/source/design/`](docs/sphinx/source/design/)）

## Instructions

在 QCOS 项目中开发一个包含数据模型、业务逻辑、API 接口和 CLI 命令的完整功能模块时，按以下步骤执行。

### 步骤总览

```
1. 需求分析 → 2. 设计文档 → 3. 基础设施 → 4. 核心逻辑
→ 5. 数据模型 → 6. API 层 → 7. 初始化集成 → 8. CLI 客户端
→ 9. 单元测试 → 10. 系统测试 → 11. 文档更新
```

### 步骤 1: 需求分析

- 阅读相关设计文档（`docs/sphinx/source/design/`）
- 分析现有代码结构，理解相关模块的实现方式
- 确定新模块与现有组件的交互关系
- 输出：需求清单和接口定义

### 步骤 2: 设计文档

- 在 `plans/` 目录编写设计文档（Markdown）
- 包含：架构图（Mermaid）、类关系图、时序图、数据模型设计
- 明确各组件职责和依赖关系
- 经用户确认后再进入实现阶段

### 步骤 3: 基础设施

创建模块目录结构和基础类：

```
src/wy_qcos/<module_name>/
├── __init__.py          # 模块导出
├── errors.py            # 自定义异常
├── <data_objects>.py    # 数据对象 (dataclass)
└── <base_classes>.py    # 基类/接口
```

**要点：**

- 数据对象使用 `@dataclass`，避免可变默认值
- 基类定义抽象方法，子类实现具体逻辑
- 异常继承 `wy_qcos.common.errors.BaseException`
- 文件头部统一版权声明
- 所有 import 在文件顶部

### 步骤 4: 核心逻辑

实现业务处理类：

```
src/wy_qcos/<module_name>/
├── <handler>.py         # 处理器/管理器
└── <impls>/             # 具体实现（如 filter/weigher 等）
    ├── __init__.py
    └── <impl>.py
```

**要点：**

- 参考现有设计模式（如 [`DriverManager`](src/wy_qcos/drivers/driver_manager.py) 插件加载模式）
- 支持通过配置启用/禁用组件
- 提供 registry 便于自动发现
- 方法注释使用英文，docstring 包含 Args/Returns

### 步骤 5: 数据模型

```
src/wy_qcos/db/models/<model>.py       # SQLAlchemy 模型
src/wy_qcos/db/repositories/<repo>.py   # Repository 数据库操作
src/wy_qcos/db/migration/alembic/versions/<migration>.py  # 迁移脚本
```

**要点：**

- 模型继承 `BaseTable`，注册到 [`db/models/__init__.py`](src/wy_qcos/db/models/__init__.py)
- Repository 继承 `BaseRepository`，复用 get_all/get_by_uuid 等方法
- Alembic 迁移脚本指定正确的 `down_revision`
- 新增字段需同时修改模型和迁移脚本

### 步骤 6: API 层

```
src/wy_qcos/api/schemas/<schema>.py              # Pydantic Schema
src/wy_qcos/api/posiq/routes_jsonrpc/<route>.py  # JSON-RPC 路由
```

**要点：**

- Schema 继承 `BaseModel` 或 `UuidMixin`
- 在 [`api/schemas/__init__.py`](src/wy_qcos/api/schemas/__init__.py) 中注册导出
- 路由使用 `@<api>_v1.method()` 装饰器注册
- 在 [`api/posiq/routes_jsonrpc/__init__.py`](src/wy_qcos/api/posiq/routes_jsonrpc/__init__.py) 中导入路由模块
- 路由复用 `job_api_v1` entrypoint 或在 `routes.py` 新增 entrypoint

### 步骤 7: 初始化集成

- 在 [`TaskScheduler`](src/wy_qcos/task_manager/task_scheduler.py) 中添加 setter 方法
- 在 [`server.py`](src/wy_qcos/server.py) 的 `run()` 方法中按正确顺序初始化
- 初始化顺序：Config → DriverManager → DeviceManager → DB → 新模块 → TaskManager

**要点：**

- 使用延迟导入避免循环依赖（`from wy_qcos.xxx import Yyy` 在方法内部）
- 初始化方法需在 `set_db_engine` 之后调用

### 步骤 8: CLI 客户端

```
src/wy_qcos_client/
├── client.py    # API 调用方法
└── shell.py     # CLI 命令定义和注册
```

**要点：**

- [`client.py`](src/wy_qcos_client/client.py)：添加 API 调用方法，参数使用 keyword-only（`*`）
- [`shell.py`](src/wy_qcos_client/shell.py)：
  - 在 `QcosShell` 中添加 `CMD_GROUP_<NAME>`
  - 命令类继承 `Command`/`ShowOne`/`Lister`
  - 使用 `CommandHelper.check_results()` 处理响应
  - 在 `# Register commands` 部分注册命令
- JSON 参数使用 `json.loads()` 解析，捕获 `JSONDecodeError`

### 步骤 9: 单元测试

```
src/wy_qcos/tests/unit_tests/<module_name>/
├── __init__.py       # 空（或极简）
├── test_<component1>.py
└── test_<component2>.py
```

**要点：**

- 测试类按组件分组：`TestXxxFilter`、`TestYyyWeigher`
- 使用 `unittest.mock.MagicMock` 模拟依赖
- 辅助函数 `make_xxx()` / `make_spec()` 构建测试数据
- 测试正常路径、边界条件、异常路径
- 运行命令：`python -m pytest src/wy_qcos/tests/unit_tests/<module>/ -v --tb=short --timeout=60`
- **注意**：不要把测试放在 `__init__.py` 中，pytest 默认不收集

### 步骤 10: 系统测试

在 `src/wy_qcos/tests/system_tests/` 下编写端到端集成测试：

```
src/wy_qcos/tests/system_tests/<module_name>/
├── __init__.py
├── conftest.py          # 测试 fixtures（如 mock api server）
└── test_<scenario>.py   # 端到端测试用例
```

**要点：**

- 参考现有系统测试结构（如 `system_tests/job/driver/`）
- 使用 `StLibrary` 封装 API 调用（参考 `system_tests/common/library.py`）
- 使用 mock api server 模拟后端设备（参考 `system_tests/job/driver/*/xxx_api_server.py`）
- 测试完整流程：提交作业 → 等待结果 → 验证状态
- 标记 `@pytest.mark.smoke` 用于冒烟测试，`@pytest.mark.slow` 用于慢测试
- 运行命令：`python -m pytest src/wy_qcos/tests/system_tests/<module>/ -v --tb=short`
- **注意**：系统测试需要完整的运行环境（Prefect、Redis、DB），确保环境就绪

### 步骤 11: 文档更新

**设计文档：**

- 更新 `docs/sphinx/source/design/module-design/` 下的相关 `.rst` 文档
- 从"规划"状态更新为实现状态
- 补充架构图、配置说明、使用示例

**API 接口文档：**

- 如有 API 变更，更新 `docs/sphinx/source/design/module-design/api/` 下的相关 `.rst` 文档
- 按组件对应文件：`job.rst`（作业）、`device.rst`（设备）、`user.rst`（用户）等
- 新增 API 接口需补充：请求参数、响应格式、错误码、使用示例
- 修改现有接口需同步更新参数说明和示例

**CLI 用户指南：**

- 更新 [`docs/sphinx/source/user-guide/cli/*.rst`](docs/sphinx/source/user-guide/cli/*.rst)，补充新增 CLI 命令的使用说明
- 包含命令语法、参数说明、使用示例

**CHANGELOG：**

- 在 [`CHANGELOG.md`](CHANGELOG.md) 中新增变更记录
- 格式参考现有条目，包含版本号、日期、变更类型（Added/Changed/Fixed/Removed）
- 描述新增功能、修改点、修复内容

## 编码规范检查清单

- [ ] PEP8 规范：4 空格缩进，snake_case，79 字符限制
- [ ] 文件头部版权声明
- [ ] 所有 import 在文件顶部（除延迟导入）
- [ ] 代码注释使用英文
- [ ] LF 换行符
- [ ] 路径使用 `pathlib` 或 `os.path.join`
- [ ] 无硬编码路径字符串
- [ ] shell.py 中可追加的参数使用 `nargs="+"` 形式，而非 `action="append"`
- [ ] 导入（import/from）必须放在文件开始处，不得在代码中间使用延迟导入

## 常见陷阱

1. **DeviceState 不可哈希**：dataclass 包含 `list`/`dict` 字段时默认不可哈希，不能作为 dict key，需改用索引方式
2. **pytest 不收集 `__init__.py`**：测试必须放在 `test_*.py` 文件中
3. **循环导入**：[`server.py`](src/wy_qcos/server.py) 初始化时使用延迟导入
4. **Schema 导出**：新增 Schema 必须在 [`api/schemas/__init__.py`](src/wy_qcos/api/schemas/__init__.py) 中导入，否则路由中 `schemas.XxxRequest` 找不到
5. **路由注册**：新增路由模块必须在 [`routes_jsonrpc/__init__.py`](src/wy_qcos/api/posiq/routes_jsonrpc/__init__.py) 中 `from . import xxx`
