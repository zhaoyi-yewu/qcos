设备分组接口
================

设备分组（Device Group）接口用于管理设备的逻辑分组，支持通过API和CLI创建、查询、更新和删除设备分组。
设备分组可以被Flavor通过device_groups字段关联，用于调度时按分组过滤设备。

.. list-table:: 设备分组接口规范
   :widths: 20 20 30 30
   :header-rows: 1
   :align: left
   :class: longtable

   * - 用途
     - 方法
     - 请求参数
     - 返回值

   * - **创建设备分组**
     - **create_device_group**

       URI: /v1/job/create_device_group
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "id": 1,
               "method": "create_device_group",
               "params": {
                 "body": {
                   "name": "superconducting-group",
                   "description": "超导量子计算机分组",
                   "device_names": ["uqc_matrix2", "dummy"],
                   "is_public": true
                 }
               }
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "result": {
                 "id": "5e4337a0-42d1-410b-827f-761ebd6df470",
                 "project_id": "00000000-0000-4000-8000-000000000001",
                 "name": "superconducting-group",
                 "description": "超导量子计算机分组",
                 "device_names": ["uqc_matrix2", "dummy"],
                 "is_public": true,
                 "created_at": "2026-07-09T10:00:00",
                 "updated_at": "2026-07-09T10:00:00"
               },
               "error": null,
               "id": 1
             }

   * - **更新设备分组**
     - **update_device_group**

       URI: /v1/job/update_device_group
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "id": 1,
               "method": "update_device_group",
               "params": {
                 "body": {
                   "group_id": "5e4337a0-42d1-410b-827f-761ebd6df470",
                   "description": "更新后的描述",
                   "device_names": ["uqc_matrix2", "dummy", "qutip_sim"]
                 }
               }
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "result": {
                 "id": "5e4337a0-42d1-410b-827f-761ebd6df470",
                 "name": "superconducting-group",
                 "description": "更新后的描述",
                 "device_names": ["uqc_matrix2", "dummy", "qutip_sim"],
                 "is_public": true
               },
               "error": null,
               "id": 1
             }

   * - **查询设备分组详情**
     - **get_device_group**

       URI: /v1/job/get_device_group
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "id": 1,
               "method": "get_device_group",
               "params": {
                 "body": {
                   "group_id": "5e4337a0-42d1-410b-827f-761ebd6df470"
                 }
               }
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "result": {
                 "id": "5e4337a0-42d1-410b-827f-761ebd6df470",
                 "project_id": "00000000-0000-4000-8000-000000000001",
                 "name": "superconducting-group",
                 "description": "超导量子计算机分组",
                 "device_names": ["uqc_matrix2", "dummy"],
                 "is_public": true
               },
               "error": null,
               "id": 1
             }

   * - **查询设备分组列表**
     - **get_device_groups**

       URI: /v1/job/get_device_groups
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "id": 1,
               "method": "get_device_groups",
               "params": {
                 "body": {
                   "filters": {
                     "group_name": "superconducting-group",
                     "group_ids": [
                       "5e4337a0-42d1-410b-827f-761ebd6df470"
                     ]
                   }
                 }
               }
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "result": [
                 {
                   "id": "5e4337a0-42d1-410b-827f-761ebd6df470",
                   "name": "superconducting-group",
                   "description": "超导量子计算机分组",
                   "device_names": ["uqc_matrix2", "dummy"],
                   "is_public": true
                 }
               ],
               "error": null,
               "id": 1
             }

   * - **批量删除设备分组**
     - **delete_device_groups**

       URI: /v1/job/delete_device_groups
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "id": 1,
               "method": "delete_device_groups",
               "params": {
                 "body": {
                   "group_ids": [
                     "5e4337a0-42d1-410b-827f-761ebd6df470",
                     "00000000-0000-0000-0000-000000000002"
                   ]
                 }
               }
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "result": {
                 "results": [
                   {
                     "group_id": "5e4337a0-42d1-410b-827f-761ebd6df470",
                     "success": true,
                     "error": null
                   },
                   {
                     "group_id": "00000000-0000-0000-0000-000000000002",
                     "success": false,
                     "error": "Device group is referenced by flavors"
                   }
                 ]
               },
               "error": null,
               "id": 1
             }

与Flavor的集成
---------------

设备分组可通过Flavor的extra_properties中的 ``qc:device_groups`` 字段引用。
调度时，``DeviceGroupFilter`` 会根据该字段查找分组成员设备列表，仅选择属于该分组的设备。

示例Flavor配置::

   {
     "name": "sc-flavor",
     "extra_properties": {
       "qc:device_groups": "superconducting-group"
     }
   }

权限说明
---------

- **create_device_group**: 需要 admin 角色
- **update_device_group**: 需要 admin 角色
- **get_device_group**: 所有角色可用
- **get_device_groups**: 所有角色可用
- **delete_device_groups**: 需要 admin 角色
