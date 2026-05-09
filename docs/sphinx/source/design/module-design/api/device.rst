设备管理接口
================

设备接口用于查询和管理设备。

.. list-table:: 设备管理接口规范
   :widths: 20 20 30 30
   :header-rows: 1
   :align: left
   :class: longtable

   * - 用途
     - 方法
     - 请求参数
     - 返回值

   * - **查询设备详情**
     - **get_device**

       URI: /v1/device/get_device
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "id": 1,
               "method": "get_device",
               "params": {
                 "body": {
                   "name": "dummy",
                   "detail": true
                 }
               }
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "result": {
                 "name": "dummy",
                 "alias_name": "空载测试设备",
                 "description": "空载测试设备(dummy)",
                 "driver_name": "DriverDummy",
                 "enable": true,
                 "status": "online",
                 "configs": {
                   "transpiler": {
                     "qpu_configs": {
                       "qubits": 6
                     },
                     "decomposition_rule": {}
                   }
                 },
                 "details": {
                   "qubit1": {
                     "single_qubit_gate_fidelity": 0.999,
                     "qubit_frequency": 5.018,
                     "readout_frequency": 6.8295,
                     "single_qubit_gate_duration": 30.0,
                     "T1": 28.994326898773733,
                     "T2": 5.690175203450656,
                     "readout_fidelity_state0": 0.9705333333333334,
                     "readout_fidelity_state1": 0.8440000000000001
                   }
                 },
                 "topo_configs": null
               },
               "error": null,
               "id": 1
             }

   * - **查询设备列表**
     - **get_devices**

       URI: /v1/device/get_devices
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "id": 1,
               "method": "get_devices",
               "params": {
                 "filters": {}  // 过滤
               }
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "result": {
                 "dummy": {
                   "name": "dummy",
                   "alias_name": "空载测试设备",
                   "description": "空载测试设备(dummy)",
                   "driver_name": "DriverDummy",
                   "enable": true,
                   "status": "online",
                   "configs": {
                     "transpiler": {
                       "qpu_configs": {
                         "qubits": 6
                       },
                       "decomposition_rule": {}
                     }
                   },
                   "details": null
                 }
               },
               "error": null,
               "id": 1
             }

   * - **校准设备**
     - **calibrate-device**

       URI: /v1/device/calibrate-device
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "id": 1,
               "method": "calibrate_device",
               "params": {
                 "body": {
                   "device_name": "dummy",
                   "options": { // 校准参数选项
                     "init_freq": 5.018,
                     "step": 0.001,
                     "scan_param": "qubit_frequency",
                     "scan_shots": 100
                   }
                 }
               }
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "id": 1,
               "result": {
                 "details": {}
               },
               // 有错误时会出现, 具体格式参照<错误返回>
               "error": {}
             }

   * - **获取校准结果**
     - **get_calibrate_results**

       URI: /v1/device/get_calibrate_results
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "id": 1,
               "method": "get_calibrate_results",
               "params": {
                 "body": {
                   "device_name": "dummy"
                 }
               }
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "id": 1,
               "result": {
                 "details": {}
               },
               // 有错误时会出现, 具体格式参照<错误返回>
               "error": {}
             }

   * - **设置设备选项**
     - **set_device_options**

       URI: /v1/device/set_device_options
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "id": 1,
               "method": "set_device_options",
               "params": {
                 "body": {
                   "device_name": "dummy",
                   "options": {
                     "sleep": 300, // 设备休眠300s
                     "shot_gap": 100, // 量子任务shot间隔100ms
                     "readout_threshold": 0.8,
                     "qubits": {
                       "qubit1": true, // qubit1 可用于单量子比特门
                       "qubit2": false, // qubit2 不可用于单量子比特门
                       "qubit1_qubit2": false // qubit1 和 qubit2 不可用于双量子比特门
                     }
                   }
                 }
               }
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "id": 1,
               "result": {
                 "details": {
                   "sleep": true,
                   "shot_gap": true,
                   "readout_threshold": true,
                   "qubits": {
                     "qubit1": true, // qubit1 可用于单量子比特门
                     "qubit2": false, // qubit2 不可用于单量子比特门
                     "qubit1_qubit2": false // qubit1 和 qubit2 不可用于双量子比特门
                   }
                 }
               },
               // 有错误时会出现, 具体格式参照<错误返回>
               "error": {}
             }

   * - **获取设备选项**
     - **get_device_options**

       URI: /v1/device/get_device_options
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "id": 1,
               "method": "get_device_options",
               "params": {
                 "body": {
                   "device_name": "dummy"
                 }
               }
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "id": 1,
               "result": {
                 "details": {
                   "sleep": true,
                   "shot_gap": true,
                   "readout_threshold": true,
                   "qubits": {
                     "qubit1": true, // qubit1 可用于单量子比特门
                     "qubit2": false, // qubit2 不可用于单量子比特门
                     "qubit1_qubit2": false // qubit1 和 qubit2 不可用于双量子比特门
                   }
                 }
               },
               // 有错误时会出现, 具体格式参照<错误返回>
               "error": {}
             }

设备参数详解
~~~~~~~~~~~~

设备配置 (Device Configs)
^^^^^^^^^^^^^^^^^^^^^^^^^^

设备的 ``configs`` 字段包含设备的硬件配置信息：

.. code-block:: json

   {
     "configs": {
       "transpiler": {
         "qpu_configs": {
           "qubits": 6,
           "gates": ["x", "y", "z", "h", "cx", "rx", "ry"],
           "connectivity": "all-to-all"
         },
         "decomposition_rule": {
           "gate_x": ["u1(pi),u2(pi/2,pi/2)"],
           "gate_rx": ["rx(theta)"]
         }
       }
     }
   }

**关键字段说明**：

- ``qubits``: 设备可用的量子比特数量（整数）
- ``gates``: 设备原生支持的量子门列表
- ``connectivity``: 比特连接拓扑 (all-to-all, chain, grid等)
- ``decomposition_rule``: 将高层门分解为原生门的规则

设备物理参数 (Device Details)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

设备的 ``details`` 字段包含设备的物理特性，每个比特包含以下参数：

.. code-block:: json

   {
     "details": {
       "qubit1": {
         "single_qubit_gate_fidelity": 0.999,
         "two_qubit_gate_fidelity": 0.98,
         "qubit_frequency": 5.018,
         "readout_frequency": 6.8295,
         "single_qubit_gate_duration": 30.0,
         "two_qubit_gate_duration": 50.0,
         "T1": 28.994,
         "T2": 5.690,
         "readout_fidelity_state0": 0.9705,
         "readout_fidelity_state1": 0.8440
       }
     }
   }

物理参数详解
^^^^^^^^^^^^^

.. list-table:: 物理参数表
   :widths: 30 20 50
   :header-rows: 1
   :align: left

   * - 参数名
     - 单位
     - 说明
   * - single_qubit_gate_fidelity
     - 无(0-1)
     - 单比特门操作的保真度。越接近1越好，表示操作精度
   * - two_qubit_gate_fidelity
     - 无(0-1)
     - 双比特门操作的保真度。通常低于单比特门保真度
   * - qubit_frequency
     - GHz
     - 量子比特共振频率，用于脉冲控制
   * - readout_frequency
     - GHz
     - 读取操作使用的频率
   * - single_qubit_gate_duration
     - ns (纳秒)
     - 单比特门执行时长。影响相干时间内能做的操作数
   * - two_qubit_gate_duration
     - ns (纳秒)
     - 双比特门执行时长。通常比单比特门长
   * - T1
     - μs (微秒)
     - 弛豫时间 (Longitudinal)。激发态回到基态的时间。越大越好，一般几十μs
   * - T2
     - μs (微秒)
     - 相干时间 (Transverse)。量子叠加态衰减的时间。通常T2 < 2*T1
   * - readout_fidelity_state0
     - 无(0-1)
     - 读取状态|0⟩的正确概率
   * - readout_fidelity_state1
     - 无(0-1)
     - 读取状态|1⟩的正确概率

设备状态说明 (Device Status)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

设备的 ``status`` 字段表示设备的当前状态：

.. code-block:: text

   status 可能的值：

   ✓ online       - 设备在线可用，可以提交作业
   ✗ offline      - 设备离线不可用，无法提交作业
   ⟳ calibrating - 设备正在校准中，无法提交作业
   ⛔ maintenance - 设备维护中，无法提交作业
   ⚠️  error      - 设备出现故障，无法提交作业

校准参数说明 (Calibration Options)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

校准设备时，``options`` 字段用于配置校准过程：

.. code-block:: json

   {
     "options": {
       "init_freq": 5.018,          // 初始频率，从该频率开始扫描
       "step": 0.001,               // 扫描步长，每次增加的频率值
       "scan_param": "qubit_frequency",  // 扫描参数名称
       "scan_shots": 100            // 每个频率点的测量次数
     }
   }

**参数详解**：

- ``init_freq``: 起点频率（GHz），校准算法从此开始搜索
- ``step``: 扫描间隔（GHz），每次增加或减少的频率值
- ``scan_param``: 要扫描的参数（qubit_frequency, readout_frequency等）
- ``scan_shots``: 每个频率的采样次数，影响精度和耗时

设备选项说明 (Device Options)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

设置和获取设备选项时，``options`` 字段的含义：

.. code-block:: json

   {
     "options": {
       "sleep": 300,               // 设备休眠时长 (秒)
       "shot_gap": 100,            // 连续shot间的延迟 (毫秒)
       "readout_threshold": 0.8,   // 读取判决阈值 (0-1)
       "qubits": {
         "qubit1": true,           // qubit1 可用于单量子门
         "qubit2": false,          // qubit2 不可用
         "qubit1_qubit2": false    // qubit1-qubit2 不可用双门
       }
     }
   }

**选项说明**：

- ``sleep``: 设备待机时长，0表示禁用休眠
- ``shot_gap``: 两个连续shot之间的间隔，用于热恢复
- ``readout_threshold``: 判决阈值，用于区分0和1的测量结果
- ``qubits``: 比特可用性配置，true表示可用，false表示禁用或故障

设备选择指南
^^^^^^^^^^^^

根据应用场景选择合适的设备：

.. code-block:: text

   开发和测试阶段:
   ├─ dummy
   │  • 10个虚拟量子比特
   │  • 无物理约束，支持任意门
   │  • 零延迟执行
   │  • 推荐: 快速原型开发和算法验证
   │
   └─ qutip_sim
      • 模拟器后端
      • 任意量子态模拟
      • 推荐: 小规模量子电路仿真

   实际硬件部署:
   ├─ hanyuan1 (中科酷原)
   │  • 10个中性原子比特
   │  • 保真度: ~0.99 (单比特), ~0.95 (双比特)
   │  • 推荐: 原子系统相关研究
   │
   ├─ spinq_rpc (量旋科技)
   │  • NMR核磁共振系统
   │  • 支持的比特数: 2-11 (取决于型号)
   │  • 推荐: NMR物理实验
   │
   ├─ uqc_matrix2 (幺正量子)
   │  • 离子阱系统
   │  • 高保真度: ~0.999 (单比特), ~0.98 (双比特)
   │  • 推荐: 高精度量子计算
   │
   └─ tiangong* (伊辛机)
      • 光学QUBO求解器
      • 仅支持QUBO问题
      • 推荐: 组合优化问题

最佳实践建议
^^^^^^^^^^^^^^^^

1. **查询设备前先检查状态**

   .. code-block:: python

      # 先检查设备是否在线
      device = get_device("hanyuan1", detail=False)
      if device["status"] != "online":
          print(f"设备不可用: {device['status']}")
          return

2. **根据物理参数评估电路复杂度**

   .. code-block:: python

      # 电路深度受 T2 时间限制
      gate_duration = device["details"]["qubit1"]["single_qubit_gate_duration"]
      t2 = device["details"]["qubit1"]["T2"]
      max_gates = int(t2 * 1000 / gate_duration)
      if circuit_depth > max_gates:
          print(f"警告: 电路太深 ({circuit_depth} > {max_gates})")

3. **优化门序列以提高保真度**

   .. code-block:: python

      # 优先使用高保真度的操作
      single_fidelity = device["details"]["qubit1"]["single_qubit_gate_fidelity"]
      two_qubit_fidelity = device["details"]["qubit1"]["two_qubit_gate_fidelity"]

      if single_fidelity > 0.999 and two_qubit_fidelity > 0.95:
          # 可以使用更复杂的电路

