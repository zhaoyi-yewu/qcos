转译器管理接口
================

转译器接口用于查询转译器信息。

.. list-table:: 转译器管理接口规范
   :widths: 20 20 30 30
   :header-rows: 1
   :align: left
   :class: longtable

   * - 用途
     - 方法
     - 请求参数
     - 返回值
   * - **查询转译器详情**
     - **get_transpiler**

       URI: /v1/transpiler/get_transpiler
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "id": 1,
               "method": "get_transpiler",
               "params": {
                 "body": {
                   "name": "cmss",
                 }
               }
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "result": {
                 "name": "cmss",
                 "alias_name": "五岳转译器",
                 "enable": true,
                 "supported_code_types": [
                   "qasm",
                   "qasm2"
                 ],
                 "transpiler_options": null,
                 "transpiler_options_schema": null
               },
               // 有错误时会出现, 具体格式参照<错误返回>
               "error": {}
               "id": 1
             }

   * - **查询转译器列表**
     - **get_transpilers**

       URI: /v1/transpiler/get_transpilers
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "id": 1,
               "method": "get_transpilers",
               "params": {
                 "filters": {}  // 过滤
               }
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "result": {
                 "cmss": {
                   "name": "cmss",
                   "alias_name": "五岳转译器",
                   "enable": true,
                   "supported_code_types": [
                     "qasm",
                     "qasm2"
                   ],
                   "transpiler_options": null,
                   "transpiler_options_schema": null
                 }
               },
               // 有错误时会出现, 具体格式参照<错误返回>
               "error": {}
               "id": 1
             }
