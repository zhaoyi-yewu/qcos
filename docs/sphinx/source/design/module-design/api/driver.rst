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
                   "name": "DriverDummy",
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
                 "enable_transpiler": true,
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
               // 有错误时会出现, 具体格式参照<错误返回>
               "error": {}
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
                   "enable_transpiler": true,
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
               // 有错误时会出现, 具体格式参照<错误返回>
               "error": {}
               "id": 1
             }
