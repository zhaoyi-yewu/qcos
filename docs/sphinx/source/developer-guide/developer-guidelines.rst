项目开发规范
===================

本章节介绍了项目开发规范。

.. contents:: 目录
   :local:
   :depth: 3

编码规范
------------------

遵循Python3代码规范，包括: PEP8标准、并可使用ruff检查与修复命令：

- 命名规范（模块名小写 + 下划线 / 类名大驼峰 / 函数名小写 + 下划线 / 常量全大写）：

  - 模块名：driver_utils.py（正确）、DriverUtils.py（错误）
  - 类名：BaseDriver（正确）、base_driver（错误）
  - 函数名：parse_qasm_code()（正确）、ParseQasmCode()（错误）
  - 常量：MAX_RETRY_COUNT = 3（正确）、max_retry_count = 3（错误）
- 注释规范（函数需写Google风格的docstring、复杂逻辑加行注释、驱动类需标注适配设备型号）
- 文件版权声明：使用Mulan PSL v2许可的文件头，可参考同类文件的文件头

文档规范
------------------

- 部署、设计等文档放在docs/sphinx/source/下的对应目录中，以reStructuredText(rst)格式书写
- 文档中涉及到的流程图、时序图、架构图等UML图片，尽量以PlantUML语法书写

  - PlantUML文件(.puml)可以放在目录docs/sphinx/source/_static/下的对应目录中，然后在rst文件中引用
  - PlantUML语法可以参考：https://plantuml.com/zh/activity-diagram-beta
  - PlantUML在线预览：https://www.plantuml.com/plantuml/uml/ ，也可在PyCharm/VSCode等IDE中安装PlantUML相关插件来进行图片生成预览

接口开发规范
------------------

- 北向API规范：基于JSON-RPC 2.0格式、请求/响应字段要求、错误码定义

驱动开发规范
------------------

- 驱动文件需要放在 ``wy_qcos/driver/`` 目录下；通常可以在 drivers 目录下
  创建一个新目录来放驱动，建议为： ``wy_qcos/driver/厂商名英文缩写/`` 。
- 驱动文件名必须以 ``driver_`` 开头（如 ``driver_dummy.py``），
  DriverManager 在加载时通过 ``Library.import_classes`` 扫描
  ``wy_qcos/driver/`` 目录树，自动发现所有继承 ``DriverBase`` 的子类
  （排除基类），文件名不以 ``driver_`` 开头的模块会被跳过。
- 南向驱动接口规范：新增驱动必须实现 ``run()`` 等方法，参考
  ``wy_qcos/driver/dummy/driver_dummy.py``。
- 项目默认提供了丰富的驱动基类，如 ``DriverGateBase``、
  ``DriverPulseBase``、``DriverWuyueBase`` 和 ``DriverQuboBase`` 等，
  用户可以从中选择一个基类继承。
- ``__init__()`` 函数开发规范：``__init__()`` 函数用于初始化驱动类的
  成员变量。

.. code-block:: shell

    参数：
        version # 版本号
        transpiler # 驱动默认使用的转译器
        supported_transpilers # 驱动支持的转译器
        tech_type # 量子计算机的技术路线
        supported_basis_gates # 基础门列表，用于转译器模块的门分解
        supported_code_types # 支持的代码类型，如QASM2.0，QASM3.0等
        enable_circuit_aggregation # 是否支持电路聚合
        max_qubits # 驱动支持的最大比特数
        enable_device_mgr # 是否开启设备管理器，用于动态下发设备配置
        enable_device_monitor # 是否开启设备监控进程，获取设备动态运行信息
    返回值：
        None

- init_driver() 函数用于初始化驱动，并设置驱动状态为online
- validate_driver_configs() 函数用于校验驱动配置文件是否合理。如果校验失败则不会加载此驱动

.. code-block:: shell

    参数：
        configs # 配置数据
    返回值：
        success # 校验是否成功
        err_msg # 错误信息

- run() 函数用于提交量子任务到量子计算机，并获取量子任务结果。

.. code-block:: shell

    参数：
        job_id # 量子任务的ID
        num_qubits # 量子线路使用单比特数目
        data # 量子线路数据
        data_type # 量子线路数据类型
        shots # 量子线路执行次数
    返回值：
        None

- dry_run() 函数用于模拟提交量子任务的执行，并获取量子任务结果。

.. code-block:: shell

    参数：
        job_id # 量子任务的ID
        num_qubits # 量子线路使用单比特数目
        data # 量子线路数据
        data_type # 量子线路数据类型
        shots # 量子线路执行次数
    返回值：
        None

- fetch_running_info(): 如果使能enable_device_mgr或者enable_device_monitor，驱动类需要实现此函数。此函数的作用是获取设备运行信息。

.. code-block:: shell

    参数：
        None
    返回值：
        device_running_info # 设备运行信息字典

- close_driver(): 关闭驱动，清理资源。【可选】
- fetch_configs(): 用于执行作业前，先主动从设备处获取配置信息）【可选】
- cancel(): 用于主动对设备下发取消请求）【可选】
- set_results(): 设置量子任务结果

.. code-block:: shell

    参数：
        job_id: # 量子任务的ID
        data_index: # 量子线路index
        results # 量子任务结果
    返回值：
        None

- set_machine_time_info(): 设置量子计算机执行耗时数据结果

.. code-block:: shell

    参数：
        job_id: # 量子任务的ID
        data_index: # 量子线路index
        machine_time_info # 量子计算机执行耗时数据信息
    返回值：
        None

调度器 Filter / Weigher 开发规范
----------------------------------

QCOS 自动调度器（AutoScheduler）采用 Filter + Weigher 模式选择执行后端，
Filter 用于淘汰不满足条件的设备，Weigher 用于对剩余设备打分排序。
Filter 和 Weigher 类均通过 ``Library.import_classes`` 在启动时自动发现，
无需手动注册。

**Filter 开发：**

- Filter 文件放在 ``scheduler/filters/`` 目录下，文件名建议为
  ``<filter_name>.py``（如 ``my_filter.py``）。
- Filter 类需继承 ``BaseFilter``，并实现 ``_filter_one()`` 方法，
  返回 ``True`` 表示设备通过过滤。
- 所有 Filter 共享统一的初始化接口：Filter 类的 ``__init__()`` 不接受
  特殊参数。AutoScheduler 在实例化 Filter 后，会统一通过
  ``set_device_group_manager()`` 方法向每个 Filter 实例注入
  ``device_group_manager``。需要访问设备分组管理器的 Filter
  （如 ``DeviceGroupFilter``）应重写该方法来保存引用；
  不需要该管理器的 Filter 可直接使用 ``BaseFilter`` 中的默认空实现。
- 可选重写 ``is_enabled()`` 方法，根据 ``RequestSpec`` 动态启用/禁用。
- 新增 Filter 后无需修改任何注册表，AutoScheduler 初始化时会自动扫描
  ``scheduler/filters`` 目录发现该类。
- 若需将 Filter 加入默认列表，可将其添加到
  ``scheduler/filters/__init__.py`` 的 ``DEFAULT_FILTERS`` 中；
  也可在 ``qcos.toml`` 的 ``[SCHEDULER].ENABLED_FILTERS`` 中按类名启用。
- ``ENABLED_FILTERS`` 中重复的类名会被自动跳过（去重），
  ``DeviceGroupFilter`` 在被动态发现后会自动追加到过滤链末尾（去重）。

.. code-block:: python

    from wy_qcos.scheduler.filters.base import BaseFilter
    from wy_qcos.scheduler.device_state import DeviceState
    from wy_qcos.scheduler.request_spec import RequestSpec

    class MyFilter(BaseFilter):
        """My custom filter."""

        def _filter_one(
            self, obj: DeviceState, spec: RequestSpec
        ) -> bool:
            # return True to keep the device
            return obj.some_attribute >= spec.threshold

**Weigher 开发：**

- Weigher 文件放在 ``scheduler/weighers/`` 目录下。
- Weigher 类需继承 ``BaseWeigher``，并实现 ``_weigh_object()`` 方法，
  返回权重值（越大越优先）。
- 可通过类属性 ``multiplier`` 控制该 Weigher 的整体权重倍率。
- 新增 Weigher 后无需手动注册，AutoScheduler 会自动扫描
  ``scheduler/weighers`` 目录发现该类。
- 默认列表管理同 Filter，在 ``scheduler/weighers/__init__.py`` 的
  ``DEFAULT_WEIGHERS`` 或配置文件 ``ENABLED_WEIGHERS`` 中配置。
- ``ENABLED_WEIGHERS`` 中重复的类名会被自动跳过（去重）。

.. code-block:: python

    from wy_qcos.scheduler.weighers.base import BaseWeigher
    from wy_qcos.scheduler.device_state import DeviceState
    from wy_qcos.scheduler.request_spec import RequestSpec

    class MyWeigher(BaseWeigher):
        """My custom weigher."""

        multiplier: float = 1.0

        def _weigh_object(
            self, obj: DeviceState, spec: RequestSpec
        ) -> float:
            # higher weight = more preferred
            return float(obj.some_score)

设备配置文件规范
------------------

- 驱动内可以选择读取该设备的专属独立配置，qcos容器启动时，会自动读取
  ``/etc/qcos/conf.d/`` 目录下的设备配置文件。
- 相关示例代码可放在源代码目录的 ``etc/qcos/conf.d/`` 目录下。
- QCOS容器启动时，``entrypoint.sh`` 会自动把源代码目录的
  ``etc/qcos/conf.d/`` 目录下复制到 ``/etc/qcos/conf.d/`` 中，
  如果配置文件已存在则不会复制。
- 设备配置文件为 toml 格式，格式可参考 ``dummy.toml``。
- 【必选】配置文件必须声明设备名称、别名、设备对应的驱动名称和设备描述。

.. code-block:: shell

    [dummy] # 设备名称 (建议设备名为小写字母、数字、下划线组成，不允许空格)
    alias_name = "空载测试设备" # 别名
    driver = "DriverDummy" # 驱动名称，须与动态发现的驱动类名一致
    description = "空载测试设备(dummy)" # 设备描述

  其中 ``driver`` 字段的值须与 DriverManager 通过
  ``Library.import_classes`` 动态扫描发现的驱动类名（即 ``DriverBase``
  子类的类名）完全一致，否则设备将无法找到对应的驱动而加载失败。

- 【可选】配置文件中可以配置debug字段，debug字段是设备是日志控制开关, 用于控制设备日志的开关
- 【可选】配置文件中可以配置日志文件保存路径

.. code-block:: shell

    device_log_file # 设备日志
    monitor_log_file # 设备监控日志，需要使能驱动类中的enable_device_monitor字段
    mgr_log_file # 设备管理日志，需要使能驱动类中的enable_device_mgrr字段

- 【可选】配置文件中可以配置日志相关字段

.. code-block:: shell

    log_format # 日志格式
    log_rotate_max_size_mb # 日志文件单文件最大大小
    log_rotate_backup_count # 日志保留备份文件数量
    log_rotate_compression # 是否压缩历史日志

- 【可选】设备配置中涉及到密码加密的，可以使用encrypt-password.py获取加密后的密文，填入配置文件相关密码字段中：

.. code-block:: shell

    # 密码加密命令
    cd bin
    ./encrypt-password.py -e my_password

- 【可选】配置文件中可以配置 device_max_qubits
- 【可选】配置文件中可以配置 max_queued_jobs。-1 表示不现在排队的任务数量
- 用户可以根据自己的设备特性添加字段，如用户名，密码，ip地址，端口号，token和coupler_map等。
- 添加配置文件后，需要在/etc/qcos/qcos.toml将设备名字写入DEVICE_LIST
