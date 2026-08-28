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

自动调度
********************
自动调度是指，用户提交任务时，不指定backend名称，由操作系统自动选择后端设备，并提交任务到该设备所关联的deployment/workpool环境中运行。

自动调度的详细设计（调度流程、Filter/Weigher、Flavor/extra_specs、
设备可用率统计、配置等）见独立文档： :doc:`auto-scheduler`。
