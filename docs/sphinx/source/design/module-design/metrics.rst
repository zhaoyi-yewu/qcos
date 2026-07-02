系统监控
==========

本章节主要介绍QCOS系统监控指标管理与采集模块（Metrics）设计。模块提供两类指标输出通道：基于POSIQ协议的JSON-RPC 2.0查询接口和Prometheus格式的HTTP指标暴露端点。

概述
----

QCOS Metrics 模块（``wy_qcos.metrics``）是量子操作系统的监控核心组件，负责采集、聚合和对外提供系统与作业相关的指标数据。模块采用多通道输出架构，分别面向人工查询与自动化监控系统：

* **RPC接口**：基于 POSIQ JSON-RPC 2.0 协议，提供系统健康、API 统计、作业统计的查询能力，需要 ``ROLE_ADMIN`` 角色权限
* **Prometheus接口**：提供独立的HTTP指标暴露端点（默认端口19400），以标准Prometheus text format输出所有指标，供Prometheus监控系统定时抓取

核心功能包括：

1. **作业指标（Job Metrics）**：按状态统计作业数量，涵盖 completed、failed、running、
   queued、cancelling、cancelled、deleted、unknown 共8种状态，
   通过 Prometheus Gauge 暴露
2. **系统健康指标（System Health Metrics）**：监控 worker、prefect、fastapi、redis 四个核心组件的健康状态，输出整体在线状态与心跳时间戳
3. **API 访问指标（API Metrics）**：追踪所有 API 请求的请求总数、并发数与响应耗时分布，支持按模块/方法/端点/状态码分类统计
4. **定时调度**：基于异步定时器的周期性指标更新机制，内置并发锁与限频控制，确保指标数据实时性
5. **自动采集**：基于 Starlette ``BaseHTTPMiddleware`` 的自动采集能力，支持路径标准化（动态 ID 替换）、排除路径配置

模块组成
--------

* ``__init__.py`` — 模块入口，导出 MetricsCollector 单例
* ``metrics_collector.py`` — 指标采集器（核心，定义所有指标类型）
* ``metrics_middleware.py`` — FastAPI 中间件，自动采集 API 访问指标
* ``metrics_server.py`` — Prometheus HTTP 指标服务（独立 HTTP 服务器）
* ``metrics_scheduler.py`` — 指标定时调度器（周期性更新 job/health 指标）
* ``metrics_task.py`` — 具体的指标更新任务实现

北向接口路由
~~~~~~~~~~~~

* ``api/posiq/routes_jsonrpc/metrics.py`` — RPC 接口路由层
* ``api/schemas/metrics.py`` — Pydantic 数据模型

.. plantuml:: ../../_static/design/module-design/metrics-class-relations.puml
   :caption: Metrics 模块类关系图
   :alt: Metrics 模块类关系图
   :width: 70%
   :align: center

核心组件说明
------------

MetricsCollector（指标采集核心）
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``metrics_collector.py`` 中定义的 ``MetricsCollector`` 是整个模块的统一入口，内部维护三个子指标收集器：

* **JobMetrics**：管理 job 相关的 8 项 Gauge 指标（通过 status 标签区分不同状态）
* **SystemHealthMetrics**：管理系统健康相关的 3 项 Gauge 指标
* **APIMetrics**：管理 API 访问相关的 Counter、Gauge、Histogram 指标

核心方法如下：

* ``update_job_metrics(data: JobMetricsData)`` — 更新 job 指标
* ``record_api_request(data: APIMetricsData)`` — 记录一次 API 请求（写入 Counter 和 Histogram）
* ``record_api_requests_in_progress(is_increment: bool)`` — 增减进行中请求计数
* ``update_system_health(data: SystemHealthMetricsData)`` — 更新系统健康指标
* ``get_system_health_status()`` — 获取当前系统健康状态
* ``get_metrics()`` — 生成 Prometheus 格式输出（供 PrometheusServer 调用）
* ``get_content_type()`` — 返回 Prometheus 内容类型 ``text/plain; version=0.0.4``

MetricsMiddleware（中间件）
~~~~~~~~~~~~~~~~~~~~~~~~~~~

``metrics_middleware.py`` 继承自 ``starlette.middleware.base.BaseHTTPMiddleware``，拦截所有 API 请求并自动采集访问指标。

API 访问指标采集流程：

.. plantuml:: ../../_static/design/module-design/metrics-api-flow.puml
   :caption: API 访问指标采集流程图
   :alt: API 访问指标采集流程图
   :width: 70%
   :align: center

路径标准化规则（动态参数替换为占位符）：

* 移除 URL 查询参数（如 ``?name=test``）
* 将纯数字 ID 替换为 ``{id}``，例如 ``/v1/driver/123`` → ``/v1/driver/{id}``
* 将 UUID 格式替换为 ``{uuid}``，例如 ``/v1/device/550e8400-e29b-41d4-a716-446655440000`` → ``/v1/device/{uuid}``
* 将 24 位 hex ID 替换为 ``{hex_id}``，例如 ``/v1/job/507f1f77bcf86cd799439011`` → ``/v1/job/{hex_id}``

排除路径：

* ``/metrics`` — 避免指标采集接口自身的请求被重复记录
* ``/health`` — 健康检查接口
* ``/favicon.ico`` — 浏览器图标请求

采集模块：

* ``device``、``driver``、``job``、``system``、``transpiler``

MetricsServer（Prometheus 服务器）
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``metrics_server.py`` 中定义的 ``MetricsServer`` 是一个独立的 HTTP 服务器
（基于 Python ``http.server.HTTPServer``），
监听单独的端口（默认 19400），
通过 ``PrometheusHandler`` 处理 GET 请求并返回 Prometheus 格式指标数据。


接口规格如下：

* **方法**：HTTP GET
* **路径**：``/metrics``
* **Content-Type**：``text/plain; charset=utf-8``
* **其他路径**：返回 404 Not Found
* **权限**：无需认证，供 Prometheus 抓取

服务器特性：

* 支持 IPv4/IPv6 及双栈模式（Dual-Stack）
* 开启 ``SO_REUSEADDR`` 和 ``SO_REUSEPORT`` 选项允许快速重启时释放端口
* 默认监听 IP 为空字符串时使用 IPv6 ``::`` 并启用双栈模式（``IPV6_V6ONLY=False``）
* 监听 IP 与端口通过配置文件动态设置

MetricsScheduler（定时调度器）
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``metrics_scheduler.py`` 中定义的 ``MetricsScheduler`` 是指标定时更新的调度器，是基于 ``APScheduler`` 实现。

调度机制：

* 默认更新间隔为 ``Constant.DEFAULT_UPDATE_METRICS_INTERVAL_SECONDS`` （15 秒）
* 启动时执行一次初始化更新（非致命错误不影响启动）
* 之后每间隔固定时长触发周期性更新
* APSheduler 配置 ``max_instances=1`` 确保同一时刻只有一个更新任务在执行
* APSheduler 配置 ``coalesce=True`` 跳过错过的执行，避免堆积

metrics_task（更新任务）
~~~~~~~~~~~~~~~~~~~~~~~~

``metrics_task.py`` 包含具体的指标采集与更新逻辑，包含以下函数：

* ``update_job_metrics()`` — 通过 ``JobRepository`` 查询数据库，按状态统计各状态作业数量并更新 JobMetrics
* ``check_worker_health()`` — 遍历所有设备，并发检查每个设备的 work pool 中是否有在线 worker（超时 5s，最多重试 1 次，重试延迟 2s）
* ``check_prefect_health()`` — 通过调用 ``sync_client.hello()`` 检查 Prefect API 可用性（超时 3s）
* ``check_fastapi_health()`` — 由于 FastAPI 与指标监控在同一进程，默认返回健康
* ``check_redis_health()`` — 通过 ``redis.ping()`` 检查 Redis 连接（超时 2s，失败时重置客户端）
* ``update_system_health_metrics()`` — 并发执行所有 4 项组件健康检查，汇总结果并更新SystemHealthMetrics
* ``update_metrics_task_async()`` — 并发执行 ``update_job_metrics()`` 与 ``update_system_health_metrics()``，总超时 15s

配置信息
~~~~~~~~

所有任务级别的超时控制参数：

* ``PREFECT_CHECK_TIMEOUT = 3.0`` — Prefect 健康检查超时（秒）
* ``WORKER_CHECK_TIMEOUT = 5.0`` — Worker 健康检查超时（秒）
* ``WORKER_CHECK_RETRY_DELAY = 2.0`` — Worker 健康检查超时后重试延迟（秒）
* ``REDIS_CHECK_TIMEOUT = 2.0`` — Redis 健康检查超时（秒）
* ``METRICS_TOTAL_TIMEOUT = 15.0`` — 指标更新总超时（秒）

初始化
------

Metrics 模块在系统启动时通过 FastAPI 的 lifespan 机制完成初始化，由 ``BackgroundServiceManager`` 统一管理生命周期：

.. code-block:: python

    @asynccontextmanager
    async def app_lifespan(app: jsonrpc.API):
        manager = BackgroundServiceManager()

        # 注册指标调度器
        metrics_schedule = MetricsScheduler()
        manager.add_service(metrics_schedule)

        # 注册指标服务器
        metrics_server = MetricsServer()
        manager.add_service(metrics_server)

        # 启动所有后台服务
        await manager.start_all()
        try:
            yield
        finally:
            await manager.stop_all()

MetricsMiddleware 作为 ``BaseHTTPMiddleware`` 注册到 FastAPI 应用中间件链中：

.. code-block:: python

    from wy_qcos.metrics.metrics_middleware import MetricsMiddleware
    app.add_middleware(MetricsMiddleware)

数据流
------

Metrics 模块涉及两种数据流：

**API 访问指标采集流程** — 见上方"MetricsMiddleware"章节流程图。

**Job/Health 指标定期更新流程**：

.. plantuml:: ../../_static/design/module-design/metrics-update-flow.puml
   :caption: Job/Health 指标定期更新流程图
   :alt: Job/Health 指标定期更新流程图
   :width: 90%
   :align: center

指标分类
--------

Job Metrics（作业指标）
~~~~~~~~~~~~~~~~~~~~~~~~

以 Gauge 类型暴露作业数量信息。

.. list-table:: Job Metrics 指标说明
    :widths: 35 12 12 45
    :header-rows: 1
    :align: left
    :class: longtable

    * - 指标名称
      - 类型
      - 标签
      - 说明
    * - **total**
      - Gauge
      - status
      - 按状态分类的作业数量，status 标签值包括：completed、failed、running、queued、cancelling、cancelled、deleted、unknown

System Health Metrics（系统健康指标）
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

以 Gauge 类型暴露系统及各组件各健康状态。

.. list-table:: System Health Metrics 指标说明
   :widths: 35 12 20 35
   :header-rows: 1
   :align: left
   :class: longtable

   * - 指标名称
     - 类型
     - 标签
     - 说明
   * - **system_healthy**
     - Gauge
     - 无
     - 系统整体健康状态（1=健康，0=不健康）
   * - **heartbeat_timestamp**
     - Gauge
     - 无
     - 系统心跳时间戳（Unix 时间戳，秒）
   * - **component_status**
     - Gauge
     - component
     - 组件健康状态（1=健康，0=不健康）。component 标签值包括：worker, prefect, fastapi, redis

API Metrics（API 访问指标）
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

以 Counter、Gauge、Histogram 类型暴露 API 访问性能数据。

.. list-table:: API Metrics 指标说明
    :widths: 35 15 25 25
    :header-rows: 1
    :align: left
    :class: longtable

    * - 指标名称
      - 类型
      - 标签
      - 说明
    * - **api_requests_total**
      - Counter
      - module, method, endpoint, status_code
      - 按模块、方法、端点、状态码分类的 API 请求总数
    * - **api_requests_in_progress**
      - Gauge
      - 无
      - 当前正在处理的 API 请求数
    * - **api_request_duration**
      - Histogram
      - module, method, endpoint
      - API 请求耗时（秒），预定义 12 个桶：0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0

标签说明：

* **module** — API 所属模块（device, driver, job, system, transpiler 等）
* **method** — JSON-RPC 方法名（从请求 body 中解析）
* **endpoint** — 标准化后的端点路径，动态 ID 参数会被替换为 ``{id}``（如 ``/v1/driver/{id}``）
* **status_code** — HTTP 响应状态码

Prometheus 端点示例输出：

.. code-block:: text

   # HELP total Total number of jobs by status
   # TYPE total gauge
   total{status="completed"} 80.0
   total{status="failed"} 10.0
   total{status="running"} 5.0
   # HELP system_healthy System healthy status (1=online, 0=offline)
   # TYPE system_healthy gauge
   system_healthy 1.0
   # HELP heartbeat_timestamp System heartbeat timestamp (Unix timestamp)
   # TYPE heartbeat_timestamp gauge
   heartbeat_timestamp 1234567890
   # HELP component_status Component health status (1=healthy, 0=unhealthy)
   # TYPE component_status gauge
   component_status{component="worker"} 1.0
   component_status{component="prefect"} 1.0
   # HELP api_requests_total Total API requests
   # TYPE api_requests_total counter
   api_requests_total{module="job",method="createJob",endpoint="/v1/job",status_code="201"} 50.0
   # HELP api_request_duration API request duration in seconds
   # TYPE api_request_duration histogram
   api_request_duration_bucket{module="job",method="createJob",endpoint="/v1/job",le="0.001"} 5.0
   api_request_duration_bucket{module="job",method="createJob",endpoint="/v1/job",le="+Inf"} 50.0
   api_request_duration_count{module="job",method="createJob",endpoint="/v1/job"} 50.0
   api_request_duration_sum{module="job",method="createJob",endpoint="/v1/job"} 1.234

配置说明
--------

Metrics 模块相关的配置项

.. list-table:: Metrics 模块配置项
   :widths: 35 25 15 25
   :header-rows: 1
   :align: left
   :class: longtable

   * - 配置项
     - 配置段
     - 默认值
     - 说明
   * - **METRICS_SERVER_LISTEN_IP**
     - [METRICS_SERVER]
     - ""（实际使用 ``::`` IPv6 双栈）
     - Metrics 服务端监听 IP，空字符串默认使用 IPv6 ``::`` 并启用双栈模式（同时监听 IPv4 和 IPv6）
   * - **METRICS_SERVER_LISTEN_PORT**
     - [METRICS_SERVER]
     - 19400
     - Metrics 服务端监听端口
   * - **DEFAULT_UPDATE_METRICS_INTERVAL_SECONDS**
     - -
     - 15
     - 指标更新间隔（秒），默认 15 秒

注意事项
--------

* Prometheus Server 默认监听独立端口（19400），与主服务（FastAPI）端口分离
* 所有 RPC 查询接口（``get_system_health``、``get_api_stats``、``get_job_stats``）均需 ``ROLE_ADMIN`` 角色权限
* 建议将 ``DEFAULT_UPDATE_METRICS_INTERVAL_SECONDS`` 设置为大于指标更新最大耗时（15s）的值，以避免更新任务重叠
* ``APIMetrics`` 中的时间戳缓冲区会保留最近 24 小时的数据，超过部分自动清理
* ``MetricsMiddleware`` 会在请求体被读取后自动恢复，确保下游中间件可以正常读取请求体
