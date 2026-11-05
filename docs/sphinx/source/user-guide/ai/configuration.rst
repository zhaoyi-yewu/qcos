.. _ai-configuration:

AI 配置详解
===========

QCOS AI 功能的配置位于 ``etc/qcos/qcos.toml`` 文件中的 ``[AI]`` 及相关子章节。

配置结构
--------

.. code-block:: toml

   # AI 功能全局开关
   [AI]
   ENABLED = true

   # AI MCP Server 配置（供外部 LLM 客户端调用）
   [AI.MCP_SERVER]
   ENABLED = true

   # AI Agent 聊天助手配置
   [AI.AGENT]
   ENABLED = true
   LLM_PROVIDER = "openai_compatible"
   LLM_BASE_URL = "http://vllm:8000/v1"
   LLM_API_KEY = ""
   LLM_MODEL = "Qwen/Qwen2.5-72B-Instruct"
   LLM_TEMPERATURE = 0.3
   LLM_MAX_TOKENS = 4096

   # Vision 模型配置（可选，为空时回退到 LLM_*）
   VISION_PROVIDER = ""
   VISION_BASE_URL = ""
   VISION_API_KEY = ""
   VISION_MODEL = ""

   # Embedding 模型配置（用于 RAG 知识库检索）
   EMBEDDING_BASE_URL = "http://embedding:8001/v1"
   EMBEDDING_API_KEY = ""
   EMBEDDING_MODEL = "bge-large-zh-v1.5"
   EMBEDDING_DIM = 1024

   # 会话配置
   SESSION_TTL_SECONDS = 604800
   RAG_TOP_K = 8

   # 图片附件限制
   IMAGE_MAX_COUNT_PER_MESSAGE = 4
   IMAGE_MAX_BYTES_PER_IMAGE = 5242880
   IMAGE_MAX_TOTAL_BYTES_PER_SESSION = 52428800

配置项说明
----------

[AI] 章节
~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - 配置项
     - 默认值
     - 说明
   * - ``ENABLED``
     - ``true``
     - AI 功能全局开关。设为 ``false`` 时同时禁用 MCP Server 和 AI Agent。

[AI.MCP_SERVER] 章节
~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - 配置项
     - 默认值
     - 说明
   * - ``ENABLED``
     - ``true``
     - MCP Server 端点开关。仅在 ``[AI].ENABLED=true`` 时生效。

[AI.AGENT] 章节
~~~~~~~~~~~~~~~

**基础开关**

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - 配置项
     - 默认值
     - 说明
   * - ``ENABLED``
     - ``true``
     - AI Agent 聊天功能开关。仅在 ``[AI].ENABLED=true`` 时生效。

**LLM 配置**

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - 配置项
     - 默认值
     - 说明
   * - ``LLM_PROVIDER``
     - ``openai_compatible``
     - LLM 提供商类型：``openai_compatible`` / ``openai`` / ``anthropic``
   * - ``LLM_BASE_URL``
     - ``http://vllm:8000/v1``
     - LLM 服务端点地址。``openai_compatible`` 模式下必填。
   * - ``LLM_API_KEY``
     - ``""``
     - LLM API 密钥。无认证端点可留空。
   * - ``LLM_MODEL``
     - ``Qwen/Qwen2.5-72B-Instruct``
     - 模型名称，传给 LLM 提供商。
   * - ``LLM_TEMPERATURE``
     - ``0.3``
     - 采样温度，范围 0.0-2.0。值越低输出越确定。
   * - ``LLM_MAX_TOKENS``
     - ``4096``
     - LLM 响应最大 token 数。

**Vision 模型配置（可选）**

当需要图片理解能力时配置。若任一字段为空，则回退到对应的 ``LLM_*`` 配置。

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - 配置项
     - 默认值
     - 说明
   * - ``VISION_PROVIDER``
     - ``""``
     - Vision 模型提供商，为空时使用 ``LLM_PROVIDER``。
   * - ``VISION_BASE_URL``
     - ``""``
     - Vision 模型端点，为空时使用 ``LLM_BASE_URL``。
   * - ``VISION_API_KEY``
     - ``""``
     - Vision API 密钥，为空时使用 ``LLM_API_KEY``。
   * - ``VISION_MODEL``
     - ``""``
     - Vision 模型名称，为空时使用 ``LLM_MODEL``。

**Embedding 配置**

用于 RAG 知识库检索的文本向量化模型。

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - 配置项
     - 默认值
     - 说明
   * - ``EMBEDDING_BASE_URL``
     - ``http://embedding:8001/v1``
     - Embedding 服务端点地址。
   * - ``EMBEDDING_API_KEY``
     - ``""``
     - Embedding API 密钥，无认证时可留空。
   * - ``EMBEDDING_MODEL``
     - ``bge-large-zh-v1.5``
     - Embedding 模型名称。
   * - ``EMBEDDING_DIM``
     - ``1024``
     - Embedding 向量维度，需与模型实际维度一致。

**会话与检索配置**

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - 配置项
     - 默认值
     - 说明
   * - ``SESSION_TTL_SECONDS``
     - ``604800``
     - AI 会话过期时间（秒），默认 7 天。
   * - ``RAG_TOP_K``
     - ``8``
     - RAG 检索返回的文档片段数量，范围 1-100。

**图片附件限制**

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - 配置项
     - 默认值
     - 说明
   * - ``IMAGE_MAX_COUNT_PER_MESSAGE``
     - ``4``
     - 单条消息最大图片数量。
   * - ``IMAGE_MAX_BYTES_PER_IMAGE``
     - ``5242880``
     - 单张图片最大字节数（base64 编码后），默认 5MB。
   * - ``IMAGE_MAX_TOTAL_BYTES_PER_SESSION``
     - ``52428800``
     - 单会话累计图片最大字节数，默认 50MB。

完整配置示例
------------

生产环境
~~~~~~~~

.. code-block:: toml

   [AI]
   ENABLED = true

   [AI.MCP_SERVER]
   ENABLED = true

   [AI.AGENT]
   ENABLED = true
   LLM_PROVIDER = "openai_compatible"
   LLM_BASE_URL = "http://vllm.internal:8000/v1"
   LLM_API_KEY = "sk-xxxxxxxx"
   LLM_MODEL = "Qwen/Qwen2.5-72B-Instruct"
   LLM_TEMPERATURE = 0.3
   LLM_MAX_TOKENS = 4096

   EMBEDDING_BASE_URL = "http://tei-bge-m3:8080/v1"
   EMBEDDING_MODEL = "BAAI/bge-m3"
   EMBEDDING_DIM = 1024

   SESSION_TTL_SECONDS = 604800
   RAG_TOP_K = 8

开发/测试环境
~~~~~~~~~~~~~

.. code-block:: toml

   [AI]
   ENABLED = true

   [AI.AGENT]
   ENABLED = true
   LLM_PROVIDER = "openai_compatible"
   LLM_BASE_URL = "http://localhost:11434/v1"  # Ollama
   LLM_MODEL = "qwen2.5:7b"
   LLM_TEMPERATURE = 0.5

   EMBEDDING_BASE_URL = "http://localhost:8080/v1"
   EMBEDDING_MODEL = "BAAI/bge-m3"
   EMBEDDING_DIM = 1024

关闭 AI 功能
~~~~~~~~~~~~

.. code-block:: toml

   [AI]
   ENABLED = false

   # 以下子章节开关均被忽略，无需修改
   [AI.MCP_SERVER]
   ENABLED = true

   [AI.AGENT]
   ENABLED = true
