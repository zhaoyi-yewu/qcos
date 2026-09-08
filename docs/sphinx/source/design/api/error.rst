错误返回
================

本章节定义了北向接口的错误返回格式。

错误返回格式规范
^^^^^^^^^^^^^^^^

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
^^^^^^

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

错误处理最佳实践
~~~~~~~~~~~~~~~~

通用错误处理流程
^^^^^^^^^^^^^^^^

.. code-block:: python

   def call_api(method, params):
       try:
           response = json_rpc_request(method, params)

           if "error" in response and response["error"] is not None:
               error_code = response["error"]["code"]
               error_msg = response["error"]["message"]
               error_details = response["error"].get("data", {})

               # 根据错误码进行相应处理
               if error_code == -401:
                   # 需要重新登录
                   login()
               elif error_code == -403:
                   # 权限不足
                   log_permission_denied(error_msg)
               else:
                   # 其他错误
                   handle_error(error_code, error_msg, error_details)
               return None
           else:
               return response["result"]
       except Exception as e:
           # 网络错误等异常处理
           handle_exception(e)
           return None

错误码分类
^^^^^^^^^^

1. **解析类错误 (-32700至-32600)**

   这类错误表示请求本身有问题：

   - JSON 格式错误
   - 缺少必需字段
   - 参数类型不匹配

   **处理建议**：检查请求格式，确保JSON有效

2. **方法类错误 (-32601至-32602)**

   这类错误表示调用的方法或参数有误：

   - 方法名拼写错误
   - 参数格式不正确
   - 缺少必需参数

   **处理建议**：查阅API文档，验证方法名和参数

3. **业务类错误 (-400至-503)**

   这类错误表示业务逻辑问题：

   - 认证失败 (-401)
   - 权限不足 (-403)
   - 资源不存在 (-404)
   - 数据冲突 (-409)
   - 服务不可用 (-503)

   **处理建议**：根据具体错误码采取相应措施

常见错误及解决方案
^^^^^^^^^^^^^^^^^^

常见错误码和解决方法：

- **-32700** (Parse error) - 请求格式不是有效JSON，检查JSON格式
- **-32600** (Invalid Request) - 请求不是有效的JSON RPC 2.0格式，检查结构
- **-32601** (Method not found) - 调用的方法不存在，检查拼写
- **-32602** (Invalid params) - 参数数量或格式不正确，验证参数
- **-400** (Bad Request) - 请求参数非法，检查参数值
- **-401** (Unauthorized) - 未认证或token已过期，重新登认证
- **-403** (Forbidden) - 当前用户无权限，联系管理员
- **-404** (Not Found) - 资源不存在，检查资源ID或名称
- **-409** (Conflict) - 资源名称重复或依赖关系未满足，修改名称
- **-500** (Internal Server Error) - 服务器内部错误，检查错误详情
- **-503** (Service Unavailable) - 服务不可用或维护中，稍后重试

调试技巧
^^^^^^^^

1. **启用请求日志**

   .. code-block:: python

      import json

      # 记录完整的请求和响应
      def log_request(method, params):
          print(f"Request: {json.dumps({'method': method, 'params': params}, indent=2)}")

      def log_response(response):
          print(f"Response: {json.dumps(response, indent=2)}")

2. **使用工具验证**

   .. code-block:: text

      • 使用 curl 或 Postman 测试API
      • 使用 jsonschema 验证响应格式
      • 启用详细日志记录所有网络交互

3. **重试机制**

   .. code-block:: python

      import time

      def call_api_with_retry(method, params, max_retries=3):
          for attempt in range(max_retries):
              try:
                  return call_api(method, params)
              except Exception as e:
                  if attempt < max_retries - 1:
                      time.sleep(2 ** attempt)  # 指数退避
                  else:
                      raise
