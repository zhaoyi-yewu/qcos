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

返回结果中还包含 ``metrics`` 字典，其中包含设备上线率（availability rate）
相关指标：

- ``metrics.availability_hourly``：当前小时实时上线率
  （``online``/``busy`` 采样数 / 总采样数），取值 ``0.0``~``1.0``；
  当前小时尚无采样时为 ``null``。
- ``metrics.availability_last_hour``：上一个整点小时的聚合上线率，
  来源于 ``device_availability_hourly`` 表；无历史记录时为 ``null``。
- ``metrics.availability_history``：最近若干小时的上线率历史列表，
  用于查看可用性趋势；无历史记录时为 ``null``。

.. code-block:: shell

   # 以 JSON 格式输出，查看 job_count 与 metrics.availability 明细
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

set-device
^^^^^^^^^^

设置设备属性（状态、启用/禁用、最大比特数、可用比特数）。至少指定
``--state``、``--enable``、``--max-qubits`` 或 ``--available-qubits``
中的一个参数。

需要 admin 角色权限。

命令行参数
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 设置设备属性
   usage: qcos-cli set-device [-h]
       [--state {auto,online,offline,busy,disconnected,calibrating,maintain,unknown}]
       [--enable {true,false}]
       [--max-qubits MAX_QUBITS]
       [--available-qubits AVAILABLE_QUBITS]
       BACKEND

   Set device attributes (state, enable, max_qubits,
   available_qubits).

   positional arguments:
     BACKEND               Device name (backend)

   options:
     -h, --help            show this help message and exit
     --state {auto,online,offline,busy,disconnected,calibrating,maintain,unknown}
                           Device state
     --enable {true,false}
                           Enable or disable the device
     --max-qubits MAX_QUBITS
                           Max qubits: 'auto' or a positive integer
     --available-qubits AVAILABLE_QUBITS
                           Available qubits: 'auto' or a positive
                           integer

典型场景示例
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 设置设备状态为在线
   qcos-cli set-device hanyuan1 --state online

   # 设置设备状态为维护
   qcos-cli set-device hanyuan1 --state maintain

   # 恢复为自动状态（使用内存监控状态）
   qcos-cli set-device hanyuan1 --state auto

   # 禁用设备
   qcos-cli set-device hanyuan1 --enable false

   # 设置最大比特数为 100
   qcos-cli set-device hanyuan1 --max-qubits 100

   # 恢复驱动声明的默认最大比特数
   qcos-cli set-device hanyuan1 --max-qubits auto

   # 设置可用比特数为 50
   qcos-cli set-device hanyuan1 --available-qubits 50

   # 恢复驱动声明的默认可用比特数
   qcos-cli set-device hanyuan1 --available-qubits auto

   # 组合设置
   qcos-cli set-device hanyuan1 --state online --enable true --max-qubits auto

分页、排序与过滤
~~~~~~~~~~~~~~~~

所有 list 命令均支持以下服务端参数：

.. code-block:: shell

    # 分页查询（第1页，每页20条）
    qcos-cli list-devices --page 1 --page-size 20

    # 获取全部记录（不分页）
    qcos-cli list-devices --page-size -1

    # 按字段排序（'-'前缀表示降序）
    qcos-cli list-devices --sort=-name

    # 多字段排序
    qcos-cli list-devices --sort=-name,max_qubits

    # 服务端过滤（key=value，可重复）
    qcos-cli list-devices --filter name=dummy

    # 多条件过滤
    qcos-cli list-devices --filter name=dummy --filter status=online
