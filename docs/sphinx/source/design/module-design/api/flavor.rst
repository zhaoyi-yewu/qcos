资源规格接口
================

资源规格（Flavor）接口用于管理预设调度策略，支持通过API和CLI创建、查询、更新和删除Flavor。
Flavor可以定义量子比特数范围、技术类型、门保真度等调度约束，并通过device_groups字段关联设备分组。

.. list-table:: 资源规格接口规范
   :widths: 20 20 30 30
   :header-rows: 1
   :align: left
   :class: longtable

   * - 用途
     - 方法
     - 请求参数
     - 返回值

   * - **创建资源规格**
     - **create_flavor**

       URI: /v1/job/create_flavor
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "id": 1,
               "method": "create_flavor",
               "params": {
                 "body": {
                   "name": "high-fidelity-group",
                   "description": "高保真度设备规格",
                   "is_public": true,
                   "min_qubits": 2,
                   "max_qubits": 32,
                   "gate_fidelity_1q_min": 0.99,
                   "gate_fidelity_2q_min": 0.99,
                   "device_groups": [
                     "5e4337a0-42d1-410b-827f-761ebd6df470"
                   ]
                 }
               }
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "result": {
                 "id": "4d12c756-7e2d-468e-b689-178fc660bd7b",
                 "project_id": "00000000-0000-4000-8000-000000000001",
                 "name": "high-fidelity-group",
                 "description": "高保真度设备规格",
                 "is_public": true,
                 "min_qubits": 2,
                 "max_qubits": 32,
                 "gate_fidelity_1q_min": 0.99,
                 "gate_fidelity_2q_min": 0.99,
                 "device_groups": [
                   "5e4337a0-42d1-410b-827f-761ebd6df470"
                 ],
                 "extra_properties": null,
                 "created_at": "2026-07-09T10:00:00",
                 "updated_at": "2026-07-09T10:00:00"
               },
               "error": null,
               "id": 1
             }

   * - **更新资源规格**
     - **update_flavor**

       URI: /v1/job/update_flavor
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "id": 1,
               "method": "update_flavor",
               "params": {
                 "body": {
                   "flavor_id": "4d12c756-7e2d-468e-b689-178fc660bd7b",
                   "description": "更新后的描述",
                   "max_qubits": 64,
                   "device_groups": [
                     "5e4337a0-42d1-410b-827f-761ebd6df470"
                   ]
                 }
               }
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "result": {
                 "id": "4d12c756-7e2d-468e-b689-178fc660bd7b",
                 "name": "high-fidelity-group",
                 "description": "更新后的描述",
                 "max_qubits": 64,
                 "device_groups": [
                   "5e4337a0-42d1-410b-827f-761ebd6df470"
                 ],
                 "extra_properties": null
               },
               "error": null,
               "id": 1
             }

   * - **查询资源规格详情**
     - **get_flavor**

       URI: /v1/job/get_flavor
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "id": 1,
               "method": "get_flavor",
               "params": {
                 "body": {
                   "flavor_id": "4d12c756-7e2d-468e-b689-178fc660bd7b"
                 }
               }
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "result": {
                 "id": "4d12c756-7e2d-468e-b689-178fc660bd7b",
                 "project_id": "00000000-0000-4000-8000-000000000001",
                 "name": "high-fidelity-group",
                 "description": "高保真度设备规格",
                 "is_public": true,
                 "min_qubits": 2,
                 "max_qubits": 32,
                 "device_groups": [
                   "5e4337a0-42d1-410b-827f-761ebd6df470"
                 ],
                 "extra_properties": null
               },
               "error": null,
               "id": 1
             }

   * - **查询资源规格列表**
     - **get_flavors**

       URI: /v1/job/get_flavors
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "id": 1,
               "method": "get_flavors",
               "params": {
                 "body": {
                   "filters": {
                     "flavor_name": "g1.all",
                     "flavor_ids": [
                       "4d12c756-7e2d-468e-b689-178fc660bd7b"
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
                   "id": "00000000-0000-0000-0000-000000000001",
                   "name": "g1.all",
                   "description": "all quantum computers with general purpose",
                   "is_public": true,
                   "min_qubits": 1,
                   "device_groups": [
                     "5e4337a0-42d1-410b-827f-761ebd6df470"
                   ],
                   "extra_properties": null
                 }
               ],
               "error": null,
               "id": 1
             }

   * - **批量删除资源规格**
     - **delete_flavors**

       URI: /v1/job/delete_flavors
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "jsonrpc": "2.0",
               "id": 1,
               "method": "delete_flavors",
               "params": {
                 "body": {
                   "flavor_ids": [
                     "4d12c756-7e2d-468e-b689-178fc660bd7b",
                     "00000000-0000-0000-0000-000000000001"
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
                     "flavor_id": "4d12c756-7e2d-468e-b689-178fc660bd7b",
                     "success": true,
                     "error": null
                   },
                   {
                     "flavor_id": "00000000-0000-0000-0000-000000000001",
                     "success": false,
                     "error": "Flavor not found"
                   }
                 ]
               },
               "error": null,
               "id": 1
             }

更新字段语义说明
-----------------

update_flavor 接口支持以下字段更新语义：

- **不更新字段**：请求中不传该字段，保持原值不变

- **取消设置字段（unset）**：将字段值显式设为 ``null``，取消设置该字段。
  适用于 ``description``、``min_qubits``、``max_qubits``、
  ``gate_fidelity_1q_min``、``gate_fidelity_2q_min``、
  ``extra_properties``、``device_groups``

- ``device_groups`` 设为 ``null`` 时取消设置所有设备分组映射

- ``extra_properties`` 设为 ``null`` 时取消设置所有额外属性；设为非空
  dict 时与已有属性合并

extra_properties 支持的字段
-------------------------------

Flavor的extra_properties字段支持以下键值，用于调度时过滤设备：

.. list-table:: extra_properties 支持字段
   :widths: 30 40 30
   :header-rows: 1
   :align: left

   * - 字段名
     - 说明
     - 示例值

   * - ``qc:devices``
     - 允许的设备名称列表（逗号分隔）
     - ``"dummy,qutip_sim"``

   * - ``qc:exclude_devices``
     - 排除的设备名称列表（逗号分隔）
     - ``"dummy"``

   * - ``qc:device_availability`` 【暂不支持】
     - 设备可用性要求
     - ``0.99``

   * - ``qc:code_types``
     - 支持的代码类型
     - ``"qasm2,qasm3"``

   * - ``qc:tech_types``
     - 量子技术路线类型
     - ``"superconducting,ion_trap"``

权限说明
---------

- **create_flavor**: 需要 admin 角色
- **update_flavor**: 需要 admin 角色
- **get_flavor**: 所有角色可用
- **get_flavors**: 所有角色可用
- **delete_flavors**: 需要 admin 角色
