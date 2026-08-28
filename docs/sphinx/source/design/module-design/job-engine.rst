作业引擎/量子引擎
====================

作业引擎/量子引擎层(job engine)是量子操作系统的核心，主要用来解析、转译、优化、调用测控系统或真机执行量子程序、得到测量结果，必要时会进行量子线路聚合/拆分等优化。

用户调用作业提交API后，量子作业会被Prefect组件调度，随后作业引擎会被Prefect组件以进程形式运行。

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
