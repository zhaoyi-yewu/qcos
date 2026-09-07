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
     - **get_user_mgmt**

       URI: /v1/user/get_user_mgmt
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "id": 1,
               "method": "get_user_mgmt",
               "params": {
                 "body": null
               }
             }
     - .. container:: table-code-small-font

          .. code-block:: json

              {
                "jsonrpc": "2.0",
                "result": {
                  "auth_mode": "jwt",
                  "password_expiry_days": 90,
                  "max_login_attempts": 5,
                  "lockout_duration_minutes": 30
                },
                "error": null,
                "id": 1
              }

   * - **设置用户管理模式**
     - **set_user_mgmt**

       URI: /v1/user/set_user_mgmt
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "id": 1,
               "method": "set_user_mgmt",
               "params": {
                 "body": {
                   "auth_mode": "jwt"
                 }
               }
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "result": {
                 "auth_mode": "jwt",
                 "message": "Authentication mode updated to 'jwt'"
               },
               "error": null,
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
                   "user_name": "exampleUser",
                   "password": "P*ssword1",
                   "roles": ["user"],
                   "description": "string (optional)",
                   "password_expiry_days": 90,
                   "is_enabled": true,
                   "is_locked": false
                 }
               }
             }
     - .. container:: table-code-small-font

          .. code-block:: json

              {
                "jsonrpc": "2.0",
                "result": {
                  "id": "uuid",
                  "project_id": "uuid",
                  "user_name": "string",
                  "roles": ["user"],
                  "is_enabled": true,
                  "is_locked": false,
                  "last_login": null,
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
                   "user_id": "uuid"
                 }
               }
             }
     - .. container:: table-code-small-font

          .. code-block:: json

              {
                "jsonrpc": "2.0",
                "result": {
                  "id": "uuid",
                  "project_id": "uuid",
                  "user_name": "string",
                  "roles": ["user"],
                  "is_enabled": true,
                  "is_locked": false,
                  "last_login": null,
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
                 "user1-uuid": {
                   "id": "uuid",
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
                 "user2-uuid": {
                   "id": "uuid",
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
               "error": null,
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
                   "user_id": "uuid",
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
                  "id": "uuid",
                  "project_id": "uuid",
                  "user_name": "string",
                  "roles": ["admin"],
                  "is_enabled": true,
                  "is_locked": false,
                  "last_login": null,
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
                   "user_id": "uuid",
                   "force": false
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
                "error": null,
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
                "error": null,
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
               "error": null,
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
               "error": null,
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
               "error": null,
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
               "error": null,
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
                   "action": "lock or unlock"
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
                 "locked_until": "2026-04-08T16:39:15 or null",
                 "message": "User 'string' has been locked/unlocked"
               },
               "error": null,
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
                   "user_id": "uuid",
                   "old_password": "P*ssword1",
                   "new_password": "P*ssword2"
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
               "error": null,
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
                   "user_id": "uuid (optional)",
                   "user_name": "string (optional)",
                   "start_time": "2026-04-01T00:00:00 (optional)",
                   "end_time": "2026-04-08T23:59:59 (optional)",
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
                   "user_id": "uuid",
                   "project_id": "uuid",
                   "login_time": "2026-04-08T16:39:15",
                   "ip_address": "192.168.1.1",
                   "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                   "login_status": true,
                   "failure_reason": null
                 }
               ],
               "error": null,
               "id": 1
             }

   * - **清空登录日志**
     - **clear_login_logs**

       URI: /v1/user/clear_login_logs

       权限要求: ``ROLE_ADMIN``
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "id": 1,
               "method": "clear_login_logs",
               "params": {
                 "body": {
                   "user_id": "uuid (optional)",
                   "user_name": "string (optional)"
                 }
               }
             }

       **参数说明**:

       - ``user_id`` (optional): 清空特定用户ID的登录日志
       - ``user_name`` (optional): 清空特定用户名的登录日志
       - 若两个参数都不指定，清空所有用户的登录日志
       - 注意：``user_id`` 和 ``user_name`` 不能同时指定
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "result": {
                 "count": 42
               },
               "error": null,
               "id": 1
             }

用户管理参数详解
~~~~~~~~~~~~~~~~

用户信息字段说明
^^^^^^^^^^^^^^^^

用户对象的关键字段：

- **id** (uuid) - 用户全局唯一标识
- **user_name** (string) - 用户名，用于登录和识别
- **project_id** (uuid) - 用户所属项目的唯一标识
- **roles** (array) - 用户角色列表，控制用户权限
- **is_enabled** (boolean) - 用户是否启用
- **is_locked** (boolean) - 用户是否被锁定（登录失败过多自动锁定）
- **last_login** (datetime) - 最后登录时间，用于审计
- **password_expiry_days** (int) - 密码有效期内剩余天数
- **password_changed_at** (datetime) - 最后修改密码的时间
- **locked_until** (datetime) - 账户锁定截止时间（null表示未锁定）
- **description** (string) - 用户描述信息
- **created_at** (datetime) - 用户创建时间
- **updated_at** (datetime) - 用户最后修改时间

登录日志字段说明
^^^^^^^^^^^^^^^^

登录日志对象的关键字段：

- **id** (uuid) - 登录日志的唯一标识
- **user_name** (string) - 进行登录操作的用户名
- **user_id** (uuid) - 用户的全局唯一标识
- **project_id** (uuid) - 用户所属项目的唯一标识（可为 null）
- **ip_address** (string) - 登录请求的 IP 地址（支持 IPv4 和 IPv6）
- **login_time** (datetime) - 登录操作发生的时间戳
- **login_status** (boolean) - 登录是否成功（true 为成功，false 为失败）
- **failure_reason** (string) - 登录失败原因（仅当 login_status 为 false 时有值，可为 null）
- **user_agent** (string) - 客户端用户代理信息（可为 null）

角色权限说明
^^^^^^^^^^^^

系统支持基于角色的访问控制 (RBAC)：

- **admin**：管理员角色，拥有所有权限
- **user**：普通用户，有限的权限访问
- **custom**：自定义角色，权限由管理员设定

权限格式：``/v1/{module}/{operation}``

示例：

- ``/v1/device/get_device`` - 获取设备信息
- ``/v1/job/submit_job`` - 提交作业
- ``/v1/user/*`` - 用户管理所有操作
