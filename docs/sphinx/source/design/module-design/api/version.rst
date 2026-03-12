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
