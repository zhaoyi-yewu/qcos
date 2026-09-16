通用认证HTTP头
====================

通用认证HTTP头用于通过HTTP Header，传递认证信息。

用户认证头
~~~~~~~~~~

JWT认证
^^^^^^^^^^^^^^

JSON RPC的HTTP Header中添加Authorization头，用于JWT认证。

.. code-block:: text

   http headers:
     "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

**说明**：

- ``Authorization`` 头使用标准的Bearer Token格式
- Token内容为JWT令牌，由登录接口返回
- 所有需要认证的接口都需要携带此头

虚拟实例认证
^^^^^^^^^^^^^^

JSON RPC的HTTP Header中添加x-qcos-virtual-instance-id, 可以用来区分量子计算机虚拟实例

.. code-block:: text

   http headers:
     "x-qcos-virtual-instance-id": "xxxxx-xxxx"

**说明**：

- ``x-qcos-virtual-instance-id`` 用于多实例场景下的实例隔离
- 该字段可选，仅在部署多实例时需要指定
- 如不指定，则使用默认实例

内容格式Header
^^^^^^^^^^^^^^

所有JSON RPC请求都需要指定Content-Type：

.. code-block:: text

   http headers:
     "Content-Type": "application/json"

最佳实践
~~~~~~~~~~~~

1. **Token刷新策略**

   .. code-block:: text

      • 定期调用 refresh_token 刷新访问令牌
      • access_token 过期时间较短（通常15分钟）
      • refresh_token 过期时间较长（通常7天）
      • 当 access_token 过期时，使用 refresh_token 获取新的 access_token

2. **错误处理**

   .. code-block:: text

      • 收到 401 Unauthorized 时，需要重新登录
      • 收到 403 Forbidden 时，当前用户无权限访问
      • 不要在日志中记录完整的 token 信息

3. **安全建议**

   .. code-block:: text

      • 始终使用 HTTPS 传输认证信息
      • 不要在URL中传递认证信息
      • 定期更新密码，特别是 password_expiry_days 即将到期时
      • 如怀疑 token 泄露，立即登出并重新登录


