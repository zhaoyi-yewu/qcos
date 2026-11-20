版本管理接口
================

版本接口用于协商API版本号、获取系统版本、能力以及各重要参数的枚举值。

**注意**：该API的url中没有版本前缀

.. list-table:: 版本管理接口规范
   :widths: 20 20 30 30
   :header-rows: 1
   :align: left
   :class: longtable

   * - 用途
     - 方法
     - 请求参数
     - 返回值
   * - **版本和能力信息获取**

       可供前端界面获取各参数可选值
     - **version**

       URI: /version
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "id": 1,
               "method": "version",
               "params": {
               "body": {}
               }
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "result": {
                 "version": "1.0.0",
                 "api_version": "v1",
                 "supported_api_versions": [
                   {
                     "version": "v1",
                     "status": "CURRENT"
                   }
                 ],
                 "platform_version": "WUYUEQbit量子计算操作系统(qcos) v1.0.0",
                 "capabilities": {
                   "job_types": [
                     "sampling",
                     "estimation"
                   ],
                   "drivers": {
                     "DriverHanyuan1": {
                       "supported_code_types": null,
                       "description": "中科酷原-汉原1 中性原子驱动"
                     },
                     "DriverCirqSim": {
                       "supported_code_types": null,
                       "description": "Cirq Simulator 模拟器驱动"
                     },
                     "DriverTiangong100": {
                       "supported_code_types": [
                         "qubo"
                       ],
                       "description": "玻色量子-天工100 光量子伊辛机驱动"
                     },
                     "DriverQiskitAerSim": {
                       "supported_code_types": null,
                       "description": "Qiskit Aer 模拟器驱动"
                     },
                     "DriverQiskitQasmSim": {
                       "supported_code_types": null,
                       "description": "Qiskit Qasm 模拟器驱动"
                     },
                     "DriverDummy": {
                       "supported_code_types": null,
                       "description": "空载测试驱动(中性原子)"
                     }
                   },
                   "transpilers": {
                     "cmss": {
                       "alias_name": "五岳转译器",
                       "supported_code_types": [
                         "qasm",
                         "qasm2"
                       ]
                     },
                     "dummy": {
                       "alias_name": "空载转译器(dummy)",
                       "supported_code_types": [
                       ]
                     },
                     "qiskit": {
                       "alias_name": "IBM Qiskit",
                       "supported_code_types": [
                         "qasm",
                         "qasm2",
                         "qasm3"
                       ]
                     }
                   },
                   "tech_types": {
                     "none": {
                       "alias_name": "无"
                     },
                     "neutral_atom": {
                       "alias_name": "中性原子"
                     },
                     "ion_trap": {
                       "alias_name": "离子阱"
                     },
                     "superconducting": {
                       "alias_name": "超导"
                     },
                     "photon": {
                       "alias_name": "光量子"
                     },
                     "generic_simulator": {
                       "alias_name": "通用量子模拟器"
                     }
                   },
                   "profiling": {
                     "all": {
                       "alias_name": "使能所有性能评估类型"
                     },
                     "code": {
                       "alias_name": "作业中单代码执行耗时"
                     },
                     "schedule": {
                       "alias_name": "调度器耗时"
                     },
                     "driver:parse": {
                       "alias_name": "代码解析耗时"
                     },
                     "driver:transpile": {
                       "alias_name": "转译器耗时"
                     },
                     "driver:run": {
                       "alias_name": "后端运行耗时"
                     }
                   },
                   "driver_transpiler_mappings": {
                     "DriverHanyuan1": [
                       "cmss"
                     ],
                     "DriverCirqSim": [
                       "dummy"
                     ],
                     "DriverTiangong100": [],
                     "DriverQiskitAerSim": [
                       "qiskit"
                     ],
                     "DriverQiskitQasmSim": [
                       "qiskit"
                     ],
                     "DriverDummy": [
                       "cmss"
                     ]
                   }
                 }
               },
               "id": 1
             }

版本协商详解
~~~~~~~~~~~~

API 版本管理
^^^^^^^^^^^^

系统支持多个API版本，允许客户端与不同版本的服务器兼容：

- **当前版本 (CURRENT)**：正在活跃使用的API版本
- **废弃版本 (DEPRECATED)**：即将停止支持的版本
- **支持期**：通常为新版本发布后的6个月

能力枚举 (Capabilities)
^^^^^^^^^^^^^^^^^^^^^^^

``capabilities`` 字段包含系统支持的各种功能和类型：

1. **job_types**：系统支持的作业类型
   - ``sampling``：采样作业，获取量子电路的测量结果
   - ``estimation``：估计作业，评估电路性能

2. **drivers**：可用的驱动程序列表
   - 包含驱动名称、支持的代码类型和描述

3. **transpilers**：可用的转译器列表
   - 包含转译器别名和支持的代码类型

4. **tech_types**：支持的量子技术类型
   - 中性原子、离子阱、超导、光量子等

5. **profiling**：性能评估类型
   - 用于了解作业执行性能

6. **driver_transpiler_mappings**：驱动与转译器的对应关系
   - 指定每个驱动支持的转译器

高级参数 Schema（capabilities.schemas）
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

请求体中的 ``body.details`` 为 ``true`` 时，``capabilities`` 额外包含
``schemas``。该字段只描述参数名称、类型、展示信息和必要约束，不替换
``drivers[name].driver_options`` 中的现有默认值，也不改变 ``submit_job``
的后端校验行为。``details`` 为 ``false`` 时仍返回 ``capabilities=null``。

六个入口及索引规则如下：

.. list-table:: 高级参数 Schema 入口
   :widths: 24 44 32
   :header-rows: 1

   * - 入口
     - 内容
     - 索引方式
   * - ``driver_options``
     - 当前已加载 Driver 的提交参数
     - ``driver_options[driverName]``
   * - ``transpiler_options``
     - 与 ``capabilities.transpilers`` 相同的转译器集合
     - ``transpiler_options[transpilerName]``
   * - ``options``
     - 线路拆分、QUBO 拆分和精度约减通用开关
     - 直接返回一个 Schema
   * - ``qem_options``
     - ``readout``、``rem``、``zne``、``dd`` 误差缓解参数
     - 直接返回一个 Schema
   * - ``qec_options``
     - 当前已加载 Driver 的量子纠错参数
     - ``qec_options[driverName]``
   * - ``extra_specs``
     - Flavor 模式的十项扩展调度参数白名单
     - 直接返回一个 Schema

所有具体 Schema 均使用 **JSON Schema draft-07**，根节点包含
``$schema: "http://json-schema.org/draft-07/schema#"``。声明式字典默认是封闭
对象，即 ``additionalProperties: false``。Driver 的 QEC Getter 返回 ``None``
时发布为开放通用对象；Transpiler Getter 返回 ``None`` 时发布为无属性的封闭
空对象，与当前提交校验语义一致。名称索引 map 只是容器，不添加展示元数据键。

通用与专用字段标识
------------------

``driver_options`` 和 ``transpiler_options`` 的顶层 ``properties`` 字段额外包含
``x-qcos-parameter-scope``：

- ``common``：由 ``DriverBase`` 或 ``TranspilerBase`` 的通用展示 Schema 声明的字段。
- ``specific``：由具体驱动或转译器子类扩展的字段。

嵌套对象整体继承顶层字段的分区，用于 WebUI 修改弹窗中的“通用参数”和“专用参数”
分组；该扩展关键字不参与 Ajv 校验，也不改变现有提交校验行为。

字段元数据契约
--------------

每个具体 Schema 根、object 容器、叶子字段以及 object 型
``additionalProperties`` 的 value Schema 都包含非空中文 ``alias_name``、
``description`` 和 ``field_constraints``。完整字段示例如下：

.. code-block:: json

   {
     "type": "integer",
     "exclusiveMinimum": 0,
     "alias_name": "评分层数",
     "description": "控制 MCTS 评分计算的层数，值越大计算开销越高。",
     "field_constraints": {
       "schema": {
         "exclusive_minimum": 0
       },
       "runtime": {}
     }
   }

``field_constraints.schema`` 是声明式提交约束，并同步为标准 JSON Schema，
供 Ajv 等校验器使用；``runtime`` 是构造器、驱动或算法额外约束，只用于展示，
不写入标准约束，也不应由前端用于拒绝输入。运行时条件规则放在
``runtime.custom`` 中，每项包含适用条件 ``when`` 和中文说明 ``rule``。
``runtime.on_invalid`` 可描述 ``reject``、``skip_technique``、``fallback``
或 ``clamp`` 等现有行为。敏感 Token 字段使用标准 ``writeOnly: true``，不会在
响应中返回实际 Token、设备 URL 或连接配置值。

约束键映射
----------

``schema/runtime`` 可包含 ``required``、``nullable``、``minimum``、
``maximum``、``exclusive_minimum``、``exclusive_maximum``、``multiple_of``、
``min_length``、``max_length``、``pattern``、``min_items``、``max_items``、
``exact_items``、``unique_items``、``min_properties``、``max_properties``
和 ``enum``。无额外约束时使用空对象，不使用空 ``enum``。

- ``required: true`` 同步到父对象的 ``required`` 数组。
- ``nullable: true`` 同步到 ``type``，例如 ``["integer", "null"]``。
- ``exclusive_minimum`` 和 ``exclusive_maximum`` 分别映射为 draft-07 数值型
  ``exclusiveMinimum`` 和 ``exclusiveMaximum``。
- ``exact_items: n`` 同步为 ``minItems=n`` 和 ``maxItems=n``。
- 其余范围、长度、数组和对象约束按 JSON Schema 标准驼峰关键字映射。
- ``default``、``type`` 和 ``items`` 直接作为标准 Schema 节点，不在约束对象中
  重复维护。仅运行时约束（例如 ``optimization_level`` 的 0 到 3）不会镜像为
  Ajv 提交限制。

QEM 的 nullable 字段仅为 ``scale_factors``、``scale_factor``、
``polynomial_degree``、``folding_seed``、``fold_gate_names`` 和
``gate_times``；数组元素及 ``gate_times`` 的动态 value 不允许 ``null``。
``fold_gate_names=null`` 在 Factory 先构造再 ``set_config`` 的链路中表示使用
全部内置自逆门，不同于构造器缺省的仅 CZ 行为。``extra_specs`` 所有字段允许
``null``，数值和 CSV/数组类型与当前调度代码一致；两个 fidelity 字段的说明会
明确标注当前仅从 Flavor 读取。

单个插件转换失败不会导致整个 ``/version`` 失败，该条目降级为通用对象并带有
``x-qcos-schema-status: "unavailable"``；可保留部分类型的未知 callable 使用
``"partial"``。缺少展示元数据时服务端提供安全占位文本，客户端仍应以后端提交
校验结果为最终依据。

API版本状态说明
^^^^^^^^^^^^^^^

系统支持多个API版本状态：

- **CURRENT** - 当前活跃版本，推荐使用，优先使用
- **DEPRECATED** - 已废弃但仍可用，即将停止支持，尽快升级
- **UNSUPPORTED** - 不再支持的版本，必须升级

最佳实践建议
^^^^^^^^^^^^^^^^

1. **启动时查询版本**

   .. code-block:: python

      # 应用启动时调用一次
      version_info = version()
      api_version = version_info["api_version"]
      availability = version_info["supported_api_versions"]

2. **版本兼容性检查**

   .. code-block:: python

      # 检查服务器是否支持需要的API版本
      def check_compatibility(required_version):
          version_info = version()
          for api_version in version_info["supported_api_versions"]:
              if api_version["version"] == required_version:
                  return api_version["status"] != "UNSUPPORTED"
          return False

3. **驱动与转译器配合**

   .. code-block:: python

      # 获取特定驱动支持的转译器
      version_info = version()
      driver_transpilers = version_info["capabilities"]["driver_transpiler_mappings"]

      # 提交作业时使用兼容的组合
      available_transpilers = driver_transpilers.get("DriverDummy", [])

4. **缓存版本信息**

   .. code-block:: text

      • 推荐在应用启动时查询一次 version() 接口
      • 将版本信息缓存在内存中
      • 通常无需频繁调用，除非检测到API不兼容错误

