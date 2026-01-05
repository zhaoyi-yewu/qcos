运维问题
==============

本章节介绍了运维方面的问题。

.. contents:: 目录
   :local:
   :depth: 3

检查容器启动失败原因？
--------------------------------
- 检查 Docker 状态

.. code-block:: shell

    systemctl status docker

- 查看容器启动日志

.. code-block:: shell

    docker logs qcos
    或者
    docker logs qcos-dev

如何查看API日志？
--------------------------------
.. code-block:: shell

    tail -f /var/log/qcos/qcos-api.log
    或者
    cat /var/log/qcos/qcos-api.log | grep ERROR

如何查看引擎或者驱动执行报错问题？
------------------------------------
.. code-block:: shell

    tail -f /var/log/qcos/qcos-engine.log
    或者
    cat /var/log/qcos/qcos-engine.log | grep ERROR
