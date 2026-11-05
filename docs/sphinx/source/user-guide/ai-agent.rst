
.. _ai-agent:

AI 智能助手
===========

QCOS WebUI 内置 AI 智能助手，支持自然语言对话、知识库检索（RAG）、
MCP 工具调用和图片理解。

功能特性
--------

- **对话能力**：询问 QCOS 使用方法、排查问题、生成 QASM 代码片段
- **知识库检索**：基于 QCOS Sphinx 文档仓的语义检索，回答引用具体文档段落
- **工具调用**：AI 可主动调用 MCP server 查询设备状态、作业进度等
- **多用户隔离**：每个用户的对话上下文独立存储，互不干扰
- **双形态显示**：右侧 Drawer 与浮动 Dialog 可随时切换
- **图片理解**：支持粘贴/拖拽上传量子电路图、代码截图等

快速开始
--------

1. 点击导航栏右侧的 AI 机器人图标（或按 ``Ctrl+/``）打开 AI 助手
2. 在输入框中输入问题，按 ``Ctrl+Enter`` 或点击"发送"
3. 如需上传图片，点击输入框工具栏的图片图标，或直接粘贴/拖拽图片

配置
----

AI 助手的配置位于 ``etc/qcos/qcos.toml`` 的 ``[AI]`` 节：

.. code-block:: toml

   [AI]
   ENABLED = true
   LLM_PROVIDER = "openai_compatible"
   LLM_BASE_URL = "http://vllm:8000/v1"
   LLM_MODEL = "Qwen/Qwen2.5-72B-Instruct"
   VISION_MODEL = ""
   EMBEDDING_MODEL = "bge-large-zh-v1.5"
   SESSION_TTL_SECONDS = 604800

支持的 LLM Provider
~~~~~~~~~~~~~~~~~~~

- ``openai_compatible``：任何兼容 OpenAI ``/v1/chat/completions`` 协议的端点
  （vLLM、Ollama、DeepSeek、Moonshot、Qwen、LiteLLM 等）
- ``openai``：官方 OpenAI API
- ``anthropic``：Claude（通过 pydantic-ai 的 AnthropicModel）

知识库索引
----------

AI 助手的知识库来源于 QCOS 的 Sphinx 文档。部署后需要构建索引：

.. code-block:: bash

   python bin/qcos-ai-indexer.py --docs-dir docs/sphinx/source --recreate

索引存储在 PostgreSQL 的 ``ai_document_chunks`` 表中（pgvector 扩展）。

快捷键
------

- ``Ctrl+/``：显示 / 隐藏 AI 助手
- ``Ctrl+Shift+/``：在 Drawer 与 Floating 模式之间切换
- ``Ctrl+Enter``：发送消息
