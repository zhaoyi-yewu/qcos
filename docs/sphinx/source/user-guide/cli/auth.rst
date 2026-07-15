认证命令
----------------------

认证相关命令包含用户登录登出、Token刷新及查询当前用户等操作。

.. note::

   **通用说明**

   - 某些用户和角色相关命令支持双参数模式：可接受 UUID 或名称
   - 例如：``qcos-cli get-user test`` (按名称查询) 或 ``qcos-cli get-user 00000000-0000-4000-8000-000000000001`` (按UUID查询)
   - 系统会自动识别参数类型并执行相关查询

登录
***************

用户登录获取访问令牌

命令行参数
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 用户登录
   usage: qcos-cli login [-h] [--access-token] [--refresh-token]
                         username password

   User login to get JWT token.

   positional arguments:
     username              Username
     password              Password

   options:
     -h, --help            show this help message and exit
     --access-token        Only print the access token
     --refresh-token       Only print the refresh token

典型场景示例
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 标准登录（显示完整信息）
   qcos-cli login admin 123456

   # 保存access token到环境变量中, 供后续命令认真时使用
   export QCOS_ACCESS_TOKEN=`qcos-cli login admin 123456 --access-token`

   # 只显示访问令牌
   qcos-cli login admin 123456 --access-token

   # 只显示刷新令牌
   qcos-cli login admin 123456 --refresh-token


登出
***************

用户登出清除令牌

命令行参数
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 用户登出
   usage: qcos-cli logout [-h]

   User logout.

   options:
     -h, --help  show this help message and exit

典型场景示例
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 登出
   qcos-cli logout


刷新令牌
***************

刷新JWT访问令牌

命令行参数
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 刷新令牌
   usage: qcos-cli refresh-token [-h] [--refresh-token REFRESH_TOKEN]

   Refresh JWT token.

   options:
     -h, --help                show this help message and exit
     --refresh-token REFRESH_TOKEN
                               Specify refresh_token directly
                               (overrides QCOS_REFRESH_TOKEN environment variable)

典型场景示例
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 使用环境变量中的刷新令牌 (refresh token可在login登陆时获取)
   export QCOS_REFRESH_TOKEN=your_refresh_token
   qcos-cli refresh-token

   # 直接指定刷新令牌
   qcos-cli refresh-token --refresh-token eyJ0eXAiOiJKV1QiLCJhbGc...


查询当前用户
***************

显示当前已认证用户的信息

命令行参数
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 查询当前用户
   usage: qcos-cli whoami [-h] [-f {json,shell,table,value,yaml}]
                          [-c COLUMN] [--noindent] [--prefix PREFIX]
                          [--max-width <integer>] [--fit-width]
                          [--print-empty]

   Show current authenticated user information.

   options:
     -h, --help            show this help message and exit

典型场景示例
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 查询当前认证用户
   qcos-cli whoami


