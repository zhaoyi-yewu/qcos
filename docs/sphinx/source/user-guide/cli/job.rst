作业命令
-------------

作业命令包含作业提交、作业更新、状态查询、结果获取、取消及删除等操作，是qcos-cli的核心功能模块。

提交作业
***************

提交作业支持不同后端驱动、参数配置及执行模式

命令行参数
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 作业提交
   usage: qcos-cli submit-job [-h] [--code-type {qasm,qasm2,qasm3,qubo}] [--job-id JOB_ID]
                              [--circuit-aggregation {None,internal,external}] [-n JOB_NAME] [--job-type {sampling,estimation}]
                              [--job-priority JOB_PRIORITY] [--description DESCRIPTION] [--shots SHOTS]
                              [--backend BACKEND] [--driver-options DRIVER_OPTIONS] [--transpiler TRANSPILER]
                              [--transpiler-options TRANSPILER_OPTIONS]
                              [--profiling [{all,code,queuing,scheduling,driver:parse,driver:transpile,driver:run,machine} ...]]
                              [--callbacks CALLBACKS] [-D] [--qec-options QEC_OPTIONS] -f SOURCE_CODE_FILES [SOURCE_CODE_FILES ...]

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
                           Set transpiler name.
     --transpiler-options TRANSPILER_OPTIONS
                           Set transpiler options
     --profiling [{all,code,queuing,scheduling,driver:parse,driver:transpile,driver:run,machine} ...]
                           Profiling types: all,code,queuing,scheduling,driver:parse,driver:transpile,driver:run,machine
     --qec-options QEC_OPTIONS
                           Set qec options
     --callbacks CALLBACKS
                           Callbacks list
     -D, --dry-run         Dry run
     -f SOURCE_CODE_FILES [SOURCE_CODE_FILES ...], --source-code-file SOURCE_CODE_FILES [SOURCE_CODE_FILES ...]
                           Source code files (space-separated, at least one required)

典型场景示例
~~~~~~~~~~~~~~~

- dummy驱动 (测试用)

.. code-block:: shell

   # 基础提交
   qcos-cli submit-job --code-type qasm --shots 10 --backend dummy -f ./samples/qasm/2.0/simple-qasm.qasm

   # 使用profiling进行模块性能测量
   qcos-cli submit-job --code-type qasm --shots 10 --profiling queuing scheduling driver:parse driver:transpile driver:run --backend dummy -f ./samples/qasm/2.0/simple-qasm.qasm

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
   qcos-cli submit-job --code-type qasm --shots 10 --backend quafu --driver-options '{"enable_wirecut":true, "wirecut_qubit_width": 10}' -f ./samples/qasm/2.0/wirecut/12_30.qasm

- 自动调度 (不指定backend，由系统自动选择设备)

.. code-block:: shell

   # 使用 extra_specs 自动调度
   qcos-cli submit-job --code-type qasm --shots 10 --extra-specs '{"max_qubits": 100}' -f ./samples/qasm/2.0/simple-qasm.qasm

   # 使用 flavor_id 自动调度
   qcos-cli submit-job --code-type qasm --shots 10 --flavor-id 00000000-0000-4000-8000-000000000001 -f ./samples/qasm/2.0/simple-qasm.qasm

- Flavor管理 (预设调度策略)

.. code-block:: shell

   # 创建 Flavor
   qcos-cli create-flavor q-flavor-sc --specs '{"min_qubits": 16, "tech_type": "superconducting", "gate_fidelity_2q_min": 0.995}'

   # 查看 Flavor 列表
   qcos-cli list-flavors

   # 查看单个 Flavor
   qcos-cli get-flavor 00000000-0000-4000-8000-000000000001

   # 删除 Flavor
   qcos-cli delete-flavor 00000000-0000-4000-8000-000000000001 -y

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
   qcos-cli submit-job --code-type qasm2 --shots 10 --backend wy_hanyuan1 --transpiler-options '{"enable_mapping": false}' -f ./samples/qasm/2.0/simple-qasm.qasm
   qcos-cli submit-job --code-type qasm2 --shots 10 --backend wy_hanyuan1_sim --transpiler-options '{"enable_mapping": false}' -f ./samples/qasm/2.0/simple-qasm.qasm
   qcos-cli submit-job --code-type qasm --shots 10 --backend hanyuan1_pulse --transpiler-options '{"enable_mapping": false}' -f ./samples/qasm/2.0/simple-qasm-1-bit.qasm

   # 4. 电路切割
   # 4.1 电路切割开启 （--driver-options '{"enable_wirecut":true}'）
   qcos-cli submit-job --code-type qasm --shots 10 --backend hanyuan1 --transpiler-options '{"enable_na_move": true}' --driver-options '{"enable_wirecut":true}' -f ./samples/qasm/2.0/wirecut/12_30.qasm
   # 4.2 电路切割开启，手动设置切割宽度 （--driver-options '{"enable_wirecut":true， "wirecut_qubit_width": 2}'）
   qcos-cli submit-job --code-type qasm --shots 10 --backend hanyuan1 --transpiler-options '{"enable_na_move": true}' --driver-options '{"enable_wirecut":true, "wirecut_qubit_width": 2}' -f ./samples/qasm/2.0/wirecut/3_8.qasm

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

- 夸父 超导量子计算机

.. code-block:: shell

   # 夸父 超导量子计算机 真实运行
   qcos-cli submit-job --code-type qasm --shots 1024 --backend quafu -f ./samples/qasm/2.0/simple-qasm.qasm

- 逻辑比特 超导量子计算机

.. code-block:: shell

   # 逻辑比特 超导量子计算机 真实运行
   qcos-cli submit-job --code-type qasm --shots 100 --backend logical_qubit -f ./samples/qasm/2.0/simple-qasm.qasm

- stim 驱动 (量子纠错用)

.. code-block:: shell

   qcos-cli submit-job --code-type qasm2 --shots 100 --backend stim --transpiler-options '{"enable_mapping": false}' --qec-options '{"qec_code": "shor", "distance": 3, "phy_bit_num": 9, "logical_bit_num": 1}' -f ./samples/qasm/2.0/simple-qasm-1-bit.qasm

   # 指定错误注入类型和噪声概率
   qcos-cli submit-job --code-type qasm2 --shots 100 --backend stim --transpiler-options '{"enable_mapping": false}' --qec-options '{"qec_code": "shor", "error_inject": {"error_type": "x_error", "noise_prob": 0.05}}' -f ./samples/qasm/2.0/simple-qasm-1-bit.qasm
   qcos-cli submit-job --code-type qasm2 --shots 100 --backend stim --transpiler-options '{"enable_mapping": false}' --qec-options '{"qec_code": "shor", "error_inject": {"error_type": "y_error", "noise_prob": 0.02}}' -f ./samples/qasm/2.0/simple-qasm-1-bit.qasm
   qcos-cli submit-job --code-type qasm2 --shots 100 --backend stim --transpiler-options '{"enable_mapping": false}' --qec-options '{"qec_code": "shor", "error_inject": {"error_type": "z_error", "noise_prob": 0.03}}' -f ./samples/qasm/2.0/simple-qasm-1-bit.qasm
   qcos-cli submit-job --code-type qasm2 --shots 100 --backend stim --transpiler-options '{"enable_mapping": false}' --qec-options '{"qec_code": "shor", "error_inject": {"error_type": "random", "noise_prob": 0.01}}' -f ./samples/qasm/2.0/simple-qasm-1-bit.qasm


更新作业
***************

更新作业支持对排队中任务修改优先级

命令行参数
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 作业更新
   usage: qcos-cli update-job [-h] [--job-name JOB_NAME] [--description DESCRIPTION] [--job-priority JOB_PRIORITY] job_id

   Update job.

   positional arguments:
     job_id        Job uuid

   options:
     -h, --help            show this help message and exit
     --job-name JOB_NAME
                           Set job name
     --description DESCRIPTION
                           Set job description
     --job-priority JOB_PRIORITY
                           Set job priority. Values: 1-10, Default: 5. Highest priority: 1, Lowest Priority: 10


典型场景示例
~~~~~~~~~~~~~~~

.. code-block:: shell

   qcos-cli update-job --job-name "My Updated Job" --description "Updated description" --job-priority 3 00000000-0000-4000-8000-000000000001


查询作业
*************************

查询作业的列表、状态和结果

命令行参数
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 查询作业列表
   usage: qcos-cli list-jobs [-h] [-f {csv,json,table,value,yaml}] [-c COLUMN] [--quote {all,minimal,none,nonnumeric}]
   [--noindent] [--max-width <integer>] [--fit-width] [--print-empty] [--sort-column SORT_COLUMN]
   [--sort-ascending | --sort-descending] [--all-projects] [--all-users] [--project-id PROJECT_ID]
   [--user-id USER_ID] [--job-ids [JOB_IDS ...]]

   Get jobs.

   options:
   -h, --help            show this help message and exit
   --all-projects        All projects
   --all-users           All users from same projects
   --project-id PROJECT_ID
   Filter by project ID
   --user-id USER_ID
   Filter by user ID
   --job-ids [JOB_IDS ...]
   Filter by job IDs (space-separated)

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
                                   [--output-file OUTPUT_FILE]
                                   job_id

   Get job results.

   positional arguments:
     job_id        Job ID
     output-file   save job results to file

   output formatters:
     output formatter options
     -f {csv,json,table,value,yaml}, --format {csv,json,table,value,yaml}
                           the output format, defaults to table

   options:
     -h, --help            show this help message and exit

典型场景示例
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 获取所有作业列表
   qcos-cli list-jobs

   # 获取所有作业列表 (带job id列表过滤参数)
   qcos-cli list-jobs --job-ids 8d0da177-8d8e-4882-a6b5-2c2bf6140fcb 7b960693-0a1f-4e44-b824-3edc51b57227

   # 获取作业状态
   qcos-cli get-job-status 00000000-0000-4000-8000-000000000001

   # 获取作业结果
   qcos-cli get-job-results 00000000-0000-4000-8000-000000000001

   # 获取作业结果，并保存为results.yaml
   qcos-cli get-job-results 00000000-0000-4000-8000-000000000001 -f yaml --output-file results.yaml -y

作业删除和取消
*************************

作业的删除和取消

命令行参数
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 删除作业
   usage: qcos-cli delete-jobs [-h] [-y] [-f] job_ids

   Delete jobs.

   positional arguments:
   job_ids  Job IDs

   options:
   -h, --help       show this help message and exit
   -y, --yes        Answer yes for all question
   -f, --force      Force delete jobs regardless of status


.. code-block:: shell

   # 取消作业
   usage: qcos-cli cancel-jobs [-h] [-y] job_ids

   Cancel jobs.

   positional arguments:
     job_ids  Job IDs

   options:
     -h, --help       show this help message and exit
     -y, --yes        Answer yes for all question

典型场景示例
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 删除作业
   qcos-cli delete-jobs 00000000-0000-4000-8000-000000000001
   qcos-cli delete-jobs 00000000-0000-4000-8000-000000000001,00000000-0000-4000-8000-000000000002
   qcos-cli delete-jobs -y all

   # 强制删除作业
   qcos-cli delete-jobs -f -y all

   # 取消作业
   qcos-cli cancel-jobs 00000000-0000-4000-8000-000000000001
   qcos-cli cancel-jobs -y all


作业结果设置（回调）
******************************

异步回调设置作业结果

命令行参数
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

典型场景示例
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 设置单个作业结果
   qcos-cli set-job-results 00000000-0000-4000-8000-000000000001 --results '{"results": {"01":100}, "num_qubits": 2}'

   # 设置多作业结果（针对多源代码作业）
   qcos-cli set-job-results 00000000-0000-4000-8000-000000000001 --results '{"results": {"01":100}, "num_qubits": 2}' '{"results": {"01":200}, "num_qubits": 2}'

   # 设置多作业结果（针对多源代码作业, 第2个结果带错误）
   qcos-cli set-job-results 00000000-0000-4000-8000-000000000001 --results '{"results": {"01":100}, "num_qubits": 2}' '{"code": -104, "message": "error test"}'

