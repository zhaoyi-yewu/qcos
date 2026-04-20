通用认证HTTP头
====================

通用认证HTTP头用于通过HTTP Header，传递认证信息。

用户认证头
------------

JWT认证
^^^^^^^^^^^^^^

JSON RPC的HTTP Header中添加Authorization头，用于JWT认证。

.. code-block:: text

   http headers:
     "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

虚拟实例认证
^^^^^^^^^^^^^^

JSON RPC的HTTP Header中添加x-qcos-virtual-instance-id, 可以用来区分量子计算机虚拟实例

.. code-block:: text

   http headers:
     "x-qcos-virtual-instance-id": "xxxxx-xxxx"
