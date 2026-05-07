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

系统参数详解
~~~~~~~~~~~~

心跳检测 (Ping)
^^^^^^^^^^^^^^^

心跳检测用于检验服务连通性：

- 请求参数：任意字符串，由调用方自定义
- 返回内容：完整回复请求参数
- 用途：检测服务可用性、网络连通性
- 响应时间：通常小于100ms

系统信息字段说明
^^^^^^^^^^^^^^^^

``system_info`` 接口返回系统运行状态：

+------------------+---------+---------------------------------------------+
| 字段名           | 类型    | 说明                                        |
+==================+=========+=============================================+
| total_jobs_count | integer | 系统中已完成的作业总数                      |
+------------------+---------+---------------------------------------------+

最佳实践建议
^^^^^^^^^^^^^^^^

1. **健康检查**

   .. code-block:: python

      # 使用 ping 进行周期性健康检查
      def health_check():
          try:
              response = ping("health_check")
              if response["message"] == "health_check":
                  return True
              return False
          except:
              return False

2. **连接维持**

   .. code-block:: text

      • 建议每30秒调用一次 ping 保持连接活跃
      • 连续3次 ping 失败应认为服务不可用
      • 可整合到客户端心跳机制中

3. **性能监控**

   .. code-block:: text

      • 通过 system_info 了解系统负载情况
      • total_jobs_count 增长过快可能表示系统成为瓶颈
      • 建议定期监控系统统计数据
