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
                   "password": "string"
                 }
               }
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "result": {
                 "access_token": "string",
                 "token_type": "bearer",
                 "expires_in": 3600
               },
               // 有错误时会出现, 具体格式参照<错误返回>
               "error": {}
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
               // 有错误时会出现, 具体格式参照<错误返回>
               "error": {}
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
                 "body": null
               }
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "result": {
                 "access_token": "string",
                 "token_type": "bearer",
                 "expires_in": 3600
               },
               // 有错误时会出现, 具体格式参照<错误返回>
               "error": {}
               "id": 1
             }

   * - **获取当前用户信息**
     - **get_current_user_info**

       URI: /v1/auth/get_current_user_info
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "id": 1,
               "method": "get_current_user_info",
               "params": {
                 "body": null
               }
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "result": {
                 "id": 1,
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
               // 有错误时会出现, 具体格式参照<错误返回>
               "error": {}
               "id": 1
             }
