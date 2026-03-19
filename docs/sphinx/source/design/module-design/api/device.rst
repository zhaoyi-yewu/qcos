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
     - **calibrate**

       URI: /v1/device/calibrate
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "id": 1,
               "method": "calibrate",
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
