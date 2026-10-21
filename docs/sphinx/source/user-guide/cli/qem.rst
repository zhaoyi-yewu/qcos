量子错误缓解
================

量子错误缓解（Quantum Error Mitigation, QEM）通过作业提交参数
``qem_options`` 启用，提供读出错误缓解（REM）、零噪声外推（ZNE）和
动力学解耦（DD）三种策略，在不额外引入物理量子比特资源的前提下抑制
噪声对计算结果的影响。

.. note::

   ``qcos-cli`` 命令行当前暂未暴露 ``--qem-options`` 参数，
   错误缓解需通过 Python 客户端的 ``submit_job(qem_options=...)`` 启用，
   详见 :doc:`/user-guide/sdk` 与 :doc:`/user-guide/scenario/qem`。

通过 SDK 提交时，``qem_options`` 结构如下：

.. code-block:: python

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

错误缓解的端到端操作流程详见 :doc:`/user-guide/scenario/qem`，
各策略算法细节与级联顺序详见 :doc:`/design/module-design/qem`。
