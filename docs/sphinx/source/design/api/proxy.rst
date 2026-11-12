反向代理接口
================

反向代理接口将集群内部的监控组件（Prometheus、Alertmanager、
VictoriaLogs 等）统一暴露在同一 API 入口之下，避免向外部直接
开放各组件的独立端口。所有代理端点挂载在 ``/v1/proxy/<service>``
前缀下，以纯 ASGI 子应用方式实现字节级透传。

代理接口遵循全局 ``AUTH_MODE``：``jwt`` 模式下必须在 HTTP Header
中携带 ``Authorization: Bearer <token>``，否则返回 HTTP 401；
其余认证模式下放行。

.. contents:: 目录
   :local:
   :depth: 3

代理目标
--------

代理目标通过配置文件 ``[PROXY]`` 节的 ``*_BASE_URL`` 项注册；
配置为空字符串时对应端点不挂载（视为禁用）。

.. list-table:: 内置代理目标
   :widths: 20 30 25 25
   :header-rows: 1
   :align: left

   * - 端点路径
     - 配置项（``[PROXY]`` 节）
     - 上游示例
     - 健康探测路径

   * - ``/v1/proxy/prometheus``
     - ``PROMETHEUS_BASE_URL``
     - ``http://127.0.0.1:9090``
     - ``/-/healthy``
   * - ``/v1/proxy/alertmanager``
     - ``ALERTMANAGER_BASE_URL``
     - ``http://127.0.0.1:9093``
     - ``/-/healthy``
   * - ``/v1/proxy/victorialogs``
     - ``VICTORIALOGS_BASE_URL``
     - ``http://127.0.0.1:9428``
     - ``/health``

转发行为
--------

- **路径映射**：剥去挂载前缀后拼接到上游地址，例如
  ``/v1/proxy/prometheus/api/v1/query?query=up`` 转发为
  ``<PROMETHEUS_BASE_URL>/api/v1/query?query=up``；查询串原样透传
- **请求头**：剥离 RFC 2616 §13.5.1 定义的 hop-by-hop 头
  （``Connection`` / ``Keep-Alive`` / ``Proxy-Authenticate`` /
  ``Proxy-Authorization`` / ``TE`` / ``Trailer`` /
  ``Transfer-Encoding`` / ``Upgrade``）及 ``Host`` 头，
  其余头原样转发
- **响应头**：除 hop-by-hop 头外，额外剥离 ``Content-Length``
  （响应改为 chunked 流式回传）与 ``Content-Encoding``
  （HTTP 客户端已透明解压，避免下游重复解压）
- **响应体**：以 64 KiB 分块流式回传，大响应（如 Prometheus
  ``query_range`` 结果）不在代理内存中整体缓冲
- **连接复用**：默认复用 FastAPI 应用生命周期内共享的
  ``httpx.AsyncClient`` 连接池

限制与错误码
------------

.. list-table::
   :widths: 20 80
   :header-rows: 1
   :align: left

   * - 状态码
     - 场景

   * - ``401``
     - ``jwt`` 认证模式下 Token 缺失或无效
   * - ``413``
     - 请求体超过 10 MB 上限
   * - ``502``
     - 上游连接 / 传输错误（Bad Gateway）
   * - ``504``
     - 上游读写超时（默认 connect 5s / read 60s / write 30s /
       pool 5s）

健康检查接口
------------

``get_proxy_health``（JSON-RPC，挂载于 ``/v1/metrics`` 端点，
仅管理员角色可用）逐个探测所有已注册代理目标的健康状态，
供 WebUI 监控中心展示各组件在线情况。

.. list-table:: get_proxy_health 返回项（ProxyHealthItem）
   :widths: 25 75
   :header-rows: 1
   :align: left

   * - 字段
     - 说明

   * - ``name``
     - 代理目标名称（path segment）
   * - ``path``
     - 代理挂载路径，如 ``/v1/proxy/prometheus``
   * - ``base_url``
     - 配置的上游地址
   * - ``enabled``
     - 是否已配置并挂载
   * - ``healthy``
     - 探测结果（上游 2xx 视为健康）
   * - ``status``
     - ``healthy`` / ``unhealthy`` / ``disabled``
   * - ``latency_ms``
     - 探测耗时（毫秒），失败时为 ``null``
   * - ``detail``
     - 失败原因简述（超时、连接错误、非 2xx 状态码等）

扩展示例：

.. container:: table-code-small-font

   .. code-block:: json

      {
        "items": [
          {
            "name": "prometheus",
            "path": "/v1/proxy/prometheus",
            "base_url": "http://127.0.0.1:9090",
            "enabled": true,
            "healthy": true,
            "status": "healthy",
            "latency_ms": 3,
            "detail": ""
          }
        ]
      }

扩展新代理目标
--------------

新增一个代理服务只需两处改动：

1. 在 ``wy_qcos.common.config.ProxySection`` 中新增
   ``XXX_BASE_URL`` 配置字段（默认 ``""``）
2. 在 ``wy_qcos.api.posiq.routes_rest.proxy_registry.PROXY_TARGETS``
   中追加一条 ``ProxyTarget`` 记录（path segment、配置取值函数、
   健康探测路径）

相关文档
--------

- 监控指标接口：:doc:`metrics`
- 反向代理模块设计：:doc:`../module-design/reverse-proxy`
- 监控部署指南：:doc:`../../user-guide/deploy-guide/config-run-metrics`
