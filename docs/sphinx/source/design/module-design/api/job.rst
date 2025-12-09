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
                   // 量子硬件插件名称 [可选]
                   "backend": "dummy",
                   // 转译器名称 [可选]
                   "transpiler": "cmss",
                   // 转译器配置参数 [可选]
                   "transpiler_info": {},
                   // 作业类型: estimation [可选]
                   "job_type": "",
                   // 作业调度优先级1-10 [可选]
                   "job_priority": 10,
                   // 次数
                   "shots": 1,
                   // 进行性能测试的模块列表 [可选]
                   "profiling": ["driver:transpile"],
                   // 模拟运行
                   "dry_run": false,
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
                 "job_priority": 10,
                 // 代码类型: qasm, qasm2, qasm3,qubo
                 "code_type": "qasm",
                 "source_code": ["源代码"],
                 // 作业描述
                 "description": "description",
                 "backend": "dummy",
                 "transpiler": "cmss",
                 // 可选, 转译器配置参数
                 "transpiler_info": {},
                 "shots": 2,
                 // 进行性能测试的模块列表 [可选]
                 "profiling": ["driver:transpile"],
                 // 模拟运行
                 "dry_run": false,
                 // 作业开始日期
                 "creation_date": "2025-07-15T14:58:55.283302"
                 // 作业结束日期
                 "end_date": null,
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
                 "job_priority": 10,
                 // 作业描述
                 "description": "description",
                 "backend": "dummy",
                 "transpiler": "cmss",
                 // 转译器配置参数 [可选]
                 "transpiler_info": {},
                 "shots": 2,
                 "progress": 100,
                 // 作业开始日期
                 "creation_date":"2025-07-15T14:53:00.412438",
                 // 作业结束日期
                 "end_date":"2025-07-15T14:53:43.355531"},
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
                 "job_priority": 10,
                 // 代码类型: qasm, qasm2, qasm3,qubo
                 "code_type": "qasm",
                 "source_code": ["源代码"],
                 // 作业描述
                 "description": "description",
                 "backend": "dummy",
                 "transpiler": "cmss",
                 // 转译器配置参数
                 "transpiler_info": {},
                 "shots": 100,
                 "progress": 100,
                 // 作业开始日期
                 "creation_date": "2025-07-15T14:53:00.412438",
                 // 作业结束日期
                 "end_date": "2025-07-15T14:53:43.355531"},
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
                 "filters": {}  // 过滤
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
                 "job_priority": 100,
                 "backend": "dummy",
                 "transpiler": "cmss",
                 "shots": 2,
                 "progress": 100,
                 // 作业开始日期
                 "creation_date": "2025-07-15T14:53:00.412438",
                 // 作业结束日期
                 "end_date":"2025-07-15T14:53:43.355531"},
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
                   "results": [{"01": 0}]
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
                 "job_status": "COMPLETED",
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
                   // 作业调度优先级1-10 [可选]
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
                 "job_priority": 10,  // 作业调度优先级1-10
                 // 代码类型: qasm, qasm2, qasm3,qubo
                 "code_type": "qasm",
                 "source_code": ["源代码"],
                 // 作业描述
                 "description": "description",
                 "backend": "dummy",
                 "transpiler": "cmss",
                 // 转译器配置参数
                 "transpiler_info": {},
                 "shots": 2,
                 // 进行性能测试的模块列表
                 "profiling": ["driver:transpile"],
                 // 模拟运行
                 "dry_run": false,
                 // 作业开始日期
                 "creation_date": "2025-07-15T14:58:55.283302"
                 // 作业结束日期
                 "end_date": null,
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

   - code_type中: qasm代表不区分qasm版本, 即source_code内容可以是qasm v1或者qasm v2或者qasm v3。由转译器自行判断qasm版本以及是否支持
   - 当code_type为qasm, qasm2, qasm3时, source_code格式为: ["代码字符串"], schema为: [str]

     当code_type为qubo时, source_code格式为: [[[整型/浮点, ...],[整型/浮点, ...]]], schema为: [[[int/float]]]
   - "results": ["result": XXX]中的XXX值由驱动driver设置, 格式由驱动定义，上层不做格式约束
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
                   "end_date": "2025-08-05 11:21:06.106873"
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
                   "end_date": "2025-08-05 11:20:32.369681"
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
                         "end_date": "2025-08-18T16:36:08.446082"
                       },
                       "profiling": {
                         "driver:parse": 0.036981821060180667,
                         "driver:transpile": 0.018097877502441407,
                         "driver:run": 0.018996477127075197
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
                         "end_date": "2025-08-18T16:36:08.530882"
                       },
                       "profiling": {
                         "driver:parse": 0.03369569778442383,
                         "driver:transpile": 0.016620397567749025,
                         "driver:run": 0.017986774444580079
                       }
                     }
                   ],
                   "creation_date": "2025-08-18T16:36:01.647565",
                   "end_date": "2025-08-18T16:36:08.530882"
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
                     "end_date": "2025-08-05T11:26:18.318860"
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
               "creation_date": "2025-08-05T11:26:01.980783",
               "end_date": "2025-08-05T11:26:18.318860"
             },
             "id":1
           }
