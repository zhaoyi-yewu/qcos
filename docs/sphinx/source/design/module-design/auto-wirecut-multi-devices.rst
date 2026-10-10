自动线路切割到多设备
=======================

自动线路切割（Auto Wirecut）是指，当用户提交的作业所需量子比特数超过所有可用设备的最大比特数时，QCOS 自动将线路切割为多个子电路，分发到多台设备上并发执行，最后合并结果，从而支持超出单设备容量的大规模量子线路。

自动切割是自动调度（Auto Scheduler）的扩展能力：当调度器因 ``QubitCountFilter`` 过滤失败（所有设备比特数不足）时，不直接拒绝作业，而是回退到 wirecut 模式，将原始线路拆分后重新调度到多个设备。

.. contents::
   :local:
   :depth: 2


设计目标
--------------------

1. **突破单设备比特数限制**：支持超出任一单台设备最大比特数的量子线路
2. **按需启用**：用户通过 ``options.enable_wirecut`` 显式开启，
   对切割过程无需感知
3. **自动回退**：调度因比特数不足失败时自动触发切割，无需手动指定设备
4. **并发执行**：子电路分发到多台设备并行运行，缩短总执行时间
5. **结果聚合**：自动收集所有子电路结果并合并为完整结果


整体架构
--------------------


触发条件
--------------------

自动切割在以下条件下触发：

1. 用户提交作业时未指定 ``backend`` （启用自动调度）
2. 自动调度器执行 ``QubitCountFilter`` 过滤后，所有设备均因比特数不足被过滤
3. 此时调度器抛出 ``DeviceQubitExceededError`` 而非 ``NoValidDeviceError``
4. ``submit_job`` API 捕获 ``DeviceQubitExceededError`` 后，检查作业的
   ``options.enable_wirecut`` 是否为 ``True``：

   - **开启**\（ ``enable_wirecut=True`` ）：将 ``backend_type``
     设置为 ``wirecut``，通过 ``get_last_filtered_devices()``
     获取通过非比特数过滤的候选设备列表，序列化为
     ``filtered_devices`` 附加到作业数据中，然后以 wirecut 模式
     提交到 ``vdev|wirecut`` 工作池
   - **关闭**\（ ``enable_wirecut=False`` 或未设置 ）：直接返回
     ``BadRequestError``，提示用户比特数超出设备限制

   ``enable_wirecut`` 来自作业提交时的 ``options`` 字段，默认为
   ``False``。用户需显式设置 ``{"enable_wirecut": true}`` 才能启用自动切割回退。

5. ``enable_wirecut`` 开启且存在候选设备时，作业以 wirecut 模式
   提交到 ``vdev|wirecut`` 工作池

.. note::

   ``QubitCountFilter`` 必须在 ``etc/qcos/qcos.toml`` 的
   ``ENABLED_FILTERS`` 列表中排在 **最后**，以确保所有其他过滤器
   先执行，这样 ``filtered_devices`` 中保留的是满足所有非比特数
   条件的设备，可作为切割后的候选设备。


核心组件
--------------------


wirecut_engine
~~~~~~~~~~~~~~~~~~~~~~~

``wirecut_engine`` 是自动切割的核心引擎，以 Prefect Flow
（``wirecut_flow``）形式运行在 ``vdev|wirecut`` 虚拟设备工作池中。

主要函数：

- ``wirecut_flow`` — Prefect Flow 入口，编排切割、提交、监听的完整流程
- ``wirecut_schedule`` — 将源码切割为子电路，并为每个子电路分配设备
- ``submit_jobs`` — 通过 ``create_flow_run_from_deployment`` 将子电路
  提交到对应设备的 ``dev|{device}`` 工作池的
  ``dev|{device}_4`` 优先级队列
  （ ``SUB_WIRECUT_PRIORITY = 4`` ，高于默认优先级 ``5`` 的队列，
  确保子电路作业优先于普通用户作业被调度执行）
- ``poll_job_results`` — 订阅 Redis Pub/Sub 通道并回查快照，
  收集子电路结果，等待全部到达终态后返回


调度器增强
~~~~~~~~~~~~~~~~~~~~~~~

``AutoScheduler`` 新增以下能力以支持 wirecut 回退：

- ``DeviceQubitExceededError`` — 新增异常，当唯一失败过滤器为
  ``QubitCountFilter`` 时抛出，区别于通用的 ``NoValidDeviceError``
- ``BaseFilterHandler.get_filtered_objects`` — 新增
  ``run_all_filters`` 参数和返回值 ``last_failed_filter``，用于
  区分失败原因
- ``AutoScheduler.schedule`` — 新增 ``run_all_filters`` 参数，
  并保存 ``last_filtered_devices`` 供 API 层获取候选设备
- ``AutoScheduler.get_last_filtered_devices`` — 获取最近一次过滤后
  保留的设备列表（满足非比特数条件，但被 QubitCountFilter 过滤）


Redis 双存储机制
--------------------

自动切割的子电路作业使用 Redis 存储结果（``results_db_storage = "redis"``），
而普通作业使用 SQL 数据库（``results_db_storage = "sql"``）。
这避免了大量短生命周期子电路作业对主数据库造成写入压力。


存储 Key 格式
~~~~~~~~~~~~~~~~~~~~~~~

::

   /qcos/jobs/{flow_run_name}/{flow_run_id}

其中 ``flow_run_name`` 是子电路对应的 Prefect Flow Run Name（即子作业
的 ``job_id``），``flow_run_id`` 是子电路对应的 Prefect Flow Run ID，
两者共同唯一标识一个子电路的存储位置。同一个 redis key 同时也是
pub/sub channel 名称，子电路每次更新状态时在该 channel 上发布通知。


存储内容
~~~~~~~~~~~~~~~~~~~~~~~

子电路作业完成后，``db_job_callback`` 将以下字段写入 Redis：

.. code-block:: json

   {
     "job_status": "COMPLETED",
     "progress": 100,
     "results": [
       {
         "metadata": {"status": "COMPLETED"},
         "counts": {"00": 512, "11": 512},
         "profiling": {}
       }
     ],
     "started_at": "2026-09-30T14:24:43.870115",
     "ended_at": "2026-09-30T14:25:10.123456",
     "is_callback_success": true,
     "flow_run_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
     "backend": "dummy",
     "callbacks": []
   }


db_utils 改造
~~~~~~~~~~~~~~~~~~~~~~~

``db_utils`` 模块通过 ``results_db_storage`` 参数实现双存储分发：

- ``db_job_callback`` — 从作业数据读取 ``results_db_storage`` 和
  ``db_config.ttl``，redis 模式下以
  ``{REDIS_CHANNEL_JOB_PREFIX}/{job_id}/{flow_run_id}`` 作为 key
  存储结果，并在同一 channel 上发布 pub/sub 通知
- ``db_update_job`` — 新增 ``flow_run_id`` / ``ttl`` 参数，通过
  ``get_job_storage_backend()`` 工厂方法分发到 SQL 或 Redis 后端，
  ``db_engine`` 参数在 SQL 模式下为 SQLAlchemy engine，在 Redis
  模式下为 redis client
- ``store_sub_job_context`` — 在子电路开始执行前预存
  ``flow_run_id`` / ``backend`` / ``callbacks`` 等上下文，供父作业
  后续查询子电路信息
- ``redis_update_job`` / ``redis_get_job`` — Redis 读写辅助函数，
  支持 merge 更新和完整读取


子电路结果收集
--------------------

``poll_job_results`` 使用 **订阅 + 快照回查** 模式收集子电路
结果，而非轮询。发布端（子电路侧）由
``RedisJobStorageBackend.update_job`` 在每次更新记录时调用
``redis_client.publish(channel, record_json)`` 发布通知，
channel 名称与 redis key 相同，因此进度变化和终态通知都能被
父流程近实时接收。


竞态问题与消息丢失
~~~~~~~~~~~~~~~~~~~~

该机制需要防御两类丢消息场景：

**场景一：订阅建立前的消息丢失（竞态）**

Redis Pub/Sub **不回放订阅建立之前发布的消息**。而
``submit_jobs`` 提交子电路与 ``poll_job_results`` 建立订阅
之间存在时间窗口（循环提交多个子电路、构建 pending 列表等），
快速完成的子电路可能在该窗口内到达终态，其通知在无人订阅时
发布即永久丢失。

消除方式是经典的 **先订阅、后快照** 顺序：

1. 先 ``SUBSCRIBE`` 全部子电路 channel
2. 再逐一 ``GET`` 各子电路的 redis key 回查快照，
   已经处于终态的子电路直接收集
3. 之后进入有限超时监听

订阅点之前的状态由快照覆盖，订阅点之后的更新由订阅覆盖，
两者无缝衔接、不重不漏。

**场景二：订阅建立后的消息丢失（publish 失败）**

子电路侧 ``RedisJobStorageBackend.update_job`` 的 ``SET`` 与
``PUBLISH`` 是**两次独立的 redis 调用**，不是原子操作：终态
记录可能已安全落库（redis key 存在），但其 publish 通知丢失
（网络闪断、publish 异常被降级为 warning 等）。实测中出现过
6 个子电路全部完成、redis 记录完整存在、但父流程仅收到 2 个
终态通知的情况。

消除方式是 **有限超时监听 + 超时回查兜底**：监听循环阻塞在
``get_message(timeout=POLL_MESSAGE_TIMEOUT)`` （5 秒）上，超时
未收到任何消息时，对仍处于 pending 的子电路重做一轮 redis key
回查。记录既然已落库，最多延迟一个超时周期即可被收集，父流程
永不因丢消息而永久挂起。


监听流程
~~~~~~~~~~~~~~~

.. plantuml:: ../../_static/design/module-design/auto-wirecut-watch-flow.puml
   :alt: 子电路结果监听流程图
   :width: 80%
   :align: center

.. centered:: *子电路结果监听流程图*


设计要点
~~~~~~~~~~~~~~~

1. **订阅 Channel**：``submit_jobs`` 返回的每个子电路包含
   ``flow_run_id`` 和 ``job_id``，据此构造 channel
   ``/qcos/jobs/{job_id}/{flow_run_id}``，一次性订阅
   所有子电路的 channel
2. **快照回查**：订阅建立后立即逐一 ``GET`` 各子电路的
   redis key，已到达终态的子电路直接从快照收集，
   消除提交到订阅窗口内的通知丢失竞态
3. **有限超时监听**：通过 ``get_message(timeout=5s)`` 等待
   消息，每条消息的 data 是子电路最新的完整 record JSON，
   可直接读取 progress 和 job_status；
   超时无消息时对 pending 子电路重做一轮 redis key 回查，
   兜底收集因 publish 丢失而未收到通知的终态记录
4. **终态判断**：``COMPLETED`` / ``FAILED`` / ``CANCELLED``
   视为终态，收集到结果后从 pending 列表移除
5. **退出条件**：所有子电路都到达终态（pending 集合为空）
   后退出监听循环
6. **清理**：监听结束后 DELETE 已消费的 redis key
7. **结果顺序**：返回的结果列表顺序与 ``new_job_list``
   一致，便于与子电路一一对应


完整流程
--------------------


1. 用户提交作业
~~~~~~~~~~~~~~~~~~~~~~~

1. 用户通过 ``submit_job`` API 提交作业，不指定 ``backend``，
   并在 ``options`` 中设置 ``{"enable_wirecut": true}``
2. API 层构建 ``RequestSpec``，调用 ``AutoScheduler.schedule``
3. 调度器执行所有过滤器
4. ``QubitCountFilter`` 过滤掉所有设备（比特数不足）
5. 调度器抛出 ``DeviceQubitExceededError``

2. 回退到 wirecut 模式
~~~~~~~~~~~~~~~~~~~~~~~

1. ``submit_job`` 捕获 ``DeviceQubitExceededError``
2. 检查 ``options.enable_wirecut`` 是否为 ``True``：

   - 是：继续 wirecut 回退流程
   - 否：返回 ``BadRequestError``，提示比特数超出限制

3. 调用 ``auto_scheduler.get_last_filtered_devices()`` 获取候选设备
4. 若候选设备为空，返回 ``BadRequestError``\（无可用设备）
5. 通过 ``build_serialized_filtered_devices`` 将候选设备序列化为
   ``filtered_devices`` 列表
6. 设置 ``backend_type = "wirecut"``， ``backend = "wirecut"``
7. 将作业提交到 ``vdev|wirecut`` 工作池

3. wirecut_flow 执行
~~~~~~~~~~~~~~~~~~~~~~~

1. ``wirecut_flow`` 在 ``vdev|wirecut`` 工作池启动
2. 初始化 logger，更新作业状态为 ``RUNNING``
3. 初始化数据库引擎并注册到 ``db_utils``
4. 启动 ``flow_task_monitor`` 任务监控
5. 创建 Redis 实例并注册到 ``db_utils`` （ ``set_redis_client`` ）
6. 调用 ``wirecut_schedule`` 切割线路并分配设备
7. 调用 ``submit_jobs`` 将子电路通过
   ``create_flow_run_from_deployment`` 提交到各设备工作池
8. 调用 ``poll_job_results`` 监听 Redis 收集子电路结果
9. 返回结果列表

4. 子电路执行
~~~~~~~~~~~~~~~~~~~~~~~

1. 各子电路在对应设备工作池的 ``dev|{device}_4`` 优先级队列中
   执行（ ``SUB_WIRECUT_PRIORITY = 4`` ，高于默认优先级 ``5`` ）
2. 完成后触发 ``db_job_callback``
3. ``db_job_callback`` 将结果写入 Redis key
   ``/qcos/jobs/{job_id}/{flow_run_id}``，
   并在同一 channel 上发布 pub/sub 通知
4. 若通知发布时父流程尚未订阅（子电路在提交->订阅窗口内
   完成），该通知丢失，但结果已持久化在 redis key 中，
   由 ``poll_job_results`` 的快照回查兜底收集

5. 结果收集
~~~~~~~~~~~~~~~~~~~~~~~

1. ``poll_job_results`` 先订阅全部 channel，再回查快照，
   随后阻塞监听，收集所有子电路结果
2. 删除已消费的 Redis key
3. 返回结果列表给 ``wirecut_flow``


配置说明
--------------------


etc/qcos/qcos.toml
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: toml

   [SCHEDULER]
   ENABLE_AUTO_SCHEDULE = true

   # QubitCountFilter 必须排在最后，以确保 wirecut 回退时
   # filtered_devices 中保留的是满足所有非比特数条件的设备
   ENABLED_FILTERS = [
     "CodeTypeFilter",
     "InputConstraintsFilter",
     "DeviceStatusFilter",
     "TechTypeFilter",
     "QueueLimitFilter",
     "GateFidelityFilter",
     "DeviceAvailabilityFilter",
     "DeviceNameFilter",
     "DeviceGroupFilter",
     "QubitCountFilter",  # must be last for auto wirecut
   ]


Redis 配置
~~~~~~~~~~~~~~~~~~~~~~~

无需特殊配置。Pub/Sub 是 Redis 的内置功能，默认可用，
无需启用 Keyspace Notifications。


子电路优先级队列
~~~~~~~~~~~~~~~~~~~~~~~

子电路作业提交到设备工作池时使用专用优先级队列
``dev|{device_name}_{SUB_WIRECUT_PRIORITY}``
（即 ``dev|{device_name}_4`` ）。Prefect 队列优先级数值越小
越优先， ``SUB_WIRECUT_PRIORITY = 4`` 高于默认作业优先级
``DEFAULT_JOB_PRIORITY = 5`` ，使父作业已占用的设备资源能优先
服务于其子电路，避免父作业等待子电路时设备被其他用户作业
长时间占用。常量定义见
``Constant.SUB_WIRECUT_PRIORITY``\（ ``constant.py`` ）。


工作池命名
~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :widths: 30 40 30
   :header-rows: 1

   * - 工作池类型
     - 命名格式
     - 用途
   * - ``WORK_POOL_DEV``
     - ``dev|{device_name}``
     - 设备作业执行
   * - ``WORK_POOL_MON``
     - ``mon|{device_name}``
     - 设备监控
   * - ``WORK_POOL_MGR``
     - ``mgr|{device_name}``
     - 设备管理任务
   * - ``WORK_POOL_VDEV``
     - ``vdev|wirecut``
     - 虚拟设备（wirecut 引擎）

设备工作池内的队列命名格式为
``dev|{device_name}_{priority}`` ，普通作业默认提交到
``dev|{device_name}_5`` 队列\（ ``DEFAULT_JOB_PRIORITY = 5`` ），
wirecut 子电路提交到 ``dev|{device_name}_4`` 队列
\（ ``SUB_WIRECUT_PRIORITY = 4`` ）以获得更高调度优先级。


相关常量
--------------------

.. list-table::
   :widths: 40 60
   :header-rows: 1

   * - 常量
     - 说明
   * - ``BACKEND_TYPE_DEVICE``
     - 普通设备作业
   * - ``BACKEND_TYPE_WIRECUT``
     - wirecut 虚拟设备作业
   * - ``RESULTS_DB_STORAGE_SQL``
     - SQL 数据库存储
   * - ``RESULTS_DB_STORAGE_REDIS``
     - Redis 存储子电路结果
   * - ``REDIS_CHANNEL_JOB_PREFIX``
     - Redis key/channel 前缀 ``/qcos/jobs``
   * - ``VIRT_DEIVCE_WIRECUT``
     - 虚拟设备名 ``wirecut``
   * - ``WORK_POOL_VDEV``
     - 虚拟设备工作池前缀 ``vdev``
   * - ``DEFAULT_JOB_PRIORITY``
     - 普通作业默认优先级 ``5``
   * - ``SUB_WIRECUT_PRIORITY``
     - wirecut 子电路作业优先级 ``4`` ，数值小于默认优先级，
       在 Prefect 队列中优先于普通作业被调度
   * - ``JOB_TERMINAL_STATUSES``
     - 作业终态集合 ``COMPLETED`` / ``FAILED`` / ``CANCELLED``
       ，``poll_job_results`` 据此判断子电路是否完成
