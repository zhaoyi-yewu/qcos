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
