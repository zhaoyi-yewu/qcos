设备命令
----------------------

设备命令用于查询设备信息、设备校准和设备选项管理。

设备列表查询
***************

查询所有设备信息列表

命令行参数
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 查询设备信息列表
   usage: qcos-cli list-devices [-h] [-f {csv,json,table,value,yaml}] [-c COLUMN] [--quote {all,minimal,none,nonnumeric}] [--noindent]
                                [--max-width <integer>] [--fit-width] [--print-empty] [--sort-column SORT_COLUMN]
                                [--sort-ascending | --sort-descending]

   Get device list.

   options:
     -h, --help            show this help message and exit

典型场景示例
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 获取所有设备信息列表
   qcos-cli list-devices

设备详情查询
***************

查询设备信息详情

命令行参数
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 查询设备信息详情
   usage: qcos-cli get-device [-h] [-f {json,shell,table,value,yaml}] [-c COLUMN] [--noindent] [--prefix PREFIX]
                              [--max-width <integer>] [--fit-width] [--print-empty]
                              device_name

   Get device info.

   positional arguments:
     device_name   Device name

   options:
     -h, --help            show this help message and exit

典型场景示例
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 获取设备 dummy 的详情
   qcos-cli get-device dummy

返回结果中包含 ``job_count`` 字段，按作业状态（UNKNOWN、QUEUED、
RUNNING、FAILED、COMPLETED、CANCELLING、CANCELLED、DELETING、
DELETED）统计该设备上各状态的作业数量，数据来源于 qcos 数据库。

.. code-block:: shell

   # 以 JSON 格式输出，查看 job_count 明细
   qcos-cli get-device dummy -f json

设备校准
***************

对设备进行校准操作

命令行参数
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 设备校准
   usage: qcos-cli calibrate-device [-h] [--options OPTIONS] device_name

   Calibrate device.

   positional arguments:
     device_name   Device name

   options:
     -h, --help            show this help message and exit
     --options OPTIONS     Calibration options

典型场景示例
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 设备校准
   qcos-cli calibrate-device dummy
   qcos-cli calibrate-device dummy --options '{"calibrate_option": "value"}'

校准结果查询
***************

获取设备校准结果

命令行参数
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 获取设备校准结果
   usage: qcos-cli get-calibrate-results [-h] device_name

   Get calibrate results.

   positional arguments:
     device_name   Device name

   options:
     -h, --help            show this help message and exit

典型场景示例
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 获取设备 dummy 的校准结果
   qcos-cli get-calibrate-results dummy

设备选项设置
***************

设置设备选项

命令行参数
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 设置设备选项
   usage: qcos-cli set-device-options [-h] [--options OPTIONS] device_name

   Set device options.

   positional arguments:
     device_name   Device name

   options:
     -h, --help            show this help message and exit
     --options OPTIONS     Device options

典型场景示例
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 设置设备 dummy 的选项
   qcos-cli set-device-options dummy --options '{"options": "value"}'

设备选项查询
***************

获取设备选项

命令行参数
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 获取设备选项
   usage: qcos-cli get-device-options [-h] device_name

   Get device options.

   positional arguments:
     device_name   Device name

   options:
     -h, --help            show this help message and exit

典型场景示例
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 获取设备 dummy 的选项
   qcos-cli get-device-options dummy

设置设备维护模式
********************

将设备设为维护模式或恢复在线模式。设备处于维护模式时，设备监控进程不会覆盖其维护状态。

需要 admin 角色权限。

命令行参数
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 设置设备维护模式
   usage: qcos-cli set-device-maintain-mode [-h] [--backend BACKEND] {on,off}

   Set device maintain mode (on/off).

   positional arguments:
     {on,off}              Maintain mode: on (set to maintain) or off (set to online)

   options:
     -h, --help            show this help message and exit
     --backend BACKEND     Device name (backend) (required)

典型场景示例
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 将设备 hanyuan1 设为维护模式
   qcos set-device-maintain-mode on --backend hanyuan1

   # 将设备 hanyuan1 恢复在线模式
   qcos set-device-maintain-mode off --backend hanyuan1
