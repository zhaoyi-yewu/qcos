驱动管理接口
================

驱动接口用于查询驱动信息。

.. list-table:: 驱动管理接口规范
   :widths: 20 20 30 30
   :header-rows: 1
   :align: left
   :class: longtable

   * - 用途
     - 方法
     - 请求参数
     - 返回值
   * - **查询驱动详情**
     - **get_driver**

       URI: /v1/driver/get_driver
     - .. container:: table-code-small-font

          .. code-block:: json

              {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "get_driver",
                "params": {
                  "body": {
                    "name": "DriverDummy"
                  }
                }
              }
     - .. container:: table-code-small-font

          .. code-block:: json

              {
                "jsonrpc": "2.0",
                "result": {
                  "name": "DriverDummy",
                  "alias_name": "空载测试驱动(中性原子)",
                  "version": "0.0.1",
                  "description": "空载测试驱动(中性原子)",
                  "tech_type": "neutral_atom",
                  "max_qubits": 10,
                  "transpiler": "cmss",
                  "supported_transpilers": [
                    "cmss"
                  ],
                  "enable_circuit_aggregation": true,
                  "supported_code_types": [
                    "qasm",
                    "qasm2"
                  ],
                  "supported_basis_gates": [
                    "x",
                    "y"
                  ],
                  "results_fetch_mode": "sync"
                },
                "error": null,
                "id": 1
              }

   * - **查询驱动列表**
     - **get_drivers**

       URI: /v1/driver/get_drivers
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "id": 1,
               "method": "get_drivers",
               "params": {
                 "filters": {}  // 过滤
               }
             }
     - .. container:: table-code-small-font

          .. code-block:: json

              {
                "jsonrpc": "2.0",
                "result": {
                  "DriverDummy": {
                    "name": "DriverDummy",
                    "alias_name": "空载测试驱动(中性原子)",
                    "version": "0.0.1",
                    "description": "空载测试驱动(中性原子)",
                    "tech_type": "neutral_atom",
                    "max_qubits": 10,
                    "transpiler": "cmss",
                    "supported_transpilers": [
                      "cmss"
                    ],
                    "enable_circuit_aggregation": true,
                    "supported_code_types": [
                      "qasm",
                      "qasm2"
                    ],
                    "supported_basis_gates": [
                      "x",
                      "y"
                    ],
                    "results_fetch_mode": "sync"
                  }
                },
                "error": null,
                "id": 1
              }

驱动程序详解
~~~~~~~~~~~~

驱动配置字段说明
^^^^^^^^^^^^^^^^

驱动程序的关键配置字段：

- **name** (string) - 驱动程序唯一标识
- **alias_name** (string) - 驱动别名，用于界面显示
- **version** (string) - 驱动版本号，遵循语义化版本规范
- **description** (string) - 驱动描述信息
- **tech_type** (string) - 量子技术类型
- **max_qubits** (integer) - 最大支持量子比特数
- **transpiler** (string) - 推荐使用的转译器
- **supported_transpilers** (array) - 支持的转译器列表
- **enable_circuit_aggregation** (boolean) - 是否支持电路聚合优化
- **supported_code_types** (array) - 支持的代码类型（qasm/qasm2/qasm3等）
- **supported_basis_gates** (array) - 支持的基础门列表
- **results_fetch_mode** (string) - 结果获取方式（sync/async）

技术类型详解
^^^^^^^^^^^^

系统支持以下量子技术类型：

- **neutral_atom** - 中性原子系统
- **ion_trap** - 离子阱系统
- **superconducting** - 超导系统
- **photon** - 光量子系统
- **generic_simulator** - 通用量子模拟器

结果获取方式
^^^^^^^^^^^^

- **sync**：同步模式，任务完成立即返回结果
- **async**：异步模式，任务完成后通过回调通知

最佳实践建议
^^^^^^^^^^^^^^^^

1. **选择合适的驱动**

   .. code-block:: text

      • 根据硬件平台选择相应驱动
      • 查询 get_drivers 了解可用驱动
      • 验证驱动支持的代码类型和门集合

2. **检查驱动参数**

   .. code-block:: python

      # 提交任务前检查比特数
      driver_info = get_driver("DriverDummy")
      if circuit.num_qubits <= driver_info["max_qubits"]:
          # 电路可以在该驱动上运行
          submit_job(backend="dummy", source_code=code)

3. **利用电路聚合优化**

   .. code-block:: text

      • 当 enable_circuit_aggregation 为 true 时
      • 系统会自动优化多个量子电路的执行
      • 可显著提升系统吞吐量
