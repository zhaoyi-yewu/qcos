---
name: develop-new-driver
description: 在 QCOS 项目中开发新的量子设备驱动，包含驱动基类继承、配置校验、远程API对接、单元测试和系统测试的完整开发流程
version: 1.0.0
---

## Preconditions

- 已阅读 `.roo/rules-code/rules.md` 编码规范
- 已阅读 `.roo/rules-ask/rules.md` 沟通规范
- 熟悉 QCOS 项目架构（参见 [`docs/sphinx/source/design/`](docs/sphinx/source/design/)）

## Instructions

在 QCOS 项目中开发一个新的量子设备驱动时，按以下步骤执行。

### 步骤总览

```
1. 需求分析 → 2. 选择基类 → 3. 创建驱动目录
→ 4. 实现驱动类 → 5. 配置与注册 → 6. venv 部署
→ 7. 单元测试 → 8. 系统测试 → 9. 文档更新
```

### 步骤 1: 需求分析

- 确认量子设备的厂商、型号、技术路线（超导/中性原子/离子阱/核磁/模拟器等）
- 确认设备 SDK/API 的调用方式（REST API / gRPC / SDK 包 / 本地模拟等等）
- 确认设备支持的量子比特数、门集、code type（QASM/QASM2/QASM3/QUBO等）
- 确认设备是否支持校准、监控、设备管理等功能
- 输出：需求清单和接口定义

### 步骤 2: 选择基类

QCOS 驱动继承体系（`src/wy_qcos/driver/`）：

```
DriverBase (driver_base.py)                   # 驱动基类
├── DriverGateBase (driver_gate_base.py)      # 门级驱动基类，支持 QASM
│   ├── DriverDummy (dummy/)                  # 空载测试
│   ├── DriverQuafuBase (quafu/)              # 北京量子院夸父
│   ├── DriverCetcBase (cetc/)                # 国基量子
│   ├── DriverLogicalQubitBase (logical_qubit/) # 逻辑比特
│   └── DriverQutipSim (qutip/)               # Qutip模拟器
│   └── DriverQudoorBase (qudoor/)            # 启科量子
├── DriverPulseBase (driver_pulse_base.py)    # 脉冲级驱动基类
├── DriverQuboBase (driver_qubo_base.py)      # QUBO驱动基类，支持 QUBO
└── DriverWuyueBase (driver_wuyue_base.py)    # 五岳平台驱动基类
```

**选择规则：**

- 设备支持 QASM 2.0/3.0 门级操作 → 继承 `DriverGateBase`
- 设备支持脉冲级操作 → 继承 `DriverPulseBase`
- 设备是 QUBO 求解器 → 继承 `DriverQuboBase`
- 设备是五岳云平台版本 → 继承 `DriverWuyueBase`

参考现有驱动实现：[`DriverDummy`](src/wy_qcos/driver/dummy/driver_dummy.py) 是最简单的参考实现。

### 步骤 3: 创建驱动目录

```
src/wy_qcos/driver/<vendor厂商>/
├── __init__.py
└── driver_<name>.py       # 主驱动文件
```

**目录命名规范：**

- 按厂商命名，如 `quafu/`、`cetc/`、`qutip/`、`spinq/`
- 驱动文件名格式：`driver_<name>.py`，如 `driver_quafu_dongling.py`
- 驱动类名格式：`Driver<Name>`，如 `DriverQuafuDongling`、`DriverCetcBaihua`

**要点：**

- 文件头部统一版权声明
- `__init__.py` 可为空

### 步骤 4: 实现驱动类

参考 [`DriverDummy`](src/wy_qcos/driver/dummy/driver_dummy.py) 和
[`DriverQuafuBase`](src/wy_qcos/driver/quafu/driver_quafu_base.py) 实现。

**4.1 `__init__` 设置驱动属性**

```python
class DriverXXX(DriverGateBase):
    """驱动描述.

    Vendor/Model driver
    """

    def __init__(self):
        super().__init__()
        self.version = "0.0.1"
        self.alias_name = "厂商-型号 驱动"
        self.description = "厂商-型号 驱动描述"
        self.tech_type = Constant.TECH_TYPE_SUPERCONDUCTING  # 量子技术路线
        self.transpiler = Constant.TRANSPILER_CMSS  # 默认转译器
        self.supported_basis_gates = [  # 量子设备支持的基础门列表
            Constant.SINGLE_QUBIT_GATE_H,
            Constant.SINGLE_QUBIT_GATE_RX,
            # ...
        ]
        self.supported_transpilers = [  # 支持的转译器列表
            Constant.TRANSPILER_CMSS,
        ]
        self.max_qubits = 100  # 设备支持的最大量子比特数量
        self.enable_circuit_aggregation = False  # 是否支持线路切割
        self.default_data_type = DriverBase.DATA_TYPE_QASM2  # 默认支持大QASM类型
        self.results_fetch_mode = Constant.RESULTS_FETCH_MODE_SYNC  # 结果获取方式 (同步(轮询)/异步(主动上报))
```

**4.2 `init_driver` 初始化连接**

```python
def init_driver(self):
    """Init driver."""
    self.set_device_status(Device.DEVICE_STATUS_ONLINE)
```

**4.3 `validate_driver_configs` 校验设备配置**

定义 `schema` 校验规则，验证设备配置文件（`etc/conf.d/<device>.toml`）中的参数：

```python
def validate_driver_configs(self, configs):
    """Validate driver configs."""
    success = True
    err_msg = None
    driver_config_schema = {
        "ip_address": str,
        "port": int,
        "token": str,
        Optional("timeout"): int,
    }
    success, err_msg = Library.validate_schema(
        configs, driver_config_schema
    )
    return success, err_msg
```

**4.4 `fetch_configs` 获取远程配置**

从设备远程 API 获取动态配置（如校准数据、QPU 配置等）：

```python
def fetch_configs(self):
    """Fetch configs from remote device."""
    extra_configs = self.get_configs()
    self.token = extra_configs.get("token", "")
    self.url = extra_configs.get("url", "")
    # 调用设备 SDK/API 获取远程配置
    # ...
```

**4.5 `fetch_running_info` 获取运行状态**

供 device monitor 轮询设备状态：

```python
def fetch_running_info(self):
    """Fetch running info."""
    return {"status": Device.DEVICE_STATUS_ONLINE}
```

**4.6 `run` 执行量子作业**

核心方法，提交量子电路并获取结果：

```python
def run(self, job_id, num_qubits, data, data_type, shots=1, qec_options=None):
    """Run job."""
    # 1. Convert code (if needed)
    final_code = self.convert_code(num_qubits, data["source_code"], data["transpile_results"])

    # 2. Submit task to device
    task_id = self.submit_task(final_code, shots)

    # 3. Wait for task completion
    success, _, _ = Library.loop_with_timeout(
        self.check_task_status,
        self.max_job_wait_time,
        self.job_query_interval,
        task_id,
    )

    # 4. Get and normalize results
    raw_results = self.get_task_results(task_id)
    results = self.convert_results(raw_results)
    self.set_results(job_id, data["index"], results=results,
                     result_type=Constant.RESULT_TYPE_SAMPLING)

    # 5. Set device status back to ONLINE
    self.set_device_status(Device.DEVICE_STATUS_ONLINE)
```

**4.7 `input_constrains` 定义调度约束**

声明作业参数的约束 schema，供 `InputConstraintsFilter` 校验：

```python
self.input_constrains["job_shots"] = Schema(
    And(int, lambda x: 1 <= x <= 50000)
)
```

**4.8 `driver_options_schema` 驱动选项 schema**

声明 `driver_options` 的可选参数 schema：

```python
self.driver_options_schema.update({
    Optional("enable_wirecut"): bool,
    Optional("max_qubits"): int,
})
```

**4.9 `transpiler_options_schema` 转译器选项 schema**

声明转译器选项的可选参数 schema（继承自 `DriverGateBase`，按需扩展）：

```python
self.transpiler_options_schema["enable_mapping"] = (
    Optional("enable_mapping", default=True), bool,
)
```

### 步骤 5: 配置与注册

**5.1 添加设备配置文件**

在 `etc/conf.d/` 下创建设备配置文件（TOML 格式），YYY为设备名，保证driver=后的Driver名称和4.1中的驱动类名DriverXXX一致：

```toml
# etc/conf.d/YYY.toml
[YYY]
alias_name = "YYY 超导量子计算机"
driver = "DriverXXX"
description = "YYY超导量子计算机"

# [Optional] debug
# debug = false

# [Optional] device log file path
# device_log_file = /var/log/qcos/device_YYY.log

# [Optional] device monitor log file path
# monitor_log_file = /var/log/qcos/device_YYY.log

# [Optional] max queued jobs, -1 means unlimited
# max_queued_jobs = -1

# [Optional] max job wait time, default value is 604800 seconds (7 days)
# max_job_wait_time = 604800

# [Optional] job query interval, default value is 5 seconds
# job_query_interval = 5

ip_address = "192.168.1.100"
port = 8080
token = "your-token"
timeout = 30

[YYY.transpiler.qpu_configs]   # 可选，默认初始化QPU配置信息
...
```

在 `etc/qcos/qcos.toml` 的 `DEVICE_LIST` 中添加设备名：

```toml
DEVICE_LIST = ["dummy", "YYY"]
```

**5.2 添加驱动 venv 配置**

如果驱动中需要调用QCOS系统没有默认安装的特殊第三方库（比如：厂商自己的SDK），可以在 `requirements/venv-configs.toml` 中添加驱动的 venv 配置：

```toml
[DriverXXX]
module_name = "driver_xxx"
deps_pyproject_file = "../pyproject.toml"
deps_sections = ["driver-xxx"]
envs = ["python3"]
```

在 `pyproject.toml` 的 `[project.optional-dependencies]` 中添加依赖分区：

```toml
driver-xxx = [
    "vendor-XXX-sdk==1.0.0",  # 如果要在驱动中调用厂商SDK或其它依赖组件，可以在这里指定
]
```

安装驱动 venv（详见 :doc:`../design/module-design/venv`）：

```shell
# 可以手动在研发环境下通过下列命令安装，也可以在编译QCOS base镜像时，由编译脚本自动安装
$ python3 requirements/install-venvs.py --name DriverXXX
```

### 步骤 6: venv 部署

详见 :doc:`../design/module-design/venv`。

要点：
- 每个驱动使用独立 venv 避免依赖冲突
- Prefect worker 进程在对应 venv 中加载驱动模块
- 调试时 source 对应 venv 环境

### 步骤 7: 单元测试

```
src/wy_qcos/tests/unit_tests/driver/<vendor>
├── test_driver_xxx.py
```

**要点：**

- 使用 `unittest.mock` 模拟远程 API 调用
- 测试 `validate_driver_configs`：正常配置、缺失字段、非法值
- 测试 `run`：正常流程、提交失败、超时、结果解析
- 测试 `fetch_configs`：远程 API 返回解析
- 参考 [`test_driver_quafu.py`](src/wy_qcos/tests/unit_tests/driver/test_driver_quafu.py)
- 运行：`python -m pytest src/wy_qcos/tests/unit_tests/driver/quafu/test_driver_xxx.py -v` 或者 `cicd/run-tests.sh -u src/wy_qcos/tests/unit_tests/driver/<vendor>/test_driver_xxx.py`

### 步骤 8: 系统测试

```
src/wy_qcos/tests/system_tests/job/driver/<vendor>/
├── __init__.py
├── <name>_api_server.py   # mock API server
└── test_job.py            # 端到端测试
```

**要点：**

- 编写 mock API server 模拟设备后端（参考
  `system_tests/job/driver/quafu/quafu_api_server.py`）
- **端口选择**：`cls.api_port` 不要和常用端口（如 80/443/8080
  等）或其他 ST 已使用的端口重复，建议使用 18xxx 范围
- **mock API server 启动方式**：在 `setup_class` 中通过
  `multiprocessing.Process` 以 daemon 模式启动，ST 测试完成后
  自动结束进程；也可以独立拉起 mock API server 用于手动调试
- 在 `setup_class` 中：

  - `StLibrary.cleanup_test_jobs(client, test_job_names)`
    清理上次残留的测试作业
  - 启动 mock API server（daemon 模式）
  - 等待 mock API server 就绪
    （`Library.wait_network_connection`）
  - `set_device(backend, state="online")` 初始化设备状态，
    防止上次测试遗留的 state 影响

- 在 `teardown_class` 中：

  - `StLibrary.cleanup_test_jobs(client, test_job_names)`
    清理本次测试创建的作业，防止资源残留
  - `set_device(backend, state="auto")` 恢复设备状态为自动模式
  - 停止 mock API server 进程（`process.terminate()`）

- 测试方法中提交作业后，在 `finally` 块中清理作业和恢复设备状态
- 测试完整流程：提交作业 → 等待结果 → 验证状态
- 运行：`python -m pytest
  src/wy_qcos/tests/system_tests/job/driver/<vendor>/ -v`
  或者 `cicd/run-tests.sh -s
  src/wy_qcos/tests/system_tests/job/driver/<vendor>/`

**`setup_class` / `teardown_class` 示例：**

.. code-block:: python

    class TestJob:
        test_job_names = ["test_xxx_submit_job"]

        @classmethod
        def setup_class(cls):
            cls.admin_client = GLOBAL_CONFIGS["admin_client"]
            # cleanup jobs from previous test runs
            StLibrary.cleanup_test_jobs(
                cls.admin_client, cls.test_job_names
            )
            # init device state to online
            cls.admin_client.set_device(
                "xxx_device", enable=True, state="online"
            )

        @classmethod
        def teardown_class(cls):
            # cleanup jobs created by this test
            StLibrary.cleanup_test_jobs(
                cls.admin_client, cls.test_job_names
            )
            # restore device state to auto
            cls.admin_client.set_device(
                "xxx_device", enable=True, state="auto"
            )

### 步骤 9: 文档更新

**兼容性文档：**

- 在 [`COMPATIBILITY.md`](COMPATIBILITY.md) 的驱动兼容性表格中添加新驱动行

**CHANGELOG：**

- 在 [`CHANGELOG.md`](CHANGELOG.md) 中新增变更记录

## 编码规范检查清单

- [ ] PEP8 规范：4 空格缩进，snake_case，79 字符限制
- [ ] 文件头部版权声明
- [ ] 所有 import 在文件顶部
- [ ] 代码注释使用英文
- [ ] LF 换行符
- [ ] 路径使用 `pathlib` 或 `os.path.join`
- [ ] 无硬编码密码等敏感信息
- [ ] 密码不允许明文显示到日志或屏幕上，必须打印时需调用 `Library._mask_connection_url`、`Library.mask_password` 或 `Library.mask_password_from_pydantic` 等方法进行脱敏处理
- [ ] 导入（import/from）必须放在文件开始处，不得在代码中间使用延迟导入
- [ ] 远程 API 调用必须有超时保护（使用 `Library.loop_with_timeout`）
- [ ] `set_device_status` 在 `run` 结束时恢复为 ONLINE
- [ ] `input_constrains` 声明了作业参数约束

## 常见陷阱

1. **venv 依赖冲突**：不同驱动 SDK 可能存在版本冲突，必须使用独立 venv
2. **远程 API 超时**：`fetch_configs`、`run` 中的远程调用必须加超时保护，避免 worker 进程永久阻塞
3. **状态未恢复**：`run` 方法中设备状态设为 BUSY 后，无论成功失败都必须恢复为 ONLINE
4. **schema 校验遗漏**：`validate_driver_configs` 必须校验所有必需字段，使用 `Optional` 标记可选字段
5. **transpiler_options_schema 未覆盖**：驱动特有的转译器选项必须在 `__init__` 中通过 `self.transpiler_options_schema` 声明
6. **驱动配置文件名不匹配**：`etc/conf.d/` 下的文件名必须与 `qcos.toml` 中 `DEVICE_LIST` 的设备名一致
