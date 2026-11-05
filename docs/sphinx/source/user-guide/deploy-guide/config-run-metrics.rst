监控组件配置与启动
======================

本文档介绍 QCOS 监控组件栈的部署方法，包括一键启动脚本 ``run-docker-metrics.sh`` 会部署哪些组件、各组件的职责、关键配置文件位置，以及常见运维操作。

.. contents:: 目录
   :local:
   :depth: 3

概述
----

QCOS 的监控栈由 ``build-scripts/run-docker-metrics.sh`` 一键启动，
包含指标采集、存储、可视化、告警和日志聚合等组件。整个栈通过
``build-scripts/docker-compose-metrics.yaml`` 编排，
**所有容器均运行在 host 网络模式**，直接监听宿主机端口。

.. important::

   **监控组件栈是可选的（Optional）。** QCOS 主服务
   （API Server / WebUI / Prefect / Redis / PostgreSQL）不依赖任何
   监控组件即可正常运行；监控栈仅用于可观测性增强（指标可视化、
   告警通知、日志聚合）。如果你不需要这些能力，可以**跳过本文档**，
   不执行 ``run-docker-metrics.sh``。

启动后部署的组件
-----------------

``run-docker-metrics.sh`` 会按以下顺序部署 7 个监控组件：

.. list-table::
   :header-rows: 1
   :widths: 18 14 18 50

   * - 组件
     - 容器名
     - 默认端口
     - 职责
   * - Prometheus
     - ``prometheus``
     - 9090
     - 指标采集与时序存储；按 ``/etc/qcos/prometheus/prometheus.yml`` 配置周期抓取 QCOS Metrics / Node Exporter / Process Exporter 等目标，30 天数据保留。
   * - Alertmanager
     - ``alertmanager``
     - 9093
     - 告警路由与通知；接收 Prometheus 触发的告警并按 ``/etc/qcos/alertmanager/alertmanager.yml`` 路由到邮件 / Webhook 等接收器。
   * - Grafana
     - ``grafana``
     - 3000
     - 监控可视化仪表盘；通过 ``/etc/qcos/grafana/provisioning`` 自动注入 Prometheus 数据源与预置面板。
   * - Node Exporter
     - ``node-exporter``
     - 9100
     - 宿主机硬件 / 操作系统指标（CPU、内存、磁盘、网络、文件系统等）；挂载宿主机 ``/proc``、``/sys``、``/`` （只读、``rslave``）保证数据与宿主机 ``df`` 一致。
   * - Process Exporter
     - ``process-exporter``
     - 9256
     - 进程级指标（每个进程的 CPU / 内存 / IO）；按 ``/etc/qcos/process-exporter/process-exporter.yml`` 中的进程名模式采集 QCOS 关键进程。
   * - VictoriaLogs
     - ``victorialogs``
     - 9428
     - 日志聚合存储；接收 Fluent Bit 推送的结构化日志，提供 LogsQL 查询接口，30 天保留期。
   * - Fluent Bit
     - ``fluentbit``
     - （无监听）
     - 日志采集与转发；按 ``/etc/qcos/fluent-bit/fluent-bit.conf`` 配置 tail ``/var/log/qcos`` 下的日志文件，结构化解析后推送给 VictoriaLogs。

启动方法
--------

前提条件
~~~~~~~~~

- 已安装 ``docker`` 与 ``docker-compose``
- 已存在 ``/etc/qcos/qcos.toml``\（QCOS 主配置，监控栈从中读取 metrics 端口等）
- 已完成 ``build-scripts/env.template`` → ``.env`` 的环境变量初始化（见 :doc:`edit-env`）

一键启动
~~~~~~~~~

.. code-block:: shell

   cd build-scripts
   ./run-docker-metrics.sh

脚本会按顺序执行以下动作：

1. **加载环境变量** —— ``source setup-env.sh``，读取 ``.env``
   与系统环境。
2. **首次部署配置文件** —— 若 ``/etc/qcos/prometheus`` 等目录不
   存在，则从源码树 ``etc/prometheus/``、``etc/alertmanager/``、
   ``etc/grafana/``、``etc/process-exporter/``、``etc/fluent-bit/``
   拷贝默认配置，并用 ``envsubst`` 把 ``${METRICS_SERVER_ACCESS_IP}``
   等环境变量替换进配置文件。
3. **生成临时 docker-compose 文件** —— 把
   ``docker-compose-metrics.yaml`` 中的 ``${VAR}`` 占位符替换为当前
   环境变量值，输出到 ``.docker-compose-metrics.yaml``。
4. **重启监控栈** —— ``docker-compose down && docker-compose up -d``。

.. note::

   后续重新执行脚本时，``/etc/qcos/<component>/`` 目录已存在，配置文件不会被覆盖，需要手工编辑后再次执行 ``./run-docker-metrics.sh`` 让容器重启加载新配置。

关键环境变量
------------

监控栈的监听端口、目标地址、登录密码等都通过 ``.env`` 控制：

.. list-table::
   :header-rows: 1
   :widths: 32 18 50

   * - 变量
     - 默认值
     - 说明
   * - ``METRICS_SERVER_ACCESS_IP``
     - （必填）
     - QCOS Metrics 服务对外暴露的 IP，Prometheus 抓取目标使用该 IP。
   * - ``QCOS_SERVER_IP``
     - （必填）
     - QCOS API 服务 IP，用作 Alertmanager 抓取目标。
   * - ``PROMETHEUS_LISTEN_PORT``
     - ``9090``
     - Prometheus Web UI / API 监听端口。
   * - ``ALERTMANAGER_LISTEN_PORT``
     - ``9093``
     - Alertmanager Web UI / API 监听端口。
   * - ``GRAFANA_LISTEN_PORT``
     - ``3000``
     - Grafana Web UI 监听端口（通过 ``GF_SERVER_ROOT_URL`` 透传）。
   * - ``GRAFANA_ADMIN_PASSWORD``
     - ``123456``
     - Grafana admin 账号初始密码，生产环境**必须修改**。
   * - ``NODE_EXPORTER_LISTEN_PORT``
     - ``9100``
     - Node Exporter 监听端口。
   * - ``PROCESS_EXPORTER_LISTEN_PORT``
     - ``9256``
     - Process Exporter 监听端口。
   * - ``VICTORIALOGS_LISTEN_PORT``
     - ``9428``
     - VictoriaLogs HTTP 监听端口。
   * - ``VICTORIALOGS_RETENTION``
     - ``30d``
     - VictoriaLogs 日志保留期，支持 ``7d`` / ``90d`` 等。
   * - ``METRICS_SERVER_LISTEN_PORT``
     - ``19400``
     - QCOS Metrics 服务自身端口（详见 :doc:`network-ports`）。

告警邮件通知（可选）
~~~~~~~~~~~~~~~~~~~~~

如果需要 Alertmanager 通过 SMTP 发送告警邮件，在 ``.env`` 中配置：

.. code-block:: shell

   SMTP_HOST=smtp.example.com
   SMTP_PORT=465
   SMTP_FROM=qcos-alert@example.com
   SMTP_AUTH_USER=qcos
   SMTP_AUTH_PASSWORD=<secret>
   ALERT_RECEIVE_EMAIL=ops@example.com

脚本检测到 ``SMTP_HOST`` 与 ``ALERT_RECEIVE_EMAIL`` 同时非空时，
会用 ``envsubst`` 渲染 ``/etc/qcos/alertmanager/alertmanager.yml`` 启用邮件路由；
任一为空则保留默认配置（不发送邮件）。

配置文件位置
------------

监控栈的所有配置文件都集中在 ``/etc/qcos/`` 下，首次启动由脚本自动从源码树拷贝：

.. code-block:: text

   /etc/qcos/
   ├── prometheus/
   │   ├── prometheus.yml          # Prometheus 抓取配置（targets / rules）
   │   └── rules/                  # 告警规则
   ├── alertmanager/
   │   └── alertmanager.yml        # 告警路由 / 接收器配置
   ├── grafana/
   │   └── provisioning/
   │       ├── datasources/        # 自动注入 Prometheus 数据源
   │       └── dashboards/         # 预置仪表盘 JSON
   ├── process-exporter/
   │   └── process-exporter.yml    # 进程名匹配规则
   ├── fluent-bit/
   │   ├── fluent-bit.conf         # 主配置（输入 / 解析 / 输出）
   │   └── parsers.conf            # 日志格式解析器
   └── victorialogs/               # VictoriaLogs 数据目录占位（无配置文件）

常用运维操作
------------

查看容器状态
~~~~~~~~~~~~~

.. code-block:: shell

   docker ps --filter name=prometheus --filter name=alertmanager \
             --filter name=grafana --filter name=node-exporter \
             --filter name=process-exporter --filter name=victorialogs \
             --filter name=fluentbit

查看 Prometheus 抓取目标
~~~~~~~~~~~~~~~~~~~~~~~~~

浏览器访问 ``http://<host>:9090/targets``，确认 ``qcos-metrics``、``node-exporter``、``process-exporter`` 等 job 均为 ``UP``。

查看 Grafana 仪表盘
~~~~~~~~~~~~~~~~~~~~

浏览器访问 ``http://<host>:3000``，使用 ``admin`` / ``${GRAFANA_ADMIN_PASSWORD}`` 登录。

修改抓取配置后重启
~~~~~~~~~~~~~~~~~~~

.. code-block:: shell

   vim /etc/qcos/prometheus/prometheus.yml
   # 重新渲染 + 重启监控栈
   cd build-scripts && ./run-docker-metrics.sh

或者仅热更新 Prometheus 配置：

.. code-block:: shell

   curl -X POST http://127.0.0.1:9090/-/reload

查看日志
~~~~~~~~~

.. code-block:: shell

   docker logs -f prometheus
   docker logs -f alertmanager
   docker logs -f grafana
   docker logs -f victorialogs
   docker logs -f fluentbit

VictoriaLogs 日志查询
~~~~~~~~~~~~~~~~~~~~~~

VictoriaLogs 提供 LogsQL 查询接口，例如查询最近 100 条 QCOS 错误日志：

.. code-block:: shell

   curl -s "http://127.0.0.1:9428/select/logsql/query" \
       -d 'query=level:error' -d 'limit=100'

或在 QCOS WebUI 的「监控中心 → 日志」标签页中直接检索。

安全建议
--------

- 监控栈端口（``9090`` / ``9093`` / ``3000`` / ``9100`` / ``9256`` / ``9428``）建议**仅在内网开放**，对外通过防火墙或安全组限制来源 IP。
- 生产环境务必修改 ``GRAFANA_ADMIN_PASSWORD`` 默认值。
- 如需对 Grafana 启用 HTTPS，请在 ``.env`` 中追加 ``GF_SERVER_PROTOCOL``、``GF_SERVER_CERT_FILE``、``GF_SERVER_CERT_KEY`` 并挂载证书目录。
- 各容器均启用 ``no-new-privileges`` 与只读根文件系统（除 Fluent Bit / VictoriaLogs 外），符合最小权限原则；如需进一步收紧请改用非 host 网络 + 自定义 bridge。

参考文档
--------

- :doc:`network-ports` —— 端口矩阵与防火墙建议
- :doc:`security` —— HTTPS / 认证配置
- :doc:`config-run-webui` —— WebUI 部署
