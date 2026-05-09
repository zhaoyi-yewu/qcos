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
                   "user_name": "string",
                   "password": "string",
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
                   "user_id": "uuid or user_name"
                 }
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
                 "user2": {
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
                   "user_id": "uuid or user_name",
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
                   "user_id": "uuid or user_name",
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
                   "user_id": "uuid or user_name",
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
                   "user_id": "uuid or user_name",
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
                   "user_id": "uuid or user_name (optional)",
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
                   "login_time": "2026-04-08T16:39:15",
                   "ip_address": "192.168.1.1",
                   "user_agent": "Mozilla/5.0...",
                   "success": true,
                   "failure_reason": null
                 }
               ],
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

最佳实践建议
^^^^^^^^^^^^^^^^

1. **用户生命周期管理**

   .. code-block:: text

      创建用户 -> 分配角色 -> 定期审计 -> 禁用/删除

      • 创建新用户时设置合理的密码过期时间
      • 定期检查 last_login 字段检测异常账户
      • 未使用的账户应及时禁用而不是删除

2. **密码策略**

   .. code-block:: text

      • 初始密码应临时且强制首次登录时修改
      • 定期强制修改密码（建议90天）
      • 实施密码复杂性检查
      • 防止密码重复使用

3. **账户安全**

   .. code-block:: python

      # 监控异常活动
      def check_account_security(user_id):
          login_logs = get_login_logs(user_id=user_id)

          # 检查异常登录地点
          ips = [log["ip_address"] for log in login_logs]
          if has_unusual_ips(ips):
              alert_security_team()

          # 检查失败尝试
          failures = [log for log in login_logs if not log["success"]]
          if len(failures) > 5:
              lock_user_account(user_id)

4. **权限管理**

   .. code-block:: text

      最小权限原则：

      • 为用户分配完成工作所需的最小权限
      • 定期审查和更新用户权限
      • 使用自定义角色为不同场景定制权限
      • 记录所有权限变更用于审计

5. **角色设计**

   .. code-block:: python

      # 推荐的角色划分
      roles = {
          "admin": [
              "/v1/user/*",      # 用户管理
              "/v1/device/*",    # 设备管理
              "/v1/job/*",       # 作业管理
              "/v1/system/*"     # 系统管理
          ],
          "operator": [
              "/v1/device/get_device",      # 查看设备
              "/v1/job/*"                   # 作业操作
          ],
          "viewer": [
              "/v1/device/get_device",      # 仅查看设备
              "/v1/job/get_jobs",           # 仅查看作业列表
              "/v1/job/get_job_status"      # 仅查看作业状态
          ]
      }
