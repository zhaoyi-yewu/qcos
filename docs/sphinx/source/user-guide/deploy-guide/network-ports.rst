服务端口
================

本章节介绍 QCOS 部署后各服务对外暴露的网络端口及其用途，便于在网络规划、防火墙策略和容器编排（host 网络模式）中正确放通与管理端口。

.. contents:: 目录
   :local:
   :depth: 3

默认端口总览
------------

下表列出QCOS各服务监听的宿主机默认端口、协议与用途：

.. list-table::
   :header-rows: 1
   :widths: 22 12 12 54

   * - 服务
     - 默认端口
     - 协议
     - 用途
   * - QCOS API 服务
     - 18400
     - HTTP / HTTPS
     - QCOS 对外 API 服务器，提供作业提交、设备管理、用户认证等接口；启用 SSL 后在同一端口提供 HTTPS 服务。
   * - QCOS Metrics
     - 19400
     - HTTP
     - QCOS 自身的 Prometheus 指标采集端点（``/metrics``），供 Prometheus 抓取。
   * - QCOS WebUI
     - 18401
     - HTTP
     - QCOS Web 管理界面（nginx），对外提供可视化操作控制台。
   * - Prefect Server
     - 4200
     - HTTP
     - Prefect 调度引擎的 API 与 UI 服务，QCOS 通过 ``PREFECT_API_URL`` 连接该端口进行作业编排。
   * - Redis
     - 6379
     - TCP
     - 子电路结果暂存、键空间事件通知与 Prefect 事件消息存储；需配置访问密码。
   * - PostgreSQL
     - 5432
     - TCP
     - QCOS 与 Prefect 的持久化数据库（``qcos`` 与 ``prefect`` 两个库），SQLite 模式下不占用本端口。
   * - Prometheus
     - 9090
     - HTTP
     - 指标采集与查询服务，抓取 QCOS Metrics 端点并存储时序数据。
   * - Alertmanager
     - 9093
     - HTTP
     - 告警管理与通知服务，处理 Prometheus 触发的告警规则。
   * - Grafana
     - 3000
     - HTTP
     - 监控可视化仪表盘，从 Prometheus 数据源展示 QCOS 运行指标与告警。

.. note::

   以上均为默认端口，可在 ``build-scripts/env.template``\（复制为 ``.env``）或对应配置文件中修改。修改任一端口后，需同步更新关联服务的连接配置（例如 ``PREFECT_API_URL``、``REDIS_URL``、``QCOS_DATABASE_CONNECTION_URL`` 等）。

端口配置说明
------------

各端口的监听 IP 与端口通过环境变量（``.env``）或配置文件控制，主要配置项如下：

QCOS API 服务
~~~~~~~~~~~~~~

- 配置文件： ``etc/qcos/qcos.toml`` 的 ``[API_SERVER]`` 段
- 监听 IP： ``API_SERVER_LISTEN_IP``\（默认空，监听全部 IPv4+IPv6）
- 监听端口： ``API_SERVER_LISTEN_PORT``\（默认 ``18400``）
- 启用 HTTPS 时，同一端口对外提供 HTTPS 服务，相关配置见 ``[SSL]`` 段与 :doc:`security`

QCOS WebUI
~~~~~~~~~~~

- 配置来源： ``.env`` 的 ``QCOS_WEBUI_LISTEN_IP`` 与 ``QCOS_WEBUI_LISTEN_PORT``
- 默认监听 IP： ``0.0.0.0``
- 默认监听端口： ``18401``
- 容器内由 nginx 按该地址监听，并将前端请求代理至静态资源。

Prefect Server
~~~~~~~~~~~~~~~

- 配置来源： ``.env`` 的 ``PREFECT_SERVER_API_HOST`` 与 ``PREFECT_SERVER_PORT``
- 默认监听端口： ``4200``
- QCOS 通过 ``PREFECT_API_URL``\（默认 ``http://127.0.0.1:4200/api``）连接该服务。

Redis
~~~~~~

- 配置来源： ``.env`` 的 ``REDIS_SERVER_IP``、``REDIS_SERVER_PORT``、``REDIS_SERVER_LISTEN_IP``
- 默认监听端口： ``6379``
- 启动时通过 ``--requirepass`` 设置访问密码，并通过 ``--bind`` 限定监听地址。

PostgreSQL
~~~~~~~~~~~

- 配置文件： ``etc/postgres/postgresql.conf``
- 默认监听地址： ``listen_addresses = '*'``
- 默认端口： ``5432``\（配置项 ``port``，默认注释即生效）
- QCOS 与 Prefect 分别使用 ``qcos`` 与 ``prefect`` 两个数据库，
  连接 URL 见 ``.env`` 中的 ``QCOS_DATABASE_CONNECTION_URL`` 与 ``PREFECT_SERVER_DATABASE_CONNECTION_URL``。

监控组件
~~~~~~~~~

- QCOS Metrics： ``etc/qcos/qcos.toml`` 的 ``[METRICS_SERVER]`` 段，``METRICS_SERVER_LISTEN_PORT`` 默认 ``19400``。
- Prometheus： ``.env`` 的 ``PROMETHEUS_LISTEN_PORT``，默认 ``9090``，抓取目标为 QCOS Metrics 端点。
- Alertmanager： ``.env`` 的 ``ALERTMANAGER_LISTEN_PORT``，默认 ``9093``。
- Grafana： ``.env`` 的 ``GRAFANA_LISTEN_PORT``，默认 ``3000``，默认管理员密码由 ``GRAFANA_ADMIN_PASSWORD`` 配置。

驱动 Mock API Server 端口
-------------------------

QCOS 的系统测试（ ``src/wy_qcos/tests/system_tests/`` ）为每个驱动内置了 Mock API Server，用于在无真实量子设备时模拟设备侧的作业提交、状态查询与结果返回接口。

下表列出各驱动 Mock API Server 的默认监听端口与协议：

.. list-table::
   :header-rows: 1
   :widths: 30 12 14 44

   * - 驱动 / 设备
     - 默认端口
     - 协议
     - 对应配置文件与说明
   * - qboson（TianGong 550/1000 v2）
     - 18600
     - HTTP
     - ``etc/qcos/conf.d/tiangong1000_v2.toml``、``tiangong550_v2.toml``，模拟玻色量子-天工接口。
   * - TianGong100
     - 18601
     - HTTP
     - ``etc/qcos/conf.d/tiangong100.toml``，模拟玻色量子-天工旧版接口。
   * - SpinQ NMR（Gemini/Triangulum）
     - 18602
     - HTTP
     - ``etc/qcos/conf.d/spinq_gemini.toml``、``spinq_triangulum.toml``，基于aiohttp + Socket.IO模拟量旋科技云接口。
   * - CIQTek Ion-1
     - 18605
     - HTTP
     - ``etc/qcos/conf.d/ciqtek_ion_1.toml``，模拟国仪量子离子阱设备接口。
   * - Quafu
     - 18606
     - HTTP
     - ``etc/qcos/conf.d/quafu_*.toml``，模拟北京量子院-夸父平台接口。
   * - Logical Qubit（Agate100/MQ02/QZ01/QZ02）
     - 18607
     - HTTP
     - ``etc/qcos/conf.d/lq_*.toml``，模拟逻辑比特平台接口。
   * - WuYue Hanyuan1（含 sim）
     - 18609
     - HTTP
     - ``etc/qcos/conf.d/wy_hanyuan1.toml``、``wy_hanyuan1_sim.toml``，模拟中科酷原-汉原1设备接口。
   * - Hanyuan1
     - 18610
     - HTTP
     - ``etc/qcos/conf.d/hanyuan1.toml``，模拟中科酷原-汉原1。
   * - CETC Baihua
     - 18611
     - HTTP
     - ``etc/qcos/conf.d/cetc_baihua.toml``，模拟国基量子平台接口。
.. note::

   以上 Mock API Server 仅在系统测试中由 ``test_job.py`` 通过 ``multiprocessing.Process`` 临时启动，监听 ``127.0.0.1``，测试结束后自动终止，**不会在生产部署中常驻**。生产环境中各驱动连接的是真实量子设备的远端 API 地址，具体由对应 ``conf.d/*.toml`` 配置文件中的 ``url`` / ``host`` / ``port`` 等字段指定。

端口访问建议
------------

- **API 与 WebUI**：对外暴露 ``18400``、``18401``，建议在生产环境启用 HTTPS 并通过反向代理或防火墙限制来源 IP。
- **内部服务**：Prefect（``4200``）、Redis（``6379``）、PostgreSQL（``5432``）为内部组件，建议仅监听 ``127.0.0.1`` 或内网地址，禁止对公网开放。
- **监控组件**：Prometheus（``9090``）、Alertmanager（``9093``）、Grafana（``3000``）建议仅在内网开放，Grafana 如需对外访问应配置强密码并启用 HTTPS。
- **SSL 配置**：API 服务启用 HTTPS 的证书生成与配置步骤详见 :doc:`security`。
