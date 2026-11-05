.. _ai-embedding:

Embedding 服务部署
==================

QCOS AI 的 RAG（知识库检索）功能依赖 Embedding 服务将文本转换为向量。
本文介绍如何部署 `Text Embeddings Inference (TEI)`_ 服务以及离线环境下
的模型下载方法。

.. _Text Embeddings Inference (TEI): https://github.com/huggingface/text-embeddings-inference

.. contents:: 目录
   :local:
   :depth: 2

服务部署
--------

Docker Compose 部署（推荐）
~~~~~~~~~~~~~~~~~~~~~~~~~~~

QCOS 提供了现成的 docker-compose 配置和启动脚本：

.. code-block:: bash

   cd build-scripts

   # 编辑 .env，确保以下配置正确
   # TEI_IMAGE_NAME=ghcr.io/huggingface/text-embeddings-inference
   # TEI_IMAGE_VERSION=cpu-1.9
   # TEI_MODEL_ID=BAAI/bge-m3
   # TEI_LISTEN_PORT=8080
   # TEI_OMP_NUM_THREADS=8

   # 启动服务
   ./run-docker-ai.sh

服务启动后， embedding API 地址为 ``http://<host>:8080/v1``。

Docker 直接运行
~~~~~~~~~~~~~~~

.. code-block:: bash

   docker run -d \
     --name tei-bge-m3 \
     -p 8080:8080 \
     -e OMP_NUM_THREADS=8 \
     -v tei-cache:/root/.cache/huggingface \
     ghcr.io/huggingface/text-embeddings-inference:cpu-1.9 \
     --model-id BAAI/bge-m3 \
     --port 8080

参数说明：

- ``--model-id``: HuggingFace 模型 ID 或本地路径
- ``--port``: 服务监听端口
- ``OMP_NUM_THREADS``: CPU 并行线程数，建议设为 CPU 核心数
- ``-v tei-cache:/root/.cache/huggingface``: 模型缓存卷，避免重复下载

验证服务
~~~~~~~~

.. code-block:: bash

   # 健康检查
   curl http://localhost:8080/health

   # 测试 embedding
   curl -X POST http://localhost:8080/v1/embeddings \
     -H "Content-Type: application/json" \
     -d '{
       "model": "BAAI/bge-m3",
       "input": "量子计算操作系统"
     }'

QCOS 配置对接
-------------

在 ``etc/qcos/qcos.toml`` 中配置 embedding 服务地址：

.. code-block:: toml

   [AI.AGENT]
   EMBEDDING_BASE_URL = "http://<tei-host>:8080/v1"
   EMBEDDING_MODEL = "BAAI/bge-m3"
   EMBEDDING_DIM = 1024

.. note::
   ``EMBEDDING_DIM`` 必须与所选模型的实际维度一致。
   BGE-M3 的维度为 1024，BGE-large-zh 也是 1024。

离线模型下载
------------

无外网环境下，可通过以下方式获取模型文件。

方案一：ModelScope（推荐，国内源）
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

`BAAI/bge-m3`_ 在 ModelScope 上有官方镜像，无需翻墙：

.. _BAAI/bge-m3: https://modelscope.cn/models/BAAI/bge-m3

.. code-block:: bash

   # 安装 modelscope
   pip install modelscope

   # 下载模型到本地目录
   modelscope download --model BAAI/bge-m3 --local_dir ./bge-m3

   # 或使用 Python API
   python -c "
   from modelscope import snapshot_download
   model_dir = snapshot_download('BAAI/bge-m3', local_dir='./bge-m3')
   print(f'模型已下载到: {model_dir}')
   "

方案二：HuggingFace 镜像站
~~~~~~~~~~~~~~~~~~~~~~~~~~

使用 `hf-mirror.com`_ 镜像：

.. _hf-mirror.com: https://hf-mirror.com

.. code-block:: bash

   # 方法 1：使用 huggingface-cli
   pip install huggingface-hub
   export HF_ENDPOINT=https://hf-mirror.com
   huggingface-cli download BAAI/bge-m3 --local-dir ./bge-m3

   # 方法 2：使用 hf 命令（huggingface-hub v2 CLI）
   HF_ENDPOINT=https://hf-mirror.com hf download BAAI/bge-m3 --local-dir ./bge-m3

方案三：手动下载必需文件
~~~~~~~~~~~~~~~~~~~~~~~~

如果只需 TEI 运行必需的核心文件，可手动下载：

.. code-block:: bash

   mkdir -p ./bge-m3 && cd ./bge-m3

   # 从镜像站逐个下载
   wget https://hf-mirror.com/BAAI/bge-m3/resolve/main/config.json
   wget https://hf-mirror.com/BAAI/bge-m3/resolve/main/config_sentence_transformers.json
   wget https://hf-mirror.com/BAAI/bge-m3/resolve/main/model.onnx
   wget https://hf-mirror.com/BAAI/bge-m3/resolve/main/tokenizer.json
   wget https://hf-mirror.com/BAAI/bge-m3/resolve/main/tokenizer_config.json
   wget https://hf-mirror.com/BAAI/bge-m3/resolve/main/sentencepiece.bpe.model
   wget https://hf-mirror.com/BAAI/bge-m3/resolve/main/1_Pooling/config.json
   wget https://hf-mirror.com/BAAI/bge-m3/resolve/main/modules.json

方案四：有外网机器预下载 + 离线拷贝
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

在有外网的机器上下载，然后拷贝到目标机器：

.. code-block:: bash

   # 有外网的机器上执行
   docker run --rm \
     -v tei-cache:/root/.cache/huggingface \
     ghcr.io/huggingface/text-embeddings-inference:cpu-1.9 \
     --model-id BAAI/bge-m3 \
     --port 9999

   # 导出模型缓存
   docker run --rm \
     -v tei-cache:/data \
     -v $(pwd):/backup \
     alpine tar czf /backup/tei-cache.tar.gz -C /data .

   # 拷贝 tei-cache.tar.gz 到目标机器后导入
   docker run --rm \
     -v tei-cache:/data \
     -v $(pwd):/backup \
     alpine tar xzf /backup/tei-cache.tar.gz -C /data

   # 启动服务（使用缓存，无需联网）
   docker-compose -f docker-compose-ai.yaml up -d

离线环境启动
------------

使用本地模型路径启动 TEI（完全离线）：

.. code-block:: bash

   docker run -d \
     --name tei-bge-m3 \
     -p 8080:8080 \
     -e OMP_NUM_THREADS=8 \
     -v /data/models/bge-m3:/models/bge-m3:ro \
     ghcr.io/huggingface/text-embeddings-inference:cpu-1.9 \
     --model-id /models/bge-m3 \
     --port 8080

或修改 ``docker-compose-ai.yaml``：

.. code-block:: yaml

   services:
     tei-bge-m3:
       image: ${REGISTRY}${TEI_IMAGE_NAME}:${TEI_IMAGE_VERSION}
       container_name: tei-bge-m3
       restart: unless-stopped
       network_mode: "host"
       read_only: true
       security_opt:
         - no-new-privileges:true
       tmpfs:
         - /tmp
       environment:
         - OMP_NUM_THREADS=${TEI_OMP_NUM_THREADS:-8}
       volumes:
         # 直接挂载本地模型目录
         - /data/models/bge-m3:/models/bge-m3:ro
       command:
         - '--model-id'
         - '/models/bge-m3'  # 使用本地路径
         - '--port'
         - '${TEI_LISTEN_PORT:-8080}'
       logging:
         driver: "json-file"
         options:
           max-size: "50m"
           max-file: "5"

常用 Embedding 模型推荐
-----------------------

.. list-table::
   :header-rows: 1
   :widths: 20 15 15 50

   * - 模型
     - 维度
     - 大小
     - 说明
   * - ``BAAI/bge-m3``
     - 1024
     - ~2.3GB
     - 多语言、长文本（8192 tokens），推荐
   * - ``BAAI/bge-large-zh-v1.5``
     - 1024
     - ~1.3GB
     - 中文优化，速度快
   * - ``BAAI/bge-base-zh-v1.5``
     - 768
     - ~400MB
     - 轻量级中文模型
   * - ``BAAI/bge-small-zh-v1.5``
     - 512
     - ~100MB
     - 极简中文模型，资源受限环境适用

故障排查
--------

模型下载失败：DNS 解析错误
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: text

   Error: Could not download model artifacts
   Caused by: dns error: failed to lookup address information

**原因**：服务器无法访问 huggingface.co。

**解决**：
1. 使用 ``HF_ENDPOINT=https://hf-mirror.com`` 环境变量
2. 或使用 ModelScope 下载（见上方"离线模型下载"）

模型下载失败：连接重置
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: text

   Error: Local entry not found. [Errno 104] Connection reset by peer

**原因**：网络连接被重置，通常是防火墙或网络策略限制。

**解决**：
1. 使用 ModelScope 国内源
2. 在有外网的机器上下载后离线拷贝

Embedding 维度不匹配
~~~~~~~~~~~~~~~~~~~~

QCOS 日志中出现向量维度错误。

**解决**：确保 ``qcos.toml`` 中 ``EMBEDDING_DIM`` 与模型实际维度一致。
BGE-M3 / BGE-large-zh 为 1024，BGE-base-zh 为 768，BGE-small-zh 为 512。

服务启动后无法访问
~~~~~~~~~~~~~~~~~~

检查防火墙和端口监听：

.. code-block:: bash

   # 检查容器状态
   docker ps | grep qcos-text-embeddings

   # 检查端口监听
   ss -tlnp | grep 8080

   # 查看容器日志
   docker logs qcos-text-embeddings
