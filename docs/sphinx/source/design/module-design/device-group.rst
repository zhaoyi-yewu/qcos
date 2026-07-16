设备分组（Device Group）
========================

设备分组（Device Group）用于将设备进行逻辑分类管理。一个设备可以属于一个分组，
通过 ``device_names`` 字段维护成员设备名称列表。设备分组可被Flavor通过独立的
映射表（ ``flavor_device_group_mappings`` ）关联，用于调度时按分组过滤设备。

设备分组管理器
-----------------------------

DeviceGroupManager在服务启动时初始化，负责设备分组的CRUD操作、
成员设备查找和默认设备分组的种子化。初始化在FlavorManager之前执行
（Flavor的默认数据需要引用默认设备分组）。

.. code-block:: python

   # server.py 中服务启动时的初始化顺序
   scheduler.set_db_engine(db_engine)
   scheduler.init_device_group_manager()
   scheduler.init_flavor_manager()
   scheduler.init_auto_scheduler()
   # DeviceGroupManager在初始化时会自动创建默认的设备分组（幂等）

默认预设设备分组
~~~~~~~~~~~~~~~~~~~~~~~~~~

系统内置四个默认设备分组：

- ``qc.all``: 所有量子计算机（真机与模拟器， ``device_names`` 为 ``["_all"]`` ）
- ``qc.real``: 所有量子真机（ ``device_names`` 为 ``None``，由驱动类型动态判定）
- ``qc.sim``: 所有量子模拟器（ ``device_names`` 为 ``["qutip_sim"]`` ）
- ``qc.qubo``: 所有QUBO求解器（ ``device_names`` 为 ``None`` ）

数据模型
-------------------------

.. code-block:: python

   class DeviceGroup(BaseTable):
       """DeviceGroup table - logical grouping of devices."""

       __tablename__ = "device_groups"

       id = Column(GUID, primary_key=True, default=uuid.uuid4)
       project_id = Column(
           GUID,
           ForeignKey("projects.id"),
           nullable=False,
           default=uuid.UUID(Constant.ADMIN_PROJECT_ID),
       )
       name = Column(String(128), nullable=False, unique=True)
       description = Column(String(256))
       device_names = Column(JSON, nullable=True, default=None)
       is_public = Column(Boolean, default=True)

设计说明
~~~~~~~~~~~~~~~~~~~~~~~~~~

- 采用 ``device_names`` JSON字段存储成员设备名称列表，而非在Device表上添加外键。
  原因：Device是内存对象（从配置文件/驱动加载），不在DB中持久化，无法添加外键。
  通过 ``device_names`` 列表维护成员关系更灵活。
- ``device_names`` 支持特殊值 ``_all``，表示包含所有设备。
- ``device_names`` 为 ``None`` 时，该分组不通过显式列表匹配，可由其他机制
  （如驱动类型）动态判定成员。
- ``project_id`` 外键关联projects表，默认为管理项目，支持项目级权限隔离。
- ``name`` 唯一约束，便于按名称查找。
- ``is_public`` 控制可见性，公开分组对所有项目可见。

与Flavor的集成
-----------------------------

设备分组通过独立的映射表 ``flavor_device_group_mappings`` 与Flavor建立多对多关系
（参见 :doc:`flavor` ）。Flavor创建/更新时通过 ``device_groups`` 参数指定设备分组
UUID列表，FlavorManager校验分组存在性并维护映射记录。

调度时，FlavorManager的 ``get_flavor_specs`` 会将映射表中的第一个设备分组UUID
注入为 ``qc:device_groups``，供 ``DeviceGroupFilter`` 使用。

.. code-block:: python

   # Flavor通过映射表关联设备分组（非直接字段）
   # flavor_device_group_mappings:
   #   flavor_id  ->  device_group_id

DeviceGroupFilter调度过滤器
-----------------------------

``DeviceGroupFilter`` 是自动调度器的Filter之一，用于根据设备分组过滤候选设备。
``device_group_manager`` 由AutoScheduler在初始化时注入。

.. code-block:: python

   DEVICE_GROUP_SPEC_KEY = "qc:device_groups"

   class DeviceGroupFilter(BaseFilter):
       """Filter devices by device group membership."""

       def __init__(self, device_group_manager=None):
           self._device_group_manager = device_group_manager

       def is_enabled(self, spec: RequestSpec) -> bool:
           """Enabled when flavor_specs contains 'qc:device_groups'."""
           group_ref = spec.flavor_specs.get(DEVICE_GROUP_SPEC_KEY)
           return group_ref is not None

       def _filter_one(self, obj: DeviceState, spec: RequestSpec) -> bool:
           """Check if device is in the referenced group."""
           group_ref = spec.flavor_specs.get(DEVICE_GROUP_SPEC_KEY)
           if not group_ref:
               return True
           if self._device_group_manager is None:
               return True
           device_names = (
               self._device_group_manager.get_device_names_by_group(group_ref)
           )
           if not device_names:
               return False
           return obj.name in device_names

调度流程
~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Flavor通过映射表关联设备分组
2. AutoScheduler调用 ``get_flavor_specs`` 构建 ``flavor_specs``，
   其中自动注入 ``qc:device_groups`` (第一个关联分组的UUID)
3. DeviceGroupFilter检查 ``flavor_specs`` 中是否有 ``qc:device_groups``
4. 如果有，通过DeviceGroupManager查找分组成员设备名称列表
5. 仅保留属于该分组的设备

权限控制
-------------------------

- 创建、更新、删除设备分组需要 ``admin`` 角色
- 查询设备分组所有角色可用
- 支持项目级别的可见性控制（ ``is_public`` 标志）

CLI命令
-------------------------

.. code-block:: shell

   # 创建设备分组（至少指定一个 --device）
   qcos-cli create-device-group my-group --device dummy --device qutip_sim

   # 更新设备分组（可空字段可用 --unset-{key} 清空）
   qcos-cli update-device-group my-group1 --description "new simulator" --device dummy qutip_sim
   qcos-cli update-device-group my-group1 --unset-description
   qcos-cli update-device-group my-group1 --unset-device

   # 查询设备分组列表
   qcos-cli list-device-groups

   # 删除设备分组
   qcos-cli delete-device-groups my-group1 -y
