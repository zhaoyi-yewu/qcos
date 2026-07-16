系统监控命令
----------------------

系统监控命令用于查询系统健康状态、API访问统计和作业统计等信息。

系统健康状态
***************

查询系统健康状态

命令行参数
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 获取系统健康状态
   usage: qcos-cli get-system-health [-h]

   Get system health status.

典型场景示例
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 查询系统健康状态
   qcos-cli get-system-health

API访问统计
***************

查询API访问统计信息

命令行参数
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 获取API访问统计
   usage: qcos-cli get-api-stats [-h]

   Get API access statistics.

典型场景示例
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 查询API访问统计
   qcos-cli get-api-stats

作业统计
***************

查询作业统计信息

命令行参数
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 获取作业统计
   usage: qcos-cli get-job-stats [-h]

   Get job statistics.

典型场景示例
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 查询作业统计
   qcos-cli get-job-stats
