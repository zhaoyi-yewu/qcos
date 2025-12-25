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
                       "qubits": 6,
                     },
                     "decomposition_rule": {
                     }
                   }
                 }
               },
               // 有错误时会出现, 具体格式参照<错误返回>
               "error": {}
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
                         "qubits": 6,
                       },
                       "decomposition_rule": {
                       }
                     }
                   }
                 }
               },
               // 有错误时会出现, 具体格式参照<错误返回>
               "error":
               "id": 1
             }
