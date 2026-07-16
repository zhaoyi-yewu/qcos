资源规格（Flavor）
==================

资源规格（Flavor）是预设的调度策略，用于定义量子作业自动调度时的设备过滤条件。
Flavor可以设置量子比特数范围、门保真度等约束，并通过独立的映射表关联设备分组，
还可通过extra_properties携带额外的设备过滤条件。

Flavor管理器
-------------------------

FlavorManager在服务启动时初始化，负责Flavor的CRUD操作和默认Flavor的种子化。
初始化在DeviceGroupManager之后执行（Flavor的默认数据需要引用默认设备分组）。

.. code-block:: python

   # server.py 中服务启动时的初始化顺序
   scheduler.set_db_engine(db_engine)
   scheduler.init_device_group_manager()
   scheduler.init_flavor_manager()
   scheduler.init_auto_scheduler()
   # FlavorManager在初始化时会自动创建默认的预设Flavor（幂等）

默认预设Flavor
~~~~~~~~~~~~~~~~~~~~~~~~~~

系统内置五个默认Flavor：

- ``g1.all``: 所有量子计算机（真机与模拟器）
- ``r1.all``: 所有量子真机
- ``rh1.all``: 所有高保真度（≥0.99）量子真机
- ``s1.all``: 所有量子模拟器
- ``q1.all``: 所有QUBO求解器

每个默认Flavor通过 ``device_groups`` 字段关联一个默认设备分组
（如 ``g1.all`` 关联 ``qc.all``，``s1.all`` 关联 ``qc.sim``）。

数据模型
-------------------------

Flavor表本身不存储设备分组映射，而是通过独立的映射表
``flavor_device_group_mappings`` 维护多对多关系。

.. code-block:: python

   class Flavor(BaseTable):
       """Flavor table - preset scheduling policy specs."""

       __tablename__ = "flavors"

       id = Column(GUID, primary_key=True, default=uuid.uuid4)
       project_id = Column(
           GUID,
           ForeignKey("projects.id"),
           nullable=False,
           default=uuid.UUID(Constant.ADMIN_PROJECT_ID),
       )
       name = Column(String(128), nullable=False, unique=True)
       description = Column(String(256))
       is_public = Column(Boolean, default=True)
       min_qubits = Column(Integer, nullable=True)
       max_qubits = Column(Integer, nullable=True)
       gate_fidelity_1q_min = Column(Float, nullable=True)
       gate_fidelity_2q_min = Column(Float, nullable=True)
       extra_properties = Column(JSON, nullable=True, default=None)

FlavorDeviceGroup映射表
~~~~~~~~~~~~~~~~~~~~~~~~~~

Flavor与DeviceGroup之间为多对多关系，通过 ``FlavorDeviceGroup`` 映射表维护。
每个记录关联一个Flavor和一个DeviceGroup，并在 ``(flavor_id, device_group_id)``
上建立唯一约束。该表为纯映射表，不含时间戳字段。

.. code-block:: python

   class FlavorDeviceGroup(Base):
       """FlavorDeviceGroup mapping table."""

       __tablename__ = "flavor_device_group_mappings"

       id = Column(GUID, primary_key=True, default=uuid.uuid4)
       flavor_id = Column(GUID, ForeignKey("flavors.id"), nullable=False)
       device_group_id = Column(
           GUID, ForeignKey("device_groups.id"), nullable=False
       )

       __table_args__ = (
           UniqueConstraint(
               "flavor_id",
               "device_group_id",
               name="uq_flavor_device_group",
           ),
       )

创建/更新Flavor时， ``device_groups`` 参数接收设备分组UUID列表，
FlavorManager负责校验分组存在性并维护映射表记录；查询时通过
``get_flavor_device_groups()`` 解析映射关系并返回UUID列表。

extra_properties字段
~~~~~~~~~~~~~~~~~~~~~~~~~~

Flavor的extra_properties字段支持以下键值（键名需为 ``namespace:name`` 格式），
由FlavorManager校验，用于调度时过滤设备：

- ``qc:devices``: 显式允许的设备名称（逗号分隔，如 ``"dummy,qutip_sim"``）
- ``qc:exclude_devices``: 排除的设备名称（逗号分隔，如 ``"dummy"``）
- ``qc:device_availability``: 设备可用性要求（如 ``0.99``）
- ``qc:code_types``: 支持的代码类型（如 ``"qasm2,qasm3"``）
- ``qc:tech_types``: 量子技术路线类型（如 ``"superconducting,ion_trap"``）

注意： ``qc:device_groups`` 不属于用户可设置的extra_properties字段，
它由FlavorManager在构建调度specs时根据映射表自动注入（见下文）。

调度集成
-------------------------

Flavor与自动调度器（AutoScheduler）集成，调度流程如下：

1. 用户提交作业时指定 ``flavor_name`` 或 ``flavor_id``
2. AutoScheduler通过FlavorManager获取Flavor的specs（ ``get_flavor_specs`` ）
3. 将specs合并到RequestSpec的 ``flavor_specs`` 中
4. 调度Filter链根据specs过滤设备

``get_flavor_specs`` 在构建specs时，会将映射表中的第一个设备分组UUID
作为 ``qc:device_groups`` 注入到specs中，供 ``DeviceGroupFilter`` 使用：

.. code-block:: python

   # AutoScheduler中使用Flavor
   flavor_specs = flavor_manager.get_flavor_specs(flavor_id)
   spec = RequestSpec(
       job_id=job_id,
       flavor_id=flavor_id,
       flavor_specs=flavor_specs,
       extra_specs=extra_specs or {},
   )

.. code-block:: python

   # get_flavor_specs 内部注入设备分组引用
   specs = {}
   if flavor.min_qubits is not None:
       specs["min_qubits"] = flavor.min_qubits
   # ... max_qubits, gate_fidelity_* ...
   if flavor.extra_properties:
       specs.update(flavor.extra_properties)
   # inject device group reference from mapping table
   group_ids = self.get_flavor_device_groups(flavor_id)
   if group_ids:
       specs[DEVICE_GROUP_SPEC_KEY] = group_ids[0]

权限控制
-------------------------

- 创建、更新、删除Flavor需要 ``admin`` 角色
- 查询Flavor所有角色可用
- 支持项目级别的可见性控制（ ``is_public`` 标志）

CLI命令
-------------------------

.. code-block:: shell

   # 创建Flavor（需指定至少一个设备分组）
   qcos-cli create-flavor my-flavor --min-qubits 2 --max-qubits 32 \
       --device-groups <device-group-uuid>

   # 更新Flavor（可空字段可用 --unset-{key} 清空）
   qcos-cli update-flavor my-flavor --max-qubits 64
   qcos-cli update-flavor my-flavor --unset-description --unset-max-qubits

   # 查询Flavor列表
   qcos-cli list-flavors

   # 删除Flavor
   qcos-cli delete-flavors my-flavor -y
