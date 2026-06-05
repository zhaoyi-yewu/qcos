作业管理和调度
================

本章节主要介绍作业管理和调度。

作业管理和Prefect
--------------------
作业管理中利用到了工作流编排管理库: Prefect。 Prefect的核心理念是将工作流视为代码，通过Python语言来定义任务和流程，
使得工作流具有高度的可读性、可维护性和可扩展型，能够轻松地构建、调度和监控复杂的工作流。而量子作业较为复杂，特别适合使用工作流来进行编排管理。

.. plantuml:: ../../_static/design/module-design/jobs-arch.puml
   :caption: 作业管理和调度架构图
   :alt: 作业管理和调度架构图
   :width: 80%
   :align: center

- qcos启动后task-manager组件会初始化prefect server，启动针对不同驱动的work-pool，每个work-pool内置10个queue并共享一个worker
- 命令行或者北向接口接收用户的作业请求后， 解析作业优先级类型、计算作业优先级、后端类型、qasm文件 / qubo矩阵
- 根据后端类型，查找对应后端的flow脚本，并将步骤2解析出的作业信息作为flow参数，提交至prefect-server
- 当prefect的worker空闲时，会根据所在worker-pool的队列的优先级，从队列取出flow作业并执行

作业结束回调机制
--------------------
作业提交时，支持设置可选的callback列表，callback信息中包括: name, type, method, timeout, retries, headers, url等。
该功能能够在作业结束时，主动发送http api请求到指定位置进行返回值的回调通知。
如果作业因各种原因导致没有成功回调，支持在qcos服务重启时根据作业中metadata字段中的callback_success失败信息进行重新回调。

作业调度
--------------------
作业调度是指，用户提交作业时，系统根据用户提交的作业信息和设备的动态信息，选择合适的后端设备，并将作业提交到该设备所关联的deployment/workpool环境中运行。
调度可分为静态调度和自动调度两种方式。

静态调度
********************
提交任务时，需要用户指定后端的backend名称，即设备名称，此时任务会直接提交到设备所关联的deployment/workpool环境中运行。

自动调度 (规划)
********************
自动调度是指，用户提交任务时，不指定backend名称，由操作系统自动选择后端设备，并提交任务到该设备所关联的deployment/workpool环境中运行。

自动调度功能可能依赖于设备动态信息，来做调度决策。目前设备动态信息会由每个设备独立的prefect长任务进行定时收集，信息回存在redis数据库中供其它组件读取和使用。

自动调度可以通过下列参数进行综合判断选择后端设备，包括：

**必须符合的条件：**

- 匹配设备支持的输入的代码类型CODE_TYPE：QASM、QASM2、QASM3、QUBO等
- 设备的在线状态，必须为在线
- 输入的量子比特数满足后端设备要求 【可选】

**按权重排序的条件：**

- 设备繁忙度、排队情况 【可选】
- 历史任务(每QBIT)的平均执行时间 【可选】

自动调度时，使用调度过滤器，先过滤必须符合的条件，如果没有设备符合则直接报错：没有符合条件的设备。如果返回了多个设备，则按照权重排序条件，依次进行过滤，

自动调度会在submit_job中增加2个可选参数: flavor_id和extra_specs。 flavor_id是用户选择的预设的调度策略，extra_specs是用户自定义的调度参数。

用了flavor_id后，额外的调度参数依然建议保留在一个独立的extra_specs字段中。因为 Flavor 定义的是“静态的、硬件的物理规格”，而有些调度参数是“动态的、单次作业特有的运行策略”。两者解耦，设计最清晰。

最终的用户提交json示例：

.. code-block:: json

   {
     "job_name": "my-job",
     "source_code": ["..."], // 代码类型和内容
     "flavor_id": "00000000-0000-4000-8000-000000000001", // 决定去什么规格的机器
     "extra_specs": {                           // 额外调度参数
        "max_qubits": 100,
     }
   }

flavor_id 对应的预设调度策略规格示例：

.. code-block:: json

   {
       "id": "00000000-0000-4000-8000-000000000001",
       "name": "q-flavor-superconducting",
       "description": "superconducting quantum computer",
       "is_public": true,
       "specs": {
           "min_qubits": 16,
           "max_qubits": null,
           "tech_type": "superconducting",
           "gate_fidelity_2q_min": 0.995
       }
   }

针对特殊硬件或者动态调度需求，用户可以通过额外的extra_specs来定义一些特定的调度参数，这些参数会被传递到调度器中进行处理。
