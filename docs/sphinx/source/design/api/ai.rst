AI服务接口
================

AI 服务接口为 WebUI 内置 AI 智能体提供后端能力，包括 SSE 流式
对话和会话历史管理。与基于 TCP JSON-RPC 2.0 的常规北向接口不同，
AI 对话接口采用 REST + SSE（Server-Sent Events）协议，统一挂载在
``/v1/ai`` 前缀下。

调用前需通过登录接口获取 JWT Token，后续请求在 HTTP Header 中携带
``Authorization: Bearer <token>``。当全局 ``AUTH_MODE`` 不是
``jwt`` 时，接口以匿名用户身份放行。

.. note::

   AI 服务接口仅在 ``[AI].ENABLED=true`` 且 ``[AI.AGENT].ENABLED=true``
   时注册；未启用时调用返回 HTTP 503。MCP 工具调用接口（供外部
   LLM 客户端使用）见 :doc:`mcp`。

.. contents:: 目录
   :local:
   :depth: 3

模型清单接口
------------

``GET /v1/ai/models`` 返回服务端配置的模型清单（需用户鉴权），
供 WebUI/CLI 构建模型选择菜单。响应只包含非敏感字段，不包含
provider、URL、API Key、提示词或完整配置，也不会实例化 Agent。

.. code-block:: json

   {
     "default_model_id": "kimi-k3",
     "models": [
       {
         "id": "kimi-k3",
         "display_name": "Kimi K3",
         "model": "moma/kimi-k3",
         "supports_vision": true
       },
       {
         "id": "glm-main",
         "display_name": "GLM 主模型",
         "model": "glm/glm-5.3",
         "supports_vision": false
       }
     ]
   }

其中 ``default_model_id`` 为配置数组 ``[[AI.AGENT.MODELS]]`` 第一项；
``supports_vision`` 对应模型项的 ``VISION_ENABLED``。旧版本服务端无
此端点（404），客户端应禁用模型菜单并回退到默认对话。

对话接口
--------

对话接口以 SSE 流式返回模型输出，响应 ``Content-Type`` 为
``text/event-stream``，并携带 ``Cache-Control: no-cache`` 与
``X-Accel-Buffering: no`` 头（禁止代理缓冲）。

请求体（两个对话端点共用）
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table:: ChatRequest 请求体
   :widths: 20 20 60
   :header-rows: 1
   :align: left

   * - 字段
     - 类型 / 必填
     - 说明

   * - ``session_id``
     - string，可选
     - 会话 ID。为空时后端自动创建新会话
   * - ``message``
     - string，必填
     - 用户消息文本
   * - ``enable_rag``
     - bool，默认 ``true``
     - 是否启用知识库检索（RAG）
   * - ``attachments``
     - array，可选
     - 图片附件列表，每项含 ``kind`` （固定 ``image`` ）、
       ``media_type`` （ ``image/png`` / ``image/jpeg`` /
       ``image/webp`` / ``image/gif`` ）、``data`` （base64 编码）。
       仅当前模型 ``VISION_ENABLED=true`` 时允许，否则后端拒绝
   * - ``model_id``
     - string，可选
     - 已配置的模型 ID（严格白名单，见 ``GET /v1/ai/models``）。
       缺省时不发送该字段：后端恢复会话最近模型或使用默认项；
       显式传入未知 ID 时返回 HTTP 400，不静默换模。同一会话
       后续消息可切换模型，不影响已发出的请求

SSE 流式聊天（内部事件格式）
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table:: AI 对话接口规范
   :widths: 20 20 30 30
   :header-rows: 1
   :align: left
   :class: longtable

   * - 用途
     - 方法
     - 请求参数
     - 返回值

   * - **流式对话（内部事件格式）**
     - **POST**

       URI: /v1/ai/chat
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "session_id": "uuid 或 null",
               "message": "dummy 设备现在状态如何？",
               "enable_rag": true,
               "attachments": null
             }
     - SSE 事件流，每个事件一帧
       ``data: {...}``，事件类型：

        - ``chunk``：文本增量
        - ``thinking``：思考过程增量
        - ``tool_call``：MCP 工具调用开始
        - ``tool_result``：工具调用结果
        - ``done``：本轮结束（含 token 用量、``model_id`` 与实际上游
          ``model``）
        - ``error``：错误信息

SSE 流式聊天（AG-UI 协议）
~~~~~~~~~~~~~~~~~~~~~~~~~~

``/v1/ai/chat/agui`` 与 ``/v1/ai/chat`` 行为一致，但输出遵循
AG-UI 标准事件协议，便于前端按标准协议渲染对话过程：

.. list-table:: AG-UI 事件类型
   :widths: 25 75
   :header-rows: 1
   :align: left

   * - 事件类型
     - 说明

   * - ``RUN_STARTED``
     - 本轮对话开始，流的首个事件，携带真实 ``sessionId``
   * - ``TEXT_MESSAGE_START``
     - 助手消息开始，携带 ``messageId`` 与 ``role``
   * - ``TEXT_MESSAGE_CONTENT``
     - 文本增量，携带 ``messageId`` 与 ``delta``
   * - ``THINKING_CONTENT``
     - 思考过程增量（自定义事件，前端渲染为可折叠气泡）
   * - ``TOOL_CALL_START``
     - 工具调用开始，携带 ``toolCallId`` / ``toolCallName``
   * - ``TOOL_CALL_RESULT``
     - 工具调用结果，携带 ``toolCallId`` 与 ``content``
   * - ``TEXT_MESSAGE_END``
     - 助手消息结束
   * - ``RUN_FINISHED``
     - 本轮正常结束（最后一个事件），可携带 ``usage`` token 统计；
       显式携带真实 ``sessionId``、本轮 ``modelId`` 与实际上游
       ``model``。前端应以 ``sessionId`` 维护会话，不再把
       ``messageId`` 当作会话 ID（旧服务端无 ``sessionId`` 时
       才保留兼容回退）
   * - ``RUN_ERROR``
     - 本轮异常结束，携带 ``error``

会话管理接口
------------

会话历史按用户隔离存储（Redis），支持多会话管理。除创建会话为
POST 外，其余均为标准 REST 语义。

.. list-table:: AI 会话管理接口规范
   :widths: 20 20 30 30
   :header-rows: 1
   :align: left
   :class: longtable

   * - 用途
     - 方法
     - 请求参数
     - 返回值

   * - **创建会话**
     - **POST**

       URI: /v1/ai/sessions
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "title": "新的会话"
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "session_id": "uuid",
               "title": "新的会话"
             }

   * - **查询会话列表**
     - **GET**

       URI: /v1/ai/sessions
     - 无参数（按当前用户过滤，按创建时间倒序）
     - .. container:: table-code-small-font

          .. code-block:: json

              [
                {
                  "session_id": "uuid",
                  "created_at": 1761200000.0,
                  "title": "dummy 设备状态",
                  "message_count": 6,
                  "model_id": "kimi-k3"
                }
              ]

   * - **查询会话详情**
     - **GET**

       URI: /v1/ai/sessions/{session_id}
     - 路径参数：``session_id``
     - .. container:: table-code-small-font

          .. code-block:: json

              {
                "session": {
                  "session_id": "uuid",
                  "created_at": 1761200000.0,
                  "title": "dummy 设备状态",
                  "message_count": 2,
                  "model_id": "kimi-k3"
                },
                "messages": [
                  {
                    "role": "user",
                    "content": "dummy 设备现在状态如何？",
                    "created_at": 1761200001.0,
                    "attachments": null,
                    "model_id": "kimi-k3",
                    "model": null
                  },
                  {
                    "role": "assistant",
                    "content": "dummy 设备当前在线。",
                    "created_at": 1761200003.0,
                    "attachments": null,
                    "model_id": "kimi-k3",
                    "model": "moma/kimi-k3"
                  }
                ]
              }

        会话不存在时返回 HTTP 404。``session.model_id`` 为会话最近
        使用的模型（可空，空表示使用默认模型）；消息的 ``model_id``
        为本轮配置 ID、``model`` 为实际生成的上游模型名，旧数据缺
        字段时均为 ``null``。清空与截断操作不改变会话当前模型。

   * - **删除会话**
     - **DELETE**

       URI: /v1/ai/sessions/{session_id}
     - 路径参数：``session_id``
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "status": "deleted",
               "session_id": "uuid"
             }

   * - **清空会话消息**
     - **DELETE**

       URI: /v1/ai/sessions/{session_id}/messages
     - 路径参数：``session_id``
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "status": "cleared",
               "session_id": "uuid"
             }

       仅清空消息历史，保留会话记录（id / 标题 / 创建时间），
       会话仍出现在列表中。

   * - **截断问题及后续消息**
     - **POST**

       URI: /v1/ai/sessions/{session_id}/messages/truncate
     - .. code-block:: json

          {
            "from_index": 2,
            "expected_content": "编辑前的原始问题"
          }

       ``from_index`` 必须指向用户消息，原文不匹配时返回 409。
     - 返回截断后保留的权威消息前缀：

       .. code-block:: json

          {
            "session_id": "uuid",
            "message_count": 2,
            "messages": []
          }

       用于“修改问题并重新生成”：先删除该用户问题及后续消息，
       再通过正常聊天接口追加新问答，避免刷新后旧历史重复出现。

错误与限制
----------

.. list-table::
   :widths: 20 80
   :header-rows: 1
   :align: left

   * - 状态码
     - 场景

   * - ``401``
     - JWT Token 缺失、无效或过期
   * - ``404``
     - 会话不存在（查询会话详情或截断消息）
   * - ``503``
     - AI 功能未启用（``[AI].ENABLED`` 或
       ``[AI.AGENT].ENABLED`` 为 ``false``），或 AI 依赖未安装
   * - ``400`` / ``422``
     - 请求体校验失败；显式 ``model_id`` 未在服务端配置（流开始前
       返回，不自动换模）；当前模型 ``VISION_ENABLED=false`` 时携带
       图片附件；图片附件超限（数量、单张大小、会话累计大小，
       由 ``[AI.AGENT]`` 的 ``IMAGE_*`` 配置控制）；截断索引越界或目标
       不是用户消息
   * - ``409``
     - 截断目标原文与 Redis 当前内容不一致，需要重新加载会话后重试

相关文档
--------

- AI 智能体使用手册：:doc:`../../user-guide/ai/agent`
- AI 配置说明：:doc:`../../user-guide/ai/configuration`
- MCP 服务接口：:doc:`mcp`
