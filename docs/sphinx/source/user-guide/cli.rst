命令行示例
==============

本章节介绍QCOS命令行工具（qcos-cli）的常用操作示例，涵盖作业管理、系统信息查询、驱动与设备管理等核心功能。

.. contents:: 目录
   :local:
   :depth: 3

作业命令
-------------

作业命令包含作业提交、作业更新、状态查询、结果获取、取消及删除等操作，是qcos-cli的核心功能模块。

提交作业
***************

提交作业支持不同后端驱动、参数配置及执行模式

*命令行参数*
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 作业提交
   usage: qcos-cli submit-job [-h] [--code-type {qasm,qasm2,qasm3,qubo}] [--job-id JOB_ID]
                              [--circuit-aggregation {None,internal,external}] [-n JOB_NAME] [--job-type {sampling,estimation}]
                              [--job-priority JOB_PRIORITY] [--description DESCRIPTION] [--shots SHOTS] [--backend BACKEND]
                              [--driver-options DRIVER_OPTIONS] [--transpiler TRANSPILER] [--transpiler-options TRANSPILER_OPTIONS]
                              [--profiling [{all,code,scheduling,driver:parse,driver:transpile,driver:run,machine} ...]] [--callbacks CALLBACKS] [-D]
                              -f SOURCE_CODE_FILES [SOURCE_CODE_FILES ...]

   Submit job.

   options:
     -h, --help            show this help message and exit
     --code-type {qasm,qasm2,qasm3,qubo}
                           Code Types: qasm,qasm2,qasm3,qubo
     --job-id JOB_ID
                           Job uuid
     --circuit-aggregation {None,internal,external}
                           Circuit aggregation: None,internal,external
     -n JOB_NAME, --job-name JOB_NAME
                           Job name
     --job-type {sampling,estimation}
                           Job type: sampling,estimation
     --job-priority JOB_PRIORITY
                           Set job priority. Values: 1-10, Default: 5. Highest priority: 1, Lowest Priority: 10
     --description DESCRIPTION
                           Set job description
     --shots SHOTS
                           Shots
     --backend BACKEND
                           Set backend device name. eg: dummy
     --driver-options DRIVER_OPTIONS
                           Set driver options
     --transpiler TRANSPILER
                           Set transpiler name. eg. cmss
     --transpiler-options TRANSPILER_OPTIONS
                           Set transpiler options
     --profiling [{all,code,scheduling,driver:parse,driver:transpile,driver:run,machine} ...]
                           Profiling types: all,code,scheduling,driver:parse,driver:transpile,driver:run,machine
     --callbacks CALLBACKS
                           Callbacks list
     -D, --dry-run         Dry run
     -f SOURCE_CODE_FILES [SOURCE_CODE_FILES ...], --source-code-file SOURCE_CODE_FILES [SOURCE_CODE_FILES ...]
                           Source code file, files can be specified multiple times

*典型场景示例*
~~~~~~~~~~~~~~~

- dummy驱动 (测试用)

.. code-block:: shell

   # 基础提交
   qcos-cli submit-job --code-type qasm --shots 10 --backend dummy -f ./samples/qasm/2.0/simple-qasm.qasm

   # 使用profiling进行模块性能测量
   qcos-cli submit-job --code-type qasm --shots 10 --profiling scheduling driver:parse driver:transpile driver:run --backend dummy -f ./samples/qasm/2.0/simple-qasm.qasm

   # 使用callbacks进行回调
   qcos-cli submit-job --code-type qasm --shots 10 --callbacks '[{"name":"callback","type":"results","method":"post","timeout":4,"retries":3,"headers":{"Content-Type": "application/json","user_id":"qcos"},"url":"http://127.0.0.1:8088/v1/job/set_job_results"}]' --backend dummy -f ./samples/qasm/2.0/simple-qasm.qasm

   # 指定job-id
   qcos-cli submit-job --job-id 00000000-0000-4000-8000-000000000001 --code-type qasm --shots 10 --backend dummy -f ./samples/qasm/2.0/simple-qasm.qasm

   # 指定job名称
   qcos-cli submit-job --job-name test-dummy --code-type qasm --shots 10 --backend dummy -f ./samples/qasm/2.0/simple-qasm.qasm

   # 单作业多代码执行 (线路串行模式)
   qcos-cli submit-job --code-type qasm --shots 10 --backend dummy -f ./samples/qasm/2.0/simple-qasm.qasm ./samples/qasm/2.0/simple-qasm.qasm

   # 多作业并行执行 (线路聚合模式)
   qcos-cli submit-job --code-type qasm --shots 10 --circuit-aggregation internal --backend dummy -f ./samples/qasm/2.0/simple-qasm.qasm ./samples/qasm/2.0/simple-qasm.qasm
   qcos-cli submit-job --code-type qasm --shots 10 --circuit-aggregation external --backend dummy -f ./samples/qasm/2.0/simple-qasm.qasm

   # 设置 等待时长sleep (调试用)
   qcos-cli submit-job --code-type qasm --shots 10 --backend dummy --driver-options '{"sleep": 30}' -f ./samples/qasm/2.0/simple-qasm.qasm

   # 设置 max_qubits
   qcos-cli submit-job --code-type qasm --shots 10 --backend dummy --driver-options '{"max_qubits": 20}' -f ./samples/qasm/2.0/simple-qasm.qasm

   # 设置任务优先级。取值范围1~10，默认优先级为5，最高优先级为1，最低优先级为10
   qcos-cli submit-job --code-type qasm --shots 10 --backend dummy  --job-priority 5 -f ./samples/qasm/2.0/simple-qasm.qasm

   # 开启电路切割
   qcos-cli submit-job --code-type qasm --shots 10 --backend dummy --transpiler-options '{"enable_na_move": true}' --driver-options '{"enable_wirecut":true}' -f ./samples/qasm/2.0/wirecut/12_30.qasm

- qutip驱动 (测试用)

.. code-block:: shell

   # 基础提交
   qcos-cli submit-job --code-type qasm --shots 10 --backend qutip_sim -f ./samples/qasm/2.0/simple-qasm.qasm

- 中科酷原-汉原1 中性原子驱动

.. code-block:: shell

   # 2. 模拟运行(dry-run)
   qcos-cli submit-job --code-type qasm --shots 10 --dry-run --backend hanyuan1 -f ./samples/qasm/2.0/simple-qasm-1-bit.qasm

   # 2.1 模拟运行双量子比特门 (dry-run)
   qcos-cli submit-job --code-type qasm --shots 10 --dry-run --backend hanyuan1 --transpiler-options '{"enable_na_move": true}' -f ./samples/qasm/2.0/rb.qasm

   # 2.2 模拟跳过mapping运行双量子比特门 (dry-run)
   qcos-cli submit-job --code-type qasm --shots 10 --dry-run --backend hanyuan1 --transpiler-options '{"enable_na_move": true, "enable_mapping": false}' -f ./samples/qasm/2.0/rb.qasm

   # 3. 真实运行
   qcos-cli submit-job --code-type qasm --shots 10 --backend hanyuan1 -f ./samples/qasm/2.0/simple-qasm-1-bit.qasm
   qcos-cli submit-job --code-type qasm2 --shots 10 --backend wy-hanyuan1 --transpiler-options '{"enable_mapping": false}' -f ./samples/qasm/2.0/simple-qasm.qasm
   qcos-cli submit-job --code-type qasm2 --shots 10 --backend wy-hanyuan1-sim --transpiler-options '{"enable_mapping": false}' -f ./samples/qasm/2.0/simple-qasm.qasm

   # 4. 电路切割开启 （--driver-options '{"enable_wirecut":true}'）
   qcos-cli submit-job --code-type qasm --shots 10 --backend hanyuan1 --transpiler-options '{"enable_na_move": true}' --driver-options '{"enable_wirecut":true}' -f ./samples/qasm/2.0/wirecut/12_30.qasm

   # 5. 支持不同mapping算法 （--transpiler-options '{"na_mapping_type": "ZAC\ZAP\default",）
   qcos-cli submit-job --code-type qasm --shots 10 --dry-run --backend hanyuan1 --transpiler-options '{"enable_na_move": true, "na_mapping_type": "ZAC"}' -f ./samples/qasm/2.0/rb.qasm
   qcos-cli submit-job --code-type qasm --shots 10 --dry-run --backend hanyuan1 --transpiler-options '{"enable_na_move": true, "na_mapping_type": "ZAP"}' -f ./samples/qasm/2.0/rb.qasm
   qcos-cli submit-job --code-type qasm --shots 10 --dry-run --backend hanyuan1 --transpiler-options '{"enable_na_move": true, "na_mapping_type": "default"}' -f ./samples/qasm/2.0/rb.qasm

- 光量子伊辛机

.. code-block:: shell

   # 真实运行
   qcos-cli submit-job --code-type qubo --backend tiangong100 -f ./samples/qubo/simple-qubo.json
   qcos-cli submit-job --code-type qubo --backend tiangong100 -f ./samples/qubo/simple-qubo.csv
   qcos-cli submit-job --code-type qubo --backend tiangong550_v2 -f ./samples/qubo/simple-qubo.json
   qcos-cli submit-job --code-type qubo --backend tiangong550_v2 -f ./samples/qubo/simple-qubo.csv
   qcos-cli submit-job --code-type qubo --backend tiangong1000_v2 -f ./samples/qubo/simple-qubo.json
   qcos-cli submit-job --code-type qubo --backend tiangong1000_v2 -f ./samples/qubo/simple-qubo.csv
   qcos-cli submit-job --code-type qubo --transpiler cmss_qubo --backend tiangong100 -f ./samples/qubo/simple-qubo.json
   qcos-cli submit-job --code-type qubo --transpiler cmss_qubo --backend tiangong100 -f ./samples/qubo/simple-qubo.csv
   qcos-cli submit-job --code-type qubo --transpiler dummy --backend tiangong550_v2 -f ./samples/qubo/simple-qubo.json
   qcos-cli submit-job --code-type qubo --transpiler dummy --backend tiangong550_v2 -f ./samples/qubo/simple-qubo.csv
   qcos-cli submit-job --code-type qubo --transpiler dummy --backend tiangong1000_v2 -f ./samples/qubo/simple-qubo.json
   qcos-cli submit-job --code-type qubo --transpiler dummy --backend tiangong1000_v2 -f ./samples/qubo/simple-qubo.csv

   # 开启subqubo功能（默认关闭）
   qcos-cli submit-job --code-type qubo --backend tiangong100 --driver-options '{"enable_subqubo": true}' -f ./samples/qubo/qubo_200X200.csv
   qcos-cli submit-job --code-type qubo --transpiler cmss_qubo --backend tiangong100 --driver-options '{"enable_subqubo": true}' -f ./samples/qubo/qubo_200X200.csv

   # 开启降精度功能（默认关闭）
   qcos-cli submit-job --code-type qubo --backend tiangong100 --driver-options '{"enable_prec_reduce": true}' -f ./samples/qubo/qubo_200X200.csv
   qcos-cli submit-job --code-type qubo --transpiler cmss_qubo --backend tiangong100 --driver-options '{"enable_prec_reduce": true}' -f ./samples/qubo/qubo_200X200.csv

- 量旋科技

.. code-block:: shell

   # 量旋科技 真实运行
   qcos-cli submit-job --code-type qasm --shots 10 --backend spinq_rpc -f ./samples/qasm/2.0/simple-qasm.qasm

   # 使用MCTS路由算法并自定义sc_mapping参数
   qcos-cli submit-job \
       -f ./samples/qasm/2.0/benchmark/gcm_h6_2447.qasm \
       --backend spinq_rpc \
       --transpiler cmss \
       --transpiler-options '{"optimization_level": 2, "sc_mapping_options": {"routing_algorithm": "mct", "select_mode": ["KS", 2], "use_prune": 1, "use_hash": 1, "score_layer": 1, "mode_sim": ["fix_cx_num", [10, 3]], "score_decay_rate_size": 0.7, "score_decay_rate_depth": 0.85}}'

   # 使用SABRE路由算法
   qcos-cli submit-job \
       -f ./samples/qasm/2.0/simple-qasm.qasm \
       --backend spinq_rpc \
       --transpiler cmss \
       --transpiler-options '{"sc_mapping_options": {"routing_algorithm": "sabre", "sabre_extention_size": 20, "sabre_weight": 0.5, "sabre_decay": 0.001}}'

- 幺正量子

.. code-block:: shell

   # 幺正量子 真实运行
   qcos-cli submit-job --code-type qasm3 --shots 100 --backend uqc_matrix2 --transpiler-options '{"enable_mapping": false}' -f ./samples/qasm/3.0/simple-qasm-1-bit.qasm

更新作业
***************

更新作业支持对排队中任务修改优先级

*命令行参数*
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 作业更新
   usage: qcos-cli update-job [-h] [--job-priority JOB_PRIORITY] job_id

   Update job.

   positional arguments:
     job_id        Job uuid

   options:
     -h, --help            show this help message and exit
     --job-priority JOB_PRIORITY
                           Set job priority. Values: 1-10, Default: 5. Highest priority: 1, Lowest Priority: 10


*典型场景示例*
~~~~~~~~~~~~~~~

.. code-block:: shell

   qcos-cli update-job --job-priority 3 00000000-0000-4000-8000-000000000001


查询作业
*************************

查询作业的列表、状态和结果

*命令行参数*
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 查询作业列表
   usage: qcos-cli list-jobs [-h] [-f {csv,json,table,value,yaml}] [-c COLUMN] [--quote {all,minimal,none,nonnumeric}] [--noindent]
                            [--max-width <integer>] [--fit-width] [--print-empty] [--sort-column SORT_COLUMN] [--sort-ascending | --sort-descending]

   Get jobs.

   options:
     -h, --help            show this help message and exit

   output formatters:
     output formatter options

     -f {csv,json,table,value,yaml}, --format {csv,json,table,value,yaml}
                           the output format, defaults to table
     -c COLUMN, --column COLUMN
                           specify the column(s) to include, can be repeated to show multiple columns
     --sort-column SORT_COLUMN
                           specify the column(s) to sort the data (columns specified first have a priority, non-existing columns are ignored), can be repeated
     --sort-ascending      sort the column(s) in ascending order
     --sort-descending     sort the column(s) in descending order

.. code-block:: shell

   # 查看作业状态
   usage: qcos-cli get-job-status [-h] [-f {json,shell,table,value,yaml}] [-c COLUMN] [--noindent] [--prefix PREFIX]
                                  [--max-width <integer>] [--fit-width] [--print-empty]
                                  job_id

   Get job status.

   positional arguments:
     job_id        Job ID

.. code-block:: shell

   # 查看作业结果
   usage: qcos-cli get-job-results [-h] [-f {json,shell,table,value,yaml}] [-c COLUMN] [--noindent] [--prefix PREFIX]
                                   [--max-width <integer>] [--fit-width] [--print-empty]
                                   [--outfile OUTFILE]
                                   job_id

   Get job results.

   positional arguments:
     job_id        Job ID

   options:
     -h, --help            show this help message and exit

*典型场景示例*
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 获取作业状态
   qcos-cli get-job-status 00000000-0000-4000-8000-000000000001

   # 获取作业结果
   qcos-cli get-job-results 00000000-0000-4000-8000-000000000001

   # 获取作业结果，并保存为result.txt
   qcos-cli get-job-results --outfile "result.txt" 00000000-0000-4000-8000-000000000001

   # 获取所有作业列表
   qcos-cli list-jobs

作业删除和取消
*************************

作业的删除和取消

*命令行参数*
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 删除作业
   usage: qcos-cli delete-jobs [-h] [-y] job_ids

   Delete jobs.

   positional arguments:
     job_ids  Job IDs

   options:
     -h, --help       show this help message and exit
     -y, --yes        Answer yes for all question

.. code-block:: shell

   # 取消作业
   usage: qcos-cli cancel-jobs [-h] [-y] job_ids

   Cancel jobs.

   positional arguments:
     job_ids  Job IDs

   options:
     -h, --help       show this help message and exit
     -y, --yes        Answer yes for all question

*典型场景示例*
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 取消作业
   qcos-cli cancel-jobs 00000000-0000-4000-8000-000000000001
   qcos-cli cancel-jobs -y all

   # 删除作业
   qcos-cli delete-jobs 00000000-0000-4000-8000-000000000001
   qcos-cli delete-jobs 00000000-0000-4000-8000-000000000001,00000000-0000-4000-8000-000000000002
   qcos-cli delete-jobs -y all

作业结果设置（回调）
******************************

异步回调设置作业结果

*命令行参数*
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 设置作业结果
   usage: qcos-cli set-job-results [-h] --results RESULTS [RESULTS ...] job_id

   Set job results.

   positional arguments:
     job_id        Job ID

   options:
     -h, --help            show this help message and exit
     --results RESULTS [RESULTS ...]
                           Job Results

*典型场景示例*
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 设置单个作业结果
   qcos-cli set-job-results 00000000-0000-4000-8000-000000000001 --results '{"results": {"01":100}, "num_qubits": 2}'

   # 设置多作业结果（针对多源代码作业）
   qcos-cli set-job-results 00000000-0000-4000-8000-000000000001 --results '{"results": {"01":100}, "num_qubits": 2}' '{"code": -104, "message": "error test"}'

版本命令
-------------

查询当前服务端的软件版本、API版本、支持的设备和能力清单

*命令行参数*
***************

.. code-block:: shell

   # 查询服务端版本
   usage: qcos-cli version [-h]

   Get server version.

   options:
     -h, --help  show this help message and exit

*典型场景示例*
***************

.. code-block:: shell

   # 请求服务端版本
   qcos-cli version

系统命令
-------------

系统相关命令

*命令行参数*
***************

.. code-block:: shell

   # 系统服务连通性测试
   usage: qcos-cli ping [-h] message

   Ping-pong to verify the availability of the system.

   positional arguments:
     message  Message to send

   options:
     -h, --help       show this help message and exit

.. code-block:: shell

   # 系统运行信息
   usage: qcos-cli system-info [-h] [-f {json,shell,table,value,yaml}] [-c COLUMN] [--noindent] [--prefix PREFIX]
                               [--max-width <integer>] [--fit-width] [--print-empty]

   Show system information.

   options:
     -h, --help            show this help message and exit

*典型场景示例*
***************

.. code-block:: shell

   # ping命令（测试服务连通性）
   qcos-cli ping 123

   # 获取系统信息
   qcos-cli system-info


系统监控命令
-------------

系统监控指标相关查询命令，包括系统健康状态、API访问统计和作业统计

*命令行参数*
***************

.. code-block:: shell

    # 获取系统健康状态
    usage: qcos-cli get-system-health [-h]

    Get system health status.

    options:
      -h, --help  show this help message and exit

.. code-block:: shell

    # 获取API访问统计
    usage: qcos-cli get-api-stats [-h]

    Get API access statistics.

    options:
      -h, --help  show this help message and exit

.. code-block:: shell

    # 获取作业统计
    usage: qcos-cli get-job-stats [-h]

    Get job statistics.

    options:
      -h, --help  show this help message and exit

*典型场景示例*
***************

.. code-block:: shell

    # 获取系统健康状态，显示各组件的运行状态
    qcos-cli get-system-health

    # 获取API访问统计，包括总请求数、最近一小时和最近一天的请求数
    qcos-cli get-api-stats

    # 获取作业统计，包括总任务数、已完成、失败、运行中等各状态的任务数量
    qcos-cli get-job-stats

驱动命令
-------------

驱动相关的查询命令

*命令行参数*
***************

.. code-block:: shell

   # 查询驱动信息列表
   usage: qcos-cli list-drivers [-h] [-f {csv,json,table,value,yaml}] [-c COLUMN] [--quote {all,minimal,none,nonnumeric}] [--noindent]
                                [--max-width <integer>] [--fit-width] [--print-empty] [--sort-column SORT_COLUMN]
                                [--sort-ascending | --sort-descending]

   Get driver list.

   options:
     -h, --help            show this help message and exit

.. code-block:: shell

   # 查询驱动信息详情
   usage: qcos-cli get-driver [-h] [-f {json,shell,table,value,yaml}] [-c COLUMN] [--noindent] [--prefix PREFIX]
                              [--max-width <integer>] [--fit-width] [--print-empty]
                              driver_name

   Get driver info.

   positional arguments:
     driver_name   Driver name

   options:
     -h, --help            show this help message and exit

*典型场景示例*
***************

.. code-block:: shell

   # 获取所有驱动信息列表
   qcos-cli list-drivers

   # 获取驱动信息详情
   qcos-cli get-driver DriverDummy

设备命令
-------------

设备相关查询和配置命令

*命令行参数*
***************

.. code-block:: shell

   # 查询设备信息列表
   usage: qcos-cli list-devices [-h] [-f {csv,json,table,value,yaml}] [-c COLUMN] [--quote {all,minimal,none,nonnumeric}] [--noindent]
                                [--max-width <integer>] [--fit-width] [--print-empty] [--sort-column SORT_COLUMN]
                                [--sort-ascending | --sort-descending]

   Get device list.

   options:
     -h, --help            show this help message and exit

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

.. code-block:: shell

   # 设备校准
   usage: qcos-cli calibrate-device [-h] [--options OPTIONS] device_name

   Calibrate device.

   positional arguments:
     device_name   Device name

   options:
     -h, --help            show this help message and exit
     --options OPTIONS     Calibration options

.. code-block:: shell

   # 获取设备校准结果
   usage: qcos-cli get-calibrate-results [-h] device_name

   Get calibrate results.

   positional arguments:
     device_name   Device name

   options:
     -h, --help            show this help message and exit

.. code-block:: shell

   # 设置设备选项
   usage: qcos-cli set-device-options [-h] [--options OPTIONS] device_name

   Set device options.

   positional arguments:
     device_name   Device name

   options:
     -h, --help            show this help message and exit
     --options OPTIONS     Device options

.. code-block:: shell

   # 获取设备选项
   usage: qcos-cli get-device-options [-h] device_name

   Get device options.

   positional arguments:
     device_name   Device name

   options:
     -h, --help            show this help message and exit

*典型场景示例*
***************

.. code-block:: shell

   # 获取所有设备信息列表
   qcos-cli list-devices

   # 获取设备信息详情
   qcos-cli get-device dummy

   # 设备校准
   qcos-cli calibrate-device dummy
   qcos-cli calibrate-device dummy --options '{"calibrate_option": "value"}'

   # 获取设备校准结果
   qcos-cli get-calibrate-results dummy

   # 设置设备选项
   qcos-cli set-device-options dummy --options '{"options": "value"}'

   # 获取设备选项
   qcos-cli get-device-options dummy

转译器命令
-------------

转译器相关查询和配置命令

*命令行参数*
***************

.. code-block:: shell

   # 查询转译器信息列表
   usage: qcos-cli list-transpilers [-h] [-f {csv,json,table,value,yaml}] [-c COLUMN] [--quote {all,minimal,none,nonnumeric}] [--noindent]
                                    [--max-width <integer>] [--fit-width] [--print-empty] [--sort-column SORT_COLUMN]
                                    [--sort-ascending | --sort-descending]

   Get transpiler list.

   options:
     -h, --help            show this help message and exit

.. code-block:: shell

   # 查询转译器信息详情
   usage: qcos-cli get-transpiler [-h] [-f {json,shell,table,value,yaml}] [-c COLUMN] [--noindent] [--prefix PREFIX]
                                  [--max-width <integer>] [--fit-width] [--print-empty]
                                  transpiler_name

   Get transpiler info.

   positional arguments:
     transpiler_name
                           Transpiler name

   options:
     -h, --help            show this help message and exit

*典型场景示例*
***************

.. code-block:: shell

   # 获取所有设备信息列表
   qcos-cli list-devices

   # 获取设备信息详情
   qcos-cli get-device dummy

认证命令
----------------------

认证相关命令包含用户登录登出、Token刷新及查询当前用户等操作。

.. note::

   **通用说明**

   - 某些用户和角色相关命令支持双参数模式：可接受 UUID 或名称
   - 例如：``qcos-cli get-user test`` (按名称查询) 或 ``qcos-cli get-user 00000000-0000-4000-8000-000000000001`` (按UUID查询)
   - 系统会自动识别参数类型并执行相关查询

登录
***************

用户登录获取访问令牌

*命令行参数*
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 用户登录
   usage: qcos-cli login [-h] [--access-token] [--refresh-token]
                         username password

   User login to get JWT token.

   positional arguments:
     username              Username
     password              Password

   options:
     -h, --help            show this help message and exit
     --access-token        Only print the access token
     --refresh-token       Only print the refresh token

*典型场景示例*
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 标准登录（显示完整信息）
   qcos-cli login admin 123456

   # 保存access token到环境变量中, 供后续命令认真时使用
   export QCOS_ACCESS_TOKEN=`qcos-cli login admin 123456 --access-token`

   # 只显示访问令牌
   qcos-cli login admin 123456 --access-token

   # 只显示刷新令牌
   qcos-cli login admin 123456 --refresh-token


登出
***************

用户登出清除令牌

*命令行参数*
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 用户登出
   usage: qcos-cli logout [-h]

   User logout.

   options:
     -h, --help  show this help message and exit

*典型场景示例*
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 登出
   qcos-cli logout


刷新令牌
***************

刷新JWT访问令牌

*命令行参数*
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 刷新令牌
   usage: qcos-cli refresh-token [-h] [--refresh-token REFRESH_TOKEN]

   Refresh JWT token.

   options:
     -h, --help                show this help message and exit
     --refresh-token REFRESH_TOKEN
                               Specify refresh_token directly
                               (overrides QCOS_REFRESH_TOKEN environment variable)

*典型场景示例*
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 使用环境变量中的刷新令牌 (refresh token可在login登陆时获取)
   export QCOS_REFRESH_TOKEN=your_refresh_token
   qcos-cli refresh-token

   # 直接指定刷新令牌
   qcos-cli refresh-token --refresh-token eyJ0eXAiOiJKV1QiLCJhbGc...


查询当前用户
***************

显示当前已认证用户的信息

*命令行参数*
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 查询当前用户
   usage: qcos-cli whoami [-h] [-f {json,shell,table,value,yaml}]
                          [-c COLUMN] [--noindent] [--prefix PREFIX]
                          [--max-width <integer>] [--fit-width]
                          [--print-empty]

   Show current authenticated user information.

   options:
     -h, --help            show this help message and exit

*典型场景示例*
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 查询当前认证用户
   qcos-cli whoami


用户管理命令
----------------------

用户管理命令包含用户账户的增删改查、角色的增删改查、权限配置、密码的修改等操作。

.. important::

   **双参数模式说明**

   以下命令支持使用 UUID 或名称来标识用户/角色：

   - 用户命令：``get-user``、``update-user``、``delete-user``、``change-password``
   - 角色命令：``get-role``、``update-role``、``delete-role``

   系统会自动识别参数类型（UUID格式或字符串名称）并执行对应的查询操作。

用户管理状态
***************

获取用户管理系统状态的操作命令

*命令行参数*
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 获取用户管理状态
   usage: qcos-cli get-user-mgmt-status [-h] [-f {json,shell,table,value,yaml}]
                                        [-c COLUMN] [--noindent] [--prefix PREFIX]
                                        [--max-width <integer>] [--fit-width]
                                        [--print-empty]

   Get user management status.

   options:
     -h, --help            show this help message and exit

*典型场景示例*
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 获取用户管理状态
   qcos-cli get-user-mgmt-status

用户创建
***************

创建用户的操作命令

*命令行参数*
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 创建用户
   usage: qcos-cli create-user [-h] [--role-name ROLE_NAMES] [--description DESCRIPTION] [--password-expiry-days PASSWORD_EXPIRY_DAYS] [--disable] [--lock] user_name password

   Create user.

   positional arguments:
     user_name             User name
     password              Password

   options:
     -h, --help            show this help message and exit
     --role-name ROLE_NAMES
                           Role name (can be specified multiple times)
     --description DESCRIPTION
                           Description
     --password-expiry-days PASSWORD_EXPIRY_DAYS
                           Password expiry days (optional, 0: never expired)
     --disable             Disable user account upon creation
     --lock                Lock user account upon creation

*典型场景示例*
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 创建一个普通用户
   qcos-cli create-user test mypassword

   # 创建一个管理员用户
   qcos-cli create-user test1 mypassword --role-name admin

   # 创建一个禁用的用户
   qcos-cli create-user test2 mypassword --disable

   # 创建一个锁定的用户
   qcos-cli create-user test3 mypassword --lock

   # 创建一个密码永不过期的用户
   qcos-cli create-user test4 mypassword --password-expiry-days 0

   # 创建一个完整配置的用户
   qcos-cli create-user test5 mypassword --role-name admin --description "Admin" --password-expiry-days 90 --disable --lock

用户列表查询
***************

查询用户列表的操作命令

*命令行参数*
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 查询用户列表
   usage: qcos-cli list-users [-h] [--user-name USER_NAME]
                              [-f {csv,json,table,value,yaml}] [-c COLUMN]
                              [--quote {all,minimal,none,nonnumeric}] [--noindent]
                              [--max-width <integer>] [--fit-width] [--print-empty]
                              [--sort-column SORT_COLUMN] [--sort-ascending | --sort-descending]

   Get users.

   options:
     -h, --help            show this help message and exit
     --user-name USER_NAME Filter users by user name (optional)

*典型场景示例*
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 查询所有用户列表
   qcos-cli list-users

   # 查询特定用户
   qcos-cli list-users --user-name admin

用户详情查询
***************

查询用户详情的操作命令

*命令行参数*
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 查询用户详情
   usage: qcos-cli get-user [-h] [-f {json,shell,table,value,yaml}] [-c COLUMN] [--noindent] [--prefix PREFIX]
                            [--max-width <integer>] [--fit-width] [--print-empty]
                            user_id

   Get user by ID or name. Can accept either a UUID or a user name as user_id parameter. If a valid UUID is provided, it will be used directly.
   Otherwise, the system will look up the user by name.

   positional arguments:
     user_id       User ID (UUID) or user name

*典型场景示例*
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 查询用户test的详情
   qcos-cli get-user test

用户信息更新
***************

更新用户的操作命令

*命令行参数*
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 更新用户
   usage: qcos-cli update-user [-h] [--role-name ROLE_NAMES]
                               [--password-expiry-days PASSWORD_EXPIRY_DAYS]
                               [--description DESCRIPTION] [--enable] [--disable]
                               [--lock] [--unlock]
                               user_id

   Update user by ID or name.
   Can accept either a UUID or a user name as user_id parameter.
   If a valid UUID is provided, it will be used directly.
   Otherwise, the system will look up the user by name.

   positional arguments:
     user_id               User ID (UUID) or user name

   options:
     -h, --help            show this help message and exit
     --role-name ROLE_NAMES
                           Role names (can be specified multiple times, default: user)
     --password-expiry-days PASSWORD_EXPIRY_DAYS
                           Password expiry days (optional, 0: never expired)
     --description DESCRIPTION
                           Description
     --enable              Enable user account
     --disable             Disable user account
     --lock                Lock user account
     --unlock              Unlock user account

*典型场景示例*
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 更新用户角色和密码过期天数
   qcos-cli update-user test --role-name admin --password-expiry-days 80

   # 启用用户账户
   qcos-cli update-user test --enable

   # 禁用用户账户
   qcos-cli update-user test --disable

   # 锁定用户账户
   qcos-cli update-user test --lock

   # 解锁用户账户
   qcos-cli update-user test --unlock

   # 完整的用户更新示例
   qcos-cli update-user test --role-name admin --password-expiry-days 90 --description "updated admin" --enable --unlock

   # 使用UUID更新用户
   qcos-cli update-user 00000000-0000-4000-8000-000000000001 --enable

用户删除
***************

删除用户的操作命令

*命令行参数*
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 删除用户
   usage: qcos-cli delete-user [-h] [-f/--force] user_id

   Delete user by ID or name.
   Can accept either a UUID or a user name as user_id parameter.
   If a valid UUID is provided, it will be used directly.
   Otherwise, the system will look up the user by name.

   positional arguments:
     user_id       User ID (UUID) or user name

   options:
     -h, --help            show this help message and exit
     -f, --force           Force delete user and cascade delete related resources

*典型场景示例*
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 删除用户：test
   qcos-cli delete-user test

   # 强制删除用户及其相关资源
   qcos-cli delete-user test --force

   # 使用UUID删除用户
   qcos-cli delete-user 00000000-0000-4000-8000-000000000001

用户密码修改
***************

修改用户密码的操作命令

*命令行参数*
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 修改密码
   usage: qcos-cli change-password [-h] user_id old_password new_password

   Change password for user by ID or name.
   Can accept either a UUID or a user name as user_id parameter.
   If a valid UUID is provided, it will be used directly.
   Otherwise, the system will look up the user by name.

   positional arguments:
     user_id       User ID (UUID) or user name
     old_password  Old password
     new_password  New password

   options:
     -h, --help    show this help message and exit

*典型场景示例*
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 修改用户test的密码
   qcos-cli change-password test oldpass123 newpass456

   # 使用UUID修改密码
   qcos-cli change-password 00000000-0000-4000-8000-000000000001 oldpass123 newpass456

登录日志查询
***************

查询用户登录日志的操作命令

*命令行参数*
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 获取登录日志
   usage: qcos-cli list-login-logs [-h] [--user-id USER_ID] [--user-name USER_NAME]
                                   [--limit LIMIT] [--offset OFFSET]
                                   [-f {csv,json,table,value,yaml}] [-c COLUMN]
                                   [--quote {all,minimal,none,nonnumeric}]
                                   [--noindent] [--max-width <integer>]
                                   [--fit-width] [--print-empty]

   Get login logs.

   options:
     -h, --help            show this help message and exit
     --user-id USER_ID     User ID (UUID)
     --user-name USER_NAME User name
     --limit LIMIT         Limit (default: 100)
     --offset OFFSET       Offset (default: 0)

   注意：--user-id 和 --user-name 不能同时指定，请只选择其中一个

*典型场景示例*
~~~~~~~~~~~~~~~

.. code-block:: shell

    # 获取所有登录日志
    qcos-cli list-login-logs

    # 获取特定用户的登录日志
    qcos-cli list-login-logs --user-name admin

    # 获取特定用户ID的登录日志，限制50条
    qcos-cli list-login-logs --user-id 00000000-0000-4000-8000-000000000001 --limit 50

    # 分页查询
    qcos-cli list-login-logs --limit 20 --offset 40

登录日志清空
***************

清空用户登录日志的操作命令

*命令行参数*
~~~~~~~~~~~~~~~

.. code-block:: shell

    # 清空登录日志
    usage: qcos-cli clear-login-logs [-h] [--user-id USER_ID] [--user-name USER_NAME] [--force]

    Clear login logs.

    options:
      -h, --help            show this help message and exit
      --user-id USER_ID     Clear logs for a specific user ID (UUID)
      --user-name USER_NAME Clear logs for a specific user name
      --force               Skip confirmation prompt

    注意：--user-id 和 --user-name 不能同时指定，请只选择其中一个

*典型场景示例*
~~~~~~~~~~~~~~~

.. code-block:: shell

    # 清空所有登录日志（需要确认）
    qcos-cli clear-login-logs

    # 清空所有登录日志（跳过确认）
    qcos-cli clear-login-logs --force

    # 清空特定用户的登录日志
    qcos-cli clear-login-logs --user-name admin

    # 清空特定用户ID的登录日志，跳过确认
    qcos-cli clear-login-logs --user-id 00000000-0000-4000-8000-000000000001 --force

角色管理命令
***************

角色相关的增删改查操作

角色创建
~~~~~~~~~~~~~~~~~

创建角色的操作命令

*命令行参数*
~~~~~~~~~~~~

.. code-block:: shell

   # 创建角色
   usage: qcos-cli create-role [-h] [--description DESCRIPTION]
                               role_name permissions

   Create role.

   positional arguments:
     role_name             Role name
     permissions           Permissions (JSON array, e.g., '["api/path1", "api/path2"]')

   options:
     -h, --help            show this help message and exit
     --description DESCRIPTION
                           Role description

*典型场景示例*
~~~~~~~~~~~~~~~~~~~~

.. code-block:: shell

   # 创建一个只读用户角色
   qcos-cli create-role viewer '["/version", "/v1/driver/get_drivers"]' --description "Read-only user"

角色列表查询
~~~~~~~~~~~~~~~~~

查询所有角色的操作命令

*命令行参数*
~~~~~~~~~~~~

.. code-block:: shell

   # 查询角色列表
   usage: qcos-cli list-roles [-h] [--role-name ROLE_NAME]
                              [-f {csv,json,table,value,yaml}] [-c COLUMN]
                              [--quote {all,minimal,none,nonnumeric}]
                              [--noindent] [--max-width <integer>]
                              [--fit-width] [--print-empty]
                              [--sort-column SORT_COLUMN]
                              [--sort-ascending | --sort-descending]

   Get roles.

   options:
      -h, --help            show this help message and exit
      --role-name ROLE_NAME Filter roles by role name

*典型场景示例*
~~~~~~~~~~~~~~~~~~~~

.. code-block:: shell

   # 查询所有角色
   qcos-cli list-roles

   # 查询特定角色
   qcos-cli list-roles --role-name admin

角色详情查询
~~~~~~~~~~~~~~~~~

查询角色详情的操作命令

*命令行参数*
~~~~~~~~~~~~

.. code-block:: shell

   # 查询角色详情
   usage: qcos-cli get-role [-h] [-f {json,shell,table,value,yaml}]
                            [-c COLUMN] [--noindent] [--prefix PREFIX]
                            [--max-width <integer>] [--fit-width]
                            [--print-empty]
                            role_id

   Get role by ID or name.
   Can accept either a UUID or a role name as role_id parameter.
   If a valid UUID is provided, it will be used directly.
   Otherwise, the system will look up the role by name.

   positional arguments:
     role_id       Role ID (UUID) or role name

*典型场景示例*
~~~~~~~~~~~~~~~~~~~~

.. code-block:: shell

   # 查询admin角色的详情
   qcos-cli get-role admin

   # 使用UUID查询角色详情
   qcos-cli get-role 00000000-0000-4000-8000-000000000002

角色更新
~~~~~~~~~~~~~~~

更新角色的操作命令

*命令行参数*
~~~~~~~~~~~~

.. code-block:: shell

   # 更新角色
   usage: qcos-cli update-role [-h] [--permissions PERMISSIONS]
                               [--description DESCRIPTION]
                               role_id

   Update role by ID or name.
   Can accept either a UUID or a role name as role_id parameter.
   If a valid UUID is provided, it will be used directly.
   Otherwise, the system will look up the role by name.

   positional arguments:
     role_id               Role ID (UUID) or role name

   options:
     -h, --help            show this help message and exit
     --permissions PERMISSIONS
                           Permissions (JSON array, e.g., '["api/path1", "api/path2"]')
     --description DESCRIPTION
                           Role description

*典型场景示例*
~~~~~~~~~~~~~~~~~~~~

.. code-block:: shell

   # 更新角色权限
   qcos-cli update-role admin --permissions '["/version"]'

   # 更新角色描述
   qcos-cli update-role viewer --description "Read-only viewer role"

   # 同时更新权限和描述
   qcos-cli update-role viewer --permissions '["/version", "/v1/driver/get_drivers"]' --description "Editor role"

角色删除
~~~~~~~~~~~~~~~

删除角色的操作命令

*命令行参数*
~~~~~~~~~~~~

.. code-block:: shell

   # 删除角色
   usage: qcos-cli delete-role [-h] role_id

   Delete role by ID or name.
   Can accept either a UUID or a role name as role_id parameter.
   If a valid UUID is provided, it will be used directly.
   Otherwise, the system will look up the role by name.

   positional arguments:
     role_id       Role ID (UUID) or role name

   options:
     -h, --help    show this help message and exit

*典型场景示例*
~~~~~~~~~~~~~~~~~~~~

.. code-block:: shell

   # 删除一个角色
   qcos-cli delete-role viewer

   # 使用UUID删除角色
   qcos-cli delete-role 00000000-0000-4000-8000-000000000003
