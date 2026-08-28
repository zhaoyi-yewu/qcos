设备管理引擎
=============

设备管理引擎（device manage engine）主要用来下发设备管理任务，如校准任务，设置设备选项等任务。

设备管理引擎与 Prefect Worker 的关系
--------------------------------------

设备管理引擎（即 :func:`device_mgr_flow`）本身并不直接被 API 进程调用，而是以
Prefect **flow** 的形式注册为 deployment，由独立的 **Prefect Worker 进程** 拉取并执行。
二者是"被调度者"与"调度执行者"的关系：

- **设备管理引擎**：即 :func:`device_mgr_flow`，是一个被 ``@flow`` 装饰的 Prefect flow，
  负责初始化驱动并调用驱动方法下发设备管理命令（如校准、设置选项等）。
- **Prefect Worker**：由 :class:`ProcessWorker` 实现的常驻进程，负责从 Prefect Server
  轮询其所归属工作池中的 flow run，拉取到任务后在本地子进程中执行对应的 flow。

每个设备在启动时会创建一个 **mgr Worker** 进程，绑定到 ``mgr|{device_name}`` 工作池
（工作池前缀为 ``mgr|``）。该 Worker 仅在设备驱动的 ``enable_device_mgr`` 为真时启动，
监听 ``default`` 队列。

部署与启动流程：

1. :meth:`generate_deployment_configs` 为设备生成 deployment，将 :func:`device_mgr_flow`
   关联到 ``mgr|{device_name}`` 工作池，入口命令为 ``python -m prefect.engine``。
2. :meth:`create_deployments` 通过 :meth:`flow.deploy` 在 Prefect Server 注册
   deployment 并记录 ``deploy_id``。
3. :meth:`start_workers` 调用 :meth:`_start_worker_process` 以
   ``multiprocessing.Process`` 启动 mgr Worker，Worker 内部实例化
   :class:`ProcessWorker` 并 :meth:`worker.start` 进入轮询循环。

设备监控引擎调用驱动
---------------------

引擎层核心调用逻辑如下：

.. code-block:: python

   device_manager_flow ->
      init_driver()                                  # 初始化驱动
      call_device_method()                           # 调用设备驱动函数，下发设备管理命令

设备管理整体调用逻辑
--------------------------

.. code-block:: python

   北向接口 ->
     scheduler.add_manage_job() ->                    # 添加管理任务
       get_device()                                   # 获取相应设备
       get_driver()                                   # 获取相应驱动
       task_manager.get_deployment()                  # 获取部署信息
       device_mgr_info                                # 构造device_mgr_info
       policy_handler.exec_manage_task() ->           # 执行任务
          run_manage_task_flow_by_client() ->         # client 执行任务
             create_flow_run_from_deployment() ->     # 创建flow
               device_manager_flow()                  # 执行flow
