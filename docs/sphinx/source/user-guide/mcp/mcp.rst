MCP服务使用指南
==================

QCOS 通过 MCP（Model Context Protocol）服务将量子计算能力暴露给 AI 助手。
用户可以通过自然语言与 AI 助手交互，完成设备查询、作业提交、结果查看等操作，
无需直接调用 API 或使用命令行。

前提条件
--------------------

1. QCOS 服务已启动并正常运行
2. 已知 QCOS 服务地址（如 ``http://192.168.1.100:18400``）
3. 拥有 QCOS 账号（用户名和密码）
4. AI 助手支持 MCP 协议（如 Claude Desktop、支持 MCP 的 IDE 插件等）

MCP 端点地址
--------------------

MCP 服务与 QCOS JSON-RPC API 共享同一端口，端点地址为：

.. code-block:: text

   http://<qcos-host>:<port>/v1/ai/mcp

例如：

.. code-block:: text

   http://192.168.1.100:18400/v1/ai/mcp

配置 AI 助手
--------------------

Claude Desktop
~~~~~~~~~~~~~~~~~~~~

1. 打开 Claude Desktop 配置文件：

   - Windows: ``%APPDATA%\Claude\claude_desktop_config.json``
   - macOS: ``~/Library/Application Support/Claude/claude_desktop_config.json``
   - Linux: ``~/.config/Claude/claude_desktop_config.json``

2. 添加 MCP 服务器配置：

.. code-block:: json

   {
     "mcpServers": {
       "qcos": {
         "url": "http://192.168.1.100:18400/v1/ai/mcp",
         "transport": "streamable-http"
       }
     }
   }

3. 重启 Claude Desktop

Cherry Studio
~~~~~~~~~~~~~~~~~~~~

Cherry Studio 是一款支持 MCP 协议的国产 AI 客户端，界面友好，配置简单。

1. 打开 Cherry Studio，进入 **设置** → **MCP 服务器**

2. 点击 **添加服务器**，填写以下信息：

   - **名称**: ``qcos``
   - **类型**: 选择 ``Streamable HTTP``
   - **URL**: ``http://192.168.1.100:18400/v1/ai/mcp``

3. 保存并启用该服务器

OpenClaw（小龙虾）
~~~~~~~~~~~~~~~~~~~~

OpenClaw（中文社区常称"小龙虾"）是一款开源的桌面 AI 客户端，
原生支持 MCP 协议，可以便捷地接入各类 MCP 服务器。

1. 从 OpenClaw 官方仓库或发布页下载并安装客户端

2. 打开 OpenClaw，进入 **设置** 或 **MCP 服务器** 配置界面

3. 点击 **添加 MCP 服务器**，选择 ``HTTP`` 或 ``Streamable HTTP`` 类型

4. 填写服务器信息：

   - **名称**: ``qcos``
   - **URL**: ``http://192.168.1.100:18400/v1/ai/mcp``

5. 保存配置并启用，OpenClaw 会自动连接并加载可用的工具列表

Hermes Agent
~~~~~~~~~~~~~~~~~~~~

Hermes Agent 是另一款支持 MCP 协议的 AI 助手客户端，
提供图形化的服务器管理界面。

1. 打开 Hermes Agent，进入 **设置** 或 **MCP 配置** 页面

2. 点击 **添加服务器** 或 **新建 MCP 连接**

3. 填写服务器配置：

   - **名称**: ``qcos``
   - **传输方式**: 选择 ``Streamable HTTP``
   - **服务器地址**: ``http://192.168.1.100:18400/v1/ai/mcp``

4. 保存并连接，Hermes Agent 会自动发现 QCOS 提供的所有 MCP 工具

Cursor
~~~~~~~~~~~~~~~~~~~~

Cursor 编辑器内置 AI 助手，支持通过 MCP 协议接入外部工具。

1. 打开 Cursor 设置（``Ctrl + Shift + J`` 或 **File** → **Preferences** → **Cursor Settings**）

2. 进入 **MCP** 选项卡，点击 **Add new global MCP server**

3. 编辑生成的 ``mcp.json`` 配置文件：

   - Windows: ``%USERPROFILE%\.cursor\mcp.json``
   - macOS/Linux: ``~/.cursor/mcp.json``

4. 添加 QCOS 配置：

.. code-block:: json

   {
     "mcpServers": {
       "qcos": {
         "url": "http://192.168.1.100:18400/v1/ai/mcp",
         "transport": "streamable-http"
       }
     }
   }

5. 保存后返回 MCP 设置页，确认 ``qcos`` 服务已启用

Windsurf
~~~~~~~~~~~~~~~~~~~~

Windsurf 是 Codeium 推出的 AI 编辑器，同样支持 MCP 协议。

1. 打开 Windsurf 设置，进入 **Cascade** → **MCP Servers**

2. 点击 **Add Custom Server**，编辑 ``mcp_config.json``：

   - Windows: ``%USERPROFILE%\.codeium\windsurf\mcp_config.json``
   - macOS/Linux: ``~/.codeium/windsurf/mcp_config.json``

3. 添加 QCOS 配置：

.. code-block:: json

   {
     "mcpServers": {
       "qcos": {
         "url": "http://192.168.1.100:18400/v1/ai/mcp",
         "transport": "streamable-http"
       }
     }
   }

4. 保存后点击 **Refresh** 重新加载 MCP 服务器

Zoo Code（PyCharm / VSCode 插件）
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Zoo Code 是 JetBrains PyCharm / VSCode 中的 AI 编码助手插件，
通过 ``streamable-http`` 传输方式接入 MCP 服务器。

1. 在项目根目录创建（或编辑）``.roo/mcp.json`` 配置文件

2. 添加 QCOS 服务器配置：

.. code-block:: json

   {
     "mcpServers": {
       "qcos": {
         "type": "streamable-http",
         "url": "http://192.168.1.100:18400/v1/ai/mcp",
         "timeout": 30,
         "alwaysAllow": [
           "qcos_login",
           "qcos_get_version",
           "qcos_list_devices",
           "qcos_submit_job",
           "qcos_get_job_status",
           "qcos_get_job_result"
         ],
         "disabled": false
       }
     }
   }

3. 重启 IDE 或重新加载插件窗口，使配置生效

.. note::

   - ``alwaysAllow`` 列表中的工具调用时不再弹窗确认，
     可根据安全需要自行裁剪
   - 配置文件路径：项目根目录下 ``.roo/mcp.json``
   - 若服务地址变更，仅需修改 ``url`` 字段并重启插件

其他支持 MCP 的客户端
~~~~~~~~~~~~~~~~~~~~~

对于其他支持 MCP 协议的 IDE 插件或自定义客户端，通常需要提供以下信息：

- **Server URL**: ``http://<qcos-host>:<port>/v1/ai/mcp``
- **Transport**: ``streamable-http``（推荐）或 ``sse``

认证登录
--------------------

在使用 MCP 工具前，需要先通过 ``qcos_login`` 工具进行认证：

.. code-block:: text

   请帮我登录 QCOS 系统，用户名是 admin，密码是 xxxxxxxx

AI 助手会调用 ``qcos_login`` 工具，返回的 JWT Token 会自动存储在 MCP 会话中，
后续所有工具调用都会自动携带该 Token。

.. note::

   - Token 有效期由 QCOS 服务端配置决定（默认 24 小时）
   - 如果 Token 过期，需要重新调用 ``qcos_login``
   - 当 ``AUTH_MODE=no`` 时，无需登录即可使用

常用操作示例
--------------------

查看系统信息
~~~~~~~~~~~~~~~~~~~~

.. code-block:: text

   请查看 QCOS 系统版本和状态

AI 助手会调用：
- ``qcos_get_version``: 获取系统版本
- ``qcos_get_system_health``: 获取健康状态
- ``qcos_system_info``: 获取系统信息

查看设备列表
~~~~~~~~~~~~~~~~~~~~

.. code-block:: text

   请列出所有可用的量子设备

AI 助手会调用 ``qcos_list_devices``，返回设备名称、类型、比特数、状态等信息。

查看设备详情
~~~~~~~~~~~~~~~~~~~~

.. code-block:: text

   请查看 dummy 设备的详细信息

AI 助手会调用 ``qcos_get_device_detail(name="dummy")``。

提交量子作业
~~~~~~~~~~~~~~~~~~~~

.. code-block:: text

   请帮我提交一个量子作业，使用 dummy 设备，QASM 代码如下：
   OPENQASM 2.0;
   include "qelib1.inc";
   qreg q[2];
   creg c[2];
   h q[0];
   cx q[0], q[1];
   measure q -> c;

AI 助手会调用 ``qcos_submit_job``，参数包括：
- ``source_code``: QASM 代码列表
- ``backend``: 设备名称（如 ``dummy``）
- ``shots``: 测量次数（默认 1024）

查询作业状态
~~~~~~~~~~~~~~~~~~~~

.. code-block:: text

   请查看作业 job-12345 的状态

AI 助手会调用 ``qcos_get_job_status(job_id="job-12345")``。

获取作业结果
~~~~~~~~~~~~~~~~~~~~

.. code-block:: text

   请获取作业 job-12345 的执行结果

AI 助手会调用 ``qcos_get_job_result(job_id="job-12345")``，返回测量计数和概率分布。

列出我的作业
~~~~~~~~~~~~~~~~~~~~

.. code-block:: text

   请列出我提交的所有作业

AI 助手会调用 ``qcos_list_jobs``，可以添加过滤条件：

.. code-block:: text

   请列出状态为 running 的作业

AI 助手会调用 ``qcos_list_jobs(job_status="running")``。

管理资源规格（Flavor）
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: text

   请列出所有资源规格

AI 助手会调用 ``qcos_get_flavors``。

.. code-block:: text

   请创建一个名为 "high-fidelity" 的资源规格，要求最小 1 比特，最大 10 比特，
   单比特门保真度不低于 0.99

AI 助手会调用 ``qcos_create_flavor``，并自动关联设备分组。

系统监控
~~~~~~~~~~~~~~~~~~~~

.. code-block:: text

   请查看系统 API 统计和作业统计

AI 助手会调用：
- ``qcos_get_api_stats``: API 请求统计
- ``qcos_get_job_stats``: 作业统计（按状态分组）

工具分类速查
--------------------

设备管理
~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - 工具
     - 说明
   * - ``qcos_list_devices``
     - 列出所有设备
   * - ``qcos_get_device_detail``
     - 查看设备详情
   * - ``qcos_set_device``
     - 设置设备状态/启用/比特数
   * - ``qcos_calibrate_device``
     - 触发设备校准
   * - ``qcos_get_calibrate_results``
     - 查看校准结果
   * - ``qcos_set_device_options``
     - 设置设备选项
   * - ``qcos_get_device_options``
     - 查看设备选项

作业管理
~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - 工具
     - 说明
   * - ``qcos_submit_job``
     - 提交量子作业
   * - ``qcos_list_jobs``
     - 列出作业（支持过滤）
   * - ``qcos_get_job_status``
     - 查看作业状态
   * - ``qcos_get_job_result``
     - 获取作业结果
   * - ``qcos_cancel_jobs``
     - 取消作业
   * - ``qcos_delete_jobs``
     - 删除作业
   * - ``qcos_update_job``
     - 更新作业属性

资源规格与分组
~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - 工具
     - 说明
   * - ``qcos_create_flavor``
     - 创建 Flavor
   * - ``qcos_update_flavor``
     - 更新 Flavor
   * - ``qcos_get_flavor``
     - 查看 Flavor 详情
   * - ``qcos_get_flavors``
     - 列出 Flavor
   * - ``qcos_delete_flavors``
     - 删除 Flavor
   * - ``qcos_create_device_group``
     - 创建设备分组
   * - ``qcos_update_device_group``
     - 更新设备分组
   * - ``qcos_get_device_group``
     - 查看分组详情
   * - ``qcos_get_device_groups``
     - 列出设备分组
   * - ``qcos_delete_device_groups``
     - 删除设备分组

驱动与转译器
~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - 工具
     - 说明
   * - ``qcos_get_drivers``
     - 列出所有驱动
   * - ``qcos_get_driver``
     - 查看驱动详情
   * - ``qcos_get_transpilers``
     - 列出所有转译器
   * - ``qcos_get_transpiler``
     - 查看转译器详情

项目管理
~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - 工具
     - 说明
   * - ``qcos_create_project``
     - 创建项目
   * - ``qcos_get_project``
     - 查看项目详情
   * - ``qcos_get_projects``
     - 列出项目
   * - ``qcos_update_project``
     - 更新项目
   * - ``qcos_delete_project``
     - 删除项目

用户与权限（管理员）
~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - 工具
     - 说明
   * - ``qcos_login``
     - 用户登录
   * - ``qcos_get_current_user``
     - 查看当前用户
   * - ``qcos_create_user``
     - 创建用户
   * - ``qcos_get_user``
     - 查看用户详情
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
     - 查看角色详情
   * - ``qcos_get_roles``
     - 列出角色
   * - ``qcos_update_role``
     - 更新角色
   * - ``qcos_delete_role``
     - 删除角色
   * - ``qcos_get_user_mgmt``
     - 查看用户管理配置
   * - ``qcos_set_user_mgmt``
     - 设置认证模式
   * - ``qcos_get_login_logs``
     - 查看登录日志
   * - ``qcos_clear_login_logs``
     - 清除登录日志

系统监控
~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - 工具
     - 说明
   * - ``qcos_get_system_health``
     - 系统健康状态
   * - ``qcos_get_api_stats``
     - API 请求统计
   * - ``qcos_get_job_stats``
     - 作业统计
   * - ``qcos_ping``
     - 连通性检查
   * - ``qcos_system_info``
     - 系统信息
   * - ``qcos_show_mem``
     - 内存使用情况
   * - ``qcos_gc_mem``
     - 触发垃圾回收
   * - ``qcos_list_workers``
     - 列出 Worker
   * - ``qcos_restart_worker``
     - 重启 Worker

MCP 资源
--------------------

MCP 资源是只读的数据端点，AI 助手可以直接读取：

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - 资源 URI
     - 内容
   * - ``qcos://version``
     - 系统版本信息
   * - ``qcos://devices``
     - 设备摘要信息

常见问题
--------------------

连接失败
~~~~~~~~~~~~~~~~~~~~

**问题**: AI 助手无法连接到 MCP 端点

**排查步骤**:

1. 确认 QCOS 服务正在运行：

   .. code-block:: bash

      curl http://<qcos-host>:<port>/v1/version

2. 检查 MCP 端点是否可访问：

   .. code-block:: bash

      curl -X POST http://<qcos-host>:<port>/v1/ai/mcp \
        -H "Content-Type: application/json" \
        -d '{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}'

3. 检查防火墙设置，确保端口可达

Session not found（会话未找到）
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**问题**: 工具调用返回 ``-32600 Session not found`` 或
``Bad Request: Missing session ID`` 错误

**原因**:

MCP Streamable HTTP 协议要求客户端先调用 ``initialize``，
服务端在响应头中返回 ``mcp-session-id``，后续所有请求必须在
HTTP 头 ``Mcp-Session-Id`` 中携带该值。若客户端未正确缓存或
回传该 ID，即会出现此错误。

**排查步骤**:

1. 手动验证服务端是否能正确下发 Session ID：

   .. code-block:: bash

      curl -i -X POST http://<qcos-host>:<port>/v1/ai/mcp \
        -H "Content-Type: application/json" \
        -d '{"jsonrpc":"2.0","id":1,"method":"initialize",
             "params":{"protocolVersion":"2024-11-05",
             "capabilities":{},
             "clientInfo":{"name":"debug","version":"1.0"}}}'

   正常响应应包含响应头：

   .. code-block:: text

      mcp-session-id: 9fe3290f7e7e44308056ea0a297f5c35

2. 使用获取到的 Session ID 调用工具，验证服务端链路正常：

   .. code-block:: bash

      curl -X POST http://<qcos-host>:<port>/v1/ai/mcp \
        -H "Content-Type: application/json" \
        -H "Mcp-Session-Id: <上一步获取的id>" \
        -d '{"jsonrpc":"2.0","id":2,"method":"tools/call",
             "params":{"name":"qcos_get_version","arguments":{}}}'

3. 若上述两步均成功，但 AI 助手仍报错，则问题在客户端实现：

   - 确认 IDE / 插件版本为最新
   - 重启 IDE 让客户端重新执行 ``initialize`` 握手
   - 检查客户端日志中是否正确发送了 ``Mcp-Session-Id`` 请求头
   - 联系客户端厂商反馈 Bug

.. note::

   该问题与 QCOS 服务端配置（如 ``mcp.json``、``qcos.toml``）无关，
   通常是 MCP 客户端对 Streamable HTTP 会话管理的实现缺陷。

认证失败
~~~~~~~~~~~~~~~~~~~~

**问题**: 工具调用返回 401 错误

**解决方案**:

1. 确认已调用 ``qcos_login`` 并成功获取 Token
2. 检查 Token 是否过期，重新登录
3. 确认 QCOS 的 ``AUTH_MODE`` 配置：
   - ``jwt``: 需要有效 Token
   - ``no``: 无需认证
   - ``virtual_instance``: 虚拟实例模式

工具调用超时
~~~~~~~~~~~~~~~~~~~~

**问题**: 某些工具调用（如 ``qcos_submit_job``）超时

**解决方案**:

1. 检查 QCOS 服务负载
2. 确认目标设备在线且可用
3. 增加客户端超时时间（如果支持）

版本兼容性
~~~~~~~~~~~~~~~~~~~~

**问题**: MCP 客户端与服务器版本不兼容

**解决方案**:

QCOS 同时支持 MCP 1.x 和 2.x 协议，客户端会自动协商版本。
如果遇到兼容性问题，请尝试更新 MCP 客户端到最新版本。
