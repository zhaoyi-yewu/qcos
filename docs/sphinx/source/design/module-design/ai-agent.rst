AI Agent 助手
====================================

本章节介绍 QCOS 操作系统中内置 AI Agent（AI 助手）后端的设计与实现，
代码位于 ``src/wy_qcos/ai/``。

.. note::

   本文档只覆盖 ``src/wy_qcos`` 后端代码设计；WebUI 聊天界面（Vue 组件、
   SSE 消费逻辑）不在本文范围内。

概述
--------------------

QCOS AI Agent 是集成在 QCOS API 服务中的智能助手，为用户提供：

- **自然语言问答**：QCOS 使用方法、量子计算概念、故障排查
- **实时数据查询**：通过工具调用（function calling）查询设备状态、
  作业进度、系统健康度
- **文档检索（RAG）**：基于 pgvector 的 QCOS 文档语义检索，回答时引用
  官方文档
- **图片理解（Vision）**：分析量子线路图、QASM/QUBO 代码截图、错误
  堆栈、设备拓扑图等
- **可观测性问答**：借助反向代理工具直接回答 Prometheus 指标、
  Alertmanager 告警、VictoriaLogs 日志类问题

架构设计
--------------------

整体分层
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: text

   WebUI / 客户端
        |  HTTP POST (SSE)
        v
   +------------------------------------------+
   | REST 层  api/posiq/routes_rest/ai.py     |
   |   /v1/ai/chat, /v1/ai/chat/agui          |
   |   /v1/ai/sessions...                     |
   +-------------------+----------------------+
                       |
   +-------------------v----------------------+
   | 编排层  ai/agent.py  (AiAgent)            |
   |   历史加载 -> RAG -> Agent 驱动 -> 持久化 |
   +----+----------------+---------------+----+
        |                |               |
   +----v----+   +-------v-------+   +---v---------------+
   | LLM 层  |   | 会话层        |   | 工具层            |
   | llm/    |   | session_store |   | tools/mcp_tools   |
   | client  |   | (Redis)      |   | (MCP in-process) |
   | prompts |   +---------------+   +------------------+
   +---------+
        |                |
   +-----v-----+   +-----v------------------+
   | RAG 层    |   | 数据层                  |
   | rag/      |   | db.py (SQLAlchemy)      |
   | retriever |   | db/models/ai_doc_chunk |
   | embedder  |   | (pgvector)             |
   | indexer   |   +------------------------+
   +-----------+

核心组件
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - 组件
     - 职责
   * - ``api/posiq/routes_rest/ai.py``
     - REST 端点：SSE 流式聊天（内部格式 + AG-UI 协议）、会话增删查
   * - ``ai/agent.py``
     - ``AiAgent`` 编排类：加载历史 → RAG 检索 → 驱动 pydantic-ai
       Agent 图 → 流式产出事件 → 持久化消息
   * - ``ai/llm/client.py``
     - pydantic-ai Agent 工厂：text agent / vision agent 双实例，
       多 provider 兼容构建
   * - ``ai/llm/prompts.py``
     - 系统提示词模板（强制简体中文回答与思考）
   * - ``ai/tools/mcp_tools.py``
     - 把 MCP server 工具以 ``@agent.tool`` 注册到 pydantic-ai Agent，
       并实现 ``qcos_read_file`` 只读文件工具
   * - ``ai/deps.py``
     - ``AiDeps`` 依赖注入上下文 + contextvars 鉴权传播
   * - ``ai/session_store.py``
     - Redis 会话存储：按用户/会话隔离消息，TTL 过期 + 容量上限
   * - ``ai/rag/``
     - RAG 全链路：chunker（切分）/ embedder（向量化）/ indexer
       （离线入库）/ retriever（在线检索）
   * - ``ai/db.py``
     - 共享 async SQLAlchemy 引擎工厂（asyncpg / aiosqlite）
   * - ``db/models/ai_document_chunk.py``
     - ``ai_document_chunks`` 表模型，pgvector ``Vector(1024)`` 列

核心设计决策
--------------------

pydantic-ai 作为 LLM 框架
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

LLM 调用基于 **pydantic-ai** （``pydantic-ai==2.66.0``），而非 LangChain：

- 强类型 Agent 抽象，依赖注入（``deps``）原生支持
- 内置工具调用（``@agent.tool``）与流式事件
- 与 QCOS 现有 Pydantic 模型无缝集成
- 避免 LangChain 庞大依赖树（langchain / core / community 50+ MB）

多版本兼容层：pydantic-ai 迭代较快，命名跨版本变化（如
``OpenAIModel`` → ``OpenAIChatModel``、``TextPartDelta.delta`` →
``content_delta``、``_agent_graph`` 内部模块调整）。代码在 import 期通过
``inspect.signature`` 探测构造参数（如 ``_AGENT_SUPPORTS_INSTRUMENT``、
``_ANTHROPIC_MODEL_TAKES_CLIENT``），并 try/except 兜底导入，使锁定的
多个版本区间均可运行。

Provider 无关
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``_build_model()`` （``src/wy_qcos/ai/llm/client.py``）支持
``openai_compatible`` / ``openai`` / ``anthropic`` 三种 provider：

- **openai_compatible**：任何暴露 OpenAI ``/v1/chat/completions`` 协议的
  端点（vLLM / Ollama / DeepSeek / Moonshot / Qwen / LiteLLM 网关），
  由 ``[AI.AGENT] LLM_BASE_URL`` 指定
- **anthropic**：Claude 官方 API，经 ``AnthropicModel`` 直连
- 通过 ``[AI.AGENT] LLM_PROVIDER + LLM_MODEL + LLM_BASE_URL + LLM_API_KEY``
  切换，无需改代码

**超时防护**：``LLM_TIMEOUT`` （默认 60s）覆盖 OpenAI SDK 默认的 600s，
防止挂起的 LLM 端点长期占用 API worker 耗尽 worker 池。

文本与视觉双 Agent
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

维护两个独立 Agent 实例：

.. list-table::
   :header-rows: 1
   :widths: 25 25 50

   * - Agent
     - 配置来源
     - 特点
   * - text agent
     - ``LLM_*``
     - 文本对话 + 工具调用 + RAG，成本敏感
   * - vision agent
     - ``VISION_*`` （缺省回退 ``LLM_*``）
     - 仅图片分析；**不注册 MCP 工具**，防止图像分析意外触发工具调用

均通过 ``@lru_cache(maxsize=1)`` 单例构建，惰性初始化避免 import 副作用。

Agent 图手动驱动（Agent.iter）
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

文本对话使用 ``Agent.iter()`` 而非 ``run_stream()``：``iter()`` 逐节点
产出执行图（``ModelRequestNode`` → ``CallToolsNode`` → ... → ``End``），
是**单条 SSE 流内同时呈现工具调用事件与工具后 LLM 总结文本**的唯一方式。
``src/wy_qcos/ai/agent.py`` 对不同节点分类处理：

- **ModelRequestNode**：流式产出文本增量、思考链（thinking）增量、
  ``FunctionToolCallEvent`` （工具请求）
- **CallToolsNode**：pydantic-ai 在此执行工具，产出
  ``FunctionToolCallEvent`` / ``FunctionToolResultEvent``，
  后端将其透传给前端渲染"工具执行中/已完成"状态
- 运行结束后读取 ``agent_run.usage()`` 获取 token 用量，附在 ``done``
  事件返回（本地 provider 无 usage API 时为 ``None``）

超长文本增量按 ~2 字符切分后逐段 yield，前端获得平滑打字机效果。

RAG 设计
--------------------

知识库链路
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: text

   docs/sphinx/source/*.rst / *.md
        |  (离线) bin/qcos-ai-indexer.py
        v
   rag/chunker.py     按标题切分 (Markdown / RST AST 或正则回退)
        |
   rag/embedder.py    调 OpenAI 兼容 /embeddings 端点向量化
        |
   rag/indexer.py     pgvector upsert (ON CONFLICT DO UPDATE)
        v
   ai_document_chunks (PostgreSQL + pgvector)
        |
        |  (在线) 用户提问
        v
   rag/embedder.py    embed_single(question)
        |
   rag/retriever.py   cosine_distance top-K 查询
        |
   format_chunks_for_prompt()  拼为 "Relevant documentation excerpts"
        v
   注入 AiDeps.rag_context -> 系统提示

数据模型
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``ai_document_chunks`` 表（``src/wy_qcos/db/models/ai_document_chunk.py``）：

.. list-table::
   :header-rows: 1
   :widths: 25 20 55

   * - 字段
     - 类型
     - 说明
   * - ``id``
     - ``BigInteger``
     - 自增主键
   * - ``chunk_id``
     - ``String(256)``
     - 唯一标识 ``<source_file>#<index>``，upsert 冲突键
   * - ``source_file`` / ``section_path`` / ``title``
     - ``Text`` / ``Text`` / ``String(256)``
     - 来源文件、章节路径、标题（引用溯源）
   * - ``content``
     - ``Text``
     - chunk 正文
   * - ``embedding``
     - ``Vector(1024)``
     - pgvector 向量列；未安装 pgvector 时回退 ``Text`` （如 SQLite 单测）
   * - ``metadata``
     - ``JSONB``
     - 附加元数据

关键点：

- **向量检索** 用 pgvector 的 SQLAlchemy ORM 集成
  （``embedding.cosine_distance(...)``），无需裸 SQL/CAST
- **top-K** 默认 8（``RAG_TOP_K``），每 chunk 截断 2000 字符防 token 溢出
- **降级策略**：RAG 检索失败（embedding 端点不可达 / DB 异常）时记
  warning 并返回空上下文，对话降级为无 RAG 继续进行，**不中断聊天**
- **图片消息跳过 RAG**：vision 分支不检索文档
- **离线索引**：``bin/qcos-ai-indexer.py`` 独立脚本一次性入库，
  不占用 FastAPI 进程

会话管理
--------------------

Redis 键结构
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

键前缀定义于 ``src/wy_qcos/common/constant.py`` （``qcos/ai/...``）：

.. code-block:: text

   qcos/ai/session/{user_id}/{session_id}              # 会话元数据 (JSON)
   qcos/ai/messages/{user_id}/{session_id}             # 消息列表 (Redis List)
   qcos/ai/user_sessions/{user_id}                     # 用户会话集合 (Set)

机制要点（``src/wy_qcos/ai/session_store.py``）：

- **用户隔离**：所有键以 ``user_id`` 为第一段，天然按用户隔离
- **TTL 过期**：默认 7 天（``SESSION_TTL_SECONDS``），每次操作续期，
  防止 Redis 无限膨胀
- **容量上限**：消息列表超过 200 条时 ``LTRIM`` 保留最近 200 条
- **自动标题**：首条用户消息截取前 50 字符作为会话标题
- **pipeline 批量**：写入用 Redis pipeline 合并往返

REST API
--------------------

端点一览（均挂在 ``/v1/ai`` 前缀，见 ``src/wy_qcos/api/posiq/routes_rest/ai.py``）：

.. list-table::
   :header-rows: 1
   :widths: 35 15 50

   * - 端点
     - 方法
     - 说明
   * - ``/v1/ai/chat``
     - POST
     - 内部事件格式 SSE 流式聊天
   * - ``/v1/ai/chat/agui``
     - POST
     - AG-UI 协议标准事件流（TEXT_MESSAGE_* / TOOL_CALL_* / RUN_*）
   * - ``/v1/ai/sessions``
     - GET / POST
     - 列出当前用户会话 / 创建新会话
   * - ``/v1/ai/sessions/{id}``
     - GET / DELETE
     - 获取会话全部消息 / 删除会话
   * - ``/v1/ai/sessions/{id}/messages``
     - DELETE
     - 清空消息但保留会话记录（聊天工具栏"清空对话"按钮）

鉴权
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- **JWT 模式**：校验 ``Authorization: Bearer <token>``，解析出
  ``user_id`` 用于会话隔离；失败返回 401
- **非 JWT 模式** （no / virtual_instance）：透传合成用户 ``anonymous``
- **功能开关**：``Config.is_ai_agent_enabled()`` 为假时全部端点返回 503

AG-UI 事件映射
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

内部事件 → AG-UI 标准事件的映射（``_to_agui_event()``）：

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - 内部事件
     - AG-UI 事件
   * - ``chunk``
     - ``TEXT_MESSAGE_CONTENT`` （messageId + delta）
   * - ``thinking``
     - ``THINKING_CONTENT`` （自定义类型，前端路由到可折叠思考气泡）
   * - ``tool_call``
     - ``TOOL_CALL_START`` （toolCallId + toolCallName）
   * - ``tool_result``
     - ``TOOL_CALL_RESULT`` （toolCallId + content）
   * - ``error``
     - ``RUN_ERROR``
   * - ``done``
     - **不映射** （返回 None）——由外层生成器保证
       ``TEXT_MESSAGE_END`` 先于 ``RUN_FINISHED`` 的顺序，
       避免 RUN_FINISHED 重复下发导致前端停留在骨架屏状态

流关闭顺序：
``RUN_STARTED`` → ``TEXT_MESSAGE_START`` → 事件序列 →
``TEXT_MESSAGE_END`` → ``RUN_FINISHED`` （携带 token usage）。

工具集成（MCP in-process）
------------------------------

工具注册方式
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``register_mcp_tools()`` （``src/wy_qcos/ai/tools/mcp_tools.py``）把
MCP server（``src/wy_qcos/api/mcp/mcp_server.py``）的工具函数逐个包成
pydantic-ai 的 ``@agent.tool``：

.. code-block:: python

   @agent.tool
   async def qcos_list_devices(ctx: RunContext[AiDeps]) -> str:
       """List all available quantum computing devices."""
       with ctx.deps.auth_context():
           return await mcp_server.qcos_list_devices()

关键点：

- **必须用 ``@agent.tool``** （而非 ``@agent.tool_plain``）：每个工具都
  需要接收 ``RunContext`` 以取到 ``AiDeps``；pydantic-ai 拒绝 plain 工具
  上出现 ``RunContext`` 注解
- **in-process 直调**：直接 import mcp_server 的函数，不走网络，
  避免 SSRF 与性能损耗
- **工具清单**：设备 / 作业 / 系统类（list_devices、get_job_status、
  submit_job、cancel_jobs、get_system_health 等）+ proxy 可观测类
  （query_metrics、list_alerts、query_logs 等）+ ``qcos_read_file``
  文件只读工具

鉴权传播：auth_context
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

MCP 工具内部按"当前用户"鉴权（如 admin-only 操作）。AI 聊天请求来自
HTTP 层，需把该用户身份传进工具调用链：

- ``AiDeps`` （``src/wy_qcos/ai/deps.py``）携带 ``user_id`` / ``session_id``
  等上下文，在编排层构造后经 ``deps=`` 注入 Agent 运行
- 每个工具执行时先 ``with ctx.deps.auth_context()``：内部把实例设入
  ``contextvars.ContextVar``，MCP server 侧再 ``get_current_deps()`` 读取
- contextvars 天然适配 asyncio 并发：不同请求的多个 chat_stream
  并行运行时身份互不串扰

qcos_read_file 只读文件工具
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

AI 唯一的文件能力，**严格只读**，实现为 ``_read_local_file()``：

1. **无任何写/删/执行工具**：注册清单里文件类能力仅 read 一种
2. **只读打开**：``open(...)`` 后仅 ``readlines()``，返回带行号文本
3. **目录沙箱**：路径基于 ``Config.PROJECT_SRC_DIR`` 解析，必须位于
   ``src/wy_qcos/`` 之下（``is_relative_to`` 校验）
4. **拒绝绝对路径**：``Path(file_path).is_absolute()`` 直接拒绝
5. **拒绝路径穿越**：路径含 ``..`` 即拒绝
6. **模糊回退**：精确路径不存在时，在 ``src/wy_qcos/`` 内按 basename
   搜索（排除隐藏/缓存目录）；唯一匹配即用，多匹配报错让 LLM 重试
7. **读取上限**：``max_lines`` 默认 2000 行截断，防 token 溢出
8. **错误不抛出**：校验失败返回错误字符串而非异常，避免冒泡到
   pydantic-ai 的 ``tool_execute_error`` 处理器导致整条 SSE 流崩溃

系统提示词
--------------------

``src/wy_qcos/ai/llm/prompts.py`` 定义的文本/vision 系统提示词包含：

- **语言规则（最高优先级）**：无论用户用什么语言提问，最终答案与思考
  过程必须使用简体中文
- **工具调用强制规则**：涉及设备/作业/状态/文件等真实数据问题时必须
  发起真实 function call，禁止只以文字描述"我将调用…"；工具失败或
  返回空时如实告知，禁止编造数据
- **工具清单**：与 ``register_mcp_tools`` 注册集严格同步

配置
--------------------

开关层级
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

功能受两级开关门控（``Config.is_ai_agent_enabled()``）：

.. code-block:: text

   [AI] ENABLED = true          # 全局 AI 总开关（同时控制 MCP server）
   [AI.AGENT] ENABLED = true    # AI Agent 聊天子开关

只有两级都为真时 ``/v1/ai/*`` 才注册并可用；任一为假时端点不注册/503。

AI.AGENT 配置项
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``AIAgentSection`` （``src/wy_qcos/common/config.py``）：

.. list-table::
   :header-rows: 1
   :widths: 35 15 50

   * - 字段
     - 默认值
     - 说明
   * - ``LLM_PROVIDER``
     - ``openai_compatible``
     - provider 类型（openai_compatible / openai / anthropic）
   * - ``LLM_BASE_URL``
     - ``http://vllm:8000/v1``
     - LLM 端点（托管 provider 忽略）
   * - ``LLM_API_KEY``
     - ``""``
     - API key（本地端点可为空）
   * - ``LLM_MODEL``
     - ``Qwen/Qwen2.5-72B-Instruct``
     - 模型名
   * - ``LLM_TIMEOUT``
     - ``60.0``
     - LLM HTTP 超时秒数
   * - ``VISION_PROVIDER / VISION_BASE_URL / VISION_API_KEY / VISION_MODEL``
     - 空
     - 视觉模型独立配置，空值回退 ``LLM_*``
   * - ``IMAGE_MAX_COUNT_PER_MESSAGE``
     - 4
     - 单消息图片上限
   * - ``IMAGE_MAX_BYTES_PER_IMAGE``
     - 5242880
     - 单图字节上限（base64 估算 4/3）
   * - ``EMBEDDING_BASE_URL / EMBEDDING_API_KEY / EMBEDDING_MODEL / EMBEDDING_DIM``
     - - / ``""`` / ``bge-m3`` / 1024
     - Embedding 端点配置
   * - ``SESSION_TTL_SECONDS``
     - 604800
     - 会话 TTL（默认 7 天）
   * - ``RAG_TOP_K``
     - 8
     - RAG 检索 chunk 数

附件校验（``_validate_attachments()``）：
图片仅允许 png/jpeg/webp/gif，超数量/超大小直接 raise（HTTP 层转为 4xx）。

数据库访问
--------------------

``src/wy_qcos/ai/db.py`` 提供共享 async SQLAlchemy 引擎：

- 连接串从 ``[DATABASE] QCOS_DATABASE_CONNECTION_URL`` 派生：
  ``postgresql://`` → ``postgresql+asyncpg://``，
  ``sqlite://`` → ``sqlite+aiosqlite://``
- 进程级单例：``pool_size=10``，``max_overflow=20``，``pool_pre_ping=True``
- 日志对连接串脱敏（只输出 ``@`` 之后部分）
- ``close_async_engine()`` 供进程退出时释放

图片消息处理流程
--------------------

1. HTTP 层附件经 Pydantic 校验后 base64 透传
2. 编排层校验数量/大小/媒体类型，超限 raise
3. base64 解码为字节，包成 pydantic-ai 的 ``BinaryContent``
   （自动序列化为 OpenAI ``image_url`` 格式）
4. 走 vision agent（``run_stream`` 纯文本流，无工具事件）
5. 图片消息**不做 RAG 检索**、不注册工具

安全设计汇总
--------------------

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - 威胁
     - 防护措施
   * - 越权访问数据
     - JWT 鉴权 + ``auth_context()`` contextvars 传播，工具按当前用户
       权限执行（admin-only 工具非 admin 用户不可用）
   * - 用户间会话串扰
     - Redis 键第一段为 user_id，天然隔离
   * - 文件系统越界读取
     - ``qcos_read_file`` 沙箱：拒绝绝对路径与 ``..``，限定
       ``src/wy_qcos/`` 树，无写/删/执行能力
   * - LLM 端点挂起拖垮 API
     - ``LLM_TIMEOUT`` 有限超时；超时向前端返回 RUN_ERROR
       而非无限占用 worker
   * - 大响应 / token 溢出
     - RAG chunk 2000 字符截断、文件读取 2000 行截断、
       图片数量/大小上限
   * - 配置中的敏感信息
     - ``LLM_API_KEY`` / ``EMBEDDING_API_KEY`` 等字段标记
       ``sensitive``，输出时脱敏
   * - 无界资源消耗
     - 会话 TTL + 消息 200 条 LTRIM

模块组织
--------------------

.. code-block:: text

   src/wy_qcos/ai/
   ├── __init__.py
   ├── agent.py            # AiAgent 编排：RAG + Agent.iter() + 持久化
   ├── db.py               # 共享 async SQLAlchemy 引擎工厂
   ├── deps.py             # AiDeps + contextvars 鉴权传播
   ├── session_store.py    # Redis 会话存储
   ├── llm/
   │   ├── client.py       # pydantic-ai Agent 工厂（text + vision）
   │   └── prompts.py      # 系统提示词
   ├── rag/
   │   ├── chunker.py      # Markdown / RST 文档切分
   │   ├── embedder.py     # OpenAI 兼容 embedding 客户端
   │   ├── indexer.py      # 离线批量入库（bin/qcos-ai-indexer.py）
   │   └── retriever.py    # pgvector top-K 检索
   └── tools/
       └── mcp_tools.py    # MCP 工具桥接 + qcos_read_file

依赖（``pyproject.toml`` AI 相关）：

- ``pydantic-ai==2.66.0``：Agent 框架
- ``openai==3.41.0`` / ``anthropic==2.3.0``：LLM SDK
- ``pgvector==0.5.1``：向量列支持
- ``docutils``：RST AST 切分
- ``pillow``：图片处理

与相关组件的关系
--------------------

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - 组件
     - 关系
   * - MCP server（``/v1/ai/mcp``）
     - 同属 AI 功能族，共享 ``[AI].ENABLED`` 总开关；Agent 的全部业务
       工具即 MCP server 工具的 in-process 复用
   * - 反向代理（``/v1/proxy/*``）
     - proxy 可观测类工具的下游：MCP server 内通过 QCOS 自身的
       ``/v1/proxy/<service>`` 访问 Prometheus / Alertmanager /
       VictoriaLogs
   * - Redis
     - 会话/消息存储；沿用现有 ``REDIS_URL``
   * - PostgreSQL + pgvector
     - RAG 知识库；沿用现有 ``[DATABASE]`` 连接
   * - WebUI
     - 消费 ``/v1/ai/chat/agui`` AG-UI 事件流与 sessions REST；
       前端设计不在本文范围
