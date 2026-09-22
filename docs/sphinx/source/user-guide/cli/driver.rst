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

分页、排序与过滤
~~~~~~~~~~~~~~~~

所有 list 命令均支持以下服务端参数：

.. code-block:: shell

    # 分页查询（第1页，每页20条）
    qcos-cli list-drivers --page 1 --page-size 20

    # 获取全部记录（不分页）
    qcos-cli list-drivers --page-size -1

    # 按字段排序（'-'前缀表示降序）
    qcos-cli list-drivers --sort=-name

    # 多字段排序
    qcos-cli list-drivers --sort=-name,tech_type

    # 服务端过滤（key=value，可重复）
    qcos-cli list-drivers --filter name=DriverQutipSim

    # 多条件过滤
    qcos-cli list-drivers --filter name=DriverQutipSim --filter tech_type=generic_simulator
