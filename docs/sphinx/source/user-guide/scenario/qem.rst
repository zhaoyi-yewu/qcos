量子错误缓解场景
====================

量子错误缓解（Quantum Error Mitigation, QEM）在不额外引入物理量子比特资源
的前提下，通过对量子线路变换和测量结果后处理，抑制噪声对计算结果的影响。
QCOS 提供读出错误缓解（REM）、零噪声外推（ZNE）和动力学解耦（DD）三种策略，
并支持按固定顺序级联执行。

.. note::

   - QEM 通过作业提交参数 ``qem_options`` 启用，作用于真实量子后端
     （如 ``quafu``、``cetc_baihua`` 等超导设备）
   - ``qcos-cli`` 命令行当前暂未暴露 ``--qem-options`` 参数，
     错误缓解需通过 :doc:`/user-guide/sdk` 的 ``submit_job(qem_options=...)`` 启用
   - 三种策略的算法细节与级联顺序详见 :doc:`/design/module-design/qem`

QEM 执行流程
****************

启用量子错误缓解的作业执行流程如下：

.. code-block:: text

   submit_job(qem_options=...)
   -> MitigationManager.configure(qem_options)   # 配置启用的技术实例
   -> validate_device(device_configs)            # 设备能力校验
   -> get_calibration_circuits()                 # 生成校准线路（REM 需要）
   -> 执行校准线路并构建混淆矩阵                   # REM 校准
   -> transform_circuit()                        # 线路变换（DD + ZNE）
   -> 执行原始线路与噪声放大变体
   -> postprocess_results()                      # 后处理（DD → REM → ZNE）

其中线路变换阶段 DD 先于 ZNE 应用，结果后处理阶段按 DD → REM → ZNE 顺序级联，
原始结果保存在 ``mitigation_metadata.raw_results`` 中。

前置准备
****************

初始化客户端并登录
~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import json
   from wy_qcos_client.client import Client

   client = Client(api_server_ip="127.0.0.1", api_server_port=18400)
   client.login(username="admin", password="P*ssword1")

   with open("./samples/qasm/2.0/simple-qasm.qasm", "r") as f:
       source_code = f.read()

场景示例
****************

读出错误缓解（REM）
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

REM 通过校准每个量子比特的混淆矩阵并施加伪逆校正，修正测量读出误差。
启用 REM 需要执行校准线路，``calibration_shots`` 控制校准采样数：

.. code-block:: python

   status_code, reason, text, result = client.submit_job(
       [source_code],
       code_type="qasm",
       shots=1024,
       backend="quafu_dongling",
       qem_options={
           "rem": {"enabled": True, "calibration_shots": 8192},
       },
   )

   job_id = json.loads(text)["result"]["job_id"]
   # 等待作业完成后获取缓解后的结果
   status_code, reason, text, result = client.get_job_results(job_id)

零噪声外推（ZNE）
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

ZNE 通过对 CZ 门折叠放大线路噪声，执行原始线路与一个或多个噪声放大变体，
再将测量概率外推到零噪声极限：

.. code-block:: python

   status_code, reason, text, result = client.submit_job(
       [source_code],
       code_type="qasm",
       shots=1024,
       backend="quafu_dongling",
       qem_options={
           "zne": {
               "enabled": True,
               "scale_factors": [1, 3, 5],
               "extrapolation_method": "polynomial",
               "polynomial_degree": 1,
           },
       },
   )

``scale_factors`` 为噪声放大倍率列表（须含 1 作为原始基准），
``extrapolation_method`` 支持 ``polynomial`` / ``richardson`` / ``linear`` /
``exponential`` 四种外推方法。

动力学解耦（DD）
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

DD 在量子线路的空闲窗口插入回波脉冲序列，抑制空闲期间的退相干。
``sequence`` 指定脉冲序列，``gate_times`` 提供门时长用于空闲窗口检测：

.. code-block:: python

   status_code, reason, text, result = client.submit_job(
       [source_code],
       code_type="qasm",
       shots=1024,
       backend="quafu_dongling",
       qem_options={
           "dd": {
               "enabled": True,
               "sequence": "XY4",
               "gate_times": {"h": 0.02, "cz": 0.04, "x": 0.02},
           },
       },
   )

``sequence`` 支持 ``XY4`` / ``CPMG`` / ``XY8`` / ``XX`` / ``XXYX`` / ``UDD<n>``
等序列，``gate_times`` 的键为门名、值为门时长（秒）。

策略级联（REM + ZNE）
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

多种策略可同时启用，由 ``MitigationManager`` 按固定顺序级联执行：
线路变换阶段 DD 先于 ZNE，结果后处理阶段按 DD → REM → ZNE 顺序处理。

.. code-block:: python

   status_code, reason, text, result = client.submit_job(
       [source_code],
       code_type="qasm",
       shots=1024,
       backend="quafu_dongling",
       qem_options={
           "rem": {"enabled": True, "calibration_shots": 8192},
           "zne": {
               "enabled": True,
               "scale_factors": [1, 3, 5],
               "extrapolation_method": "polynomial",
               "polynomial_degree": 1,
           },
       },
   )

``qem_options`` 参数说明
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table:: qem_options 字段
   :widths: 15 20 65
   :header-rows: 1
   :align: left

   * - 技术
     - 字段
     - 说明
   * - **rem**
     - enabled / calibration_shots
     - 启用读出错误缓解；``calibration_shots`` 为校准采样数
   * - **zne**
     - enabled / scale_factors / extrapolation_method / polynomial_degree
     - 启用零噪声外推；``scale_factors`` 为放大倍率列表，
       ``extrapolation_method`` 为外推方法
   * - **dd**
     - enabled / sequence / gate_times
     - 启用动力学解耦；``sequence`` 为脉冲序列，
       ``gate_times`` 为门时长配置

.. note::

   - REM 需要额外执行校准线路，会增加作业总执行时间
   - ZNE 会执行多个噪声放大变体，采样次数随 ``scale_factors`` 数量成倍增加
   - DD 要求设备配置中包含 ``gate_times`` 信息，否则设备校验不通过
