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
                 "platform_version": "五岳量子计算操作系统(qcos) v1.0.0",
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

