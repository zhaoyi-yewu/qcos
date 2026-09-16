系统监控接口
================

系统监控接口用于查询系统健康状态、API 访问统计和作业统计信息，同时提供 Prometheus 格式的指标数据暴露端点。


.. list-table:: 指标管理接口规范
   :widths: 20 20 30 30
   :header-rows: 1
   :align: left
   :class: longtable

   * - 用途
     - 方法
     - 请求参数
     - 返回值
   * - **查询系统健康状态**
     - **get_system_health**

       URI: /v1/metrics/get_system_health
     - .. container:: table-code-small-font

        .. code-block:: json

           {
             "jsonrpc": "2.0",
             "id": 1,
             "method": "get_system_health",
             "params": {}
           }
     - .. container:: table-code-small-font

        .. code-block:: json

            {
              "jsonrpc": "2.0",
              "id": 1,
              "result": {
                "system_healthy": true,
                "heartbeat_timestamp": 1234567890.123,
                "component_status": {
                  "fastapi": "online",
                  "redis": "online",
                  "prefect": "online",
                  "worker": "online"
                }
              },
              "error": null
            }

   * - **查询 API 访问统计**
     - **get_api_stats**

       URI: /v1/metrics/get_api_stats
     - .. container:: table-code-small-font

        .. code-block:: json

           {
             "jsonrpc": "2.0",
             "id": 1,
             "method": "get_api_stats",
             "params": {}
           }
     - .. container:: table-code-small-font

        .. code-block:: json

           {
             "jsonrpc": "2.0",
             "id": 1,
             "result": {
               "total_requests": 1000,
               "last_hour_requests": 50,
               "last_day_requests": 500
             },
             "error": null,
             "id": 1
           }

   * - **查询作业统计**
     - **get_job_stats**

       URI: /v1/metrics/get_job_stats
     - .. container:: table-code-small-font

        .. code-block:: json

           {
             "jsonrpc": "2.0",
             "id": 1,
             "method": "get_job_stats",
             "params": {}
           }
     - .. container:: table-code-small-font

        .. code-block:: json

           {
             "jsonrpc": "2.0",
             "id": 1,
             "result": {
               "total": 100,
               "completed": 80,
               "failed": 10,
               "running": 5,
               "queued": 3,
               "cancelling": 1,
               "cancelled": 1,
               "deleting": 0,
               "deleted": 0,
               "unknown": 0,
               "submitted_job_rate_min": 2.5,
               "completed_job_rate_min": 1.0
             },
             "error": null,
             "id": 1
           }

.. list-table:: 字段说明
   :widths: 25 10 65
   :header-rows: 1
   :align: left
   :class: longtable

   * - Field
     - Type
     - Description
   * - **system_healthy**
     - bool
     - 系统整体健康状态。只有 worker、prefect、fastapi、redis 四个组件均在线时为 true
   * - **heartbeat_timestamp**
     - float
     - 最后心跳时间戳（Unix 时间戳，秒）
   * - **component_status**
     - object
     - 各组件状态映射（键：组件名，值："online"/"offline"）
   * - **total_requests**
     - int
     - 系统启动以来的总 API 请求数
   * - **last_hour_requests**
     - int
     - 最近一小时内收到的 API 请求数
   * - **last_day_requests**
     - int
     - 最近一天内收到的 API 请求数
   * - **total/completed/failed/running/queued/cancelling/cancelled/deleting/deleted/unknown**
     - int
     - 各状态作业计数
   * - **submitted_job_rate_min**
     - float
     - 最近每分钟作业提交速率（job 条目数/分钟），基于最近 1 分钟内
       created_at 的 job 数量统计
   * - **completed_job_rate_min**
     - float
     - 最近每分钟已完成作业速率（completed job 数/分钟），基于最近 1
       分钟内 created_at 且状态为 completed 的 job 数量统计
