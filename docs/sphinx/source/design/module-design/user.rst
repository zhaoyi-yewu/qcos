用户管理
================

本章节主要介绍QCOS系统的用户管理模块设计，包括用户认证、授权、会话管理等核心功能。

概述
----

用户管理模块是QCOS系统的安全核心，负责处理用户身份认证、权限控制、会话管理等关键安全功能。该模块采用现代化的安全架构设计，确保系统的安全性和可扩展性。

核心功能
--------

1. **用户认证**：支持用户名密码认证，使用bcrypt算法进行密码哈希
2. **权限管理**：基于角色的访问控制（RBAC），支持多角色分配
3. **会话管理**：JWT令牌机制，支持令牌刷新和黑名单管理
4. **安全审计**：登录日志记录，支持安全事件追踪
5. **账户安全**：账户锁定、密码过期策略、登录失败限制

数据模型设计
~~~~~~~~~~~~~~

用户表 (users)
~~~~~~~~~~~~~~

.. code-block:: sql

    CREATE TABLE users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_name VARCHAR(50) UNIQUE NOT NULL,
        hashed_password VARCHAR(255) NOT NULL,
        is_active BOOLEAN DEFAULT TRUE,
        roles JSON DEFAULT [],
        is_locked BOOLEAN DEFAULT FALSE,
        last_login DATETIME,
        password_changed_at DATETIME,
        locked_until DATETIME,
        password_expiry_days INTEGER DEFAULT 0,
        failed_login_attempts INTEGER DEFAULT 0,
        description TEXT,
        created_at DATETIME,
        updated_at DATETIME
    );

**关键字段说明：**

- ``user_name``：用户名，业务唯一标识，50字符以内
- ``hashed_password``：bcrypt加密后的密码哈希值
- ``is_active``：账户是否激活，用于软删除场景
- ``roles``：JSON格式存储的角色列表，支持多角色
- ``is_locked``：账户是否被锁定，用于登录失败保护
- ``failed_login_attempts``：连续登录失败次数
- ``locked_until``：账户锁定截止时间
- ``password_expiry_days``：密码过期天数，0表示永不过期
- ``password_changed_at``：上次密码修改时间

角色表 (roles)
~~~~~~~~~~~~~~~

.. code-block:: sql

    CREATE TABLE roles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        role_name VARCHAR(50) UNIQUE NOT NULL,
        permissions JSON DEFAULT [],
        description TEXT,
        created_at DATETIME,
        updated_at DATETIME
    );

**关键字段说明：**

- ``role_name``：角色名称，业务唯一标识
- ``permissions``：JSON格式存储的权限列表
- ``description``：角色描述信息

用户角色关联表 (user_roles)
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: sql

    CREATE TABLE user_roles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        role_id INTEGER NOT NULL,
        created_at DATETIME,
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (role_id) REFERENCES roles(id)
    );

登录日志表 (login_logs)
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: sql

    CREATE TABLE login_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_name VARCHAR(50) NOT NULL,
        ip_address VARCHAR(45) NOT NULL,
        login_time DATETIME,
        login_status VARCHAR(20) NOT NULL,
        user_agent TEXT,
        FOREIGN KEY (user_name) REFERENCES users(user_name)
    );

**关键字段说明：**

- ``ip_address``：支持IPv6格式（最大45字符）
- ``login_status``：登录状态，包括 'success' 和 'failed'
- ``user_agent``：客户端用户代理信息

令牌黑名单表 (token_blacklist)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: sql

    CREATE TABLE token_blacklist (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        token_jti VARCHAR(36) UNIQUE NOT NULL,
        expires_at DATETIME NOT NULL,
        created_at DATETIME
    );

**关键字段说明：**

- ``token_jti``：JWT令牌的唯一标识符（UUID格式）
- ``expires_at``：令牌过期时间，用于自动清理

架构设计
--------

分层架构
~~~~~~~~

用户管理模块采用经典的三层架构设计：

1. **数据访问层（Repository）**：``UserRepository`` 负责数据库操作
2. **业务逻辑层（Service）**：``UserService`` 处理业务规则
3. **接口适配层（API）**：``UserAPI`` 提供北向接口

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
            self, access_control_model_file, access_control_policy_file, all_api
        ):
            """Init UserManager.

            Args:
                access_control_model_file (str): Access control model file path
                access_control_policy_file (str): Access control policy file path
                all_api: list of all API endpoints
            """
            self.users_db = {}  # key: user_id (UUID str), value: User object
            self.roles_db = {}  # key: role_id (UUID str), value: Role object
            self._username_to_id = {}  # key: username, value: user_id
            self._role_name_to_id = {}  # key: role_name, value: role_id
            self.login_logs = []
            # key: token_jti, value: expires_at (datetime)
            self.token_blacklist = {}
            self.all_api = all_api
            # Initialize permission manager for casbin access control
            self.permission_manager = PermissionManager(
                access_control_model_file, access_control_policy_file
            )
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
            self.init_users()

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

系统启动时，用户管理模块会初始化用户数据库、权限管理器和认证服务。

.. code-block:: python

   # 初始化用户管理器
   from wy_qcos.user.user_manager import UserManager
   user_manager = UserManager(
       access_control_model_file="path/to/model.conf",
       access_control_policy_file="path/to/policy.csv",
       all_api=all_api_endpoints
   )

   # 获取用户管理状态
   status = user_manager.get_user_mgmt_status()

用户角色和权限
--------------------

QCOS系统采用基于角色的访问控制（RBAC），用户可以被分配多个角色，每个角色拥有不同的权限。

内置角色包括：

- **user**：普通用户，具有基本的系统访问权限
- **admin**：管理员，具有用户管理和系统配置权限

权限通过Casbin策略文件定义，支持细粒度的访问控制。

.. plantuml:: ../../_static/design/module-design/user-role-er.puml
   :caption: 用户角色关系图
   :alt: 用户角色关系图
   :width: 50%
   :align: center

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

- **访问令牌**：短期有效（默认15分钟）
- **刷新令牌**：长期有效（默认7天）
- **令牌刷新**：支持使用刷新令牌获取新的访问令牌
- **令牌撤销**：支持令牌黑名单机制

账户锁定策略
~~~~~~~~~~~~

- **失败限制**：连续登录失败5次后锁定账户
- **锁定时间**：默认锁定30分钟
- **自动解锁**：锁定时间过后自动解锁
- **手动解锁**：管理员可手动解锁账户

权限管理
--------

RBAC模型
~~~~~~~~

系统采用基于角色的访问控制（RBAC）模型：

- **用户**：系统使用者
- **角色**：权限的集合
- **权限**：具体的操作许可

角色层级
~~~~~~~~

系统预定义以下角色：

1. **系统管理员（admin）**：拥有系统管理权限
2. **普通用户（user）**：拥有基本使用权限

权限验证
~~~~~~~~

权限验证在API层进行，通过装饰器实现：

.. code-block:: python

   @user_api_v1.method(
   openapi_extra={"allowed_roles": [Constant.ROLE_ADMIN]},
   errors=[jsonrpc_errors.ConflictError, jsonrpc_errors.BadRequestError],
   )
   def create_user(
   body: schemas.CreateUserRequest,


配置说明
--------

环境变量配置
~~~~~~~~~~~~

系统通过环境变量配置用户管理相关参数：

.. code-block:: bash

    # JWT配置
    JWT_SECRET_KEY=your-secret-key-here
    JWT_ALGORITHM=HS256
    ACCESS_TOKEN_EXPIRE_MINUTES=15
    REFRESH_TOKEN_EXPIRE_DAYS=7

    # 安全策略
    MAX_LOGIN_ATTEMPTS=5
    LOCKOUT_DURATION_MINUTES=30
    PASSWORD_EXPIRY_DAYS=90
    MIN_PASSWORD_LENGTH=8

    # 数据库配置
    QCOS_DATABASE_PASSWORD=database-password

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
