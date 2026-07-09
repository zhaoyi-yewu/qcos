作业管理接口
================

作业接口具备通用量子QASM2.0/3.0、QUBO矩阵、驱动接口直通调用等等。

.. list-table:: 作业管理接口规范
   :widths: 20 20 30 30
   :header-rows: 1
   :align: left
   :class: longtable

   * - 用途
     - 方法
     - 请求参数
     - 返回值
   * - **提交作业**
     - **submit_job**

       URI: /v1/job/submit_job
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "id": 1,
               "method": "submit_job",
               "params": {
                 "body": {
                   // 自定义job_id [可选]
                   "job_id": "00000000-0000-4000-8000-000000000001",
                   // 作业名称 [可选]
                   "job_name": "test-dummy",
                   // 代码类型: qasm, qasm2, qasm3, qubo
                   "code_type": "qasm",
                   "source_code": ["源代码"],
                   // 作业描述 [可选]
                   "description": "description",
                   // 量子后端硬件名称
                   "backend": "dummy",
                   // 转译器名称 [可选]
                   "transpiler": "cmss",
                   // 转译器配置参数 [可选]
                   "transpiler_options": {},
                   // 作业类型: estimation [可选]
                   "job_type": "",
                   // 作业调度优先级1-10 [可选]
                   // 最高优先级：1， 最低优先级：10
                   "job_priority": 10,
                   // 次数
                   "shots": 1,
                   // 进行性能测试的模块列表 [可选]
                   "profiling": ["driver:transpile"],
                   // 模拟运行
                   "dry_run": false,
                   // 代码压缩等级 0-9 [可选]，0: 不压缩，9: 最高压缩
                   "code_compress_level": 0,
                   // 作业标签列表 [可选]，用于分类和过滤
                   "tags": ["tag1", "tag2"],
                   // 作业结束后, 回调通知结果
                   "callbacks": [
                     {
                       "name": "callback",
                       "type": "results",
                       "method": "post",
                       "url": "http://127.0.0.1:8088/v1/job/set_job_results"
                     }
                   ],
                 }
               }
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "id": 1,
               "result": {
                 "job_id": "00000000-0000-4000-8000-000000000001",
                 // 作业名称 [可选]
                 "job_name": "test-dummy",
                 // 作业状态: UNKNOWN,QUEUED,RUNNING,FAILED,
                 //          COMPLETED,CANCELLING,CANCELLED,DELETED
                 "job_status": "QUEUED",
                 // 作业调度优先级1-10
                 // 最高优先级：1， 最低优先级：10
                 "job_priority": 10,
                 // 代码类型: qasm, qasm2, qasm3,qubo
                 "code_type": "qasm",
                 "source_code": ["源代码"],
                 // 作业描述
                 "description": "description",
                 "backend": "dummy",
                 "transpiler": "cmss",
                 // 可选, 转译器配置参数
                 "transpiler_options": {},
                 "shots": 2,
                 // 进行性能测试的模块列表 [可选]
                 "profiling": ["driver:transpile"],
                 // 模拟运行
                 "dry_run": false,
                 // 代码压缩等级 0-9 [可选]
                 "code_compress_level": 0,
                 // 作业标签列表 [可选]
                 "tags": ["tag1", "tag2"],
                 // 作业创建日期
                 "created_at": "2025-07-15T14:58:55.283302",
                 // 作业更新日期 [可选]
                 "updated_at": "2025-07-15T14:59:00.000000",
                 // 作业开始日期 [可选]
                 "started_at": null,
                 // 作业结束日期 [可选]
                 "ended_at": null,
                 // 回调通知
                 "callbacks": [
                   {
                     "name": "callback",
                     "type": "results",
                     "method": "post",
                     "url": "http://127.0.0.1:8088/v1/job/set_job_results"
                   }
                 ],
               },
             // 可选, 有错误时会出现, 具体格式参照<错误返回>
             "error": {}
             }

   * - **查询作业状态**
     - **get_job_status**

       URI: /v1/job/get_job_status
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "id": 1,
               "method": "get_job_status",
               "params": {
                 "body": {
                   "job_id": "00000000-0000-4000-8000-000000000001",
                 }
               }
             }

     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "id": 1,
               "result": {
                 "job_id": "00000000-0000-4000-8000-000000000001",
                 // 作业名称 [可选]
                 "job_name": "test-dummy",
                 // 作业状态: UNKNOWN,QUEUED,RUNNING,FAILED,
                 //          COMPLETED,CANCELLING,CANCELLED,DELETED
                 "job_status": "QUEUED",
                 // 作业调度优先级1-10
                 // 最高优先级：1， 最低优先级：10
                 "job_priority": 10,
                 // 作业描述
                 "description": "description",
                 "backend": "dummy",
                 "transpiler": "cmss",
                 // 转译器配置参数 [可选]
                 "transpiler_options": {},
                 "shots": 2,
                 // 进行性能测试的模块列表 [可选]
                 "profiling": ["driver:transpile"],
                 // 模拟运行
                 "dry_run": false,
                 // 作业创建日期
                 "created_at": "2025-07-15T14:53:00.412438",
                 // 作业更新日期 [可选]
                 "updated_at": "2025-07-15T14:53:30.000000",
                 // 作业开始日期 [可选]
                 "started_at": "2025-07-15T14:53:15.000000",
                 // 作业结束日期 [可选]
                 "ended_at": "2025-07-15T14:53:43.355531"
               },
               // 有错误时会出现, 具体格式参照<错误返回>
               "error": {}
             }

   * - **返回作业测量结果**
     - **get_job_results**

       URI: /v1/job/get_job_results
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "id": 1,
               "method": "get_job_results",
               "params": {
                 "body": {
                   "job_id": "00000000-0000-4000-8000-000000000001",
                 }
               }
             }

     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "id": 1,
               "result": {
                 "job_id": "00000000-0000-4000-8000-000000000001",
                 // 作业名称
                 "job_name": "test-dummy",
                 // 作业状态: UNKNOWN,QUEUED,RUNNING,FAILED,
                 //          COMPLETED,CANCELLING,CANCELLED,DELETED
                 "job_status": "QUEUED",
                 // 作业调度优先级1-10
                 // 最高优先级：1， 最低优先级：10
                 "job_priority": 10,
                 // 代码类型: qasm, qasm2, qasm3,qubo
                 "code_type": "qasm",
                 "source_code": ["源代码"],
                 // 作业描述
                 "description": "description",
                 "backend": "dummy",
                 "transpiler": "cmss",
                 // 转译器配置参数
                 "transpiler_options": {},
                 "shots": 100,
                 "progress": 100,
                 // 作业创建日期
                 "created_at": "2025-07-15T14:53:00.412438",
                 // 作业更新日期 [可选]
                 "updated_at": "2025-07-15T14:53:30.000000",
                 // 作业开始日期 [可选]
                 "started_at": "2025-07-15T14:53:15.000000",
                 // 作业结束日期 [可选]
                 "ended_at": "2025-07-15T14:53:43.355531",
                 "results": [
                   {
                     "metadata": {},
                     "profiling": {},
                     "results": {"00": 50,"01":50},
                     "num_qubits":2
                   }
                 ]
                 "num_qubits":2
               },
               // 有错误时会出现, 具体格式参照<错误返回>
               "error": {}
             }

   * - **查询作业列表**
     - **get_jobs**

       URI: /v1/job/get_jobs
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "id": 1,
               "method": "get_jobs",
               "params": {
                 // 可选过滤参数
                 "filters": {
                   "all_projects": true,             // [可选] 选择所有项目, 只有管理员可用
                   "all_users": true,                // [可选] 选择项目下所有用户, 只有管理员可用
                   "project_id": "project-uuid",     // [可选] 按项目ID过滤
                   "user_id": "user-uuid",           // [可选] 按用户ID过滤
                   "job_ids": ["id1", "id2"],        // [可选] 按任务ID列表过滤
                 }
               }
             }

     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "id": 1,
               "result": [{
                 "job_id": "00000000-0000-4000-8000-000000000001",
                 // 作业名称
                 "job_name": "test-dummy",
                 // 作业状态: UNKNOWN,QUEUED,RUNNING,FAILED,
                 //          COMPLETED,CANCELLING,CANCELLED,DELETED
                 "job_status": "QUEUED",
                 "job_priority": 10,
                 "backend": "dummy",
                 "transpiler": "cmss",
                 "shots": 2,
                 "progress": 100,
                 // 代码压缩等级
                 "code_compress_level": 0,
                 // 作业标签列表
                 "tags": ["tag1", "tag2"],
                 // 作业开始日期
                 "created_at": "2025-07-15T14:53:00.412438",
                 // 作业结束日期
                 "ended_at":"2025-07-15T14:53:43.355531",
               }],
               // 有错误时会出现, 具体格式参照<错误返回>
               "error": {}
             }

   * - **批量取消作业**

       注意: 只有非RUNNING状态的作业才能被取消
     - **cancel_jobs**

       URI: /v1/job/cancel_jobs
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "id": 1,
               "method": "cancel_jobs",
               "params": {
                 "body": {
                   "job_ids": ["00000000-0000-4000-8000-000000000001"],
                 }
               }
             }

     - .. container:: table-code-small-font

          被取消的作业ID列表, 不包括无法取消的作业ID

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "id": 1,
               "result": [{
                 "job_id": "00000000-0000-4000-8000-000000000001",
                 "job_status": "CANCELLED",
               }],
               // 有错误时会出现, 具体格式参照<错误返回>
               "error": {}
             }

   * - **批量删除作业**

       注意: 只有非RUNNING状态的作业才能被删除
     - **delete_jobs**

       URI: /v1/job/delete_jobs
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "id": 1,
               "method": "delete_jobs",
               "params": {
                 "body": {
                   "job_ids": ["00000000-0000-4000-8000-000000000001"],
                 }
               }
             }

     - .. container:: table-code-small-font

          被删除的作业ID列表

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "id": 1,
               "result": [{
                 "job_id": "00000000-0000-4000-8000-000000000001",
                 "job_status": "DELETED",
               }],
               // 有错误时会出现, 具体格式参照<错误返回>
               "error": {}
             }

   * - **异步设置作业测量结果**
     - **set_job_results**

       URI: /v1/job/set_job_results
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "id": 1,
               "method": "set_job_results",
               "params": {
                 "body": {
                    "job_id": "00000000-0000-4000-8000-000000000001",
                    // 设置作业结果列表
                    "results": [
                      {
                        "results": {"00": 10, "11": 5},
                        "num_qubits": 2
                      }
                    ]
                 }
               }
             }

     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "id": 1,
               "result": {
                 "job_id": "00000000-0000-4000-8000-000000000001",
                 "backend": "dummy",
                 "job_status": "COMPLETED"
               },
               // 有错误时会出现, 具体格式参照<错误返回>
               "error": {}
             }

   * - **更新作业**
     - **update_job**

       URI: /v1/job/update_job
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "id": 1,
               "method": "update_job",
               "params": {
                 "body": {
                   "job_id": "00000000-0000-4000-8000-000000000001",
                   // 作业名称 [可选]
                   "job_name": "updated-job-name",
                   // 作业描述 [可选]
                   "description": "updated description",
                   // 作业调度优先级1-10 [可选]
                   // 最高优先级：1， 最低优先级：10
                   "job_priority": 10,
                 }
               }
             }

     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "id": 1,
               "result": {
                 "job_id": "00000000-0000-4000-8000-000000000001",
                 // 作业名称
                 "job_name": "test-dummy",
                 // 作业状态: UNKNOWN,QUEUED,RUNNING,FAILED,
                 //          COMPLETED,CANCELLING,CANCELLED,DELETED
                 "job_status": "QUEUED",
                 // 作业调度优先级1-10
                 // 最高优先级：1， 最低优先级：10
                 "job_priority": 10,
                 // 代码类型: qasm, qasm2, qasm3, qubo
                 "code_type": "qasm",
                 "source_code": ["源代码"],
                 // 作业描述
                 "description": "description",
                 "backend": "dummy",
                 "transpiler": "cmss",
                 // 转译器配置参数
                 "transpiler_options": {},
                 "shots": 2,
                 // 进行性能测试的模块列表
                 "profiling": ["driver:transpile"],
                 // 模拟运行
                 "dry_run": false,
                 // 作业创建日期
                 "created_at": "2025-07-15T14:58:55.283302",
                 // 作业更新日期 [可选]
                 "updated_at": "2025-07-15T14:59:00.000000",
                 // 作业开始日期 [可选]
                 "started_at": null,
                 // 作业结束日期 [可选]
                 "ended_at": null,
                 // 回调通知
                 "callbacks": [
                   {
                     "name": "callback",
                     "type": "results",
                     "method": "post",
                     "url": "http://127.0.0.1:8088/v1/job/set_job_results"
                   }
                 ],
               },
             }

.. note::

   - code_type中：qasm代表不区分qasm版本，即source_code内容可以是qasm v1或者qasm v2或者qasm v3。由转译器自行判断qasm版本以及是否支持
   - 当code_type为qasm、qasm2、qasm3时，source_code格式为: ["代码字符串"]，schema为: [str]

     当code_type为qubo时，source_code格式为: [[[整型/浮点, ...],[整型/浮点, ...]]]，schema为: [[[int/float]]]
   - "results"：["result": XXX]中的XXX值由RESULT_TYPE约束
   - code_compression_level：代码压缩等级（0-9），0不压缩，9最高压缩。推荐值5-7，可平衡压缩率和解压缩时间
   - tags：作业标签列表，用于分类、分组和过滤作业
   - 数据库过滤支持：``get_jobs`` 接口支持多条件过滤，支持的字段：

     +------------------+-------------------------------------------+
     | 过滤字段         | 说明                                      |
     +==================+===========================================+
     | all_projects     | [可选] 选择所有项目, 只有管理员可用       |
     | all_users        | [可选] 选择项目下所有用户, 只有管理员可用 |
     | project_id       | 项目ID（AND 逻辑）                        |
     +------------------+-------------------------------------------+
     | user_id          | 用户ID（AND 逻辑）                        |
     +------------------+-------------------------------------------+
     | job_ids          | 作业ID列表（IN 操作符）                   |
     +------------------+-------------------------------------------+
   - 回调的body:

     成功示例

     .. container:: table-code-small-font

        .. code-block:: json

           {
             "job_id": "3a906c1f-a2b1-40f3-a713-18b3f123c334",
             "job_status": "COMPLETED",
             "backend": "dummy",
             "results": [
               {
                  "metadata": {
                    "results_fetch_mode": "sync",
                    "status": "COMPLETED",
                    "ended_at": "2025-08-05T11:21:06.106873"
                  },
                 "profiling": {},
                 "results": {
                   "00": 10
                 },
                 "num_qubits": 2
               }
             ]
           }

     失败示例

     .. container:: table-code-small-font

        .. code-block:: json

           {
             "job_id": "43ec40a4-2ea7-4336-befb-bba28e280d8a",
             "job_status": "FAILED",
             "backend": "dummy",
             "results": [
               {
                 "results": null,
                 "metadata": {
                   "results_fetch_mode": "sync",
                   "status": "FAILED",
                   "ended_at": "2025-08-05T11:20:32.369681"
                 },
                 "error": {
                   "code": -102,
                   "message": "[JobEngine] Parse Error: in line 1, can not parser the sentence at token: '1'"
                 }
               }
             ]
           }

   - QASM返回值示例

     该qasm文件中量子比特数为2个, 所以所有量子比特的组合为: 00, 01, 10, 11, 重复实验次数(shots)为104

     results中{"00": 95, "11":9}表示104次实验测试中, 有95次测量结果为"00", 9次测量结果为"11", 0次测量结果为"01"和"10" (0次会被忽略掉)

     .. container:: table-code-small-font

        .. code-block:: json

           {
             "jsonrpc": "2.0",
             "result": {
                 "job_id": "f177f9c6-238e-4f20-a658-a325fd0e3f2b",
                 "job_name": "t2",
                 "job_status": "COMPLETED",
                 "code_type": "qasm",
                 "source_code": [
                   "OPENQASM 2.0;\ninclude \"qelib1.inc\";\n\nqreg q[2];\ncreg c[2];\nx q[0];\nx q[1];\n\nmeasure q -> c;\n\n",
                   "OPENQASM 2.0;\ninclude \"qelib1.inc\";\n\nqreg q[2];\ncreg c[2];\nx q[0];\nx q[1];\n\nmeasure q -> c;\n\n"
                 ],
                 "backend": "dummy",
                 "driver_options": null,
                 "transpiler": "cmss",
                 "transpiler_options": null,
                 "enable_circuit_aggregation": false,
                 "job_priority": 5,
                 "description": null,
                 "shots": 104,
                 "dry_run": true,
                 "results": [
                   {
                     "results": {
                       "00": 95,
                       "11": 9
                     },
                     "num_qubits": 2,
                     "metadata": {
                       "results_fetch_mode": "sync",
                       "status": "COMPLETED",
                       "ended_at": "2025-08-18T16:36:08.446082",
                       // 原始结果 [可选], 厂商返回的原始数据
                       "raw_results": {
                         "optimization": "OPENQASM 2.0;\ninclude \"qelib1.inc\";\n\nqreg q[2];\ncreg c[2];\nx q[0];\nx q[1];\n\nmeasure q -> c;\n\n",
                         "grid": "(0,0)\r\n(0,2)\r\n\r\n(0,0),(0,2)\r\n",
                         "lineResult": "{\"00\":95,\"11\":9}"
                       }
                     },
                     "profiling": {
                       // 作业中单代码执行耗时及起止时间
                       "code": 0.07406,
                       "code_started_at": "2025-08-18T16:36:08.400000",
                       "code_ended_at": "2025-08-18T16:36:08.446082",
                       // 作业排队耗时及起止时间
                       "queuing": 6.752435,
                       "queuing_started_at": "2025-08-18T16:36:01.647565",
                       "queuing_ended_at": "2025-08-18T16:36:08.400000",
                       // 调度器耗时及起止时间
                       "scheduling": 0.00123,
                       "scheduling_started_at": "2025-08-18T16:36:01.646335",
                       "scheduling_ended_at": "2025-08-18T16:36:01.647565",
                       // 代码解析耗时及起止时间
                       "driver:parse": 0.03698,
                       "driver:parse_started_at": "2025-08-18T16:36:08.401000",
                       "driver:parse_ended_at": "2025-08-18T16:36:08.437980",
                       // 转译器耗时及起止时间
                       "driver:transpile": 0.01809,
                       "driver:transpile_started_at": "2025-08-18T16:36:08.437980",
                       "driver:transpile_ended_at": "2025-08-18T16:36:08.456070",
                       // 后端运行耗时及起止时间
                       "driver:run": 0.01899,
                       "driver:run_started_at": "2025-08-18T16:36:08.456070",
                       "driver:run_ended_at": "2025-08-18T16:36:08.446082",
                       // 量子计算机运行耗时及起止时间 [可选],
                       "machine": 0.01500,
                       "machine_started_at": "2025-08-18T16:36:08.458000",
                       "machine_ended_at": "2025-08-18T16:36:08.473000"
                     }
                   },
                   {
                     "results": {
                       "00": 101,
                       "01": 1,
                       "11": 2
                     },
                     "num_qubits": 2,
                     "metadata": {
                       "results_fetch_mode": "sync",
                       "status": "COMPLETED",
                       "ended_at": "2025-08-18T16:36:08.530882",
                       // 原始结果 [可选], 厂商返回的原始数据
                       "raw_results": {
                         "optimization": "OPENQASM 2.0;\ninclude \"qelib1.inc\";\n\nqreg q[2];\ncreg c[2];\nx q[0];\nx q[1];\n\nmeasure q -> c;\n\n",
                         "grid": "(0,0)\r\n(0,2)\r\n\r\n(0,0),(0,2)\r\n",
                         "lineResult": "{\"00\":95,\"11\":9}"
                       }
                     },
                     "profiling": {
                       "code": 0.06829,
                       "code_started_at": "2025-08-18T16:36:08.485000",
                       "code_ended_at": "2025-08-18T16:36:08.530882",
                       "queuing": 6.837435,
                       "queuing_started_at": "2025-08-18T16:36:01.647565",
                       "queuing_ended_at": "2025-08-18T16:36:08.485000",
                       "scheduling": 0.00123,
                       "scheduling_started_at": "2025-08-18T16:36:01.646335",
                       "scheduling_ended_at": "2025-08-18T16:36:01.647565",
                       "driver:parse": 0.03369,
                       "driver:parse_started_at": "2025-08-18T16:36:08.486000",
                       "driver:parse_ended_at": "2025-08-18T16:36:08.519690",
                       "driver:transpile": 0.01662,
                       "driver:transpile_started_at": "2025-08-18T16:36:08.519690",
                       "driver:transpile_ended_at": "2025-08-18T16:36:08.536310",
                       "driver:run": 0.01798,
                       "driver:run_started_at": "2025-08-18T16:36:08.536310",
                       "driver:run_ended_at": "2025-08-18T16:36:08.530882",
                       "machine": 0.01400,
                       "machine_started_at": "2025-08-18T16:36:08.538000",
                       "machine_ended_at": "2025-08-18T16:36:08.552000"
                     }
                   }
                 ],
                 "created_at": "2025-08-18T16:36:01.647565",
                 "ended_at": "2025-08-18T16:36:08.530882"
             },
             "id": 1
           }

   - QUBO返回值示例

     其中quboValue表示: qubo值，maxcutValue表示: 最大割，solutionVector表示: 解向量

     最大割越大，求解效果越好，一般返回效果最好的10个解。

     判断结果是否符合预期需要把结果代回实际问题看，这里只纯数学求解。

     .. container:: table-code-small-font

        .. code-block:: json

           {
             "jsonrpc":"2.0",
             "result":
             {
               "job_id": "c0feb3ed-d83a-4768-a67f-795c5d099a5d",
               "job_name": null,
               "job_status": "COMPLETED",
               "code_type": "qubo",
               "source_code": [
                 [
                   [-12,8,0,0,0,0,0,0,0,0,8,0,0,0,0,0,0,0,0,8],
                   [0,-12,8,0,0,0,0,0,0,0,0,8,0,0,0,0,0,0,0,0],
                   [0,0,-12,8,0,0,0,0,0,0,0,0,8,0,0,0,0,0,0,0],
                   [0,0,0,-12,8,0,0,0,0,0,0,0,0,8,0,0,0,0,0,0],
                   [0,0,0,0,-12,8,0,0,0,0,0,0,0,0,8,0,0,0,0,0],
                   [0,0,0,0,0,-12,8,0,0,0,0,0,0,0,0,8,0,0,0,0],
                   [0,0,0,0,0,0,-12,8,0,0,0,0,0,0,0,0,8,0,0,0],
                   [0,0,0,0,0,0,0,-12,8,0,0,0,0,0,0,0,0,8,0,0],
                   [0,0,0,0,0,0,0,0,-12,8,0,0,0,0,0,0,0,0,8,0],
                   [0,0,0,0,0,0,0,0,0,-12,8,0,0,0,0,0,0,0,0,8],
                   [0,0,0,0,0,0,0,0,0,0,-12,8,0,0,0,0,0,0,0,0],
                   [0,0,0,0,0,0,0,0,0,0,0,-12,8,0,0,0,0,0,0,0],
                   [0,0,0,0,0,0,0,0,0,0,0,0,-12,8,0,0,0,0,0,0],
                   [0,0,0,0,0,0,0,0,0,0,0,0,0,-12,8,0,0,0,0,0],
                   [0,0,0,0,0,0,0,0,0,0,0,0,0,0,-12,8,0,0,0,0],
                   [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,-12,8,0,0,0],
                   [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,-12,8,0,0],
                   [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,-12,8,0],
                   [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,-12,8],
                   [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,-12]
                 ]
               ],
               "backend": "tiangong100",
               "driver_options": null,
               "transpiler": null,
               "transpiler_options": null,
               "enable_circuit_aggregation": false,
               "job_priority": 5,
               "description": null,
               "shots": 1,
               "dry_run": false,
               // results为列表, 按照source_code列表顺序进行返回
               "results": [
                 {
                   "metadata": {
                     "results_fetch_mode": "sync",
                     "status": "COMPLETED",
                     "ended_at": "2025-08-05T11:26:18.318860"
                   },
                   "profiling": {},
                   "results": [
                     {
                       "result": 1,
                       "quboValue": -112.0,
                       "maxcutValue": 28.0,
                       "solutionVector":  [1,0,1,0,1,0,1,1,0,1,0,1,0,1,0,1,0,0,1,0]
                     }, {
                       "result": 2,
                       "quboValue": -108.0,
                       "maxcutValue": 27.0,
                       "solutionVector": [1,0,1,0,1,0,1,1,0,1,0,1,0,1,0,1,1,0,1,0]
                     }, {
                       "result": 3,
                       "quboValue": -108.0,
                       "maxcutValue": 27.0,
                       "solutionVector": [1,0,1,0,1,0,1,1,0,1,0,1,0,1,0,1,0,1,1,0]
                     }, {
                       "result": 4,
                       "quboValue": -100.0,
                       "maxcutValue": 25.0,
                       "solutionVector": [1,0,1,0,1,0,1,1,1,1,0,1,0,1,0,1,0,0,1,0]
                     }, {
                       "result": 5,
                       "quboValue": -100.0,
                       "maxcutValue": 25.0,
                       "solutionVector": [1,0,1,0,1,1,1,1,0,1,0,1,0,1,0,1,0,0,1,0]
                     }, {
                       "result": 6,
                       "quboValue": -96.0,
                       "maxcutValue": 24.0,
                       "solutionVector": [1,0,1,0,1,0,1,1,0,1,0,1,0,1,0,1,1,1,1,0]
                     }, {
                       "result": 7,
                       "quboValue": -96.0,
                       "maxcutValue": 24.0,
                       "solutionVector": [1,0,1,0,1,0,1,1,1,1,0,1,0,1,0,1,0,1,1,0]
                     }, {
                       "result": 8,
                       "quboValue": -96.0,
                       "maxcutValue": 24.0,
                       "solutionVector": [1,0,1,0,1,0,1,1,1,1,0,1,0,1,0,1,1,0,1,0]
                     }, {
                       "result": 9,
                       "quboValue": -96.0,
                       "maxcutValue": 24.0,
                       "solutionVector": [1,0,1,0,1,1,1,1,0,1,0,1,0,1,0,1,0,1,1,0]
                     }, {
                       "result": 10,
                       "quboValue": -96.0,
                       "maxcutValue": 24.0,
                       "solutionVector": [1,0,1,0,1,1,1,1,0,1,0,1,0,1,0,1,1,0,1,0]
                     }
                   ]
                 }
               ],
               "created_at": "2025-08-05T11:26:01.980783",
               "ended_at": "2025-08-05T11:26:18.318860"
             },
             "id":1
           }

作业管理详解
~~~~~~~~~~~~

作业状态说明
^^^^^^^^^^^^

作业在其生命周期中会经历多个状态：

- **UNKNOWN** - 未知状态，通常表示不可预见的错误
- **QUEUED** - 已排队，等待系统调度执行
- **RUNNING** - 运行中，正在硬件或模拟器上执行
- **COMPLETED** - 已完成，获取结果使用 get_job_results
- **FAILED** - 执行失败，查看错误信息了解失败原因
- **CANCELLING** - 取消中，正在处理取消请求
- **CANCELLED** - 已取消，用户主动取消的作业
- **DELETED** - 已删除，作业记录已被清除

作业参数详解
^^^^^^^^^^^^

提交作业时的关键参数：

+------------------------+----------+----------------------------------------------+
| 参数名                 | 类型     | 说明                                         |
+========================+==========+==============================================+
| job_id                 | uuid     | 作业唯一标识，可自定义或由系统生成           |
+------------------------+----------+----------------------------------------------+
| code_type              | string   | 代码类型：qasm/qasm2/qasm3/qubo              |
+------------------------+----------+----------------------------------------------+
| source_code            | array    | 量子代码列表，支持批量提交                   |
+------------------------+----------+----------------------------------------------+
| backend                | string   | 目标硬件或模拟器名称                         |
+------------------------+----------+----------------------------------------------+
| transpiler             | string   | 转译器名称，将代码转为硬件可执行格式         |
+------------------------+----------+----------------------------------------------+
| job_priority           | int      | 任务优先级(1-10)，1最高，10最低              |
+------------------------+----------+----------------------------------------------+
| shots                  | int      | 测量次数，影响统计精度                       |
+------------------------+----------+----------------------------------------------+
| code_compression_level | int      | 代码压缩等级(0-9)，0不压缩，9最高压缩        |
+------------------------+----------+----------------------------------------------+
| tags                   | array    | 任务标签列表[可选]，用于分类和过滤任务       |
+------------------------+----------+----------------------------------------------+
| dry_run                | boolean  | 模拟运行，不使用真实硬件资源                 |
+------------------------+----------+----------------------------------------------+
| profiling              | array    | 性能评估类型，可用于分析运行时间分布         |
+------------------------+----------+----------------------------------------------+
| callbacks              | array    | 回调通知配置，作业完成时推送结果             |
+------------------------+----------+----------------------------------------------+
| created_at             | datetime | 作业创建时间，系统自动生成                   |
+------------------------+----------+----------------------------------------------+
| updated_at             | datetime | 作业更新时间 [可选]，每次状态变化时更新      |
+------------------------+----------+----------------------------------------------+
| started_at             | datetime | 作业开始执行时间 [可选]                      |
+------------------------+----------+----------------------------------------------+
| ended_at               | datetime | 作业结束执行时间 [可选]                      |
+------------------------+----------+----------------------------------------------+

代码类型说明
~~~~~~~~~~~~

- **qasm**：通用QASM格式，兼容v1/v2/v3版本
- **qasm2**：OpenQASM 2.0标准格式
- **qasm3**：OpenQASM 3.0标准格式
- **qubo**：矩阵格式，用于QUBO优化问题

测量结果格式
~~~~~~~~~~~~

对于量子电路（qasm格式），results 字段格式：

.. code-block:: json

   {
     "00": 95,  // 测得|00⟩状态的次数
     "11": 9    // 测得|11⟩状态的次数
   }

对于QUBO问题（qubo格式），results 字段格式：

.. code-block:: json

   [
     {
       "result": 1,
       "quboValue": -112.0,
       "maxcutValue": 28.0,
       "solutionVector": [1, 0, 1, 0]
     }
   ]

最佳实践建议
^^^^^^^^^^^^^^^^

1. **作业提交流程**

   .. code-block:: python

      # 步骤1: 准备量子代码
      qasm_code = """
      OPENQASM 2.0;
      include "qelib1.inc";
      qreg q[2];
      creg c[2];
      h q[0];
      cx q[0], q[1];
      measure q -> c;
      """

      # 步骤2: 提交作业，包含新参数
      job = submit_job(
          code_type="qasm2",
          source_code=[qasm_code],
          backend="dummy",
          transpiler="cmss",
          shots=1000,
          job_priority=5,
          code_compression_level=5,    # 中等压缩等级
          tags=["exp1", "circuit1"]  # 作业标签
      )

      # 步骤3: 轮询等待完成
      while True:
          status = get_job_status(job["job_id"])
          if status["job_status"] in ["COMPLETED", "FAILED"]:
              break
          time.sleep(1)

      # 步骤4: 获取结果
      if status["job_status"] == "COMPLETED":
          results = get_job_results(job["job_id"])

2. **批量作业管理与高级过滤**

   .. code-block:: python

      # 查询特定项目的已完成作业
      completed_jobs = get_jobs(filters={
          "project_id": "project-uuid",
          "job_status": "COMPLETED"
      })

      # 按标签过滤（API 返回结果包含 tags）
      all_jobs = get_jobs(filters={
          "project_id": "project-uuid"
      })
      filtered = [j for j in all_jobs
                  if "exp1" in j.get("tags", [])]

      # 按 job_ids 列表批量查询
      specific_jobs = get_jobs(filters={
          "job_ids": ["id1", "id2", "id3"]
      })

      # 复杂查询：特定用户在特定项目的作业
      user_project_jobs = get_jobs(filters={
          "project_id": "project-uuid",
          "user_id": "user-uuid",
          "job_status": "QUEUED"
      })

3. **错误处理和重试**

   .. code-block:: python

      def submit_job_with_retry(params, max_retries=3):
          for attempt in range(max_retries):
              try:
                  job = submit_job(**params)
                  return job
              except Exception as e:
                  if attempt < max_retries - 1:
                      time.sleep(2 ** attempt)
                  else:
                      raise

      def handle_failed_job(job_id):
          job = get_job_status(job_id)
          if job["job_status"] == "FAILED":
              results = get_job_results(job_id)
              for result in results["results"]:
                  if "error" in result:
                      msg = result.get("error", {}).get("message", "")
                      print(f"Error: {msg}")

4. **性能优化**

  -  使用 ``dry_run=true`` 测试代码（不消耗资源）
  -  启用 ``profiling`` 分析运行时间分布
  -  设置合理的 ``code_compression_level`` （推荐5-7）
  -  使用 ``tags`` 对相关作业进行分组管理
  -  批量提交相关作业提高资源利用率
  -  利用 ``filters`` 进行高效的作业查询

5. **回调通知配置**

   .. code-block:: python

      callbacks = [
          {
              "name": "webhook",
              "type": "results",
              "method": "post",
              "url": "http://server/webhook/callback"
          }
      ]

      job = submit_job(
          source_code=[qasm_code],
          callbacks=callbacks,
          code_compression_level=5,
          tags=["important"],
          ...
      )

      # 服务器端接收回调
      # POST /webhook/callback
      # Body: {
      #   "job_id": "xxx",
      #   "job_status": "COMPLETED",
      #   "results": [...]
      # }
