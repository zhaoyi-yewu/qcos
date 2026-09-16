用户管理命令
----------------------

用户管理命令包含用户账户的增删改查、角色的增删改查、权限配置、密码的修改等操作。

.. important::

   **双参数模式说明**

   以下命令支持使用 UUID 或名称来标识用户/角色：

   - 用户命令：``get-user``、``update-user``、``delete-user``、``change-password``
   - 角色命令：``get-role``、``update-role``、``delete-role``

   系统会自动识别参数类型（UUID格式或字符串名称）并执行对应的查询操作。

用户管理状态
***************

获取用户管理系统状态的操作命令

命令行参数
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 获取用户管理状态
   usage: qcos-cli get-user-mgmt [-h] [-f {json,shell,table,value,yaml}]
                                        [-c COLUMN] [--noindent] [--prefix PREFIX]
                                        [--max-width <integer>] [--fit-width]
                                        [--print-empty]

   Get user management status.

   options:
     -h, --help            show this help message and exit

典型场景示例
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 获取用户管理状态
   qcos-cli get-user-mgmt

用户创建
***************

创建用户的操作命令

命令行参数
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 创建用户
   usage: qcos-cli create-user [-h] [--role-name ROLE_NAMES [ROLE_NAMES ...]] [--description DESCRIPTION] [--password-expiry-days PASSWORD_EXPIRY_DAYS] [--disable] [--lock] user_name password

   Create user.

   positional arguments:
     user_name             User name
     password              Password

   options:
     -h, --help            show this help message and exit
     --role-name ROLE_NAMES [ROLE_NAMES ...]
                           Role names (space-separated)
     --description DESCRIPTION
                           Description
     --password-expiry-days PASSWORD_EXPIRY_DAYS
                           Password expiry days (optional, 0: never expired)
     --disable             Disable user account upon creation
     --lock                Lock user account upon creation

典型场景示例
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 创建一个普通用户
   qcos-cli create-user test mypassword

   # 创建一个管理员用户
   qcos-cli create-user test1 mypassword --role-name admin

   # 创建一个禁用的用户
   qcos-cli create-user test2 mypassword --disable

   # 创建一个锁定的用户
   qcos-cli create-user test3 mypassword --lock

   # 创建一个密码永不过期的用户
   qcos-cli create-user test4 mypassword --password-expiry-days 0

   # 创建一个完整配置的用户（多角色）
   qcos-cli create-user test5 mypassword --role-name admin operator --description "Admin" --password-expiry-days 90 --disable --lock

用户列表查询
***************

查询用户列表的操作命令

命令行参数
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 查询用户列表
   usage: qcos-cli list-users [-h] [--user-name USER_NAME]
                              [-f {csv,json,table,value,yaml}] [-c COLUMN]
                              [--quote {all,minimal,none,nonnumeric}] [--noindent]
                              [--max-width <integer>] [--fit-width] [--print-empty]
                              [--sort-column SORT_COLUMN] [--sort-ascending | --sort-descending]

   Get users.

   options:
     -h, --help            show this help message and exit
     --user-name USER_NAME Filter users by user name (optional)

典型场景示例
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 查询所有用户列表
   qcos-cli list-users

   # 查询特定用户
   qcos-cli list-users --user-name admin

用户详情查询
***************

查询用户详情的操作命令

命令行参数
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 查询用户详情
   usage: qcos-cli get-user [-h] [-f {json,shell,table,value,yaml}] [-c COLUMN] [--noindent] [--prefix PREFIX]
                            [--max-width <integer>] [--fit-width] [--print-empty]
                            user_id

   Get user by ID or name. Can accept either a UUID or a user name as user_id parameter. If a valid UUID is provided, it will be used directly.
   Otherwise, the system will look up the user by name.

   positional arguments:
     user_id       User ID (UUID) or user name

典型场景示例
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 查询用户test的详情
   qcos-cli get-user test

用户信息更新
***************

更新用户的操作命令

命令行参数
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 更新用户
   usage: qcos-cli update-user [-h] [--role-name ROLE_NAMES [ROLE_NAMES ...]]
                               [--password-expiry-days PASSWORD_EXPIRY_DAYS]
                               [--description DESCRIPTION] [--enable] [--disable]
                               [--lock] [--unlock]
                               user_id

   Update user by ID or name.
   Can accept either a UUID or a user name as user_id parameter.
   If a valid UUID is provided, it will be used directly.
   Otherwise, the system will look up the user by name.

   positional arguments:
     user_id               User ID (UUID) or user name

   options:
     -h, --help            show this help message and exit
     --role-name ROLE_NAMES [ROLE_NAMES ...]
                           Role names (space-separated, default: user)
     --password-expiry-days PASSWORD_EXPIRY_DAYS
                           Password expiry days (optional, 0: never expired)
     --description DESCRIPTION
                           Description
     --enable              Enable user account
     --disable             Disable user account
     --lock                Lock user account
     --unlock              Unlock user account

典型场景示例
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 更新用户角色和密码过期天数
   qcos-cli update-user test --role-name admin --password-expiry-days 80

   # 更新用户多角色
   qcos-cli update-user test --role-name admin operator

   # 启用用户账户
   qcos-cli update-user test --enable

   # 禁用用户账户
   qcos-cli update-user test --disable

   # 锁定用户账户
   qcos-cli update-user test --lock

   # 解锁用户账户
   qcos-cli update-user test --unlock

   # 完整的用户更新示例
   qcos-cli update-user test --role-name admin --password-expiry-days 90 --description "updated admin" --enable --unlock

   # 使用UUID更新用户
   qcos-cli update-user 00000000-0000-4000-8000-000000000001 --enable

用户删除
***************

删除用户的操作命令

命令行参数
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 删除用户
   usage: qcos-cli delete-user [-h] [-f/--force] user_id

   Delete user by ID or name.
   Can accept either a UUID or a user name as user_id parameter.
   If a valid UUID is provided, it will be used directly.
   Otherwise, the system will look up the user by name.

   positional arguments:
     user_id       User ID (UUID) or user name

   options:
     -h, --help            show this help message and exit
     -f, --force           Force delete user and cascade delete related resources

典型场景示例
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 删除用户：test
   qcos-cli delete-user test

   # 强制删除用户及其相关资源
   qcos-cli delete-user test --force

   # 使用UUID删除用户
   qcos-cli delete-user 00000000-0000-4000-8000-000000000001

用户密码修改
***************

修改用户密码的操作命令

命令行参数
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 修改密码
   usage: qcos-cli change-password [-h] user_id old_password new_password

   Change password for user by ID or name.
   Can accept either a UUID or a user name as user_id parameter.
   If a valid UUID is provided, it will be used directly.
   Otherwise, the system will look up the user by name.

   positional arguments:
     user_id       User ID (UUID) or user name
     old_password  Old password
     new_password  New password

   options:
     -h, --help    show this help message and exit

典型场景示例
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 修改用户test的密码
   qcos-cli change-password test oldpass123 newpass456

   # 使用UUID修改密码
   qcos-cli change-password 00000000-0000-4000-8000-000000000001 oldpass123 newpass456

登录日志查询
***************

查询用户登录日志的操作命令

命令行参数
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 获取登录日志
   usage: qcos-cli list-login-logs [-h] [--user-id USER_ID] [--user-name USER_NAME]
                                   [--limit LIMIT] [--offset OFFSET]
                                   [-f {csv,json,table,value,yaml}] [-c COLUMN]
                                   [--quote {all,minimal,none,nonnumeric}]
                                   [--noindent] [--max-width <integer>]
                                   [--fit-width] [--print-empty]

   Get login logs.

   options:
     -h, --help            show this help message and exit
     --user-id USER_ID     User ID (UUID)
     --user-name USER_NAME User name
     --limit LIMIT         Limit (default: 100)
     --offset OFFSET       Offset (default: 0)

   注意：--user-id 和 --user-name 不能同时指定，请只选择其中一个

典型场景示例
~~~~~~~~~~~~~~~

.. code-block:: shell

    # 获取所有登录日志
    qcos-cli list-login-logs

    # 获取特定用户的登录日志
    qcos-cli list-login-logs --user-name admin

    # 获取特定用户ID的登录日志，限制50条
    qcos-cli list-login-logs --user-id 00000000-0000-4000-8000-000000000001 --limit 50

    # 分页查询
    qcos-cli list-login-logs --limit 20 --offset 40

登录日志清空
***************

清空用户登录日志的操作命令

命令行参数
~~~~~~~~~~~~~~~

.. code-block:: shell

    # 清空登录日志
    usage: qcos-cli clear-login-logs [-h] [--user-id USER_ID] [--user-name USER_NAME] [--force]

    Clear login logs.

    options:
      -h, --help            show this help message and exit
      --user-id USER_ID     Clear logs for a specific user ID (UUID)
      --user-name USER_NAME Clear logs for a specific user name
      --force               Skip confirmation prompt

    注意：--user-id 和 --user-name 不能同时指定，请只选择其中一个

典型场景示例
~~~~~~~~~~~~~~~

.. code-block:: shell

    # 清空所有登录日志（需要确认）
    qcos-cli clear-login-logs

    # 清空所有登录日志（跳过确认）
    qcos-cli clear-login-logs --force

    # 清空特定用户的登录日志
    qcos-cli clear-login-logs --user-name admin

    # 清空特定用户ID的登录日志，跳过确认
    qcos-cli clear-login-logs --user-id 00000000-0000-4000-8000-000000000001 --force

角色管理命令
***************

角色相关的增删改查操作

角色创建
~~~~~~~~~~~~~~~~~

创建角色的操作命令

命令行参数
~~~~~~~~~~~~

.. code-block:: shell

   # 创建角色
   usage: qcos-cli create-role [-h] [--description DESCRIPTION]
                               role_name permissions

   Create role.

   positional arguments:
     role_name             Role name
     permissions           Permissions (JSON array, e.g., '["api/path1", "api/path2"]')

   options:
     -h, --help            show this help message and exit
     --description DESCRIPTION
                           Role description

典型场景示例
~~~~~~~~~~~~~~~~~~~~

.. code-block:: shell

   # 创建一个只读用户角色
   qcos-cli create-role viewer '["/version", "/v1/driver/get_drivers"]' --description "Read-only user"

角色列表查询
~~~~~~~~~~~~~~~~~

查询所有角色的操作命令

命令行参数
~~~~~~~~~~~~

.. code-block:: shell

   # 查询角色列表
   usage: qcos-cli list-roles [-h] [--role-name ROLE_NAME]
                              [-f {csv,json,table,value,yaml}] [-c COLUMN]
                              [--quote {all,minimal,none,nonnumeric}]
                              [--noindent] [--max-width <integer>]
                              [--fit-width] [--print-empty]
                              [--sort-column SORT_COLUMN]
                              [--sort-ascending | --sort-descending]

   Get roles.

   options:
      -h, --help            show this help message and exit
      --role-name ROLE_NAME Filter roles by role name

典型场景示例
~~~~~~~~~~~~~~~~~~~~

.. code-block:: shell

   # 查询所有角色
   qcos-cli list-roles

   # 查询特定角色
   qcos-cli list-roles --role-name admin

角色详情查询
~~~~~~~~~~~~~~~~~

查询角色详情的操作命令

命令行参数
~~~~~~~~~~~~

.. code-block:: shell

   # 查询角色详情
   usage: qcos-cli get-role [-h] [-f {json,shell,table,value,yaml}]
                            [-c COLUMN] [--noindent] [--prefix PREFIX]
                            [--max-width <integer>] [--fit-width]
                            [--print-empty]
                            role_id

   Get role by ID or name.
   Can accept either a UUID or a role name as role_id parameter.
   If a valid UUID is provided, it will be used directly.
   Otherwise, the system will look up the role by name.

   positional arguments:
     role_id       Role ID (UUID) or role name

典型场景示例
~~~~~~~~~~~~~~~~~~~~

.. code-block:: shell

   # 查询admin角色的详情
   qcos-cli get-role admin

   # 使用UUID查询角色详情
   qcos-cli get-role 00000000-0000-4000-8000-000000000002

角色更新
~~~~~~~~~~~~~~~

更新角色的操作命令

命令行参数
~~~~~~~~~~~~

.. code-block:: shell

   # 更新角色
   usage: qcos-cli update-role [-h] [--permissions PERMISSIONS]
                               [--description DESCRIPTION]
                               role_id

   Update role by ID or name.
   Can accept either a UUID or a role name as role_id parameter.
   If a valid UUID is provided, it will be used directly.
   Otherwise, the system will look up the role by name.

   positional arguments:
     role_id               Role ID (UUID) or role name

   options:
     -h, --help            show this help message and exit
     --permissions PERMISSIONS
                           Permissions (JSON array, e.g., '["api/path1", "api/path2"]')
     --description DESCRIPTION
                           Role description

典型场景示例
~~~~~~~~~~~~~~~~~~~~

.. code-block:: shell

   # 更新角色权限
   qcos-cli update-role admin --permissions '["/version"]'

   # 更新角色描述
   qcos-cli update-role viewer --description "Read-only viewer role"

   # 同时更新权限和描述
   qcos-cli update-role viewer --permissions '["/version", "/v1/driver/get_drivers"]' --description "Editor role"

角色删除
~~~~~~~~~~~~~~~

删除角色的操作命令

命令行参数
~~~~~~~~~~~~

.. code-block:: shell

   # 删除角色
   usage: qcos-cli delete-role [-h] role_id

   Delete role by ID or name.
   Can accept either a UUID or a role name as role_id parameter.
   If a valid UUID is provided, it will be used directly.
   Otherwise, the system will look up the role by name.

   positional arguments:
     role_id       Role ID (UUID) or role name

   options:
     -h, --help    show this help message and exit

典型场景示例
~~~~~~~~~~~~~~~~~~~~

.. code-block:: shell

   # 删除一个角色
   qcos-cli delete-role viewer

   # 使用UUID删除角色
   qcos-cli delete-role 00000000-0000-4000-8000-000000000003
