设备监控引擎
=============

设备监控引擎（device monitor engine）主要用来执行周期性任务获取设备的运行信息，包括状态等。

操作系统启动后，每个设备都会自动生成一个 Prefect 作业，以进程形式运行。

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
