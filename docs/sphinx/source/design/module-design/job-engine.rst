作业引擎/量子引擎
====================

作业引擎/量子引擎层(job engine)是量子操作系统的核心，主要用来解析、转译、优化、调用测控系统或真机执行量子程序、得到测量结果，必要时会进行量子线路聚合/拆分等优化。

用户调用作业提交API后，量子作业会被Prefect组件调度，随后作业引擎会被Prefect组件以进程形式运行。

作业引擎与 Prefect Worker 的关系
-----------------------------------

作业引擎（``job_engine``）运行在 **Prefect Worker 进程** 中，其本身并不直接被 API 进程调用，而是以 Prefect **flow** 的形式注册为
deployment，由独立的Prefect Worker进程拉取并执行。二者是"被调度者"与"调度执行者"的关系：

- **作业引擎**：即 :func:`job_flow`，是一个被 ``@flow`` 装饰的 Prefect flow，负责加载驱动、
  解析、转译、运行驱动并返回测量结果，是真正的量子作业执行逻辑。
- **Prefect Worker**：由 :class:`ProcessWorker` 实现的常驻进程，负责从 Prefect Server 轮询
  其所归属工作池（work pool）中的 flow run，拉取到任务后在本地子进程中执行对应的 flow。

每个设备（device）在启动时会创建三类 Worker 进程，分别绑定到不同的工作池：

.. list-table:: Worker 类型与工作池
   :header-rows: 1
   :widths: 15 20 30 35

   * - Worker 类型
     - 工作池前缀
     - 执行的 flow
     - 职责
   * - job
     - ``device|``
     - :func:`job_flow`
     - 执行量子作业（解析/转译/驱动运行）
   * - monitor
     - ``monitor|``
     - :func:`device_monitor_flow`
     - 设备状态监控
   * - mgr
     - ``mgr|``
     - device_mgr_flow
     - 设备管理任务

部署与启动流程
^^^^^^^^^^^^^^

1. **生成 deployment 配置**：:meth:`generate_deployment_configs` 为每个设备生成
   deployment，将 :func:`job_flow` 关联到 ``device|{device_name}`` 工作池，
   入口命令为 ``python -m prefect.engine``。
2. **创建 deployment**：:meth:`create_deployments` 通过
   :meth:`flow.deploy` 在 Prefect Server 注册 deployment，并记录 ``deploy_id``。
3. **启动 Worker 进程**：:meth:`start_workers` 遍历所有设备，调用
   :meth:`_start_worker_process` 以 ``multiprocessing.Process`` 启动 job/monitor/mgr
   三类 Worker；每个 Worker 内部实例化 :class:`ProcessWorker` 并
   :meth:`worker.start` 进入轮询循环。

作业执行链路
^^^^^^^^^^^^^^

用户提交作业后的完整链路如下：

.. code-block:: text

   用户提交作业 (API)
     -> TaskScheduler.submit_job  # 限流与设备校验
        -> exec_task  # 按 backend 解析 deployment、按优先级选择 work queue
           -> run_flow_by_client  # 调用 create_flow_run_from_deployment
              创建 flow run 并投递到对应 work queue
                 |
 (flow run 进入 Prefect Server 的 work queue)
                 v
   Prefect Worker (ProcessWorker) 轮询到 flow run
     -> 在本地子进程中加载并执行 job_flow(job_info)
        -> init_driver / parse / transpile / run_driver
        -> 返回测量结果

工作队列与优先级
^^^^^^^^^^^^^^^^^

job Worker 不只监听单个队列，而是同时监听 ``MAX_JOB_PRIORITY``（默认 10）个优先级队列，
队列名格式为 ``{device_pool_name}_{priority}``。提交时 :meth:`exec_task` 根据作业优先级
选择对应 work queue，Prefect 按队列顺序消费，从而实现优先级调度。

Worker 生命周期
^^^^^^^^^^^^^^^^^

- Worker 进程以 daemon 方式启动，随 API Server 进程退出而终止。
- Worker 通过 proctitle ``[prefect] {worker_name}`` 标识自身，
  :meth:`list_workers` 据此解析进程状态。
- 当 Worker 因 Prefect/Redis 异常崩溃退出后，由
  :ref:`Worker Watchdog <worker-watchdog>` （见下文）自动检测并重启。

作业后端解析
--------------------------

作业提交时，``backend`` 与 ``flavor_id`` 互斥，二者必须指定其一：

- 指定 ``backend`` 时，直接使用该设备作为执行后端，此时不允许传入 ``extra_specs``。
- 未指定 ``backend`` 时触发自动调度（AutoScheduler）：必须提供 ``flavor_id``
  （可选搭配 ``extra_specs``）。AutoScheduler 通过 FlavorManager 获取 Flavor 的
  specs 并合并 ``extra_specs``，经 Filter 链过滤设备后解析出 ``backend``。

.. note::

   API 层仅接受 ``flavor_id``（UUID）；CLI 端 ``--flavor`` 可传入 flavor ID 或
   flavor 名称，名称在提交前解析为 ``flavor_id``。

作业引擎启动后，会加载用户作业提交API中的参数，然后根据作业中指定的设备后端(backend)所关联的驱动会被实例化，随后引擎层会调用驱动实例中的方法来和厂商量子真机进行交互，并获取测量结果。

作业引擎调用驱动和转译器
--------------------------
引擎层核心调用逻辑如下:

.. code-block:: text

   job_flow ->
      loop src_code_list  # 循环作业中的源代码列表(source_code)
      [
       init_driver()  # 初始化驱动
       parse()  # 源代码解析
        init_transpiler()  # 初始化转译器（含默认值填充）
        transpile()  # 进行转译
        results = run_driver()  # 运行驱动中的run函数
       return results

         run_code ->
             init_driver ->  # 初始化驱动
                 driver.validate_driver_configs(device_configs)  # 验证驱动配置
                 driver.set_configs(device_configs)  # 驱动中加载设备配置
                 driver.init_driver() ->  # 驱动初始化
                 driver.fetch_configs() ->  # 驱动动态获取真机配置信息
             init_transpiler ->  # 初始化转译器
                 # 从 driver.transpiler_options_schema 填充默认值
                 # 仅填充用户未指定且 schema 声明了 default 的 key
                 transpiler.update_transpiler_options()  # 应用转译器选项
             flow_parse ->  # 解析源代码
                 transpiler.parse() ->  # 调用转译器解析源代码
             flow_transpile ->  # 转译
                 transpiler.transpile() ->  # 调用转译器进行转译
             flow_run_driver ->  # 驱动运行
                 driver_run ->  # 驱动运行
                     driver.run() / driver.dry_run() ->  # 运行驱动中的run(真实运行)或者dry_run(模拟运行/空跑)
                     post_run(driver)  # 运行后处理（sleep/进度更新）
                     driver.set_progress_by_task(COMPLETE)  # 设置完成进度
         get_results  # 获取运行结果
      ]

转译器选项默认值填充
--------------------------

``init_transpiler`` 在实例化转译器后，会从驱动声明的
``transpiler_options_schema`` 中读取各选项的默认值，填充到用户
未指定的选项中，确保转译器始终获得完整参数。

填充逻辑如下：

1. 当 ``transpiler_options`` 为 ``None`` 时，初始化为空字典 ``{}``
2. 通过 ``Library.convert_schema`` 将驱动的 schema dict 转换为
   ``{Optional_marker: validator}`` 形式
3. 遍历转换后的 schema，对每个 ``Optional`` marker：

   - 通过 ``getattr(key, "schema", key)`` 获取选项名
   - 若选项名已存在于 ``transpiler_options`` 中，跳过（不覆盖）
   - 若该 marker 声明了 ``default``（``hasattr(key, "default")``），
     则将默认值填入 ``transpiler_options``
4. 最终调用 ``transpiler.update_transpiler_options()`` 应用选项

驱动运行后处理（post_run）
------------------------------

``driver_run`` 在调用 ``driver.run()`` / ``driver.dry_run()`` 后，
统一执行 ``post_run(driver)`` 进行运行后处理，然后设置
``TASK_STAGE_COMPLETE`` 进度。

``post_run`` 的主要逻辑：

- 读取 ``driver.driver_options`` 中的 ``sleep`` 值（调试用等待秒数）
- 若 ``sleep`` 为真值，从当前进度到 100 按比例递增设置进度，
  每秒推进一次，实现等待期间的进度可视化

此逻辑原先在 ``DriverDummy.run()`` 中实现，现统一提取到
``job_engine`` 层，所有驱动均可通过 ``driver_options`` 的
``sleep`` 键触发等待进度，无需各自实现。

.. _worker-watchdog:

Worker Watchdog 自动重启
------------------------------

系统内置 Worker Watchdog 看门狗机制，在定期健康检查中自动检测并重启已死亡的
Worker 进程，无需人工干预。

工作原理
^^^^^^^^^^

1. ``update_system_health_metrics()`` 在每次指标更新周期中并发执行 4 项组件
   健康检查（worker、prefect、fastapi、redis）
2. 当检测到 Prefect 服务健康但 Worker 不健康时，自动调用
   ``watchdog_restart_dead_workers()``
3. Watchdog 遍历所有状态为 ``offline`` 的 Worker，通过 Worker 名称解析出
   设备名称和 Worker 类型（job/monitor/mgr），调用
   ``_start_worker_process()`` 重启对应进程

触发条件
^^^^^^^^^^

- **三个核心组件必须在线**：FastAPI、Prefect、Redis 三个组件均健康时才触发
  Watchdog。当任一组件不可用时跳过，因为 Worker 重启需要 Prefect API 和 Redis
  均可用
- **至少有一个 Worker 不健康**：仅当 ``worker_healthy=False`` 时触发
- **执行超时**：Watchdog 执行有 30 秒超时保护，防止阻塞健康检查流程

典型场景
^^^^^^^^^^

当 Redis 服务断连时，Prefect Server 的 docket/events 功能依赖 Redis，
Redis 断连会导致 Prefect Server 异常，进而使 Worker 进程因心跳/查询失败而
崩溃退出。Redis 恢复后，Prefect Server 恢复正常，但 Worker 进程已死亡。
此时 Watchdog 会在下一次健康检查周期中自动检测到 Worker offline 并重启。

.. note::

   Watchdog 的执行频率取决于 ``PREFECT_WORKER_HEARTBEAT_SECONDS``
   （默认 30 秒）配置。若需手动立即重启，可使用
   ``qcos-cli restart-worker`` 命令。
