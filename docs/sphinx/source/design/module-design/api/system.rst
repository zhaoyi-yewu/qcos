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

   * - **内存占用查询**
     - **show_mem**

       URI: /v1/system/show_mem
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "id": 1,
               "method": "show_mem",
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
                 "pid": 1234,
                 "rss_mb": 256.5,
                 "vms_mb": 512.0,
                 "thread_count": 10,
                 "num_objects": 50000,
                 "cpu_percent": 5.5
               },
               "error": null
             }

   * - **手动垃圾回收**
     - **gc_mem**

       URI: /v1/system/gc_mem
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "id": 1,
               "method": "gc_mem",
               "params": {
                 "body": {
                   "generations": 2
                 }
               }
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "id": 1,
               "result": {
                 "collected": 1500,
                 "uncollectable": 0,
                 "count_before": 50000,
                 "count_after": 48500,
                 "malloc_trim_ret": 1
               },
               "error": null
             }

   * - **内存分配追踪**
     - **trace_mem**

       URI: /v1/system/trace_mem
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "id": 1,
               "method": "trace_mem",
               "params": {
                 "body": {
                   "action": "snapshot",
                   "nframe": 25,
                   "sort_count": false
                 }
               }
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "id": 1,
               "result": {
                 "tracing": true,
                 "traced_blocks": 1024,
                 "current": 2048,
                 "peak": 4096,
                 "top_stats": [
                   {
                     "location": "/path/to/file.py:42",
                     "size": 1024,
                     "count": 5
                   }
                 ]
               },
               "error": null
             }

系统参数详解
~~~~~~~~~~~~

内存与调试接口
^^^^^^^^^^^^^^

**内存占用查询（show_mem）**

返回 API 服务端进程的内存占用情况，需要管理员权限：

.. list-table:: 字段说明
   :widths: 25 15 60
   :header-rows: 1
   :align: left

   * - 字段名
     - 类型
     - 说明
   * - pid
     - integer
     - 进程 ID
   * - rss_mb
     - float
     - 常驻内存集大小（MB）
   * - vms_mb
     - float
     - 虚拟内存大小（MB）
   * - thread_count
     - integer
     - 线程数
   * - num_objects
     - integer
     - GC 跟踪对象总数
   * - cpu_percent
     - float
     - CPU 使用率（%）

**手动垃圾回收（gc_mem）**

手动触发 Python 垃圾回收并执行 malloc_trim，用于调试内存问题，需要管理员权限：

.. list-table:: 字段说明
   :widths: 25 15 60
   :header-rows: 1
   :align: left

   * - 字段名
     - 类型
     - 说明
   * - collected
     - integer
     - 本次回收的对象数量
   * - uncollectable
     - integer
     - 无法回收的对象数量（引用循环）
   * - count_before
     - integer
     - 回收前 GC 跟踪对象总数
   * - count_after
     - integer
     - 回收后 GC 跟踪对象总数
   * - malloc_trim_ret
     - integer
     - malloc_trim 返回值（1成功/0失败/None）

请求参数 ``generations`` 可选（0/1/2），默认 2（全量回收）。

**内存分配追踪（trace_mem）**

通过 tracemalloc 追踪 Python 内存分配，返回当前/峰值内存及 Top 内存分配统计，需要管理员权限：

.. list-table:: 字段说明
   :widths: 25 15 60
   :header-rows: 1
   :align: left

   * - 字段名
     - 类型
     - 说明
   * - tracing
     - bool
     - tracemalloc 是否正在追踪
   * - traced_blocks
     - integer
     - 已追踪的内存块数量
   * - current
     - integer
     - 当前已追踪内存（字节）
   * - peak
     - integer
     - 峰值已追踪内存（字节）
   * - top_stats
     - array
     - Top 内存分配统计列表

请求参数：

- ``action``：操作类型（snapshot/stop/clear），默认 snapshot
- ``nframe``：显示 Top N 内存分配（仅 snapshot），默认 25
- ``sort_count``：是否按分配次数排序（默认按大小排序）

.. note::
   tracemalloc 启动后会对每次内存分配产生额外开销，建议调试完成后用
   ``action=stop`` 关闭。

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

.. list-table:: 字段说明
   :widths: 25 15 60
   :header-rows: 1
   :align: left

   * - 字段名
     - 类型
     - 说明
   * - total_jobs_count
     - integer
     - 系统中已完成的作业总数

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
