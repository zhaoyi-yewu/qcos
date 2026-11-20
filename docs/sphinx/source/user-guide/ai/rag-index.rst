.. _ai-rag-index:

知识库索引构建（RAG Index）
===========================

AI 智能体的知识库检索（RAG）功能依赖对 QCOS Sphinx 文档预先构建的
向量索引。本文介绍如何使用 ``qcos-ai-indexer.py`` 脚本构建和刷新索引。

工作原理
--------

索引构建流程分为三步：

1. **切分（Chunk）**：扫描文档目录下所有 ``.rst`` / ``.md`` 文件，
   按章节结构切分为文本片段
2. **向量化（Embed）**：调用 Embedding 服务将每个片段转换为向量
3. **写入（Upsert）**：按 ``chunk_id`` 写入 PostgreSQL 的
   ``ai_document_chunks`` 表（pgvector 扩展），已存在的片段执行更新

前置条件
--------

1. **数据库迁移已执行**：``ai_document_chunks`` 表由 Alembic 迁移创建，
   索引脚本不会自动建表：

   .. code-block:: bash

      alembic upgrade head

2. **数据库配置正确**：索引脚本从配置文件的 ``[DATABASE]`` 节读取
   数据库连接地址，数据库需已启用 pgvector 扩展。

3. **Embedding 服务可用**：向量化依赖 ``[AI.AGENT]`` 节配置的
   Embedding 服务（``EMBEDDING_BASE_URL`` / ``EMBEDDING_MODEL`` /
   ``EMBEDDING_DIM``）。服务部署方法请参考 :doc:`embedding`。

构建索引
--------

在 QCOS 源码仓根目录执行：

.. code-block:: bash

   python bin/qcos-ai-indexer.py --docs-dir docs/sphinx/source --recreate

命令参数
--------

.. list-table::
   :header-rows: 1
   :widths: 25 25 50

   * - 参数
     - 默认值
     - 说明
   * - ``-c`` / ``--config-file``
     - ``/etc/qcos/qcos.toml``
     - QCOS 配置文件路径，从中读取 ``[DATABASE]`` 与
       ``[AI.AGENT]`` 配置
   * - ``--docs-dir``
     - ``docs/sphinx/source``
     - Sphinx 文档源目录，相对当前工作目录。支持传入多个目录
       （空格分隔），会合并索引
   * - ``--recreate``
     - 关闭
     - 删除 ``ai_document_chunks`` 表全部数据后重建索引。
       不加该参数时按 ``chunk_id`` 增量 upsert
   * - ``--batch-size``
     - ``32``
     - 每批发送给 Embedding 服务的片段数量

增量更新与全量重建
------------------

- **增量更新** （不加 ``--recreate`` ）：按 ``chunk_id`` upsert，适合
  日常文档小幅修改。注意已从文档仓删除的源文件对应的旧片段会残留在
  索引中。
- **全量重建** （加 ``--recreate`` ）：清空表后重建，适合文档结构大幅
  调整后的清理。为防止临时故障（文档目录不存在、Embedding 服务不可达
  等）导致索引被意外清空，脚本只在所有文件切分成功且产出非空片段后
  才执行删除操作；表结构本身不受影响（schema 由 Alembic 迁移管理）。

验证
----

构建成功后日志末尾输出 ``Indexing complete``。随后打开 WebUI 的
AI 智能体提问 QCOS 用法类问题，回答中引用具体文档段落即表明
RAG 检索已生效。
