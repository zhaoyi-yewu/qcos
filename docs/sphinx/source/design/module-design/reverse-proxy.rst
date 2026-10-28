反向代理（Reverse Proxy）
====================================

本章节介绍 QCOS 操作系统中反向代理模块的设计与实现。

概述
--------------------

QCOS 在运维侧依赖若干独立部署的组件（Prometheus、Alertmanager 等）。
这些组件都有自己的 HTTP API，但默认监听独立端口、独立鉴权策略，
对前端 / 第三方调用方而言入口分散。

反向代理模块解决以下问题：

- **入口统一**：调用方只需要知道 QCOS API 服务地址与端口，无需感知后端各组件地址。
- **鉴权统一**：复用 QCOS 的 JWT 鉴权机制，不再要求 Prometheus/Alertmanager 自身配置认证。
- **网络收敛**：生产部署中只需对外开放 QCOS API 端口，Prometheus/Alertmanager 端口可封闭在内网。
- **WebUI 集成**：QCOS WebUI 设备监控页可直接通过 QCOS API 调用 PromQL，无需浏览器直连 Prometheus。

命名空间约定
--------------------

所有反向代理端点挂在 QCOS FastAPI 主应用的 ``/v1/proxy/<service>`` 路径下，
其中 ``<service>`` 是被代理组件的小写标识。

.. list-table::
   :header-rows: 1
   :widths: 35 30 35

   * - 端点
     - 默认上游
     - 说明
   * - ``/v1/proxy/prometheus/*``
     - ``http://127.0.0.1:9090``
     - Prometheus HTTP API（``/api/v1/query``、``/api/v1/query_range``、``/api/v1/targets``、``/api/v1/alerts`` 等）
   * - ``/v1/proxy/alertmanager/*``
     - ``http://127.0.0.1:9093``
     - Alertmanager HTTP API（``/api/v2/alerts``、``/api/v2/silences``、``/api/v2/status`` 等）

**路径剥离规则**：FastAPI 的 ``app.mount("/v1/proxy/<service>", sub_app)``
会自动剥掉挂载前缀，子应用收到的 ``path`` 即为上游所需的相对路径。例如：

.. code-block:: text

   客户端请求:  GET /v1/proxy/prometheus/api/v1/query?query=up
   代理转发:    GET http://127.0.0.1:9090/api/v1/query?query=up

配置
--------------------

配置节
~~~~~~~~~~~~~~~~~~~~

在 ``etc/qcos/qcos.toml`` 中新增 ``[PROXY]`` 配置节：

.. code-block:: toml

   [PROXY]
   # Prometheus base URL. Empty string disables the proxy endpoint.
   PROMETHEUS_BASE_URL = "http://127.0.0.1:9090"
   # Alertmanager base URL. Empty string disables the proxy endpoint.
   ALERTMANAGER_BASE_URL = "http://127.0.0.1:9093"

配置模型
~~~~~~~~~~~~~~~~~~~~

在 ``src/wy_qcos/common/config.py`` 中新增 ``ProxySection``：

.. list-table::
   :header-rows: 1
   :widths: 30 15 30 25

   * - 字段
     - 类型
     - 默认值
     - 说明
   * - ``PROMETHEUS_BASE_URL``
     - ``str``
     - ``http://127.0.0.1:9090``
     - Prometheus 上游地址
   * - ``ALERTMANAGER_BASE_URL``
     - ``str``
     - ``http://127.0.0.1:9093``
     - Alertmanager 上游地址

空字符串语义：**该上游不启用**，对应的 mount 逻辑跳过，不影响其他路由。

鉴权
--------------------

代理端点的鉴权策略与 MCP 端点一致，**跟随全局 ``AUTH_MODE``**：

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - ``AUTH_MODE``
     - 行为
   * - ``no``
     - 不鉴权，所有请求直接放行
   * - ``virtual_instance``
     - 不鉴权（虚拟实例模式无 JWT）
   * - ``jwt``
     - 校验 ``Authorization: Bearer <token>``，复用 ``decode_jwt_token``

校验失败返回 **HTTP 401** + JSON 错误体：

.. code-block:: json

   {
     "jsonrpc": "2.0",
     "error": {
       "code": -32001,
       "message": "Unauthorized: valid JWT token required"
     },
     "id": null
   }

.. note::

   QCOS JWT 默认有效期较短，因此该代理主要面向 **WebUI / 用户脚本** 这类已登录场景。

请求/响应透传规则
--------------------

请求透传
~~~~~~~~~~~~~~~~~~~~

代理把入站 HTTP 请求转换为对上游的调用：

- **方法**：原样透传（GET/POST/PUT/DELETE/PATCH/HEAD/OPTIONS）
- **路径**：剥离 ``/v1/proxy/<service>`` 前缀后透传
- **Query string**：原样透传
- **Body**：流式透传（不缓冲、不改写）
- **Headers**：

  - **剔除**\ （hop-by-hop，RFC 2616 §13.5.1 + Host）：

    - ``Connection``
    - ``Keep-Alive``
    - ``Proxy-Authenticate``
    - ``Proxy-Authorization``
    - ``TE``
    - ``Trailer``
    - ``Transfer-Encoding``
    - ``Upgrade``
    - ``Host``\ （由 httpx 根据目标 URL 重新生成）

  - **保留**：其他所有 header，包括 ``Authorization``、``Cookie``、``Content-Type``、``Accept``、``User-Agent`` 等

响应透传
~~~~~~~~~~~~~~~~~~~~

- **Status code**：原样返回
- **Headers**：剔除 hop-by-hop 头后原样返回；``Content-Length`` 由 ASGI 服务器根据 body 重新计算
- **Body**：流式返回（不缓冲、不改写）

错误处理
~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 40 15 45

   * - 场景
     - 状态码
     - 响应体
   * - 未配置该上游 base_url
     - 路由不存在
     - FastAPI 默认 404
   * - 未通过 JWT 校验
     - 401
     - ``{"jsonrpc":"2.0","error":{"code":-32001,...}}``
   * - 上游连接失败 / DNS 失败 / 拒绝连接
     - 502
     - ``{"detail":"Bad gateway: <reason>"}``
   * - 上游读 / 写超时
     - 504
     - ``{"detail":"Gateway timeout"}``
   * - 客户端中断
     - 499（尽可能）/ 静默关闭
     - —

超时
~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 20 20 60

   * - 类型
     - 默认值
     - 说明
   * - connect
     - 5s
     - 与上游建立 TCP 连接
   * - read
     - 60s
     - 等待上游响应（PromQL 长查询足够）
   * - write
     - 30s
     - 发送请求体
   * - pool
     - 5s
     - 从连接池获取连接

连接复用
~~~~~~~~~~~~~~~~~~~~

``httpx.AsyncClient`` 在 FastAPI ``lifespan`` 启动时创建一次，
存到 ``app.state.http_client``，所有代理请求共享连接池。
``shutdown`` 阶段调用 ``aclose()`` 释放资源。

健康检查 API
--------------------

为了让 WebUI 在不直接访问上游的情况下也能感知每个代理后端是否可用，
QCOS 在 JSON-RPC 入口暴露 ``get_proxy_health`` 方法。

**端点**

.. code-block:: text

   POST /v1/metrics
   {"jsonrpc":"2.0","method":"get_proxy_health","params":{},"id":1}

**权限**：admin only（与 ``get_system_health`` 一致）。

**响应**

.. code-block:: json

   {
     "jsonrpc": "2.0",
     "id": 1,
     "result": {
       "targets": [
         {
           "name": "prometheus",
           "path": "/v1/proxy/prometheus",
           "base_url": "http://127.0.0.1:9090",
           "enabled": true,
           "healthy": true,
           "status": "online",
           "latency_ms": 3,
           "detail": ""
         },
         {
           "name": "alertmanager",
           "path": "/v1/proxy/alertmanager",
           "base_url": "http://127.0.0.1:9093",
           "enabled": true,
           "healthy": false,
           "status": "offline",
           "latency_ms": null,
           "detail": "connect error: connection refused"
         }
       ]
     }
   }

**字段语义**

.. list-table::
   :header-rows: 1
   :widths: 20 20 60

   * - 字段
     - 类型
     - 说明
   * - ``name``
     - ``str``
     - 注册表中的 ``path_segment``，例如 ``prometheus``
   * - ``path``
     - ``str``
     - 对外公开的挂载路径，例如 ``/v1/proxy/prometheus``
   * - ``base_url``
     - ``str``
     - 配置的上游 base URL；disabled 时为空串
   * - ``enabled``
     - ``bool``
     - 是否启用（``base_url`` 非空）
   * - ``healthy``
     - ``bool``
     - 探测是否成功（上游返回 2xx）
   * - ``status``
     - ``str``
     - ``online`` / ``offline`` / ``disabled``
   * - ``latency_ms``
     - ``int | null``
     - 探测往返延迟（毫秒）；失败或 disabled 时为 ``null``
   * - ``detail``
     - ``str``
     - 失败时的简短原因（如 ``connect error: ...``）

**探测路径**

每个代理目标在 ``PROXY_TARGETS`` 注册时会声明一个 ``health_path``：

.. list-table::
   :header-rows: 1
   :widths: 30 30

   * - 目标
     - health_path
   * - prometheus
     - ``/-/healthy``
   * - alertmanager
     - ``/-/healthy``

**探测策略**

* 方法：``GET``
* 超时：connect 2s / read 3s（快速失败，便于 WebUI 轮询）
* 健康判据：HTTP 状态码 2xx
* 3xx/4xx/5xx 视为 ``offline``\ （上游可达但行为异常）
* 连接错误 / DNS 错误 / 超时均视为 ``offline``，``detail`` 给出原因

**复用连接**

优先复用 ``app.state.http_client``；在单元测试等无 lifespan
场景下自动创建临时 client 并在结束时关闭。

模块组织
--------------------

.. code-block:: text

   src/wy_qcos/api/posiq/routes_rest/
   ├── __init__.py
   ├── reverse_proxy.py      # create_reverse_proxy_app() 工厂
   ├── proxy_auth.py         # ProxyJwtMiddleware
   └── proxy_registry.py     # PROXY_TARGETS 注册表

``PROXY_TARGETS`` 是一个列表，元素为 ``(path_segment, config_getter)``：

.. code-block:: python

   PROXY_TARGETS = [
       ("prometheus",   lambda: Config.PROXY.PROMETHEUS_BASE_URL),
       ("alertmanager", lambda: Config.PROXY.ALERTMANAGER_BASE_URL),
   ]

``fastapi_server.py`` 启动时遍历该注册表，对每个 **非空** base_url 调用：

.. code-block:: python

   app.mount(
       f"/v1/proxy/{path_segment}",
       ProxyJwtMiddleware(create_reverse_proxy_app(path_segment, base_url)),
   )

新增一个被代理服务只需两步：

1. 在 ``Config.PROXY`` 添加对应 ``XXX_BASE_URL`` 字段（默认 ``""``）
2. 在 ``PROXY_TARGETS`` 追加一条 ``(path_segment, getter)``

无需改动 ``fastapi_server.py``。

与现有组件的关系
--------------------

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - 组件
     - 关系
   * - ``/v1/metrics`` (JSON-RPC)
     - 现有的 JSON-RPC 接口，提供 QCOS 内部聚合后的 ``get_system_health`` / ``get_job_stats`` 等，**与代理并存**：RPC 适合结构化查询，代理适合完整 PromQL / Alertmanager API
   * - ``/metrics`` (独立端口)
     - QCOS 自身暴露给 Prometheus 抓取的指标端点，独立 HTTP 服务（默认 :19400），**与本代理无关**
   * - MCP ``/v1/ai/mcp``
     - 与本代理同级的另一个 REST 风格挂载点，鉴权模式相同

使用示例
--------------------

假设 QCOS API 监听 ``192.168.0.1:18400``，已获取 JWT token：

.. code-block:: bash

   # 1. PromQL 即时查询
   curl -H "Authorization: Bearer $TOKEN" \
     'http://192.168.0.1:18400/v1/proxy/prometheus/api/v1/query?query=up'

   # 2. PromQL 范围查询（WebUI 设备监控页用）
   curl -H "Authorization: Bearer $TOKEN" \
     'http://192.168.0.1:18400/v1/proxy/prometheus/api/v1/query_range?query=job_count&start=2026-10-23T00:00:00Z&end=2026-10-23T01:00:00Z&step=15'

   # 3. 查看 Alertmanager 当前告警
   curl -H "Authorization: Bearer $TOKEN" \
     'http://192.168.0.1:18400/v1/proxy/alertmanager/api/v2/alerts'

   # 4. 创建静默
   curl -X POST \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "matchers": [{"name":"alertname","value":"QcosServiceUnavailable","isRegex":false}],
       "startsAt": "2026-10-23T01:00:00Z",
       "endsAt":   "2026-10-23T02:00:00Z",
       "createdBy": "admin",
       "comment":  "maintenance window"
     }' \
     'http://192.168.0.1:18400/v1/proxy/alertmanager/api/v2/silences'

限制与注意事项
--------------------

1. **不支持 WebSocket**：第一版仅支持普通 HTTP 请求/响应。
2. **不改写响应内容**：上游返回 JSON 中若包含 **绝对 URL**\ （极少见），
   不会因经过代理而改写。Prometheus / Alertmanager 的常见 API 均返回纯数据，不受影响。
3. **JWT 过期**：长会话需客户端自行刷新 token。
4. **大响应**：当前实现流式转发，但需要 ASGI 服务器（uvicorn）配合。
   已在连接池、read timeout 上预留足够余量。

测试
--------------------

单元测试位于：

- ``src/wy_qcos/tests/unit_tests/api/test_reverse_proxy.py``：
  基于 ``httpx.MockTransport``，覆盖路径/query/body/header 透传、
  上游 4xx/5xx 透传、上游不可达 502、JWT 鉴权（含三种 ``AUTH_MODE``）、
  未配置上游时跳过 mount 等场景
- ``src/wy_qcos/tests/unit_tests/common/test_config_proxy.py``：
  验证 ``ProxySection`` 默认值与可选字段语义

系统测试建议（后续追加）：

- 启动一个 mock Prometheus（任何返回固定 JSON 的 HTTP 服务）+ QCOS，
  验证 ``/v1/proxy/prometheus/api/v1/query`` 端到端可用
- 与 WebUI 设备监控页联调
