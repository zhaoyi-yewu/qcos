设备分组（Device Group）
========================

设备分组（Device Group）用于将设备进行逻辑分类管理。一个设备可以属于一个分组，
通过 ``device_names`` 字段维护成员设备名称列表。设备分组可被Flavor的 ``extra_properties``
引用，用于调度时按分组过滤设备。

设备分组管理器
-----------------------------

DeviceGroupManager在服务启动时初始化，负责设备分组的CRUD操作和成员设备查找。

.. code-block:: python

   # init device group manager
   scheduler.init_device_group_manager()

数据模型
-------------------------

.. code-block:: python

   class DeviceGroup(BaseTable):
       """DeviceGroup table - logical grouping of devices."""

       __tablename__ = "device_groups"

       id = Column(GUID, primary_key=True, default=uuid.uuid4)
       project_id = Column(GUID, ForeignKey("projects.id"), nullable=False)
       name = Column(String(128), nullable=False, unique=True)
       description = Column(String(256))
       device_names = Column(JSON, nullable=True, default=None)
       is_public = Column(Boolean, default=True)

设计说明
~~~~~~~~~~~~~~~~~~~~~~~~~~

- 采用 ``device_names`` JSON字段存储成员设备名称列表，而非在Device表上添加外键。
  原因：Device是内存对象（从配置文件/驱动加载），不在DB中持久化，无法添加外键。
  通过 ``device_names`` 列表维护成员关系更灵活。
- ``project_id`` 外键关联projects表，支持项目级权限隔离。
- ``name`` 唯一约束，便于按名称查找。
- ``is_public`` 控制可见性，公开分组对所有项目可见。

与Flavor的集成
-----------------------------

设备分组可通过Flavor的 ``extra_properties`` 中的 ``qc:device_groups`` 字段引用。
调度时，``DeviceGroupFilter`` 会根据该字段查找分组成员设备列表，仅选择属于该分组的设备。

.. code-block:: python

   # Flavor配置示例
   {
     "name": "sc-flavor",
     "extra_properties": {
       "qc:device_groups": "superconducting-group"
     }
   }

DeviceGroupFilter调度过滤器
-----------------------------

``DeviceGroupFilter`` 是自动调度器的Filter之一，用于根据设备分组过滤候选设备。

.. code-block:: python

   class DeviceGroupFilter(BaseFilter):
       """Filter devices by device group membership."""

       def is_enabled(self, spec):
           """Enabled when flavor_specs contains 'qc:device_groups'."""
           group_ref = spec.flavor_specs.get("qc:device_groups")
           return group_ref is not None

       def _filter_one(self, obj, spec):
           """Check if device is in the referenced group."""
           group_ref = spec.flavor_specs.get("qc:device_groups")
           if not group_ref:
               return True
           device_names = (
               self._device_group_manager
               .get_device_names_by_group(group_ref)
           )
           return obj.name in device_names

调度流程
~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Flavor的 ``extra_properties`` 中指定 ``qc:device_groups``
2. AutoScheduler将extra_properties合并到RequestSpec的flavor_specs中
3. DeviceGroupFilter检查flavor_specs中是否有 ``qc:device_groups``
4. 如果有，通过DeviceGroupManager查找分组成员设备名称列表
5. 仅保留属于该分组的设备

权限控制
-------------------------

- 创建、更新、删除设备分组需要 ``admin`` 角色
- 查询设备分组所有角色可用
- 支持项目级别的可见性控制（``is_public`` 标志）

CLI命令
-------------------------

.. code-block:: shell

   # 创建设备分组
   qcos-cli create-device-group my-group --device dummy --device qutip_sim

   # 查询设备分组列表
   qcos-cli list-device-groups

   # 删除设备分组
   qcos-cli delete-device-group 5e4337a0-42d1-410b-827f-761ebd6df470 -y
