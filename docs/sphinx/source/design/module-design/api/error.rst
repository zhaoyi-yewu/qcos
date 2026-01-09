错误返回
================

本章节定义了北向接口的错误返回格式。

错误返回格式规范
--------------------

错误格式分为两种:

- jsonrpc api请求出错的返回

  .. container:: table-code-small-font

     .. code-block:: json

        {
          "jsonrpc": "2.0",
          "id": 1,
          "error": {
          // 正确为0, 错误为负数
            "code": 0,
            // 错误描述, submit_job/get_job_status等api操作级别名称;
            // 该类错误为请求api时, 直接返回的错误，作业过程中产生的错误不在这里
            "message": "Failed to submit_job",
            "data": {
              // 具体错误信息, 一般是底层代码抛出的异常内容 [可选]
              "details": "详细错误信息"
            }
          }
        }

- 作业已创建, 运行过程中发生的错误

  .. container:: table-code-small-font

     .. code-block:: json

        {
          "jsonrpc": "2.0",
          "result": {
            "job_id": "1a287691-9df5-44f2-b62c-72c0b79ea689",
            "job_status": "FAILED"
            "source_code": [
              "CODE1",
              "CODE2"
            ],
            // results是列表, 和source_code代码对应, 每段source_code代码对应一个result
            // result内容是不一样的, 只要有一个results是failed, 则整个job状态为failed
            "results": [
              {
                "metadata": {
                  "results_fetch_mode": "sync",
                  "status": "FAILED",
                  "end_date": "2025-07-30T15:58:56.998078"
                },
                "results": {"00": 10},
                "num_qubits": 2,
                "error": {
                  "code": -1  // 错误为负数
                  // 具体错误信息, 一般是底层代码抛出的异常内容
                  "message": "详细错误信息"
                }
              }
            ]
          }
        }

错误码
--------------------

- JSON-RPC标准错误码

  .. list-table:: JSON-RPC标准错误码
     :widths: 30 30 40
     :header-rows: 1
     :align: left
     :class: longtable

     * - 错误码
       - 消息
       - 描述
     * - -32700
       - Parse error
       - 解析错误
     * - -32600
       - Invalid Request
       - 非法请求
     * - -32601
       - Method not found
       - 方法未找到
     * - -32602
       - Invalid params
       - 非法参数
     * - -32603
       - Internal error
       - 内部错误

- JSON-RPC业务层自定义错误码

  .. list-table:: JSON-RPC业务层自定义错误码
     :widths: 30 30 40
     :header-rows: 1
     :align: left
     :class: longtable

     * - 错误码
       - 消息
       - 描述
     * - -400
       - Bad Request
       - 非法的参数或者请求
     * - -401
       - Unauthorized
       - 未登录认证或者token非法/过期
     * - -403
       - Forbidden
       - 无权限访问资源
     * - -404
       - Not Found
       - 资源找不到
     * - -409
       - Conflict
       - 资源名称/ID重复，或者资源依赖关系未满足
     * - -500
       - Internal Server Error
       - 内部错误，一般是bug或者出现未处理的异常
     * - -501
       - Not Implemented
       - 功能还未实现
     * - -503
       - Service Unavailable
       - 服务下线，不可用
