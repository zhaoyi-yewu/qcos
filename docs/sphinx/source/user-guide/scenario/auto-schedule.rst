自动调度场景
======================

自动调度是 QCOS 的核心能力之一，系统根据量子计算任务的特征（量子比特数、
量子技术路线、门保真度、设备可用率等）自动选择最合适的量子计算设备，
无需用户手动指定 ``--backend``。

自动调度通过 **资源规格（Flavor）** 定义调度策略，通过 **额外调度参数
（extra_specs）** 实现单次作业的动态覆盖。资源规格关联一个或多个设备组
（Device Group），设备组中包含具体设备。

.. note::

   - 自动调度需要搭配 ``--flavor`` 参数使用，不能与 ``--backend`` 同时指定
   - ``extra_specs`` 中的同名字段会覆盖 Flavor 中定义的值
   - 支持的 ``extra_specs`` 字段详见 :doc:`/design/api/job` 中的
     "额外调度参数 (extra_specs)" 章节

前置准备
****************

查看当前可用设备
~~~~~~~~~~~~~~~~~

提交自动调度任务前，先查看系统中已注册的设备及其技术路线：

.. code-block:: shell

   # 查询所有设备信息
   qcos-cli list-devices

根据 ``list-devices`` 输出的 ``name`` 和 ``tech_type`` 字段，
确定后续要加入设备组的设备名称。

创建设备组
~~~~~~~~~~~~~~~~

设备组（Device Group）是自动调度的设备池，一个设备组可包含多种技术路线的设备。

.. code-block:: shell

   # 创建设备组 dg1，加入 5 台设备（覆盖 3 种技术路线）
   # 设备名根据 list-devices 实际输出填写
   qcos-cli create-device-group dg1 \
       --device cetc_baihua lq_mq02 lq_qz01_surface quafu wy_hanyuan1

.. tip::

   - 设备组中的设备可以属于不同的技术路线（如超导、离子阱、中性原子等）
   - 一个 Flavor 可关联多个设备组，实现跨设备组的调度

场景示例
****************

支持自动调度（量子计算任务特征算力调度能力）
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

通过资源规格定义调度策略，系统根据任务特征自动匹配最优设备。

.. code-block:: shell

   # 1. 查看设备，确认当前可用设备及技术路线
   qcos-cli list-devices

   # 2. 创建设备组 dg1，加入 5 台设备（3 种技术路线）
   qcos-cli create-device-group dg1 \
       --device cetc_baihua lq_mq02 lq_qz01_surface quafu wy_hanyuan1

   # 3. 创建资源规格 f1：
   #    要求量子技术路线为超导（superconducting）
   #    最小量子比特数为 18
   qcos-cli create-flavor f1 \
       --property qc:tech_types=superconducting \
       --min-qubits 18 \
       --device-groups dg1

   # 4. 使用资源规格 f1 提交量子任务
   qcos-cli submit-job \
       --code-type qasm \
       --shots 1024 \
       --flavor f1 \
       -f ./samples/qasm/2.0/simple-qasm-2q-2sg-1dg.qasm

   # 5. 查看backend字段看哪台设备被调度到，并查看结果，确认调度和结果符合预期
   qcos-cli get-job-results {JOB_ID}

4. 2 种异构算力调度
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

通过 ``extra_specs`` 动态指定比特数范围，在不同技术路线的设备上
执行相同量子电路，验证异构算力调度能力。

**场景1：调度到 24 比特超导量子计算机**

.. code-block:: shell

   # 提交到 24 量子比特的设备（需保证该设备为超导技术路线）
   qcos-cli submit-job \
       --code-type qasm \
       --shots 1024 \
       --flavor g1.all \
       --extra-specs '{"qc:min_qubits": 24, "qc:max_qubits": 24}' \
       -f ./samples/qasm/2.0/simple-qasm-2q-2sg-1dg.qasm

   # 查看结果，确认调度符合预期
   qcos-cli get-job-results {JOB_ID}

**场景2：调度到 100 比特中性原子量子计算机**

.. code-block:: shell

   # 提交到 100 量子比特的设备（需保证该设备为中性原子技术路线）
   qcos-cli submit-job \
       --code-type qasm \
       --shots 1024 \
       --flavor g1.all \
       --extra-specs '{"qc:min_qubits": 100, "qc:max_qubits": 100}' \
       -f ./samples/qasm/2.0/simple-qasm-2q-2sg-1dg.qasm

   # 查看结果，确认调度符合预期
   qcos-cli get-job-results {JOB_ID}

.. note::

   - ``g1.all`` 是一个包含全部通用设备的资源规格名称，系统会提前创建
   - ``qc:min_qubits`` 和 ``qc:max_qubits`` 同时指定可锁定比特数范围
   - 系统会综合 Flavor 中的 ``qc:tech_types`` 等条件与 extra_specs
     共同过滤设备
