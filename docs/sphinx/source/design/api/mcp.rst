MCP服务接口
================

MCP（Model Context Protocol）服务接口用于 AI 助手与 QCOS 系统交互，
通过自然语言对话完成设备查询、作业提交、用户管理等操作。

MCP 服务挂载在 FastAPI 应用上，端点路径为 ``/v1/ai/mcp``，与常规
JSON-RPC API 端点区分。调用 MCP 工具前需先通过 ``qcos_login`` 认证
获取 JWT Token，后续调用自动在 HTTP Header 中携带
``Authorization: Bearer <token>``。

.. contents:: 目录
   :local:
   :depth: 3

认证接口
--------

.. list-table:: MCP 认证接口规范
   :widths: 20 20 30 30
   :header-rows: 1
   :align: left
   :class: longtable

   * - 用途
     - 方法
     - 请求参数
     - 返回值

   * - **用户登录**
     - **qcos_login**

       URI: /v1/ai/mcp
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "username": "admin",
               "password": "password"
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "user_name": "admin",
               "token_type": "bearer",
               "expires_in": 86400,
               "status": "logged in"
             }

系统信息接口
------------

.. list-table:: MCP 系统信息接口规范
   :widths: 20 20 30 30
   :header-rows: 1
   :align: left
   :class: longtable

   * - 用途
     - 方法
     - 请求参数
     - 返回值

   * - **获取系统版本和能力**
     - **qcos_get_version**

       URI: /v1/ai/mcp
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "details": true
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "version": "1.8.0",
               "api_version": "v1",
               "supported_api_versions": [
                 {"version": "v1", "status": "CURRENT"}
               ],
               "platform_version": "WUYUEQbit QCOS v1.8.0",
               "auth_mode": "yes",
               "capabilities": {
                 "job_types": ["sampling", "estimation"],
                 "drivers": {},
                 "transpilers": {},
                 "tech_types": {},
                 "profiling": {},
                 "driver_transpiler_mappings": {}
               }
             }

   * - **Ping 系统**
     - **qcos_ping**

       URI: /v1/ai/mcp
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "message": "hello"
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "message": "pong",
               "echo": "hello"
             }

   * - **获取系统健康状态**
     - **qcos_get_system_health**

       URI: /v1/ai/mcp
     - 无参数
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "system_healthy": true,
               "heartbeat": "2026-10-22T10:00:00",
               "components": {
                 "fastapi": "healthy",
                 "redis": "healthy",
                 "prefect": "healthy",
                 "worker": "healthy"
               }
             }

   * - **获取 API 统计**
     - **qcos_get_api_stats**

       URI: /v1/ai/mcp
     - 无参数
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "total_requests": 1000,
               "last_hour_requests": 50,
               "last_day_requests": 500
             }

   * - **获取作业统计**
     - **qcos_get_job_stats**

       URI: /v1/ai/mcp
     - 无参数
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "total": 100,
               "completed": 80,
               "failed": 5,
               "running": 3,
               "queued": 10,
               "cancelled": 2
             }

   * - **获取系统信息**
     - **qcos_system_info**

       URI: /v1/ai/mcp
     - 无参数
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "total_jobs_count": 1000
             }

   * - **显示内存占用**
     - **qcos_show_mem**

       URI: /v1/ai/mcp
     - 无参数
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "pid": 12345,
               "rss_mb": 256.5,
               "vms_mb": 512.3,
               "thread_count": 10,
               "num_objects": 50000,
               "cpu_percent": 5.2
             }

   * - **垃圾回收**
     - **qcos_gc_mem**

       URI: /v1/ai/mcp
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "generations": 2
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "collected": 100,
               "count_before": 50000,
               "count_after": 49900
             }

设备管理接口
------------

.. list-table:: MCP 设备管理接口规范
   :widths: 20 20 30 30
   :header-rows: 1
   :align: left
   :class: longtable

   * - 用途
     - 方法
     - 请求参数
     - 返回值

   * - **查询设备列表**
     - **qcos_list_devices**

       URI: /v1/ai/mcp
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "details": true
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "dummy": {
                 "name": "dummy",
                 "alias_name": "空载测试设备",
                 "driver_name": "DriverDummy",
                 "enable": true,
                 "status": "online",
                 "qubits": 6
               }
             }

   * - **查询设备详情**
     - **qcos_get_device_detail**

       URI: /v1/ai/mcp
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "name": "dummy",
               "details": true
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "name": "dummy",
               "alias_name": "空载测试设备",
               "driver_name": "DriverDummy",
               "enable": true,
               "status": "online",
               "configs": {},
               "details": {}
             }

   * - **设置设备属性**
     - **qcos_set_device**

       URI: /v1/ai/mcp
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "device_name": "dummy",
               "state": "online",
               "enable": true,
               "max_qubits": "100",
               "available_qubits": "6"
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "name": "dummy",
               "state": "online",
               "enable": true,
               "max_qubits": 100,
               "available_qubits": 6
             }

   * - **设备校准**
     - **qcos_calibrate_device**

       URI: /v1/ai/mcp
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "device_name": "dummy",
               "method": "xeb",
               "options": {}
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "status": "started",
               "device_name": "dummy",
               "method": "xeb"
             }

   * - **获取校准结果**
     - **qcos_get_calibrate_results**

       URI: /v1/ai/mcp
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "device_name": "dummy",
               "method": "xeb"
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "device_name": "dummy",
               "method": "xeb",
               "results": {}
             }

   * - **设置设备选项**
     - **qcos_set_device_options**

       URI: /v1/ai/mcp
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "device_name": "dummy",
               "method": "transpile",
               "options": {"optimization_level": 3}
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "status": "ok"
             }

   * - **获取设备选项**
     - **qcos_get_device_options**

       URI: /v1/ai/mcp
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "device_name": "dummy",
               "method": "transpile"
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "options": {"optimization_level": 3}
             }

作业管理接口
------------

.. list-table:: MCP 作业管理接口规范
   :widths: 20 20 30 30
   :header-rows: 1
   :align: left
   :class: longtable

   * - 用途
     - 方法
     - 请求参数
     - 返回值

   * - **提交作业**
     - **qcos_submit_job**

       URI: /v1/ai/mcp
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "source_code": ["OPENQASM 2.0; ..."],
               "code_type": "qasm",
               "backend": "dummy",
               "flavor_id": "",
               "extra_specs": {},
               "shots": 1024,
               "job_name": "test-job",
               "description": "test",
               "transpiler": "cmss",
               "dry_run": false,
               "job_priority": 5
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "job_id": "00000000-0000-4000-8000-000000000001",
               "job_status": "QUEUED"
             }

   * - **查询作业列表**
     - **qcos_list_jobs**

       URI: /v1/ai/mcp
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "job_status": "COMPLETED",
               "backend": "dummy",
               "page_size": 20,
               "page_num": 1
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "items": [
                 {
                   "job_id": "00000000-0000-4000-8000-000000000001",
                   "job_name": "test-job",
                   "job_status": "COMPLETED",
                   "backend": "dummy",
                   "created_at": "2026-10-22T10:00:00"
                 }
               ],
               "total": 1,
               "page": 1,
               "page_size": 20,
               "total_pages": 1
             }

   * - **查询作业状态**
     - **qcos_get_job_status**

       URI: /v1/ai/mcp
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "job_id": "00000000-0000-4000-8000-000000000001"
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "job_id": "00000000-0000-4000-8000-000000000001",
               "job_name": "test-job",
               "job_status": "COMPLETED",
               "job_priority": 5,
               "backend": "dummy",
               "progress": 100,
               "created_at": "2026-10-22T10:00:00",
               "updated_at": "2026-10-22T10:01:00"
             }

   * - **查询作业结果**
     - **qcos_get_job_result**

       URI: /v1/ai/mcp
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "job_id": "00000000-0000-4000-8000-000000000001"
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "job_id": "00000000-0000-4000-8000-000000000001",
               "counts": {"00": 512, "11": 512},
               "probabilities": {"00": 0.5, "11": 0.5}
             }

   * - **取消作业**
     - **qcos_cancel_jobs**

       URI: /v1/ai/mcp
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "job_ids": ["00000000-0000-4000-8000-000000000001"]
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "cancelled": ["00000000-0000-4000-8000-000000000001"]
             }

   * - **删除作业**
     - **qcos_delete_jobs**

       URI: /v1/ai/mcp
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "job_ids": ["00000000-0000-4000-8000-000000000001"]
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "deleted": ["00000000-0000-4000-8000-000000000001"]
             }

   * - **更新作业**
     - **qcos_update_job**

       URI: /v1/ai/mcp
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "job_id": "00000000-0000-4000-8000-000000000001",
               "job_name": "new-name",
               "description": "new description",
               "job_priority": 3
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "job_id": "00000000-0000-4000-8000-000000000001",
               "job_name": "new-name",
               "job_priority": 3
             }

资源规格接口
------------

.. list-table:: MCP 资源规格接口规范
   :widths: 20 20 30 30
   :header-rows: 1
   :align: left
   :class: longtable

   * - 用途
     - 方法
     - 请求参数
     - 返回值

   * - **创建资源规格**
     - **qcos_create_flavor**

       URI: /v1/ai/mcp
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "name": "g1.all",
               "device_groups": ["group-uuid"],
               "description": "通用规格",
               "is_public": true,
               "min_qubits": 1,
               "max_qubits": 100,
               "gate_fidelity_1q_min": 0.99,
               "gate_fidelity_2q_min": 0.95,
               "extra_properties": {},
               "project_id": ""
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "id": "flavor-uuid",
               "name": "g1.all",
               "device_groups": ["group-uuid"],
               "is_public": true
             }

   * - **更新资源规格**
     - **qcos_update_flavor**

       URI: /v1/ai/mcp
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "flavor_id": "flavor-uuid",
               "name": "g2.all",
               "min_qubits": 2
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "id": "flavor-uuid",
               "name": "g2.all",
               "min_qubits": 2
             }

   * - **查询资源规格详情**
     - **qcos_get_flavor**

       URI: /v1/ai/mcp
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "flavor_id": "flavor-uuid"
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "id": "flavor-uuid",
               "name": "g1.all",
               "device_groups": ["group-uuid"],
               "is_public": true
             }

   * - **查询资源规格列表**
     - **qcos_get_flavors**

       URI: /v1/ai/mcp
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "flavor_name": "g1",
               "flavor_ids": ["uuid1"],
               "page_size": 20,
               "page_num": 1
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "items": [
                 {
                   "id": "flavor-uuid",
                   "name": "g1.all",
                   "is_public": true
                 }
               ],
               "total": 1
             }

   * - **删除资源规格**
     - **qcos_delete_flavors**

       URI: /v1/ai/mcp
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "flavor_ids": ["uuid1", "uuid2"]
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "deleted": ["uuid1", "uuid2"]
             }

设备分组接口
------------

.. list-table:: MCP 设备分组接口规范
   :widths: 20 20 30 30
   :header-rows: 1
   :align: left
   :class: longtable

   * - 用途
     - 方法
     - 请求参数
     - 返回值

   * - **创建设备分组**
     - **qcos_create_device_group**

       URI: /v1/ai/mcp
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "name": "superconducting",
               "device_names": ["dummy", "wy_hanyuan1"],
               "description": "超导设备组",
               "is_public": true,
               "project_id": ""
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "id": "group-uuid",
               "name": "superconducting",
               "device_names": ["dummy", "wy_hanyuan1"]
             }

   * - **更新设备分组**
     - **qcos_update_device_group**

       URI: /v1/ai/mcp
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "group_id": "group-uuid",
               "name": "new-name",
               "device_names": ["dummy"]
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "id": "group-uuid",
               "name": "new-name",
               "device_names": ["dummy"]
             }

   * - **查询设备分组详情**
     - **qcos_get_device_group**

       URI: /v1/ai/mcp
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "group_id": "group-uuid"
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "id": "group-uuid",
               "name": "superconducting",
               "device_names": ["dummy"]
             }

   * - **查询设备分组列表**
     - **qcos_get_device_groups**

       URI: /v1/ai/mcp
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "group_name": "super",
               "group_ids": ["uuid1"],
               "page_size": 20,
               "page_num": 1
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "items": [
                 {
                   "id": "group-uuid",
                   "name": "superconducting"
                 }
               ],
               "total": 1
             }

   * - **删除设备分组**
     - **qcos_delete_device_groups**

       URI: /v1/ai/mcp
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "group_ids": ["uuid1", "uuid2"]
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "deleted": ["uuid1", "uuid2"]
             }

驱动与转译器接口
----------------

.. list-table:: MCP 驱动与转译器接口规范
   :widths: 20 20 30 30
   :header-rows: 1
   :align: left
   :class: longtable

   * - 用途
     - 方法
     - 请求参数
     - 返回值

   * - **查询驱动列表**
     - **qcos_get_drivers**

       URI: /v1/ai/mcp
     - 无参数
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "DriverDummy": {
                 "version": "1.0.0",
                 "tech_type": "superconducting",
                 "max_qubits": 100,
                 "supported_code_types": ["qasm"],
                 "supported_transpilers": ["cmss"]
               }
             }

   * - **查询驱动详情**
     - **qcos_get_driver**

       URI: /v1/ai/mcp
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "name": "DriverDummy"
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "name": "DriverDummy",
               "version": "1.0.0",
               "description": "空载测试驱动"
             }

   * - **查询转译器列表**
     - **qcos_get_transpilers**

       URI: /v1/ai/mcp
     - 无参数
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "cmss": {
                 "alias_name": "cmss",
                 "version": "1.0.0",
                 "supported_code_types": ["qasm2", "qasm3"]
               }
             }

   * - **查询转译器详情**
     - **qcos_get_transpiler**

       URI: /v1/ai/mcp
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "name": "cmss"
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "name": "cmss",
               "alias_name": "cmss",
               "version": "1.0.0",
               "options_schema": {}
             }

项目管理接口
------------

.. list-table:: MCP 项目管理接口规范
   :widths: 20 20 30 30
   :header-rows: 1
   :align: left
   :class: longtable

   * - 用途
     - 方法
     - 请求参数
     - 返回值

   * - **创建项目**
     - **qcos_create_project**

       URI: /v1/ai/mcp
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "project_name": "project1",
               "description": "测试项目"
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "id": "project-uuid",
               "name": "project1",
               "description": "测试项目"
             }

   * - **查询项目详情**
     - **qcos_get_project**

       URI: /v1/ai/mcp
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "project_id": "project-uuid"
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "id": "project-uuid",
               "name": "project1",
               "description": "测试项目"
             }

   * - **查询项目列表**
     - **qcos_get_projects**

       URI: /v1/ai/mcp
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "project_name": "project1",
               "page_size": 20,
               "page_num": 1
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "items": [
                 {
                   "id": "project-uuid",
                   "name": "project1"
                 }
               ],
               "total": 1
             }

   * - **更新项目**
     - **qcos_update_project**

       URI: /v1/ai/mcp
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "project_id": "project-uuid",
               "project_name": "new-name",
               "description": "new desc"
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "id": "project-uuid",
               "name": "new-name"
             }

   * - **删除项目**
     - **qcos_delete_project**

       URI: /v1/ai/mcp
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "project_id": "project-uuid"
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "name": "project1",
               "deleted_at": "2026-10-22T10:00:00"
             }

用户与角色管理接口（管理员）
----------------------------

.. list-table:: MCP 用户与角色管理接口规范
   :widths: 20 20 30 30
   :header-rows: 1
   :align: left
   :class: longtable

   * - 用途
     - 方法
     - 请求参数
     - 返回值

   * - **获取当前用户**
     - **qcos_get_current_user**

       URI: /v1/ai/mcp
     - 无参数
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "user_name": "admin",
               "project_id": "project-uuid",
               "roles": ["admin"]
             }

   * - **创建用户**
     - **qcos_create_user**

       URI: /v1/ai/mcp
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "user_name": "user1",
               "password": "password",
               "roles": ["user"],
               "project_id": "project-uuid",
               "password_expiry_days": 90,
               "is_enabled": true,
               "is_locked": false,
               "description": "测试用户"
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "id": "user-uuid",
               "user_name": "user1",
               "roles": ["user"]
             }

   * - **查询用户详情**
     - **qcos_get_user**

       URI: /v1/ai/mcp
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "user_id": "user-uuid"
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "id": "user-uuid",
               "user_name": "user1",
               "roles": ["user"]
             }

   * - **查询用户列表**
     - **qcos_get_users**

       URI: /v1/ai/mcp
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "user_name": "user1",
               "page_size": 20,
               "page_num": 1
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "items": [
                 {
                   "id": "user-uuid",
                   "user_name": "user1"
                 }
               ],
               "total": 1
             }

   * - **更新用户**
     - **qcos_update_user**

       URI: /v1/ai/mcp
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "user_id": "user-uuid",
               "roles": ["admin"],
               "is_enabled": true
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "id": "user-uuid",
               "user_name": "user1",
               "roles": ["admin"]
             }

   * - **删除用户**
     - **qcos_delete_user**

       URI: /v1/ai/mcp
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "user_id": "user-uuid",
               "force": false
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "user_name": "user1",
               "deleted_at": "2026-10-22T10:00:00"
             }

   * - **修改密码**
     - **qcos_change_password**

       URI: /v1/ai/mcp
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "user_id": "user-uuid",
               "new_password": "new-password",
               "old_password": "old-password"
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "status": "password changed"
             }

   * - **创建角色**
     - **qcos_create_role**

       URI: /v1/ai/mcp
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "role_name": "operator",
               "permissions": ["job:submit", "device:read"],
               "description": "操作员角色"
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "id": "role-uuid",
               "role_name": "operator",
               "permissions": ["job:submit", "device:read"]
             }

   * - **查询角色详情**
     - **qcos_get_role**

       URI: /v1/ai/mcp
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "role_id": "role-uuid"
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "id": "role-uuid",
               "role_name": "operator",
               "permissions": ["job:submit"]
             }

   * - **查询角色列表**
     - **qcos_get_roles**

       URI: /v1/ai/mcp
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "role_name": "operator",
               "page_size": 20,
               "page_num": 1
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "items": [
                 {
                   "id": "role-uuid",
                   "role_name": "operator"
                 }
               ],
               "total": 1
             }

   * - **更新角色**
     - **qcos_update_role**

       URI: /v1/ai/mcp
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "role_id": "role-uuid",
               "permissions": ["job:submit", "device:read", "device:write"]
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "id": "role-uuid",
               "role_name": "operator",
               "permissions": ["job:submit", "device:read", "device:write"]
             }

   * - **删除角色**
     - **qcos_delete_role**

       URI: /v1/ai/mcp
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "role_id": "role-uuid"
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "role_name": "operator"
             }

   * - **获取用户管理状态**
     - **qcos_get_user_mgmt**

       URI: /v1/ai/mcp
     - 无参数
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "auth_mode": "yes",
               "password_expiry_days": 90,
               "max_login_attempts": 5,
               "lockout_duration_minutes": 30
             }

   * - **设置认证模式**
     - **qcos_set_user_mgmt**

       URI: /v1/ai/mcp
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "auth_mode": "jwt"
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "auth_mode": "jwt",
               "message": "auth mode updated"
             }

   * - **获取登录日志**
     - **qcos_get_login_logs**

       URI: /v1/ai/mcp
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "user_id": "user-uuid",
               "user_name": "admin",
               "start_time": "2026-10-01T00:00:00",
               "end_time": "2026-10-31T23:59:59",
               "page_size": 20,
               "page_num": 1
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "items": [
                 {
                   "user_name": "admin",
                   "login_time": "2026-10-22T10:00:00",
                   "ip": "127.0.0.1"
                 }
               ],
               "total": 1
             }

   * - **清除登录日志**
     - **qcos_clear_login_logs**

       URI: /v1/ai/mcp
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "user_id": "user-uuid",
               "user_name": "admin"
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "deleted_count": 10
             }

Worker 管理接口
---------------

.. list-table:: MCP Worker 管理接口规范
   :widths: 20 20 30 30
   :header-rows: 1
   :align: left
   :class: longtable

   * - 用途
     - 方法
     - 请求参数
     - 返回值

   * - **查询 Worker 列表**
     - **qcos_list_workers**

       URI: /v1/ai/mcp
     - 无参数
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "workers": [
                 {
                   "worker_name": "worker-1",
                   "work_pool": "default",
                   "device_name": "dummy",
                   "worker_status": "online",
                   "pid": 12345
                 }
               ]
             }

   * - **重启 Worker**
     - **qcos_restart_worker**

       URI: /v1/ai/mcp
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "worker_name": "worker-1"
             }
     - .. container:: table-code-small-font

          .. code-block:: json

             {
               "status": "restarted",
               "worker_name": "worker-1"
             }

相关文档
--------

- MCP 用户使用手册：:doc:`../../user-guide/mcp/mcp`
- MCP 模块设计：:doc:`../module-design/mcp`
