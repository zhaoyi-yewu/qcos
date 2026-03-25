设备管理引擎
=============

设备管理引擎（device manage engine）主要用来下发设备管理任务，如校准任务，设置设备选项等任务。

设备监控引擎调用驱动
---------------------

引擎层核心调用逻辑如下：

.. code-block:: python

   device_manager_flow ->
      init_driver()                                  # 初始化驱动
      call_device_method()                           # 调用设备驱动函数，下发设备管理命令

设备管理整体调用逻辑如下：
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
