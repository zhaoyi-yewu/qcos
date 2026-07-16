用户管理
================

本章节主要介绍QCOS系统的用户管理模块设计，包括用户认证、授权、会话管理等核心功能。

概述
----

用户管理模块是QCOS系统的安全核心，负责处理用户身份认证、权限控制、会话管理等关键安全功能。该模块采用现代化的安全架构设计，确保系统的安全性和可扩展性。

核心功能
--------

1. **用户认证**：支持用户名密码认证，使用bcrypt算法进行密码哈希
2. **用户管理**：支持用户的创建、查询、更新和删除等操作，并支持用户与角色的绑定管理
3. **角色管理**：基于角色的访问控制（RBAC），支持角色的创建、查询、更新和删除等操作
4. **权限管理**：支持角色和权限的定义和管理，基于Casbin实现细粒度的权限控制
5. **会话管理**：JWT令牌机制，支持令牌刷新和黑名单管理
6. **安全审计**：登录日志记录，支持安全事件追踪
7. **账户安全**：账户锁定、密码过期策略、登录失败限制

数据模型设计
~~~~~~~~~~~~~~

.. plantuml:: ../../_static/design/module-design/user-role-er.puml
   :caption: 用户管理数据库表ER图
   :alt: 用户管理数据库表ER图
   :width: 80%
   :align: center

项目表 (projects)
~~~~~~~~~~~~~~~~~

.. code-block:: sql

    CREATE TABLE projects (
        id VARCHAR(36) PRIMARY KEY,
        name VARCHAR(100) UNIQUE NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );

**关键字段说明：**

- ``id``：项目ID，UUID格式（最多36字符），主键
- ``name``：项目名称，业务唯一标识（最多100字符）
- ``created_at``：项目创建时间
- ``updated_at``：项目最后更新时间

**内置项目**：

系统启动时自动创建两个默认项目：

1. **默认项目 (Default Project)**

   - 项目ID：``00000000-0000-4000-8000-000000000000``
   - 项目名：``default project``
   - 用途：一般用户和管理员的默认项目

2. **管理项目 (Admin Project)** (保留)

   - 项目ID：``00000000-0000-4000-8000-000000000001``
   - 项目名：``admin project``
   - 用途：系统管理和内部使用

用户表 (users)
~~~~~~~~~~~~~~

.. code-block:: sql

    CREATE TABLE users (
        id UUID PRIMARY KEY,
        project_id VARCHAR(36) NOT NULL,
        user_name VARCHAR(50) UNIQUE NOT NULL,
        hashed_password VARCHAR(255) NOT NULL,
        is_enabled BOOLEAN DEFAULT TRUE,
        is_locked BOOLEAN DEFAULT FALSE,
        last_login DATETIME,
        password_changed_at DATETIME,
        locked_until DATETIME,
        password_expiry_days INTEGER DEFAULT 0,
        failed_login_attempts INTEGER DEFAULT 0,
        description TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (project_id) REFERENCES projects(id)
    );

**关键字段说明：**

- ``id``：用户ID，UUID格式，主键
- ``project_id``：项目ID（外键），用户所属项目，实现多租户隔离
- ``user_name``：用户名，业务唯一标识，50字符以内
- ``hashed_password``：bcrypt加密后的密码哈希值
- ``is_enabled``：账户是否激活，用于启用/禁用用户
- ``roles``：用户关联的角色（通过 user_roles 表维护）
- ``is_locked``：账户是否被锁定，用于登录失败保护
- ``failed_login_attempts``：连续登录失败次数
- ``locked_until``：账户锁定截止时间
- ``password_expiry_days``：密码过期天数，0表示永不过期
- ``password_changed_at``：上次密码修改时间

**内置用户**：

系统启动时自动创建以下用户：

1. **管理员用户 (Admin User)**

   - 用户名：``admin``
   - 密码：``123456`` （默认，应在生产环境修改）
   - 角色：``admin``
   - 项目：``default`` （项目ID: 00000000-0000-4000-8000-000000000000）
   - 描述：``Administrator with full permissions``

2. **匿名用户 (Anonymous User)** (仅在 auth_mode=no 时使用)

   - 用户名：``anonymous``
   - 密码：``123456``
   - 角色：``admin``
   - 项目：``default``
   - 描述：``Anonymous user with full permissions (auth_mode=no)``

角色表 (roles)
~~~~~~~~~~~~~~~

.. code-block:: sql

    CREATE TABLE roles (
        id VARCHAR(36) PRIMARY KEY,
        role_name VARCHAR(50) UNIQUE NOT NULL,
        permissions JSON DEFAULT [],
        description TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );

**关键字段说明：**

- ``id``：角色ID，UUID格式，主键
- ``role_name``：角色名称，业务唯一标识
- ``permissions``：JSON格式存储的权限列表，存储API资源路径
- ``description``：角色描述信息

**内置角色**：

系统启动时自动创建以下角色：

1. **管理员角色 (Admin Role)**

   - 角色名：``admin``
   - 描述：``Administrator with full permissions``
   - 权限：具有所有API访问权限（由Casbin策略定义）

2. **普通用户角色 (User Role)**

   - 角色名：``user``
   - 描述：``Regular user with basic permissions``
   - 权限：基本的系统访问权限（由Casbin策略定义）

用户角色关联表 (user_roles)
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: sql

    CREATE TABLE user_roles (
        id VARCHAR(36) PRIMARY KEY,
        user_id VARCHAR(36) NOT NULL,
        role_id VARCHAR(36) NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (user_id, role_id),
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (role_id) REFERENCES roles(id)
    );

登录日志表 (login_logs)
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: sql

    CREATE TABLE login_logs (
        id VARCHAR(36) PRIMARY KEY,
        project_id VARCHAR(36),
        user_name VARCHAR(50) NOT NULL,
        ip_address VARCHAR(45) NOT NULL,
        login_time DATETIME,
        login_status BOOLEAN NOT NULL,
        failure_reason TEXT,
        user_agent TEXT,
        FOREIGN KEY (project_id) REFERENCES projects(id)
    );

**关键字段说明：**

- ``id``：登录日志ID，UUID格式，主键
- ``project_id``：项目ID（外键，可为null），用户所属项目
- ``ip_address``：支持IPv6格式（最大45字符）
- ``login_status``：登录状态（boolean），true 表示成功，false 表示失败
- ``failure_reason``：登录失败原因（仅当 login_status 为 false 时有值）
- ``user_agent``：客户端用户代理信息（可为null）

令牌黑名单表 (token_blacklist)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: sql

    CREATE TABLE token_blacklist (
        id VARCHAR(36) PRIMARY KEY,
        token_jti VARCHAR(36) UNIQUE NOT NULL,
        expires_at DATETIME NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );

**关键字段说明：**

- ``id``：黑名单记录ID，UUID格式，主键
- ``token_jti``：JWT令牌的唯一标识符（UUID格式）
- ``expires_at``：令牌过期时间，用于自动清理

架构设计
--------

分层架构
~~~~~~~~

用户管理模块采用经典的三层架构设计：

1. **数据访问层（Repository）**：``UserRepository``、``RoleRepository``、``ProjectRepository`` 负责数据库操作
2. **业务逻辑层（Manager）**：``UserManager`` 处理业务规则和权限管理
3. **接口适配层（API）**：``UserAPI`` 提供北向 JSON-RPC 接口

核心类设计
~~~~~~~~~~~

UserRepository
~~~~~~~~~~~~~~

.. code-block:: python

    class UserRepository(BaseRepository):
        """用户数据库操作库"""

        # 密码管理
        @staticmethod
        def hash_password(password: str) -> str
        @staticmethod
        def verify_password(plain_password: str, hashed_password: str) -> bool

        # 用户CRUD
        def create_user(user_create: CreateUserRequest)
        def get_user_by_username(user_name: str)
        def get_user_by_id(user_id: UUID)
        def get_users()
        def update_user(user_id: UUID, user_update: UpdateUserRequest)
        def delete_user_by_id(user_id: UUID)

        # 登录日志
        def create_login_log(user_name: str, ip_address: str, login_status: str)
        def get_login_logs(user_id: UUID, start_time: datetime, end_time: datetime)

        # 令牌管理
        def add_to_blacklist(token_jti: str, expires_at: datetime)
        def is_blacklisted(token_jti: str) -> bool
        def cleanup_blacklist()

UserManager
~~~~~~~~~~~

.. code-block:: python

    class UserManager:
        """User manager."""

        def __init__(
            self,
            access_control_model_file: str,
            access_control_policy_file: str,
            all_api,
            db_session: Session = None,
        ):
            """Init UserManager.

            Args:
                access_control_model_file (str): Access control model file path
                access_control_policy_file (str): Access control policy file path
                all_api: list of all API endpoints
                db_session (Session, optional): SQLAlchemy database session for ORM operations.
                    If provided, enables database persistence. If None, operates in memory.
            """
            self._db_session = db_session
            self.users_repo = UserRepository(db_session) if db_session else None
            self.roles_repo = RoleRepository(db_session) if db_session else None
            self.projects_repo = ProjectRepository(db_session) if db_session else None

            self.all_api = all_api
            # Initialize permission manager for casbin access control
            self.permission_manager = PermissionManager(
                access_control_model_file, access_control_policy_file
            )
            # Internal data structures for managing users and roles
            self.users_db = {}  # key: user_id (UUID str), value: User object
            self.roles_db = {}  # key: role_id (UUID str), value: Role object
            self._username_to_id = {}  # key: username, value: user_id
            self._role_name_to_id = {}  # key: role_name, value: role_id
            self.login_logs = []
            # Initialize default policies for different roles
            self.default_admin_policies = self.fetch_default_policies(
                role=Constant.ROLE_ADMIN
            )
            self.default_user_policies = self.fetch_default_policies(
                role=Constant.ROLE_USER
            )
            self.default_all_policies = self.fetch_default_policies()
            self.noauth_policies = self.fetch_default_policies(
                role=Constant.ROLE_ANY
            )
            self.init_db()
            self.load_role_permissions()

        def create_user(self, user_create: schemas.CreateUserRequest):
            """Create user.

            Args:
                user_create: user create request

            Returns:
                success, error, user
            """
            # Implementation here

        def get_user_mgmt_status(self):
            """Get user management status.

            Returns:
                user management status
            """
            # Implementation here

用户管理初始化
-------------------------

**前置条件**：第一次部署系统时，需要先初始化数据库。

初始部署步骤
~~~~~~~~~~~~

**1. 初始化数据库**

在项目根目录下运行以下命令初始化QCOS数据库：

.. code-block:: bash

   # 进入项目根目录
   cd /path/to/wuyue-os

   # 初始化数据库（创建qcos用户和qcos数据库）
   ./build-scripts/db-manager.sh -i

   # 升级数据库到最新版本（运行所有迁移脚本）
   ./build-scripts/db-manager.sh -u

**db-manager.sh 脚本说明**

``db-manager.sh`` 脚本负责数据库初始化和版本管理，位于 ``build-scripts/`` 目录：

**功能**：

- ``-i, --init`` - 初始化数据库：

  - 创建 ``qcos`` 数据库用户（如不存在）
  - 创建 ``qcos`` 数据库（如不存在）
  - 使用 ``.env`` 文件中的 ``PASS`` 变量作为用户密码

- ``-u, --upgrade`` - 升级数据库到指定版本：

  - 默认升级到最新版本 (head)
  - 运行 Alembic 迁移脚本
  - 创建所有数据库表和关系

- ``-d, --downgrade`` - 降级数据库到指定版本：

  - 默认降级到基础版本 (base)
  - 用于回滚数据库变更

- ``-l, --list`` - 列出所有数据库迁移历史

**使用示例**：

.. code-block:: bash

   # 初始化数据库（仅首次部署需要）
   ./build-scripts/db-manager.sh -i

   # 升级数据库到最新版本
   ./build-scripts/db-manager.sh -u head

   # 降级数据库到基础版本
   ./build-scripts/db-manager.sh -d base

   # 查看迁移历史
   ./build-scripts/db-manager.sh -l

**2. 配置环境变量**

在运行 ``db-manager.sh`` 前，确保 ``build-scripts/.env`` 文件已正确配置：

.. code-block:: bash

   # 数据库连接配置
   QCOS_DATABASE_CONNECTION_URL=postgresql+pg8000://qcos:${PASS}@localhost:5432/qcos

   # 用户管理配置
   AUTH_MODE=jwt
   JWT_AUTH_SECRET_KEY=your-secret-key-here
   JWT_AUTH_ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=30
   REFRESH_TOKEN_EXPIRE_DAYS=7

   # 安全策略
   MAX_LOGIN_ATTEMPTS=5
   LOCKOUT_DURATION_MINUTES=30
   PASSWORD_EXPIRY_DAYS=90

**3. 启动系统**

数据库初始化完成后，系统启动时 ``UserManager.init_db()`` 会按以下顺序执行初始化（仅在数据库为空时执行一次）：

1. **检查PostgreSQL连接** - 验证数据库连接是否正常
2. **检查表是否存在** - 如果表已存在，则跳过初始化
3. **创建默认项目**

   - ``default project`` (ID: 00000000-0000-4000-8000-000000000000)
   - ``admin project`` (ID: 00000000-0000-4000-8000-000000000001)

4. **创建默认角色**

   - ``admin`` - 管理员角色（所有API权限）
   - ``user`` - 普通用户角色（基本系统权限）

5. **创建默认用户**

   - 用户 ``admin`` / 密码 ``123456`` / 角色 ``admin``
   - 用户 ``anonymous`` / 密码 ``123456`` / 角色 ``admin`` (仅在 AUTH_MODE=no 时使用)

**常见问题**

Q: 数据库初始化失败怎么办？
   A: 检查以下项目：

      - PostgreSQL服务是否已启动
      - ``PASS`` 环境变量是否正确设置
      - 数据库用户是否有足够权限
      - 数据库连接配置是否正确

Q: 如何重置数据库？
   A: 执行降级后再升级：

      .. code-block:: bash

         # 降级到基础版本（清除所有表）
         ./build-scripts/db-manager.sh -d base

         # 再次升级到最新版本
         ./build-scripts/db-manager.sh -u

Q: 如何修改默认密码？
   A: 在系统启动后，使用管理员账户登录，然后修改密码或在 ``.env`` 中修改 ``PASS`` 变量后重新初始化

**系统启动检查清单**

.. code-block:: text

   ✓ PostgreSQL已安装并运行（默认localhost:5432）
   ✓ build-scripts/.env已正确配置
   ✓ 运行db-manager.sh -i初始化数据库
   ✓ 运行db-manager.sh -u升级数据库到最新版本
   ✓ 验证所有数据库表已创建
   ✓ 启动QCOS服务
   ✓ 使用admin/123456登录验证系统

**部署完成后**：

1. 系统自动创建的默认用户：

   - 用户名: ``admin``
   - 密码: ``123456`` (⚠️ 生产环境必须修改)
   - 角色: ``admin`` (拥有所有权限)

2. 立即采取的安全措施：

   - 修改管理员默认密码
   - 配置 JWT_AUTH_SECRET_KEY
   - 启用HTTPS
   - 配置防火墙规则

用户角色和权限
--------------------

项目管理
~~~~~~~~

QCOS系统采用多租户架构，支持项目隔离。用户关联到特定的项目，不同项目之间的用户和权限完全隔离。
项目通过 ``ProjectRepository`` 进行管理，支持以下操作：

- 创建项目并分配项目ID（UUID）
- 为项目初始化默认角色和管理员用户
- 查询和管理项目的用户和角色

相关实现详见 :ref:`rbac-权限模型` 部分。

用户管理API使用示例
-------------------------

以下是使用Python客户端调用用户管理API的示例：

.. code-block:: python

   from wy_qcos_client import Client

   # 初始化客户端
   client = Client(base_url="http://localhost:8000")

   # 获取用户管理状态
   status_code, reason, text, result = client.get_user_mgmt_status()
   print(f"User mgmt status: {result}")

   # 创建用户
   status_code, reason, text, result = client.create_user(
       user_name="testuser",
       password="password123",
       roles=["user"],
       description="Test user"
   )
   print(f"Created user: {result}")

   # 获取用户信息
   status_code, reason, text, result = client.get_user(user_id=result['id'])
   print(f"User info: {result}")

   # 更新用户信息
   status_code, reason, text, result = client.update_user(
       user_id=result['id'],
       roles=["user", "admin"],
       description="Updated test user"
   )
   print(f"Updated user: {result}")

   # 查看登录日志
   status_code, reason, text, result = client.get_login_logs(limit=50)
   print(f"Login logs: {result}")

   # 清空所有登录日志
   status_code, reason, text, result = client.clear_login_logs()
   print(f"Cleared all login logs: {result}")

   # 清空特定用户的登录日志
   status_code, reason, text, result = client.clear_login_logs(user_name="admin")
   print(f"Cleared login logs for admin: {result}")

   # 删除用户
   status_code, reason, text, result = client.delete_user(user_id=result['id'])
   print(f"Deleted user: {result}")

安全机制
--------

密码安全
~~~~~~~~

- **加密算法**：使用bcrypt算法进行密码哈希
- **盐值生成**：自动为每个密码生成唯一盐值
- **密码策略**：支持密码复杂度要求和过期策略

认证流程
~~~~~~~~

1. 用户提交用户名和密码
2. 系统验证用户存在且账户未被锁定
3. 验证密码哈希匹配
4. 检查密码是否过期
5. 更新登录时间和失败计数
6. 生成JWT访问令牌和刷新令牌
7. 记录登录日志

JWT令牌机制
~~~~~~~~~~~

- **访问令牌**：短期有效（默认30分钟，通过 ``ACCESS_TOKEN_EXPIRE_MINUTES`` 配置）
- **刷新令牌**：长期有效（默认7天，通过 ``REFRESH_TOKEN_EXPIRE_DAYS`` 配置）
- **令牌刷新**：支持使用刷新令牌获取新的访问令牌
- **令牌撤销**：支持令牌黑名单机制（存储 token jti 和过期时间）

账户锁定策略
~~~~~~~~~~~~

- **失败限制**：连续登录失败5次后锁定账户
- **锁定时间**：默认锁定30分钟
- **自动解锁**：锁定时间过后自动解锁
- **手动解锁**：管理员可手动解锁账户

权限管理
--------

RBAC权限模型
~~~~~~~~~~~~

QCOS系统采用基于角色的访问控制（RBAC），用户可以被分配多个角色，每个角色拥有不同的权限。

内置角色包括：

- **user**：普通用户，具有基本的系统访问权限
- **admin**：管理员，具有用户管理和系统配置权限

权限通过Casbin策略文件定义，支持细粒度的访问控制。

API权限认证机制
~~~~~~~~~~~~~~~

QCOS为所有API方法提供了细粒度的权限控制，包括两部分：

**1. 基于角色的API级别权限 (Role-based)**

通过 ``openapi_extra`` 参数指定API的允许角色：

.. code-block:: python

    @user_api_v1.method(
        openapi_extra={"allowed_roles": [Constant.ROLE_ADMIN]},
        errors=[jsonrpc_errors.ConflictError]
    )
    def create_user(body: schemas.CreateUserRequest):
        """创建用户 - 仅管理员可访问"""
        pass

    @user_api_v1.method(
        openapi_extra={"allowed_roles": Constant.ALL_ROLES},
        errors=[]
    )
    def get_user(body: schemas.GetUserRequest):
        """获取用户信息 - 所有认证用户可访问"""
        pass

**2. 用户级别的操作权限 (User-level)**

某些操作（如修改密码、查看个人信息）需要验证用户身份匹配。使用 ``auth_match_user_id`` 进行额外的权限检查：

.. code-block:: python

    def change_password(
        body: schemas.ChangePasswordRequest,
        auth_data: dict | None = Depends(auth),
    ):
        """修改密码"""
        user_id = body.user_id

        # 权限认证：用户只能修改自己的密码，或管理员可修改任何人的密码
        auth_match_user_id(user_id, auth_data, allow_admin=True)
        # ...进行密码修改...

**auth_match_user_id 说明**：

.. code-block:: python

    def auth_match_user_id(
        user_id: str,
        auth_data: dict | None,
        allow_admin: bool = False
    ):
        """
        验证用户身份匹配

        Args:
            user_id: 目标用户ID
            auth_data: 认证数据（包含当前用户ID和角色）
            allow_admin: 是否允许管理员绕过检查（默认False）

        行为：
            - 如果当前用户ID与目标user_id相同，通过验证
            - 如果 allow_admin=True 且当前用户是admin角色，通过验证
            - 否则抛出 Forbidden 错误
        """
        pass

权限检查规则
~~~~~~~~~~~~

系统对不同的API操作进行权限检查：

- create_user (创建用户) - 要求 ROLE_ADMIN 角色
- get_user (查看用户信息) - 所有角色可用，支持管理员查看其他用户
- update_user (更新用户) - 要求 ROLE_ADMIN 角色
- delete_user (删除用户) - 要求 ROLE_ADMIN 角色
- change_password (修改密码) - 所有角色可用，支持用户修改自己的密码
- get_login_logs (查看登录日志) - 要求 ROLE_ADMIN 角色

.. note::

   在多租户架构下，系统通过 project_id 字段在数据库层面实现租户隔离。
   每个用户只能访问自己所在项目的资源，即使具有对应的角色权限。

配置说明
--------

认证模式 (AUTH_MODE)
~~~~~~~~~~~~~~~~~~~~

QCOS系统通过 ``AUTH_MODE`` 配置参数支持多种认证模式，适应不同的部署场景。

**模式概览**：

.. code-block:: text

    AUTH_MODE: no | jwt | virtual_instance

    - no:                  禁用认证（开发/测试环境）
    - jwt:                 启用JWT认证（生产环境推荐）
    - virtual_instance:    虚拟实例认证（云资源隔离）


**1. AUTH_MODE=no (禁用认证)**

**作用**：完全禁用用户认证和权限检查

**效果**：

- ✅ 所有API调用无需认证令牌
- ✅ 系统自动使用 ``anonymous`` 用户身份
- ✅ 所有用户被视为 ``admin`` 角色（具有所有权限）
- ✅ 不记录登录日志和权限审计
- ✅ JWT令牌验证被跳过

**使用场景**：

- 本地开发环境
- 内部测试和演示
- 不需要鉴权的专网部署

**安全风险**：⚠️ **仅用于非生产环境**

**配置示例**：

.. code-block:: bash

    AUTH_MODE=no

**API行为**：

.. code-block:: python

    # 所有API都无需提供认证令牌
    client = Client(api_server_ip="127.0.0.1")

    # 即使传入错误的token也会被忽略
    result = client.create_user(
        user_name="test",
        password="password",
        roles=["user"]
    )  # 成功，无需认证

**2. AUTH_MODE=jwt (JWT认证)**

**作用**：启用基于JWT令牌的身份认证

**效果**：

- ✅ 用户必须通过 ``login`` 接口获取JWT令牌
- ✅ 所有API请求必须携带有效的访问令牌
- ✅ 系统执行基于角色的权限检查 (RBAC)
- ✅ 用户可以修改密码、管理个人设置
- ✅ 完整的登录日志和权限审计记录
- ✅ 支持令牌刷新和令牌撤销

**认证流程**：

1. 用户调用 ``login`` 获取令牌

   .. code-block:: python

      # Step 1: 获取令牌
      response = client.login(
          username="admin",
          password="123456"
      )
      access_token = response["access_token"]
      refresh_token = response["refresh_token"]

2. 使用令牌访问受保护的API

   .. code-block:: python

      # Step 2: 提供令牌给client
      client.set_token(access_token)

      # Step 3: 访问受保护的API
      result = client.create_user(
          user_name="testuser",
          password="password123",
          roles=["user"]
      )  # 成功，因为default用户(admin)有权限

3. 令牌过期后使用刷新令牌获取新令牌

   .. code-block:: python

      # 当访问令牌过期时
      response = client.refresh_token(
          refresh_token=refresh_token
      )
      new_access_token = response["access_token"]
      client.set_token(new_access_token)

**使用场景**：

- 生产环境
- 多用户系统
- 需要权限隔离的部署
- 需要审计日志的合规场景

**默认用户**：

- 用户名: ``admin``
- 密码: ``123456`` (在部署时建议修改为强密码)
- 角色: ``admin``

**配置示例**：

.. code-block:: bash

    AUTH_MODE=jwt

    # 用户认证和授权配置
    ACCESS_TOKEN_EXPIRE_MINUTES=30
    REFRESH_TOKEN_EXPIRE_DAYS=7
    MAX_LOGIN_ATTEMPTS=5
    LOCKOUT_DURATION_MINUTES=30
    PASSWORD_EXPIRY_DAYS=90

    # JWT配置
    JWT_AUTH_SECRET_KEY=your-secret-key-here
    JWT_AUTH_ALGORITHM=HS256

**权限检查示例**：

.. code-block:: text

    API: create_user
    ├─ 第1层：基于角色
    │  └─ allowed_roles: [ROLE_ADMIN]  → admin用户通过 ✅
    │                                     user用户被拒 ❌ (Forbidden)
    │
    └─ 第2层：用户级检查（若有）
       └─ auth_match_user_id(user_id) → 额外验证用户匹配


**3. AUTH_MODE=virtual_instance (虚拟实例认证)**

**作用**：使用虚拟实例ID进行设备级别的认证和隔离

**效果**：

- ✅ 系统验证 ``x-qcos-virtual-instance-id`` 请求头
- ✅ 虚拟实例ID包含加密的设备信息
- ✅ 系统基于虚拟实例隔离设备访问权限
- ✅ 无需用户级别的密码认证
- ✅ 适用于云环境中的资源隔离

**虚拟实例ID加密编码**：

使用encrypt-virtual-instance-id.py工具生成虚拟实例ID, 在HTTP header中
带入x-qcos-virtual-instance-id: {encrypted-data}, 就可以进行认证，无需
事先创建用户。其中:
1. salt参数是加密的盐值，必须与系统配置的PASSWORD_SALT一致
2. device_name参数是设备名称，可以指定一个或多个设备， 示例中为dummy和qutip_sim两个设备

.. code-block:: shell

    ./bin/encrypt-virtual-instance-id.py -e -s 123456 -dn dummy qutip_sim -i 00000000-0000-4000-8000-000000000123
    [Input]
    device_name: dummy, qutip_sim
    instance_id: 00000000-0000-4000-8000-000000000123, salt: 123456

    [Output]
    virtual_instance_id: ZHVtbXkrcXV0aXBfc2ltfDAwMDAwMDAwLTAwMDAtNDAwMC04MDAwLTAwMDAwMDAwMDEyM3w5NzQ5
    export QCOS_VIRTUAL_INSTANCE_ID=ZHVtbXkrcXV0aXBfc2ltfDAwMDAwMDAwLTAwMDAtNDAwMC04MDAwLTAwMDAwMDAwMDEyM3w5NzQ5

**虚拟实例ID格式**：

虚拟实例ID是一个加密的令牌，包含：

.. code-block:: text

    x-qcos-virtual-instance-id: {encrypted-data}

    解密后内容示例:
    {
        "device_names": ["device1", "device2"],
        "instance_id": "instance-id-123"
    }

    特殊值:

    - device_names=["all"], instance_id="all" → admin权限

**认证流程**：

1. 云平台生成虚拟实例ID

   .. code-block:: python

      from wy_qcos.common.library import Library

      # 加密虚拟实例信息
      device_names = ["device1", "device2"]
      instance_id = "instance-xyz"

      success, error, encrypted_id = Library.encrypt_virtual_instance_id(
          device_names, instance_id,
          salt=PASSWORD_SALT,
          encode=True
      )

2. 客户端在请求头中提供虚拟实例ID

   .. code-block:: python

      headers = {
          "x-qcos-virtual-instance-id": encrypted_id
      }

      # 调用API
      response = client.submit_job(
          code_type="qasm",
          backend="device1",  # 必须在device_names中
          ...
      )

3. 系统验证虚拟实例ID

   .. code-block:: text

      API接收到请求 → 验证虚拟实例ID
      ├─ 解密成功 → 验证设备权限
      │  ├─ 设备在允许列表 → 请求通过 ✅
      │  └─ 设备不在允许列表 → Unauthorized ❌
      │
      └─ 解密失败 → Unauthorized ❌

**使用场景**：

- 云平台多租户隔离
- 物理设备的虚拟化分配
- SaaS环境中的资源隔离
- 无需用户密码的云API调用

**配置示例**：

.. code-block:: bash

    AUTH_MODE=virtual_instance

    # 密钥配置
    PASSWORD_SALT=your-encryption-salt

**虚拟实例隔离示例**：

.. code-block:: text

    企业A虚拟实例:
    ├─ device_names: ["device-A-1", "device-A-2"]
    ├─ instance_id: "tenant-a-001"
    └─ 只能访问device-A-1和device-A-2

    企业B虚拟实例:
    ├─ device_names: ["device-B-1", "device-B-3"]
    ├─ instance_id: "tenant-b-001"
    └─ 只能访问device-B-1和device-B-3

    系统管理员虚拟实例:
    ├─ device_names: ["all"]
    ├─ instance_id: "all"
    └─ 可以访问所有设备

---

**认证模式对比**：

认证模式的特性对比：

- 用户认证: no(❌) jwt(✅) virtual_instance(❌)
- 密码检查: no(❌) jwt(✅) virtual_instance(❌)
- 权限检查: no(❌) jwt(✅) virtual_instance(✅)
- 登录日志: no(❌) jwt(✅) virtual_instance(❌)
- JWT令牌: no(❌) jwt(✅) virtual_instance(❌)
- 虚拟实例隔离: no(❌) jwt(❌) virtual_instance(✅)
- 设备访问隔离: no(❌) jwt(❌) virtual_instance(✅)
- 使用场景: no(开发测试) jwt(生产环境) virtual_instance(云平台隔离)
- 安全等级: no(低⚠️) jwt(高✅) virtual_instance(中等⚡)

环境变量配置
~~~~~~~~~~~~

系统通过环境变量或配置文件配置用户管理相关参数：

.. code-block:: bash

    # JWT配置
    JWT_AUTH_SECRET_KEY=47pW_6k8A4iU1Z8-r8G2j4_xN9M5V3L7Q9p2X1Y4Z0A
    JWT_AUTH_ALGORITHM=HS256
    ACCESS_TOKEN_EXPIRE_MINUTES=30          # 访问令牌过期时间（分钟）
    REFRESH_TOKEN_EXPIRE_DAYS=7             # 刷新令牌过期时间（天）

    # 安全策略
    MAX_LOGIN_ATTEMPTS=5                    # 最大登录失败次数
    LOCKOUT_DURATION_MINUTES=30             # 账户锁定时长（分钟）
    PASSWORD_EXPIRY_DAYS=90                 # 密码过期天数（0表示永不过期）

    # 数据库和权限配置
    QCOS_DATABASE_CONNECTION_URL=postgresql+pg8000://prefect:${password}@127.0.0.1:5432/qcos
    ACCESS_CONTROL_MODEL_FILE=/etc/qcos/roles/casbin_model.conf
    ACCESS_CONTROL_POLICY_FILE=/etc/qcos/roles/policy.conf
    ADMIN_PASSWORD=your-admin-password      # 默认管理员密码（可选），推荐强密码

安全建议
--------

1. **生产环境部署**：

   - 使用强随机密钥作为JWT_SECRET_KEY
   - 启用HTTPS传输加密
   - 定期轮换密钥

2. **密码策略**：

   - 要求密码包含大小写字母、数字和特殊字符
   - 设置合理的密码过期时间
   - 禁止使用常见弱密码

3. **监控和审计**：

   - 监控异常登录行为
   - 定期审计用户权限分配
   - 保留足够的登录日志用于安全分析

4. **数据保护**：

   - 定期备份用户数据
   - 实施数据库访问控制
   - 加密敏感数据存储
