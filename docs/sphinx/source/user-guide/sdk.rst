Python客户端
=========================

QCOS 提供 Python 客户端库: QCOS-Client（``wy_qcos_client.client.Client``）。
开发者可通过 Client 库在应用程序中直接调用QCOS API，实现量子作业提交、查询、取消、设备管理等操作。

.. contents:: 目录
   :local:
   :depth: 3

安装 QCOS Client
-------------------

.. code-block:: shell

    # 通过脚本编译出wheel包，再通过wheel包安装
    $ cd build-scripts/cli
    $ ./build-wheel.sh
    $ pip install ./
    $ pip install output/dist/wy_qcos_client-1.5.0-py3-none-any.whl

    # 或者，从本地源码直接安装
    $ cd build-scripts/cli
    $ pip install .

    # 或者，从PyPI上安装特定版本
    $ pip install wy-qcos-client


初始化客户端
----------------

.. code-block:: python

    import json
    from wy_qcos_client.client import Client

    # 方式1: 连接本地 QCOS 服务
    client = Client(
        api_server_ip="127.0.0.1",
        api_server_port=18400,
    )

    # 方式2: 连接远程 QCOS 服务（支持 SSL）
    client = Client(
        api_server_ip="remote.example.com",
        api_server_port=443,
        use_ssl=True,
        ssl_cafile="/path/to/ca.pem",
        timeout=120,
    )

用户登录
--------

所有操作前需要先登录获取 JWT Token（如果开启了用户认证，
默认关闭时不需要）：

.. code-block:: python

    # 登录
    status_code, reason, text, result = client.login(
        username="admin",
        password="P*ssword1",
    )
    if status_code != 200:
        raise Exception(f"Login failed: {reason}")

    # 登录后 Token 自动保存在 client 对象中
    # 后续所有 API 调用会自动携带 Token

设备管理
----------------

**查询设备列表：**

.. code-block:: python

    # 获取所有设备（简要信息）
    status_code, reason, text, result = client.get_devices()
    devices = json.loads(text)
    print(devices)

    # 获取所有设备（详细信息，含校准数据等）
    status_code, reason, text, result = client.get_devices(details=True)
    devices = json.loads(text)
    print(devices)

**查询单个设备：**

.. code-block:: python

    status_code, reason, text, result = client.get_device(
        "dummy", details=True
    )
    device_info = json.loads(text)
    print(device_info)

**设置设备属性：**

.. code-block:: python

    # 设置设备状态为 online（手动覆盖）
    status_code, reason, text, result = client.set_device(
        "dummy", state="online"
    )

    # 设置设备状态为 offline
    status_code, reason, text, result = client.set_device(
        "dummy", state="offline"
    )

    # 恢复为自动状态（使用 monitor 上报的内存状态）
    status_code, reason, text, result = client.set_device(
        "dummy", state="auto"
    )

    # 组合设置：状态 + 启用 + 最大比特数
    status_code, reason, text, result = client.set_device(
        "dummy",
        state="online",
        enable=True,
        max_qubits="auto",
    )

量子作业管理
----------------

**提交作业：**

.. code-block:: python

    # 读取 QASM 源代码
    with open("./samples/qasm/2.0/simple-qasm.qasm", "r") as f:
        source_code = f.read()

    # 提交作业到指定后端设备
    status_code, reason, text, result = client.submit_job(
        [source_code],
        code_type="qasm",
        job_name="my_quantum_job",
        job_type="sampling",
        job_priority=5,
        description="test quantum job",
        shots=1024,
        backend="dummy",
        transpiler="cmss",
        dry_run=False,
    )
    result_data = json.loads(text)
    job_id = result_data["result"]["job_id"]

    # 自动调度（不指定 backend，由系统选择设备）
    status_code, reason, text, result = client.submit_job(
        [source_code],
        code_type="qasm",
        job_name="auto_scheduled_job",
        job_type="sampling",
        shots=1024,
        flavor_id="some-flavor-uuid",  # 可选，使用 Flavor 预设策略
    )

**查询作业状态：**

.. code-block:: python

    status_code, reason, text, result = client.get_job_status(job_id)
    result_data = json.loads(text)
    job_status = result_data["result"]["job_status"]
    # 状态值: QUEUED / RUNNING / COMPLETED / FAILED / CANCELLED

**查询作业结果：**

.. code-block:: python

    status_code, reason, text, result = client.get_job_results(job_id)
    result_data = json.loads(text)
    job_results = result_data["result"]
    # results 包含采样结果、metadata、profiling 等信息

**查询作业列表：**

.. code-block:: python

    # 查询所有作业
    status_code, reason, text, result = client.get_jobs()

    # 按条件过滤
    status_code, reason, text, result = client.get_jobs(
        filters={"job_status": "RUNNING"}
    )

**取消作业：**

.. code-block:: python

    status_code, reason, text, result = client.cancel_jobs([job_id])

**删除作业：**

.. code-block:: python

    # 普通删除（作业必须已完成或取消）
    status_code, reason, text, result = client.delete_jobs([job_id])

    # 强制删除（无论作业状态）
    status_code, reason, text, result = client.delete_jobs(
        [job_id], force=True
    )

完整示例：提交并等待作业完成
-------------------------------

.. code-block:: python

    import json
    import time
    from wy_qcos_client.client import Client

    # 1. 创建客户端和QCOS操作系统连接
    client = Client(
        api_server_ip="127.0.0.1",
        api_server_port=18400,
    )

    # 2. 查询可用设备
    status_code, reason, text, result = client.get_devices()
    devices = json.loads(text)
    print("Available devices:", list(devices.keys()))

    # 3. 读取 QASM 并提交作业
    with open("./samples/qasm/2.0/simple-qasm.qasm", "r") as f:
        source_code = f.read()

    status_code, reason, text, result = client.submit_job(
        [source_code],
        code_type="qasm",
        job_name="example_job",
        job_type="sampling",
        shots=1024,
        backend="dummy",
    )
    if status_code != 200:
        raise Exception(f"Submit failed: {text}")

    result_data = json.loads(text)
    job_id = result_data["result"]["job_id"]
    print(f"Job submitted: {job_id}")

    # 4. 轮询作业状态
    while True:
        status_code, reason, text, result = client.get_job_status(job_id)
        result_data = json.loads(text)
        job_status = result_data["result"]["job_status"]
        print(f"Job status: {job_status}")

        if job_status in ("COMPLETED", "FAILED", "CANCELLED"):
            break
        time.sleep(5)

    # 5. 获取作业结果
    if job_status == "COMPLETED":
        status_code, reason, text, result = client.get_job_results(job_id)
        result_data = json.loads(text)
        print("Job results (details):", result_data["result"])
        print("Job results:", result_data["result"]["results"][0]["results"])
    else:
        print(f"Job ended with status: {job_status}")

    # 6. 清理作业
    client.delete_jobs([job_id])

错误处理
----------------

所有 Client 方法返回 ``(status_code, reason, text, result)`` 四元组：

.. code-block:: python

    status_code, reason, text, result = client.submit_job(...)

    if status_code != 200:
        error_data = json.loads(text)
        if "error" in error_data:
            error_msg = error_data["error"]["message"]
            error_details = error_data["error"].get("data", {}).get("details", "")
            print(f"Error: {error_msg} - {error_details}")

常用 API 速查
----------------

====================================  ====================
方法                                  说明
====================================  ====================
``client.login(user, password)``      用户登录
``client.get_devices(details)``       获取设备列表
``client.get_device(name)``           获取设备信息
``client.set_device(name, ...)``      设置设备属性
``client.submit_job(code, ...)``      提交量子作业
``client.get_job_status(id)``         查询作业状态
``client.get_job_results(id)``        获取作业结果
``client.get_jobs(filters)``          查询作业列表
``client.cancel_jobs(ids)``           取消作业
``client.delete_jobs(ids)``           删除作业
``client.get_job_stats()``            获取作业统计
====================================  ====================

完整 QCOS Client API 文档请参考：https://qcos.readthedocs.io/zh-cn/latest/api/wy_qcos_client.html
