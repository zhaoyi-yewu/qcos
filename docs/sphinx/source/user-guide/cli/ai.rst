AI Agent 命令
================

AI Agent 命令提供单次提问和交互式多轮对话两种使用方式，支持流式输出、
RAG 知识库检索、MCP 工具调用和会话管理。

使用前请按 :doc:`auth` 完成用户登录，并确保服务端已启用 AI Agent、完成模型配置，
详见 :doc:`/user-guide/ai/configuration`。

单次提问：ai-ask
----------------------

``ai-ask`` 用于提交一个问题并输出 AI Agent 的流式回答。

命令行参数
~~~~~~~~~~~~~~~

.. code-block:: shell

   usage: qcos-cli ai-ask [-h] [--session-id SESSION_ID] [--model MODEL]
                          [--no-rag] [--show-tools]
                          message [message ...]

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - 参数
     - 说明
   * - ``message``
     - 问题内容；包含空格时使用引号包裹。
   * - ``--session-id SESSION_ID``
     - 继续指定的已有会话，保留该会话的上下文。
   * - ``--model MODEL``
     - 指定本次提问使用的模型 ID（见 ``ai-models``）。显式选模时会先查询
       服务端模型清单并校验；旧版服务端无此能力时会提示升级，不会去掉
       模型后自动重试。未指定时不做预检，由服务端恢复会话模型或使用默认项。
   * - ``--no-rag``
     - 本次提问不检索 RAG 知识库，默认启用 RAG 检索。
   * - ``--show-tools``
     - 在回答中显示工具调用和工具结果标记，默认不显示。

典型场景示例
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 提问并启用默认的 RAG 检索
   qcos-cli ai-ask "如何查询当前可用的量子设备？"

   # 在指定会话中继续提问，并显示工具调用标记
   qcos-cli ai-ask "继续分析上面的结果" --session-id <SESSION_ID> --show-tools

   # 使用指定模型提问
   qcos-cli ai-ask "生成一个 Bell 态线路" --model kimi-k3

   # 不使用 RAG 知识库检索
   qcos-cli ai-ask "解释量子线路中的 CNOT 门" --no-rag

模型清单：ai-models
----------------------

``ai-models`` 列出服务端配置的全部模型，包括 ID、显示名、上游 MODEL、
默认标记（``*``）和视觉能力：

.. code-block:: shell

   $ qcos-cli ai-models
   * qwen-main: Qwen 主模型  (model=Qwen/Qwen2.5-72B-Instruct, text-only)
     kimi-k3: Kimi K3  (model=moma/kimi-k3, vision)
   (* = default model)

交互式对话：ai-chat
----------------------

``ai-chat`` 启动交互式多轮对话。直接输入问题即可发送；首条消息自动创建会话，
后续消息沿用当前会话上下文。

命令行参数
~~~~~~~~~~~~~~~

.. code-block:: shell

   usage: qcos-cli ai-chat [-h] [--session-id SESSION_ID] [--model MODEL]
                           [--no-rag] [--show-tools]

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - 参数
     - 说明
   * - ``--session-id SESSION_ID``
     - 启动时恢复指定的已有会话。
   * - ``--model MODEL``
     - 启动时选择模型 ID，仅影响后续消息；规则同 ``ai-ask --model``。
   * - ``--no-rag``
     - 启动时关闭 RAG 检索，可在会话中通过 ``/rag on`` 重新开启。
   * - ``--show-tools``
     - 启动时显示工具调用和工具结果标记，可在会话中动态切换。

典型场景示例
~~~~~~~~~~~~~~~

.. code-block:: shell

   # 启动新会话
   qcos-cli ai-chat

   # 恢复已有会话
   qcos-cli ai-chat --session-id <SESSION_ID>

   # 启动会话并显示工具调用标记
   qcos-cli ai-chat --show-tools

交互命令
~~~~~~~~~~~~~~~

交互界面中输入以 ``/`` 开头的命令管理会话和输出选项：

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - 命令
     - 说明
   * - ``/new [title]``
     - 新建并切换到会话，可选指定标题；未指定时使用 ``CLI conversation``。
       新会话重置为服务端默认模型。
   * - ``/list``
     - 列出当前用户的会话，星号标记当前会话。
   * - ``/use <session_id>``
     - 切换到指定会话，并恢复该会话保存的模型（若模型已被删除则回退默认）。
   * - ``/history``
     - 显示当前会话的历史消息（助手消息附带实际使用的上游模型名）。
   * - ``/delete <session_id>``
     - 删除指定会话；删除当前会话后清除当前会话选择。
   * - ``/model``
     - 列出可选模型和当前选择。
   * - ``/model <model_id>``
     - 校验后切换模型，只影响后续消息，不影响已发出的请求。
   * - ``/model default``
     - 显式设为服务端默认模型。
   * - ``/rag on|off``
     - 开启或关闭 RAG 检索。
   * - ``/tools on|off``
     - 开启或关闭工具调用和工具结果标记。
   * - ``/help``
     - 显示交互命令帮助。
   * - ``/exit`` 或 ``/quit``
     - 退出交互式对话。

例如，在 ``ai>`` 提示符后依次输入以下命令，可新建会话、关闭 RAG 并提问：

.. code-block:: text

   ai> /new 线路问题排查
   ai[SESSION_ID]> /rag off
   ai[SESSION_ID]> 解释量子线路中的 CNOT 门

切换模型示例：

.. code-block:: text

   ai> /model
   * qwen-main: Qwen 主模型  (model=Qwen/Qwen2.5-72B-Instruct, text-only)
     kimi-k3: Kimi K3  (model=moma/kimi-k3, vision)
   Current model: server default (qwen-main)
   ai> /model kimi-k3
   Model set to: kimi-k3
   ai> 分析这张线路图   # 后续消息使用 kimi-k3
