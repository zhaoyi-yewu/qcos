系统管理命令
----------------------

系统管理命令用于系统配置、服务连通性测试和运行信息查询。

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

内存占用查询
***************

查询API服务端进程的内存占用情况，包括RSS内存、虚拟内存、线程数、GC跟踪对象数和CPU使用率。需要管理员权限。

命令行参数
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 内存占用查询
   usage: qcos-cli show-mem [-h] [-f {json,shell,table,value,yaml}] [-c COLUMN] [--noindent] [--prefix PREFIX]
                            [--max-width <integer>] [--fit-width] [--print-empty]

   Show memory usage of the API server process.

典型场景示例
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 查询服务端内存占用
   qcos-cli show-mem

手动垃圾回收
***************

手动触发Python垃圾回收（GC），用于调试内存问题。可指定回收的代数（0、1、2），默认全量回收（2）。需要管理员权限。

命令行参数
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 手动垃圾回收
   usage: qcos-cli gc-mem [-h] [--generations {0,1,2}]

   Manually trigger garbage collection.

   optional arguments:
     --generations {0,1,2}  GC generations to collect (0, 1, 2). Default: 2

典型场景示例
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 全量垃圾回收（默认）
   qcos-cli gc-mem

   # 仅回收第0代对象
   qcos-cli gc-mem --generations 0

内存分配追踪
***************

通过tracemalloc追踪Python内存分配，返回当前/峰值内存及Top内存分配统计。支持三种操作：snapshot（快照）、stop（停止追踪）、clear（清空追踪）。需要管理员权限。

.. note::
   tracemalloc启动后会对每次内存分配产生额外开销，建议调试完成后用 ``--action stop`` 关闭。

命令行参数
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 内存分配追踪
   usage: qcos-cli trace-mem [-h] [--action {snapshot,stop,clear}] [--nframe NFRAME]
                             [--sort-count]

   Trace memory allocations via tracemalloc.

   optional arguments:
     --action {snapshot,stop,clear}  Action: snapshot (default), stop, or clear
     --nframe NFRAME                 Number of top memory allocations to show
                                     (only for snapshot). Default: 25
     --sort-count                    Sort top memory allocations by count
                                     (descending) instead of by size. Only
                                     for snapshot. Default: False

典型场景示例
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 1. 开启追踪并获取内存快照（若未启动则自动启动，默认显示Top 25）
   qcos-cli trace-mem

   # 2. 指定显示Top 10内存分配
   qcos-cli trace-mem --nframe 10

   # 3. 按分配次数（降序）排序展示Top内存分配
   #    默认按分配大小排序，加上 --sort-count 后改为按分配次数排序
   #    适用于定位频繁分配小块内存导致的内存碎片/性能问题
   qcos-cli trace-mem --sort-count

   # 3.1 按分配次数排序并显示Top 10
   qcos-cli trace-mem --sort-count --nframe 10

   # 4. 清空追踪记录（保持追踪状态，重置统计基准）
   qcos-cli trace-mem --action clear

   # 5. 停止追踪并释放所有追踪记录（调试完成后关闭，消除性能开销）
   qcos-cli trace-mem --action stop
