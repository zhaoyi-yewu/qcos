系统管理接口
================

系统接口用于管理系统。

.. list-table:: 系统管理接口规范
   :widths: 20 20 30 30
   :header-rows: 1
   :align: left
   :class: longtable

   * - 用途
     - 方法
     - 请求参数
     - 返回值
   * - **心跳检测**
     - **ping**

       URI: /v1/system/ping
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "id": 1,
               "method": "ping",
               "params": {
                 "body": {
                   "message": "123",  // 任意字符串
                 }
               }
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "id": 1,
               "result": {
                 "message": "123"  // 用户输入的字符串
               },
               // 有错误时会出现, 具体格式参照<错误返回>
               "error": {}
             }

   * - **系统信息**
     - **system_info**

       URI: /v1/system/system_info
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "id": 1,
               "method": "system_info",
               "params": {
                 "body": {}
               }
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "id": 1,
               "result": {
                 "total_jobs_count": 10
               },
               // 有错误时会出现, 具体格式参照<错误返回>
               "error": {}
             }
