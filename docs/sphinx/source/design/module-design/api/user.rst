用户管理接口
================

用户管理接口用于用户管理、角色和权限管理等等。

.. list-table:: 用户管理接口规范
   :widths: 20 20 30 30
   :header-rows: 1
   :align: left
   :class: longtable

   * - 用途
     - 方法
     - 请求参数
     - 返回值

   * - **获取用户管理状态**
     - **get_user_mgmt_status**

       URI: /v1/user/get_user_mgmt_status
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "id": 1,
               "method": "get_user_mgmt_status",
               "params": {
                 "body": null
               }
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "result": {
                 "enabled": true,
                 "password_expiry_days": 90,
                 "max_login_attempts": 5,
                 "lockout_duration_minutes": 30
               },
               // 有错误时会出现, 具体格式参照<错误返回>
               "error": {}
               "id": 1
             }

   * - **创建用户**
     - **create_user**

       URI: /v1/user/create_user
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "id": 1,
               "method": "create_user",
               "params": {
                 "body": {
                   "user_name": "string",
                   "password": "string",
                   "roles": ["user"],
                   "description": "string"
                 }
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

   * - **获取用户详情**
     - **get_user**

       URI: /v1/user/get_user
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "id": 1,
               "method": "get_user",
               "params": {
                 "body": {
                   "user_id": "1"
                 }
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

   * - **获取用户列表**
     - **get_users**

       URI: /v1/user/get_users
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "id": 1,
               "method": "get_users",
               "params": {
                 "body": null
               }
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "result": {
                 "user1": {
                   "id": 1,
                   "user_name": "user1",
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
                 "user2": {
                   "id": 2,
                   "user_name": "user2",
                   "roles": ["admin"],
                   "is_enabled": true,
                   "is_locked": false,
                   "last_login": "2026-04-08T16:39:15",
                   "password_expiry_days": 90,
                   "password_changed_at": "2026-04-08T16:39:15",
                   "locked_until": null,
                   "description": "string",
                   "created_at": "2026-04-08T16:39:15",
                   "updated_at": "2026-04-08T16:39:15"
                 }
               },
               // 有错误时会出现, 具体格式参照<错误返回>
               "error": {}
               "id": 1
             }

   * - **更新用户信息**
     - **update_user**

       URI: /v1/user/update_user
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "id": 1,
               "method": "update_user",
               "params": {
                 "body": {
                   "user_id": "1",
                   "roles": ["admin"],
                   "is_enabled": true,
                   "is_locked": false,
                   "password_expiry_days": 90,
                   "description": "string"
                 }
               }
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "result": {
                 "id": 1,
                 "user_name": "string",
                 "roles": ["admin"],
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

   * - **删除用户**
     - **delete_user**

       URI: /v1/user/delete_user
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "id": 1,
               "method": "delete_user",
               "params": {
                 "body": {
                   "user_id": "1"
                 }
               }
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "result": {
                 "user_name": "string",
                 "deleted_at": "2026-04-08T16:39:15"
               },
               // 有错误时会出现, 具体格式参照<错误返回>
               "error": {}
               "id": 1
             }


   * - **创建角色**
     - **create_role**

       URI: /v1/user/create_role
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "id": 1,
               "method": "create_role",
               "params": {
                 "body": {
                   "role_name": "string",
                   "permissions": ["/v1/device/get_device"],
                   "description": "string"
                 }
               }
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "result": {
                 "id": "string",
                 "role_name": "string",
                 "permissions": ["/v1/device/get_device"],
                 "description": "string"
               },
               // 有错误时会出现, 具体格式参照<错误返回>
               "error": {}
               "id": 1
             }

   * - **获取角色详情**
     - **get_role**

       URI: /v1/user/get_role
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "id": 1,
               "method": "get_role",
               "params": {
                 "body": {
                   "role_id": "string"
                 }
               }
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "result": {
                 "id": "string",
                 "role_name": "string",
                 "permissions": ["/v1/device/get_device"],
                 "description": "string"
               },
               // 有错误时会出现, 具体格式参照<错误返回>
               "error": {}
               "id": 1
             }

   * - **获取角色列表**
     - **get_roles**

       URI: /v1/user/get_roles
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "id": 1,
               "method": "get_roles",
               "params": {
                 "body": null
               }
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "result": {
                 "admin": {
                   "id": "string",
                   "role_name": "admin",
                   "permissions": ["/v1/device/get_device"],
                   "description": "Administrator role"
                 },
                 "user": {
                   "id": "string",
                   "role_name": "user",
                   "permissions": ["/v1/device/get_device"],
                   "description": "User role"
                 }
               },
               // 有错误时会出现, 具体格式参照<错误返回>
               "error": {}
               "id": 1
             }

   * - **更新角色信息**
     - **update_role**

       URI: /v1/user/update_role
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "id": 1,
               "method": "update_role",
               "params": {
                 "body": {
                   "role_id": "string",
                   "permissions": ["/v1/device/get_device"],
                   "description": "Updated role"
                 }
               }
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "result": {
                 "role_name": "string",
                 "permissions": ["/v1/device/get_device"],
                 "description": "Updated role"
               },
               // 有错误时会出现, 具体格式参照<错误返回>
               "error": {}
               "id": 1
             }

   * - **删除角色**
     - **delete_role**

       URI: /v1/user/delete_role
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "id": 1,
               "method": "delete_role",
               "params": {
                 "body": {
                   "role_id": "string"
                 }
               }
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "result": {
                 "role_name": "string",
                 "deleted_at": "2026-04-08T16:39:15"
               },
               // 有错误时会出现, 具体格式参照<错误返回>
               "error": {}
               "id": 1
             }

   * - **锁定/解锁用户**
     - **lock_user**

       URI: /v1/user/lock_user
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "id": 1,
               "method": "lock_user",
               "params": {
                 "body": {
                   "user_name": "string",
                   "action": "lock"
                 }
               }
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "result": {
                 "user_name": "string",
                 "is_locked": true,
                 "locked_until": "2026-04-08T16:39:15",
                 "message": "User 'string' has been locked"
               },
               // 有错误时会出现, 具体格式参照<错误返回>
               "error": {}
               "id": 1
             }

   * - **修改用户密码**
     - **change_password**

       URI: /v1/user/change_password
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "id": 1,
               "method": "change_password",
               "params": {
                 "body": {
                   "user_id": "1",
                   "old_password": "string",
                   "new_password": "string"
                 }
               }
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "result": {
                 "user_name": "string",
                 "password_changed_at": "2026-04-08T16:39:15",
                 "message": "Password changed successfully"
               },
               // 有错误时会出现, 具体格式参照<错误返回>
               "error": {}
               "id": 1
             }

   * - **获取登录日志**
     - **get_login_logs**

       URI: /v1/user/get_login_logs
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "id": 1,
               "method": "get_login_logs",
               "params": {
                 "body": {
                   "user_id": "string",
                   "start_time": "2026-04-01T00:00:00",
                   "end_time": "2026-04-08T23:59:59",
                   "limit": 100,
                   "offset": 0
                 }
               }
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "result": [
                 {
                   "user_name": "string",
                   "login_time": "2026-04-08T16:39:15",
                   "ip_address": "192.168.1.1",
                   "user_agent": "Mozilla/5.0...",
                   "success": true,
                   "failure_reason": null
                 }
               ],
               // 有错误时会出现, 具体格式参照<错误返回>
               "error": {}
               "id": 1
             }
