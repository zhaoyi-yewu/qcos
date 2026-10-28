MCP服务
====================================

本章节介绍 QCOS 操作系统中 MCP 服务的设计与实现。

概述
--------------------

MCP（Model Context Protocol）是一种开放协议，用于在 AI 助手与外部系统之间建立标准化的上下文交互通道。
QCOS 通过集成 MCP 服务，将量子计算操作系统的设备管理、作业提交、资源调度等核心能力暴露给 AI 助手，
使用户可以通过自然语言指令完成量子计算相关操作。

MCP 服务挂载在 QCOS 现有的 FastAPI 应用之上，与 JSON-RPC API 共享同一 HTTP 端口，
无需额外开放端口。AI 客户端通过 ``/v1/ai/mcp`` 端点接入。

架构设计
--------------------

MCP 服务采用分层架构设计，从上到下依次为：

1. **AI 客户端层**：支持 MCP 协议的 AI 助手（如 Claude、GPT 等）
2. **MCP 协议层**：基于 MCP Python SDK 实现的服务端，处理协议解析与路由
3. **工具适配层**：将 MCP 工具调用转换为 QCOS 内部 JSON-RPC API 调用
4. **业务逻辑层**：QCOS 现有的设备管理、作业调度、用户管理等模块

.. code-block:: text

   +---------------------+
   |   AI Assistant      |
   |  (Claude / GPT / ...)|
   +----------+----------+
              | MCP Protocol (HTTP/SSE)
   +----------v----------+
   |  MCP Server (qcos)  |
   |  /v1/ai/mcp         |
   +----------+----------+
              | Internal JSON-RPC
   +----------v----------+
   |  QCOS FastAPI App   |
   |  /v1/device, /v1/job|
   +----------+----------+
              |
   +----------v----------+
   |  Business Modules   |
   |  (Driver/Scheduler) |
   +---------------------+

核心设计决策
~~~~~~~~~~~~~~~~~~~~

**1. 共享端口而非独立服务**

MCP 服务不启动独立 HTTP 服务器，而是作为 ASGI 中间件挂载到现有 FastAPI 应用。
优点：

- 减少端口占用，简化部署
- 复用现有的认证、日志、监控中间件
- 避免跨进程通信开销

**2. 内部 JSON-RPC 调用**

MCP 工具不直接调用业务模块，而是通过 ``httpx`` 向自身发送 JSON-RPC 请求。
优点：

- 避免循环导入（MCP 层与业务层解耦）
- 复用现有的认证与依赖注入机制
- 保持 MCP 工具实现的简洁性

**3. 单例模式与生命周期管理**

MCP 2.x 版本要求显式管理任务组（task group）生命周期。
QCOS 在 FastAPI 应用启动时通过 ``init_mcp_lifespan()`` 初始化，
关闭时通过 ``cleanup_mcp_lifespan()`` 清理。

MCP 版本兼容
~~~~~~~~~~~~~~~~~~~~

实现同时兼容 MCP 1.x（``FastMCP``）和 2.x（``MCPServer``）两个版本：

.. code-block:: python

   try:
       from mcp.server.fastmcp import FastMCP as _MCPServer
       _MCP_VERSION = 1
   except ImportError:
       from mcp.server.mcpserver import MCPServer as _MCPServer
       _MCP_VERSION = 2

- MCP 1.x：使用 ``app.mount()`` 直接挂载
- MCP 2.x：使用自定义 ASGI 中间件拦截 ``/v1/ai/mcp`` 路径，
  并将请求路径重写为 ``/mcp`` 后转发给 MCP 应用

认证与安全
--------------------

JWT 认证
~~~~~~~~~~~~~~~~~~~~

当 ``AUTH_MODE`` 为 ``jwt`` 时，MCP 端点强制要求 Bearer Token：

- 中间件在请求到达 MCP 应用前校验 ``Authorization`` 头
- 无效或缺失 Token 返回 HTTP 401
- 当 ``AUTH_MODE`` 为 ``no`` 或 ``virtual_instance`` 时，MCP 端点开放访问

Host 头安全
~~~~~~~~~~~~~~~~~~~~

MCP 2.x 默认启用 DNS 重绑定保护（仅允许 localhost）。
QCOS 通过补丁禁用该检查，允许内网部署：

.. code-block:: python

   os.environ.setdefault("MCP_ALLOWED_HOSTS", "*")

MCP 工具集
--------------------

MCP 服务提供丰富的工具（Tools），覆盖 QCOS 主要功能领域：

设备管理
~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - 工具名称
     - 功能描述
   * - ``qcos_list_devices``
     - 列出所有可用量子设备
   * - ``qcos_get_device_detail``
     - 获取指定设备详细信息
   * - ``qcos_set_device``
     - 设置设备状态、启用标志、比特数
   * - ``qcos_calibrate_device``
     - 触发设备校准
   * - ``qcos_get_calibrate_results``
     - 获取校准结果
   * - ``qcos_set_device_options``
     - 设置设备选项
   * - ``qcos_get_device_options``
     - 获取设备选项

作业管理
~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - 工具名称
     - 功能描述
   * - ``qcos_submit_job``
     - 提交量子作业（QASM 代码）
   * - ``qcos_list_jobs``
     - 列出量子作业（支持过滤）
   * - ``qcos_get_job_status``
     - 获取作业状态
   * - ``qcos_get_job_result``
     - 获取作业执行结果
   * - ``qcos_cancel_jobs``
     - 取消作业
   * - ``qcos_delete_jobs``
     - 删除作业
   * - ``qcos_update_job``
     - 更新作业属性（``job_name`` / ``description`` 任意状态可改；``job_priority`` 仅允许在排队中（QUEUED）状态下修改）

资源规格（Flavor）
~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - 工具名称
     - 功能描述
   * - ``qcos_create_flavor``
     - 创建 Flavor
   * - ``qcos_update_flavor``
     - 更新 Flavor
   * - ``qcos_get_flavor``
     - 获取 Flavor 详情
   * - ``qcos_get_flavors``
     - 列出 Flavor（支持过滤与分页）
   * - ``qcos_delete_flavors``
     - 删除 Flavor

设备分组
~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - 工具名称
     - 功能描述
   * - ``qcos_create_device_group``
     - 创建设备分组
   * - ``qcos_update_device_group``
     - 更新设备分组
   * - ``qcos_get_device_group``
     - 获取设备分组详情
   * - ``qcos_get_device_groups``
     - 列出设备分组
   * - ``qcos_delete_device_groups``
     - 删除设备分组

驱动与转译器
~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - 工具名称
     - 功能描述
   * - ``qcos_get_drivers``
     - 列出所有驱动
   * - ``qcos_get_driver``
     - 获取驱动详情
   * - ``qcos_get_transpilers``
     - 列出所有转译器
   * - ``qcos_get_transpiler``
     - 获取转译器详情

项目管理
~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - 工具名称
     - 功能描述
   * - ``qcos_create_project``
     - 创建项目
   * - ``qcos_get_project``
     - 获取项目详情
   * - ``qcos_get_projects``
     - 列出项目
   * - ``qcos_update_project``
     - 更新项目
   * - ``qcos_delete_project``
     - 删除项目

用户与权限管理
~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - 工具名称
     - 功能描述
   * - ``qcos_login``
     - 用户登录，获取 JWT Token
   * - ``qcos_get_current_user``
     - 获取当前认证用户信息
   * - ``qcos_create_user``
     - 创建用户（管理员）
   * - ``qcos_get_user``
     - 获取用户详情
   * - ``qcos_get_users``
     - 列出用户
   * - ``qcos_update_user``
     - 更新用户
   * - ``qcos_delete_user``
     - 删除用户
   * - ``qcos_change_password``
     - 修改密码
   * - ``qcos_create_role``
     - 创建角色
   * - ``qcos_get_role``
     - 获取角色详情
   * - ``qcos_get_roles``
     - 列出角色
   * - ``qcos_update_role``
     - 更新角色
   * - ``qcos_delete_role``
     - 删除角色
   * - ``qcos_get_user_mgmt``
     - 获取用户管理配置
   * - ``qcos_set_user_mgmt``
     - 设置用户认证模式
   * - ``qcos_get_login_logs``
     - 获取登录日志
   * - ``qcos_clear_login_logs``
     - 清除登录日志

系统监控
~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - 工具名称
     - 功能描述
   * - ``qcos_get_system_health``
     - 获取系统健康状态
   * - ``qcos_get_api_stats``
     - 获取 API 请求统计
   * - ``qcos_get_job_stats``
     - 获取作业统计
   * - ``qcos_ping``
     - 系统连通性检查
   * - ``qcos_system_info``
     - 获取系统信息
   * - ``qcos_show_mem``
     - 显示内存使用情况
   * - ``qcos_gc_mem``
     - 触发垃圾回收
   * - ``qcos_list_workers``
     - 列出 Prefect Worker
   * - ``qcos_restart_worker``
     - 重启 Worker

MCP 资源
--------------------

除工具外，MCP 服务还提供两个资源（Resources），供 AI 助手直接读取：

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - 资源 URI
     - 内容描述
   * - ``qcos://version``
     - QCOS 系统版本信息
   * - ``qcos://devices``
     - 可用量子设备摘要

部署配置
--------------------

环境变量
~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - 环境变量
     - 说明
   * - ``QCOS_MCP_BASE_URL``
     - QCOS 内部 API 基础地址，默认 ``http://127.0.0.1:18400``
   * - ``MCP_ALLOWED_HOSTS``
     - MCP 允许的 Host 头，默认 `*` （允许所有）

端点地址
~~~~~~~~~~~~~~~~~~~~

MCP 服务端点：``http://<host>:<port>/v1/ai/mcp``

- 与 JSON-RPC API 共享同一端口
- 支持 Streamable HTTP（MCP 2.x）和 SSE（MCP 1.x）传输
