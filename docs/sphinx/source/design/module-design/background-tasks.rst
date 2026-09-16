后台任务
==========

本章节介绍 QCOS 系统中基于 APScheduler 实现的周期性后台任务。这些任务在系统启动时通过 ``BackgroundServiceManager`` 统一注册和管理生命周期，负责内存回收、孤立流程清理和过期作业清理等运维工作。

概述
----

QCOS 后台任务均位于 ``wy_qcos.task_manager`` 模块下，采用 ``AsyncIOScheduler`` 调度，具有以下共同特性：

* **单实例执行**：配置 ``max_instances=1``，确保同一时刻只有一个任务实例运行
* **合并堆积**：配置 ``coalesce=True``，跳过错过的执行，避免任务堆积
* **可配置间隔**：通过配置文件的 ``[DEFAULT]`` 段控制执行间隔
* **可禁用**：将间隔配置设为 ``-1`` 可禁用对应任务
* **异常隔离**：单次执行失败不影响后续调度，错误通过日志记录

模块组成
--------

* ``task_manager/gc_cleaner.py`` — 周期性垃圾回收服务（GcCleaner）
* ``task_manager/job_cleaner.py`` — 作业与流程清理服务（JobCleaner）

GcCleaner（周期性垃圾回收）
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``GcCleaner`` 定期执行 Python 垃圾回收和 glibc 堆内存释放，缓解内存碎片和缓慢内存泄漏问题。

调度配置：

* **间隔**：由 ``Config.DEFAULT.GC_INTERVAL`` 控制（单位：天，默认 1 天）
* **禁用**：``GC_INTERVAL = -1`` 时跳过启动
* **调度器**：``AsyncIOScheduler``，``max_instances=1``，``coalesce=True``

每次执行的操作：

1. ``gc.collect(2)`` — 回收所有 3 代对象（全量回收）
2. ``Library.malloc_trim(0)`` — 调用 glibc ``malloc_trim`` 将空闲堆内存归还操作系统（仅 Linux glibc 可用，其他平台跳过）

适用场景：

* 长时间运行的服务进程，Python 垃圾回收器无法回收的内存碎片
* 缓慢内存泄漏的临时缓解（根本修复需定位泄漏源）
* Prefect/Pydantic 等依赖库产生的临时对象导致的内存增长

.. note::
   ``malloc_trim`` 仅在 Linux glibc 环境下可用，其他平台（如 Windows、musl libc）会跳过该步骤并记录 debug 日志。

JobCleaner（作业与流程清理）
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``JobCleaner`` 定期扫描 Prefect flow runs 和数据库中的作业记录，清理孤立流程和过期数据。

调度配置：

* **间隔**：由 ``Config.DEFAULT.JOB_SCAN_INTERVAL`` 控制（单位：分钟，默认 60 分钟）
* **调度器**：``AsyncIOScheduler``，``max_instances=1``，``coalesce=True``

每次执行按顺序执行三个清理子任务：

1. **清理孤立设备流程（flow-clean）** — ``_clean_orphaned_device_flows()``

   扫描所有 Prefect flow runs，识别 device 工作池中名称为 UUID 但在数据库作业表中不存在的流程（孤立流程），依次执行取消、等待终态、删除 flow run 和关联 artifacts。

   * 通过 ``TaskFlowManager.read_all_flow_runs()`` 分页拉取全部 flow runs
   * 从数据库获取全部作业 ID 集合，DB 查询失败时中止清理以防止误删
   * 跳过 monitor、mgr 前缀的工作池和非 UUID 名称的流程

2. **清理过期已完成流程（flow-clean）** — ``_clean_prefect_flows()``

   删除属于 job-flow 且已结束（COMPLETED/FAILED/CRASHED/CANCELLED）且结束时间超过 ``FLOW_EXPIRE_DAYS`` 的 flow runs 及其 artifacts。

   * 由 ``Config.DEFAULT.FLOW_EXPIRE_DAYS`` 控制（单位：天，``-1`` 禁用）
   * 通过 ``TaskFlowManager.read_all_flow_runs()`` 分页拉取全部 flow runs
   * 按 ``flow_id`` 过滤出 job-flow 的 flow runs，再按 ``end_time`` 判断是否过期

3. **清理过期作业（job-clean）** — ``_clean_expired_job_flows()``

   删除数据库中创建时间超过 ``JOB_EXPIRE_DAYS`` 的作业记录，同时删除其关联的 Prefect flow runs 和 artifacts。

   * 由 ``Config.DEFAULT.JOB_EXPIRE_DAYS`` 控制（单位：天，``-1`` 禁用）
   * 从数据库查询所有作业，按 ``created_at`` 判断是否过期
   * 先删除 Prefect flow run 和 artifacts，再删除数据库作业记录

read_flow_runs 分页机制
^^^^^^^^^^^^^^^^^^^^^^^

由于 Prefect 的 ``read_flow_runs()`` 受 ``PREFECT_API_DEFAULT_LIMIT``（默认 200）限制，
单次请求无法返回全部 flow runs。``JobCleaner`` 通过 ``TaskFlowManager.read_all_flow_runs()`` 辅助方法进行分页拉取：

* 以 ``page_size=200`` 为页大小，通过 ``offset`` 递增循环请求
* 当某页返回数量小于 ``page_size`` 时终止循环
* 确保清理逻辑不会因分页限制遗漏超过 200 条的 flow runs

配置项汇总
~~~~~~~~~~

.. list-table:: 后台任务相关配置项
   :widths: 35 15 20 30
   :header-rows: 1
   :align: left
   :class: longtable

   * - 配置项
     - 默认值
     - 单位
     - 说明
   * - ``GC_INTERVAL``
     - 1
     - 天
     - GcCleaner 执行间隔，``-1`` 禁用
   * - ``JOB_SCAN_INTERVAL``
     - 60
     - 分钟
     - JobCleaner 执行间隔
   * - ``JOB_EXPIRE_DAYS``
     - -1
     - 天
     - 作业过期天数，``-1`` 永不过期
   * - ``FLOW_EXPIRE_DAYS``
     - 1
     - 天
     - 已完成流程过期天数，``-1`` 永不过期
