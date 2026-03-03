作业引擎/量子引擎
====================

作业引擎/量子引擎层(job engine)是量子操作系统的核心，主要用来解析、转译、优化、调用测控系统或真机执行量子程序、得到测量结果，必要时会进行量子线路聚合/拆分等优化。

用户调用作业提交API后，量子作业会被Prefect组件调度，随后作业引擎会被Prefect组件以进程形式运行。

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
        init_transpiler()  # 初始化转译器
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
             flow_parse ->  # 解析源代码
                 transpiler.parse() ->  # 调用转译器解析源代码
             flow_transpile ->  # 转译
                 transpiler.transpile() ->  # 调用转译器进行转译
             flow_run_driver ->  # 驱动运行
                 driver_run ->  # 驱动运行
                     driver.run() / driver.dry_run() ->  # 运行驱动中的run(真实运行)或者dry_run(模拟运行/空跑)
         get_results  # 获取运行结果
      ]
