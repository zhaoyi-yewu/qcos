自动线路切割/QUBO分解到多设备场景
=======================================

自动线路切割（Wirecut）/QUBO分解（subqubo）是 QCOS 的核心能力之一。当量子电路/QUBO
的比特数超过单台量子计算设备的最大支持比特数时，系统通过 ``enable_wirecut``
选项自动将电路切割为多个子电路，通过 ``enable_subqubo`` 自动将QUBO分解为多个子QUBO，
分别调度到设备组中的不同设备上并行执行，再将各子电路/子QUBO的结果聚合重构为完整结果。

与手动指定 ``--backend`` 的单设备线路切割不同，自动线路切割/QUBO分解搭配
``--flavor`` 参数使用，系统根据资源规格（Flavor）关联的设备组自动选择多台设备进行
切割/分解调度，无需用户手动指定目标设备。

.. note::

   - 自动线路切割需要搭配 ``--flavor`` 参数和 ``--options '{"enable_wirecut": true}'``
     使用，不能与 ``--backend`` 同时指定
   - 自动QUBO分解需要搭配 ``--flavor`` 参数和 ``--options '{"enable_subqubo": true}'``
     使用，不能与 ``--backend`` 同时指定
   - 设备组中的设备应尽量属于相同或兼容的技术路线，以保证切割后的
     子电路可以在对应设备上执行
   - 线路切割/QUBO分解和结果重构由系统自动完成，用户只需提交原始电路/QUBO

前置准备
****************

查看当前可用设备
~~~~~~~~~~~~~~~~

提交自动线路切割/QUBO分解任务前，先查看系统中已注册的设备及其技术路线：

.. code-block:: shell

   # 查询所有设备信息
   qcos-cli list-devices

根据 ``list-devices`` 输出的 ``name`` 和 ``tech_type`` 字段，
确定后续要加入设备组的设备名称。

创建设备组
~~~~~~~~~~

设备组（Device Group）是自动线路切割/QUBO分解的设备池。切割后的子电路/子QUBO将调度到设备组中的各台设备上执行。

.. code-block:: shell

   # 创建设备组 qc.wirecut，加入 6 台设备
   # 设备名根据 list-devices 实际输出填写
   qcos-cli create-device-group qc.wirecut \
       --device dummy dummy1 dummy2 qutip_sim qutip_sim1 qutip_sim2

   # 查看已创建的设备组
   qcos-cli list-device-groups

.. tip::

   - 设备组中的设备可以包含模拟器和真实量子计算设备
   - 一个 Flavor 可关联多个设备组，实现跨设备组的切割调度
   - 记下 ``list-device-groups`` 输出中的设备组 UUID，后续创建 Flavor 时需要

场景示例
****************

自动线路切割到多设备
~~~~~~~~~~~~~~~~~~~~

通过资源规格定义切割调度策略，提交大比特数电路，系统自动切割并调度
到设备组中的多台设备上并行执行。

.. code-block:: shell

   # 1. 查看设备，确认当前可用设备及技术路线
   qcos-cli list-devices

   # 2. 创建设备组 qc.wirecut，加入 6 台设备
   qcos-cli create-device-group qc.wirecut \
       --device dummy dummy1 dummy2 qutip_sim qutip_sim1 qutip_sim2

   # 查看设备组列表，获取设备组 UUID
   qcos-cli list-device-groups

   # 3. 创建资源规格 g1.wirecut，关联设备组
   #    将上一步 list-device-groups 输出的 UUID 填入 --device-groups
   qcos-cli create-flavor g1.wirecut \
       --device-groups 69cde107-a9c3-4564-a7d9-6fd7fc8ebc89

   # 查看已创建的资源规格
   qcos-cli list-flavors

   # 4. 使用资源规格 g1.wirecut 提交量子任务
   #    通过 --options 开启 enable_wirecut，提交 60 比特的大电路
   qcos-cli submit-job \
       --code-type qasm \
       --shots 1024 \
       --options '{"enable_wirecut": true}' \
       --flavor g1.wirecut \
       -f ./samples/qasm/2.0/test-60-bit.qasm

   # 5. 查看作业结果，确认切割调度和结果重构符合预期
   qcos-cli get-job-results {JOB_ID}

自动QUBO切割到多设备
~~~~~~~~~~~~~~~~~~~~

通过资源规格定义切割调度策略，提交大比特数QUBO，系统自动分解并调度
到设备组中的多台设备上并行执行。

.. code-block:: shell

   # 1. 查看设备，确认当前可用设备及技术路线
   qcos-cli list-devices

   # 2. 创建设备组 qc.subqubo，加入 3 台设备
   qcos-cli create-device-group qc.subqubo \
       --device tiangong100 tiangong1000_v2 tiangong550_v2

   # 查看设备组列表，获取设备组 UUID
   qcos-cli list-device-groups

   # 3. 创建资源规格 g1.subqubo，关联设备组
   #    将上一步 list-device-groups 输出的 UUID 填入 --device-groups
   qcos-cli create-flavor g1.subqubo \
       --device-groups 69cde107-a9c3-4564-a7d9-6fd7fc8ebc89

   # 查看已创建的资源规格
   qcos-cli list-flavors

   # 4. 使用资源规格 g1.subqubo 提交QUBO任务
   #    通过 --options 开启 enable_subqubo，提交 1200 比特的大QUBO
   qcos-cli submit-job \
       --code-type qubo \
       --shots 1024 \
       --options '{"enable_subqubo": true}' \
       --transpiler cmss_qubo \
       --flavor g1.subqubo \
       -f ./samples/qubo/qubo_1200X1200.csv

   # 5. 查看作业结果，确认切割调度和结果重构符合预期
   qcos-cli get-job-results {JOB_ID}

.. note::

   - ``--options '{"enable_wirecut": true}'`` 是开启自动线路切割的必填项
   - ``--options '{"enable_subqubo": true}'`` 是开启QUBO分解的必填项
   - ``--flavor`` 指定的资源规格关联的设备组中需包含足够数量的设备，
     以满足切割后子电路/子QUBO的调度需求
   - 系统自动完成电路切割/QUBO分解、子电路调度、并行执行和结果重构，
     用户只需提交原始电路/QUBO并等待结果
