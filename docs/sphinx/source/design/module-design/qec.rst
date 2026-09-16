量子纠错码管理
==================

量子纠错码（Quantum Error Correction, QEC）模块提供量子错误纠正码的抽象、实现和工厂管理能力，用于在量子计算任务中对抗噪声引起的量子比特错误。

QEC模块架构
--------------

QEC模块由三个主要部分组成：

- ``QuantumCodeBase``：量子纠错码抽象基类，定义了所有量子纠错码的统一接口。
- ``ShorCode``：九比特Shor码的具体实现，可纠正任意单量子比特错误。
- ``QecFactory``：量子纠错码工厂，负责量子纠错码实例的注册与创建。

.. code-block:: text

   +-----------------------+
   |      QecFactory       |
   |   量子纠错码工厂       |
   +-----------------------+
            |
            | create("shor")
            v
   +-----------------------+
   |      QuantumCodeBase  |
   |  量子纠错码抽象基类    |
   +-----------------------+
            ^
            |
   +-----------------------+
   |       ShorCode        |
   |   九比特Shor码实现     |
   +-----------------------+
            |
            | 按线路类型分发
            v
   +---------------------------+  +----------------------------------+
   |    ShorStimStrategy       |  |  ShorQuantumCircuitStrategy     |
   |  （Stim线路策略）          |  |  （量子线路策略）                 |
   +---------------------------+  +----------------------------------+

量子纠错码抽象基类
----------------------

``QuantumCodeBase`` 是所有量子纠错码的抽象基类，定义了量子纠错操作的标准接口，包括编码、错误注入、伴随式测量、纠错和解码。

.. code-block:: python

   from abc import ABC, abstractmethod


   class QuantumCodeBase(ABC):
       """Abstract base class for quantum error correction codes."""

       def __init__(self, name: str = "QuantumCodeBase"):
           self._name = name
           self._physical_bit_num: int = 0
           self._logical_bit_num: int = 0
           self._distance: int = 1

       @abstractmethod
       def encode(self, circuit, **kwargs):
           """Encode a logical state into the physical qubit state."""

       @abstractmethod
       def decode(self, circuit, **kwargs):
           """Decode the syndrome."""

       @abstractmethod
       def correct(self, circuit, **kwargs):
           """Apply error correction based on the syndrome measurement."""

       @abstractmethod
       def validate_and_format_circuit(self, circuit, num_qubits: int):
           """Validate and format circuit data."""

       @abstractmethod
       def compute_samples(self, circuit, samples: list):
           """Compute samples to get raw bits and syndrome."""

该类提供以下基础属性：

.. list-table:: QuantumCodeBase 属性说明
   :widths: 20 30 50
   :header-rows: 1
   :align: left

   * - 属性
     - 类型
     - 说明
   * - **name**
     - str
     - 量子纠错码名称
   * - **n_physical**
     - int
     - 物理量子比特数量
   * - **n_logical**
     - int
     - 逻辑量子比特数量
   * - **distance**
     - int
     - 码距
   * - **physical_bit_num**
     - int
     - 物理比特数（可通过 ``get_physical_bit_num`` / ``set_physical_bit_num`` 访问）
   * - **logical_bit_num**
     - int
     - 逻辑比特数（可通过 ``get_logical_bit_num`` / ``set_logical_bit_num`` 访问）

抽象方法接口说明：

.. list-table:: QuantumCodeBase 抽象方法
   :widths: 20 40 40
   :header-rows: 1
   :align: left

   * - 方法
     - 功能
     - 说明
   * - **encode**
     - 编码
     - 将逻辑态编码为物理量子比特态，支持通过 ``error_inject`` 和 ``noise_prob`` 注入噪声
   * - **decode**
     - 解码
     - 根据伴随式测量结果解码，返回错误位置信息
   * - **correct**
     - 纠错
     - 基于伴随式测量结果执行纠错操作
   * - **validate_and_format_circuit**
     - 线路校验与格式化
     - 校验并格式化输入的量子线路
   * - **compute_samples**
     - 样本计算
     - 从采样结果中提取原始比特和伴随式信息

Shor码
----------

Shor码是一种九比特量子纠错码，它将1个逻辑量子比特编码为9个物理量子比特，能够纠正任意单量子比特错误。Shor码通过级联三比特相位翻转码和三比特比特翻转码实现。

``ShorCode`` 类实现了 ``QuantumCodeBase`` 接口，并使用策略模式按量子线路类型分发处理逻辑：

- ``ShorStimStrategy``：基于 Stim 线路的 Shor 码策略，使用 Stim 量子线路执行 QEC 编码、解码与纠错流程。
- ``ShorQuantumCircuitStrategy``：基于量子线路（``BaseOperation`` 列表）的 Shor 码策略。

.. code-block:: python

   ShorCode.register(stim.Circuit)(ShorStimStrategy)
   ShorCode.register(list[BaseOperation])(ShorQuantumCircuitStrategy)

Shor码基本参数
****************

.. list-table:: Shor码参数
   :widths: 20 30 50
   :header-rows: 1
   :align: left

   * - 参数
     - 值
     - 说明
   * - **编码码率**
     - 1/9
     - 1个逻辑量子比特编码为9个物理量子比特
   * - **码距**
     - 3
     - 可以纠正任意单量子比特错误
   * - **Z稳定子**
     - 6个
     - 检测比特翻转错误：Z₀Z₁, Z₁Z₂, Z₃Z₄, Z₄Z₅, Z₆Z₇, Z₇Z₈
   * - **X稳定子**
     - 2个
     - 检测相位翻转错误：X₀X₁X₂X₃X₄X₅, X₃X₄X₅X₆X₇X₈

Stim策略编码流程
****************

``ShorStimStrategy.encode`` 方法将1个逻辑量子比特编码为9个物理量子比特，编码流程如下：

.. code-block:: text

   初始化: R 全部9个数据比特 + 6个Z伴随比特 + 2个X伴随比特
   -> 相位翻转编码: H[0] -> CX[0,3] CX[0,6]
   -> 比特翻转编码: 三个分组内分别执行CX
   -> 应用逻辑门: X / Z / Y / S（H门不支持横向实现）
   -> 噪声注入: 根据 error_inject 配置注入 X_ERROR / Y_ERROR / Z_ERROR / DEPOLARIZE1
   -> Z稳定子测量: 6个伴随比特测量 Z₀Z₁, Z₁Z₂, ...
   -> X稳定子测量: 2个伴随比特测量 X₀X₁X₂X₃X₄X₅, X₃X₄X₅X₆X₇X₈
   -> 反向比特翻转 / 反向相位翻转 / 反向H
   -> M 测量9个数据比特

支持量子门和错误注入类型
****************************

``ShorStimStrategy`` 支持以下逻辑门和错误注入类型：

.. code-block:: python

   VALID_ERROR_TYPES = {"x_error", "y_error", "z_error", "depolarize"}

``ShorStrategy._validate_error_inject`` 方法用于校验 ``error_inject`` 配置，校验规则如下：

- ``error_inject`` 必须为 ``dict`` 类型，否则抛出 ``ValueError``。
- ``error_type`` 必须为 ``VALID_ERROR_TYPES`` 中的一种，否则抛出 ``ValueError``。
- ``noise_prob`` 必须为 ``int`` 或 ``float`` 类型，否则抛出 ``ValueError``。

.. list-table:: 支持的操作
   :widths: 20 30 50
   :header-rows: 1
   :align: left

   * - 操作
     - 类型
     - 说明
   * - **X门**
     - 逻辑门
     - 横向实现为 Z[0], Z[3], Z[6]
   * - **Z门**
     - 逻辑门
     - 横向实现为 X[0..8]
   * - **Y门**
     - 逻辑门
     - 横向实现为 Z[0,3,6] + X[0..8]
   * - **S门**
     - 逻辑门
     - 横向实现为 S[0], S[3], S[6]
   * - **H门**
     - 逻辑门
     - 不支持（需要非横向实现）
   * - **x_error**
     - 错误注入
     - 注入 X_ERROR，仅支持单比特门线路
   * - **y_error**
     - 错误注入
     - 注入 Y_ERROR
   * - **z_error**
     - 错误注入
     - 注入 Z_ERROR
   * - **depolarize**
     - 错误注入
     - 注入 DEPOLARIZE1 去极化噪声

解码与纠错流程
****************

Shor码的纠错流程包含以下步骤：

.. code-block:: text

   compute_samples(samples)  # 从采样结果中提取伴随式和原始比特
   -> decode()               # 根据伴随式解码得到错误位置 err_pos
   -> correct(err_pos)       # 根据错误位置翻转错误比特
   -> logical_measure(bits)  # 从纠错后的比特中提取逻辑值

.. code-block:: python

   # 伴随式解码逻辑
   # Z稳定子伴随式共6位, 每2位对应一个三比特分组:
   # (s0, s1) = (1, 0) -> 第0比特错误
   # (s0, s1) = (1, 1) -> 第1比特错误
   # (s0, s1) = (0, 1) -> 第2比特错误

量子纠错码工厂
----------------

``QecFactory`` 是量子纠错码的工厂类，维护量子纠错码注册表，并提供按名称创建量子纠错码实例的能力。

.. code-block:: python

   class QecFactory:
       """Factory class for creating quantum error correction code instances.

       Example:
           >>> factory = QecFactory()
           >>> shor_code = factory.create("shor")
       """

工厂默认注册了 ``"shor"`` 对应的 ``ShorCode``。支持的扩展操作包括：

.. list-table:: QecFactory 方法说明
   :widths: 20 30 50
   :header-rows: 1
   :align: left

   * - 方法
     - 功能
     - 说明
   * - **create(name)**
     - 创建纠错码实例
     - 根据名称创建量子纠错码实例，未注册的名称抛出 ``ValueError``
   * - **register(name, code_class)**
     - 注册纠错码
     - 注册量子纠错码类，非 ``QuantumCodeBase`` 子类抛出 ``TypeError``
   * - **unregister(name)**
     - 注销纠错码
     - 注销已注册的量子纠错码，未注册的名称抛出 ``KeyError``
   * - **list_codes()**
     - 列出已注册纠错码
     - 返回所有已注册的量子纠错码名称列表
   * - **get_registry()**
     - 获取注册表
     - 返回内部注册表的副本

使用示例
------------

创建Shor码实例：

.. code-block:: python

   from wy_qcos.qec.qec_factory import QecFactory

   factory = QecFactory(None)
   qec_code = factory.create("shor")
   qec_code.set_distance(3)
   qec_code.set_physical_bit_num(9)
   qec_code.set_logical_bit_num(1)

与Stim驱动集成
------------------

QEC模块与Stim驱动（``DriverStim``）集成，通过作业提交参数 ``qec_options`` 启用量子纠错功能。Stim驱动的 ``qec_options`` 配置如下：

.. code-block:: python

   # DriverStim.qec_options_schema
   {
       "qec_code": str,                    # 量子纠错码名称，必填，如 "shor"
       Optional("distance"): int,          # 码距
       Optional("phy_bit_num"): int,       # 物理比特数
       Optional("logical_bit_num"): int,   # 逻辑比特数
       Optional("error_inject"): {         # 错误注入配置
           "error_type": str,              # 错误类型
           "noise_prob": float,            # 噪声概率
       },
   }

Stim驱动QEC作业执行流程如下：

.. code-block:: text

   convert_circuit(raw_circuit)  # 将BaseOperation列表转换为Stim线路
   -> QecFactory.create(qec_code_str)  # 创建量子纠错码实例
   -> validate_and_format_circuit()  # 校验并格式化线路（Shor码仅支持1比特）
   -> encode(circuit, error_inject=error_inject)  # 编码并可选注入噪声
   -> compile_sampler().sample(shots)  # 编译采样器并采样
   -> compute_samples()  # 提取伴随式和原始比特
   -> decode()  # 解码得到错误位置
   -> correct(err_pos)  # 纠错
   -> logical_measure()  # 提取逻辑值
   -> format_result()  # 统计并格式化结果

作业提交示例：

.. code-block:: python

   job_info = {
       "dry_run": False,
       "backend": "stim",
       "qec_options": {
           "qec_code": "shor",
           "distance": 3,
           "error_inject": {
               "error_type": "x_error",
               "noise_prob": 0.05,
           },
       },
       "shots": 100,
   }
