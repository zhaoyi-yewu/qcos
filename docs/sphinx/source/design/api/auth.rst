认证接口
================

认证接口用于用户认证。

.. list-table:: 认证接口规范
   :widths: 20 20 30 30
   :header-rows: 1
   :align: left
   :class: longtable

   * - 用途
     - 方法
     - 请求参数
     - 返回值

   * - **用户登录**
     - **login**

       URI: /v1/auth/login
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "id": 1,
               "method": "login",
               "params": {
                 "body": {
                   "username": "string",
                   "password": "P*ssword1"
                 }
               }
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "result": {
                 "access_token": "string",
                 "refresh_token": "string",
                 "token_type": "bearer",
                 "expires_in": 900,
                 "refresh_expires_in": 604800
               },
               "error": null,
               "id": 1
             }

   * - **用户登出**
     - **logout**

       URI: /v1/auth/logout
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "id": 1,
               "method": "logout",
               "params": {
                 "body": null
               }
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "result": {
                 "message": "Successfully logged out"
               },
               "error": null,
               "id": 1
             }

   * - **刷新令牌**
     - **refresh_token**

       URI: /v1/auth/refresh_token
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "id": 1,
               "method": "refresh_token",
               "params": {
                 "body": {
                   "refresh_token": "string"
                 }
               }
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "result": {
                 "access_token": "string",
                 "refresh_token": "string",
                 "token_type": "bearer",
                 "expires_in": 900,
                 "refresh_expires_in": 604800
               },
               "error": null,
               "id": 1
             }

   * - **获取当前用户信息**
     - **me**

       URI: /v1/auth/me
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "id": 1,
               "method": "me",
               "params": {
                 "body": null
               }
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "result": {
                 "id": "uuid",
                 "user_name": "string",
                 "roles": ["user"],
                 "is_enabled": true,
                 "is_locked": false,
                 "last_login": "2026-04-08T16:39:15",
                 "password_expiry_days": 90,
                 "password_changed_at": "2026-04-08T16:39:15",
                 "locked_until": null,
                 "description": "string",
                 "created_at": "2026-04-08T16:39:15",
                 "updated_at": "2026-04-08T16:39:15"
               },
               "error": null,
               "id": 1
             }

认证令牌详解
~~~~~~~~~~~~

访问令牌 (Access Token)
^^^^^^^^^^^^^^^^^^^^^^^

访问令牌用于API请求认证，生命周期较短：

- 类型：JWT(JSON Web Token)
- 过期时间：900秒（15分钟）
- 使用方式：在HTTP Header的 ``Authorization`` 中携带
- 格式：``Authorization: Bearer <access_token>``

刷新令牌 (Refresh Token)
^^^^^^^^^^^^^^^^^^^^^^^^

刷新令牌用于获取新的访问令牌，生命周期较长：

- 类型：JWT(JSON Web Token)
- 过期时间：604800秒（7天）
- 使用场景：当访问令牌即将过期或已过期时
- 不能直接用于API认证，仅用于刷新操作

用户信息字段说明
^^^^^^^^^^^^^^^^

登录或创建用户后会返回用户详情，具体字段含义：

- **id** (uuid) - 用户全局唯一标识
- **user_name** (string) - 用户名，用于登录
- **roles** (array) - 用户角色列表，控制权限
- **is_enabled** (boolean) - 用户是否启用，禁用状态无法登录
- **is_locked** (boolean) - 用户是否被锁定，通常由登录失败触发
- **last_login** (datetime) - 最后登录时间
- **password_expiry_days** (int) - 密码过期天数，超过后需要重置密码
- **password_changed_at** (datetime) - 最后修改密码的时间
- **locked_until** (datetime or null) - 账户锁定截止时间，null表示未设置
- **description** (string) - 用户描述信息
- **created_at** (datetime) - 用户创建时间
- **updated_at** (datetime) - 用户最后更新时间

最佳实践建议
^^^^^^^^^^^^^^^^

1. **认证流程**

   .. code-block:: text

      a) 调用 login 接口进行用户认证
      b) 获取 access_token 和 refresh_token
      c) 使用 access_token 调用其他API
      d) 当 access_token 即将过期时，调用 refresh_token 刷新
      e) 用户登出时调用 logout 接口清理会话

2. **令牌刷新策略**

   .. code-block:: python

      # 推荐：在 access_token 剩余时间少于5分钟时主动刷新
      if remaining_time < 300:  # 5分钟
          new_tokens = refresh_token(refresh_token)
          access_token = new_tokens['access_token']

3. **错误处理**

   .. code-block:: text

      错误码含义：
      • -401: 未登录或token已过期，需要重新登录
      • -403: 权限不足，当前用户无权访问该资源
      • -409: 用户已被锁定或禁用，联系管理员
      • -500: 服务器错误，请稍后重试

4. **安全建议**

   .. code-block:: text

      • 定期调用 me 验证用户身份
      • 密码过期前主动修改，避免无法登录
      • 发现异常登录记录时立即修改密码
      • 不要在代码中硬编码用户凭证
      • 使用HTTPS加密所有认证请求
