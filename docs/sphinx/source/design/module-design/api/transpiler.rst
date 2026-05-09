转译器管理接口
================

转译器接口用于查询转译器信息。

.. list-table:: 转译器管理接口规范
   :widths: 20 20 30 30
   :header-rows: 1
   :align: left
   :class: longtable

   * - 用途
     - 方法
     - 请求参数
     - 返回值
   * - **查询转译器详情**
     - **get_transpiler**

       URI: /v1/transpiler/get_transpiler
     - .. container:: table-code-small-font

          .. code-block:: json

              {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "get_transpiler",
                "params": {
                  "body": {
                    "name": "cmss"
                  }
                }
              }
     - .. container:: table-code-small-font

          .. code-block:: json

              {
                "jsonrpc": "2.0",
                "result": {
                  "name": "cmss",
                  "alias_name": "五岳转译器",
                  "enable": true,
                  "supported_code_types": [
                    "qasm",
                    "qasm2"
                  ],
                  "transpiler_options": null,
                  "transpiler_options_schema": null
                },
                "error": null,
                "id": 1
              }

   * - **查询转译器列表**
     - **get_transpilers**

       URI: /v1/transpiler/get_transpilers
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "id": 1,
               "method": "get_transpilers",
               "params": {
                 "filters": {}  // 过滤
               }
             }
     - .. container:: table-code-small-font

          .. code-block:: json

              {
                "jsonrpc": "2.0",
                "result": {
                  "cmss": {
                    "name": "cmss",
                    "alias_name": "五岳转译器",
                    "enable": true,
                    "supported_code_types": [
                      "qasm",
                      "qasm2"
                    ],
                    "transpiler_options": null,
                    "transpiler_options_schema": null
                  }
                },
                "error": null,
                "id": 1
              }

转译器参数详解
~~~~~~~~~~~~~~

转译器基本信息
^^^^^^^^^^^^^^

转译器配置字段说明：

- **name** (string) - 转译器唯一标识名称
- **alias_name** (string) - 转译器别名，用于界面显示
- **enable** (boolean) - 转译器是否启用，禁用时无法使用
- **supported_code_types** (array) - 支持的代码类型（qasm/qasm2/qasm3等）
- **transpiler_options** (object) - 转译器配置参数，由具体实现决定
- **transpiler_options_schema** (object) - 转译器参数的JSON Schema定义

转译过程说明
^^^^^^^^^^^^

转译器的主要功能：

1. **代码解析**：解析QASM格式的量子电路代码
2. **电路优化**：对量子电路进行优化和简化
3. **映射转换**：将逻辑电路映射到物理硬件
4. **门分解**：将高层门分解为硬件原生门

最佳实践建议
^^^^^^^^^^^^^^^^

1. **选择合适的转译器**

   .. code-block:: text

      • 不同硬件设备支持特定的转译器组合
      • 使用 get_transpilers 查询系统可用转译器
      • 根据目标硬件驱动选择对应转译器

2. **检查代码类型兼容性**

   .. code-block:: python

      # 提交作业前检查代码类型支持
      transpiler_info = get_transpiler("cmss")
      if "qasm2" in transpiler_info["supported_code_types"]:
          # 可以使用该转译器处理qasm2代码
          submit_job(code_type="qasm2", transpiler="cmss")

3. **性能考虑**

   .. code-block:: text

      • 复杂电路转译时间可能较长，故设置合理超时
      • 可使用 transpiler_info 评估转译器能力
      • 建议在小规模电路上先验证转译效果

