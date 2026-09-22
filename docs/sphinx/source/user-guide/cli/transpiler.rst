转译器命令
----------------------

转译器命令用于查询转译器信息列表和转译器详情。

转译器列表查询
***************

查询所有转译器信息列表

命令行参数
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 查询转译器信息列表
   usage: qcos-cli list-transpilers [-h] [-f {csv,json,table,value,yaml}] [-c COLUMN] [--quote {all,minimal,none,nonnumeric}] [--noindent]
                                     [--max-width <integer>] [--fit-width] [--print-empty] [--sort-column SORT_COLUMN]
                                     [--sort-ascending | --sort-descending]

   Get transpiler list.

典型场景示例
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 查询所有转译器信息列表
   qcos-cli list-transpilers

转译器详情查询
***************

查询转译器信息详情

命令行参数
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 查询转译器信息详情
   usage: qcos-cli get-transpiler [-h] [-f {json,shell,table,value,yaml}] [-c COLUMN] [--noindent] [--prefix PREFIX]
                                  [--max-width <integer>] [--fit-width] [--print-empty]
                                  transpiler_name

   Get transpiler info.

   positional arguments:
     transpiler_name   Transpiler name

典型场景示例
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 查询转译器 cmss 的详情
   qcos-cli get-transpiler cmss

分页、排序与过滤
~~~~~~~~~~~~~~~~

所有 list 命令均支持以下服务端参数：

.. code-block:: shell

    # 分页查询（第1页，每页20条）
    qcos-cli list-transpilers --page 1 --page-size 20

    # 获取全部记录（不分页）
    qcos-cli list-transpilers --page-size -1

    # 按字段排序（'-'前缀表示降序）
    qcos-cli list-transpilers --sort=-name

    # 多字段排序
    qcos-cli list-transpilers --sort=-name,version

    # 服务端过滤（key=value，可重复）
    qcos-cli list-transpilers --filter name=example

    # 多条件过滤
    qcos-cli list-transpilers --filter name=example --filter enable=true
