驱动命令
----------------------

驱动命令用于查询驱动信息列表和驱动详情。

驱动列表查询
***************

查询所有驱动信息列表

命令行参数
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 查询驱动信息列表
   usage: qcos-cli list-drivers [-h] [-f {csv,json,table,value,yaml}] [-c COLUMN] [--quote {all,minimal,none,nonnumeric}] [--noindent]
                                [--max-width <integer>] [--fit-width] [--print-empty] [--sort-column SORT_COLUMN]
                                [--sort-ascending | --sort-descending]

   Get driver list.

典型场景示例
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 查询所有驱动信息列表
   qcos-cli list-drivers

驱动详情查询
***************

查询驱动信息详情

命令行参数
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 查询驱动信息详情
   usage: qcos-cli get-driver [-h] [-f {json,shell,table,value,yaml}] [-c COLUMN] [--noindent] [--prefix PREFIX]
                              [--max-width <integer>] [--fit-width] [--print-empty]
                              driver_name

   Get driver info.

   positional arguments:
     driver_name   Driver name

典型场景示例
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 查询驱动 DriverDummy 的详情
   qcos-cli get-driver DriverDummy
