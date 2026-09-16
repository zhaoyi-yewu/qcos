量子错误缓解
==============

量子错误缓解（Quantum Error Mitigation, QEM）模块提供读出错误缓解（REM）、
零噪声外推（ZNE）和动力学解耦（DD）三种策略，通过对量子线路变换和测量
结果后处理，在不额外引入物理量子比特资源的前提下抑制噪声对计算结果的影响。

QEM模块架构
--------------

QEM模块由五个主要部分组成：

- ``MitigationBase``：错误缓解技术抽象基类，定义了校准、线路变换和结果后处理的统一接口。
- ``MitigationManager``：错误缓解管理器，负责配置技术实例、校准数据缓存，
  并按正确顺序级联执行线路变换与结果后处理。
- ``MitigationFactory``：错误缓解技术工厂，维护技术注册表，提供按名称创建实例的能力。
- ``ReadoutMitigation`` / ``ZNEMitigation`` / ``DDMitigation``：REM、
  ZNE、DD 三种策略的具体实现。
- ``utils``：共享工具函数（计数转概率、概率投影、期望值计算等）。

.. code-block:: text

   +-----------------------+
   |   MitigationManager   |
   | 错误缓解管理器         |
   +-----------------------+
            |
            | configure(qem_options)
            v
   +-----------------------+
   |  MitigationFactory    |
   | 错误缓解技术工厂       |
   +-----------------------+
            |
            | create("rem"/"zne"/"dd")
            v
   +-----------------------+
   |   MitigationBase      |
   | 错误缓解抽象基类       |
   +-----------------------+
            ^
            |
   +-------------+   +----------------+   +------------------+
   | ReadoutMiti-|   | ZNEMitigation  |   | DDMitigation     |
   | gation(REM) |   | (零噪声外推)    |   | (动力学解耦)     |
   +-------------+   +----------------+   +------------------+

错误缓解流水线
^^^^^^^^^^^^^^^

``MitigationManager`` 将多种技术按固定顺序级联执行，分为线路变换阶段
（执行前）和结果后处理阶段（执行后）：

.. code-block:: text

   [线路变换阶段]
   transform_circuit(circuit)
   -> DD: 在空闲窗口插桩解耦脉冲序列（保留原 label）
   -> ZNE: 对每个变体按 scale_factors 折叠 CZ 门生成变体
      （label 覆盖为 original/scaled）

   [硬件执行]
   原始线路 + 噪声放大变体 + 校准线路

   [结果后处理阶段]
   postprocess_results(variant_results)
   -> DD: 直通（仅记录 metadata，不改结果）
   -> REM: 伪逆校正读出误差
   -> ZNE: 外推到零噪声极限

.. list-table:: MitigationManager 关键方法
   :widths: 25 35 40
   :header-rows: 1
   :align: left

   * - 方法
     - 功能
     - 说明
   * - **configure(qem_options)**
     - 配置技术实例
     - 从用户配置创建启用的技术实例；未注册名或非 dict 静默跳过
   * - **validate_device(device_config)**
     - 设备校验
     - 校验所有启用技术对设备能力（如 basis_gates、gate_times）的要求
   * - **get_calibration_circuits(circuit, target_qubits)**
     - 生成校准线路
     - 为需要校准的技术（REM）生成按物理比特制备 ``|0⟩`` / ``|1⟩`` 的测量线路
   * - **store_calibration_data(name, data)**
     - 缓存校准数据
     - 存储校准结果供后处理阶段使用
   * - **transform_circuit(circuit)**
     - 线路变换
     - DD 先于 ZNE 应用；返回变体列表
   * - **postprocess_results(variant_results, ...)**
     - 结果后处理
     - 按 DD → REM → ZNE 顺序级联；原始结果保存在
       ``mitigation_metadata.raw_results``

错误缓解抽象基类
------------------

``MitigationBase`` 是所有错误缓解技术的抽象基类，定义了校准、线路变换和结果后处理的标准接口。

.. code-block:: python

   from abc import ABC, abstractmethod
   from typing import Any


   class MitigationBase(ABC):
       """Abstract base class for error mitigation techniques."""

       def __init__(self, name: str):
           self._name = name
           self._enabled = False
           self._config: dict[str, Any] = {}

       @property
       def name(self) -> str:
           return self._name

       @property
       def enabled(self) -> bool:
           return self._enabled

       def set_config(self, config: dict[str, Any]) -> None:
           """Set configuration for this mitigation technique."""
           self._config = config
           self._enabled = config.get("enabled", False)

       def needs_calibration(self) -> bool:
           """Whether this technique requires calibration data before execution."""
           return False

       def calibrate(self, circuit, device_id, target_qubits=None, **kwargs):
           """Run calibration procedure (default: no-op)."""
           return {}

       def transform_circuit(self, circuit):
           """Transform the circuit (default: original circuit unchanged)."""
           return [{"label": "original", "circuit": circuit, "scale_factor": 1}]

       @abstractmethod
       def postprocess(self, results, calibration=None, **kwargs):
           """Post-process raw measurement results (must be implemented)."""
           raise NotImplementedError("postprocess() must be implemented by subclass")

       def validate_device(self, device_config) -> tuple:
           """Validate that the device supports this technique."""
           return (True, None)

该类提供以下基础属性：

.. list-table:: MitigationBase 属性说明
   :widths: 20 30 50
   :header-rows: 1
   :align: left

   * - 属性
     - 类型
     - 说明
   * - **name**
     - str
     - 错误缓解技术名称
   * - **enabled**
     - bool
     - 是否启用，由 ``set_config`` 中 ``enabled`` 字段控制
   * - **_config**
     - dict
     - 技术配置字典

抽象方法接口说明：

.. list-table:: MitigationBase 方法
   :widths: 25 35 40
   :header-rows: 1
   :align: left

   * - 方法
     - 功能
     - 说明
   * - **needs_calibration**
     - 是否需校准
     - 返回是否在校准阶段生成校准线路；REM 返回 ``True``，ZNE/DD 返回 ``False``
   * - **calibrate**
     - 校准
     - 默认返回空字典，具体技术可覆盖以执行校准流程
   * - **transform_circuit**
     - 线路变换
     - 默认返回原始线路；ZNE 生成噪声放大变体，DD 插入解耦脉冲
   * - **postprocess**
     - 结果后处理
     - 抽象方法，子类必须实现，返回 ``{results, metadata}``
   * - **validate_device**
     - 设备校验
     - 默认 ``(True, None)``；ZNE 要求设备含 CZ 门，DD 要求含 gate_times 配置

读出错误缓解（REM）
--------------------

读出错误缓解通过校准每个量子比特的 2×2 混淆矩阵（confusion matrix），对测量结果施加伪逆校正，修正量子比特读出错误。

REM核心算法
^^^^^^^^^^^^^

REM 的核心是逐比特混淆矩阵的 Kronecker 组合与伪逆校正：

.. code-block:: text

   校准: 每比特制备 |0⟩/|1⟩ 测量 -> 构建 2x2 混淆矩阵 M[row][col]
         M[0][0]=P(meas=0|prep=0), M[1][0]=P(meas=1|prep=0)
   组合: M_global = kron(M_q0, M_q1, ...)  (2^k x 2^k)
   校正: p_true = pinv(M_global) @ p_meas   (伪逆)
   投影: 最近合法概率分布投影（mitiq L2 投影）

混淆矩阵约定：``cm[row][col]``，``row`` 为读出值，``col`` 为真值；``build_confusion_matrix_from_counts`` 的列 ``i`` 等于制备态 ``i`` 的测量分布。

.. list-table:: REM 函数
   :widths: 30 30 40
   :header-rows: 1
   :align: left

   * - 函数
     - 功能
     - 说明
   * - **build_local_confusion_matrix**
     - 构建全局混淆矩阵
     - 对指定量子比特的逐比特混淆矩阵做 Kronecker 积
   * - **mitigate_readout**
     - 伪逆校正
     - 计算 ``pinv(M) @ p`` 后投影到最近合法概率分布
   * - **build_confusion_matrix_from_counts**
     - 从计数构建混淆矩阵
     - 列 ``i`` 等于制备态 ``i`` 的测量概率分布
   * - **expectation_from_samples_unbiased**
     - 无偏奇偶期望估计
     - 支持大 support 时避免构建完整 2^k 边缘分布
   * - **mitigate_observable_from_samples**
     - 自适应可观测值缓解
     - 小 support 用精确边缘法，大 support 用无偏估计器

REM后处理防恶化机制
^^^^^^^^^^^^^^^^^^^^^

``ReadoutMitigation.postprocess`` 在伪逆校正后包含两道防恶化保护：

- **条件数检查**：若全局混淆矩阵条件数 ``cond > 1e6``，判定为病态，跳过校正并记录 ``warning="singular_confusion_matrix"``。
- **规模上限**：当 ``num_qubits > 15`` 时
  （``MAX_GLOBAL_MATRIX_QUBITS``），不构建全局矩阵，直接返回原计数
  并标记 ``reason="too_many_qubits_for_global_matrix"``。

.. code-block:: python

   # 防恶化路径
   cond = np.linalg.cond(local_cm)
   if cond > 1e6:
       mitigated_results[label] = counts  # 跳过校正
       metadata_list.append({"warning": "singular_confusion_matrix"})
       continue

   # 规模上限
   if num_qubits <= MAX_GLOBAL_MATRIX_QUBITS:
       # 构建全局矩阵并伪逆校正
   else:
       mitigated_results[label] = counts  # 跳过
       metadata_list.append({"reason": "too_many_qubits_for_global_matrix"})

零噪声外推（ZNE）
------------------

零噪声外推通过对 CZ 门折叠放大电路噪声，执行原始线路与一个或多个噪声放大变体，再将测量概率外推到零噪声极限。

ZNE噪声放大
^^^^^^^^^^^^^

ZNE 通过折叠 CZ 门放大噪声，``CZ * CZ = I``，奇数个 CZ 门逻辑等价于单个 CZ 但放大门噪声：

.. code-block:: text

   折叠策略
   -> apply_zne_cz_folding: 任意 scale in [1,3]，部分折叠 k/n 个 CZ -> scale = 1+2k/n
   -> fold_gates: 广义折叠，支持 left/right/random 策略，可折叠 CZ/CX 等自逆门
   -> 奇整数 scale (>3): 全门折叠 apply_zne_cz_scaling

.. list-table:: ZNE 折叠函数
   :widths: 30 30 40
   :header-rows: 1
   :align: left

   * - 函数
     - 功能
     - 说明
   * - **apply_zne_cz_scaling**
     - 整数倍 CZ 折叠
     - 每个 CZ 替换为 ``scale`` 个连续 CZ，``scale`` 必须为正奇数
   * - **apply_zne_cz_folding**
     - 任意倍率 CZ 折叠
     - 部分折叠 k 个 CZ 为三元组（+2），等效 scale = 1+2k/n
   * - **fold_gates**
     - 广义门折叠
     - 支持 left/right/random 策略，可折叠任意自逆门集合
   * - **count_cz_gates**
     - 计数 CZ 门
     - 返回线路中 CZ 门数量

ZNE外推方法
^^^^^^^^^^^^^

``extrapolate_to_zero`` 支持四种外推方法：

.. list-table:: ZNE 外推方法
   :widths: 20 30 50
   :header-rows: 1
   :align: left

   * - 方法
     - 名称
     - 说明
   * - **polynomial**
     - 多项式拟合（默认）
     - 最小二乘多项式拟合，默认阶数 1，抗 shot 噪声
   * - **richardson**
     - Richardson 消去
     - 精确消去至 n-1 阶噪声项，对 shot 噪声敏感
   * - **linear**
     - 两点线性外推
     - ``(lambda2*y1 - lambda1*y2) / (lambda2 - lambda1)``
   * - **exponential**
     - 指数外推
     - 拟合 ``a + b*exp(c*lambda)``，匹配去极化噪声模型

ZNE后处理自适应
^^^^^^^^^^^^^^^^^

``ZNEMitigation.postprocess`` 在外推前自适应剔除失效的 scale 点，并支持两种模式：

- **概率模式（默认）**：逐 bitstring 概率外推到零噪声，返回 mitigated 计数。
- **期望值模式**：传入 ``observable=[q0, q1, ...]``，将每个 scale 的计数归约为单一 Z 奇偶期望值后外推，返回 ``expectation_value``。

.. code-block:: text

   _prune_scale_points(points, num_qubits)
   -> 饱和剔除: 顶端点接近均匀分布（peak < 1.5/dim）-> 丢弃
   -> 非单调剔除: 熵随 scale 下降（hi_ent < sec_ent - 0.25）-> 丢弃
   -> 不足 2 个可信点: 回退到 scale-1 结果

   外推后保护
   -> enable_fallback=True 且负概率质量 > fallback_threshold(0.15) -> 回退 scale-1
   -> 期望值超出 [-1, 1] -> 回退 scale-1 期望值

动力学解耦（DD）
-----------------

动力学解耦在量子线路的空闲窗口插入回波脉冲序列（XY4/CPMG/UDD 等），抑制空闲期间的退相干。

DD空闲窗口检测
^^^^^^^^^^^^^^^

``detect_idle_windows`` 遍历线路构建逐比特时间线，门之间的间隙为空闲窗口，``barrier``/``sync`` 作为全局对齐点：

.. code-block:: text

   逐比特时钟推进:
   -> 门 G 在比特 q 上: gap = start - current_time[q]，gap > 0 则记录空闲窗口
   -> barrier/sync: 所有比特时钟对齐到最晚值
   -> measure/reset: 忽略
   -> include_trailing=True: 额外记录末尾空闲窗口（默认 False）

DD脉冲序列
^^^^^^^^^^^

``generate_dd_sequence`` 在空闲窗口中填充脉冲序列，窗口两端用自由演化 Delay 包夹：

.. list-table:: 支持的 DD 序列
   :widths: 20 30 50
   :header-rows: 1
   :align: left

   * - 序列
     - 类型
     - 说明
   * - **XY4**
     - 命名序列
     - ``x, y, x, y``，等间距，净单位操作
   * - **CPMG**
     - 命名序列
     - ``x, x``，等间距
   * - **XY8**
     - 命名序列
     - ``x, y, x, y, y, x, y, x``，等间距
   * - **XX**
     - 命名序列
     - ``x, x``，等间距
   * - **XXYX**
     - 命名序列
     - ``x, x, y, x``，等间距
   * - **UDD<n>**
     - Uhrig 序列
     - n 阶 Uhrig，非均匀间距 ``t_k = sin^2(k*pi/(2*(n+1)))``

错误缓解技术工厂
------------------

``MitigationFactory`` 是错误缓解技术的工厂类，维护技术注册表，提供按名称创建实例的能力。

.. code-block:: python

   class MitigationFactory:
       """Factory for creating error mitigation technique instances."""

       def __init__(self):
           self._registry = {
               "readout": ReadoutMitigation,
               "rem": ReadoutMitigation,
               "zne": ZNEMitigation,
               "dd": DDMitigation,
           }

工厂默认注册了 ``"readout"``/``"rem"``（均为 ``ReadoutMitigation``）、``"zne"``、``"dd"``。支持的操作包括：

.. list-table:: MitigationFactory 方法说明
   :widths: 20 30 50
   :header-rows: 1
   :align: left

   * - 方法
     - 功能
     - 说明
   * - **create(name, **kwargs)**
     - 创建技术实例
     - 根据名称创建错误缓解实例，未注册的名称抛出 ``ValueError``
   * - **register(name, cls)**
     - 注册技术
     - 注册错误缓解类，非 ``MitigationBase`` 子类抛出 ``TypeError``
   * - **list_available()**
     - 列出已注册技术
     - 返回所有已注册的技术名称列表（去重排序）

使用示例
------------

通过 ``MitigationManager`` 配置并执行错误缓解：

.. code-block:: python

   from wy_qcos.error_mitigation.mitigation_manager import MitigationManager

   mgr = MitigationManager()
   mgr.configure({
       "rem": {"enabled": True, "calibration_shots": 8192},
       "zne": {"enabled": True, "scale_factors": [1, 3, 5]},
       "dd": {"enabled": False},
   })

   # 1. 校准（REM 需要）
   cal_circuits = mgr.get_calibration_circuit(circuit, [0, 1])
   # ... 执行校准线路并收集结果 ...
   mgr.store_calibration_data("readout", calib_data)

   # 2. 线路变换（DD + ZNE）
   variants = mgr.transform_circuit(circuit)

   # 3. 硬件执行原始与变体线路后...
   variant_results = {"original": counts, "scaled": scaled_counts}

   # 4. 结果后处理（DD → REM → ZNE）
   output = mgr.postprocess_results(
       variant_results, num_qubits=2, target_qubits=[0, 1]
   )
   # output = {"results": ..., "mitigation_metadata": {...}}

直接使用单项技术：

.. code-block:: python

   from wy_qcos.error_mitigation.mitigation_factory import MitigationFactory

   factory = MitigationFactory()
   rem = factory.create("readout", calibration_shots=4096)
   zne = factory.create("zne", scale_factors=[1, 3])
   dd = factory.create("dd", sequence="XY4", gate_times={"h": 0.02})

与作业引擎集成
------------------

QEM 模块与作业引擎（``job_engine``）集成，通过作业提交参数 ``qem_options`` 启用错误缓解功能。``qem_options`` 配置如下：

.. code-block:: python

   # job_info["data"]["qem_options"]
   {
       "rem": {"enabled": True, "calibration_shots": 8192},
       "zne": {
           "enabled": True,
           "scale_factors": [1, 3, 5],
           "extrapolation_method": "polynomial",
           "polynomial_degree": 1,
       },
       "dd": {
           "enabled": True,
           "sequence": "XY4",
           "gate_times": {"h": 0.02, "cz": 0.04, "x": 0.02},
       },
   }

作业引擎 QEM 执行流程如下：

.. code-block:: text

   qem_options = job_data.get("qem_options")
   -> MitigationManager().configure(qem_options)  # 配置技术实例
   -> validate_device(device_configs)  # 设备能力校验
   -> needs_calibration()  # 是否需要校准
   -> get_calibration_circuits()  # 生成校准线路（REM）
   -> _run_calibration_circuits()  # 通过 driver 执行校准线路
   -> process_calibration_results()  # 构建混淆矩阵并缓存
   -> driver.run()  # 执行原始线路
   -> _apply_zne_circuit_transform()  # ZNE CZ 三倍折叠变体
   -> driver.run()  # 执行噪声放大变体
   -> postprocess_results(variant_results)  # DD → REM → ZNE 级联后处理

作业提交示例：

.. code-block:: python

   job_info = {
       "dry_run": False,
       "backend": "quafu",
       "qem_options": {
           "rem": {"enabled": True, "calibration_shots": 8192},
           "zne": {
               "enabled": True,
               "scale_factors": [1, 3, 5],
               "extrapolation_method": "polynomial",
               "polynomial_degree": 1,
           },
       },
       "shots": 1000,
   }

ZNE 变体线路的 label 经 ``MitigationManager.transform_circuit`` 后会被
覆盖为 ``original``（scale_factor == 1）或 ``scaled``（其余），作业引擎
据此在 ``variant_results`` 中组织 ``{"original": ..., "scaled": ...}``
供后处理使用。
