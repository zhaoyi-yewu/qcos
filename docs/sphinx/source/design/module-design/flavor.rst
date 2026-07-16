资源规格（Flavor）
==================

资源规格（Flavor）是预设的调度策略，用于定义量子作业自动调度时的设备过滤条件。
Flavor可以设置量子比特数范围、技术类型、门保真度等约束，并通过extra_properties引用设备分组。

Flavor管理器
-------------------------

FlavorManager在服务启动时初始化，负责Flavor的CRUD操作和默认Flavor的种子化。

.. code-block:: python

   # init flavor manager
   scheduler.init_flavor_manager()
   # FlavorManager在初始化时会自动创建默认的预设Flavor

默认预设Flavor
~~~~~~~~~~~~~~~~~~~~~~~~~~

系统内置三个默认Flavor：

- ``g1.all``: 所有通用量子计算机
- ``hf1.all``: 所有高保真度（≥0.99）量子计算机
- ``s1.all``: 所有量子模拟器

数据模型
-------------------------

.. code-block:: python

   class Flavor(BaseTable):
       """Flavor table - preset scheduling policy specs."""

       __tablename__ = "flavors"

       id = Column(GUID, primary_key=True, default=uuid.uuid4)
       project_id = Column(GUID, ForeignKey("projects.id"), nullable=False)
       name = Column(String(128), nullable=False, unique=True)
       description = Column(String(256))
       is_public = Column(Boolean, default=True)
       min_qubits = Column(Integer, nullable=True)
       max_qubits = Column(Integer, nullable=True)
       gate_fidelity_1q_min = Column(Float, nullable=True)
       gate_fidelity_2q_min = Column(Float, nullable=True)
       extra_properties = Column(JSON, nullable=True)

extra_properties字段
~~~~~~~~~~~~~~~~~~~~~~~~~~

Flavor的extra_properties字段支持以下键值，用于调度时过滤设备：

- ``qc:device_groups``: 设备分组名称或UUID
- ``qc:allowed_devices``: 允许的设备名称列表
- ``qc:code_types``: 支持的代码类型
- ``qc:device_availability``: 设备可用性要求
- ``qc:allowed_device_groups``: 允许的设备分组列表

调度集成
-------------------------

Flavor与自动调度器（AutoScheduler）集成，调度流程如下：

1. 用户提交作业时指定 ``flavor_name`` 或 ``flavor_id``
2. AutoScheduler通过FlavorManager获取Flavor的specs
3. 将specs合并到RequestSpec中
4. 调度Filter链根据specs过滤设备

.. code-block:: python

   # AutoScheduler中使用Flavor
   flavor_specs = flavor_manager.get_flavor_specs(flavor_id)
   spec = RequestSpec(
       job_id=job_id,
       flavor_id=flavor_id,
       flavor_specs=flavor_specs,
       extra_specs=extra_specs or {},
   )

权限控制
-------------------------

- 创建、更新、删除Flavor需要 ``admin`` 角色
- 查询Flavor所有角色可用
- 支持项目级别的可见性控制（``is_public`` 标志）

CLI命令
-------------------------

.. code-block:: shell

   # 创建Flavor
   qcos-cli create-flavor my-flavor --min-qubits 2 --max-qubits 32

   # 查询Flavor列表
   qcos-cli list-flavors

   # 删除Flavor
   qcos-cli delete-flavor my-flavor -y
