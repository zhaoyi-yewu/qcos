QCOS WebUI 配置与启动
=====================

本文档介绍 QCOS WebUI 的配置文件格式、启动方法以及使用注意点。
WebUI 采用 **配置文件驱动** 的方式管理 QCOS API endpoint，支持多 endpoint 配置与免登录切换。

.. contents:: 目录
   :local:
   :depth: 3

前提条件
--------

保证操作系统已安装 ``docker``、``docker-compose`` 组件：

.. code-block:: shell

   # BCLinux/CentOS/OpenEuler 环境下示例:
   yum install -y docker docker-compose

编译 WebUI 容器镜像
-------------------

.. code-block:: shell

   cd build-scripts
   cp ./env.template .env
   vim .env
   ./build-images.sh -w

关键环境变量：

- ``DEV=false`` （生产模式）或 ``DEV=true`` （开发模式）
- ``QCOS_WEBUI_LISTEN_IP`` / ``QCOS_WEBUI_LISTEN_PORT`` （可选，默认 ``0.0.0.0:18401``）
- 内网环境按需配置 ``NPM_MIRROR`` / ``NODE_BIN_MIRROR``

配置文件 ``/etc/qcos/qcos-webui.toml``
--------------------------------------

WebUI 的配置文件采用 TOML 格式，与 QCOS API 的 ``qcos.toml`` 风格一致。
容器启动时由 ``parse-webui-toml.py`` 解析并生成 nginx 反向代理、前端运行时 JSON。

创建/修改配置文件
~~~~~~~~~~~~~~~~~

.. code-block:: shell

   sudo mkdir -p /etc/qcos
   sudo vim /etc/qcos/qcos-webui.toml

最小可用配置
~~~~~~~~~~~~

.. code-block:: toml

   [DEFAULT]
   DEBUG = false
   LISTEN_IP   = "0.0.0.0"
   LISTEN_PORT = 18401
   DEFAULT_ENDPOINT = "local"

   QCOS_API_ENDPOINTS = [
     { name = "local", alias = "本地开发环境", url = "http://127.0.0.1:18400" }
   ]

完整配置示例
~~~~~~~~~~~~

.. code-block:: toml

   # ----------------------------------------------------------------------
   # QCOS WebUI configuration
   #   - Loaded once by the webui container at startup (production), or by
   #     the vite dev server (development)
   #   - Format mirrors etc/qcos/qcos.toml
   # ----------------------------------------------------------------------

   [DEFAULT]
   # Global debug switch; when true the frontend enables verbose console logs
   DEBUG = true

   # IP / port the WebUI nginx (production) or vite dev server (development)
   # listens on
   LISTEN_IP   = "0.0.0.0"
   LISTEN_PORT = 18401

   # Optional default endpoint name; when set and matches one of the entries
   # in QCOS_API_ENDPOINTS, the login page pre-selects it
   DEFAULT_ENDPOINT = "local"

   # Endpoint health check timeout in milliseconds; the /version probe is
   # aborted when no response is received within this window
   ENDPOINT_PROBE_TIMEOUT_MS = 3000

   # QCOS API endpoints visible to the user.
   # Each entry is a TOML inline table:
   #   name    - required; unique endpoint identifier (lowercase letters,
   #             digits, dash, underscore), stored in browser localStorage
   #   alias   - optional; human readable label; falls back to `name`
   #   url     - required; base URL of the QCOS API server (http:// or https://)
   #   use_ssl - optional; when true, nginx verifies the upstream TLS
   #             certificate; when false or omitted, inferred from url scheme
   #   cacert  - optional; absolute path \*inside the webui container\* of the
   #             CA certificate used to verify a self-signed https endpoint;
   #             ignored for http:// endpoints
   #
   # Example (multiple endpoints, https with custom CA):
   # QCOS_API_ENDPOINTS = [
   #   { name = "local",      alias = "本地开发环境", url = "http://127.0.0.1:18400" },
   #   { name = "production", alias = "生产环境",     url = "https://127.0.0.1:18400", use_ssl = true, cacert = "/etc/qcos/ssl/cacert.pem" },
   # ]
   QCOS_API_ENDPOINTS = [
     { name = "local", alias = "本地开发环境", url = "http://127.0.0.1:18400" }
   ]

字段说明
~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 25 15 15 45

   * - 字段
     - 类型
     - 必填
     - 说明
   * - ``DEBUG``
     - bool
     - 否
     - 前端调试开关，true 时控制台输出详细日志
   * - ``LISTEN_IP``
     - string
     - 否
     - nginx/vite 监听地址，默认 ``0.0.0.0``
   * - ``LISTEN_PORT``
     - int
     - 否
     - nginx/vite 监听端口，默认 ``18401``
   * - ``DEFAULT_ENDPOINT``
     - string
     - 否
     - 默认选中的 endpoint ``name``，缺省取第一个
   * - ``ENDPOINT_PROBE_TIMEOUT_MS``
     - int
     - 否
     - ``/version`` 健康探测超时（毫秒），默认 ``3000``
   * - ``QCOS_API_ENDPOINTS``
     - array
     - 是
     - endpoint 列表，至少一条

Endpoint 字段
~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 20 15 15 50

   * - 字段
     - 类型
     - 必填
     - 说明
   * - ``name``
     - string
     - 是
     - 唯一标识，仅允许 ``a-z 0-9 _ -``，写入浏览器 localStorage
   * - ``alias``
     - string
     - 否
     - 显示名，缺省用 ``name``
   * - ``url``
     - string
     - 是
     - QCOS API 完整地址，支持 ``http://`` 或 ``https://``
   * - ``use_ssl``
     - bool
     - 否
     - 显式要求 SSL/TLS 连接；``true`` 时 ``url`` 必须是 ``https://``
   * - ``cacert``
     - string
     - 否
     - 自签名 https 的 CA 证书在容器内的绝对路径，仅 ``use_ssl=true`` 时有效

配置加载流程
~~~~~~~~~~~~

.. code-block:: text

   /etc/qcos/qcos-webui.toml
        |
        v
   parse-webui-toml.py
        |
        +---> /tmp/webui.env (LISTEN_IP, LISTEN_PORT, DEBUG)
        +---> /apps/webui-config.json (endpoints, debug, timeout)
        +---> /etc/nginx/default.d/endpoints.conf (location /api/<name>/)

运行容器（基于 Docker）
-----------------------

.. code-block:: shell

   cd build-scripts
   ./run-docker-webui.sh

访问：``http://{QCOS_WEBUI_IP}:18401``

.. note::

   容器通过 volume 挂载 ``/etc/qcos:/etc/qcos``，因此 ``qcos-webui.toml`` 与
   ``cacert`` 证书文件都要放在宿主机的 ``/etc/qcos/`` 下
   （推荐 ``/etc/qcos/qcos-webui.toml``、``/etc/qcos/ssl/*.pem``），容器内即可读到。

调试模式（vite dev server）
---------------------------

.. code-block:: shell

   cd webui
   npm install
   # 可选：覆盖默认读取的 toml 路径（默认 ../etc/qcos/qcos-webui.toml）
   export WEBUI_TOML=/etc/qcos/qcos-webui.toml
   npm run dev

调试模式下：

- ``/webui-config.json`` 由 vite middleware 实时从 toml 生成，改完 toml 重启 dev server 即可
- 每个 endpoint 的 ``/api/<name>/`` 由 vite 代理到真实 QCOS API，
  https endpoint 的 ``cacert`` 通过 ``https.Agent({ ca })`` 在校验层生效

多 Endpoint 与 HTTPS
--------------------

多 Endpoint 工作原理
~~~~~~~~~~~~~~~~~~~~

1. 配置多个 endpoint 后，登录页与侧边栏会显示 endpoint 下拉框
2. 用户名 + token 按 ``endpoint.name`` 分别保存在浏览器 localStorage
3. 切换 endpoint 时：

   - 已认证 → 直接刷新页面使用新 endpoint 的 token，**免登录**
   - 未认证 → 自动跳转登录页，登录成功后再切换

4. 每个 endpoint 在 nginx 中有独立的 ``location /api/<name>/`` 反向代理

HTTPS endpoint 与 cacert
~~~~~~~~~~~~~~~~~~~~~~~~

由于浏览器的证书校验无法被 JS 控制，WebUI 采用 **nginx 反向代理 + 服务端证书校验** 方案：

.. code-block:: text

   浏览器 ──http(s)──▶ webui nginx ──https──▶ QCOS API (自签名)
                                          ▲
                                 nginx 用 cacert 校验

- 前端始终访问同源 ``/api/<name>/``，无需在浏览器安装 CA
- nginx 在 ``location /api/<name>/`` 内通过 ``proxy_ssl_trusted_certificate`` 校验上游证书
- **每个 endpoint 的 cacert 完全独立**，互不影响

cacert 文件准备：

.. code-block:: shell

   sudo mkdir -p /etc/qcos/ssl
   sudo cp production-cacert.pem /etc/qcos/ssl/
   sudo chmod 644 /etc/qcos/ssl/production-cacert.pem

如果上游用的是完整证书链（中间 CA + 根 CA），cacert 文件需要包含完整链：

.. code-block:: shell

   cat intermediate.pem root.pem | sudo tee /etc/qcos/ssl/cacert.pem

不可用 endpoint 处理
~~~~~~~~~~~~~~~~~~~~

登录页与侧边栏下拉框会对每个 endpoint 调用 ``/version`` 接口探测：

- **探测中**：显示 Loading 图标 + "探测中…"
- **可用**：显示版本号（如 ``v1.8.0``）+ 绿色"可用"
- **不可用**：显示红色"不可用"，鼠标悬停可查看错误原因，**该项禁用选择**

探测超时由 ``ENDPOINT_PROBE_TIMEOUT_MS`` 控制（默认 3000ms），30 秒内不重复探测以避免抖动。

注意事项
--------

1. **Token 隔离**：A endpoint 的 token 永远不会发到 B endpoint，
   base URL 与 ``Authorization`` 头都从同一个 ``activeEndpointName`` 派生。

2. **修改配置后需重启容器**：``qcos-webui.toml`` 仅在容器启动时解析一次。

3. **cacert 路径校验**：必须位于 ``/etc/qcos/ssl/`` 下且可读，否则容器启动报错。

4. **多 tab 共享**：localStorage 共享，tab A 在某 endpoint 登录后，
   tab B 切到同 endpoint 直接复用 token。

5. **退出登录仅清当前 endpoint**：其它 endpoint 的 token 保留；
   如需全部清除，在浏览器开发者工具中删除 localStorage 的 ``qcos_tokens``
   和 Cookie 的 ``qcos_active_endpoint``。

6. **安全建议**：生产环境建议为每个 https endpoint 配置独立的 ``cacert``，
   并启用 ``use_ssl = true`` 显式要求 SSL 连接。

常见问题
--------

Q1：启动后访问 404 或白屏
~~~~~~~~~~~~~~~~~~~~~~~~~

检查容器日志：

.. code-block:: shell

   docker logs qcos-webui

常见原因：

- ``/etc/qcos/qcos-webui.toml`` 缺失或 TOML 语法错误 → 看 ``parse-webui-toml.py`` 报错
- ``cacert`` 路径不存在或权限不足 → 同上
- nginx 配置生成失败 → 看 entrypoint 输出

Q2：登录后接口报 401
~~~~~~~~~~~~~~~~~~~~

- 该 endpoint 的 token 已过期：退出登录后重新登录
- 多个 endpoint 之间 token 不共享，切回旧 endpoint 后需要重新登录

Q3：HTTPS endpoint 提示"不可用"
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- 检查 ``cacert`` 路径在容器内是否可读：
  ``docker exec qcos-webui ls -l /etc/qcos/ssl/``
- 检查上游 QCOS API 证书是否由该 CA 签发
- 如果是完整证书链，确认 cacert 文件包含中间 CA + 根 CA

Q4：修改 qcos-webui.toml 后没生效
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

配置文件仅在容器启动时解析一次。修改后需要重启容器：

.. code-block:: shell

   cd build-scripts
   ./run-docker-webui.sh  # 内部会先 down 再 up -d

Q5：忘记所有 endpoint 的登录态
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

在浏览器开发者工具中清除：

- Cookie：``qcos_active_endpoint``
- localStorage：``qcos_tokens``

相关文档
--------

- :doc:`index` - QCOS 部署手册
- :doc:`build-run-docker` - 编译、安装和运行（推荐，基于 Docker 容器）
- :doc:`edit-env` - 编辑 .env 配置文件
- :doc:`security` - 安全说明
- :doc:`network-ports` - 网络端口说明
