.. _ai-agent:

AI 智能体
===========

QCOS WebUI 内置 AI 智能体，支持自然语言对话、知识库检索（RAG）、
MCP 工具调用和图片理解。

功能特性
--------

- **对话能力**：询问 QCOS 使用方法、排查问题、生成 QASM 代码片段
- **多模型选择**：可在配置的多个模型间切换，同一会话允许混合模型
- **知识库检索**：基于 QCOS Sphinx 文档仓的语义检索，回答引用具体文档段落
- **工具调用**：AI 可主动调用 MCP server 查询设备状态、作业进度等
- **多用户隔离**：每个用户的对话上下文独立存储，互不干扰
- **双形态显示**：右侧 Drawer 与浮动 Dialog 可随时切换
- **问题编辑重试**：修改历史问题后，从该问题开始重新生成回答
- **图片理解**：支持粘贴/拖拽上传量子电路图、代码截图等（需当前模型支持视觉）

快速开始
--------

1. 点击导航栏右侧的 AI 机器人图标（或按 ``Ctrl+/``）打开 AI 智能体
2. 在输入框中输入问题，按 ``Ctrl+Enter`` 或点击"发送"
3. 如需上传图片，点击输入框工具栏的图片图标，或直接粘贴/拖拽图片

选择模型
--------

输入框下方工具栏（Token 圆环左侧）提供模型下拉菜单：

- 菜单项展示模型显示名及上游 MODEL；当前选中的模型高亮显示
- **切换只影响后续消息**，已发出和排队中的消息仍使用各自发送时的模型
- 排队消息后切换模型，不会改写队列中消息的快照
- 编辑历史问题重试、重新生成回答时，使用执行操作时当前选中的模型
- 会话会保存最近使用的模型：刷新页面或重新打开会话时自动恢复；
  新建会话重置为配置中的默认模型（``[[AI.AGENT.MODELS]]`` 第一项）
- 若会话保存的模型已从配置中删除，自动回退到默认模型
- 旧版本服务端没有模型清单接口时，菜单禁用并显示"默认模型"，
  普通对话不受任何影响

**视觉限制**：当前模型 ``VISION_ENABLED=false`` 时图片按钮禁用；
若已附加图片后切换到无视觉模型，发送会被阻止并提示，附件不会
被静默丢弃，可切回支持视觉的模型后再发送。

编辑历史问题
------------

1. 点击用户问题下方的编辑按钮，在弹窗中修改问题内容
2. 点击“重新生成”，系统会删除该问题及其后续回答，再以新问题生成回答
3. 原问题中的图片附件会自动保留；点击“取消”不会修改会话历史

配置
----

AI 智能体的配置位于 ``etc/qcos/qcos.toml`` 的 ``[AI]`` 节，详见 :ref:`ai-configuration` ：

.. code-block:: toml

   [AI]
   ENABLED = true

   [AI.AGENT]
   EMBEDDING_MODEL = "bge-large-zh-v1.5"
   SESSION_TTL_SECONDS = 604800

   # 第一项为默认模型
   [[AI.AGENT.MODELS]]
   ID = "qwen-main"
   PROVIDER = "openai_compatible"
   BASE_URL = "http://vllm:8000/v1"
   MODEL = "Qwen/Qwen2.5-72B-Instruct"
   VISION_ENABLED = false

支持的 LLM Provider
~~~~~~~~~~~~~~~~~~~

- ``openai_compatible``：任何兼容 OpenAI ``/v1/chat/completions`` 协议的端点
  （vLLM、Ollama、DeepSeek、Moonshot、Qwen、LiteLLM 等）
- ``openai``：官方 OpenAI API
- ``anthropic``：Claude（通过 pydantic-ai 的 AnthropicModel）

AI 智能体的完整配置项说明（多模型 / 视觉 / Embedding / 会话 / 图片限制等）
请参考 :doc:`configuration`。

知识库索引
----------

AI 智能体的知识库来源于 QCOS 的 Sphinx 文档，部署后需要手动构建 RAG
索引才能启用知识库检索。索引构建的详细步骤请参考 :doc:`rag-index`。

快捷键
------

- ``Ctrl+/``：显示 / 隐藏 AI 智能体
- ``Ctrl+Shift+/``：在 Drawer 与 Floating 模式之间切换
- ``Ctrl+Enter``：发送消息

相关章节
--------

- :ref:`ai-configuration` — 完整配置项说明
- :ref:`ai-embedding` — Embedding 服务部署
- :ref:`ai-rag-index` — RAG 知识库索引构建
