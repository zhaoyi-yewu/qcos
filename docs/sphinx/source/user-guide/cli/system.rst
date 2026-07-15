系统命令
----------------------

系统命令用于系统服务连通性测试和运行信息查询。

连通性测试
***************

测试系统服务连通性

命令行参数
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 系统服务连通性测试
   usage: qcos-cli ping [-h] message

   Ping-pong to verify the availability of the system.

   positional arguments:
     message       Ping message

典型场景示例
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 测试系统连通性
   qcos-cli ping hello

系统信息查询
***************

查询系统运行信息

命令行参数
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 系统运行信息
   usage: qcos-cli system-info [-h] [-f {json,shell,table,value,yaml}] [-c COLUMN] [--noindent] [--prefix PREFIX]
                               [--max-width <integer>] [--fit-width] [--print-empty]

   Get system info.

典型场景示例
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 查询系统运行信息
   qcos-cli system-info
