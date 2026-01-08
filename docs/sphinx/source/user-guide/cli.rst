命令行示例
==============

本章节介绍QCOS命令行工具（qcos-cli）的常用操作示例，涵盖作业管理、系统信息查询、驱动与设备管理等核心功能。

.. contents:: 目录
   :local:
   :depth: 3

作业命令
-------------
作业命令包含作业提交、状态查询、结果获取、取消及删除等操作，是qcos-cli的核心功能模块。

提交作业
***************
提交作业支持不同后端驱动、参数配置及执行模式，以下为典型场景示例：

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

- 中科酷原-汉原1 中性原子驱动

.. code-block:: shell

   # 2. 模拟运行(dry-run)
   qcos-cli submit-job --code-type qasm --shots 10 --dry-run --backend hanyuan1 -f ./samples/qasm/2.0/simple-qasm-1-bit.qasm

   # 2.1 模拟运行双量子比特门 (dry-run)
   qcos-cli submit-job --code-type qasm --shots 10 --dry-run --backend hanyuan1 --transpiler-options '{"enable_na_move": true}' -f ./samples/qasm/2.0/rb.qasm

   # 3. 真实运行
   qcos-cli submit-job --code-type qasm --shots 10 --backend hanyuan1 -f ./samples/qasm/2.0/simple-qasm-1-bit.qasm
   qcos-cli submit-job --code-type qasm2 --shots 10 --backend wy-hanyuan1 -f ./samples/qasm/2.0/simple-qasm.qasm

   # 4. 电路切割开启 （--driver-options '{"enable_wirecut":true}'）
   qcos-cli submit-job --code-type qasm --shots 10 --backend hanyuan1 --transpiler-options '{"enable_na_move": true}' --driver-options '{"enable_wirecut":true}' --dry-run -f ./samples/qasm/2.0/wirecut/12_30.qasm

- 玻色量子-光量子伊辛机

.. code-block:: shell

   # 真实运行
   qcos-cli submit-job --code-type qubo --backend tiangong100 -f ./samples/qubo/simple-qubo.json
   qcos-cli submit-job --code-type qubo --backend tiangong100 -f ./samples/qubo/simple-qubo.csv
   qcos-cli submit-job --code-type qubo --backend tiangong100_v2 -f ./samples/qubo/simple-qubo.json
   qcos-cli submit-job --code-type qubo --backend tiangong100_v2 -f ./samples/qubo/simple-qubo.csv
   qcos-cli submit-job --code-type qubo --backend tiangong550_v2 -f ./samples/qubo/simple-qubo.json
   qcos-cli submit-job --code-type qubo --backend tiangong550_v2 -f ./samples/qubo/simple-qubo.csv
   qcos-cli submit-job --code-type qubo --backend tiangong1000_v2 -f ./samples/qubo/simple-qubo.json
   qcos-cli submit-job --code-type qubo --backend tiangong1000_v2 -f ./samples/qubo/simple-qubo.csv

   # 开启subqubo功能（默认关闭）
   qcos-cli submit-job --code-type qubo --backend tiangong100 --driver-options '{"enable_subqubo": true}' -f ./samples/qubo/qubo_200X200.csv
   qcos-cli submit-job --code-type qubo --backend tiangong100 --driver-options '{"enable_subqubo": false}' -f ./samples/qubo/qubo_200X200.csv

   # 开启降精度功能（默认关闭）
   qcos-cli submit-job --code-type qubo --backend tiangong100 --driver-options '{"enable_prec_reduce": true}' -f ./samples/qubo/qubo_200X200.csv
   qcos-cli submit-job --code-type qubo --backend tiangong100 --driver-options '{"enable_prec_reduce": false}' -f ./samples/qubo/qubo_200X200.csv

- 量旋科技

.. code-block:: shell

   # 量旋科技 真实运行
   qcos-cli submit-job --code-type qasm --shots 10 --backend spinq_rpc -f ./samples/qasm/2.0/simple-qasm.qasm

- 幺正量子

.. code-block:: shell

   # 幺正量子 真实运行
   qcos-cli submit-job --code-type qasm3 --shots 100 --backend uqc_matrix2 -f ./samples/qasm/3.0/simple-qasm-1-bit.qasm

作业状态与结果查询
*************************
.. code-block:: shell

   # 获取作业状态
   qcos-cli get-job-status 00000000-0000-4000-8000-000000000001

   # 获取作业结果
   qcos-cli get-job-results 00000000-0000-4000-8000-000000000001

   # 获取所有作业列表
   qcos-cli list-jobs

作业取消与删除
*************************
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
.. code-block:: shell

   # 设置单个作业结果
   qcos-cli set-job-results 00000000-0000-4000-8000-000000000001 --results '{"results": {"01":100}, "num_qubits": 2}'

   # 设置多作业结果（针对多源代码作业）
   qcos-cli set-job-results 00000000-0000-4000-8000-000000000001 --results '{"results": {"01":100}, "num_qubits": 2}' '{"code": -104, "message": "error test"}'

版本命令
-------------
.. code-block:: shell

   # 请求服务端版本
   qcos-cli version

系统命令
-------------
.. code-block:: shell

   # ping命令（测试服务连通性）
   qcos-cli ping 123

   # 获取系统信息
   qcos-cli system-info

驱动命令
-------------
.. code-block:: shell

   # 获取所有驱动信息列表
   qcos-cli list-drivers

   # 获取驱动信息详情
   qcos-cli get-driver DriverDummy

设备命令
-------------
.. code-block:: shell

   # 获取所有设备信息列表
   qcos-cli list-devices

   # 获取设备信息详情
   qcos-cli get-device dummy
