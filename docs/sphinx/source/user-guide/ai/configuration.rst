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
   # 共享默认值：各模型项可覆盖
   LLM_TEMPERATURE = 0.3
   LLM_MAX_TOKENS = 4096
   LLM_MODEL_SETTINGS_ENABLED = false
   LLM_TIMEOUT = 60.0
   # 自定义提示词，为空时使用代码内置默认模板
   SYSTEM_PROMPT = ""
   VISION_SYSTEM_PROMPT = ""

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

   # 模型列表：第一项为默认模型，每项拥有独立连接。
   # 支持两种等价 TOML 写法：下方 [[AI.AGENT.MODELS]] 表数组，
   # 或 MODELS = [ {...}, {...} ] 内联表数组（见下文说明）。
   # 注意：使用表数组写法时必须放在 [AI.AGENT] 所有叶子键之后，
   # 否则其后的键会被解析为数组项字段。
   [[AI.AGENT.MODELS]]
   ID = "qwen-main"
   DISPLAY_NAME = "Qwen 主模型"
   PROVIDER = "openai_compatible"
   BASE_URL = "http://vllm:8000/v1"
   API_KEY = ""
   MODEL = "Qwen/Qwen2.5-72B-Instruct"
   VISION_ENABLED = false

   [[AI.AGENT.MODELS]]
   ID = "kimi-k3"
   DISPLAY_NAME = "Kimi K3"
   PROVIDER = "openai_compatible"
   BASE_URL = "http://gateway-b.example/v1"
   API_KEY = ""
   MODEL = "moma/kimi-k3"
   VISION_ENABLED = true
   # 可选视觉覆盖；未设置时回退到本项 PROVIDER/BASE_URL/API_KEY/MODEL
   VISION_MODEL = "moma/kimi-k3-vision"
   # 可选覆盖共享默认值
   TEMPERATURE = 0.2
   MAX_TOKENS = 2048
   TIMEOUT = 45.0

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

**模型列表（[[AI.AGENT.MODELS]]）**

``MODELS`` 必须至少包含一项、最多 32 项；**第一项为默认模型**。每项拥有
独立的 provider 连接，客户端只能通过 ``ID`` 引用模型（严格白名单），不能
传递任意 provider、URL、密钥或上游模型名。

支持两种等价的 TOML 写法，解析结果完全一致，可按团队习惯选择：

.. code-block:: toml

   # 写法一：表数组（必须放在 [AI.AGENT] 所有叶子键之后）
   [[AI.AGENT.MODELS]]
   ID = "qwen-main"
   MODEL = "Qwen/Qwen2.5-72B-Instruct"
   BASE_URL = "http://vllm:8000/v1"

   # 写法二：内联表数组（可放在 [AI.AGENT] 任意位置）
   MODELS = [
     { ID = "qwen-main", MODEL = "Qwen/Qwen2.5-72B-Instruct", BASE_URL = "http://vllm:8000/v1" },
     { ID = "kimi-k3", MODEL = "moma/kimi-k3", BASE_URL = "http://gateway-b.example/v1", VISION_ENABLED = true, TEMPERATURE = 0.2 },
   ]

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - 配置项
     - 默认值
     - 说明
   * - ``ID``
     - 必填
     - 模型唯一标识，客户端请求时携带。去空白、全局唯一，格式
       ``[A-Za-z0-9][A-Za-z0-9_.-]{0,63}``。
   * - ``DISPLAY_NAME``
     - ``MODEL``
     - WebUI/CLI 展示名称；缺省时显示上游 ``MODEL``。
   * - ``PROVIDER``
     - ``openai_compatible``
     - 提供商类型：``openai_compatible`` / ``openai`` / ``anthropic``。
   * - ``BASE_URL``
     - ``""``
     - 服务端点地址。``openai_compatible`` 模式下必填。
   * - ``API_KEY``
     - ``""``
     - API 密钥，无认证端点可留空。支持加密配置（自动递归解密）。
   * - ``MODEL``
     - 必填
     - 上游模型名称，传给提供商。
   * - ``VISION_ENABLED``
     - ``false``
     - 是否允许图片附件。为 ``false`` 时 WebUI 禁用图片按钮，后端拒绝附件。
   * - ``VISION_PROVIDER``
     - ``""``
     - 视觉模型提供商，为空时使用本项 ``PROVIDER``。
   * - ``VISION_BASE_URL``
     - ``""``
     - 视觉模型端点，为空时使用本项 ``BASE_URL``。
   * - ``VISION_API_KEY``
     - ``""``
     - 视觉 API 密钥，为空时使用本项 ``API_KEY``。
   * - ``VISION_MODEL``
     - ``""``
     - 视觉模型名称，为空时使用本项 ``MODEL``。

**共享默认值与逐项覆盖**

以下字段在 ``[AI.AGENT]`` 提供共享默认值；各模型项可通过同名覆盖字段
（``TEMPERATURE`` / ``MAX_TOKENS`` / ``MODEL_SETTINGS_ENABLED`` /
``TIMEOUT`` / ``SYSTEM_PROMPT`` / ``VISION_SYSTEM_PROMPT``）按需覆盖，
未设置（``None``）表示继承共享默认。

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - 共享配置项（覆盖字段）
     - 默认值
     - 说明
   * - ``LLM_TEMPERATURE``（``TEMPERATURE``）
     - ``0.3``
     - 采样温度，范围 0.0-2.0。仅在 ``MODEL_SETTINGS_ENABLED=true`` 时发送。
   * - ``LLM_MAX_TOKENS``（``MAX_TOKENS``）
     - ``4096``
     - 响应最大 token 数。仅在 ``MODEL_SETTINGS_ENABLED=true`` 时发送。
   * - ``LLM_MODEL_SETTINGS_ENABLED``（``MODEL_SETTINGS_ENABLED``）
     - ``false``
     - 是否向模型发送采样参数。默认关闭以兼容参数范围固定或校验严格的
       模型网关；确认提供商支持后再开启。
   * - ``LLM_TIMEOUT``（``TIMEOUT``）
     - ``60.0``
     - LLM HTTP 请求超时（秒），防止端点挂起耗尽 API worker。
   * - ``SYSTEM_PROMPT``
     - ``""``
     - 文本对话系统提示词，为空时使用代码内置默认模板。
   * - ``VISION_SYSTEM_PROMPT``
     - ``""``
     - 图片理解系统提示词，为空时使用代码内置默认模板。

``etc/qcos/qcos.toml`` 中已提供完整的多行提示词模板，可直接使用 TOML
多行字面字符串（``'''...'''``）修改，无需改动 Python 代码。例如：

.. code-block:: toml

   SYSTEM_PROMPT = '''
   你是集成在 QCOS 中的 AI 智能体。
   【语言要求】
   - 默认使用简体中文回答。
   '''

提示词、采样温度和最大 Token 均在 Agent 构建时读取；修改配置后需重启
QCOS 服务才能生效。

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

从旧版单模型配置迁移
--------------------

旧版的 ``LLM_PROVIDER / LLM_BASE_URL / LLM_API_KEY / LLM_MODEL`` 与
``VISION_PROVIDER / VISION_BASE_URL / VISION_API_KEY / VISION_MODEL``
字段**已移除**，不再回退兼容。加载配置时若存在上述字段，启动校验会直接
报错并提示迁移。迁移方式：

1. 将原 ``LLM_*`` 连接信息移入第一个 ``[[AI.AGENT.MODELS]]`` 项
   （``PROVIDER / BASE_URL / API_KEY / MODEL``）。
2. 原 ``VISION_*`` 字段移入同一模型项，并显式设置
   ``VISION_ENABLED = true`` （旧版只要配置 VISION_MODEL/PROVIDER 即启用
   视觉，新版必须显式开启）。
3. ``LLM_TEMPERATURE / LLM_MAX_TOKENS / LLM_MODEL_SETTINGS_ENABLED /
   LLM_TIMEOUT / SYSTEM_PROMPT / VISION_SYSTEM_PROMPT`` 保留为共享默认，
   无需改动；仅当某个模型需要不同取值时才在模型项内覆盖。
4. AI Agent 启用时 ``MODELS`` 为空会导致启动校验失败。

完整配置示例
------------

生产环境（双网关）
~~~~~~~~~~~~~~~~~~

.. code-block:: toml

   [AI]
   ENABLED = true

   [AI.MCP_SERVER]
   ENABLED = true

   [AI.AGENT]
   ENABLED = true
   LLM_TEMPERATURE = 0.3
   LLM_MAX_TOKENS = 4096

   EMBEDDING_BASE_URL = "http://tei-bge-m3:8080/v1"
   EMBEDDING_MODEL = "BAAI/bge-m3"
   EMBEDDING_DIM = 1024

   SESSION_TTL_SECONDS = 604800
   RAG_TOP_K = 8

   [[AI.AGENT.MODELS]]
   ID = "qwen-main"
   DISPLAY_NAME = "Qwen 主模型"
   PROVIDER = "openai_compatible"
   BASE_URL = "http://vllm.internal:8000/v1"
   API_KEY = "sk-xxxxxxxx"
   MODEL = "Qwen/Qwen2.5-72B-Instruct"
   VISION_ENABLED = false

   [[AI.AGENT.MODELS]]
   ID = "kimi-k3"
   DISPLAY_NAME = "Kimi K3"
   PROVIDER = "openai_compatible"
   BASE_URL = "http://gateway-b.internal/v1"
   API_KEY = "sk-yyyyyyyy"
   MODEL = "moma/kimi-k3"
   VISION_ENABLED = true

开发/测试环境
~~~~~~~~~~~~~

.. code-block:: toml

   [AI]
   ENABLED = true

   [AI.AGENT]
   ENABLED = true
   LLM_TEMPERATURE = 0.5

   EMBEDDING_BASE_URL = "http://localhost:8080/v1"
   EMBEDDING_MODEL = "BAAI/bge-m3"
   EMBEDDING_DIM = 1024

   [[AI.AGENT.MODELS]]
   ID = "local-qwen"
   PROVIDER = "openai_compatible"
   BASE_URL = "http://localhost:11434/v1"  # Ollama
   MODEL = "qwen2.5:7b"
   VISION_ENABLED = false

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
