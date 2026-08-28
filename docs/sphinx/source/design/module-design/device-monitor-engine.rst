设备监控引擎
=============

设备监控引擎（device monitor engine）主要用来执行周期性任务获取设备的运行信息，包括状态等。

设备监控引擎与 Prefect Worker 的关系
--------------------------------------

设备监控引擎（即 :func:`device_monitor_flow`）本身并不直接被 API 进程调用，而是以
Prefect **flow** 的形式注册为 deployment，由独立的 **Prefect Worker 进程** 拉取并执行。
二者是"被调度者"与"调度执行者"的关系：

- **设备监控引擎**：即 :func:`device_monitor_flow`，是一个被 ``@flow`` 装饰的 Prefect
  flow，负责周期性采集设备运行信息（状态、可用性等）。
- **Prefect Worker**：由 :class:`ProcessWorker` 实现的常驻进程，负责从 Prefect Server
  轮询其所归属工作池中的 flow run，拉取到任务后在本地子进程中执行对应的 flow。

每个设备在启动时会创建一个 **monitor Worker** 进程，绑定到 ``monitor|{device_name}``
工作池（工作池前缀为 ``monitor|``）。该 Worker 仅在设备启用监控
（``enable_device_monitor``）时启动，监听 ``default`` 队列。

部署与启动流程：

1. :meth:`generate_deployment_configs` 为设备生成 deployment，将
   :func:`device_monitor_flow` 关联到 ``monitor|{device_name}`` 工作池，
   入口命令为 ``python -m prefect.engine``。
2. :meth:`create_deployments` 通过 :meth:`flow.deploy` 在 Prefect Server 注册
   deployment 并记录 ``deploy_id``。
3. :meth:`start_workers` 调用 :meth:`_start_worker_process` 以
   ``multiprocessing.Process`` 启动 monitor Worker，Worker 内部实例化
   :class:`ProcessWorker` 并 :meth:`worker.start` 进入轮询循环。
4. 系统启动后 :meth:`run_device_monitor` 通过
   ``create_flow_run_from_deployment`` 为每个设备创建监控 flow run，
   由对应 Worker 拉取执行。

.. note::

   monitor Worker 与 job Worker 使用不同的工作池（``monitor|`` vs ``device|``），
   二者互不影响，监控任务的排队/执行不会阻塞量子作业，反之亦然。

监控数据与自动调度的关系
--------------------------

设备监控引擎周期性采集的设备状态（online/busy/disconnected/maintain 等）与可用性指标，
会通过 DeviceManager 更新到设备对象上。自动调度器（AutoScheduler）在为作业
选择后端时，会读取这些实时状态作为 Filter 链的过滤条件：

- 仅状态为 ``online`` 或 ``busy`` 的设备才会被纳入候选
- ``maintain`` 状态的设备会被排除
- Flavor 的 ``qc:device_availability`` 约束基于监控采集的可用性数据过滤

因此监控引擎的可用性直接影响自动调度（``flavor_id`` / ``extra_specs`` 路径）
的设备候选集合；而指定 ``backend`` 的直通路径不受调度过滤影响，但仍会校验
设备状态是否可执行。

设备监控引擎调用驱动
---------------------

引擎层核心调用逻辑如下：

.. code-block:: python

   device_monitor_flow ->
      init_driver()                    # 初始化驱动
      redis.Redis()                    # 生成 Redis 实例
      while True:                      # 周期性执行
        driver.fetch_running_info()    # 通过 driver 获取设备运行信息
        redis_instance.publish()       # 发布到 Redis
        time.sleep(interval)

Device Manager 订阅 Redis
----------------------------

Device Manager 调用逻辑如下：

.. code-block:: python

   init_devices ->
      loop devices.items() [           # 遍历设备列表
        device.init_device()           # 初始化设备
        thread = threading.Thread(     # 启动订阅线程
                target=self.subscribe_device_info,
                args=(self.redis_instance, device),
            )
      ]
   self.subscribe_device_info ->
      redis_instance.pubsub()          # 创建 Redis 实例
      pubsub.subscribe(device.name)
      pubsub.listen():                 # 监听 Redis 消息
        device_info = json.loads(message["data"])
        status = device_info["status"]
        device.set_status(status)      # 更新设备信息

设备上线率统计
----------------

设备上线率（availability rate）用于衡量设备的可用性，统计窗口为整点小时，
作为 ``DeviceAvailabilityWeigher`` 的权重输入参与自动调度。整体流程如下：

1. **实时采集**：``DeviceAvailabilityCollector``（单例）启动一个后台线程，
   通过 Redis psubscribe 订阅 ``qcos/device_running_info/*`` 模式频道，
   接收所有设备运行信息上报。每收到一条样本，对应设备的
   ``total_count`` 加 1；当 ``status`` 为 ``online`` 或 ``busy`` 时
   ``online_count`` 同时加 1。计数器（``DeviceAvailabilityCounter``）保存在
   内存中，反映当前小时的实时采样。

2. **整点聚合**：``DeviceAvailabilityScheduler`` 基于 APScheduler 的
   ``CronTrigger(minute=0)``，在每小时整点触发 ``aggregate_availability_hourly``
   任务。该任务调用 ``snapshot_and_reset()`` 原子地取出当前计数快照并
   清零内存计数器，随后将快照 upsert 到 ``device_availability_hourly`` 表
   （唯一约束 ``uq_device_availability_hourly`` 覆盖 ``device_name`` + ``hour``），
   开始下一小时的统计。

3. **调度注入**：``AutoScheduler._build_device_states`` 通过
   ``DeviceAvailabilityCollector.get_rate()`` 获取当前小时实时上线率，注入
   ``DeviceState.availability``；``DeviceAvailabilityWeigher`` 据此对设备加权，
   上线率越高的设备权重越大、越优先被调度。

.. code-block:: python

   # collector: per-device in-memory counters for the current hour
   psubscribe("qcos/device_running_info/*") ->
     _handle_message(channel, data) ->
       total_count += 1
       if status in ("online", "busy"): online_count += 1

   # scheduler: hourly aggregation at minute=0
   CronTrigger(minute=0) -> aggregate_availability_hourly() ->
     snapshot = DeviceAvailabilityCollector().snapshot_and_reset()
     DeviceAvailabilityRepository.upsert_hourly(hour, snapshot)

   # scheduler weigher: higher availability rate = higher weight
   DeviceAvailabilityWeigher._weigh_object(device_state) ->
     return device_state.availability

.. note::

   上线率取值范围为 ``0.0`` ~ ``1.0``；当前小时尚无采样时
   ``get_rate`` 返回 ``None``，此时调度权重视为 ``0.0``。历史小时级
   上线率持久化于 ``device_availability_hourly`` 表，可通过
   ``DeviceAvailabilityRepository.get_availability`` / ``get_last_hour_availability`` 查询。
